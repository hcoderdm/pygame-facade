"""
Menus and the menu stack.
"""

from facade import MenuManager
from sample_menus import Overlay, Title, selected_label


def test_selection_moves_between_selectable_elements_and_stops_at_ends():
    menu = Title()
    labels = lambda: selected_label(menu)

    assert labels() == "START"
    menu.move_selected_up()
    assert labels() == "START"
    menu.move_selected_down()
    assert labels() == "OPTIONS"
    for _ in range(10):
        menu.move_selected_down()
    assert labels() == "QUIT"


def test_move_selected_by_wraps_in_reading_order():
    menu = Title()
    labels = lambda: selected_label(menu)

    menu.move_selected_by(-1)
    assert labels() == "QUIT"
    menu.move_selected_by(1)
    assert labels() == "START"


def test_manager_stack_keeps_root_unless_asked():
    manager = MenuManager()
    manager.add_menu(Title())
    manager.add_menu(Overlay())
    manager.push_stack(Title)
    manager.push_stack(Overlay)

    assert manager.in_stack(Title) and manager.in_stack(Overlay)
    assert isinstance(manager.pop_stack(), Overlay)
    assert manager.pop_stack() is None  # The root stays by default
    assert isinstance(manager.pop_stack(keep_root=False), Title)
    assert manager.top_stack() is None
    assert not manager.in_stack(Title)
