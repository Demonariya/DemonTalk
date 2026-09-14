"""Main connection service orchestrating all components."""
import threading
import time
from app.config import AppConfig
from app.database.db import Database
from app.networking.manager import ConnectionManager
from app.discovery.discovery import DeviceDiscovery
from app.audio.recorder import AudioRecorder
from app.audio.player import AudioPlayer
from app.audio.processor import compute_amplitude, apply_gain
from app.utils.logger import setup_logger

log = setup_logger('Service')


class ConnectionService:
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
        self.net = ConnectionManager()
        self.discovery = DeviceDiscovery()
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()
        self._callbacks = {}
        self._transmitting = False
        self._running = False
        self._current_channel = None
        self._connect_events()

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Service callback error: {e}")

    def _connect_events(self):
        self.net.on('device_found', self._on_device_found)
        self.net.on('voice_received', self._on_voice_received)
        self.net.on('message_received', self._on_message_received)
        self.net.on('emergency', self._on_emergency)
        self.net.on('state_changed', self._on_state_changed)
        self.net.on('peer_connected', self._on_peer_connected)
        self.net.on('peer_disconnected', self._on_peer_disconnected)

    def start(self):
        if self._running:
            return
        self._running = True
        self.net.start()
        self.player.start()
        self._emit('service_started')
        log.info("Connection service started")

    def stop(self):
        self._running = False
        if self._transmitting:
            self.stop_transmitting()
        self.net.stop()
        self.player.stop()
        self._emit('service_stopped')
        log.info("Connection service stopped")

    def start_transmitting(self, channel_id: str = ''):
        if self._transmitting:
            return
        self._transmitting = True
        self._emit('transmitting_started')
        self.player.stop()
        self.recorder.on('audio_chunk', self._on_audio_chunk)
        self.recorder.start()
        log.info("Transmitting started")

    def stop_transmitting(self):
        if not self._transmitting:
            return
        self._transmitting = False
        self.recorder.stop()
        self.player.start()
        self._emit('transmitting_stopped')
        log.info("Transmitting stopped")

    def _on_audio_chunk(self, data: bytes):
        if self._transmitting:
            sensitivity = self.config.get('audio', 'mic_sensitivity') or 0.8
            if self.config.get('audio', 'noise_suppression'):
                from app.audio.processor import simple_noise_gate
                data = simple_noise_gate(data, threshold=0.01)
            data = apply_gain(data, sensitivity)
            self.net.send_voice(data, self._current_channel or '')
            amp = compute_amplitude(data)
            self._emit('audio_level', amp)

    def _on_device_found(self, device_id, name, ip, info):
        self.discovery.register_device(device_id, name, ip)
        self._emit('device_found', device_id, name, ip, info)

    def _on_voice_received(self, source_id, source_name, audio_data):
        self.player.feed(audio_data)
        amp = compute_amplitude(audio_data)
        self._emit('voice_received', source_id, source_name, audio_data)
        self._emit('receive_level', amp)

    def _on_message_received(self, source_id, source_name, message, channel_id):
        self._emit('message_received', source_id, source_name, message, channel_id)

    def _on_emergency(self, source_id, source_name, message):
        self.player.play_notification('emergency')
        self._emit('emergency', source_id, source_name, message)

    def _on_state_changed(self, state):
        self._emit('state_changed', state)

    def _on_peer_connected(self, ip, port):
        self.player.play_notification('connect')
        self._emit('peer_connected', ip, port)

    def _on_peer_disconnected(self, peer_id):
        self.player.play_notification('disconnect')
        self._emit('peer_disconnected', peer_id)

    def send_text(self, message: str, channel_id: str = ''):
        self.net.send_text(message, channel_id)

    def join_channel(self, channel_id: str):
        self._current_channel = channel_id
        self.net.join_channel(channel_id)
        self._emit('channel_joined', channel_id)

    def leave_channel(self):
        old = self._current_channel
        self._current_channel = None
        self.net.leave_channel()
        if old:
            self._emit('channel_left', old)

    def create_channel(self, name: str, password: str = '') -> str:
        import uuid
        cid = str(uuid.uuid4())[:8]
        self.db.create_channel(cid, name, password, self.net.device_id)
        return cid

    def connect_to_device(self, ip: str, port: int = 37023) -> bool:
        return self.net.connect_to_peer(ip, port)

    def send_emergency(self, msg: str = 'EMERGENCY'):
        self.net.send_emergency(msg)

    @property
    def is_transmitting(self):
        return self._transmitting

    @property
    def state(self):
        return self.net.state

    @property
    def peer_count(self):
        return self.net.get_peer_count()
