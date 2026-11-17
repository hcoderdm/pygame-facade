"""
test_examples.py
"""

from enum import Enum
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from menus import Settings, Start  # noqa: E402
from sample_menus import selected_label  # noqa: E402

from facade import Button, HorizontalDivision, InputField, SectionHeader, Selector, Slider, Toggle, VerticalDivision  # noqa: E402


class Difficulty(Enum):
    EASY = "EASY"
    HARD = "HARD"


def boxes_of(menu):
    """Each box of a Settings menu as (section title or None, its label-and-editor rows)."""
    boxes = []
    for element in menu.root_elements:
        if isinstance(element, VerticalDivision):
            title = next((e.label.text for e in element.elements if isinstance(e, SectionHeader)), None)
            boxes.append((title, [e for e in element.elements if isinstance(e, HorizontalDivision)]))
    return boxes


def test_261111232812_56c4521b():
    # Settings builds an editor per uppercase attribute.
    settings = SimpleNamespace(VOLUME=0.5, SPEED=2.5, LIVES=3, NAME="PLAYER", MUTED=False, DIFFICULTY=Difficulty.EASY, lowercase=1)

    menu = Settings(settings=settings)
    editors = [row.elements[1] for _, rows in boxes_of(menu) for row in rows]

    assert [type(e) for e in editors] == [Slider, InputField, InputField, InputField, Toggle, Selector]


def test_261111232812_fee7ca1f():
    # Settings writes edits back.
    settings = SimpleNamespace(NAME="PLAYER", DIFFICULTY=Difficulty.EASY)
    menu = Settings(settings=settings)
    name_field, difficulty = [e for e in menu._selectable_elements if not isinstance(e, Button)]
    assert isinstance(name_field, InputField) and isinstance(difficulty, Selector)

    name_field.open()
    name_field.append("2")
    name_field.close()
    difficulty.next()

    assert settings.NAME == "PLAYER2"
    assert settings.DIFFICULTY is Difficulty.HARD


def test_261112223905_3e5747fb():
    # Start selects its first button.
    menu = Start()

    assert selected_label(menu) == "PLAY"


def test_261113152542_da4acce3():
    # Settings slider writes edits back.
    settings = SimpleNamespace(VOLUME=0.5)
    (volume,) = [e for e in Settings(settings=settings)._selectable_elements if not isinstance(e, Button)]
    assert isinstance(volume, Slider)

    volume.increment()

    assert settings.VOLUME == 0.6


def test_261113205941_fada16d9():
    # Settings without sections share one untitled box.
    menu = Settings(settings=SimpleNamespace(A=1, B=2))

    assert [(title, len(rows)) for title, rows in boxes_of(menu)] == [(None, 2)]


def test_261113205941_b198f055():
    # Settings sections box their names in order and the rest last.
    settings = SimpleNamespace(A=1, B=2, C=3, D=4)

    menu = Settings(settings=settings, sections={"Second": ["C", "A"], "First": ["B"], "Empty": ["MISSING"]})
    boxes = [(title, [row.elements[0].text for row in rows]) for title, rows in boxes_of(menu)]

    assert boxes == [("Second", ["C", "A"]), ("First", ["B"]), ("Other", ["D"])]


def test_261116225126_e2724a86():
    # Settings gave an uppercase constant with no editor, such as the sections dict, a broken input field.
    settings = SimpleNamespace(VOLUME=0.5, SECTIONS={"Audio": ["VOLUME"]})

    menu = Settings(settings=settings, sections=settings.SECTIONS)

    assert [(title, [row.elements[0].text for row in rows]) for title, rows in boxes_of(menu)] == [("Audio", ["VOLUME"])]
