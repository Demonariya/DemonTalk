"""Waveform visualization widget."""
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty, NumericProperty
from kivy.metrics import dp
from kivy.clock import Clock
import math


class WaveformWidget(Widget):
    bar_color = ListProperty([0.71, 0.29, 1.0, 1])
    inactive_color = ListProperty([0.2, 0.2, 0.3, 0.5])
    bar_count = NumericProperty(32)
    amplitude = NumericProperty(0)
    _levels = ListProperty([0.0] * 32)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, _levels=self._draw)
        Clock.schedule_interval(self._decay, 1/30)

    def set_level(self, level: float):
        n = int(self.bar_count)
        new_levels = list(self._levels)
        for i in range(n):
            target = level * (0.5 + 0.5 * math.sin(i * math.pi / n))
            new_levels[i] = max(target, new_levels[i] * 0.7)
        self._levels = new_levels

    def _decay(self, dt):
        changed = False
        new = list(self._levels)
        for i in range(len(new)):
            if new[i] > 0.01:
                new[i] *= 0.88
                changed = True
            elif new[i] > 0:
                new[i] = 0
                changed = True
        if changed:
            self._levels = new

    def _draw(self, *args):
        self.canvas.clear()
        n = int(self.bar_count)
        if n == 0 or self.width <= 0 or self.height <= 0:
            return
        bar_w = max(dp(2), (self.width - (n - 1) * dp(1)) / n)
        gap = dp(1)
        max_h = self.height * 0.9
        cx = self.x + self.width / 2

        with self.canvas:
            for i in range(n):
                level = self._levels[i] if i < len(self._levels) else 0
                h = max(dp(3), level * max_h)
                bx = self.x + i * (bar_w + gap)
                by = self.y + (self.height - h) / 2
                if level > 0.3:
                    Color(*self.bar_color[:3], min(1.0, 0.5 + level * 0.5))
                else:
                    Color(*self.inactive_color)
                RoundedRectangle(pos=(bx, by), size=(bar_w, h),
                                radius=[bar_w / 2])
