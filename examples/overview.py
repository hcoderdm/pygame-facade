"""
overview.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draws without opening a window.
import pygame

from facade import (
    DEFAULT_THEME,
    NATIVE_FONT_SIZE,
    AlignmentType,
    Button,
    Element,
    Gap,
    InputField,
    Interface,
    Menu,
    PrimaryButton,
    ProgressBar,
    Selector,
    Slider,
    Toggle,
)

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "examples" / "assets" / "fonts"
OUTPUT = ROOT / "docs" / "elements.png"

CELL_SIZE = (220, 52)  # Room for 12px of padding, a 22px input and its 3px shadow.
LABEL_PW = 170
HEADER_PH = 64
THEME = DEFAULT_THEME
SHEET_COLOR = THEME.surface_input  # A frame a step darker than the menus inside it.
CAPTION_COLOR = THEME.text_muted
DIFFICULTIES = ("EASY", "NORMAL", "HARD", "NIGHTMARE")


def parse_args() -> argparse.Namespace:
    """Parse the arguments."""
    parser = argparse.ArgumentParser(description="Render every input element in each of its states to one image.")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="")

    args = parser.parse_args()
    check_args(args)
    return args


def check_args(args: argparse.Namespace) -> None:
    """Check the arguments."""
    if args.output.suffix.lower() != ".png":
        raise SystemExit(f"Invalid {args.output=}")


def render_cell(interface: Interface, element: Element, state: str = "idle", part: str = "") -> pygame.Surface:
    """
    ``element`` alone on a menu in ``state``: ``"idle"``, ``"focused"`` by the
    keys, under the ``"pointer"`` at ``part``, or ``"typing"`` into an input
    field.
    """
    # An invisible selectable gap holds the selection when the element should look idle.
    holder = Gap(is_selectable=True, is_visible=False)
    menu = Menu(root_elements=[holder, element], root_padding=(12.0, 12.0), root_alignment=AlignmentType.TOPLEFT)
    if state != "idle":
        menu.select_element_by_id(element.id)
    if state == "pointer":
        menu.set_pointer_leading(True)
        menu.set_hovered(element, part)
    if state == "typing" and isinstance(element, InputField):
        element.open()
        element.append("2")
    interface.clear_stack()
    interface.push_stack(menu)
    surf = interface.render()
    assert surf is not None  # A menu was just pushed.
    return surf.copy()


def changed(element, *steps: str):
    """``element`` after each named method is called once, so it shows its changed colour."""
    for step in steps:
        getattr(element, step)()
    return element


def main() -> int:
    args = parse_args()

    # Set up the interface.
    pygame.init()
    pygame.display.set_mode((1, 1))
    interface = Interface(size=CELL_SIZE, theme=THEME, use_hand_cursor=False)
    interface.fonts.add_dir(str(FONTS))
    font = interface.fonts.get_font("editundo.ttf", NATIVE_FONT_SIZE)
    title_font = interface.fonts.get_font("editundo.ttf", 2 * NATIVE_FONT_SIZE)

    def player() -> InputField:
        return InputField(value=InputField.InputValueText(text="PLAYER"))

    def edited_player() -> InputField:
        field = player()
        field.open()
        field.append("2")
        field.close()
        return field

    # Each row is a name, an optional note, and (element, state, part) per column. None leaves a cell empty.
    rows = [
        ("BUTTON", None, [
            (Button(label=Button.ButtonText(text="START")), "idle", ""),
            (Button(label=Button.ButtonText(text="START")), "focused", ""),
            (Button(label=Button.ButtonText(text="START")), "pointer", "body"),
            None,
        ]),
        ("PRIMARY BUTTON", None, [
            (PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="START")), "idle", ""),
            (PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="START")), "focused", ""),
            (PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="START")), "pointer", "body"),
            None,
        ]),
        ("TOGGLE", None, [
            (Toggle(), "idle", ""), (Toggle(), "focused", ""), (Toggle(), "pointer", "body"),
            (changed(Toggle(), "__call__"), "idle", ""),
        ]),
        ("SELECTOR", None, [
            (Selector(selections=DIFFICULTIES, value=1), "idle", ""),
            (Selector(selections=DIFFICULTIES, value=1), "focused", ""),
            (Selector(selections=DIFFICULTIES, value=1), "pointer", "right"),
            (changed(Selector(selections=DIFFICULTIES, value=1), "next", "next"), "idle", ""),
        ]),
        ("SLIDER", None, [
            (Slider(value=0.6), "idle", ""),
            (Slider(value=0.6), "focused", ""),
            (Slider(value=0.6), "pointer", "right"),
            (changed(Slider(value=0.6), "decrement", "decrement"), "idle", ""),
        ]),
        ("SLIDER ENDS", "AT 0% / AT 100%", [None, (Slider(value=0.0), "focused", ""), (Slider(value=1.0), "pointer", "right"), None]),
        ("INPUT FIELD", None, [
            (player(), "idle", ""), (player(), "focused", ""), (player(), "typing", ""),
            (edited_player(), "idle", ""),
        ]),
        ("PROGRESS BAR", "25% / 60% / 100%", [(ProgressBar(value=value), "idle", "") for value in (0.25, 0.6, 1.0)] + [None]),
    ]
    columns = ("IDLE", "FOCUSED BY KEYS", "UNDER THE POINTER / TYPING", "CHANGED")

    sheet = pygame.Surface((LABEL_PW + CELL_SIZE[0] * len(columns) + 10, HEADER_PH + len(rows) * CELL_SIZE[1]))
    sheet.fill(SHEET_COLOR)
    sheet.blit(title_font.render("ELEMENTS", False, THEME.heading), (16, 10))
    for idx, column in enumerate(columns):
        sheet.blit(font.render(column, False, CAPTION_COLOR), (LABEL_PW + idx * CELL_SIZE[0] + 14, HEADER_PH - 20))
    for row_idx, (name, note, cells) in enumerate(rows):
        row_py = HEADER_PH + row_idx * CELL_SIZE[1]
        sheet.blit(font.render(name, False, THEME.text_normal), (16, row_py + 16))
        if note is not None:
            sheet.blit(font.render(note, False, CAPTION_COLOR), (16, row_py + 30))
        for col_idx, cell in enumerate(cells):
            if cell is not None:
                sheet.blit(render_cell(interface, *cell), (LABEL_PW + col_idx * CELL_SIZE[0], row_py))

    # Save the sheet.
    args.output.parent.mkdir(exist_ok=True)
    pygame.image.save(sheet, args.output)
    pygame.quit()
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
