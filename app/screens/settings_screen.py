"""Settings screen."""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.utils import rgba
from app.config import AppConfig
from app.utils.logger import setup_logger

log = setup_logger('SettingsScreen')


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._config = None

    def on_enter(self):
        self._config = AppConfig()
        self._build_settings()

    def _build_settings(self):
        container = self.ids.settings_list
        container.clear_widgets()

        sections = [
            ('Device', [
                ('name_input', 'Device Name', self._config.get('device_name'), 'text'),
            ]),
            ('Audio', [
                ('mic_sensitivity', 'Mic Sensitivity', self._config.get('audio', 'mic_sensitivity'), 'slider'),
                ('speaker_volume', 'Speaker Volume', self._config.get('audio', 'speaker_volume'), 'slider'),
                ('noise_suppression', 'Noise Suppression', self._config.get('audio', 'noise_suppression'), 'toggle'),
                ('echo_cancellation', 'Echo Cancellation', self._config.get('audio', 'echo_cancellation'), 'toggle'),
            ]),
            ('Network', [
                ('auto_discovery', 'Auto Discovery', self._config.get('network', 'auto_discovery'), 'toggle'),
                ('broadcast_interval', 'Broadcast Interval', self._config.get('network', 'broadcast_interval'), 'slider'),
            ]),
            ('Appearance', [
                ('amoled_mode', 'AMOLED Mode', self._config.get('appearance', 'amoled_mode'), 'toggle'),
                ('neon_intensity', 'Neon Intensity', self._config.get('appearance', 'neon_intensity'), 'slider'),
            ]),
            ('Notifications', [
                ('connection_sounds', 'Connection Sounds', self._config.get('notifications', 'connection_sounds'), 'toggle'),
                ('transmission_sound', 'TX Sound', self._config.get('notifications', 'transmission_sound'), 'toggle'),
                ('receiving_sound', 'RX Sound', self._config.get('notifications', 'receiving_sound'), 'toggle'),
                ('message_sound', 'Message Sound', self._config.get('notifications', 'message_sound'), 'toggle'),
                ('vibration', 'Vibration', self._config.get('notifications', 'vibration'), 'toggle'),
                ('haptic_feedback', 'Haptic Feedback', self._config.get('notifications', 'haptic_feedback'), 'toggle'),
            ]),
        ]

        for section_name, items in sections:
            section = BoxLayout(orientation='vertical', size_hint_y=None,
                              spacing=dp(4), padding=[0, dp(8), 0, dp(4)])
            section.add_widget(Label(text=section_name.upper(), font_size='13sp',
                                   color=rgba('#b44aff'), bold=True,
                                   size_hint_y=None, height=dp(28),
                                   text_size=(dp(300), None), halign='left'))

            for key, label, value, widget_type in items:
                row = self._create_setting_row(label, value, widget_type, key, section_name)
                section.add_widget(row)
            container.add_widget(section)

    def _create_setting_row(self, label, value, widget_type, key, section):
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8),
                       padding=[dp(4), dp(4)])

        with row.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*rgba('#12121a'))
            r = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])
            row.bind(pos=lambda inst, val, r=r: setattr(r, 'pos', val))
            row.bind(size=lambda inst, val, r=r: setattr(r, 'size', val))

        row.add_widget(Label(text=label, font_size='14sp', color=rgba('#e8e8f0'),
                           size_hint_x=0.5, text_size=(dp(180), None), halign='left'))

        if widget_type == 'text':
            inp = TextInput(text=str(value or ''), font_size='14sp', multiline=False,
                          size_hint_x=0.5, background_color=rgba('#1a1a2e'),
                          foreground_color=rgba('#e8e8f0'), cursor_color=rgba('#b44aff'),
                          padding=[dp(8), dp(8)])
            section_key = section.lower()
            inp.bind(on_text_validate=lambda inst, sk=section_key, ik=key:
                    self._config.set(sk, ik, inst.text.strip()))
            row.add_widget(inp)

        elif widget_type == 'toggle':
            sw = Switch(active=bool(value), size_hint_x=0.3,
                       active_color=rgba('#b44aff'))
            section_key = section.lower()
            sw.bind(active=lambda inst, sk=section_key, ik=key:
                   self._config.set(sk, ik, inst.active))
            row.add_widget(sw)

        elif widget_type == 'slider':
            val = float(value) if value else 0.5
            sld = Slider(min=0, max=1, value=val, size_hint_x=0.4,
                        cursor_color=rgba('#b44aff'),
                        track_color=rgba('#2a2a3e'))
            lbl = Label(text=f'{val:.0%}', font_size='12sp', color=rgba('#8888aa'),
                       size_hint_x=0.1)
            sld.bind(value=lambda inst, v, l=lbl: setattr(l, 'text', f'{v:.0%}'))
            section_key = section.lower()
            sld.bind(value=lambda inst, v, sk=section_key, ik=key:
                    self._config.set(sk, ik, round(v, 2)))
            row.add_widget(sld)
            row.add_widget(lbl)

        return row
