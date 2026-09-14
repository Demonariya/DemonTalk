"""Connection manager - orchestrates all networking."""
import threading
import time
import uuid
from app.config import AppConfig, VOICE_PORT, TCP_SERVER_PORT
from app.networking.udp_handler import UDPHandler
from app.networking.tcp_server import TCPServer
from app.networking.tcp_client import TCPClient
from app.database.db import Database
from app.utils.logger import setup_logger

log = setup_logger('NetMgr')


class ConnectionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.config = AppConfig()
        self.db = Database()
        self.device_id = self.config.get('device_id') or self._init_device_id()
        self.device_name = self.config.get('device_name')
        self.current_channel = None
        self.udp = UDPHandler(self.device_id, self.device_name)
        self.tcp_server = TCPServer(self.device_id, self.device_name, TCP_SERVER_PORT)
        self.tcp_client = TCPClient(self.device_id, self.device_name)
        self._callbacks = {}
        self._heartbeat_thread = None
        self._running = False
        self._connected_peers = {}
        self._state = 'offline'
        self._connect_events()

    def _init_device_id(self):
        did = str(uuid.uuid4()).replace('-', '')[:32]
        self.config.set('device_id', did)
        return did

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Event {event} callback error: {e}")

    def _connect_events(self):
        self.udp.on('device_found', self._on_device_found)
        self.udp.on('voice_data', self._on_voice_data)
        self.udp.on('text_message', self._on_text_message)
        self.udp.on('heartbeat', self._on_heartbeat)
        self.udp.on('emergency', self._on_emergency)
        self.tcp_server.on('text_message', self._on_text_message)
        self.tcp_server.on('client_connected', self._on_client_connected)
        self.tcp_client.on('text_message', self._on_text_message)
        self.tcp_client.on('voice_data', self._on_voice_data)
        self.tcp_client.on('connected', self._on_tcp_connected)
        self.tcp_client.on('disconnected', self._on_tcp_disconnected)

    def start(self):
        if self._running:
            return
        self._running = True
        self.udp.start()
        self.tcp_server.start()
        self._start_heartbeat()
        self._set_state('ready')
        log.info(f"Connection manager started | ID: {self.device_id[:8]}")

    def stop(self):
        self._running = False
        self.udp.stop()
        self.tcp_server.stop()
        self.tcp_client.disconnect()
        self._set_state('offline')
        log.info("Connection manager stopped")

    def _start_heartbeat(self):
        def loop():
            while self._running:
                self.udp.send_heartbeat()
                self._cleanup_stale_peers()
                time.sleep(5)
        self._heartbeat_thread = threading.Thread(target=loop, daemon=True, name='heartbeat')
        self._heartbeat_thread.start()

    def _cleanup_stale_peers(self):
        now = time.time()
        stale = [pid for pid, p in self._connected_peers.items() if now - p.get('last_seen', 0) > 20]
        for pid in stale:
            self._connected_peers.pop(pid, None)
            self._emit('peer_disconnected', pid)

    def _set_state(self, state: str):
        self._state = state
        self._emit('state_changed', state)

    # --- Event handlers ---
    def _on_device_found(self, device_id, device_name, ip, payload):
        import json
        try:
            info = json.loads(payload)
        except Exception:
            info = {}
        port = info.get('port', VOICE_PORT)
        self.db.add_device(device_id, device_name, ip, port)
        self._connected_peers[device_id] = {
            'name': device_name, 'ip': ip, 'port': port,
            'last_seen': time.time(), 'channels': info.get('channels', []),
        }
        self._emit('device_found', device_id, device_name, ip, info)

    def _on_heartbeat(self, device_id, device_name, ip):
        if device_id in self._connected_peers:
            self._connected_peers[device_id]['last_seen'] = time.time()
        self.db.update_device_seen(device_id, ip)

    def _on_voice_data(self, source_id, source_name, audio_data, ip=''):
        if source_id == self.device_id:
            return
        if self.current_channel:
            self.db.update_device_seen(source_id, ip)
        self._emit('voice_received', source_id, source_name, audio_data)

    def _on_text_message(self, source_id, source_name, message, channel_id='', ip=''):
        if source_id == self.device_id:
            return
        self.db.add_message(source_id, source_name, message, channel_id=channel_id)
        self._emit('message_received', source_id, source_name, message, channel_id)

    def _on_emergency(self, source_id, source_name, message, ip=''):
        self._emit('emergency', source_id, source_name, message)

    def _on_client_connected(self, device_id, device_name, ip):
        log.info(f"TCP client connected: {device_name} from {ip}")

    def _on_tcp_connected(self, ip, port):
        self._set_state('connected')
        self._emit('peer_connected', ip, port)

    def _on_tcp_disconnected(self):
        self._set_state('ready')
        self._emit('peer_disconnected', 'tcp')

    # --- Public API ---
    def send_voice(self, audio_data: bytes, channel_id: str = ''):
        if self.tcp_client.is_connected:
            self.tcp_client.send_voice_data(audio_data)
        else:
            self.udp.send_voice(audio_data, channel_id)

    def send_text(self, message: str, channel_id: str = ''):
        ch = channel_id or None
        if self.tcp_client.is_connected:
            self.tcp_client.send_text(message, ch)
        else:
            self.udp.send_text(message, ch)
        self.db.add_message(self.device_id, self.device_name, message, channel_id=ch)

    def send_emergency(self, message: str = 'EMERGENCY'):
        self.udp.send_emergency(message)

    def connect_to_peer(self, ip: str, port: int = TCP_SERVER_PORT) -> bool:
        return self.tcp_client.connect(ip, port)

    def disconnect_peer(self):
        self.tcp_client.disconnect()

    def join_channel(self, channel_id: str):
        self.current_channel = channel_id
        self._emit('channel_joined', channel_id)

    def leave_channel(self):
        old = self.current_channel
        self.current_channel = None
        if old:
            self._emit('channel_left', old)

    def get_connected_peers(self):
        peers = self.udp.get_peers()
        peers.update(self._connected_peers)
        return peers

    def get_peer_count(self):
        return len(self.get_connected_peers())

    @property
    def state(self):
        return self._state

    @property
    def is_online(self):
        return self._state in ('ready', 'connected', 'transmitting', 'receiving')
