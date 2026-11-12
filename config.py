"""
config.py

User-adjustable runtime settings, edited via the in-game Settings menu.

Finite-choice settings are typed as Enum subclasses so the menu can render
them as Selectors. Open-ended settings use primitive types (bool, int,
float, str) and are rendered as InputFields with type-matched validators.
"""

from enum import Enum


class DifficultyTypes(Enum):
    EASY = "EASY"
    NORMAL = "NORMAL"
    HARD = "HARD"
    NIGHTMARE = "NIGHTMARE"


class WindowModeTypes(Enum):
    WINDOWED = "WINDOWED"
    BORDERLESS = "BORDERLESS"
    FULLSCREEN = "FULLSCREEN"


class TextureQualityTypes(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ULTRA = "ULTRA"


# Display
FPS: int = 120

# Audio
MASTER_VOLUME: float = 1.0
MUSIC_VOLUME: float = 0.8
SFX_VOLUME: float = 1.0
MUTE_AUDIO: bool = False

# Gameplay
PLAYER_NAME: str = "PLAYER"
DIFFICULTY: DifficultyTypes = DifficultyTypes.NORMAL
INVERT_Y_AXIS: bool = False

# Debug
DEBUG_MODE: bool = False
SHOW_FPS: bool = False
SHOW_HITBOXES: bool = False
