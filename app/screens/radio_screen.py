"""Main Radio screen - walkie-talkie interface."""
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.utils import rgba
from app.services.connection_service import ConnectionService
from app.utils.logger import setup_logger

log = setup_logger('RadioScreen')


class RadioScreen(Screen):
    device_name = StringProperty('DemonTalk')
    channel_name = StringProperty('No Channel')
    status_text = StringProperty('OFFLINE')
    status_color = ListProperty([0.33, 0.33, 0.47, 1])
    peer_count = NumericProperty(0)
    network_type = StringProperty('LAN')
    is_transmitting = BooleanProperty(False)
    is_receiving = BooleanProperty(False)
    mic_enabled = BooleanProperty(True)
    speaker_enabled = BooleanProperty(True)
    battery_level = NumericProperty(100)
    battery_icon = StringProperty('🔋')
    signal_bars = StringProperty('▂▃▅▇')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = None
        self._update_event = None

    def on_enter(self):
        self._service = ConnectionService()
        self._service.on('state_changed', self._on_state)
        self._service.on('transmitting_started', self._on_tx_start)
        self._service.on('transmitting_stopped', self._on_tx_stop)
        self._service.on('voice_received', self._on_voice_received)
        self._service.on('audio_level', self._on_audio_level)
        self._service.on('receive_level', self._on_receive_level)
        self._service.on('device_found', self._on_device_found)
        self._service.on('peer_connected', self._on_peer_connected)
        self._service.on('peer_disconnected', self._on_peer_disconnected)
        self._service.on('channel_joined', self._on_channel_joined)
        self._service.on('emergency', self._on_emergency)
        self.device_name = self._service.config.get('device_name') or 'DemonTalk User'
        self._update_event = Clock.schedule_interval(self._update, 2.0)
        self._update_battery()
        self._update_peer_count()

    def on_leave(self):
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

    def _update(self, dt):
        self._update_peer_count()
        self._update_battery()

    def _update_peer_count(self):
        if self._service:
            self.peer_count = self._service.peer_count

    def _update_battery(self):
        try:
            from plyer import battery
            info = battery.battery_info
            self.battery_level = info.get('percentage', 100)
        except Exception:
            self.battery_level = 100
        if self.battery_level > 75:
            self.battery_icon = '🔋'
        elif self.battery_level > 25:
            self.battery_icon = '🪫'
        else:
            self.battery_icon = '⚠'

    def _on_state(self, state):
        state_map = {
            'ready': ('STANDBY', rgba('#00e676')),
            'connected': ('CONNECTED', rgba('#00e676')),
            'transmitting': ('TRANSMITTING', rgba('#ff1744')),
            'receiving': ('RECEIVING', rgba('#00b0ff')),
            'offline': ('OFFLINE', rgba('#555555')),
        }
        text, color = state_map.get(state, ('UNKNOWN', rgba('#555555')))
        self.status_text = text
        self.status_color = color

    def _on_tx_start(self):
        self.is_transmitting = True
        self.status_text = 'TRANSMITTING'
        self.status_color = rgba('#ff1744')

    def _on_tx_stop(self):
        self.is_transmitting = False
        self.status_text = 'STANDBY'
        self.status_color = rgba('#00e676')

    def _on_voice_received(self, source_id, source_name, audio_data):
        self.is_receiving = True
        Clock.schedule_once(lambda dt: self._set_receiving(False), 1.0)

    def _set_receiving(self, val):
        self.is_receiving = val

    def _on_audio_level(self, level):
        if hasattr(self.ids, 'waveform'):
            self.ids.waveform.set_level(level)

    def _on_receive_level(self, level):
        if hasattr(self.ids, 'receive_waveform'):
            self.ids.receive_waveform.set_level(level)
        if hasattr(self.ids, 'ptt'):
            self.ids.ptt.set_receive_level(level)

    def _on_device_found(self, device_id, name, ip, info):
        self._update_peer_count()

    def _on_peer_connected(self, ip, port):
        self._update_peer_count()
        self.network_type = 'TCP'

    def _on_peer_disconnected(self, peer_id):
        self._update_peer_count()

    def _on_channel_joined(self, channel_id):
        ch = self._service.db.get_channel(channel_id)
        if ch:
            self.channel_name = ch['name']

    def _on_emergency(self, source_id, source_name, message):
        self.status_text = 'EMERGENCY'
        self.status_color = rgba('#ff1744')

    def on_ptt_press(self):
        if self._service:
            self._service.start_transmitting(self._service._current_channel or '')

    def on_ptt_release(self):
        if self._service:
            self._service.stop_transmitting()

    def on_emergency(self):
        if self._service:
            self._service.send_emergency()
