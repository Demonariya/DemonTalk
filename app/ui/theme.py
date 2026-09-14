"""DemonTalk theme - cyberpunk dark glassmorphism."""
from kivy.utils import rgba

# Core palette
BG_DARK = rgba('#0a0a0f')
BG_CARD = rgba('#12121a')
BG_ELEVATED = rgba('#1a1a2e')
BG_GLASS = rgba('#1e1e3080')

# Neon accents
NEON_PURPLE = rgba('#b44aff')
NEON_BLUE = rgba('#4a9fff')
NEON_CYAN = rgba('#00e5ff')
NEON_PINK = rgba('#ff4a8d')

# Status colors
STATUS_ONLINE = rgba('#00e676')
STATUS_TRANSMITTING = rgba('#ff1744')
STATUS_RECEIVING = rgba('#00b0ff')
STATUS_WARNING = rgba('#ff9100')
STATUS_ERROR = rgba('#ff1744')
STATUS_OFFLINE = rgba('#555555')

# Text
TEXT_PRIMARY = rgba('#e8e8f0')
TEXT_SECONDARY = rgba('#8888aa')
TEXT_MUTED = rgba('#555577')

# Borders
BORDER_DIM = rgba('#2a2a3e')
BORDER_GLOW = rgba('#b44aff40')

# Gradients (as tuples for KV)
GRADIENT_PURPLE = [(0.71, 0.29, 1.0, 1), (0.29, 0.62, 1.0, 1)]
GRADIENT_DARK = [(0.04, 0.04, 0.06, 1), (0.07, 0.07, 0.12, 1)]

# Shadows
SHADOW_PURPLE = (0.71, 0.29, 1.0, 0.3)
SHADOW_BLUE = (0.29, 0.62, 1.0, 0.3)

# Dimensions
PTT_BUTTON_SIZE = 200
CORNER_RADIUS = 16
CARD_ELEVATION = 4
BOTTOM_NAV_HEIGHT = 64

# Animation
ANIM_SPEED = 0.3
ANIM_FAST = 0.15
ANIM_SLOW = 0.5

# Font sizes
FONT_H1 = '28sp'
FONT_H2 = '22sp'
FONT_H3 = '18sp'
FONT_BODY = '15sp'
FONT_SMALL = '13sp'
FONT_TINY = '11sp'

THEME_KV = """
#:import dp kivy.metrics.dp
#:import rgba kivy.utils rgba

<DemonTalkTheme@Widget>:
    canvas.before:
        Color:
            rgba: rgba('#0a0a0f')
        Rectangle:
            pos: self.pos
            size: self.size
"""
