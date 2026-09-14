"""DemonTalk - Offline Walkie-Talkie Application

WebView-based UI. Runs on Android via native WebView, desktop via HTTP server.
"""
import os
import sys
import json
import threading

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('KIVY_LOG_LEVEL', 'warning')

from app.config import AppConfig, DATA_DIR
from app.database.db import Database
from app.services.connection_service import ConnectionService
from app.web.bridge import WebBridge
from app.utils.logger import setup_logger

log = setup_logger('Main')

WEB_DIR = os.path.join(os.path.dirname(__file__), 'app', 'web')


def run_android():
    """Run with native Android WebView."""
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.utils import platform

    if platform == 'android':
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.RECORD_AUDIO, Permission.ACCESS_WIFI_STATE,
            Permission.CHANGE_WIFI_STATE, Permission.ACCESS_NETWORK_STATE,
            Permission.ACCESS_FINE_LOCATION, Permission.WAKE_LOCK,
            Permission.FOREGROUND_SERVICE, Permission.POST_NOTIFICATIONS,
        ])

    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread

    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    WebChromeClient = autoclass('android.webkit.WebChromeClient')
    WebSettings = autoclass('android.webkit.WebSettings')
    Context = autoclass('android.content.Context')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ValueCallback = autoclass('android.webkit.ValueCallback')
    JSInterface = autoclass('android.webkit.JavascriptInterface')
    Uri = autoclass('android.net.Uri')
    PythonJavaCallback = autoclass('org.jnius.PythonJavaCallback')

    activity = PythonActivity.mActivity
    current_app = App.get_running_app()

    webview = [None]
    bridge_ref = [None]

    @run_on_ui_thread
    def setup_webview():
        wv = WebView(activity)
        settings = wv.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setAllowFileAccess(True)
        settings.setAllowContentAccess(True)
        settings.setMediaPlaybackRequiresUserGesture(False)
        settings.setUseWideViewPort(True)
        settings.setLoadWithOverviewMode(True)

        wv.setWebViewClient(WebViewClient())
        wv.setWebChromeClient(WebChromeClient())

        # JavaScript interface
        class PyBridge:
            def __init__(self, br):
                self._bridge = br

            def call(self, payload):
                try:
                    result = self._bridge.handle(payload)
                    wv.evaluateJavascript(
                        f"Bridge._onResponse({json.loads(payload)['id']}, '{result.replace(chr(39), chr(92)+chr(39)).replace(chr(10), ' ')}')",
                        None
                    )
                except Exception as e:
                    log.error(f"JS bridge call error: {e}")

        bridge = WebBridge(None)
        bridge_ref[0] = bridge
        bridge.webview = wv

        js_interface = PyBridge(bridge)
        wv.addJavascriptInterface(js_interface, "pyBridge")

        activity.setContentView(wv)
        webview[0] = wv

        # Load HTML
        html_path = f"file://{WEB_DIR}/index.html"
        wv.loadUrl(html_path)
        log.info("WebView loaded")

        # Start connection service
        bridge.service.start()

        # Push events periodically
        def push_loop():
            while True:
                try:
                    if bridge_ref[0]:
                        peers = bridge.service.net.get_connected_peers()
                        count = len(peers)
                        Clock.schedule_once(lambda dt, c=count: bridge._push('peer_connected', {'count': c}))
                except Exception:
                    pass
                import time
                time.sleep(3)

        t = threading.Thread(target=push_loop, daemon=True)
        t.start()

    Clock.schedule_once(lambda dt: setup_webview(), 0.5)

    class DemonTalkApp(App):
        def build(self):
            from kivy.uix.widget import Widget
            return Widget()

        def on_pause(self):
            return True

        def on_stop(self):
            bridge = bridge_ref[0]
            if bridge:
                bridge.service.stop()

    DemonTalkApp().run()


def run_desktop():
    """Run with local HTTP server for desktop testing."""
    import webbrowser
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    bridge_ref = [None]

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=WEB_DIR, **kwargs)

        def do_GET(self):
            if self.path == '/':
                self.path = '/index.html'
            super().do_GET()

        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            result = bridge_ref[0].handle(body) if bridge_ref[0] else '{}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(result.encode())

        def log_message(self, format, *args):
            pass  # Silence request logs

    bridge = WebBridge(None)
    bridge_ref[0] = bridge
    bridge.service.start()

    # Patch bridge to push via polling instead of WebView
    bridge._push = lambda event, data: None  # Desktop uses polling

    # Add polling endpoint
    _events = []
    _original_push = bridge._push

    def capture_push(event, data):
        _events.append({'event': event, 'data': data})

    bridge._push = capture_push

    orig_do_post = Handler.do_POST

    def enhanced_post(self):
        nonlocal _events
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode()

        parsed = urlparse(body)
        # Check if it's a poll request
        try:
            payload = json.loads(body)
            if payload.get('method') == 'poll':
                events = _events[:]
                _events.clear()
                result = json.dumps({'id': payload['id'], 'ok': True, 'data': events})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(result.encode())
                return
        except (json.JSONDecodeError, KeyError):
            pass

        result = bridge_ref[0].handle(body) if bridge_ref[0] else '{}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(result.encode())

    Handler.do_POST = enhanced_post

    port = 8080
    server = HTTPServer(('127.0.0.1', port), Handler)
    log.info(f"Desktop server at http://127.0.0.1:{port}")

    # Add poll function to bridge for desktop
    bridge._push = capture_push

    threading.Thread(target=server.serve_forever, daemon=True).start()

    webbrowser.open(f'http://127.0.0.1:{port}')
    log.info("Desktop mode running. Press Ctrl+C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        bridge.service.stop()
        server.shutdown()


if __name__ == '__main__':
    try:
        from kivy.utils import platform as _plat
        _is_android = (_plat == 'android')
    except ImportError:
        _is_android = False
    if _is_android:
        run_android()
    else:
        run_desktop()
