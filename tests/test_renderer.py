"""
Renderer output format and caching.
"""

from dataclasses import dataclass
from pathlib import Path
import time

import pygame

from facade import DEFAULT_THEME, AlignmentType, Button, DebugRenderer, Element, Gap, InputField, Interface, Menu, NormalText, PrimaryButton, ProgressBar, Selector, Slider, Toggle
from sample_menus import Form, Overlay, Title

SIZE = (800, 600)
FONTS = Path(__file__).resolve().parents[1] / "examples" / "assets" / "fonts"


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
    assert surface.get_at((0, 0)) == drawn(DEFAULT_THEME.background)  # Menu's default background


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


def drawn(color):
    """The pixel colour a colour field draws as under the default theme, which these tests use."""
    return pygame.Color(DEFAULT_THEME.get_rgba(color))


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


def runs_of(surface, py, px_range, colors):
    """Lengths of consecutive runs of each colour along row ``py``, as (colour, length) pairs."""
    runs = []
    for px in px_range:
        color = surface.get_at((px, py))
        key = next((name for name, value in colors.items() if color == pygame.Color(value)), None)
        if runs and runs[-1][0] == key:
            runs[-1][1] += 1
        else:
            runs.append([key, 1])
    return [(key, length) for key, length in runs if key is not None]


def test_progress_bar_fills_its_fraction_of_the_segments():
    bar = ProgressBar(value=0.5, use_number=False, fill_color="#FF0000FF", empty_color="#0000FFFF", is_selectable=True)
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[bar]))
    surface = ui.render()
    track = hit_rect_of(ui, bar)

    runs = runs_of(surface, track.centery, range(track.left, track.right), {"fill": "#FF0000FF", "empty": "#0000FFFF"})

    assert [key for key, _ in runs] == ["fill"] * 5 + ["empty"] * 5
    assert len({length for _, length in runs}) == 1  # Every segment the same width


def test_text_is_centred_on_its_ink():
    # The pixel font has blank rows above its capitals and spacing after each glyph, which layout must ignore
    button = Button(label=Button.ButtonText(text="START", text_color="#FF0000FF"))
    ui = Interface(size=SIZE)
    ui.fonts.add_dir(str(FONTS))
    ui.push(Panel(root_elements=[Gap(is_selectable=True), button]))  # The gap holds the selection, so the label keeps its colour
    surface = ui.render()
    box = hit_rect_of(ui, button).inflate(-2, -2)  # Inside the border

    ink = [(px, py) for px in range(box.left, box.right) for py in range(box.top, box.bottom) if surface.get_at((px, py)) == pygame.Color("#FF0000FF")]
    ink_xs, ink_ys = [px for px, _ in ink], [py for _, py in ink]

    assert min(ink_ys) - box.top == box.bottom - 1 - max(ink_ys)
    assert min(ink_xs) - box.left == box.right - 1 - max(ink_xs)


def test_selected_slider_outlines_only_its_bar():
    slider = Slider()
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[slider]))
    surface = ui.render()
    rect = hit_rect_of(ui, slider)

    assert surface.get_at((rect.left, rect.centery)) == drawn(slider.selected_border_color)
    assert surface.get_at((rect.right - 1, rect.centery)) == drawn(slider.border_color)


def test_clicks_on_a_bar_reach_the_slider():
    slider = Slider()
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[slider]))
    ui.render()
    rect = hit_rect_of(ui, slider)

    assert ui.renderer.find_elements_at(ui.top(), rect.center)[0] is slider


def test_toggle_fills_the_half_for_its_value():
    toggle = Toggle(value=True)
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[Gap(is_selectable=True), toggle]))  # The gap holds the selection
    surface = ui.render()
    rect = hit_rect_of(ui, toggle)
    inset = 1 + int(toggle.padding[0])

    assert surface.get_at((rect.right - 1 - inset, rect.centery)) == drawn(toggle.fill_color)
    assert surface.get_at((rect.left + inset, rect.centery)) == drawn(toggle.background_color)


def test_changing_progress_bar_value_redraws():
    bar = ProgressBar(value=0.25)
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[bar]))
    first = ui.render()

    bar.value = 0.75

    assert ui.render() is not first


def test_rendering_a_slider_is_not_an_edit():
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[Slider()]))
    version = Element._render_version

    ui.render()

    assert Element._render_version == version


def test_stepping_a_slider_redraws():
    slider = Slider()
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[slider]))
    first = ui.render()

    slider.increment()

    assert ui.render() is not first


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


def test_border_without_background_leaves_the_inside_clear():
    outline = Gap(size=(40.0, 20.0), border_thickness=2, border_color="#FF0000FF", is_selectable=True)
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[outline]))
    surface = ui.render()
    rect = hit_rect_of(ui, outline)

    assert surface.get_at(rect.topleft) == pygame.Color("#FF0000FF")
    assert surface.get_at((rect.left + 1, rect.centery)) == pygame.Color("#FF0000FF")
    assert surface.get_at(rect.center) == drawn(Panel().root_background_color)


def count_pixels(surface, rect, color):
    target = drawn(color)
    return sum(surface.get_at((px, py)) == target for px in range(rect.left, rect.right) for py in range(rect.top, rect.bottom))


def test_pointer_lights_only_the_arrow_on_its_side():
    selector = Selector(selections=("A", "B", "C"), value=1)
    ui = Interface(size=SIZE)
    menu = Panel(root_elements=[selector])
    ui.push(menu)
    keys_surface = ui.render()
    rect = hit_rect_of(ui, selector)
    left_zone = pygame.Rect(rect.left + 1, rect.top + 1, 20, rect.height - 2)
    right_zone = pygame.Rect(rect.right - 21, rect.top + 1, 20, rect.height - 2)
    assert count_pixels(keys_surface, left_zone, selector.selected_arrow_color) > 0  # The keys light both arrows

    menu.set_pointer_leading(True)
    menu.set_hovered(selector, "right")
    pointer_surface = ui.render()

    assert count_pixels(pointer_surface, left_zone, selector.selected_arrow_color) == 0
    assert count_pixels(pointer_surface, right_zone, selector.selected_arrow_color) > 0


def test_focused_toggle_shows_the_other_option_in_the_accent_colour():
    toggle = Toggle()
    ui = Interface(size=SIZE)
    menu = Panel(root_elements=[toggle])
    ui.push(menu)
    lit = ui.render()
    rect = hit_rect_of(ui, toggle)
    true_half = pygame.Rect(rect.centerx, rect.top + 4, rect.width // 2 - 4, rect.height - 8)
    assert count_pixels(lit, true_half, toggle.selected_text_color) > 0

    menu.set_pointer_leading(True)  # With the pointer over nothing
    unlit = ui.render()

    assert count_pixels(unlit, true_half, toggle.selected_text_color) == 0


def test_holding_the_pointer_down_changes_nothing_on_screen():
    button = Button(label=Button.ButtonText(text="GO"))
    ui = Interface(size=SIZE)
    menu = Panel(root_elements=[button])
    ui.push(menu)
    first = ui.render()

    menu.set_pressed_part(button, "body")

    assert ui.render() is first


def test_pointer_over_nothing_lights_nothing():
    button = Button(label=Button.ButtonText(text="GO"))
    ui = Interface(size=SIZE)
    menu = Panel(root_elements=[button])
    ui.push(menu)
    menu.set_pointer_leading(True)
    surface = ui.render()

    assert surface.get_at(hit_rect_of(ui, button).topleft) == drawn(button.border_color)


def test_hover_redraws_only_when_it_changes():
    selector = Selector(selections=("A", "B"))
    ui = Interface(size=SIZE)
    menu = Panel(root_elements=[selector])
    ui.push(menu)
    menu.set_pointer_leading(True)
    menu.set_hovered(selector, "left")
    first = ui.render()

    menu.set_hovered(selector, "left")
    assert ui.render() is first
    menu.set_hovered(selector, "right")
    assert ui.render() is not first


def test_cursor_in_an_empty_field_sits_on_the_hint_without_moving_it(monkeypatch):
    field = InputField(value=InputField.InputValueText(text=""), hint=InputField.InputHintText(text="[ESC]"))
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[field]))
    ui.render()

    def text_rect(text):
        return next(rect for drawn, rect in ui.renderer._menu_tree.element_rects if isinstance(drawn, NormalText) and drawn.text == text)

    closed_hint = text_rect("[ESC]")
    monkeypatch.setattr(time, "monotonic", lambda: 0.0)
    field.open()  # The cursor shows at once after opening
    ui.render()

    assert text_rect("[ESC]").topleft == closed_hint.topleft
    assert text_rect("_").topleft == closed_hint.topleft

def bar_margins(surface, box, color):
    """Gaps between the inside of a border and the block of ``color`` within it, as left, right, top, bottom."""
    xs = [px for px in range(box.left, box.right) if surface.get_at((px, box.centery)) == color]
    ys = [py for py in range(box.top, box.bottom) if surface.get_at((box.centerx - 40, py)) == color]
    return min(xs) - box.left, box.right - 1 - max(xs), min(ys) - box.top, box.bottom - 1 - max(ys)


def test_primary_button_bar_has_an_even_gap():
    button = PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="GO"))
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[Gap(is_selectable=True), button]))  # The gap holds the selection
    surface = ui.render()
    box = hit_rect_of(ui, button).inflate(-2, -2)  # Inside the border

    assert bar_margins(surface, box, drawn(button.fill_color)) == (3, 3, 3, 3)
    assert surface.get_at(box.topleft) == drawn(button.background_color)


def test_lit_primary_button_lights_its_bar_and_border():
    button = PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="GO"))
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[button]))
    surface = ui.render()
    rect = hit_rect_of(ui, button)

    assert surface.get_at(rect.topleft) == drawn(button.selected_border_color)
    assert bar_margins(surface, rect.inflate(-2, -2), drawn(button.selected_fill_color)) == (3, 3, 3, 3)

