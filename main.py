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
    """Run with native Android WebView via pyjnius."""
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.RECORD_AUDIO, Permission.ACCESS_WIFI_STATE,
            Permission.CHANGE_WIFI_STATE, Permission.ACCESS_NETWORK_STATE,
            Permission.ACCESS_FINE_LOCATION, Permission.WAKE_LOCK,
            Permission.FOREGROUND_SERVICE, Permission.POST_NOTIFICATIONS,
        ])
    except ImportError:
        pass

    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    activity = PythonActivity.mActivity
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    WebChromeClient = autoclass('android.webkit.WebChromeClient')

    webview_ref = [None]
    bridge_ref = [None]

    bridge = WebBridge(None)
    bridge_ref[0] = bridge

    # Start local HTTP server
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
            pass

    server = HTTPServer(('127.0.0.1', 8080), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Local HTTP server started on port 8080")

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
                    pid = json.loads(payload)['id']
                    escaped = result.replace('\\', '\\\\').replace("'", "\\'")
                    wv.evaluateJavascript(
                        f"Bridge._onResponse({pid}, '{escaped}')", None
                    )
                except Exception as e:
                    log.error(f"JS bridge error: {e}")

        js_interface = PyBridge(bridge)
        wv.addJavascriptInterface(js_interface, "pyBridge")
        webview_ref[0] = wv
        bridge.webview = wv

        # Load HTML from local server
        wv.loadUrl("http://127.0.0.1:8080")
        log.info("WebView loaded")

        bridge.service.start()

        # Periodic peer count push
        def push_loop():
            import time
            while True:
                try:
                    if bridge_ref[0]:
                        count = bridge.service.peer_count
                        js = f"Bridge._onEvent('peer_connected', '{{\"count\": {count}}}')"
                        activity.runOnUiThread(lambda j=js: wv.evaluateJavascript(j, None))
                except Exception:
                    pass
                time.sleep(3)

        threading.Thread(target=push_loop, daemon=True).start()

    import time
    time.sleep(0.5)
    setup_webview()

    # Keep alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        bridge.service.stop()


def run_desktop():
    """Run with local HTTP server for desktop testing."""
    import webbrowser
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from urllib.parse import urlparse

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
            pass

    bridge = WebBridge(None)
    bridge_ref[0] = bridge
    bridge.service.start()

    _events = []
    bridge._push = lambda event, data: _events.append({'event': event, 'data': data})

    def enhanced_post(self_handler):
        length = int(self_handler.headers.get('Content-Length', 0))
        body = self_handler.rfile.read(length).decode()
        try:
            payload = json.loads(body)
            if payload.get('method') == 'poll':
                events = _events[:]
                _events.clear()
                result = json.dumps({'id': payload['id'], 'ok': True, 'data': events})
                self_handler.send_response(200)
                self_handler.send_header('Content-Type', 'application/json')
                self_handler.send_header('Access-Control-Allow-Origin', '*')
                self_handler.end_headers()
                self_handler.wfile.write(result.encode())
                return
        except (json.JSONDecodeError, KeyError):
            pass
        result = bridge_ref[0].handle(body) if bridge_ref[0] else '{}'
        self_handler.send_response(200)
        self_handler.send_header('Content-Type', 'application/json')
        self_handler.send_header('Access-Control-Allow-Origin', '*')
        self_handler.end_headers()
        self_handler.wfile.write(result.encode())

    Handler.do_POST = lambda self: enhanced_post(self)

    port = 8080
    server = HTTPServer(('127.0.0.1', port), Handler)
    log.info(f"Desktop server at http://127.0.0.1:{port}")

    threading.Thread(target=server.serve_forever, daemon=True).start()
    webbrowser.open(f'http://127.0.0.1:{port}')
    log.info("Desktop mode running.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        bridge.service.stop()
        server.shutdown()


if __name__ == '__main__':
    if sys.platform == 'android' or os.path.exists('/system/build.prop'):
        run_android()
    else:
        run_desktop()
