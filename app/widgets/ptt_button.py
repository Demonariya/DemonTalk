"""Push-to-Talk button widget with glow effects."""
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty
from kivy.metrics import dp
from kivy.animation import Animation
from app.ui.theme import *


class PTTButton(ButtonBehavior, Widget):
    state_text = StringProperty('READY')
    is_transmitting = BooleanProperty(False)
    is_receiving = BooleanProperty(False)
    glow_color = ListProperty([0.71, 0.29, 1.0, 0.6])
    button_color = ListProperty([0.12, 0.12, 0.18, 1])
    ring_color = ListProperty([0.71, 0.29, 1.0, 0.8])
    pulse_amplitude = NumericProperty(0)
    icon_text = StringProperty('▶')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pulse_anim = None
        self._glow_anim = None
        self.bind(pos=self._update_graphics, size=self._update_graphics,
                  is_transmitting=self._on_state_change,
                  is_receiving=self._on_state_change)
        self.bind(on_press=self._on_press, on_release=self._on_release)
        self._update_graphics()

    def _update_graphics(self, *args):
        self.canvas.clear()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        base_r = min(self.width, self.height) / 2 - dp(10)
        with self.canvas:
            Color(*self.glow_color)
            Ellipse(pos=(cx - base_r - dp(15), cy - base_r - dp(15)),
                    size=(2 * (base_r + dp(15)), 2 * (base_r + dp(15))))
            Color(*self.button_color)
            Ellipse(pos=(cx - base_r, cy - base_r), size=(2 * base_r, 2 * base_r))
            Color(*self.ring_color)
            Line(ellipse=(cx - base_r - dp(3), cy - base_r - dp(3),
                          2 * (base_r + dp(3)), 2 * (base_r + dp(3))),
                 width=dp(2.5))

    def _on_state_change(self, *args):
        if self.is_transmitting:
            self.state_text = 'TRANSMITTING'
            self.glow_color = [1.0, 0.09, 0.27, 0.8]
            self.ring_color = [1.0, 0.09, 0.27, 1.0]
            self.button_color = [0.3, 0.05, 0.08, 1]
            self.icon_text = '⏹'
            self._start_pulse()
        elif self.is_receiving:
            self.state_text = 'RECEIVING'
            self.glow_color = [0.0, 0.69, 1.0, 0.7]
            self.ring_color = [0.0, 0.69, 1.0, 1.0]
            self.button_color = [0.02, 0.12, 0.2, 1]
            self.icon_text = '▶'
            self._start_pulse()
        else:
            self.state_text = 'READY'
            self.glow_color = [0.71, 0.29, 1.0, 0.6]
            self.ring_color = [0.71, 0.29, 1.0, 0.8]
            self.button_color = [0.12, 0.12, 0.18, 1]
            self.icon_text = '▶'
            self._stop_pulse()
        self._update_graphics()

    def _start_pulse(self):
        if self._pulse_anim:
            self._pulse_anim.cancel(self)
        self._pulse_anim = Animation(glow_color=list(self.glow_color[:3] + [0.3]),
                                     duration=0.8, t='in_out_sine')
        self._pulse_anim += Animation(glow_color=list(self.glow_color[:3] + [0.8]),
                                      duration=0.8, t='in_out_sine')
        self._pulse_anim.loop = True
        self._pulse_anim.start(self)

    def _stop_pulse(self):
        if self._pulse_anim:
            self._pulse_anim.cancel(self)
            self._pulse_anim = None

    def _on_press(self, *args):
        if not self.is_receiving:
            anim = Animation(scale=0.92, duration=0.1, t='out_cubic')
            anim.start(self)

    def _on_release(self, *args):
        anim = Animation(scale=1.0, duration=0.15, t='out_back')
        anim.start(self)

    def set_receive_level(self, level: float):
        self.pulse_amplitude = level
        r, g, b = 0.0, 0.69, 1.0
        self.glow_color = [r, g, b, 0.3 + level * 0.7]
        self._update_graphics()
