"""TCP client for connecting to peers."""
import socket
import threading
import json
import time
from app.utils.logger import setup_logger

log = setup_logger('TCP-Client')


class TCPClient:
    def __init__(self, device_id: str, device_name: str):
        self.device_id = device_id
        self.device_name = device_name
        self._sock = None
        self._connected = False
        self._target_ip = None
        self._target_port = None
        self._lock = threading.Lock()
        self._callbacks = {}
        self._recv_thread = None
        self._running = False

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Callback error: {e}")

    def connect(self, ip: str, port: int = 37023) -> bool:
        if self._connected:
            self.disconnect()
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5.0)
            self._sock.connect((ip, port))
            self._target_ip = ip
            self._target_port = port
            register = json.dumps({
                'type': 'register',
                'device_id': self.device_id,
                'device_name': self.device_name,
            }).encode()
            self._send_msg(register)
            resp_data = self._recv_msg()
            if resp_data:
                resp = json.loads(resp_data.decode())
                if resp.get('type') == 'registered':
                    self._connected = True
                    self._running = True
                    self._sock.settimeout(30.0)
                    self._recv_thread = threading.Thread(
                        target=self._recv_loop, daemon=True, name='tcp-recv'
                    )
                    self._recv_thread.start()
                    self._emit('connected', ip, port)
                    log.info(f"Connected to {ip}:{port}")
                    return True
        except Exception as e:
            log.error(f"Connection failed to {ip}:{port}: {e}")
        self._cleanup()
        return False

    def disconnect(self):
        self._running = False
        self._connected = False
        self._cleanup()
        self._emit('disconnected')
        log.info("Disconnected")

    def _cleanup(self):
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _send_msg(self, data: bytes):
        header = len(data).to_bytes(4, 'big')
        self._sock.sendall(header + data)

    def _recv_msg(self) -> bytes:
        header = b''
        while len(header) < 4:
            chunk = self._sock.recv(4 - len(header))
            if not chunk:
                return b''
            header += chunk
        msg_len = int.from_bytes(header, 'big')
        if msg_len > 10 * 1024 * 1024:
            return b''
        data = b''
        while len(data) < msg_len:
            chunk = self._sock.recv(min(msg_len - len(data), 65536))
            if not chunk:
                return b''
            data += chunk
        return data

    def _recv_loop(self):
        while self._running and self._connected:
            try:
                data = self._recv_msg()
                if not data:
                    break
                msg = json.loads(data.decode())
                msg_type = msg.get('type', '')
                if msg_type == 'text':
                    self._emit('text_message', msg.get('sender_id', ''),
                              msg.get('sender_name', ''), msg.get('message', ''),
                              msg.get('channel_id', ''))
                elif msg_type == 'voice_start':
                    self._emit('voice_start', msg.get('sender_id', ''), msg.get('sample_rate', 16000))
                elif msg_type == 'voice_data':
                    import base64
                    audio = base64.b64decode(msg.get('audio', ''))
                    self._emit('voice_data', msg.get('sender_id', ''), audio)
                elif msg_type == 'voice_stop':
                    self._emit('voice_stop', msg.get('sender_id', ''))
                else:
                    self._emit('message', msg)
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
            except Exception as e:
                log.error(f"Recv error: {e}")
                break
        self._connected = False
        self._emit('disconnected')

    def send_text(self, message: str, channel_id: str = ''):
        if not self._connected:
            return False
        msg = json.dumps({
            'type': 'text',
            'sender_id': self.device_id,
            'sender_name': self.device_name,
            'message': message,
            'channel_id': channel_id,
        }).encode()
        try:
            with self._lock:
                self._send_msg(msg)
            return True
        except (BrokenPipeError, OSError):
            self._connected = False
            return False

    def send_voice_start(self, sample_rate: int = 16000):
        msg = json.dumps({
            'type': 'voice_start',
            'sender_id': self.device_id,
            'sample_rate': sample_rate,
        }).encode()
        try:
            with self._lock:
                self._send_msg(msg)
        except (BrokenPipeError, OSError):
            pass

    def send_voice_data(self, audio_bytes: bytes):
        import base64
        msg = json.dumps({
            'type': 'voice_data',
            'sender_id': self.device_id,
            'audio': base64.b64encode(audio_bytes).decode(),
        }).encode()
        try:
            with self._lock:
                self._send_msg(msg)
        except (BrokenPipeError, OSError):
            pass

    def send_voice_stop(self):
        msg = json.dumps({
            'type': 'voice_stop',
            'sender_id': self.device_id,
        }).encode()
        try:
            with self._lock:
                self._send_msg(msg)
        except (BrokenPipeError, OSError):
            pass

    @property
    def is_connected(self):
        return self._connected
