"""
elements.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

from facade import (
    NATIVE_FONT_SIZE,
    TRANSPARENT,
    AlignmentType,
    Button,
    Color,
    HorizontalDivision,
    JustifyType,
    Measure,
    NormalText,
    PrimaryButton,
    Text,
    ThemeColorType,
    VerticalDivision,
)

TITLE_COLUMN_PW = 296.0  # Everything on the title screen shares the width of its buttons.
COLUMN_PW = 290.0  # The width of a settings row: a label, a gap and an input.
PANEL_SHADOW_PH = 3.0

_PANEL_PADDING = 16.0


@dataclass(kw_only=True, repr=False)
class TitleButton(Button):
    """A button as wide as the title column, with its label at twice the native font size."""

    @dataclass(kw_only=True, repr=False)
    class TitleButtonText(Button.ButtonText):
        """The label of a title button."""

        # Twice the native font size keeps the pixel font crisp, and the box scales to match.
        font_size: int = NATIVE_FONT_SIZE * 2

    label: Text = field(default_factory=TitleButtonText)
    size: Measure = (TITLE_COLUMN_PW, 44.0)
    padding: Measure = (12.0, 12.0)


@dataclass(kw_only=True, repr=False)
class TitlePrimaryButton(PrimaryButton):
    """The title screen's main action, as wide as the title column."""

    @dataclass(kw_only=True, repr=False)
    class TitlePrimaryButtonText(PrimaryButton.PrimaryButtonText):
        """The label of a title primary button."""

        font_size: int = NATIVE_FONT_SIZE * 2

    label: Text = field(default_factory=TitlePrimaryButtonText)
    size: Measure = (TITLE_COLUMN_PW, 44.0)


@dataclass(kw_only=True, repr=False)
class Panel(VerticalDivision):
    """A read-only box for one section, so its rows read as one group."""

    size: Measure = (COLUMN_PW + 2 * (_PANEL_PADDING + 1), 0.0)
    padding: Measure = (_PANEL_PADDING, _PANEL_PADDING)
    gap: Measure = (0.0, 8.0)
    background_color: Color = ThemeColorType.SURFACE_INPUT
    border_thickness: int = 1
    border_color: Color = ThemeColorType.BORDER_DISPLAY
    shadow_color: Color = ThemeColorType.SHADOW
    shadow_alpha: int = 0xB0
    shadow_offset: Measure = (PANEL_SHADOW_PH, PANEL_SHADOW_PH)


@dataclass(kw_only=True, repr=False)
class SettingLabel(NormalText):
    """The name of a setting, drawn like a read-only box and wider than the input beside it."""

    size: Measure = (136.0, 22.0)
    padding: Measure = (6.0, 6.0)
    alignment: AlignmentType = AlignmentType.MIDLEFT
    background_color: Color = ThemeColorType.SURFACE_DISPLAY
    border_color: Color = ThemeColorType.BORDER_DISPLAY
    border_thickness: int = 1
    shadow_color: Color = TRANSPARENT  # Display boxes sit flat. Only inputs cast a shadow.


@dataclass(kw_only=True, repr=False)
class SettingRow(HorizontalDivision):
    """A setting's label and the input that edits it, side by side."""

    justify: JustifyType = JustifyType.START
    gap: Measure = (6.0, 0.0)
