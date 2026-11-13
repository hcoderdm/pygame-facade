"""
facade

Menu and UI overlay toolkit for pygame-ce games.
"""

from .assets import FontManager, ImageManager
from .elements import (
    ALPHANUMERIC_REGEX,
    FLOAT_REGEX,
    INT_REGEX,
    RGBA,
    RGBA_REGEX,
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
    Measure,
    MeasureType,
    NormalText,
    OverflowType,
    RotationType,
    SelectedModifier,
    Selector,
    Slider,
    SubtitleText,
    Text,
    TextDecorationType,
    TitleText,
    Toggle,
    VerticalDivision,
)
from .interface import Interface
from .manager import (
    MenuManager,
    handle_menu_keydown,
    handle_menu_mousebuttondown,
    handle_menu_mousebuttonup,
    handle_menu_mousemotion,
    handle_menu_mousewheel,
    handle_menu_textinput,
)
from .menus import Menu
from .renderer import MenuRenderer


__all__ = [
    "Interface",
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
    "Measure",
    "MeasureType",
    "JustifyType",
    "AlignmentType",
    "TextDecorationType",
    "ImageTransformType",
    "OverflowType",
    "RotationType",
    # Input validators
    "INT_REGEX",
    "FLOAT_REGEX",
    "ALPHANUMERIC_REGEX",
    "RGBA_REGEX",
    # Menus
    "Menu",
    # Menu stack and input
    "MenuManager",
    "handle_menu_mousemotion",
    "handle_menu_mousebuttondown",
    "handle_menu_mousebuttonup",
    "handle_menu_mousewheel",
    "handle_menu_keydown",
    "handle_menu_textinput",
    # Rendering
    "MenuRenderer",
    "FontManager",
    "ImageManager",
]
