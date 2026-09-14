"""Animation helpers for DemonTalk."""
from kivy.animation import Animation
from kivy.metrics import dp


def glow_pulse(widget, color=None, duration=1.5):
    if color is None:
        color = (0.71, 0.29, 1.0, 0.6)
    anim = Animation(opacity=0.4, duration=duration/2, t='in_out_sine')
    anim += Animation(opacity=1.0, duration=duration/2, t='in_out_sine')
    anim.loop = True
    anim.start(widget)
    return anim


def fade_in(widget, duration=0.3, **kwargs):
    widget.opacity = 0
    anim = Animation(opacity=1, duration=duration, t='out_cubic', **kwargs)
    anim.start(widget)
    return anim


def slide_up(widget, duration=0.3, distance=dp(50)):
    original_y = widget.y
    widget.y -= distance
    widget.opacity = 0
    anim = Animation(y=original_y, opacity=1, duration=duration, t='out_cubic')
    anim.start(widget)
    return anim


def scale_in(widget, duration=0.3):
    widget.scale = 0.5
    widget.opacity = 0
    anim = Animation(scale=1, opacity=1, duration=duration, t='out_back')
    anim.start(widget)
    return anim


def pulse(widget, scale=1.05, duration=0.3):
    anim = Animation(scale=scale, duration=duration/2, t='in_out_sine')
    anim += Animation(scale=1.0, duration=duration/2, t='in_out_sine')
    anim.start(widget)
    return anim


def color_transition(widget, target_color, duration=0.3):
    anim = Animation(rgba=target_color, duration=duration, t='in_out_cubic')
    anim.start(widget)
    return anim


def breathe(widget, min_opacity=0.7, max_opacity=1.0, duration=2.0):
    anim = Animation(opacity=min_opacity, duration=duration/2, t='in_out_sine')
    anim += Animation(opacity=max_opacity, duration=duration/2, t='in_out_sine')
    anim.loop = True
    anim.start(widget)
    return anim


def ripple_effect(widget, center_x, center_y, color=None):
    from kivy.uix.widget import Widget
    from kivy.graphics import Color, Ellipse
    if color is None:
        color = (0.71, 0.29, 1.0, 0.3)
    ripple = Widget()
    with ripple.canvas:
        c = Color(*color)
        d = Ellipse(pos=(center_x - 5, center_y - 5), size=(10, 10))
    widget.add_widget(ripple)
    anim = Animation(size=(200, 200), pos=(center_x - 100, center_y - 100),
                    opacity=0, duration=0.6, t='out_cubic')
    anim.bind(on_complete=lambda *a: widget.remove_widget(ripple))
    anim.start(ripple)
