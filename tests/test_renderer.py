"""
Renderer output format and caching.
"""

from dataclasses import dataclass
import time

import pygame

from facade import AlignmentType, Button, DebugRenderer, Element, InputField, Interface, Menu, NormalText
from sample_menus import Form, Overlay, Title

SIZE = (800, 600)


def pixels(surface):
    return pygame.image.tobytes(surface, "RGBA")


def counting_recomposes(ui):
    """Wrap the renderer's compose step and return a list counting its calls."""
    calls = []
    compose = ui.renderer._compose_tree
    ui.renderer._compose_tree = lambda *args: calls.append(1) or compose(*args)
    return calls


def test_composing_a_menu_is_not_an_edit():
    ui = Interface(size=SIZE)
    ui.push(Form())
    version = Element._render_version

    ui.render()

    assert Element._render_version == version


def test_creating_elements_elsewhere_keeps_the_cache():
    ui = Interface(size=SIZE)
    ui.push(Overlay())
    first = ui.render()

    NormalText(text="score: 10")  # e.g. a game building its own elements each frame

    assert ui.render() is first


def test_two_interfaces_keep_their_own_caches():
    a, b = Interface(size=SIZE), Interface(size=SIZE)
    a.push(Overlay())
    b.push(Title())
    calls_a, calls_b = counting_recomposes(a), counting_recomposes(b)

    for _ in range(5):
        a.render()
        b.render()

    assert (len(calls_a), len(calls_b)) == (1, 1)


def test_open_input_field_cursor_blinks_on_screen(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    menu = Form()
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
    ui.push(Form())
    cache = ui.renderer._text_cache
    cache.max_bytes = 4 * 1024 * 1024

    for width in range(600, 700):
        ui.resize((width, 600))
        ui.render()

    assert cache.nbytes <= cache.max_bytes


def test_recomposing_gives_identical_pixels():
    ui = Interface(size=SIZE)
    ui.push(Title())
    first = pixels(ui.render())

    Element._render_version += 1  # Force a full recompose with warm caches

    assert pixels(ui.render()) == first


def test_opaque_menu_is_returned_without_per_pixel_alpha():
    ui = Interface(size=SIZE)
    ui.push(Title())

    surface = ui.render()

    assert surface.get_size() == SIZE
    assert not surface.get_flags() & pygame.SRCALPHA
    assert surface.get_at((0, 0)) == pygame.Color("#0C0E14FF")  # Menu's default background


def test_menu_smaller_than_window_keeps_alpha():
    @dataclass(kw_only=True)
    class Panel(Menu):
        root_size: tuple[float, float] = (0.5, 0.5)

    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[NormalText(text="hi")]))

    surface = ui.render()

    assert surface.get_flags() & pygame.SRCALPHA
    assert surface.get_at((SIZE[0] - 1, SIZE[1] - 1)).a == 0


@dataclass(kw_only=True)
class Panel(Menu):
    """A bare menu for the layout rules below."""


def hit_rect_of(ui, element):
    return next(rect for hit, rect in ui.renderer._menu_tree.hit_rects if hit is element)


def test_scrolling_reuses_the_tree():
    ui = Interface(size=(800, 120))
    menu = Panel(root_elements=[NormalText(text=f"line {i}") for i in range(20)])
    ui.push(menu)
    calls = counting_recomposes(ui)
    first = ui.render()

    menu._scroll = 50.0
    scrolled = ui.render()

    assert scrolled is not first
    assert len(calls) == 1


def test_fixed_element_is_hit_where_it_is_aligned():
    marker = NormalText(text="x", is_fixed=True, is_selectable=True, alignment=AlignmentType.BOTTOMRIGHT)
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[marker]))
    ui.render()

    assert hit_rect_of(ui, marker).bottomright == SIZE


def test_offset_moves_the_box():
    def placed(offset):
        button = Button(label=Button.ButtonText(text="GO"), offset=offset)
        ui = Interface(size=SIZE)
        ui.push(Panel(root_elements=[button]))
        ui.render()
        return hit_rect_of(ui, button)

    plain, moved = placed((0.0, 0.0)), placed((10.0, 5.0))

    assert (moved.x, moved.y, moved.size) == (plain.x + 10, plain.y + 5, plain.size)



def debugging(ui, **modes):
    """Wrap the interface's renderer in a ``DebugRenderer`` and return it."""
    debug = DebugRenderer(ui.renderer, **modes)
    ui.renderer = debug
    return debug


def test_debug_renderer_with_no_mode_returns_the_wrapped_output():
    ui = Interface(size=SIZE)
    ui.push(Title())
    debug = debugging(ui)

    assert ui.render() is debug.renderer._menu_tree.output_surf


def test_debug_modes_leave_the_wrapped_output_and_cache_alone():
    ui = Interface(size=SIZE)
    ui.push(Title())
    debug = debugging(ui, use_stats_overlay=True, use_hover_border=True, use_hit_rects=True)
    clean = pixels(debug.renderer.render(ui.top(), SIZE))
    calls = []
    compose = debug.renderer._compose_tree
    debug.renderer._compose_tree = lambda *args: calls.append(1) or compose(*args)

    shown = ui.render()
    ui.render()

    assert pixels(debug.renderer._menu_tree.output_surf) == clean
    assert pixels(shown) != clean
    assert len(calls) == 0


def test_debug_counts_recomposes_not_frames():
    ui = Interface(size=SIZE)
    ui.push(Title())
    debug = debugging(ui)

    for _ in range(3):
        ui.render()
    ui.top().root_elements[1].label.text = "BEGIN"
    ui.render()

    assert (debug._counts["fps"], debug._counts["composes"]) == (4, 2)


def test_tree_records_rects_of_unselectable_elements():
    label = NormalText(text="score")
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[label]))
    ui.render()

    assert any(element is label for element, _ in ui.renderer._menu_tree.element_rects)


def test_hover_border_inverts_only_the_pixels_on_its_edge():
    button = Button(label=Button.ButtonText(text="GO"), background_color="#204060FF")
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[button]))
    debug = debugging(ui, use_hover_border=True)
    plain = debug.renderer.render(ui.top(), SIZE)
    rect = next(rect for hit, rect in debug.renderer._menu_tree.hit_rects if hit is button)
    debug.get_hovered_element = lambda menu: (button, rect)

    outlined = ui.render()

    before, after = plain.get_at(rect.topleft), outlined.get_at(rect.topleft)
    assert (after.r, after.g, after.b, after.a) == (255 - before.r, 255 - before.g, 255 - before.b, 255)
    assert outlined.get_at(rect.center) == plain.get_at(rect.center)


def test_hit_rects_outline_selectable_elements():
    ui = Interface(size=SIZE)
    ui.push(Title())
    debug = debugging(ui, use_hit_rects=True)

    outlined = ui.render()

    rect = debug.renderer._menu_tree.hit_rects[0][1]
    assert outlined.get_at(rect.topleft) == pygame.Color("#00FF80FF")


def test_debug_renderer_hit_tests_like_the_wrapped_one():
    ui = Interface(size=SIZE)
    ui.push(Title())
    ui.render()
    button = ui.top().root_elements[1]
    pos = hit_rect_of(ui, button).center
    debugging(ui)

    assert ui.renderer.select_element_at(ui.top(), pos) is button
