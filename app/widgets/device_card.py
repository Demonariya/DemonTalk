"""Device card widget for peer display."""
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle


class DeviceCard(BoxLayout):
    device_name = StringProperty('Unknown')
    device_ip = StringProperty('')
    device_status = StringProperty('offline')
    is_online = BooleanProperty(False)
    is_favorite = BooleanProperty(False)
    avatar_color = ListProperty([0.71, 0.29, 1.0, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = dp(12)
        self.spacing = dp(12)
        self.size_hint_y = None
        self.height = dp(72)
        self.bind(is_online=self._update_status_color)

    def _update_status_color(self, *args):
        if self.is_online:
            self.avatar_color = [0.0, 0.9, 0.46, 1]
        else:
            self.avatar_color = [0.33, 0.33, 0.47, 1]

    def set_data(self, name, ip, online=False, favorite=False):
        self.device_name = name
        self.device_ip = ip
        self.is_online = online
        self.is_favorite = favorite
