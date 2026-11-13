"""
Interface: events in, GUI surface out.
"""

import pygame
import pytest

from facade import Button, Interface, Menu, Slider
from sample_menus import Overlay, Title

SIZE = (800, 600)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1, clicks=1)


def center_of(ui, element):
    """Window position of ``element`` in the last rendered layout."""
    for hit, rect in ui.renderer._menu_tree.hit_rects:
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
    ui.push(Overlay())

    surface = ui.render()

    assert surface.get_size() == SIZE
    assert surface.get_flags() & pygame.SRCALPHA
    assert surface.get_at((SIZE[0] // 2, SIZE[1] - 1)).a == 0xC0  # Overlay's translucent background


def test_render_reuses_surface_until_something_changes(ui):
    menu = Title()
    ui.push(menu)

    first = ui.render()
    assert ui.render() is first

    menu.move_selected_down()
    assert ui.render() is not first


def test_return_key_presses_selected_button(ui):
    pressed = []
    ui.push(Title(on_start=lambda: pressed.append("start")))
    ui.render()

    assert ui.handle_event(key(pygame.K_RETURN)) is True
    assert pressed == ["start"]


def test_clicking_selected_button_presses_it(ui):
    pressed = []
    menu = Title(on_quit=lambda: pressed.append("quit"))
    ui.push(menu)
    ui.render()
    quit_button = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "QUIT")
    position = center_of(ui, quit_button)

    assert ui.handle_event(click(position)) is True  # First click selects
    assert pressed == []
    assert ui.handle_event(click(position)) is True  # Second click presses
    assert pressed == ["quit"]


def test_escape_closes_overlay_but_leaves_root_to_the_game(ui):
    ui.push(Title())
    ui.push(Overlay())
    ui.render()

    assert ui.handle_event(key(pygame.K_ESCAPE)) is True
    assert isinstance(ui.top(), Title)
    assert ui.handle_event(key(pygame.K_ESCAPE)) is False
    assert isinstance(ui.top(), Title)


def test_pop_can_close_the_last_menu(ui):
    ui.push(Overlay())

    assert isinstance(ui.pop(), Overlay)
    assert ui.render() is None


def test_push_unknown_type_raises(ui):
    with pytest.raises(KeyError):
        ui.push(Overlay)


def test_slider_keys_open_step_and_commit(ui):
    received = []
    slider = Slider(step=0.25, action=lambda value: received.append(value) or True)
    ui.push(Menu(root_elements=[slider]))
    ui.render()

    for k in (pygame.K_RETURN, pygame.K_RIGHT, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN):
        assert ui.handle_event(key(k)) is True

    assert received == [0.5]
    assert not slider.is_open


def test_escape_cancels_open_slider_without_closing_menu(ui):
    slider = Slider(step=0.25)
    ui.push(Title())
    ui.push(Menu(root_elements=[slider]))
    ui.render()

    ui.handle_event(key(pygame.K_RETURN))
    ui.handle_event(key(pygame.K_RIGHT))
    ui.handle_event(key(pygame.K_ESCAPE))

    assert slider.value == 0.0 and not slider.is_open
    assert ui.top().root_elements == [slider]
