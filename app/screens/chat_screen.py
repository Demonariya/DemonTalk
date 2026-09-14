"""Chat screen - text messaging."""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.metrics import dp
from kivy.utils import rgba
from kivy.clock import Clock
from datetime import datetime
from app.services.connection_service import ConnectionService
from app.utils.logger import setup_logger

log = setup_logger('ChatScreen')


class ChatScreen(Screen):
    channel_label = StringProperty('No channel')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = None

    def on_enter(self):
        self._service = ConnectionService()
        self._service.on('message_received', self._on_message)
        self._service.on('channel_joined', self._on_channel_joined)
        if self._service._current_channel:
            ch = self._service.db.get_channel(self._service._current_channel)
            if ch:
                self.channel_label = ch['name']
        self._load_history()

    def _load_history(self):
        container = self.ids.message_list
        container.clear_widgets()
        if not self._service._current_channel:
            return
        messages = self._service.db.get_messages(channel_id=self._service._current_channel, limit=50)
        for msg in reversed(messages):
            self._add_message_bubble(msg['sender_name'], msg['content'],
                                    msg['created_at'], msg['sender_id'] == self._service.net.device_id)

    def _add_message_bubble(self, sender, text, ts='', own=False):
        container = self.ids.message_list
        bubble = BoxLayout(orientation='vertical', size_hint_y=None,
                         padding=[dp(12), dp(6)], spacing=dp(2))
        bubble.height = dp(20) + max(dp(24), (len(text) // 35 + 1) * dp(18) + dp(12))

        with bubble.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            bg = rgba('#1e1e30') if own else rgba('#1a1a2e')
            Color(*bg)
            r = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(12)])
            bubble.bind(pos=lambda inst, val, r=r: setattr(r, 'pos', val))
            bubble.bind(size=lambda inst, val, r=r: setattr(r, 'size', val))

        name_color = rgba('#b44aff') if own else rgba('#4a9fff')
        header = BoxLayout(size_hint_y=None, height=dp(18))
        header.add_widget(Label(text=sender, font_size='12sp', color=name_color,
                              halign='left', text_size=(dp(280), None), bold=True))
        time_str = ''
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                time_str = dt.strftime('%H:%M')
            except (ValueError, TypeError):
                pass
        header.add_widget(Label(text=time_str, font_size='10sp', color=rgba('#555577'),
                              halign='right', text_size=(dp(60), None)))
        bubble.add_widget(header)

        bubble.add_widget(Label(text=text, font_size='14sp', color=rgba('#e8e8f0'),
                              halign='left', text_size=(dp(300), None),
                              size_hint_y=None,
                              height=max(dp(18), (len(text) // 35 + 1) * dp(18))))
        container.add_widget(bubble)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.05)

    def _scroll_to_bottom(self):
        scroll = self.ids.msg_scroll
        scroll.scroll_y = 0

    def send_message(self):
        text = self.ids.msg_input.text.strip()
        if not text or not self._service:
            return
        channel_id = self._service._current_channel or ''
        self._service.send_text(text, channel_id)
        self._add_message_bubble(self._service.device_name, text,
                                datetime.utcnow().isoformat(), own=True)
        self.ids.msg_input.text = ''

    def _on_message(self, source_id, source_name, message, channel_id):
        if channel_id == self._service._current_channel:
            Clock.schedule_once(lambda dt, s=source_name, m=message:
                              self._add_message_bubble(s, m), 0)

    def _on_channel_joined(self, channel_id):
        ch = self._service.db.get_channel(channel_id)
        if ch:
            self.channel_label = ch['name']
        self._load_history()

    def start_voice_record(self):
        pass
