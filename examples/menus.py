"""
menus.py

The demo's menus. Each is a ``Menu`` subclass that fills ``root_elements``
in ``__post_init__`` from its callback fields; nothing here is part of the
facade package, so a game is free to define screens that look nothing like
these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Callable

from facade import (
    ALPHANUMERIC_REGEX,
    FLOAT_REGEX,
    INT_REGEX,
    RGBA_REGEX,
    AlignmentType,
    Button,
    Element,
    Gap,
    HeadingTwoText,
    HorizontalDivision,
    InputField,
    JustifyType,
    MeasureType,
    Menu,
    NormalText,
    Selector,
    TextDecorationType,
    TitleText,
)


@dataclass(kw_only=True)
class Start(Menu):
    """Full-screen start/title menu."""

    on_start: Callable = field(default=lambda: None)
    on_quit: Callable = field(default=lambda: None)
    on_settings: Callable = field(default=lambda: None)
    on_about: Callable = field(default=lambda: None)

    def __post_init__(self):
        self.root_elements = [
            Gap(size=(1.0, 0.10), size_measure=MeasureType.RELATIVE),
            HorizontalDivision(
                gap=(12.0, 0.0),
                background_color="#3D252BFF",
                padding=(24.0, 32.0),
                border_color="#E6A23EFF",
                border_thickness=2,
                shadow_color="#E6A23EFF",
                shadow_alpha=0x60,
                elements=[
                    TitleText(
                        text="A",
                        font_size=18 * 2,
                        text_color="#F0B443FF",
                        text_decorations=TextDecorationType.ITALIC | TextDecorationType.ANTIALIASING,
                    ),
                    TitleText(
                        text="Mountain",
                        text_color="#F0B443FF",
                        shadow_color="#E6A23EFF",
                        shadow_offset=(3.0, 3.0),
                        text_decorations=TextDecorationType.UNDERLINE,
                    ),
                    TitleText(
                        text="OF",
                        font_size=18 * 2,
                        text_color="#F0B443FF",
                        text_decorations=TextDecorationType.ITALIC | TextDecorationType.ANTIALIASING,
                    ),
                    TitleText(
                        text="Tiles",
                        text_color="#F0B443FF",
                        shadow_color="#E6A23EFF",
                        shadow_offset=(3.0, 3.0),
                    ),
                ],
            ),
            Gap(size=(0, 48)),
            Button(
                label=Button.ButtonText(text="Start Game"),
                action=self.on_start,
            ),
            Gap(size=(0, 12)),
            Button(label=Button.ButtonText(text="SETTINGS"), action=self.on_settings),
            Button(label=Button.ButtonText(text="ABOUT"), action=self.on_about),
            Button(label=Button.ButtonText(text="QUIT"), action=self.on_quit),
        ]
        super().__post_init__()


@dataclass(kw_only=True)
class Pause(Menu):
    """In-game pause overlay menu."""

    on_resume: Callable = field(default=lambda: None)
    on_restart: Callable = field(default=lambda: None)
    on_exit: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.MIDTOP
    root_background_alpha: int = 0xC0  # Dims the game behind the menu by three quarters

    def __post_init__(self):
        self.root_elements = [
            Button(label=Button.ButtonText(text="RESUME"), action=self.on_resume),
            Button(label=Button.ButtonText(text="RESTART"), action=self.on_restart),
            Button(label=Button.ButtonText(text="EXIT"), action=self.on_exit),
        ]
        super().__post_init__()


@dataclass(kw_only=True)
class Settings(Menu):
    """Settings menu - dynamically generates editors for each uppercase
    attribute of ``settings`` (a module, namespace or other object).

    Edits are written straight back with ``setattr``. Enum and bool values
    are edited with a Selector; int, float and str values with an InputField.
    """

    settings: Any  # Object whose UPPERCASE attributes are edited in place
    on_return: Callable = field(default=lambda: None)

    def __post_init__(self):
        config = self.settings

        def _pick_validator(value: object) -> tuple[str, Callable[[str], object]]:
            if isinstance(value, int) and not isinstance(value, bool):
                return INT_REGEX, int
            if isinstance(value, float):
                return FLOAT_REGEX, float
            if isinstance(value, str) and re.fullmatch(RGBA_REGEX, value, flags=re.IGNORECASE):
                return RGBA_REGEX, lambda s: s.upper()
            return ALPHANUMERIC_REGEX, lambda s: s

        def _authenticator(pattern: str) -> Callable[[str], bool]:
            return lambda s, pat=pattern: bool(re.fullmatch(pat, s, flags=re.IGNORECASE))

        def _input_action(name: str, converter: Callable[[str], Any]) -> Callable[[Any], bool]:
            def _apply(raw: Any) -> bool:
                try:
                    setattr(config, name, converter(str(raw)))
                    return True
                except Exception:
                    return False
            return _apply

        def _selector_action(name: str, options: tuple[Any, ...]) -> Callable[[Any], bool]:
            def _apply(index: Any) -> bool:
                try:
                    setattr(config, name, options[int(index)])
                    return True
                except Exception:
                    return False
            return _apply

        def _label(name: str) -> Element:
            return NormalText(
                font_size=18,
                padding=(4.0, 2.0),
                background_color="#30384EFF",
                border_color="#606060FF",
                border_thickness=1,
                text=name.upper().replace("_", " ") + ":",
            )

        def _build_editor(name: str, value: Any) -> Element:
            if isinstance(value, Enum):
                enum_cls = type(value)
                members = tuple(enum_cls)
                names = tuple(m.name for m in members)
                return Selector(
                    selections=names,
                    value=members.index(value),
                    action=_selector_action(name, members),
                )
            if isinstance(value, bool):
                options = (False, True)
                return Selector(
                    selections=("FALSE", "TRUE"),
                    value=int(value),
                    action=_selector_action(name, options),
                )
            pattern, converter = _pick_validator(value)
            return InputField(
                size=(96.0, 17.0),
                value=InputField.InputValueText(text=str(value).upper()),
                hint=InputField.InputHintText(text="[ESC]"),
                validator=_authenticator(pattern),
                action=_input_action(name, converter),
            )

        dynamic_components = [
            HorizontalDivision(
                justify=JustifyType.START,
                gap=(8.0, 0.0),
                elements=[_label(name), _build_editor(name, value)],
            )
            for name, value in vars(config).items()
            if name.isupper()
        ]

        self.root_elements = [
            HeadingTwoText(text="Settings", justify=JustifyType.START, text_decorations=TextDecorationType.UNDERLINE),
            NormalText(text="Adjust game values.", justify=JustifyType.START, is_wrappable=True),
            Gap(size=(0.0, 4.0)),
            *dynamic_components,
            Gap(size=(0.0, 4.0)),
            Button(
                label=Button.ButtonText(text="RETURN"),
                action=self.on_return,
                justify=JustifyType.START,
            ),
        ]
        super().__post_init__()


_LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure "
    "dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt "
    "mollit anim id est laborum."
)


@dataclass(kw_only=True)
class About(Menu):
    """About screen."""

    on_return: Callable = field(default=lambda: None)

    def __post_init__(self):
        self.root_elements = [
            HeadingTwoText(text="About", justify=JustifyType.START, text_decorations=TextDecorationType.UNDERLINE),
            NormalText(text=_LOREM, justify=JustifyType.START, is_wrappable=True),
            NormalText(text=_LOREM, justify=JustifyType.START, is_wrappable=True),
            Button(
                label=Button.ButtonText(text="RETURN"),
                action=self.on_return,
                justify=JustifyType.START,
            ),
        ]
        super().__post_init__()
