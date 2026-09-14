"""TCP server for reliable text messaging and file transfers."""
import socket
import threading
import json
import time
from app.networking.packet import Packet
from app.utils.logger import setup_logger

log = setup_logger('TCP-Server')


class TCPServer:
    HEADER_SIZE = 4

    def __init__(self, device_id: str, device_name: str, port: int = 37023):
        self.device_id = device_id
        self.device_name = device_name
        self.port = port
        self._running = False
        self._server_sock = None
        self._clients = {}
        self._callbacks = {}
        self._lock = threading.Lock()

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Callback error: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        self._server_sock.bind(('', self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        t = threading.Thread(target=self._accept_loop, daemon=True, name='tcp-accept')
        t.start()
        log.info(f"TCP server started on port {self.port}")

    def stop(self):
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
        with self._lock:
            for sock in self._clients.values():
                try:
                    sock.close()
                except OSError:
                    pass
            self._clients.clear()
        log.info("TCP server stopped")

    def _accept_loop(self):
        while self._running:
            try:
                client_sock, addr = self._server_sock.accept()
                client_sock.settimeout(30.0)
                t = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                    name=f'tcp-client-{addr[1]}'
                )
                t.start()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(0.5)

    def _handle_client(self, sock: socket.socket, addr):
        device_id = None
        try:
            while self._running:
                header = self._recv_exact(sock, 4)
                if not header:
                    break
                msg_len = int.from_bytes(header, 'big')
                if msg_len > 10 * 1024 * 1024:
                    break
                data = self._recv_exact(sock, msg_len)
                if not data:
                    break
                msg = json.loads(data.decode())
                if msg.get('type') == 'register':
                    device_id = msg.get('device_id', '')
                    with self._lock:
                        self._clients[device_id] = sock
                    self._emit('client_connected', device_id, msg.get('device_name', ''), addr[0])
                    resp = json.dumps({'type': 'registered', 'device_id': self.device_id}).encode()
                    self._send_message(sock, resp)
                elif msg.get('type') == 'text':
                    self._emit('text_message', msg.get('sender_id', device_id),
                              msg.get('sender_name', ''), msg.get('message', ''),
                              msg.get('channel_id', ''), addr[0])
        except (ConnectionResetError, BrokenPipeError, socket.timeout):
            pass
        except Exception as e:
            log.error(f"Client handler error: {e}")
        finally:
            if device_id:
                with self._lock:
                    self._clients.pop(device_id, None)
            try:
                sock.close()
            except OSError:
                pass

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        data = b''
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return b''
            data += chunk
        return data

    def _send_message(self, sock: socket.socket, data: bytes):
        header = len(data).to_bytes(4, 'big')
        sock.sendall(header + data)

    def send_to(self, device_id: str, message: dict):
        with self._lock:
            sock = self._clients.get(device_id)
        if sock:
            try:
                self._send_message(sock, json.dumps(message).encode())
                return True
            except (BrokenPipeError, OSError):
                with self._lock:
                    self._clients.pop(device_id, None)
        return False

    def broadcast(self, message: dict):
        data = json.dumps(message).encode()
        dead = []
        with self._lock:
            for did, sock in self._clients.items():
                try:
                    self._send_message(sock, data)
                except (BrokenPipeError, OSError):
                    dead.append(did)
        for did in dead:
            with self._lock:
                self._clients.pop(did, None)

    def get_client_count(self):
        with self._lock:
            return len(self._clients)
