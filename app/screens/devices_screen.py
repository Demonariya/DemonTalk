"""Devices screen - peer management."""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty
from kivy.metrics import dp
from kivy.utils import rgba
from app.services.connection_service import ConnectionService
from app.utils.logger import setup_logger

log = setup_logger('DevicesScreen')


class DevicesScreen(Screen):
    scan_status = StringProperty('Ready to scan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = None

    def on_enter(self):
        self._service = ConnectionService()
        self._service.on('device_found', self._on_device_found)
        self._load_devices()

    def _load_devices(self):
        container = self.ids.device_list
        container.clear_widgets()
        devices = self._service.db.get_all_devices()
        self.ids.empty_label.opacity = 1 if not devices else 0
        for dev in devices:
            card = self._create_device_card(dev)
            container.add_widget(card)

    def _create_device_card(self, dev):
        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(76),
                       padding=dp(12), spacing=dp(12))

        with box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*rgba('#1e1e30'))
            r = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(14)])
            box.bind(pos=lambda inst, val, r=r: setattr(r, 'pos', val))
            box.bind(size=lambda inst, val, r=r: setattr(r, 'size', val))

        # Avatar circle
        avatar = BoxLayout(size_hint_x=None, width=dp(48))
        with avatar.canvas:
            from kivy.graphics import Color, Ellipse
            online = dev.get('last_seen', '') and self._is_recent(dev['last_seen'])
            ac = rgba('#00e676') if online else rgba('#555577')
            Color(*ac)
            Ellipse(pos=avatar.pos, size=(dp(48), dp(48)))
        initial = (dev.get('name', '?') or '?')[0].upper()
        avatar.add_widget(Label(text=initial, font_size='20sp', color=rgba('#ffffff'), bold=True))
        box.add_widget(avatar)

        # Info
        info = BoxLayout(orientation='vertical', spacing=dp(2))
        info.add_widget(Label(text=dev['name'], font_size='16sp', color=rgba('#e8e8f0'),
                            halign='left', text_size=(dp(180), None), bold=True,
                            size_hint_y=None, height=dp(22)))
        status = 'Online' if self._is_recent(dev.get('last_seen', '')) else 'Offline'
        status_color = rgba('#00e676') if status == 'Online' else rgba('#555577')
        info.add_widget(Label(text=f"{dev.get('ip_address', '')}  •  {status}",
                            font_size='12sp', color=status_color,
                            halign='left', text_size=(dp(200), None),
                            size_hint_y=None, height=dp(18)))
        box.add_widget(info)

        # Connect button
        online = self._is_recent(dev.get('last_seen', ''))
        if online:
            btn = Button(text='CONNECT', size_hint_x=None, width=dp(80),
                        font_size='11sp', bold=True, color=rgba('#00e676'),
                        background_color=rgba('#00e67620'), background_normal='')
            btn.bind(on_release=lambda inst, ip=dev.get('ip_address', ''): self._connect(ip))
            with btn.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(*rgba('#00e67620'))
                rb = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])
                btn.bind(pos=lambda inst, val, r=rb: setattr(r, 'pos', val))
                btn.bind(size=lambda inst, val, r=rb: setattr(r, 'size', val))
            box.add_widget(btn)
        else:
            box.add_widget(Label(size_hint_x=None, width=dp(80)))

        return box

    def _is_recent(self, ts_str):
        if not ts_str:
            return False
        try:
            from datetime import datetime, timedelta
            ts = datetime.fromisoformat(ts_str)
            return (datetime.utcnow() - ts) < timedelta(seconds=15)
        except (ValueError, TypeError):
            return False

    def scan_devices(self):
        self.scan_status = 'Scanning for devices...'
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._finish_scan(), 5.0)

    def _finish_scan(self):
        self.scan_status = f'Found {self._service.peer_count} device(s)'
        self._load_devices()

    def _on_device_found(self, device_id, name, ip, info):
        self.scan_status = f'Found: {name}'
        self._load_devices()

    def _connect(self, ip):
        if self._service.connect_to_device(ip):
            self.scan_status = f'Connected to {ip}'
