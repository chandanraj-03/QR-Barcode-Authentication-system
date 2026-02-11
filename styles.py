from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

COLORS = {
    'bg_dark': '#0a0a1a',
    'bg_card': '#1a1a2e',
    'bg_hover': '#252545',
    'accent': '#6c5ce7',
    'accent_light': '#a29bfe',
    'success': '#00b894',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'text': '#ffffff',
    'text_dim': '#a0a0b0',
    'border': '#3d3d5c',
    'purple': '#9b59b6',
}

GLOBAL_STYLESHEET = f"""
QMainWindow, QWidget#centralWidget {{
    background-color: {COLORS['bg_dark']};
}}
QScrollArea {{
    background-color: {COLORS['bg_card']};
    border: none;
}}
QScrollBar:vertical {{
    background: {COLORS['bg_dark']};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    height: 0;
}}
"""

def _darken(hex_color, amount=30):
    rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    d = tuple(max(0, c - amount) for c in rgb)
    return f'#{d[0]:02x}{d[1]:02x}{d[2]:02x}'

def _lighten(hex_color, amount=20):
    rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    l = tuple(min(255, c + amount) for c in rgb)
    return f'#{l[0]:02x}{l[1]:02x}{l[2]:02x}'

def make_button(text, color, font_size=11, padx=20, pady=10):
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: #ffffff;
            font-family: 'Segoe UI';
            font-size: {font_size}px;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: {pady}px {padx}px;
        }}
        QPushButton:hover {{
            background-color: {_lighten(color)};
        }}
        QPushButton:pressed {{
            background-color: {_darken(color)};
        }}
        QPushButton:disabled {{
            background-color: {COLORS['border']};
            color: {COLORS['text_dim']};
        }}
    """)
    return btn
