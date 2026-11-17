"""
menus.py
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
    ColorSwatch,
    CreditList,
    Element,
    Gap,
    HeadingTwoText,
    InputField,
    JustifyType,
    KeyBinding,
    Measure,
    Menu,
    NATIVE_FONT_SIZE,
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

from elements import COLUMN_PW, PANEL_SHADOW_PH, TITLE_COLUMN_PW, Panel, SettingLabel, SettingRow, TitleButton, TitlePrimaryButton


# What the library can do, one line each at the title column's width.
_DEMO_NOTES = (
    "MENUS RENDERED FROM AN ELEMENT TREE",
    "OPTIMIZED RERENDERS FROM CONTENT CHANGES",
    "CUSTOMIZABLE THEME WITH COLOR ROLES",
    "DEBUG FUNCTIONALITY",
)

_SECTION_GAP_PH = 12.0  # Empty space between the heading, each box and the button, shadows included.


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
    root_background_alpha: int = 0xA0  # Lets the table and ball show through.
    is_scaled: bool = False  # Built at its own sizes, which the other menus reach at the default GUI scale.

    def __post_init__(self):
        title_size = NATIVE_FONT_SIZE * 4
        # One font pixel of shadow per 14px of type keeps it on the font's grid.
        shadow_offset = title_size / NATIVE_FONT_SIZE
        self.root_elements = [
            TitleText(text="FACADE", font_size=title_size, shadow_color=ThemeColorType.HEADING_SHADOW, shadow_offset=(shadow_offset, shadow_offset)),
            Gap(size=(0, 6)),
            NormalText(text="AN EXAMPLE OF THE FACADE LIBRARY", text_color=ThemeColorType.TEXT_MUTED),
            Gap(size=(0, 22)),
            TitlePrimaryButton(label=TitlePrimaryButton.TitlePrimaryButtonText(text="PLAY"), action=self.on_start),
            TitleButton(label=TitleButton.TitleButtonText(text="SETTINGS"), action=self.on_settings),
            TitleButton(label=TitleButton.TitleButtonText(text="ABOUT"), action=self.on_about),
            TitleButton(label=TitleButton.TitleButtonText(text="QUIT"), action=self.on_quit),
            Gap(size=(0, 18)),
            SectionHeader(label=SectionHeader.HeaderText(text="INSIDE FACADE"), size=(TITLE_COLUMN_PW, 0.0)),
            BulletList(size=(TITLE_COLUMN_PW, 0.0), paragraphs=list(_DEMO_NOTES)),
        ]
        super().__post_init__()


@dataclass(kw_only=True)
class Pause(Menu):
    """
    In-game pause menu: a small boxed panel in the middle of the window, with
    the paused table only lightly dimmed around it. Leaving is set apart at
    the bottom, under a section header that says where it goes.
    """

    on_resume: Callable = field(default=lambda: None)
    on_restart: Callable = field(default=lambda: None)
    on_exit: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.CENTER
    root_background_alpha: int = 0x60  # Dims the table a little. The panel itself is nearly solid.

    def __post_init__(self):
        title_size = NATIVE_FONT_SIZE * 2
        # One font pixel of shadow per 14px of type keeps it on the font's grid.
        shadow_offset = title_size / NATIVE_FONT_SIZE
        panel = VerticalDivision(
            padding=(18.0, 18.0),
            gap=(0.0, 8.0),
            background_color=ThemeColorType.BACKGROUND,
            background_alpha=0xE0,
            border_color=ThemeColorType.BORDER_DISPLAY,
            border_thickness=1,
            elements=[
                TitleText(text="PAUSED", font_size=title_size, shadow_color=ThemeColorType.HEADING_SHADOW, shadow_offset=(shadow_offset, shadow_offset)),
                Gap(size=(0, 6)),
                Button(label=Button.ButtonText(text="RESUME"), action=self.on_resume),
                Button(label=Button.ButtonText(text="RESTART"), action=self.on_restart),
                Gap(size=(0, 6)),
                SectionHeader(label=SectionHeader.HeaderText(text="TO TITLE"), size=(148.0, 0.0)),  # As wide as the buttons.
                PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="EXIT"), action=self.on_exit),
            ],
        )
        self.root_elements = [panel]
        super().__post_init__()


@dataclass(kw_only=True)
class Settings(Menu):
    """Settings menu - dynamically generates editors for each uppercase
    attribute of ``settings`` (a module, namespace or other object).

    Edits are written straight back with ``setattr``. Enum values are edited
    with a Selector, tuples of key names with a KeyBinding, ``#RRGGBBAA`` strings
    with a ColorSwatch, bool values with a Toggle, floats from 0 to 1 with a
    Slider, and other int, float and str values with an InputField.

    Laid out like ``About``: a centred heading, one box per section and a
    centred button, evenly spaced. ``sections`` maps each box's title to the
    names it holds, in order; names left out go in a last "Other" box, and
    with no sections every setting shares one untitled box.
    """

    settings: Any  # Object whose UPPERCASE attributes are edited in place.
    sections: dict[str, list[str]] = field(default_factory=dict)
    on_return: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.CENTER
    root_gap: Measure = (0.0, 0.0)  # Every gap is a Gap below, so the heading's can differ.

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

        def _binding_action(name: str) -> Callable[[Any], bool]:
            def _apply(keys: Any) -> bool:
                setattr(config, name, tuple(keys))
                return True
            return _apply

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
            if isinstance(value, tuple):
                return KeyBinding(value=value, action=_binding_action(name))
            if isinstance(value, str) and re.fullmatch(RGBA_REGEX, value, flags=re.IGNORECASE):
                return ColorSwatch(value=ColorSwatch.InputValueText(text=value.upper()), action=_input_action(name, str.upper))
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

        # Only values with an editor become settings, so a module can keep other constants, such as its sections.
        rows = {
            name: SettingRow(elements=[SettingLabel(text=name.upper().replace("_", " ")), _build_editor(name, value)])
            for name, value in vars(config).items()
            if name.isupper() and isinstance(value, (bool, int, float, str, Enum, tuple))
        }

        groups: list[tuple[str | None, list[str]]] = [
            (title, [name for name in names if name in rows]) for title, names in self.sections.items()
        ]
        placed = {name for _, names in groups for name in names}
        leftover = [name for name in rows if name not in placed]
        if leftover:
            groups.append(("Other" if groups else None, leftover))

        heading = HeadingTwoText(text="Settings", text_decorations=TextDecorationType.UNDERLINE)
        # As on About, each spacer adds the shadow of the part above it so the visible space is even.
        elements: list[Element] = [heading, Gap(size=(0.0, _SECTION_GAP_PH + heading.shadow_offset[1]))]
        for title, names in groups:
            if not names:
                continue
            header = [SectionHeader(label=SectionHeader.HeaderText(text=title), size=(COLUMN_PW, 0.0), justify=JustifyType.START)] if title else []
            elements += [Panel(elements=[*header, *[rows[name] for name in names]]), Gap(size=(0.0, _SECTION_GAP_PH + PANEL_SHADOW_PH))]
        elements.append(Button(label=Button.ButtonText(text="RETURN"), action=self.on_return))

        self.root_elements = elements
        super().__post_init__()


@dataclass(kw_only=True)
class About(Menu):
    """About screen: a centred heading, one box per section and a centred button, all evenly spaced."""

    on_return: Callable = field(default=lambda: None)

    root_alignment: AlignmentType = AlignmentType.CENTER
    root_gap: Measure = (0.0, 0.0)  # Every gap is a Gap below, so the heading's can differ.

    def __post_init__(self):
        column = (COLUMN_PW, 0.0)
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
        # The heading's layout box already takes in its underline. Its shadow drops below that.
        after_heading = Gap(size=(0.0, _SECTION_GAP_PH + heading.shadow_offset[1]))
        after_panel = (0.0, _SECTION_GAP_PH + PANEL_SHADOW_PH)
        self.root_elements = [
            heading,
            after_heading,
            Panel(elements=[intro]),
            Gap(size=after_panel),
            Panel(elements=controls),
            Gap(size=after_panel),
            Panel(elements=credits),
            Gap(size=after_panel),
            Button(label=Button.ButtonText(text="RETURN"), action=self.on_return),
        ]
        super().__post_init__()

