"""DemonTalk - Offline Walkie-Talkie Application

Entry point. Run with: python main.py
Build for Android with: buildozer android debug
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('KIVY_LOG_LEVEL', 'warning')

from kivy.config import Config
Config.set('kivy', 'log_level', 'warning')
Config.set('kivy', 'window_icon', '')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'width', '390')
Config.set('graphics', 'height', '844')
Config.set('graphics', 'minimum_width', '320')
Config.set('graphics', 'minimum_height', '568')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import rgba, platform

if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.RECORD_AUDIO,
        Permission.ACCESS_WIFI_STATE,
        Permission.CHANGE_WIFI_STATE,
        Permission.ACCESS_NETWORK_STATE,
        Permission.ACCESS_FINE_LOCATION,
        Permission.WAKE_LOCK,
        Permission.FOREGROUND_SERVICE,
        Permission.POST_NOTIFICATIONS,
    ])

from app.config import AppConfig, DATA_DIR
from app.database.db import Database
from app.services.connection_service import ConnectionService
from app.utils.logger import setup_logger

log = setup_logger('Main')

from kivy.lang import Builder

KV_FILES = [
    'app/screens/radio_screen.kv',
    'app/screens/channels_screen.kv',
    'app/screens/chat_screen.kv',
    'app/screens/devices_screen.kv',
    'app/screens/settings_screen.kv',
]

for kv_path in KV_FILES:
    full = os.path.join(os.path.dirname(__file__), kv_path)
    if os.path.exists(full):
        Builder.load_file(full)

from app.screens.radio_screen import RadioScreen
from app.screens.channels_screen import ChannelsScreen
from app.screens.chat_screen import ChatScreen
from app.screens.devices_screen import DevicesScreen
from app.screens.settings_screen import SettingsScreen


class DemonTalkNavButton:
    pass


class DemonTalkApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'DemonTalk'
        self.config = AppConfig()
        self.db = Database()
        self.service = None

    def build(self):
        Window.clearcolor = rgba('#0a0a0f')

        root = Builder.load_string('''
BoxLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: rgba('#0a0a0f')
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        id: screen_container
        size_hint_y: 1

    BoxLayout:
        id: nav_bar
        size_hint_y: None
        height: dp(64)
        padding: [dp(4), dp(4)]
        spacing: dp(2)
        canvas.before:
            Color:
                rgba: rgba('#0e0e18')
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: rgba('#2a2a3e')
            Rectangle:
                pos: self.x, self.y + self.height - dp(1)
                size: self.width, dp(1)
''')

        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(RadioScreen(name='radio'))
        sm.add_widget(ChannelsScreen(name='channels'))
        sm.add_widget(ChatScreen(name='chat'))
        sm.add_widget(DevicesScreen(name='devices'))
        sm.add_widget(SettingsScreen(name='settings'))
        root.ids.screen_container.add_widget(sm)

        nav_items = [
            ('📡', 'Radio', 'radio'),
            ('📢', 'Channels', 'channels'),
            ('💬', 'Chat', 'chat'),
            ('📱', 'Devices', 'devices'),
            ('⚙', 'Settings', 'settings'),
        ]

        nav_bar = root.ids.nav_bar
        for icon, label, screen_name in nav_items:
            btn = Builder.load_string(f'''
BoxLayout:
    orientation: 'vertical'
    spacing: dp(2)
    padding: [dp(4), dp(4)]
    canvas.before:
        Color:
            rgba: rgba('#b44aff30') if self.active else rgba('#00000000')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

    Label:
        text: '{icon}'
        font_size: '20sp'

    Label:
        text: '{label}'
        font_size: '10sp'
        color: rgba('#b44aff') if self.active else rgba('#555577')
''')
            btn.active = (screen_name == 'radio')
            btn.screen_name = screen_name
            btn.bind(on_touch_down=lambda inst, touch, sn=screen_name, b=btn:
                     self._nav_touch(inst, touch, sn, root) if inst.collide_point(*touch.pos) else False)
            nav_bar.add_widget(btn)

        sm.current = 'radio'
        self._nav_buttons = nav_bar.children

        self.service = ConnectionService()
        self.service.start()

        log.info("DemonTalk started")
        return root

    def _nav_touch(self, inst, touch, screen_name, root):
        if not inst.collide_point(*touch.pos):
            return False
        sm = root.ids.screen_container.children[0]
        sm.current = screen_name
        for btn in root.ids.nav_bar.children:
            btn.active = (btn.screen_name == screen_name)
        return True

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        if self.service:
            self.service.stop()
        self.db.close()
        log.info("DemonTalk stopped")


if __name__ == '__main__':
    DemonTalkApp().run()
