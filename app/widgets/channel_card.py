"""Channel card widget."""
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.metrics import dp


class ChannelCard(BoxLayout):
    channel_name = StringProperty('Channel')
    channel_id = StringProperty('')
    member_count = NumericProperty(0)
    is_locked = BooleanProperty(False)
    is_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = dp(12)
        self.spacing = dp(12)
        self.size_hint_y = None
        self.height = dp(68)

    def set_data(self, name, cid, members=0, locked=False, active=False):
        self.channel_name = name
        self.channel_id = cid
        self.member_count = members
        self.is_locked = locked
        self.is_active = active
