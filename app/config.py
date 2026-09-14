"""Application configuration."""
import os
import json
from pathlib import Path

APP_NAME = 'DemonTalk'
APP_VERSION = '1.0.0'

BASE_DIR = Path(os.environ.get('ANDROID_PRIVATE', os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = BASE_DIR / 'data'
ASSETS_DIR = Path(__file__).parent / 'assets'

DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / 'demontalk.db'

DISCOVERY_PORT = 37020
VOICE_PORT = 37021
CHAT_PORT = 37022
TCP_SERVER_PORT = 37023
BROADCAST_INTERVAL = 3.0
DISCOVERY_MULTICAST = '239.255.0.1'
DISCOVERY_MAGIC = b'DMTK'

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SIZE = 960
AUDIO_BITRATE = 16000

DEFAULT_SETTINGS = {
    'device_name': 'DemonTalk User',
    'device_id': '',
    'audio': {
        'mic_sensitivity': 0.8,
        'speaker_volume': 0.8,
        'noise_suppression': True,
        'echo_cancellation': True,
        'quality': 'balanced',
        'input_device': '',
        'output_device': '',
    },
    'network': {
        'auto_discovery': True,
        'protocol': 'udp',
        'port': VOICE_PORT,
        'broadcast_interval': BROADCAST_INTERVAL,
        'connection_timeout': 10.0,
        'reconnect_delay': 3.0,
    },
    'appearance': {
        'theme': 'dark',
        'amoled_mode': False,
        'neon_intensity': 1.0,
        'animation_level': 'normal',
        'compact_mode': False,
        'large_controls': False,
    },
    'notifications': {
        'connection_sounds': True,
        'transmission_sound': True,
        'receiving_sound': True,
        'message_sound': True,
        'vibration': True,
        'haptic_feedback': True,
    },
    'mode': 'half_duplex',
}

QUALITY_PRESETS = {
    'low': {'sample_rate': 8000, 'channels': 1, 'chunk': 480, 'bitrate': 8000},
    'balanced': {'sample_rate': 16000, 'channels': 1, 'chunk': 960, 'bitrate': 16000},
    'high': {'sample_rate': 44100, 'channels': 1, 'chunk': 4096, 'bitrate': 44100},
}


class AppConfig:
    _instance = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._data is None:
            self._data = dict(DEFAULT_SETTINGS)
            self._load()

    @property
    def settings_path(self):
        return DATA_DIR / 'settings.json'

    def _load(self):
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r') as f:
                    saved = json.load(f)
                self._deep_merge(self._data, saved)
            except (json.JSONDecodeError, IOError):
                pass

    def _deep_merge(self, base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def save(self):
        with open(self.settings_path, 'w') as f:
            json.dump(self._data, f, indent=2)

    def get(self, *keys, default=None):
        d = self._data
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                return default
        return d

    def set(self, *keys_and_value):
        *keys, value = keys_and_value
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    def __getitem__(self, keys):
        if not isinstance(keys, tuple):
            keys = (keys,)
        return self.get(*keys)

    def __setitem__(self, keys, value):
        if not isinstance(keys, tuple):
            keys = (keys,)
        self.set(*keys, value)
