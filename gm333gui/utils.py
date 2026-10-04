#!/usr/bin/env python3
"""
Constants, mode metadata, palettes, and utility functions for GM333 GUI.
"""

HID_DEVICE_LINK = "/dev/input/by-id/usb-INSTANT_USB_GAMING_MOUSE-if01-hidraw"
HIDIOCSFEATURE_8 = 0xc0084806

VENDOR_ID = "30fa"
PRODUCT_ID = "1440"

# 16 Hardware Lighting Modes: id -> (name, title, description, category, supports_color)
MODES_INFO = [
    {
        "key": "neon",
        "id": 7,
        "name": "Neon Wave",
        "desc": "Smooth multi-color vibrant rainbow wave flowing across mouse",
        "icon": "weather-clear-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "breathing",
        "id": 2,
        "name": "Cycle Breathing",
        "desc": "Smoothly pulses and transitions through all RGB spectrum colors",
        "icon": "weather-clouds-night-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "static",
        "id": 3,
        "name": "Static Solid",
        "desc": "Solid steady glow with your custom selected color",
        "icon": "starred-symbolic",
        "supports_color": True,
        "supports_speed": False,
        "supports_brightness": True,
    },
    {
        "key": "wave",
        "id": 4,
        "name": "Flowing Water",
        "desc": "Continuous directional wave streaming through the LED channels",
        "icon": "emblem-shared-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "mono-wave",
        "id": 5,
        "name": "Mono Water",
        "desc": "Single-color directional flowing wave pulse",
        "icon": "media-playlist-shuffle-symbolic",
        "supports_color": True,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "comet",
        "id": 6,
        "name": "Comet Streak",
        "desc": "High-speed light trail streaking across the chassis",
        "icon": "system-run-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "ambilight",
        "id": 8,
        "name": "Ambilight",
        "desc": "Dynamic ambient glow subtly changing hues",
        "icon": "display-brightness-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "flicker",
        "id": 9,
        "name": "Rhythmic Flicker",
        "desc": "Dynamic rhythmic flickering strobe effect",
        "icon": "camera-flash-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "startrek",
        "id": 10,
        "name": "Star Trek",
        "desc": "Moving warp stars pulsating across opposite zones",
        "icon": "applications-science-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "ripple",
        "id": 11,
        "name": "Water Ripple",
        "desc": "Expansive ripple radiating like a water droplet",
        "icon": "audio-speakers-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "single-breath",
        "id": 15,
        "name": "Single Breath",
        "desc": "Pulsing breathing effect with a custom single color",
        "icon": "weather-overcast-symbolic",
        "supports_color": True,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "cycle-color",
        "id": 16,
        "name": "Color Stepper",
        "desc": "Step-switches between individual rainbow colors",
        "icon": "view-refresh-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "dpi-breath",
        "id": 1,
        "name": "DPI Breathing",
        "desc": "Breathes according to current hardware DPI preset level",
        "icon": "input-mouse-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "reactive",
        "id": 13,
        "name": "Click Response",
        "desc": "Illuminates dynamically in response to mouse clicks",
        "icon": "input-touchpad-symbolic",
        "supports_color": False,
        "supports_speed": True,
        "supports_brightness": True,
    },
    {
        "key": "music",
        "id": 12,
        "name": "Music Sync",
        "desc": "Audio-reactive rhythm sync controlled in Music Sync tab",
        "icon": "audio-x-generic-symbolic",
        "supports_color": True,
        "supports_speed": False,
        "supports_brightness": False,
    },
    {
        "key": "off",
        "id": 14,
        "name": "Turn LEDs Off",
        "desc": "Completely turn off all mouse lighting for stealth mode",
        "icon": "system-shutdown-symbolic",
        "supports_color": False,
        "supports_speed": False,
        "supports_brightness": False,
    },
]

# Quick Color Presets (Name -> (4-bit R, G, B: 0..15, Hex for UI))
PRESET_COLORS = [
    {"name": "Cyan Neon",    "rgb": (0, 15, 15), "hex": "#00ffff"},
    {"name": "Hot Magenta",  "rgb": (15, 0, 15), "hex": "#ff00ff"},
    {"name": "Cyber Purple", "rgb": (10, 0, 15), "hex": "#aa00ff"},
    {"name": "Electric Blue","rgb": (0, 0, 15),  "hex": "#0055ff"},
    {"name": "Emerald Green","rgb": (0, 15, 0),  "hex": "#00ff44"},
    {"name": "Sun Yellow",   "rgb": (15, 15, 0), "hex": "#ffee00"},
    {"name": "Vivid Orange", "rgb": (15, 5, 0),  "hex": "#ff5500"},
    {"name": "Crimson Red",  "rgb": (15, 0, 0),  "hex": "#ff1122"},
    {"name": "Pure White",   "rgb": (15, 15, 15),"hex": "#ffffff"},
]

# Music Sync Color Palettes
PALETTES = {
    "cyberpunk": {
        "name": "Cyberpunk Neon",
        "colors": [(15, 0, 15), (0, 15, 15), (15, 0, 4), (0, 8, 15)],
        "preview": ["#ff00ff", "#00ffff", "#ff0044", "#0088ff"],
    },
    "rainbow": {
        "name": "Vivid Rainbow",
        "colors": [(15, 0, 0), (15, 8, 0), (15, 15, 0), (0, 15, 0), (0, 15, 15), (0, 0, 15), (15, 0, 15)],
        "preview": ["#ff0000", "#ff8800", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff"],
    },
    "sunset": {
        "name": "Sunset Synthwave",
        "colors": [(15, 1, 0), (15, 6, 0), (15, 12, 0), (12, 0, 8), (6, 0, 12)],
        "preview": ["#ff1100", "#ff6600", "#ffcc00", "#cc0088", "#6600cc"],
    },
    "ocean": {
        "name": "Deep Ocean",
        "colors": [(0, 4, 15), (0, 12, 15), (0, 15, 10), (0, 15, 15)],
        "preview": ["#0044ff", "#00ccff", "#00ffaa", "#00ffff"],
    },
    "fire": {
        "name": "Blazing Fire",
        "colors": [(15, 0, 0), (15, 4, 0), (15, 10, 0), (15, 15, 2)],
        "preview": ["#ff0000", "#ff4400", "#ffaa00", "#ffff22"],
    },
    "emerald": {
        "name": "Matrix Emerald",
        "colors": [(0, 15, 2), (0, 15, 8), (4, 15, 0), (0, 12, 4)],
        "preview": ["#00ff22", "#00ff88", "#44ff00", "#00cc44"],
    },
    "red": {
        "name": "Pure Red",
        "colors": [(15, 0, 0)],
        "preview": ["#ff0000"],
    },
    "blue": {
        "name": "Electric Blue",
        "colors": [(0, 2, 15)],
        "preview": ["#0022ff"],
    },
    "cyan": {
        "name": "Cyber Cyan",
        "colors": [(0, 15, 15)],
        "preview": ["#00ffff"],
    },
    "purple": {
        "name": "Violet Purple",
        "colors": [(12, 0, 15)],
        "preview": ["#cc00ff"],
    },
}

def hex_to_nibbles(hex_str):
    """Convert #RRGGBB or #RGB string to 4-bit (0..15) RGB tuple."""
    if not hex_str:
        return (0, 15, 15)
    s = hex_str.strip().lstrip("#")
    if len(s) == 6:
        r = int(s[0:2], 16) >> 4
        g = int(s[2:4], 16) >> 4
        b = int(s[4:6], 16) >> 4
        return (r, g, b)
    elif len(s) == 3:
        r = int(s[0], 16)
        g = int(s[1], 16)
        b = int(s[2], 16)
        return (r, g, b)
    return (0, 15, 15)

def nibbles_to_hex(r, g, b):
    """Convert 4-bit (0..15) RGB tuple to #RRGGBB string."""
    r8 = min(255, (r & 0xf) * 17)
    g8 = min(255, (g & 0xf) * 17)
    b8 = min(255, (b & 0xf) * 17)
    return f"#{r8:02x}{g8:02x}{b8:02x}"
