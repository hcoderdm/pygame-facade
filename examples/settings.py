"""
settings.py
"""

from enum import Enum

# The Settings menu's boxes, in the order this module lists the settings.
SECTIONS = {
    "Display": ["FPS", "GUI_SCALE"],
    "Audio": ["MASTER_VOLUME", "MUSIC_VOLUME", "SFX_VOLUME", "MUTE_AUDIO"],
    "Gameplay": ["PLAYER_NAME", "DIFFICULTY", "INVERT_Y_AXIS"],
    "Controls": ["SPEED_UP", "SLOW_DOWN", "RESET_BALL"],
    "Colors": ["TABLE_COLOR", "BALL_COLOR"],
    "Debug": ["DEBUG_MODE", "SHOW_FPS", "SHOW_HITBOXES"],
}


class GuiScaleType(Enum):
    SMALL = 1
    NORMAL = 2
    LARGE = 3


class DifficultyType(Enum):
    EASY = "EASY"
    NORMAL = "NORMAL"
    HARD = "HARD"
    NIGHTMARE = "NIGHTMARE"


class WindowModeType(Enum):
    WINDOWED = "WINDOWED"
    BORDERLESS = "BORDERLESS"
    FULLSCREEN = "FULLSCREEN"


class TextureQualityType(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ULTRA = "ULTRA"


# Display.
FPS: int = 120
GUI_SCALE: GuiScaleType = GuiScaleType.SMALL

# Audio.
MASTER_VOLUME: float = 1.0
MUSIC_VOLUME: float = 0.8
SFX_VOLUME: float = 1.0
MUTE_AUDIO: bool = False

# Gameplay.
PLAYER_NAME: str = "PLAYER"
DIFFICULTY: DifficultyType = DifficultyType.NORMAL
INVERT_Y_AXIS: bool = False

# Controls, as key names that facade.get_event_keys gives for a key press.
SPEED_UP: tuple[str, ...] = ("UP",)
SLOW_DOWN: tuple[str, ...] = ("DOWN",)
RESET_BALL: tuple[str, ...] = ("CTRL", "R")

# Colors.
TABLE_COLOR: str = "#184030FF"
BALL_COLOR: str = "#FFD43BFF"

# Debug.
DEBUG_MODE: bool = False
SHOW_FPS: bool = False
SHOW_HITBOXES: bool = False
