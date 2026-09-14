"""Device discovery manager."""
import threading
import time
from app.config import AppConfig
from app.database.db import Database
from app.utils.logger import setup_logger

log = setup_logger('Discovery')


class DeviceDiscovery:
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
        self._callbacks = {}
        self._discovered = {}
        self._scanning = False

    def on(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.error(f"Discovery callback error: {e}")

    def register_device(self, device_id, name, ip, port=37021, connection_type='local'):
        self._discovered[device_id] = {
            'name': name, 'ip': ip, 'port': port,
            'type': connection_type, 'last_seen': time.time(),
        }
        self.db.add_device(device_id, name, ip, port, connection_type)
        self._emit('device_found', device_id, name, ip, port)

    def get_devices(self):
        return dict(self._discovered)

    def get_device(self, device_id):
        return self._discovered.get(device_id)

    def get_online_devices(self):
        now = time.time()
        return {
            did: d for did, d in self._discovered.items()
            if now - d.get('last_seen', 0) < 15
        }

    def update_seen(self, device_id, ip=None):
        if device_id in self._discovered:
            self._discovered[device_id]['last_seen'] = time.time()
            if ip:
                self._discovered[device_id]['ip'] = ip

    def remove_stale(self, timeout=30):
        now = time.time()
        stale = [did for did, d in self._discovered.items() if now - d['last_seen'] > timeout]
        for did in stale:
            del self._discovered[did]
            self._emit('device_lost', did)

    def get_device_count(self):
        return len(self.get_online_devices())
