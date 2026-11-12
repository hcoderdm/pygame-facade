"""
facade

Menu and UI overlay toolkit for pygame-ce games.
"""

from .assets import FontManager, ImageManager
from .elements import (
    MEASURE,
    RGBA,
    AlignmentType,
    Button,
    Division,
    Element,
    Fill,
    Gap,
    HeadingOneText,
    HeadingThreeText,
    HeadingTwoText,
    HorizontalDivision,
    Image,
    ImageTransformType,
    InputField,
    InteractiveElement,
    JustifyType,
    MeasureType,
    NormalText,
    OverflowType,
    RotationType,
    SelectedModifier,
    Selector,
    Slider,
    SubtitleText,
    Text,
    TextDecorationTypes,
    TitleText,
    Toggle,
    VerticalDivision,
)
from .manager import (
    MenuManager,
    manage_menu_keydown,
    manage_menu_mousebuttondown,
    manage_menu_mousebuttonup,
    manage_menu_mousemotion,
    manage_menu_mousewheel,
    manage_menu_textinput,
)
from .menus import About, MenuType, Pause, Settings, Start
from .renderer import MenuRenderer


__all__ = [
    # Elements
    "Element",
    "SelectedModifier",
    "Division",
    "HorizontalDivision",
    "VerticalDivision",
    "Gap",
    "Fill",
    "Text",
    "NormalText",
    "TitleText",
    "SubtitleText",
    "HeadingOneText",
    "HeadingTwoText",
    "HeadingThreeText",
    "Image",
    "InteractiveElement",
    "Button",
    "Toggle",
    "Slider",
    "Selector",
    "InputField",
    # Attribute types
    "RGBA",
    "MEASURE",
    "MeasureType",
    "JustifyType",
    "AlignmentType",
    "TextDecorationTypes",
    "ImageTransformType",
    "OverflowType",
    "RotationType",
    # Menus
    "MenuType",
    "Start",
    "Pause",
    "Settings",
    "About",
    # Menu stack and input
    "MenuManager",
    "manage_menu_mousemotion",
    "manage_menu_mousebuttondown",
    "manage_menu_mousebuttonup",
    "manage_menu_mousewheel",
    "manage_menu_keydown",
    "manage_menu_textinput",
    # Rendering
    "MenuRenderer",
    "FontManager",
    "ImageManager",
]
