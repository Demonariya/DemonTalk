"""Channels screen."""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.utils import rgba
from app.services.connection_service import ConnectionService
from app.utils.logger import setup_logger

log = setup_logger('ChannelsScreen')


class ChannelsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = None

    def on_enter(self):
        self._service = ConnectionService()
        self._load_channels()

    def _load_channels(self):
        container = self.ids.channel_list
        container.clear_widgets()
        channels = self._service.db.get_all_channels()
        self.ids.empty_label.opacity = 1 if not channels else 0
        for ch in channels:
            card = self._create_channel_card(ch)
            container.add_widget(card)

    def _create_channel_card(self, ch):
        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(68),
                       padding=dp(12), spacing=dp(12))
        with box.canvas.before:
            color = rgba('#1e1e30') if ch.get('id') != self._service.net.current_channel else rgba('#2a1a3e')
            from kivy.graphics import Color, RoundedRectangle
            Color(*color)
            rounded = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(14)])
            box.bind(pos=lambda inst, val, r=rounded: setattr(r, 'pos', val))
            box.bind(size=lambda inst, val, r=rounded: setattr(r, 'size', val))

        info = BoxLayout(orientation='vertical', spacing=dp(2))
        info.add_widget(Label(text=ch['name'], font_size='16sp', color=rgba('#e8e8f0'),
                            halign='left', text_size=(dp(200), None), bold=True,
                            size_hint_y=None, height=dp(24)))
        members = f"{ch.get('member_count', 0)} members"
        if ch.get('is_locked'):
            members += '  🔒'
        info.add_widget(Label(text=members, font_size='12sp', color=rgba('#8888aa'),
                            halign='left', text_size=(dp(200), None),
                            size_hint_y=None, height=dp(18)))
        box.add_widget(info)

        btn = Button(text='JOIN', size_hint_x=None, width=dp(72),
                    font_size='12sp', bold=True, color=rgba('#b44aff'),
                    background_color=rgba('#b44aff20'), background_normal='')
        btn.bind(on_release=lambda inst, cid=ch['id']: self._join_channel(cid))
        with btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*rgba('#b44aff20'))
            r = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])
            btn.bind(pos=lambda inst, val, r=r: setattr(r, 'pos', val))
            btn.bind(size=lambda inst, val, r=r: setattr(r, 'size', val))
        box.add_widget(btn)
        return box

    def _join_channel(self, channel_id):
        self._service.join_channel(channel_id)
        self.manager.current = 'radio'

    def show_create_dialog(self):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12),
                          size_hint_y=None, height=dp(180))

        name_input = TextInput(hint_text='Channel name', multiline=False,
                             size_hint_y=None, height=dp(44),
                             background_color=rgba('#1a1a2e'),
                             foreground_color=rgba('#e8e8f0'),
                             hint_text_color=rgba('#555577'),
                             cursor_color=rgba('#b44aff'),
                             font_size='15sp', padding=[dp(12), dp(10)])

        pw_input = TextInput(hint_text='Password (optional)', multiline=False,
                           password=True, size_hint_y=None, height=dp(44),
                           background_color=rgba('#1a1a2e'),
                           foreground_color=rgba('#e8e8f0'),
                           hint_text_color=rgba('#555577'),
                           cursor_color=rgba('#b44aff'),
                           font_size='15sp', padding=[dp(12), dp(10)])

        content.add_widget(name_input)
        content.add_widget(pw_input)

        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = Button(text='Cancel', font_size='14sp', color=rgba('#8888aa'),
                       background_color=rgba('#1a1a2e'), background_normal='')
        create = Button(text='Create', font_size='14sp', color=rgba('#ffffff'),
                       background_color=rgba('#b44aff'), background_normal='')
        btn_box.add_widget(cancel)
        btn_box.add_widget(create)
        content.add_widget(btn_box)

        popup = Popup(title='Create Channel', content=content,
                     size_hint=(0.85, None), height=dp(220),
                     background_color=rgba('#12121a'),
                     separator_color=rgba('#b44aff'),
                     title_color=rgba('#e8e8f0'))

        def do_create(*args):
            name = name_input.text.strip()
            if name:
                pw = pw_input.text.strip()
                self._service.create_channel(name, pw)
                self._load_channels()
                popup.dismiss()

        cancel.bind(on_release=popup.dismiss)
        create.bind(on_release=do_create)
        popup.open()
