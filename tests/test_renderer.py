"""
Renderer output format and caching.
"""

import time
from types import SimpleNamespace

import pygame

from facade import About, Element, InputField, Interface, NormalText, Pause, Settings, Start

SIZE = (800, 600)


def pixels(surface):
    return pygame.image.tobytes(surface, "RGBA")


def counting_recomposes(ui):
    """Wrap the renderer's compose step and return a list counting its calls."""
    calls = []
    compose = ui.renderer._compose_menu_tree
    ui.renderer._compose_menu_tree = lambda *args: calls.append(1) or compose(*args)
    return calls


def test_composing_a_menu_is_not_an_edit():
    ui = Interface(size=SIZE)
    ui.push(Settings(settings=SimpleNamespace(VOLUME=1.0, MUTE=False)))
    version = Element._iterative_version

    ui.render()

    assert Element._iterative_version == version


def test_creating_elements_elsewhere_keeps_the_cache():
    ui = Interface(size=SIZE)
    ui.push(Pause())
    first = ui.render()

    NormalText(text="score: 10")  # e.g. a game building its own elements each frame

    assert ui.render() is first


def test_two_interfaces_keep_their_own_caches():
    a, b = Interface(size=SIZE), Interface(size=SIZE)
    a.push(Pause())
    b.push(Start())
    calls_a, calls_b = counting_recomposes(a), counting_recomposes(b)

    for _ in range(5):
        a.render()
        b.render()

    assert (len(calls_a), len(calls_b)) == (1, 1)


def test_open_input_field_cursor_blinks_on_screen(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    menu = Settings(settings=SimpleNamespace(NAME="PLAYER"))
    field = next(e for e in menu._selectable_elements if isinstance(e, InputField))
    ui = Interface(size=SIZE)
    ui.push(menu)
    menu.select_element_by_id(field.id)
    field.open()

    shown = pixels(ui.render())
    assert ui.render() is ui.render()  # Steady while the glyph is unchanged
    now[0] += InputField._cursor_period
    hidden = pixels(ui.render())

    assert shown != hidden


def test_text_cache_is_bounded_while_resizing():
    ui = Interface(size=SIZE)
    ui.push(About())
    cache = ui.renderer._text_cache
    cache.max_bytes = 4 * 1024 * 1024

    for width in range(600, 700):
        ui.resize((width, 600))
        ui.render()

    assert cache.nbytes <= cache.max_bytes
