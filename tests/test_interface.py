"""
Interface: events in, GUI surface out.
"""

import pygame
import pytest

from facade import Button, Interface, Pause, Start

SIZE = (800, 600)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1, clicks=1)


def center_of(ui, element):
    """Window position of ``element`` in the last rendered layout."""
    for hit, rect, _depth in ui.renderer._menu_rect_cache:
        if hit is element:
            return rect.center
    raise LookupError(element)


@pytest.fixture
def ui():
    return Interface(size=SIZE, use_hand_cursor=False)


def test_no_menu_means_no_surface_and_no_events_used(ui):
    assert ui.render() is None
    assert ui.handle_event(key(pygame.K_RETURN)) is False
    assert ui.handle_event(click((10, 10))) is False


def test_render_returns_window_sized_transparent_surface(ui):
    ui.push(Pause())

    surface = ui.render()

    assert surface.get_size() == SIZE
    assert surface.get_flags() & pygame.SRCALPHA
    assert surface.get_at((SIZE[0] // 2, SIZE[1] - 1)).a == 0xC0  # Pause's translucent background


def test_render_reuses_surface_until_something_changes(ui):
    menu = Start()
    ui.push(menu)

    first = ui.render()
    assert ui.render() is first

    menu.move_selected_down()
    assert ui.render() is not first


def test_return_key_presses_selected_button(ui):
    pressed = []
    ui.push(Start(on_start=lambda: pressed.append("start")))
    ui.render()

    assert ui.handle_event(key(pygame.K_RETURN)) is True
    assert pressed == ["start"]


def test_clicking_selected_button_presses_it(ui):
    pressed = []
    menu = Start(on_quit=lambda: pressed.append("quit"))
    ui.push(menu)
    ui.render()
    quit_button = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "QUIT")
    position = center_of(ui, quit_button)

    assert ui.handle_event(click(position)) is True  # First click selects
    assert pressed == []
    assert ui.handle_event(click(position)) is True  # Second click presses
    assert pressed == ["quit"]


def test_escape_closes_overlay_but_leaves_root_to_the_game(ui):
    ui.push(Start())
    ui.push(Pause())
    ui.render()

    assert ui.handle_event(key(pygame.K_ESCAPE)) is True
    assert isinstance(ui.top(), Start)
    assert ui.handle_event(key(pygame.K_ESCAPE)) is False
    assert isinstance(ui.top(), Start)


def test_pop_can_close_the_last_menu(ui):
    ui.push(Pause())

    assert isinstance(ui.pop(), Pause)
    assert ui.render() is None


def test_push_unknown_type_raises(ui):
    with pytest.raises(KeyError):
        ui.push(Pause)
