"""
The demo's menus in ``examples/menus.py``, which are the package's worked example.
"""

from enum import Enum
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from menus import Settings, Start  # noqa: E402

from facade import Button, InputField, Selector  # noqa: E402


class Difficulty(Enum):
    EASY = "EASY"
    HARD = "HARD"


def test_start_selects_its_first_button():
    menu = Start()

    assert menu.get_selected_element().label.text == "Start Game"


def test_settings_builds_an_editor_per_uppercase_attribute():
    settings = SimpleNamespace(VOLUME=0.5, LIVES=3, NAME="PLAYER", MUTED=False, DIFFICULTY=Difficulty.EASY, lowercase=1)

    menu = Settings(settings=settings)
    editors = [row.elements[1] for row in menu.root_elements if hasattr(row, "elements")]

    assert [type(e) for e in editors] == [InputField, InputField, InputField, Selector, Selector]


def test_settings_writes_edits_back():
    settings = SimpleNamespace(NAME="PLAYER", DIFFICULTY=Difficulty.EASY)
    menu = Settings(settings=settings)
    name_field, difficulty = [e for e in menu._selectable_elements if not isinstance(e, Button)]

    name_field.open()
    name_field.append("2")
    name_field.close()
    difficulty.open()
    difficulty.next()
    difficulty.close()

    assert settings.NAME == "PLAYER2"
    assert settings.DIFFICULTY is Difficulty.HARD
