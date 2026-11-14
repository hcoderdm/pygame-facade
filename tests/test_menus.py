"""
test_menus.py
"""

from facade import MenuManager
from sample_menus import Overlay, Title, selected_label


def test_261111232812_863427a4():
    # Selection moves between selectable elements and stops at ends.
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


def test_261111232812_c3f63cec():
    # Manager stack keeps root unless asked.
    manager = MenuManager()
    manager.add_menu(Title())
    manager.add_menu(Overlay())
    manager.push_stack(Title)
    manager.push_stack(Overlay)

    assert manager.in_stack(Title) and manager.in_stack(Overlay)
    assert isinstance(manager.pop_stack(), Overlay)
    assert manager.pop_stack() is None  # The root stays by default.
    assert isinstance(manager.pop_stack(keep_root=False), Title)
    assert manager.top_stack() is None
    assert not manager.in_stack(Title)


def test_261113211043_7eff7b42():
    # Move selected by wraps in reading order.
    menu = Title()
    labels = lambda: selected_label(menu)

    menu.move_selected_by(-1)
    assert labels() == "QUIT"
    menu.move_selected_by(1)
    assert labels() == "START"
