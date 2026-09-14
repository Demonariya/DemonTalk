"""Chat message bubble widget."""
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty
from kivy.metrics import dp


class MessageBubble(BoxLayout):
    sender_name = StringProperty('')
    message_text = StringProperty('')
    timestamp = StringProperty('')
    is_own = BooleanProperty(False)
    message_type = StringProperty('text')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = [dp(12), dp(6), dp(12), dp(6)]
        self.spacing = dp(2)

    def set_data(self, sender, text, ts='', own=False, msg_type='text'):
        self.sender_name = sender
        self.message_text = text
        self.timestamp = ts
        self.is_own = own
        self.message_type = msg_type
        self.height = dp(20) + max(dp(20), len(text) // 30 * dp(18) + dp(24))
