"""
overview.py

Renders every input element in each of its states to ``docs/elements.png``,
the overview image in the README. Run it from the repository root after
changing how an element looks:

    python examples/overview.py
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draws without opening a window
import pygame

from facade import (
    COLOR_PALETTE_EDITED,
    COLOR_PALETTE_TEXT,
    NATIVE_FONT_SIZE,
    AlignmentType,
    Button,
    Element,
    Gap,
    InputField,
    Interface,
    Menu,
    ProgressBar,
    Selector,
    Slider,
    Toggle,
)

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "examples" / "assets" / "fonts"
OUTPUT = ROOT / "docs" / "elements.png"

CELL_SIZE = (220, 52)  # Room for 12px of padding, a 22px input and its 3px shadow
LABEL_PW = 170
HEADER_PH = 64
SHEET_COLOR = "#05060AFF"
CAPTION_COLOR = "#6E7896FF"
DIFFICULTIES = ("EASY", "NORMAL", "HARD", "NIGHTMARE")


def render_cell(interface: Interface, element: Element, is_selected: bool) -> pygame.Surface:
    """``element`` alone on a menu, selected or not."""
    # An invisible selectable gap holds the selection when the element should look idle
    holder = Gap(is_selectable=True, is_visible=False)
    menu = Menu(root_elements=[holder, element], root_padding=(12.0, 12.0), root_alignment=AlignmentType.TOPLEFT)
    if is_selected:
        menu.select_element_by_id(element.id)
    interface.clear()
    interface.push(menu)
    surface = interface.render()
    assert surface is not None  # A menu was just pushed
    return surface.copy()


def opened(element, *steps: str):
    """``element`` opened for editing, with each named method called once."""
    element.open()
    for step in steps:
        getattr(element, step)()
    return element


def typed(field: InputField, text: str) -> InputField:
    field.open()
    field.append(text)
    return field


def toggled(toggle: Toggle) -> Toggle:
    toggle()
    return toggle


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    interface = Interface(size=CELL_SIZE, use_hand_cursor=False)
    interface.fonts.add_dir(str(FONTS))
    font = interface.fonts.get_font("editundo.ttf", NATIVE_FONT_SIZE)
    title_font = interface.fonts.get_font("editundo.ttf", 2 * NATIVE_FONT_SIZE)

    # Each row is a name, an optional note, and (element, is_selected) per column; None leaves a cell empty
    rows = [
        ("BUTTON", None, [(Button(label=Button.ButtonText(text="START")), False), (Button(label=Button.ButtonText(text="START")), True), None]),
        ("TOGGLE", None, [(Toggle(), False), (Toggle(), True), (toggled(Toggle()), True)]),
        ("SELECTOR", None, [
            (Selector(selections=DIFFICULTIES, value=1), False),
            (Selector(selections=DIFFICULTIES, value=1), True),
            (opened(Selector(selections=DIFFICULTIES, value=1), "next", "next"), True),
        ]),
        ("SLIDER", None, [
            (Slider(value=0.6), False),
            (Slider(value=0.6), True),
            (opened(Slider(value=0.6), "decrement", "decrement"), True),
        ]),
        ("SLIDER ENDS", "AT 0% / AT 100%", [(Slider(value=0.0), True), (Slider(value=1.0), True), None]),
        ("INPUT FIELD", None, [
            (InputField(value=InputField.InputValueText(text="PLAYER")), False),
            (InputField(value=InputField.InputValueText(text="PLAYER")), True),
            (typed(InputField(value=InputField.InputValueText(text="PLAYER")), "2"), True),
        ]),
        ("PROGRESS BAR", "25% / 60% / 100%", [(ProgressBar(value=value), False) for value in (0.25, 0.6, 1.0)]),
    ]
    columns = ("IDLE", "SELECTED", "OPEN / CHANGED")

    sheet = pygame.Surface((LABEL_PW + CELL_SIZE[0] * len(columns) + 10, HEADER_PH + len(rows) * CELL_SIZE[1]))
    sheet.fill(SHEET_COLOR)
    sheet.blit(title_font.render("ELEMENTS", False, COLOR_PALETTE_EDITED), (16, 10))
    for idx, column in enumerate(columns):
        sheet.blit(font.render(column, False, CAPTION_COLOR), (LABEL_PW + idx * CELL_SIZE[0] + 14, HEADER_PH - 20))
    for row_idx, (name, note, cells) in enumerate(rows):
        row_py = HEADER_PH + row_idx * CELL_SIZE[1]
        sheet.blit(font.render(name, False, COLOR_PALETTE_TEXT), (16, row_py + 16))
        if note is not None:
            sheet.blit(font.render(note, False, CAPTION_COLOR), (16, row_py + 30))
        for col_idx, cell in enumerate(cells):
            if cell is not None:
                sheet.blit(render_cell(interface, *cell), (LABEL_PW + col_idx * CELL_SIZE[0], row_py))

    OUTPUT.parent.mkdir(exist_ok=True)
    pygame.image.save(sheet, OUTPUT)
    pygame.quit()
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
