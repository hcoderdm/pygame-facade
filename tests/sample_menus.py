"""
sample_menus.py
"""

from dataclasses import dataclass, field
from typing import Callable

from facade import AlignmentType, Button, InputField, Menu, NormalText, TitleText

_PARAGRAPH = " ".join(["The quick brown fox jumps over the lazy dog."] * 12)


def selected_label(menu: Menu) -> str:
    """The label text of the button selected in ``menu``."""
    element = menu.get_selected_element()
    assert isinstance(element, Button)
    return element.label.text


@dataclass(kw_only=True)
class Title(Menu):
    """An opaque full-window menu with a few buttons, like a start screen."""

    on_start: Callable = field(default=lambda: None)
    on_quit: Callable = field(default=lambda: None)

    def __post_init__(self):
        self.root_elements = [
            TitleText(text="Title"),
            Button(label=Button.ButtonText(text="START"), action=self.on_start),
            Button(label=Button.ButtonText(text="OPTIONS")),
            Button(label=Button.ButtonText(text="QUIT"), action=self.on_quit),
        ]
        super().__post_init__()


@dataclass(kw_only=True)
class Overlay(Menu):
    """A translucent menu that does not cover the window, like a pause screen."""

    root_alignment: AlignmentType = AlignmentType.MIDTOP
    root_background_alpha: int = 0xC0

    def __post_init__(self):
        self.root_elements = [
            Button(label=Button.ButtonText(text="RESUME")),
            Button(label=Button.ButtonText(text="EXIT")),
        ]
        super().__post_init__()


@dataclass(kw_only=True)
class Form(Menu):
    """Wrapped text and an input field, for cursor and text-cache tests."""

    def __post_init__(self):
        self.root_elements = [
            NormalText(text=_PARAGRAPH, is_wrappable=True),
            InputField(size=(96.0, 17.0), value=InputField.InputValueText(text="PLAYER")),
            Button(label=Button.ButtonText(text="RETURN")),
        ]
        super().__post_init__()
