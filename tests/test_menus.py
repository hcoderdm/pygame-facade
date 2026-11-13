"""
Menus and the menu stack.
"""

from enum import Enum
from types import SimpleNamespace

from facade import Button, InputField, MenuManager, Pause, Selector, Settings, Start


class Difficulty(Enum):
    EASY = "EASY"
    HARD = "HARD"


def test_selection_moves_between_selectable_elements_and_stops_at_ends():
    menu = Start()
    labels = lambda: menu.get_selected_element().label.text

    assert labels() == "Start Game"
    menu.move_selected_up()
    assert labels() == "Start Game"
    menu.move_selected_down()
    assert labels() == "SETTINGS"
    for _ in range(10):
        menu.move_selected_down()
    assert labels() == "QUIT"


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


def test_manager_stack_keeps_root_unless_asked():
    manager = MenuManager()
    manager.add_menu(Start())
    manager.add_menu(Pause())
    manager.push_stack(Start)
    manager.push_stack(Pause)

    assert manager.in_stack(Start) and manager.in_stack(Pause)
    assert isinstance(manager.pop_stack(), Pause)
    assert manager.pop_stack() is None  # The root stays by default
    assert isinstance(manager.pop_stack(keep_root=False), Start)
    assert manager.top_stack() is None
    assert not manager.in_stack(Start)
