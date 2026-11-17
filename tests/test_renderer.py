"""
test_renderer.py
"""

from dataclasses import dataclass
from pathlib import Path
import time

import pygame

from facade import DEFAULT_THEME, AlignmentType, Button, ColorSwatch, DebugRenderer, Element, Gap, HorizontalDivision, InputField, Interface, KeyBinding, Menu, MenuRenderer, NormalText, PrimaryButton, ProgressBar, Selector, Slider, ThemeColorType, Toggle
from sample_menus import Form, Overlay, Title

SIZE = (800, 600)
FONTS = Path(__file__).resolve().parents[1] / "examples" / "assets" / "fonts"


def pixels(surf):
    return pygame.image.tobytes(surf, "RGBA")


def counting_recomposes(interface):
    """Wrap the renderer's compose step and return a list counting its calls."""
    calls = []
    compose = interface.renderer._compose_tree
    interface.renderer._compose_tree = lambda menu, size: calls.append(1) or compose(menu, size)
    return calls


@dataclass(kw_only=True)
class Panel(Menu):
    """A bare menu for the layout rules below."""


def drawn(color):
    """The pixel colour a colour field draws as under the default theme, which these tests use."""
    return pygame.Color(DEFAULT_THEME.get_rgba(color))


def tree_of(renderer: MenuRenderer | DebugRenderer):
    """The tree ``renderer`` last composed, which exists once it has rendered."""
    tree = renderer._menu_tree
    assert tree is not None
    return tree


def hit_rect_of(interface, element):
    return next(rect for hit, rect in tree_of(interface.renderer).hit_rects if hit is element)


def runs_of(surf, py, px_range, colors):
    """Lengths of consecutive runs of each colour along row ``py``, as (colour, length) pairs."""
    runs = []
    for px in px_range:
        color = surf.get_at((px, py))
        key = next((name for name, value in colors.items() if color == pygame.Color(value)), None)
        if runs and runs[-1][0] == key:
            runs[-1][1] += 1
        else:
            runs.append([key, 1])
    return [(key, length) for key, length in runs if key is not None]


def debugging(interface, **modes):
    """Wrap the interface's renderer in a ``DebugRenderer`` and return it."""
    debug = DebugRenderer(interface.renderer, **modes)
    interface.renderer = debug
    return debug


def count_pixels(surf, rect, color):
    target = drawn(color)
    return sum(surf.get_at((px, py)) == target for px in range(rect.left, rect.right) for py in range(rect.top, rect.bottom))


def bar_margins(surf, box, color):
    """Gaps between the inside of a border and the block of ``color`` within it, as left, right, top, bottom."""
    xs = [px for px in range(box.left, box.right) if surf.get_at((px, box.centery)) == color]
    ys = [py for py in range(box.top, box.bottom) if surf.get_at((box.centerx - 40, py)) == color]
    return min(xs) - box.left, box.right - 1 - max(xs), min(ys) - box.top, box.bottom - 1 - max(ys)


def test_261112003834_6667b906():
    # Composing a menu is not an edit.
    interface = Interface(size=SIZE)
    interface.push_stack(Form())
    version = Element._render_version

    interface.render()

    assert Element._render_version == version


def test_261112003834_cd7c113e():
    # Creating elements elsewhere keeps the cache.
    interface = Interface(size=SIZE)
    interface.push_stack(Overlay())
    first = interface.render()

    NormalText(text="score: 10")  # e.g. a game building its own elements each frame.

    assert interface.render() is first


def test_261112003834_3972aaf3():
    # Two interfaces keep their own caches.
    a, b = Interface(size=SIZE), Interface(size=SIZE)
    a.push_stack(Overlay())
    b.push_stack(Title())
    calls_a, calls_b = counting_recomposes(a), counting_recomposes(b)

    for _ in range(5):
        a.render()
        b.render()

    assert (len(calls_a), len(calls_b)) == (1, 1)


def test_261112003852_a9f9daf2(monkeypatch):
    # Open input field cursor blinks on screen.
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    menu = Form()
    field = next(e for e in menu._selectable_elements if isinstance(e, InputField))
    interface = Interface(size=SIZE)
    interface.push_stack(menu)
    menu.select_element_by_id(field.id)
    field.open()

    shown = pixels(interface.render())
    assert interface.render() is interface.render()  # Steady while the glyph is unchanged.
    now[0] += InputField._cursor_period
    hidden = pixels(interface.render())

    assert shown != hidden


def test_261112003907_08d86fbc():
    # Text cache is bounded while resizing.
    interface = Interface(size=SIZE)
    interface.push_stack(Form())
    cache = interface.renderer._text_cache
    cache.max_bytes = 4 * 1024 * 1024

    for width in range(600, 700):
        interface.resize((width, 600))
        interface.render()

    assert cache.nbytes <= cache.max_bytes


def test_261112003947_48b42455():
    # Recomposing gives identical pixels.
    interface = Interface(size=SIZE)
    interface.push_stack(Title())
    first = pixels(interface.render())

    Element._render_version += 1  # Force a full recompose with warm caches.

    assert pixels(interface.render()) == first


def test_261112004005_f3debe1d():
    # Opaque menu is returned without per pixel alpha.
    interface = Interface(size=SIZE)
    interface.push_stack(Title())

    surf = interface.render()
    assert surf is not None

    assert surf.get_size() == SIZE
    assert not surf.get_flags() & pygame.SRCALPHA
    assert surf.get_at((0, 0)) == drawn(DEFAULT_THEME.background)  # Menu's default background.


def test_261112004005_7aabfa73():
    @dataclass(kw_only=True)
    # Menu smaller than window keeps alpha.
    class Panel(Menu):
        root_size: tuple[float, float] = (0.5, 0.5)

    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[NormalText(text="hi")]))

    surf = interface.render()
    assert surf is not None

    assert surf.get_flags() & pygame.SRCALPHA
    assert surf.get_at((SIZE[0] - 1, SIZE[1] - 1)).a == 0


def test_261113000952_f5cfefd6():
    # Scrolling reuses the tree.
    interface = Interface(size=(800, 120))
    menu = Panel(root_elements=[NormalText(text=f"line {i}") for i in range(20)])
    interface.push_stack(menu)
    calls = counting_recomposes(interface)
    first = interface.render()

    menu._scroll = 50.0
    scrolled = interface.render()

    assert scrolled is not first
    assert len(calls) == 1


def test_261113000952_7c5ab7f9():
    # Fixed element is hit where it is aligned.
    marker = NormalText(text="x", is_fixed=True, is_selectable=True, alignment=AlignmentType.BOTTOMRIGHT)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[marker]))
    interface.render()

    assert hit_rect_of(interface, marker).bottomright == SIZE


def test_261113000952_42a63b53():
    # Offset moves the box.
    def placed(offset):
        button = Button(label=Button.ButtonText(text="GO"), offset=offset)
        interface = Interface(size=SIZE)
        interface.push_stack(Panel(root_elements=[button]))
        interface.render()
        return hit_rect_of(interface, button)

    plain, moved = placed((0.0, 0.0)), placed((10.0, 5.0))

    assert (moved.x, moved.y, moved.size) == (plain.x + 10, plain.y + 5, plain.size)


def test_261113150544_46856ca9():
    # Debug renderer with no mode returns the wrapped output.
    interface = Interface(size=SIZE)
    interface.push_stack(Title())
    debug = debugging(interface)

    assert interface.render() is tree_of(debug.renderer).output_surf


def test_261113150544_2770d620():
    # Debug modes leave the wrapped output and cache alone.
    interface = Interface(size=SIZE)
    menu = Title()
    interface.push_stack(menu)
    debug = debugging(interface, use_stats_overlay=True, use_hover_border=True, use_hit_rects=True)
    clean = pixels(debug.renderer.render(menu, SIZE))
    calls = []
    compose = debug.renderer._compose_tree
    debug.renderer._compose_tree = lambda menu, size: calls.append(1) or compose(menu, size)

    shown = interface.render()
    interface.render()

    assert pixels(tree_of(debug.renderer).output_surf) == clean
    assert pixels(shown) != clean
    assert len(calls) == 0


def test_261113150544_fd34f2cb():
    # Debug counts recomposes not frames.
    interface = Interface(size=SIZE)
    menu = Title()
    interface.push_stack(menu)
    debug = debugging(interface)

    for _ in range(3):
        interface.render()
    start = menu.root_elements[1]
    assert isinstance(start, Button)
    start.label.text = "BEGIN"
    interface.render()

    assert (debug._counts["fps"], debug._counts["composes"]) == (4, 2)


def test_261113150544_68228258():
    # Tree records rects of unselectable elements.
    label = NormalText(text="score")
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[label]))
    interface.render()

    assert any(element is label for element, _ in tree_of(interface.renderer).element_rects)


def test_261113150544_ea1b5856():
    # Hover border inverts only the pixels on its edge.
    button = Button(label=Button.ButtonText(text="GO"), background_color="#204060FF")
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[button])
    interface.push_stack(menu)
    debug = debugging(interface, use_hover_border=True)
    plain = debug.renderer.render(menu, SIZE)
    rect = next(rect for hit, rect in tree_of(debug.renderer).hit_rects if hit is button)
    debug.get_hovered_element = lambda menu: (button, rect)

    outlined = interface.render()
    assert outlined is not None

    before, after = plain.get_at(rect.topleft), outlined.get_at(rect.topleft)
    assert (after.r, after.g, after.b, after.a) == (255 - before.r, 255 - before.g, 255 - before.b, 255)
    assert outlined.get_at(rect.center) == plain.get_at(rect.center)


def test_261113150544_e496af44():
    # Hit rects outline selectable elements.
    interface = Interface(size=SIZE)
    interface.push_stack(Title())
    debug = debugging(interface, use_hit_rects=True)

    outlined = interface.render()
    assert outlined is not None

    rect = tree_of(debug.renderer).hit_rects[0][1]
    assert outlined.get_at(rect.topleft) == pygame.Color("#00FF80FF")


def test_261113150544_4a86d38f():
    # Debug renderer hit tests like the wrapped one.
    interface = Interface(size=SIZE)
    menu = Title()
    interface.push_stack(menu)
    interface.render()
    button = menu.root_elements[1]
    pos = hit_rect_of(interface, button).center
    debugging(interface)

    assert interface.renderer.select_element_at(menu, pos) is button


def test_261113152542_8825a4b5():
    # Progress bar fills its fraction of the segments.
    bar = ProgressBar(value=0.5, use_number=False, fill_color="#FF0000FF", empty_color="#0000FFFF", is_selectable=True)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[bar]))
    surf = interface.render()
    track = hit_rect_of(interface, bar)

    runs = runs_of(surf, track.centery, range(track.left, track.right), {"fill": "#FF0000FF", "empty": "#0000FFFF"})

    assert [key for key, _ in runs] == ["fill"] * 5 + ["empty"] * 5
    assert len({length for _, length in runs}) == 1  # Every segment the same width.


def test_261113152542_c9682c7c():
    # The pixel font has blank rows above its capitals and spacing after each glyph, which layout must ignore.
    # Text is centred on its ink.
    button = Button(label=Button.ButtonText(text="START", text_color="#FF0000FF"))
    interface = Interface(size=SIZE)
    interface.fonts.add_dir(str(FONTS))
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), button]))  # The gap holds the selection, so the label keeps its colour.
    surf = interface.render()
    assert surf is not None
    box = hit_rect_of(interface, button).inflate(-2, -2)  # Inside the border.

    ink = [(px, py) for px in range(box.left, box.right) for py in range(box.top, box.bottom) if surf.get_at((px, py)) == pygame.Color("#FF0000FF")]
    ink_xs, ink_ys = [px for px, _ in ink], [py for _, py in ink]

    assert min(ink_ys) - box.top == box.bottom - 1 - max(ink_ys)
    assert min(ink_xs) - box.left == box.right - 1 - max(ink_xs)


def test_261113152542_8fc3583e():
    # Selected slider outlines only its bar.
    slider = Slider()
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[slider]))
    surf = interface.render()
    assert surf is not None
    rect = hit_rect_of(interface, slider)

    assert surf.get_at((rect.left, rect.centery)) == drawn(slider.selected_border_color)
    assert surf.get_at((rect.right - 1, rect.centery)) == drawn(slider.border_color)


def test_261113152542_275fd916():
    # Clicks on a bar reach the slider.
    slider = Slider()
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[slider])
    interface.push_stack(menu)
    interface.render()
    rect = hit_rect_of(interface, slider)

    assert interface.renderer.find_elements_at(menu, rect.center)[0] is slider


def test_261113152542_b124fd8c():
    # Toggle fills the half for its value.
    toggle = Toggle(value=True)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), toggle]))  # The gap holds the selection.
    surf = interface.render()
    assert surf is not None
    rect = hit_rect_of(interface, toggle)
    inset = 1 + int(toggle.padding[0])

    assert surf.get_at((rect.right - 1 - inset, rect.centery)) == drawn(toggle.fill_color)
    assert surf.get_at((rect.left + inset, rect.centery)) == drawn(toggle.background_color)


def test_261113152542_24e059ae():
    # Changing progress bar value redraws.
    bar = ProgressBar(value=0.25)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[bar]))
    first = interface.render()

    bar.value = 0.75

    assert interface.render() is not first


def test_261113152542_71c4a28f():
    # Rendering a slider is not an edit.
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Slider()]))
    version = Element._render_version

    interface.render()

    assert Element._render_version == version


def test_261113202738_75850dfd():
    # Border without background leaves the inside clear.
    outline = Gap(size=(40.0, 20.0), border_thickness=2, border_color="#FF0000FF", is_selectable=True)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[outline]))
    surf = interface.render()
    assert surf is not None
    rect = hit_rect_of(interface, outline)

    assert surf.get_at(rect.topleft) == pygame.Color("#FF0000FF")
    assert surf.get_at((rect.left + 1, rect.centery)) == pygame.Color("#FF0000FF")
    assert surf.get_at(rect.center) == drawn(Panel().root_background_color)


def test_261113211043_d198a61e():
    # Stepping a slider redraws.
    slider = Slider()
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[slider]))
    first = interface.render()

    slider.increment()

    assert interface.render() is not first


def test_261113211043_c077af5d():
    # Pointer lights only the arrow on its side.
    selector = Selector(selections=("A", "B", "C"), value=1)
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[selector])
    interface.push_stack(menu)
    keys_surf = interface.render()
    rect = hit_rect_of(interface, selector)
    left_zone = pygame.Rect(rect.left + 1, rect.top + 1, 20, rect.height - 2)
    box_right = rect.right - selector.box_gap_pw - selector.number_pw  # The selector box ends where its number box begins.
    right_zone = pygame.Rect(box_right - 21, rect.top + 1, 20, rect.height - 2)
    assert count_pixels(keys_surf, left_zone, selector.selected_arrow_color) > 0  # The keys light both arrows.

    menu.set_pointer_leading(True)
    menu.set_hovered(selector, "right")
    pointer_surf = interface.render()

    assert count_pixels(pointer_surf, left_zone, selector.selected_arrow_color) == 0
    assert count_pixels(pointer_surf, right_zone, selector.selected_arrow_color) > 0


def test_261113211043_695a97e9():
    # Focused toggle shows the other option in the accent colour.
    toggle = Toggle()
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[toggle])
    interface.push_stack(menu)
    lit = interface.render()
    rect = hit_rect_of(interface, toggle)
    true_half = pygame.Rect(rect.centerx, rect.top + 4, rect.width // 2 - 4, rect.height - 8)
    assert count_pixels(lit, true_half, toggle.selected_text_color) > 0

    menu.set_pointer_leading(True)  # With the pointer over nothing.
    unlit = interface.render()

    assert count_pixels(unlit, true_half, toggle.selected_text_color) == 0


def test_261113211043_4fc73fd2():
    # Holding the pointer down changes nothing on screen.
    button = Button(label=Button.ButtonText(text="GO"))
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[button])
    interface.push_stack(menu)
    first = interface.render()

    menu.set_pressed_part(button, "body")

    assert interface.render() is first


def test_261113211043_37b36716():
    # Pointer over nothing lights nothing.
    button = Button(label=Button.ButtonText(text="GO"))
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[button])
    interface.push_stack(menu)
    menu.set_pointer_leading(True)
    surf = interface.render()
    assert surf is not None

    assert surf.get_at(hit_rect_of(interface, button).topleft) == drawn(button.border_color)


def test_261113211043_a54dc13d():
    # Hover redraws only when it changes.
    selector = Selector(selections=("A", "B"))
    interface = Interface(size=SIZE)
    menu = Panel(root_elements=[selector])
    interface.push_stack(menu)
    menu.set_pointer_leading(True)
    menu.set_hovered(selector, "left")
    first = interface.render()

    menu.set_hovered(selector, "left")
    assert interface.render() is first
    menu.set_hovered(selector, "right")
    assert interface.render() is not first


def test_261113211043_05c8faca(monkeypatch):
    # Cursor in an empty field sits on the hint without moving it.
    field = InputField(value=InputField.InputValueText(text=""), hint=InputField.InputHintText(text="[ESC]"))
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[field]))
    interface.render()

    def text_rect(text):
        return next(rect for drawn, rect in tree_of(interface.renderer).element_rects if isinstance(drawn, NormalText) and drawn.text == text)

    closed_hint = text_rect("[ESC]")
    monkeypatch.setattr(time, "monotonic", lambda: 0.0)
    field.open()  # The cursor shows at once after opening.
    interface.render()

    assert text_rect("[ESC]").topleft == closed_hint.topleft
    assert text_rect("_").topleft == closed_hint.topleft


def test_261113212818_6ba23984():
    # Primary button bar has an even gap.
    button = PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="GO"))
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), button]))  # The gap holds the selection.
    surf = interface.render()
    assert surf is not None
    box = hit_rect_of(interface, button).inflate(-2, -2)  # Inside the border.

    assert bar_margins(surf, box, drawn(button.fill_color)) == (3, 3, 3, 3)
    assert surf.get_at(box.topleft) == drawn(button.background_color)


def test_261113212818_8a85fe77():
    # Lit primary button lights its bar and border.
    button = PrimaryButton(label=PrimaryButton.PrimaryButtonText(text="GO"))
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[button]))
    surf = interface.render()
    assert surf is not None
    rect = hit_rect_of(interface, button)

    assert surf.get_at(rect.topleft) == drawn(button.selected_border_color)
    assert bar_margins(surf, rect.inflate(-2, -2), drawn(button.selected_fill_color)) == (3, 3, 3, 3)


def test_261113213323_fb2d87b3():
    # Selector counts its position beside it in one input width.
    selector = Selector(selections=("A", "B", "C", "D"), value=1)
    plain = Selector(selections=("A", "B"), use_number=False)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), selector, plain]))
    interface.render()

    def texts():
        return [drawn.text for drawn, _ in tree_of(interface.renderer).element_rects if isinstance(drawn, NormalText)]

    assert "2" in texts() and "/4" in texts() and "/2" not in texts()
    assert hit_rect_of(interface, selector).width == hit_rect_of(interface, plain).width

    selector.next()
    interface.render()
    assert "3" in texts()


def test_261113213323_2568542c():
    # Selector counter mutes the total and marks a changed position.
    selector = Selector(selections=("A", "B", "C", "D"), value=1)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), selector]))
    selector.next()
    interface.render()

    colors = {drawn.text: drawn.text_color for drawn, _ in tree_of(interface.renderer).element_rects if isinstance(drawn, NormalText)}
    assert colors["3"] == selector.altered_selection_color
    assert colors["/4"] == selector.count_text.text_color


def test_261116235540_2fb9911e():
    # A scale multiplies sizes and font sizes but keeps 1px borders, and hit-tests on the scaled copy reach the real element.
    button = Button(label=Button.ButtonText(text="GO"))
    interface = Interface(size=SIZE)
    interface.fonts.add_dir(str(FONTS))
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), button]))
    interface.render()
    rect_1 = hit_rect_of(interface, button)

    interface.scale = 2
    surf = interface.render()
    assert surf is not None
    rect_2 = hit_rect_of(interface, button)
    assert rect_2.size == (2 * rect_1.width, 2 * rect_1.height)
    assert surf.get_at(rect_2.topleft) == drawn(button.border_color)
    assert surf.get_at((rect_2.x + 1, rect_2.y + 1)) == drawn(button.background_color)
    menu = interface.top_stack()
    assert menu is not None
    assert interface.renderer.find_selectable_at(menu, rect_2.center) is button
    assert button.size == (148.0, 22.0) and button.label.font_size == 14


def test_261116235540_3357a6eb():
    # Changing the scale recomposes once, setting the same scale does not, and composing a scaled copy is not an edit.
    interface = Interface(size=SIZE)
    interface.push_stack(Title())
    calls = counting_recomposes(interface)
    interface.render()
    version = Element._render_version

    interface.scale = 2
    interface.render()
    interface.scale = 2
    interface.render()

    assert len(calls) == 2
    assert Element._render_version == version


def test_261116235540_bfd93208():
    # A click at scale 2 activates the real button, not its scaled copy.
    pressed = []
    interface = Interface(size=SIZE)
    interface.scale = 2
    menu = Title(on_start=lambda: pressed.append(1))
    interface.push_stack(menu)
    interface.render()
    start = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "START")
    center = hit_rect_of(interface, start).center

    interface.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=center, button=1))
    interface.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=center, button=1))

    assert pressed == [1]


def test_261116235540_b64dcd29():
    # A scale must be a whole number of at least 1, and an open field keeps its typed text when drawn scaled.
    interface = Interface(size=SIZE)
    for scale in (0, 1.5, True):
        try:
            interface.scale = scale  # pyright: ignore[reportAttributeAccessIssue]
        except ValueError:
            continue
        raise AssertionError(f"Invalid {scale=} was accepted")

    menu = Form()
    field = next(e for e in menu._selectable_elements if isinstance(e, InputField))
    interface.scale = 2
    interface.push_stack(menu)
    field.open()
    field.append("2")
    interface.render()

    texts = [drawn.text for drawn, _ in tree_of(interface.renderer).element_rects if isinstance(drawn, NormalText)]
    assert any(text.startswith("PLAYER2") for text in texts)
    assert [glyph_field for glyph_field, _ in tree_of(interface.renderer).rendered_glyphs] == [field]


def test_261116235856_247c6ccd():
    # A changed selector with a number box drew its option in the normal colour, because its box copy lost is_edited.
    selector = Selector(selections=("A", "B", "C", "D"), value=1)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), selector]))
    interface.render()

    def colors():
        return {drawn.text: drawn.text_color for drawn, _ in tree_of(interface.renderer).element_rects if isinstance(drawn, NormalText)}

    assert colors()["B"] == selector.selection_text.text_color
    selector.next()
    interface.render()
    assert colors()["C"] == selector.altered_selection_color


def test_261116235911_c325db5f():
    # A menu with is_scaled off is drawn at its own sizes, and changing the scale does not recompose it.
    interface = Interface(size=SIZE)
    menu = Title(is_scaled=False)
    interface.push_stack(menu)
    interface.render()
    start = menu._selectable_elements[0]
    rect_1 = hit_rect_of(interface, start)
    calls = counting_recomposes(interface)

    interface.scale = 3
    interface.render()

    assert hit_rect_of(interface, start) == rect_1
    assert calls == []


def test_261117000945_981f1b3b():
    # Key bindings that share keys both draw in the conflict colour, and rebinding one clears it from both.
    first = KeyBinding(value=("SPACE",))
    second = KeyBinding(value=("SPACE",))
    third = KeyBinding(value=("W",))
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), first, second, third]))
    interface.render()

    def chip_fills():
        tree = tree_of(interface.renderer)
        fills = {}
        for drawn_element, rect in tree.element_rects:
            if isinstance(drawn_element, HorizontalDivision) and drawn_element.background_color in (first.fill_color, first.conflict_fill_color, first.edited_fill_color):
                owner = next(binding for binding in (first, second, third) if hit_rect_of(interface, binding).contains(rect))
                fills[owner.id] = drawn_element.background_color
        return fills

    fills = chip_fills()
    assert fills[first.id] == fills[second.id] == first.conflict_fill_color and fills[third.id] == first.fill_color
    second.bind(("E",))
    interface.render()
    fills = chip_fills()
    assert fills[first.id] == first.fill_color and fills[second.id] == first.edited_fill_color


def test_261117000945_5569de88():
    # Listening redraws a key binding as its prompt, and a colour swatch's typed text and cursor are drawn from the real field.
    binding = KeyBinding(value=("SPACE",))
    swatch = ColorSwatch(value=ColorSwatch.InputValueText(text="#FFFFFFFF"))
    field = InputField()
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), binding, swatch, field]))
    interface.render()

    def texts():
        return [drawn_element.text for drawn_element, _ in tree_of(interface.renderer).element_rects if isinstance(drawn_element, NormalText)]

    assert "SPACE" in texts()
    binding.listen()
    swatch.open()
    swatch.append("0")
    interface.render()
    assert "PRESS KEYS" in texts() and "SPACE" not in texts()
    assert any(text.startswith("#FFFFFFFF0") for text in texts())
    assert [glyph_field for glyph_field, _ in tree_of(interface.renderer).rendered_glyphs if isinstance(glyph_field, ColorSwatch)] == [swatch]
    assert hit_rect_of(interface, swatch).width == hit_rect_of(interface, field).width


def test_261117001344_72b0b060():
    # A listening key binding's prompt is normal text that flashes, redrawing only when it turns on or off, even at scale 2.
    binding = KeyBinding(value=("SPACE",))
    interface = Interface(size=SIZE)
    interface.scale = 2
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), binding]))
    calls = counting_recomposes(interface)
    binding.listen()

    def prompt():
        return next(drawn_element for drawn_element, _ in tree_of(interface.renderer).element_rects if isinstance(drawn_element, NormalText) and drawn_element.text == "PRESS KEYS")

    interface.render()
    interface.render()
    assert len(calls) == 1
    assert prompt().text_color == binding.listening_text.text_color == ThemeColorType.TEXT_NORMAL and prompt().text_alpha == 0xFF

    # Half a period later the prompt is hidden, which needs one recompose.
    binding._listen_epoch -= KeyBinding._prompt_period
    interface.render()
    interface.render()
    assert len(calls) == 2 and prompt().text_alpha == 0
    assert [real for real, _ in tree_of(interface.renderer).rendered_prompts] == [binding]

    binding.bind(("W",))
    interface.render()
    assert tree_of(interface.renderer).rendered_prompts == []
