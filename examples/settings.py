"""
settings.py
"""

from enum import Enum

# The Settings menu's boxes, in the order this module lists the settings.
SECTIONS = {
    "Display": ["FPS"],
    "Audio": ["MASTER_VOLUME", "MUSIC_VOLUME", "SFX_VOLUME", "MUTE_AUDIO"],
    "Gameplay": ["PLAYER_NAME", "DIFFICULTY", "INVERT_Y_AXIS"],
    "Debug": ["DEBUG_MODE", "SHOW_FPS", "SHOW_HITBOXES"],
}


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

# Audio.
MASTER_VOLUME: float = 1.0
MUSIC_VOLUME: float = 0.8
SFX_VOLUME: float = 1.0
MUTE_AUDIO: bool = False

# Gameplay.
PLAYER_NAME: str = "PLAYER"
DIFFICULTY: DifficultyType = DifficultyType.NORMAL
INVERT_Y_AXIS: bool = False

# Debug.
DEBUG_MODE: bool = False
SHOW_FPS: bool = False
SHOW_HITBOXES: bool = False
