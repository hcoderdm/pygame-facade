"""
types.py
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Callable
import uuid

from .elements import (
    ALPHANUMERIC_REGEX,
    FLOAT_REGEX,
    INT_REGEX,
    MEASURE,
    RGBA,
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
    NormalText,
    Selector,
    TextDecorationTypes,
    TitleText,
    VerticalDivision,
)


@dataclass(kw_only=True)
class MenuType(ABC):
    """
    Represents an abstract menu type with configurable layout, scrolling,
    and selection logic. Manages a root container of elements, supports
    smooth scrolling, and provides methods to navigate and select among
    selectable elements.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    _scroll: float = 0.0
    _dscroll: float = 0.0
    _d2scroll: float = 0.0

    # Root division config — controls how elements are laid out inside the menu
    root_elements: list[Element] = field(default_factory=list)
    root_justify: JustifyType = JustifyType.CENTER
    root_alignment: AlignmentType = AlignmentType.TOPLEFT
    root_size: MEASURE = (1.0, 1.0)
    root_anchor: MEASURE = (0.0, 0.0)
    root_margin: MEASURE = (0.0, 0.0)
    root_offset: MEASURE = (0.0, 0.0)
    root_padding: MEASURE = (16.0, 16.0)
    root_gap: MEASURE = (8.0, 8.0)
    root_size_measure = MeasureType.RELATIVE
    root_anchor_measure = MeasureType.ABSOLUTE
    root_margin_measure = MeasureType.ABSOLUTE
    root_offset_measure = MeasureType.ABSOLUTE
    root_padding_measure = MeasureType.ABSOLUTE
    root_gap_measure = MeasureType.ABSOLUTE
    root_background_color: RGBA = "#0C0E14FF"
    root_background_alpha: int = 0xFF
    root_border_thickness: int = 0
    root_border_color: RGBA = "#00000000"
    root_is_flexible: bool = False
    root_is_selectable: bool = False
    root_is_visible: bool = True

    _div: VerticalDivision = field(init=False, repr=False, compare=False)
    _selected_index: int = field(init=False, repr=False, compare=False, default=0)

    def __post_init__(self):
        self._div = VerticalDivision(
            elements=self.root_elements,
            justify=self.root_justify,
            alignment=self.root_alignment,
            size=self.root_size,
            anchor=self.root_anchor,
            margin=self.root_margin,
            offset=self.root_offset,
            padding=self.root_padding,
            gap=self.root_gap,
            size_measure=self.root_size_measure,
            anchor_measure=self.root_anchor_measure,
            margin_measure=self.root_margin_measure,
            offset_measure=self.root_offset_measure,
            padding_measure=self.root_padding_measure,
            gap_measure=self.root_gap_measure,
            background_color=self.root_background_color,
            background_alpha=self.root_background_alpha,
            border_thickness=self.root_border_thickness,
            border_color=self.root_border_color,
            is_selectable=self.root_is_selectable,
            is_visible=self.root_is_visible,
        )
        self._selected_index = 0

    """Scroll helpers"""

    def apply_scroll_impulse(self, accel: float) -> None:
        self._d2scroll += accel

    def integrate_scroll(self, max_scroll: float, dt: float, drag: float, deadzone: float) -> None:
        self._dscroll += self._d2scroll * dt
        self._dscroll *= math.exp(-drag * dt)

        if abs(self._dscroll) < deadzone:
            self._dscroll *= 0.5

        self._scroll += self._dscroll * dt

        if self._scroll < 0.0:
            if self._dscroll < 0:
                self._dscroll = 0.0
            self._scroll = 0.0
        elif self._scroll > max_scroll:
            if self._dscroll > 0:
                self._dscroll = 0.0
            self._scroll = max_scroll

        self._d2scroll = 0.0

    """Selection helpers."""

    @property
    def _selectable_elements(self) -> list[Element]:
        """Flat list of nested elements that can receive selection focus."""

        def walk(elements):
            for e in elements:
                if e.is_selectable:
                    yield e
                if hasattr(e, "elements") and e.elements:
                    yield from walk(e.elements)

        return list(walk(self.root_elements))

    def get_selected_element(self) -> Element | None:
        items = self._selectable_elements
        if not items:
            return None
        idx = self._selected_index % len(items)
        return items[idx]

    def get_selection_id(self) -> str | None:
        items = self._selectable_elements
        if not items:
            return None
        idx = self._selected_index % len(items)
        return items[idx].id

    def select_element_by_id(self, element_id: str) -> bool:
        for idx, element in enumerate(self._selectable_elements):
            if element.id == element_id:
                if self._selected_index != idx:
                    self._selected_index = idx
                    Element._iterative_version += 1
                return True
        return False

    def move_selected_down(self) -> None:
        items = self._selectable_elements
        if not items:
            return
        new_idx = min((self._selected_index + 1), len(items) - 1)
        if new_idx != self._selected_index:
            self._selected_index = new_idx
            Element._iterative_version += 1

    def move_selected_up(self) -> None:
        items = self._selectable_elements
        if not items:
            return
        new_idx = max((self._selected_index - 1), 0)
        if new_idx != self._selected_index:
            self._selected_index = new_idx
            Element._iterative_version += 1


"""
The following are example use cases of `MenuType`
"""

@dataclass(kw_only=True)
class Start(MenuType):
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
                        text_decorations=TextDecorationTypes.ITALIC | TextDecorationTypes.ANTIALIASING,
                    ),
                    TitleText(
                        text="Mountain",
                        text_color="#F0B443FF",
                        shadow_color="#E6A23EFF",
                        shadow_offset=(3.0, 3.0),
                        text_decorations=TextDecorationTypes.UNDERLINE,
                    ),
                    TitleText(
                        text="OF",
                        font_size=18 * 2,
                        text_color="#F0B443FF",
                        text_decorations=TextDecorationTypes.ITALIC | TextDecorationTypes.ANTIALIASING,
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
class Pause(MenuType):
    """In-game pause overlay menu."""

    on_resume: Callable = field(default=lambda: None)
    on_restart: Callable = field(default=lambda: None)
    on_exit: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.MIDTOP
    root_background_alpha: int = 0x80

    def __post_init__(self):
        self.root_elements = [
            Button(label=Button.ButtonText(text="RESUME"), action=self.on_resume),
            Button(label=Button.ButtonText(text="RESTART"), action=self.on_restart),
            Button(label=Button.ButtonText(text="EXIT"), action=self.on_exit),
        ]
        super().__post_init__()


@dataclass(kw_only=True)
class Settings(MenuType):
    """Settings menu - dynamically generates editors for each uppercase
    variable in the config module."""

    on_return: Callable = field(default=lambda: None)

    def __post_init__(self):
        import config

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
            HeadingTwoText(text="Settings", justify=JustifyType.START, text_decorations=TextDecorationTypes.UNDERLINE),
            NormalText(text="Adjust game values.", justify=JustifyType.START, is_wrapable=True),
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
class About(MenuType):
    """About screen."""

    on_return: Callable = field(default=lambda: None)

    def __post_init__(self):
        self.root_elements = [
            HeadingTwoText(text="About", justify=JustifyType.START, text_decorations=TextDecorationTypes.UNDERLINE),
            NormalText(text=_LOREM, justify=JustifyType.START, is_wrapable=True),
            NormalText(text=_LOREM, justify=JustifyType.START, is_wrapable=True),
            Button(
                label=Button.ButtonText(text="RETURN"),
                action=self.on_return,
                justify=JustifyType.START,
            ),
        ]
        super().__post_init__()
