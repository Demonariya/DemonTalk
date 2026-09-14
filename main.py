"""DemonTalk - Offline Walkie-Talkie Application

Simple HTTP server for p4a webview bootstrap.
"""
import os
import sys
import json
import threading

sys.path.insert(0, os.path.dirname(__file__))

from app.config import AppConfig
from app.database.db import Database
from app.services.connection_service import ConnectionService
from app.web.bridge import WebBridge
from app.utils.logger import setup_logger

log = setup_logger('Main')

WEB_DIR = os.path.join(os.path.dirname(__file__), 'app', 'web')

from http.server import HTTPServer, SimpleHTTPRequestHandler


class DemonTalkHandler(SimpleHTTPRequestHandler):
    bridge = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode()
        result = self.bridge.handle(body) if self.bridge else '{}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(result.encode())

    def log_message(self, format, *args):
        pass


def run():
    bridge = WebBridge(None)
    DemonTalkHandler.bridge = bridge
    bridge.service.start()

    # Push peer count periodically
    events = []
    bridge._push = lambda event, data: events.append({'event': event, 'data': data})

    server = HTTPServer(('0.0.0.0', 5000), DemonTalkHandler)
    log.info("DemonTalk server running on port 5000")
    server.serve_forever()


if __name__ == '__main__':
    run()
