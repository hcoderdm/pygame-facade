"""
facade

Menu and UI overlay toolkit for pygame-ce games.
"""

from .assets import FontManager, ImageManager
from .elements import (
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
from .menus import About, Menu, Pause, Settings, Start
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
    # Menus
    "Menu",
    "Start",
    "Pause",
    "Settings",
    "About",
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
