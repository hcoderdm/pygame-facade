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
    BulletList,
    Button,
    CreditList,
    Element,
    Gap,
    HeadingTwoText,
    HorizontalDivision,
    InputField,
    JustifyType,
    Measure,
    Menu,
    NATIVE_FONT_SIZE,
    TRANSPARENT,
    ThemeColorType,
    NormalText,
    PrimaryButton,
    SectionHeader,
    Selector,
    Slider,
    TextBlock,
    TextDecorationType,
    TitleText,
    Toggle,
    VerticalDivision,
)


_TITLE_COLUMN_PW = 296.0  # Everything on the title screen shares the width of its buttons

# What the library can do, one line each at the title column's width
_DEMO_NOTES = (
    "MENUS RENDERED FROM AN ELEMENT TREE",
    "OPTIMIZED RERENDERS FROM CONTENT CHANGES",
    "CUSTOMIZABLE THEME WITH COLOR ROLES",
    "DEBUG FUNCTIONALITY",
)


def _title_button(text: str, action: Callable) -> Button:
    """A button drawn at twice the native font size, with its box scaled to match."""
    return Button(
        label=Button.ButtonText(text=text, font_size=NATIVE_FONT_SIZE * 2),
        action=action,
        size=(_TITLE_COLUMN_PW, 44.0),
        padding=(12.0, 12.0),
    )


def _title_primary_button(text: str, action: Callable) -> PrimaryButton:
    """The title screen's main action, the same size as its other buttons."""
    return PrimaryButton(
        label=PrimaryButton.PrimaryButtonText(text=text, font_size=NATIVE_FONT_SIZE * 2),
        action=action,
        size=(_TITLE_COLUMN_PW, 44.0),
    )


@dataclass(kw_only=True)
class Start(Menu):
    """
    Title screen: one column centred on the page and drawn over the table,
    which shows through it with the ball still rolling. The title, the menu,
    then what the demo shows off.
    """

    on_start: Callable = field(default=lambda: None)
    on_quit: Callable = field(default=lambda: None)
    on_settings: Callable = field(default=lambda: None)
    on_about: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.CENTER
    root_background_alpha: int = 0xA0  # Lets the table and ball show through

    def __post_init__(self):
        title_size = NATIVE_FONT_SIZE * 4
        # One font pixel of shadow per 14px of type keeps it on the font's grid
        shadow_offset = title_size / NATIVE_FONT_SIZE
        self.root_elements = [
            TitleText(text="FACADE", font_size=title_size, shadow_color=ThemeColorType.HEADING_SHADOW, shadow_offset=(shadow_offset, shadow_offset)),
            Gap(size=(0, 6)),
            NormalText(text="AN EXAMPLE OF THE FACADE LIBRARY", text_color=ThemeColorType.TEXT_MUTED),
            Gap(size=(0, 22)),
            _title_primary_button("PLAY", self.on_start),
            _title_button("SETTINGS", self.on_settings),
            _title_button("ABOUT", self.on_about),
            _title_button("QUIT", self.on_quit),
            Gap(size=(0, 18)),
            SectionHeader(label=SectionHeader.HeaderText(text="INSIDE FACADE"), size=(_TITLE_COLUMN_PW, 0.0)),
            BulletList(size=(_TITLE_COLUMN_PW, 0.0), paragraphs=list(_DEMO_NOTES)),
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

    Edits are written straight back with ``setattr``. Enum values are edited
    with a Selector, bool values with a Toggle, floats from 0 to 1 with a
    Slider, and other int, float and str values with an InputField.

    Laid out like ``About``: a centred heading, one box per section and a
    centred button, evenly spaced. ``sections`` maps each box's title to the
    names it holds, in order; names left out go in a last "Other" box, and
    with no sections every setting shares one untitled box.
    """

    settings: Any  # Object whose UPPERCASE attributes are edited in place
    sections: dict[str, list[str]] = field(default_factory=dict)
    on_return: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.CENTER
    root_gap: Measure = (0.0, 0.0)  # Every gap is a Gap below, so the heading's can differ

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

        def _toggle_action(name: str) -> Callable[[Any], bool]:
            def _apply(value: Any) -> bool:
                setattr(config, name, bool(value))
                return True
            return _apply

        def _label(name: str) -> Element:
            # Drawn like a read-only box, and wider than the inputs beside it
            return NormalText(
                text=name.upper().replace("_", " "),
                size=(136.0, 22.0),
                padding=(6.0, 6.0),
                alignment=AlignmentType.MIDLEFT,
                background_color=ThemeColorType.SURFACE_DISPLAY,
                border_color=ThemeColorType.BORDER_DISPLAY,
                border_thickness=1,
                shadow_color=TRANSPARENT,  # Display boxes sit flat; only inputs cast a shadow
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
                return Toggle(value=value, action=_toggle_action(name))
            if isinstance(value, float) and 0.0 <= value <= 1.0:
                return Slider(value=value, step=0.1, action=_input_action(name, float))
            pattern, converter = _pick_validator(value)
            return InputField(
                value=InputField.InputValueText(text=str(value).upper()),
                hint=InputField.InputHintText(text="[ESC]"),
                validator=_authenticator(pattern),
                action=_input_action(name, converter),
            )

        rows = {
            name: HorizontalDivision(
                justify=JustifyType.START,
                gap=(6.0, 0.0),
                elements=[_label(name), _build_editor(name, value)],
            )
            for name, value in vars(config).items()
            if name.isupper()
        }

        groups: list[tuple[str | None, list[str]]] = [
            (title, [name for name in names if name in rows]) for title, names in self.sections.items()
        ]
        placed = {name for _, names in groups for name in names}
        leftover = [name for name in rows if name not in placed]
        if leftover:
            groups.append(("Other" if groups else None, leftover))

        heading = HeadingTwoText(text="Settings", text_decorations=TextDecorationType.UNDERLINE)
        # As on About, each spacer adds the shadow of the part above it so the visible space is even
        elements: list[Element] = [heading, Gap(size=(0.0, _SECTION_GAP_PH + heading.shadow_offset[1]))]
        for title, names in groups:
            if not names:
                continue
            header = [SectionHeader(label=SectionHeader.HeaderText(text=title), size=(_COLUMN_PW, 0.0), justify=JustifyType.START)] if title else []
            elements += [_panel([*header, *[rows[name] for name in names]]), Gap(size=(0.0, _SECTION_GAP_PH + _PANEL_SHADOW_PH))]
        elements.append(Button(label=Button.ButtonText(text="RETURN"), action=self.on_return))

        self.root_elements = elements
        super().__post_init__()


_COLUMN_PW = 290.0  # The width of a settings row: a label, a gap and an input
_PANEL_PADDING = 16.0
_SECTION_GAP_PH = 12.0  # Empty space between the heading, each box and the button, shadows included
_PANEL_SHADOW_PH = 3.0


def _panel(elements: list[Element]) -> VerticalDivision:
    """A read-only box for one section: the input panel colour, the read-only border and the shared shadow."""
    return VerticalDivision(
        elements=elements,
        size=(_COLUMN_PW + 2 * (_PANEL_PADDING + 1), 0.0),
        padding=(_PANEL_PADDING, _PANEL_PADDING),
        gap=(0.0, 8.0),
        background_color=ThemeColorType.SURFACE_INPUT,
        border_thickness=1,
        border_color=ThemeColorType.BORDER_DISPLAY,
        shadow_color=ThemeColorType.SHADOW,
        shadow_alpha=0xB0,
        shadow_offset=(_PANEL_SHADOW_PH, _PANEL_SHADOW_PH),
    )


@dataclass(kw_only=True)
class About(Menu):
    """About screen: a centred heading, one box per section and a centred button, all evenly spaced."""

    on_return: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.CENTER
    root_gap: Measure = (0.0, 0.0)  # Every gap is a Gap below, so the heading's can differ

    def __post_init__(self):
        column = (_COLUMN_PW, 0.0)
        intro = TextBlock(
            size=column,
            justify=JustifyType.START,
            paragraphs=[
                "This demo is a ball bouncing around the window, with every menu drawn over it by facade, a menu library for pygame.",
                [
                    "Open",
                    TextBlock.EmphasisText(text="Settings"),
                    "to change the game's values while it runs, or press",
                    TextBlock.EmphasisText(text="Esc"),
                    "during play to pause.",
                    TextBlock.AsideText(text="The ball stops while a menu is open."),
                ],
            ],
        )
        controls = [
            SectionHeader(label=SectionHeader.HeaderText(text="Controls"), size=column, justify=JustifyType.START),
            BulletList(
                size=column,
                justify=JustifyType.START,
                paragraphs=[
                    ["Move with the", TextBlock.EmphasisText(text="arrow keys"), "or the mouse."],
                    ["Press", TextBlock.EmphasisText(text="Return"), "to choose, or to edit a value and then keep it."],
                    ["Press", TextBlock.EmphasisText(text="Left"), "and", TextBlock.EmphasisText(text="Right"), "to change a value."],
                    ["Press", TextBlock.EmphasisText(text="Esc"), "to go back."],
                    ["Press", TextBlock.EmphasisText(text="F3"), "to", TextBlock.EmphasisText(text="F5"), "for debug overlays."],
                ],
            ),
        ]
        credits = [
            SectionHeader(label=SectionHeader.HeaderText(text="Credits"), size=column, justify=JustifyType.START),
            CreditList(
                size=column,
                justify=JustifyType.START,
                credits=[("Font", "Brian Kent"), ("Menus", "facade"), ("Engine", "pygame-ce")],
            ),
        ]

        heading = HeadingTwoText(text="About", text_decorations=TextDecorationType.UNDERLINE)
        # Shadows hang below a part's layout box, so each spacer adds the shadow of the part above it.
        # The heading's layout box already takes in its underline; its shadow drops below that
        after_heading = Gap(size=(0.0, _SECTION_GAP_PH + heading.shadow_offset[1]))
        after_panel = (0.0, _SECTION_GAP_PH + _PANEL_SHADOW_PH)
        self.root_elements = [
            heading,
            after_heading,
            _panel([intro]),
            Gap(size=after_panel),
            _panel(controls),
            Gap(size=after_panel),
            _panel(credits),
            Gap(size=after_panel),
            Button(label=Button.ButtonText(text="RETURN"), action=self.on_return),
        ]
        super().__post_init__()
