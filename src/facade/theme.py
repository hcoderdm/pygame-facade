"""
theme.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .elements import RGBA


class ThemeColorType(Enum):
    """
    A colour named by what it is used for. Element colour fields hold one of
    these, and the renderer looks it up in the active ``Theme`` when drawing,
    so a menu can change theme without rebuilding its elements.
    """

    BACKGROUND = auto()  # Behind everything in a menu.
    SURFACE_INPUT = auto()  # Inside an input.
    SURFACE_DISPLAY = auto()  # Inside a display-only box.
    BORDER_INPUT = auto()  # Around an input.
    BORDER_DISPLAY = auto()  # Around a display-only box.
    TEXT_NORMAL = auto()  # Normal text.
    TEXT_MUTED = auto()  # Prompts, hints, the unchosen option.
    FILL = auto()  # Filled toggle half, bar segments and key chips.
    HEADING = auto()  # Headings and titles.
    SHADOW = auto()  # The shadow under inputs.
    PRIMARY = auto()  # The focused or hovered element.
    WARNING = auto()  # A value changed from its original.
    DANGER = auto()  # An invalid entry or a conflict.
    SUCCESS = auto()  # Something saved or confirmed.
    INFO = auto()  # Neutral notices and tips.

    HEADING_SHADOW = auto()  # Generated: the shadow under headings.
    TEXT_DISABLED = auto()  # Generated: anything that can't be used right now.


def mix_rgba(start: RGBA, end: RGBA, amount: float) -> RGBA:
    """``start`` moved ``amount`` of the way toward ``end``, alpha included."""
    start_channels = [int(start[idx:idx + 2], 16) for idx in (1, 3, 5, 7)]
    end_channels = [int(end[idx:idx + 2], 16) for idx in (1, 3, 5, 7)]
    mixed = (round(a + (b - a) * amount) for a, b in zip(start_channels, end_channels))
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


@dataclass(frozen=True, kw_only=True)
class Theme:
    """
    The colour for every ``ThemeColorType``. Two colours are generated rather
    than chosen: the heading shadow (the heading moved toward the background)
    and disabled text (normal text moved toward the input surface).

    ``extras`` holds colours a game draws with itself, picked from the same
    palette so the game matches its menus. Themes are frozen; derive a new one
    with ``dataclasses.replace``.

    Every theme should keep these apart, or states become hard to read:
    PRIMARY from DANGER (invalid text inside a focused field), PRIMARY from
    FILL (a lit toggle's option beside its filled half), WARNING from PRIMARY
    (a changed value in a focused control), and PRIMARY and FILL should both
    stand out on SURFACE_INPUT. FILL works best as a neutral colour.
    """

    background: RGBA
    surface_input: RGBA
    surface_display: RGBA
    border_input: RGBA
    border_display: RGBA
    text_normal: RGBA
    text_muted: RGBA
    fill: RGBA
    heading: RGBA
    shadow: RGBA
    primary: RGBA
    warning: RGBA
    danger: RGBA
    success: RGBA
    info: RGBA

    extras: dict[str, RGBA] = field(default_factory=dict)

    heading_shadow_amount: float = 0.6  # How far the heading shadow moves from the heading toward the background.
    text_disabled_amount: float = 0.62  # How far disabled text moves from normal text toward the input surface.

    def get_rgba(self, color: RGBA | ThemeColorType) -> RGBA:
        """The RGBA value of ``color``: a role is looked up in this theme, and an RGBA string is returned as it is."""
        if not isinstance(color, ThemeColorType):
            return color
        if color is ThemeColorType.HEADING_SHADOW:
            return mix_rgba(self.heading, self.background, self.heading_shadow_amount)
        if color is ThemeColorType.TEXT_DISABLED:
            return mix_rgba(self.text_normal, self.surface_input, self.text_disabled_amount)
        return getattr(self, color.name.lower())

    def get_extra(self, name: str) -> RGBA:
        """A colour the game added to this theme, such as a table or a ball."""
        return self.extras[name]


# Open Color's grays, with colour kept for state alone: indigo for focus, yellow for a changed
# value and red for an invalid one. Inputs sit darker than the background and display boxes lighter.
DEFAULT_THEME = Theme(
    background="#343A40FF",  # gray 8.
    surface_input="#212529FF",  # gray 9.
    surface_display="#495057FF",  # gray 7.
    border_input="#CED4DAFF",  # gray 4.
    border_display="#868E96FF",  # gray 6.
    text_normal="#F8F9FAFF",  # gray 0.
    text_muted="#ADB5BDFF",  # gray 5.
    fill="#F1F3F5FF",  # gray 1.
    heading="#F8F9FAFF",  # gray 0.
    shadow="#1A1D20FF",  # gray 8 halfway to black.
    primary="#91A7FFFF",  # indigo 3.
    warning="#FFD43BFF",  # yellow 4.
    danger="#FF6B6BFF",  # red 5.
    success="#69DB7CFF",  # green 4.
    info="#3BC9DBFF",  # cyan 4.
)
