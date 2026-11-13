"""
renderer.py
"""

from __future__ import annotations

import pygame

from collections import OrderedDict
from collections.abc import Hashable
from dataclasses import dataclass, field, replace
from functools import singledispatchmethod
import math
import time
from typing import Any, NamedTuple

from .assets import FontManager, ImageManager
from .elements import (
    RGBA,
    TRANSPARENT,
    AlignmentType,
    Button,
    Division,
    Element,
    Fill,
    Gap,
    HorizontalDivision,
    Image,
    InputField,
    JustifyType,
    MeasureType,
    OverflowType,
    ProgressBar,
    RotationType,
    Selector,
    Slider,
    Text,
    TextDecorationType,
    Toggle,
    VerticalDivision,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .menus import Menu


_PRECISION = 4

_SCROLLBAR_PW = 10
_SCROLLBAR_MIN_PH = 32

_TEXT_CACHE_BYTES = 32 * 1024 * 1024
_BOX_CACHE_BYTES = 32 * 1024 * 1024
_SHADOW_CACHE_BYTES = 16 * 1024 * 1024

_DEBUG_SAMPLE_SECONDS = 0.5
_DEBUG_PADDING = 6
_DEBUG_BORDER_THICKNESS = 2
_DEBUG_HIT_RECT_COLOR = "#00FF80FF"

_ROTATION_DEGREES = {RotationType.LEFT: 90, RotationType.RIGHT: -90, RotationType.UPTURNED: 180}


# -----------------------------------------------------------------------------


class _SurfaceCache:
    """Least-recently-used cache bounded by the pixel memory of its surfaces."""

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        self._items: OrderedDict[Hashable, tuple[Any, int]] = OrderedDict()
        self._bytes = 0

    @property
    def nbytes(self) -> int:
        """Approximate pixel memory held, in bytes."""
        return self._bytes

    def _get(self, key: Hashable) -> Any:
        item = self._items.get(key)
        if item is None:
            return None
        self._items.move_to_end(key)
        return item[0]

    def _has(self, key: Hashable) -> bool:
        return key in self._items

    def _put(self, key: Hashable, value: Any, surf: pygame.Surface) -> None:
        nbytes = surf.get_width() * surf.get_height() * 4
        self._drop(key)
        self._items[key] = (value, nbytes)
        self._bytes += nbytes
        while self._bytes > self.max_bytes and len(self._items) > 1:
            _, (_, evicted) = self._items.popitem(last=False)
            self._bytes -= evicted

    def _take(self, key: Hashable) -> Any:
        item = self._items.pop(key, None)
        if item is None:
            return None
        self._bytes -= item[1]
        return item[0]

    def _drop(self, key: Hashable) -> None:
        self._take(key)

    def _clear(self) -> None:
        self._items.clear()
        self._bytes = 0


class _TextCache(_SurfaceCache):
    """Rendered strings, keyed by every ``Text`` field that reaches the pixels plus the wrap width."""

    def __init__(self, fonts: FontManager, max_bytes: int = _TEXT_CACHE_BYTES) -> None:
        super().__init__(max_bytes)
        self._fonts = fonts
        self._metrics_cache: dict[tuple[str, int, bool, bool, bool], tuple[int, int, int]] = {}

    def get_surf(self, text: Text, wrap_pw: int) -> tuple[pygame.Surface, pygame.Rect]:
        """
        ``text`` rendered with its font, decorations, highlight and alpha, wrapped
        at ``wrap_pw`` when wrappable, and the part of it that layout uses.

        The layout rect runs from the top of a capital to the baseline and drops
        the spacing after the last glyph, so centring the rect centres the ink.
        Descenders, underlines and cursors still draw outside it.
        """
        wrap_pw = wrap_pw if text.is_wrappable else 0
        key = (text.font_name, text.font_size, text.text, text.text_color, text.text_background, text.text_decorations, wrap_pw, text.text_alpha)
        cached = self._get(key)
        if cached is not None:
            return cached

        font = self._fonts.get_font(text.font_name, text.font_size)
        decorations = text.text_decorations
        font.set_bold(bool(decorations & TextDecorationType.BOLD))
        font.set_italic(bool(decorations & TextDecorationType.ITALIC))
        font.set_underline(bool(decorations & TextDecorationType.UNDERLINE))
        font.set_strikethrough(bool(decorations & TextDecorationType.STRIKETHROUGH))
        is_antialiased = bool(decorations & TextDecorationType.ANTIALIASING)
        glyphs = font.render(text.text, is_antialiased, text.text_color, None, wrap_pw).convert_alpha()

        surf = _make_surf(glyphs.get_width(), glyphs.get_height())
        if text.text_background != TRANSPARENT:
            surf.fill(pygame.Color(text.text_background))
        surf.blit(glyphs, (0, 0))
        surf.set_alpha(text.text_alpha)

        cap_top, cap_bottom_blank, trailing_pw = self._get_metrics(text, font, is_antialiased)
        layout_rect = pygame.Rect(0, cap_top, max(0, surf.get_width() - trailing_pw), max(0, surf.get_height() - cap_top - cap_bottom_blank))
        self._put(key, (surf, layout_rect), surf)
        return surf, layout_rect

    def _get_metrics(self, text: Text, font: pygame.font.Font, is_antialiased: bool) -> tuple[int, int, int]:
        """Blank rows above a capital, blank rows below the baseline of one line, and spacing after a glyph."""
        key = (text.font_name, text.font_size, font.bold, font.italic, is_antialiased)
        metrics = self._metrics_cache.get(key)
        if metrics is None:
            # A capital H has no overshoot or descender, so its ink marks the cap height and the baseline
            glyph_surf = font.render("H", is_antialiased, (255, 255, 255)).convert_alpha()
            ink_rects = pygame.mask.from_surface(glyph_surf).get_bounding_rects()
            if ink_rects:
                ink = ink_rects[0].unionall(ink_rects[1:])
                metrics = (ink.top, glyph_surf.get_height() - ink.bottom, glyph_surf.get_width() - ink.right)
            else:
                metrics = (0, 0, 0)
            self._metrics_cache[key] = metrics
        return metrics


class _BoxCache(_SurfaceCache):
    """Element boxes, one surface shared by every element with the same geometry and colours."""

    def __init__(self, max_bytes: int = _BOX_CACHE_BYTES) -> None:
        super().__init__(max_bytes)

    def get_surf(self, pw: int, ph: int, margin_pw: int, margin_ph: int, border_thickness: int, border_color: pygame.Color | None, background_color: pygame.Color | None) -> pygame.Surface | None:
        """The border and background of a box, or ``None`` when neither would be visible."""
        if border_color is None and background_color is None:
            return None
        key = (pw, ph, margin_pw, margin_ph, border_thickness, tuple(border_color) if border_color is not None else None, tuple(background_color) if background_color is not None else None)
        surf = self._get(key)
        if surf is not None:
            return surf

        border_rect = pygame.Rect(margin_pw, margin_ph, pw - 2 * margin_pw, ph - 2 * margin_ph)
        surf = _make_surf(pw, ph)
        if border_color is not None:
            pygame.draw.rect(surf, border_color, border_rect)
        if background_color is not None:
            pygame.draw.rect(surf, background_color, border_rect.inflate(-2 * border_thickness, -2 * border_thickness))
        self._put(key, surf, surf)
        return surf


class _ShadowCache(_SurfaceCache):
    """Shadows of cached surfaces, keyed by the identity of the source and the shadow style."""

    def __init__(self, max_bytes: int = _SHADOW_CACHE_BYTES) -> None:
        super().__init__(max_bytes)

    def get_surf(self, element: Element, source_surf: pygame.Surface) -> pygame.Surface | None:
        """The mask of ``source_surf`` in the element's shadow colour, alpha and scale, or ``None`` when invisible."""
        if element.shadow_color == TRANSPARENT or element.shadow_alpha == 0:
            return None
        key = (id(source_surf), element.shadow_color, element.shadow_alpha, element.shadow_scale)
        cached = self._get(key)
        if cached is not None and cached[0] is source_surf:
            return cached[1]

        mask = pygame.mask.from_surface(source_surf)
        if element.shadow_scale != 1:
            mask_surf = mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
            scaled_pw = int(source_surf.get_width() * element.shadow_scale)
            scaled_ph = int(source_surf.get_height() * element.shadow_scale)
            mask = pygame.mask.from_surface(pygame.transform.smoothscale(mask_surf, (scaled_pw, scaled_ph)))
        shadow_surf = mask.to_surface(setcolor=element.shadow_color, unsetcolor=(0, 0, 0, 0))
        shadow_surf.set_alpha(element.shadow_alpha)
        self._put(key, (source_surf, shadow_surf), shadow_surf)
        return shadow_surf


# -----------------------------------------------------------------------------


@dataclass(kw_only=True, repr=False)
class _SegmentStrip(Element):
    """The segments of a ``ProgressBar`` or ``Slider``, built by the renderer while composing."""

    count: int
    filled: int
    segment_pw: int
    segment_ph: int
    gap_pw: int
    fill_color: RGBA
    empty_color: RGBA

    background_color: RGBA = TRANSPARENT
    is_selectable: bool = False


# -----------------------------------------------------------------------------


@dataclass(eq=False)
class _MenuTree:
    """One menu composed at one window size and render version, and everything made from it."""

    class Space(NamedTuple):
        """The room a content composer is given, as a range per axis."""

        range_pw: range
        range_ph: range

    @dataclass(slots=True)
    class Node:
        """One composed element: its box, its content and its children."""

        element: Element
        content_surf: pygame.Surface | None = None
        children: list[_MenuTree.Node] = field(default_factory=list)
        content_rect: pygame.Rect | None = None  # Part of content_surf that layout uses; the whole surface when None

        hit_target: Element | None = None
        box_surf: pygame.Surface | None = None
        pw: int = 0
        ph: int = 0
        offset: tuple[int, int] = (0, 0)
        inner_offset: tuple[int, int] = (0, 0)
        is_opaque: bool = False

        def get_content_size(self) -> tuple[int, int]:
            """Size of the content as laid out, which can be smaller than what is drawn."""
            if self.content_rect is not None:
                return self.content_rect.size
            return self.content_surf.get_size() if self.content_surf is not None else (0, 0)

        def extent(self) -> tuple[int, int]:
            """Width and height of this box and every descendant that overflows it, relative to the box."""
            inner_pw, inner_ph = self.get_content_size()
            for child in self.children:
                if child.element.is_fixed:
                    continue
                child_pw, child_ph = child.extent()
                inner_pw = max(inner_pw, child.offset[0] + child_pw)
                inner_ph = max(inner_ph, child.offset[1] + child_ph)
            return max(self.pw, self.inner_offset[0] + inner_pw), max(self.ph, self.inner_offset[1] + inner_ph)

    menu: Menu
    size: tuple[int, int]
    render_version: int
    selection_id: str | None

    root: Node | None = None
    rendered_glyphs: list[tuple[InputField, str]] = field(default_factory=list)
    hit_rects: list[tuple[Element, pygame.Rect]] = field(default_factory=list)
    element_rects: list[tuple[Element, pygame.Rect]] = field(default_factory=list)
    facade_surf: pygame.Surface | None = None
    output_surf: pygame.Surface | None = None
    output_scroll_py: int | None = None

    @property
    def is_opaque(self) -> bool:
        """Whether the facade covers every pixel of the window with alpha 255."""
        return self.root is not None and self.root.is_opaque

    def is_current(self, menu: Menu, size: tuple[int, int]) -> bool:
        """Whether this tree still shows ``menu`` at ``size``, with no element edited and no rendered cursor glyph changed since."""
        return (
            menu is self.menu
            and size == self.size
            and Element._render_version == self.render_version
            and all(input_field.get_cursor_glyph() == glyph for input_field, glyph in self.rendered_glyphs)
        )

    def find_at(self, facade_pos: tuple[int, int]) -> list[Element]:
        """Every element under a facade position, deepest first."""
        return [element for element, rect in reversed(self.hit_rects) if rect.collidepoint(facade_pos)]


# -----------------------------------------------------------------------------


class MenuRenderer:
    """Composes a menu's element tree and returns it as a window-sized surface."""

    def __init__(self) -> None:
        self.fonts: FontManager = FontManager()
        self.images: ImageManager = ImageManager()

        self._text_cache = _TextCache(self.fonts)
        self._box_cache = _BoxCache()
        self._shadow_cache = _ShadowCache()

        self._menu_tree: _MenuTree | None = None

    # -------------------------------------------------------------------------

    def render(self, menu: Menu, size: tuple[int, int]) -> pygame.Surface:
        tree = self._menu_tree
        if tree is None or not tree.is_current(menu, size):
            tree = self._menu_tree = self._compose_tree(menu, size)
            self._render_facade(tree)
        return self._present_output(tree)

    # -------------------------------------------------------------------------

    def _compose_tree(self, menu: Menu, size: tuple[int, int]) -> _MenuTree:
        tree = _MenuTree(menu, size, Element._render_version, menu.get_selection_id())
        tree.root = self._compose_node(menu._div, tree, _MenuTree.Space(range(size[0], size[0]), range(size[1], size[1])))
        return tree

    def _compose_node(self, element: Element, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        if not element.is_visible:
            return _MenuTree.Node(element, hit_target=element)
        if isinstance(element, ProgressBar):
            # A bar is two ordinary boxes side by side; clicks on either still reach the bar itself
            node = self._compose_node(self._make_bar_row(element, tree, space), tree, space)
            node.hit_target = element
            return node

        size_pw, size_ph = self._resolve_measure(element.size, element.size_measure, space)
        margin_pw, margin_ph = self._resolve_measure(element.margin, element.margin_measure, space)
        padding_pw, padding_ph = self._resolve_measure(element.padding, element.padding_measure, space)
        offset_px, offset_py = self._resolve_measure(element.offset, element.offset_measure, space)
        border_thickness = element.border_thickness
        decor_pw = 2 * (margin_pw + border_thickness + padding_pw)
        decor_ph = 2 * (margin_ph + border_thickness + padding_ph)

        # TODO: Write a 1-line comment here.
        inner_pw = max(0, min(size_pw - decor_pw, space.range_pw.stop - decor_pw))
        inner_ph = max(0, min(size_ph - decor_ph, space.range_ph.stop - decor_ph))
        if element.overflow == OverflowType.EXTEND:
            range_pw = range(inner_pw, max(0, space.range_pw.stop - decor_pw))
            range_ph = range(inner_ph, max(0, space.range_ph.stop - decor_ph))
            inner_space = _MenuTree.Space(range_pw, range_ph)
        elif element.overflow == OverflowType.OVERFLOW:
            range_pw = range(inner_pw, inner_pw + 999)
            range_ph = range(inner_ph, inner_ph + 999)
            inner_space = _MenuTree.Space(range_pw, range_ph)
        else:
            range_pw = range(inner_pw, inner_pw)
            range_ph = range(inner_ph, inner_ph)
            inner_space = _MenuTree.Space(range_pw, range_ph)

        node = self._compose_content(element, tree, inner_space)
        content_pw, content_ph = node.extent()
        if element.overflow == OverflowType.EXTEND:
            inner_pw, inner_ph = max(inner_pw, content_pw), max(inner_ph, content_ph)
        align_px, align_py = self._align_box(element.alignment, inner_pw, inner_ph, content_pw, content_ph)

        node.hit_target = element
        node.pw, node.ph = inner_pw + decor_pw, inner_ph + decor_ph
        node.offset = (offset_px, offset_py)
        node.inner_offset = (decor_pw // 2 + align_px, decor_ph // 2 + align_py)

        border_rect = pygame.Rect(margin_pw, margin_ph, node.pw - 2 * margin_pw, node.ph - 2 * margin_ph)
        background_rect = border_rect.inflate(-2 * border_thickness, -2 * border_thickness)
        border_color = _color(node.element.border_color, node.element.border_alpha) if border_thickness > 0 and border_rect.width > 0 and border_rect.height > 0 else None
        background_color = _color(node.element.background_color, node.element.background_alpha) if background_rect.width > 0 and background_rect.height > 0 else None
        border_color = border_color if border_color is not None and border_color.a > 0 else None
        background_color = background_color if background_color is not None and background_color.a > 0 else None
        node.box_surf = self._box_cache.get_surf(node.pw, node.ph, margin_pw, margin_ph, border_thickness, border_color, background_color)

        painted_rect = border_rect if border_color is not None else background_rect
        node.is_opaque = (
            node.pw > 0
            and node.ph > 0
            and margin_pw == 0
            and margin_ph == 0
            and painted_rect.size == (node.pw, node.ph)
            and (border_color is None or border_color.a == 255)
            and (background_rect.width <= 0 or background_rect.height <= 0 or (background_color is not None and background_color.a == 255))
            and element.rotation == RotationType.NONE
        )
        return node

    @singledispatchmethod
    def _compose_content(self, element: Element, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        return _MenuTree.Node(element)

    @_compose_content.register(Division)
    def _(self, element: Division, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        gap_pw, gap_ph = self._resolve_measure(element.gap, element.gap_measure, space)
        is_vertical = isinstance(element, VerticalDivision)
        children = [self._compose_node(child, tree, space) for child in element.elements if child.is_visible]
        flowed = [child for child in children if not child.element.is_fixed]

        if is_vertical:
            flow_pw = max((child.pw for child in flowed), default=0)
            flow_ph = sum(child.ph for child in flowed) + gap_ph * max(0, len(flowed) - 1)
        else:
            flow_pw = sum(child.pw for child in flowed) + gap_pw * max(0, len(flowed) - 1)
            flow_ph = max((child.ph for child in flowed), default=0)

        flow_px, flow_py = 0, 0
        for child in flowed:
            if is_vertical:
                across = flow_pw - child.pw
                flow_px = 0 if child.element.justify == JustifyType.START else across // 2 if child.element.justify == JustifyType.CENTER else across
            else:
                across = flow_ph - child.ph
                flow_py = 0 if child.element.justify == JustifyType.START else across // 2 if child.element.justify == JustifyType.CENTER else across
            child.offset = (child.offset[0] + flow_px, child.offset[1] + flow_py)
            if is_vertical:
                flow_py += child.ph + gap_ph
            else:
                flow_px += child.pw + gap_pw

        return _MenuTree.Node(element, children=children)

    @_compose_content.register(Gap)
    def _(self, element: Gap, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        gap_pw, gap_ph = space.range_pw.start, space.range_ph.start
        if gap_pw == 0 or gap_ph == 0 or _color(element.background_color, element.background_alpha).a == 0:
            return _MenuTree.Node(element)
        gap_surf = _make_surf(gap_pw, gap_ph)
        gap_surf.fill(element.background_color)
        gap_surf.set_alpha(element.background_alpha)
        return _MenuTree.Node(element, content_surf=gap_surf)

    @_compose_content.register(Fill)
    def _(self, element: Fill, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        return _MenuTree.Node(element, content_surf=_make_surf(space.range_pw.stop, space.range_ph.stop))

    @_compose_content.register(Text)
    def _(self, element: Text, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        text_surf, layout_rect = self._text_cache.get_surf(element, space.range_pw.stop)
        return _MenuTree.Node(element, content_surf=text_surf, content_rect=layout_rect)

    @_compose_content.register(Image)
    def _(self, element: Image, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        return _MenuTree.Node(element, content_surf=self.images.get_image(element.image_path))

    @_compose_content.register(_SegmentStrip)
    def _(self, element: _SegmentStrip, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        strip_pw = element.count * element.segment_pw + max(0, element.count - 1) * element.gap_pw
        strip_surf = _make_surf(strip_pw, element.segment_ph)
        for idx in range(element.count):
            color = element.fill_color if idx < element.filled else element.empty_color
            strip_surf.fill(color, pygame.Rect(idx * (element.segment_pw + element.gap_pw), 0, element.segment_pw, element.segment_ph))
        return _MenuTree.Node(element, content_surf=strip_surf)

    @_compose_content.register(Button)
    def _(self, element: Button, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        is_selected = tree.selection_id == element.id
        if is_selected:
            element = replace(element, border_color=element.selected_border_color, label=replace(element.label, text_color=element.selected_text_color))
        return _MenuTree.Node(element, children=[self._compose_node(element.label, tree, space)])

    @_compose_content.register(Toggle)
    def _(self, element: Toggle, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        is_selected = tree.selection_id == element.id
        eff_element = replace(element, border_color=element.selected_border_color) if is_selected else element
        fill_color = element.edited_fill_color if element.is_called else element.fill_color

        # The halves split the inner width, so the filled one sits the padding away from every edge
        half_pw, half_ph = space.range_pw.start // 2, space.range_ph.start
        halves = []
        for text, is_filled in ((element.false_text, not element.value), (element.true_text, element.value)):
            label = replace(element.label, text=text, text_color=element.filled_text_color if is_filled else element.label.text_color)
            halves.append(HorizontalDivision(
                elements=[label], size=(half_pw, half_ph), alignment=AlignmentType.CENTER, gap=(0.0, 0.0),
                background_color=fill_color if is_filled else TRANSPARENT,
            ))
        row = HorizontalDivision(elements=halves, gap=(0.0, 0.0))
        return _MenuTree.Node(eff_element, children=[self._compose_node(row, tree, space)])

    @_compose_content.register(Selector)
    def _(self, element: Selector, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        is_selected = tree.selection_id == element.id
        eff_element = replace(element, border_color=element.selected_border_color) if is_selected else element

        selection_text = replace(element.selection_text, text=element.selection())
        if element.is_altered():
            selection_text = replace(selection_text, text_color=element.altered_selection_color)
        index = element.buffer_index()
        left_arrow = self._color_arrow(element.left_arrow, index == 0, is_selected, element.selected_arrow_color, element.disabled_arrow_color)
        right_arrow = self._color_arrow(element.right_arrow, index == len(element.selections) - 1, is_selected, element.selected_arrow_color, element.disabled_arrow_color)

        # The option gets a fixed slot between the arrows, so changing it never moves them
        gap_pw = self._resolve_measure(element.gap, MeasureType.ABSOLUTE, space)[0]
        slot_pw = max(0, space.range_pw.start - self._measure_text(left_arrow) - self._measure_text(right_arrow) - 2 * gap_pw)
        slot = HorizontalDivision(elements=[selection_text], size=(slot_pw, 0.0), alignment=AlignmentType.CENTER, gap=(0.0, 0.0))
        row = HorizontalDivision(elements=[left_arrow, slot, right_arrow], gap=(gap_pw, 0.0))
        return _MenuTree.Node(eff_element, children=[self._compose_node(row, tree, space)])

    @_compose_content.register(InputField)
    def _(self, element: InputField, tree: _MenuTree, space: _MenuTree.Space) -> _MenuTree.Node:
        is_selected = tree.selection_id == element.id
        eff_element = replace(element, border_color=element.selected_border_color) if is_selected else element

        glyph = element.get_cursor_glyph()
        tree.rendered_glyphs.append((element, glyph))
        value_text = replace(element.value, text=element.get_field() + glyph)
        if not element.authenticate():
            value_text = replace(value_text, text_color=element.invalid_text_color)
        elif element.is_altered():
            value_text = replace(value_text, text_color=element.edited_text_color)

        parts: list[Element] = [element.prompt]
        if not element.get_field():
            parts.append(element.hint)
        if value_text.text:
            parts.append(value_text)
        gap_pw = self._resolve_measure(element.gap, MeasureType.ABSOLUTE, space)[0]
        row = HorizontalDivision(elements=parts, gap=(gap_pw, 0.0))
        return _MenuTree.Node(eff_element, children=[self._compose_node(row, tree, space)])

    # -------------------------------------------------------------------------

    def _make_bar_row(self, element: ProgressBar, tree: _MenuTree, space: _MenuTree.Space) -> HorizontalDivision:
        """The bar box and the number box of ``element``, styled and sized from its fields."""
        size_pw, size_ph = self._resolve_measure(element.size, element.size_measure, space)
        padding = self._resolve_measure(element.padding, element.padding_measure, space)
        is_selected = tree.selection_id == element.id
        value = element.get_buffer_value() if isinstance(element, Slider) else element.value
        fraction = element.get_fraction(value)
        is_altered = isinstance(element, Slider) and element.is_altered()

        def box(elements: list[Element], pw: int, border_color: RGBA, gap_pw: int = 0) -> HorizontalDivision:
            return HorizontalDivision(
                elements=elements, size=(pw, size_ph), padding=padding, gap=(gap_pw, 0.0), alignment=element.alignment,
                background_color=element.background_color, background_alpha=element.background_alpha,
                border_thickness=element.border_thickness, border_color=border_color, border_alpha=element.border_alpha,
                shadow_color=element.shadow_color, shadow_alpha=element.shadow_alpha, shadow_scale=element.shadow_scale,
                shadow_offset=element.shadow_offset, shadow_offset_measure=element.shadow_offset_measure,
            )

        bar_pw = size_pw - (element.box_gap_pw + element.number_pw if element.use_number else 0)
        strip_pw = max(0, bar_pw - 2 * (padding[0] + element.border_thickness))
        arrows: tuple[Text, Text] | None = None
        gap_pw = 0
        if isinstance(element, Slider):
            arrows = (
                self._color_arrow(element.left_arrow, fraction <= 0.0, is_selected, element.selected_arrow_color, element.disabled_arrow_color),
                self._color_arrow(element.right_arrow, fraction >= 1.0, is_selected, element.selected_arrow_color, element.disabled_arrow_color),
            )
            gap_pw = self._resolve_measure(element.gap, MeasureType.ABSOLUTE, space)[0]
            strip_pw -= sum(self._measure_text(arrow) for arrow in arrows) + 2 * gap_pw
        count = max(1, element.segments)
        strip = _SegmentStrip(
            count=count, filled=int(fraction * count + 0.5),
            segment_pw=max(0, (strip_pw - (count - 1) * element.segment_gap_pw) // count), segment_ph=element.segment_ph,
            gap_pw=element.segment_gap_pw, fill_color=element.altered_color if isinstance(element, Slider) and is_altered else element.fill_color, empty_color=element.empty_color,
        )
        parts: list[Element] = [arrows[0], strip, arrows[1]] if arrows is not None else [strip]
        bar_border_color = element.selected_border_color if isinstance(element, Slider) and is_selected else element.border_color
        boxes: list[Element] = [box(parts, bar_pw, bar_border_color, gap_pw)]

        if element.use_number:
            number_text = replace(element.number_text, text=element.get_number(value))
            if isinstance(element, Slider) and is_altered:
                number_text = replace(number_text, text_color=element.altered_color)
            boxes.append(box([number_text], element.number_pw, element.border_color))

        return HorizontalDivision(
            elements=boxes, gap=(element.box_gap_pw, 0.0), justify=element.justify, alignment=element.alignment,
            offset=element.offset, offset_measure=element.offset_measure, margin=element.margin, margin_measure=element.margin_measure,
            rotation=element.rotation, is_fixed=element.is_fixed, is_selectable=element.is_selectable,
        )

    def _measure_text(self, text: Text) -> int:
        """Laid-out width of ``text`` on one line."""
        return self._text_cache.get_surf(text, 0)[1].width

    @staticmethod
    def _color_arrow(arrow: Text, is_disabled: bool, is_selected: bool, selected_color: RGBA, disabled_color: RGBA) -> Text:
        if is_disabled:
            return replace(arrow, text_color=disabled_color)
        if is_selected:
            return replace(arrow, text_color=selected_color)
        return arrow

    # -------------------------------------------------------------------------

    def _render_facade(self, tree: _MenuTree) -> None:
        root = tree.root
        assert root is not None
        facade = root.box_surf.copy() if root.box_surf is not None else _make_surf(root.pw, root.ph)
        tree.hit_rects = []
        tree.element_rects = [(root.element, facade.get_rect())]
        if root.element.is_selectable:
            tree.hit_rects.append((root.hit_target or root.element, facade.get_rect()))
        for child in root.children:
            self._render_node(child, tree, facade, root.inner_offset)
        tree.facade_surf = facade

    def _render_node(self, node: _MenuTree.Node, tree: _MenuTree, facade: pygame.Surface, origin: tuple[int, int]) -> None:
        element = node.element
        if element.is_fixed:
            origin = self._align_box(element.alignment, facade.get_width(), facade.get_height(), node.pw, node.ph)
        origin_px, origin_py = origin[0] + node.offset[0], origin[1] + node.offset[1]

        # A rotated subtree is rendered upright on its own surface, then turned once
        is_rotated = element.rotation != RotationType.NONE
        target = _make_surf(*node.extent()) if is_rotated else facade
        box_px, box_py = (0, 0) if is_rotated else (origin_px, origin_py)

        for surf in (node.box_surf, node.content_surf):
            if surf is None:
                continue
            at_px, at_py = (box_px, box_py) if surf is node.box_surf else (box_px + node.inner_offset[0], box_py + node.inner_offset[1])
            if surf is node.content_surf and node.content_rect is not None:
                at_px, at_py = at_px - node.content_rect.x, at_py - node.content_rect.y
            shadow_surf = self._shadow_cache.get_surf(element, surf)
            if shadow_surf is not None:
                shadow_px, shadow_py = self._resolve_measure(element.shadow_offset, element.shadow_offset_measure, _MenuTree.Space(range(surf.get_width()), range(surf.get_height())))
                target.blit(shadow_surf, (at_px + shadow_px, at_py + shadow_py))
            target.blit(surf, (at_px, at_py))

        node_rect = pygame.Rect(origin_px, origin_py, node.pw, node.ph)
        tree.element_rects.append((node.element, node_rect))
        if element.is_selectable:
            tree.hit_rects.append((node.hit_target or node.element, node_rect))

        previous_clip = target.get_clip()
        if element.overflow == OverflowType.CLIP:
            target.set_clip(pygame.Rect(box_px, box_py, node.pw, node.ph).clip(previous_clip))
        inner_px, inner_py = box_px + node.inner_offset[0], box_py + node.inner_offset[1]
        for child in node.children:
            self._render_node(child, tree, target, (inner_px, inner_py))
        target.set_clip(previous_clip)

        if is_rotated:
            facade.blit(pygame.transform.rotate(target, _ROTATION_DEGREES[element.rotation]), (origin_px, origin_py))

    def _render_scrollbar(self, output: pygame.Surface, facade_ph: int, scroll_py: int) -> None:
        output_ph = output.get_height()
        if facade_ph <= output_ph:
            return

        # pygame.draw writes without blending, so on an opaque output the bar is
        # rendered on its own strip and blended over the menu
        is_blended = not output.get_flags() & pygame.SRCALPHA
        strip = pygame.Surface((_SCROLLBAR_PW, output_ph), pygame.SRCALPHA) if is_blended else output
        track_px = 0 if is_blended else output.get_width() - _SCROLLBAR_PW

        thumb_ph = max(_SCROLLBAR_MIN_PH, int(output_ph * (output_ph / facade_ph)))
        thumb_py = int((scroll_py / (facade_ph - output_ph)) * (output_ph - thumb_ph))
        thumb_rect = pygame.Rect(track_px, thumb_py, _SCROLLBAR_PW, thumb_ph)
        pygame.draw.rect(strip, "#181C2780", pygame.Rect(track_px, 0, _SCROLLBAR_PW, output_ph))
        pygame.draw.rect(strip, "#30384E80", thumb_rect)
        pygame.draw.rect(strip, "#60606080", thumb_rect, 1)

        if is_blended:
            output.blit(strip, (output.get_width() - _SCROLLBAR_PW, 0))

    # -------------------------------------------------------------------------

    def _present_output(self, tree: _MenuTree) -> pygame.Surface:
        facade = tree.facade_surf
        assert facade is not None
        output_pw, output_ph = tree.size
        facade_ph = facade.get_height()
        max_scroll = max(0, facade_ph - output_ph)
        tree.menu._scroll = min(max(tree.menu._scroll, 0.0), float(max_scroll))
        scroll_py = int(round(tree.menu._scroll))
        if tree.output_surf is not None and tree.output_scroll_py == scroll_py:
            return tree.output_surf

        source_rect = pygame.Rect(0, scroll_py, output_pw, output_ph).clip(facade.get_rect())
        if tree.is_opaque and source_rect.size == (output_pw, output_ph):
            # No per-pixel alpha, so the game's blit is a plain copy
            output = facade.subsurface(source_rect).convert()
        else:
            # MAX against a zeroed surface copies the visible part exactly, where a
            # normal alpha blit would darken semi-transparent pixels
            output = pygame.Surface((output_pw, output_ph), pygame.SRCALPHA)
            if source_rect.width > 0 and source_rect.height > 0:
                output.blit(facade, (0, 0), source_rect, special_flags=pygame.BLEND_RGBA_MAX)
        self._render_scrollbar(output, facade_ph, scroll_py)

        tree.output_surf = output
        tree.output_scroll_py = scroll_py
        return output

    # -------------------------------------------------------------------------

    def find_elements_at(self, menu: Menu, pos: tuple[int, int]) -> list[Element]:
        """Every element under window position ``pos``, deepest first, or none until ``menu`` has been rendered."""
        tree = self._menu_tree
        if tree is None or tree.menu is not menu or tree.facade_surf is None:
            return []
        return tree.find_at((pos[0], pos[1] + int(round(menu._scroll))))

    def select_element_at(self, menu: Menu, pos: tuple[int, int]) -> Element | None:
        """Select and return the deepest selectable element under ``pos``, if any."""
        elements = self.find_elements_at(menu, pos)
        if elements and elements[0].is_selectable:
            menu.select_element_by_id(elements[0].id)
            return elements[0]
        return None

    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_measure(value: tuple[float, float], measure: MeasureType, space: _MenuTree.Space) -> tuple[int, int]:
        value_x, value_y = value
        if measure == MeasureType.RELATIVE:
            measure_x = math.floor(round(value_x * space.range_pw.stop, _PRECISION))
            measure_y = math.floor(round(value_y * space.range_ph.stop, _PRECISION))
            return measure_x, measure_y
        return int(value_x), int(value_y)

    @staticmethod
    def _align_box(alignment: AlignmentType, outer_pw: int, outer_ph: int, inner_pw: int, inner_ph: int) -> tuple[int, int]:
        align_px, align_py = 0, 0
        if alignment in (AlignmentType.MIDTOP, AlignmentType.CENTER, AlignmentType.MIDBOTTOM):
            align_px = max(0, (outer_pw - inner_pw) // 2)
        elif alignment in (AlignmentType.TOPRIGHT, AlignmentType.MIDRIGHT, AlignmentType.BOTTOMRIGHT):
            align_px = max(0, outer_pw - inner_pw)
        if alignment in (AlignmentType.MIDLEFT, AlignmentType.CENTER, AlignmentType.MIDRIGHT):
            align_py = max(0, (outer_ph - inner_ph) // 2)
        elif alignment in (AlignmentType.BOTTOMLEFT, AlignmentType.MIDBOTTOM, AlignmentType.BOTTOMRIGHT):
            align_py = max(0, outer_ph - inner_ph)
        return align_px, align_py


# -----------------------------------------------------------------------------


class DebugRenderer:
    """
    Wraps a ``MenuRenderer`` and draws debugging aids over its output.

    The stats overlay shows frame rate, element counts, recomposes per second
    and cache memory. The hover border outlines the element under the mouse in
    inverted colours. The hit rects mode outlines every selectable element.
    """

    def __init__(self, renderer: MenuRenderer, use_stats_overlay: bool = False, use_hover_border: bool = False, use_hit_rects: bool = False) -> None:
        self.renderer: MenuRenderer = renderer
        self.use_stats_overlay: bool = use_stats_overlay
        self.use_hover_border: bool = use_hover_border
        self.use_hit_rects: bool = use_hit_rects

        self._last_tree: _MenuTree | None = None
        self._last_output_surf: pygame.Surface | None = None
        self._sample_start = time.perf_counter()
        self._counts = {"fps": 0, "composes": 0, "presents": 0}
        self._rates = {"fps": 0.0, "composes": 0.0, "presents": 0.0}

        self._font: pygame.font.Font | None = None
        self._overlay_cache: pygame.Surface | None = None
        self._overlay_key: tuple[tuple[str, str], ...] | None = None

    def __getattr__(self, name: str) -> Any:
        # Anything not overridden here behaves as on the wrapped renderer
        return getattr(self.renderer, name)

    # -------------------------------------------------------------------------

    def toggle_stats_overlay(self) -> bool:
        """Flip the stats overlay and return whether it is now shown."""
        self.use_stats_overlay = not self.use_stats_overlay
        return self.use_stats_overlay

    def toggle_hover_border(self) -> bool:
        """Flip the hover border and return whether it is now shown."""
        self.use_hover_border = not self.use_hover_border
        return self.use_hover_border

    def toggle_hit_rects(self) -> bool:
        """Flip the hit rect outlines and return whether they are now shown."""
        self.use_hit_rects = not self.use_hit_rects
        return self.use_hit_rects

    # -------------------------------------------------------------------------

    def render(self, menu: Menu, size: tuple[int, int]) -> pygame.Surface:
        output = self.renderer.render(menu, size)
        self._count_frame(output)
        if not (self.use_stats_overlay or self.use_hover_border or self.use_hit_rects):
            return output

        # The wrapped renderer reuses its output between frames, so drawing on it would leak into later frames
        output = output.copy()
        if self.use_hit_rects:
            self._draw_hit_rects(output, menu)
        if self.use_hover_border:
            self._draw_hover_border(output, menu)
        if self.use_stats_overlay:
            self._draw_stats_overlay(output, menu)
        return output

    def _draw_stats_overlay(self, output: pygame.Surface, menu: Menu) -> None:
        stats = self.get_stats()
        hovered = self.get_hovered_element(menu)
        mb = 1024 * 1024
        rows = (
            ("FPS", f"{stats['fps']:.0f}"),
            ("menu", type(menu).__name__),
            ("elements", f"{stats['elements']:.0f} ({stats['selectable']:.0f} selectable)"),
            ("composes/s", f"{stats['composes']:.1f}"),
            ("presents/s", f"{stats['presents']:.1f}"),
            ("text cache", f"{stats['text_cache_bytes'] / mb:.1f} MB"),
            ("box cache", f"{stats['box_cache_bytes'] / mb:.1f} MB"),
            ("shadow cache", f"{stats['shadow_cache_bytes'] / mb:.1f} MB"),
            ("hover", f"{hovered[0]!r} {hovered[1].width}x{hovered[1].height} at ({hovered[1].x}, {hovered[1].y})" if hovered is not None else "-"),
        )
        if self._overlay_cache is None or rows != self._overlay_key:
            self._overlay_cache = self._make_overlay_surf(rows)
            self._overlay_key = rows
        output.blit(self._overlay_cache, (_DEBUG_PADDING, _DEBUG_PADDING))

    def _make_overlay_surf(self, rows: tuple[tuple[str, str], ...]) -> pygame.Surface:
        if self._font is None:
            self._font = pygame.font.Font(None, 18)
        label_surfs = [self._font.render(label, True, "#A0A8B8") for label, _ in rows]
        value_surfs = [self._font.render(value, True, "#F0F0F0") for _, value in rows]

        # The default font is not monospaced, so values get their own column rather than space padding
        value_px = 3 * _DEBUG_PADDING + max(surf.get_width() for surf in label_surfs)
        line_ph = self._font.get_linesize()
        overlay_pw = value_px + max(surf.get_width() for surf in value_surfs) + _DEBUG_PADDING
        overlay_surf = pygame.Surface((overlay_pw, line_ph * len(rows) + 2 * _DEBUG_PADDING), pygame.SRCALPHA)
        overlay_surf.fill("#000000C0")
        for idx, (label_surf, value_surf) in enumerate(zip(label_surfs, value_surfs)):
            overlay_surf.blit(label_surf, (_DEBUG_PADDING, _DEBUG_PADDING + idx * line_ph))
            overlay_surf.blit(value_surf, (value_px, _DEBUG_PADDING + idx * line_ph))
        return overlay_surf

    def _draw_hover_border(self, output: pygame.Surface, menu: Menu) -> None:
        hovered = self.get_hovered_element(menu)
        if hovered is None:
            return
        rect = hovered[1].move(0, -int(round(menu._scroll))).clip(output.get_rect())
        if rect.width == 0 or rect.height == 0:
            return

        # White minus the pixels gives their inverse, made opaque so it also shows over a transparent output
        inverted_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        inverted_surf.fill("#FFFFFFFF")
        inverted_surf.blit(output.subsurface(rect), (0, 0), special_flags=pygame.BLEND_RGB_SUB)

        thickness = min(_DEBUG_BORDER_THICKNESS, rect.width, rect.height)
        strips = (
            pygame.Rect(0, 0, rect.width, thickness),
            pygame.Rect(0, rect.height - thickness, rect.width, thickness),
            pygame.Rect(0, 0, thickness, rect.height),
            pygame.Rect(rect.width - thickness, 0, thickness, rect.height),
        )
        for strip in strips:
            output.blit(inverted_surf, (rect.x + strip.x, rect.y + strip.y), strip)

    def _draw_hit_rects(self, output: pygame.Surface, menu: Menu) -> None:
        tree = self.renderer._menu_tree
        if tree is None or tree.menu is not menu:
            return
        scroll_py = int(round(menu._scroll))
        for _, rect in tree.hit_rects:
            pygame.draw.rect(output, _DEBUG_HIT_RECT_COLOR, rect.move(0, -scroll_py), 1)

    # -------------------------------------------------------------------------

    def get_stats(self) -> dict[str, float]:
        """Frames, recomposes and presents per second, element counts and cache memory, as of the last sample."""
        tree = self.renderer._menu_tree
        return {
            **self._rates,
            "elements": len(tree.element_rects) if tree is not None else 0,
            "selectable": len(tree.hit_rects) if tree is not None else 0,
            "text_cache_bytes": self.renderer._text_cache.nbytes,
            "box_cache_bytes": self.renderer._box_cache.nbytes,
            "shadow_cache_bytes": self.renderer._shadow_cache.nbytes,
        }

    def _count_frame(self, output: pygame.Surface) -> None:
        tree = self.renderer._menu_tree
        self._counts["fps"] += 1
        if tree is not self._last_tree:
            self._counts["composes"] += 1
            self._last_tree = tree
        if output is not self._last_output_surf:
            self._counts["presents"] += 1
            self._last_output_surf = output

        now = time.perf_counter()
        elapsed = now - self._sample_start
        if elapsed >= _DEBUG_SAMPLE_SECONDS:
            self._rates = {name: count / elapsed for name, count in self._counts.items()}
            self._counts = dict.fromkeys(self._counts, 0)
            self._sample_start = now

    # -------------------------------------------------------------------------

    def get_hovered_element(self, menu: Menu) -> tuple[Element, pygame.Rect] | None:
        """The deepest element under the mouse and its facade rect, or ``None``."""
        tree = self.renderer._menu_tree
        if tree is None or tree.menu is not menu or not pygame.mouse.get_focused():
            return None
        mouse_px, mouse_py = pygame.mouse.get_pos()
        facade_pos = (mouse_px, mouse_py + int(round(menu._scroll)))
        for element, rect in reversed(tree.element_rects):
            if rect.collidepoint(facade_pos):
                return element, rect
        return None


# -----------------------------------------------------------------------------


# TODO: Consider moving these to their own space, out of this file

def _color(rgba: RGBA, alpha: int = 0xFF) -> pygame.Color:
    color = pygame.Color(rgba)
    color.a = max(0, min(255, int(color.a * alpha / 255)))
    return color


def _make_surf(pw: int, ph: int) -> pygame.Surface:
    surf = pygame.Surface((max(0, pw), max(0, ph)), pygame.SRCALPHA)
    if pygame.display.get_surface():
        surf = surf.convert_alpha()
    return surf
