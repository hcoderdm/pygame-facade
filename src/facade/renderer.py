"""
renderer.py

MenuRenderer - draws a menu into a window-sized, transparent GUI surface
that the host game blits over its own frame.
"""

from __future__ import annotations

import pygame

from collections import deque
from collections.abc import Iterable
from dataclasses import replace
import math
from typing import Callable

from .assets import FontManager, ImageManager
from .elements import (
    RGBA,
    TRANSPARENT,
    AlignmentType,
    Button,
    Element,
    Fill,
    Gap,
    HorizontalDivision,
    Image,
    InputField,
    JustifyType,
    MeasureType,
    OverflowType,
    RotationType,
    Selector,
    Slider,
    Text,
    TextDecorationTypes,
    Toggle,
    VerticalDivision,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .menus import MenuType


_PRECISION = 4

_SCROLLBAR_WIDTH = 10
_SCROLLBAR_MIN_HEIGHT = 32


class ContentNode:
    """
    Represents a node in the UI element tree, holding an element, its
    pygame.Surface, an offset position, and a list of child ContentNode
    instances.
    """

    def __init__(self, element=None, surf=None, offset=None, children=None):
        self.element: Element = element or Element()
        self.surf: pygame.Surface = surf or blank_surf()
        self.offset: tuple[int, int] = offset or (0, 0)
        self.children: list[ContentNode] = children or []


class MenuRenderer:
    """
    Composes a menu's element tree and returns it as a GUI surface.

    The window must already exist (``pygame.display.set_mode``) before
    rendering, because surfaces are converted to the display format. Fonts
    and images are looked up through this renderer's own ``fonts`` and
    ``images`` managers.
    """

    def __init__(self) -> None:

        # Asset registries owned by this renderer
        self.fonts: FontManager = FontManager()
        self.images: ImageManager = ImageManager()

        # Dispatch table that maps element types to composer functions
        self._NODE_COMPOSERS: dict[type[Element], Callable[..., ContentNode]] = {
            Button: self._compose_button_node,
            Gap: self._compose_gap_node,
            HorizontalDivision: self._compose_division_node,
            VerticalDivision: self._compose_division_node,
            InputField: self._compose_input_field_node,
            Text: self._compose_text_node,
            Toggle: self._compose_toggle_node,
            Fill: self._compose_fill_node,
            Image: self._compose_image_node,
            Slider: self._compose_slider_node,
            Selector: self._compose_selector_node,
        }

        # Composed menu, rebuilt only when an element, the size or the menu changes
        self._menu_tree_cache: ContentNode | None = None
        self._menu_rect_cache: list[tuple[Element, pygame.Rect, int]] = []  # (element, rect, depth)
        self._text_cache: dict[tuple, pygame.Surface] = {}
        self._hex_color_cache: dict[str, pygame.Color] = {}
        self._menu_surf_cache: pygame.Surface | None = None
        self._last_version: int = -1
        self._last_display_size: tuple[int, int] = (0, 0)
        self._last_menu: object = None

        # Final GUI surface, re-blitted only when the view (scroll, cursor) changes
        self._output_cache: pygame.Surface | None = None
        self._output_key: tuple | None = None

    def render(self, menu: MenuType, size: tuple[int, int]) -> pygame.Surface:
        """
        Return a ``size``-sized ``SRCALPHA`` surface showing ``menu``.

        Pixels outside the menu are fully transparent, and the menu's own
        alpha (e.g. a half-transparent Pause background) is kept, so the
        surface can be blitted at ``(0, 0)`` over the game's frame. The same
        surface object is returned while nothing has changed.
        """

        display_pw, display_ph = size

        # Compose and render the menu tree, skipping if nothing has changed
        can_use_cache = self._menu_surf_cache is not None and Element._iterative_version == self._last_version and (display_pw, display_ph) == self._last_display_size and menu is self._last_menu
        if not can_use_cache:
            menu_tree = self._compose_menu_tree(menu, display_pw, display_ph)
            self._menu_tree_cache = menu_tree
            self._collect_element_layout(menu_tree)
            self._menu_surf_cache = self._render_element_tree(menu_tree)
            self._last_version = Element._iterative_version
            self._last_display_size = (display_pw, display_ph)
            self._last_menu = menu
        menu_surf = self._menu_surf_cache
        assert menu_surf is not None

        # Keep the scroll position within the content
        content_height = menu_surf.get_height()
        max_scroll = max(0, content_height - display_ph)
        menu._scroll = min(max(menu._scroll, 0.0), float(max_scroll))
        scroll_y = int(round(menu._scroll))

        # Reuse the last GUI surface unless the visible content changed
        selected = menu.get_selected_element()
        cursor = selected.get_cursor() if isinstance(selected, InputField) else ""
        output_key = (id(menu_surf), Element._iterative_version, (display_pw, display_ph), scroll_y, cursor)
        if self._output_cache is not None and output_key == self._output_key:
            return self._output_cache

        # Copy the visible part exactly; MAX against a zeroed surface avoids
        # darkening semi-transparent pixels as a normal alpha blit would
        output = pygame.Surface((display_pw, display_ph), pygame.SRCALPHA)
        view_rect = pygame.Rect(0, scroll_y, display_pw, display_ph)
        source_rect = view_rect.clip(menu_surf.get_rect())
        if source_rect.width > 0 and source_rect.height > 0:
            output.blit(menu_surf, (0, 0), source_rect, special_flags=pygame.BLEND_RGBA_MAX)

        self._draw_scrollbar(output, content_height, display_ph, scroll_y, max_scroll)

        self._output_cache = output
        self._output_key = output_key
        return output

    def scroll(self, menu: MenuType | None, display_size: tuple[int, int], wheel_delta_y: float, dt: float=0.00833) -> None:
        """Adjust the active menu scroll offset based on mouse wheel input."""

        if menu is None:
            return

        _SCROLL_ACCEL = 10000.0  # pixels/s^2 applied per wheel notch

        display_pw, display_ph = display_size
        menu_tree = self._menu_tree_cache
        if menu_tree is None:
            return
        max_scroll = max(0, menu_tree.surf.get_height() - display_ph)

        menu.apply_scroll_impulse(-float(wheel_delta_y) * _SCROLL_ACCEL)
        menu.integrate_scroll(max_scroll, dt, 0.0, 0.1)

    def select_element_at(self, menu: MenuType, pos: tuple[int, int]) -> Element | None:
        """Return the deepest element under *pos* and update the menu selection if possible."""

        if menu is None:
            return None

        elements = self.find_elements_at(menu, pos)
        if elements != [] and elements[0].is_selectable:
            menu.select_element_by_id(elements[0].id)
            return elements[0]
        return None

    def find_elements_at(self, menu: MenuType, pos: tuple[int, int]) -> list[Element]:
        """Return all elements under window position *pos*, deepest first."""

        if self._menu_tree_cache is None or menu is not self._last_menu:
            return []

        if not self._menu_rect_cache:
            self._collect_element_layout(self._menu_tree_cache)

        # Window coordinates -> menu content coordinates
        content_pos = (pos[0], pos[1] + int(round(menu._scroll)))

        collided_elements = []
        for element, rect, _depth in reversed(self._menu_rect_cache):
            if rect.collidepoint(content_pos):
                collided_elements.append(element)

        return collided_elements

    def _render_element_tree(self, root: ContentNode) -> pygame.Surface:
        """Render the entire element tree onto a single surface and return it."""

        root_surf = root.surf
        root_pw, root_ph = root.surf.size
        element_stack = deque([(root, (0, 0), 0)])
        while element_stack:
            node, root_position, depth = element_stack.popleft()  # O(1)

            absolute_px = root_position[0] + node.offset[0]
            absolute_py = root_position[1] + node.offset[1]

            # The root is the canvas itself; blitting it onto itself would
            # apply its background alpha twice
            if node is root:
                for child in node.children:
                    element_stack.append((child, (absolute_px, absolute_py), depth + 1))
                continue

            # Render the node's shadow here, so that content overlays it
            shadow_surf = self._draw_shadow(node.element, node.surf)
            shadow_offset_px, shadow_offset_py = self._resolve_measure(node.element.shadow_offset, node.element.shadow_offset_measure, node.surf.width, node.surf.height)

            # Handle fixed elements, no adjustment for flow
            if node.element.is_fixed:
                content_pw, content_ph = node.surf.size
                offset_pw, offset_ph = 0, 0

                # Horizontal alignment of stacked child surfs
                if node.element.alignment in (AlignmentType.TOPLEFT, AlignmentType.MIDLEFT, AlignmentType.BOTTOMLEFT):
                    offset_pw = 0
                elif node.element.alignment in (AlignmentType.MIDTOP, AlignmentType.CENTER, AlignmentType.MIDBOTTOM):
                    offset_pw = max(0, (root_pw - content_pw) // 2)
                elif node.element.alignment in (AlignmentType.TOPRIGHT, AlignmentType.MIDRIGHT, AlignmentType.BOTTOMRIGHT):
                    offset_pw = max(0, root_pw - content_pw)

                # Vertical alignment of stacked child surfs
                if node.element.alignment in (AlignmentType.TOPLEFT, AlignmentType.MIDTOP, AlignmentType.TOPRIGHT):
                    offset_ph = 0
                elif node.element.alignment in (AlignmentType.MIDLEFT, AlignmentType.CENTER, AlignmentType.MIDRIGHT):
                    offset_ph = max(0, (root_ph - content_ph) // 2)
                elif node.element.alignment in (AlignmentType.BOTTOMLEFT, AlignmentType.MIDBOTTOM, AlignmentType.BOTTOMRIGHT):
                    offset_ph = max(0, root_ph - content_ph)

                root_surf.blit(shadow_surf, (offset_pw + shadow_offset_px, offset_ph + shadow_offset_py))
                root_surf.blit(node.surf, (offset_pw, offset_ph))
            else:
                # Render the node's shadow and surface onto the root
                root_surf.blit(shadow_surf, (absolute_px + shadow_offset_px, absolute_py + shadow_offset_py))
                root_surf.blit(node.surf, (absolute_px, absolute_py))

            for child in node.children:
                element_stack.append((child, (absolute_px, absolute_py), depth + 1))

        return root_surf

    def _collect_element_layout(self, root: ContentNode) -> None:
        """Populate _element_layout without performing any blits."""

        self._menu_rect_cache = []
        element_stack: list[tuple[ContentNode, tuple[int, int], int]] = [(root, (0, 0), 0)]
        while element_stack:
            node, root_position, depth = element_stack.pop()

            absolute_px = root_position[0] + node.offset[0]
            absolute_py = root_position[1] + node.offset[1]

            if node.element.is_selectable:
                hit_element = getattr(node.element, "_interaction_target", node.element)
                node_rect = pygame.Rect(absolute_px, absolute_py, node.surf.get_width(), node.surf.get_height())
                self._menu_rect_cache.append((hit_element, node_rect, depth))

            for child in node.children:
                element_stack.append((child, (absolute_px, absolute_py), depth + 1))

        self._menu_rect_cache.sort(key=lambda item: item[2], reverse=True)

    """
    Separate renderers.
    """

    def _draw_shadow(
        self,
        element: Element,
        element_surf: pygame.Surface,
    ) -> pygame.Surface:
        """
        Generates a shadow surface for the given element based on its shadow
        color, alpha, and scale properties. Returns a blank surface if the
        shadow would be invisible. Uses a mask of element_surf to create and
        optionally scale the shadow, applying the specified color and
        transparency.
        """

        # Do not create a shadow if it will not be seen
        if element.shadow_color == TRANSPARENT or element.shadow_alpha == 0x0:
            return blank_surf()

        # Create a mask of the element to use for shadow
        mask = pygame.mask.from_surface(element_surf)

        # Scale shadow if needed
        if element.shadow_scale != 1:
            mask_surf = mask.to_surface(
                setcolor=(255, 255, 255),
                unsetcolor=(0, 0, 0, 0),
            )
            original_width, original_height = element_surf.get_size()
            shadow_width = int(original_width * element.shadow_scale)
            shadow_height = int(original_height * element.shadow_scale)
            mask_surf = pygame.transform.smoothscale(mask_surf, (shadow_width, shadow_height))
            mask = pygame.mask.from_surface(mask_surf)

        shadow_surf = mask.to_surface(
            setcolor=element.shadow_color,
            unsetcolor=(0, 0, 0, 0),
        )
        shadow_surf.set_alpha(element.shadow_alpha)
        return shadow_surf

    def _draw_scrollbar(self, viewport: pygame.Surface, content_height: int, viewport_height: int, scroll_y: float, max_scroll: float) -> None:
        if content_height <= viewport_height:
            return

        track_x = viewport.get_width() - _SCROLLBAR_WIDTH
        track_rect = pygame.Rect(track_x, 0, _SCROLLBAR_WIDTH, viewport_height)
        pygame.draw.rect(viewport, "#181C2780", track_rect)

        thumb_height = max(_SCROLLBAR_MIN_HEIGHT, int(track_rect.height * (viewport_height / content_height)))
        thumb_travel = track_rect.height - thumb_height
        thumb_offset = 0 if max_scroll == 0 else int((scroll_y / max_scroll) * thumb_travel)
        thumb_rect = pygame.Rect(track_x, track_rect.y + thumb_offset, _SCROLLBAR_WIDTH, thumb_height)
        pygame.draw.rect(viewport, "#30384E80", thumb_rect)
        pygame.draw.rect(viewport, "#60606080", thumb_rect, 1)

    """
    Menu and element composition.
    """

    def _compose_menu_tree(self, menu: MenuType, display_pw: int, display_ph: int) -> ContentNode:
        """ """

        root_division: VerticalDivision = menu._div
        root_node = self._compose_element_node(
            root_division,
            range(display_pw, display_pw),
            range(display_ph, display_ph),
            selection_id=menu.get_selection_id(),
        )

        return root_node

    def _compose_element_node(
        self,
        element: Element,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """ """

        if not element.is_visible:
            return ContentNode(element)

        # Resolve dataclass parameter values into pixels
        overflow_mode = element.overflow
        extends = overflow_mode == OverflowType.EXTEND
        clips = overflow_mode == OverflowType.CLIP
        overflows = overflow_mode == OverflowType.OVERFLOW
        size_pw, size_ph = self._resolve_measure(
            element.size,
            element.size_measure,
            range_pw.stop,
            range_ph.stop,
        )
        anchor_pw, anchor_ph = self._resolve_measure(
            element.anchor,
            element.anchor_measure,
            range_pw.stop,
            range_ph.stop,
        )
        margin_pw, margin_ph = self._resolve_measure(
            element.margin,
            element.margin_measure,
            range_pw.stop,
            range_ph.stop,
        )
        offset_pw, offset_ph = self._resolve_measure(
            element.offset,
            element.offset_measure,
            range_pw.stop,
            range_ph.stop,
        )
        padding_pw, padding_ph = self._resolve_measure(
            element.padding,
            element.padding_measure,
            range_pw.stop,
            range_ph.stop,
        )
        border_thickness = element.border_thickness

        # Update width range for content element
        decor_pw: int = 2 * (margin_pw + border_thickness + padding_pw)
        width_start: int = max(0, min(size_pw - decor_pw, range_pw.stop - decor_pw))
        width_stop: int = width_start if clips else max(0, range_pw.stop - decor_pw) if extends else width_start + 999 if overflows else 0
        content_range_pw: range = range(width_start, width_stop)

        # Update height range for content element
        decor_ph: int = 2 * (margin_ph + border_thickness + padding_ph)
        height_start: int = max(0, min(size_ph - decor_ph, range_ph.stop - decor_ph))
        height_stop: int = height_start if clips else max(0, range_ph.stop - decor_ph) if extends else height_start + 999 if overflows else 0
        content_range_ph: range = range(height_start, height_stop)

        content_node = self._compose_content_node(
            element,
            content_range_pw,
            content_range_ph,
            selection_id,
        )
        content_element = content_node.element
        content_pw, content_ph = content_node.surf.size
        # TODO: offset is not handled as well as it could be
        content_node.offset = (offset_pw, offset_ph)

        if clips:
            clip_coords = (0, 0, range_pw.start, range_pw.stop)
            content_node.surf = content_node.surf.subsurface(clip_coords).copy()

        inner_pw, inner_ph = content_range_pw.start, content_range_ph.start

        def get_children_size(node: ContentNode) -> tuple[int, int]:
            """Compute total width and height of node including all descendants."""
            child_pw, child_ph = node.surf.get_size()
            for c in node.children:
                cw, ch = get_children_size(c)
                child_pw = max(child_pw, c.offset[0] + cw)
                child_ph = max(child_ph, c.offset[1] + ch)
            return child_pw, child_ph

        total_pw, total_ph = get_children_size(content_node)
        if extends:
            inner_pw = max(inner_pw, total_pw)
            inner_ph = max(inner_ph, total_ph)

        # Position content within the inner area according to element.alignment.
        # Use total_pw/ph (bounding box of all children) because many composers
        # return a blank_surf() (0x0) and store visuals entirely in child nodes.
        alignment_offset_pw, alignment_offset_ph = 0, 0

        # Horizontal alignment
        if element.alignment in (AlignmentType.MIDTOP, AlignmentType.CENTER, AlignmentType.MIDBOTTOM):
            alignment_offset_pw = max(0, (inner_pw - total_pw) // 2)
        elif element.alignment in (AlignmentType.TOPRIGHT, AlignmentType.MIDRIGHT, AlignmentType.BOTTOMRIGHT):
            alignment_offset_pw = max(0, inner_pw - total_pw)

        # Vertical alignment
        if element.alignment in (AlignmentType.MIDLEFT, AlignmentType.CENTER, AlignmentType.MIDRIGHT):
            alignment_offset_ph = max(0, (inner_ph - total_ph) // 2)
        elif element.alignment in (AlignmentType.BOTTOMLEFT, AlignmentType.MIDBOTTOM, AlignmentType.BOTTOMRIGHT):
            alignment_offset_ph = max(0, inner_ph - total_ph)

        content_node.offset = (decor_pw // 2 + alignment_offset_pw + offset_pw, decor_ph // 2 + alignment_offset_ph + offset_ph)

        # Set up to apply decorations to the element
        final_pw = inner_pw + decor_pw
        final_ph = inner_ph + decor_ph
        final_surf = pygame.Surface((final_pw, final_ph), pygame.SRCALPHA)
        border_rect = pygame.Rect(margin_pw, margin_ph, final_pw - 2 * margin_pw, final_ph - 2 * margin_ph)
        background_rect = border_rect.inflate(-2 * border_thickness, -2 * border_thickness)

        # Draw border decoration
        if border_rect.width > 0 and border_rect.height > 0 and border_thickness > 0:
            border_color = self._apply_alpha(self._parse_hex_color(content_element.border_color), content_element.border_alpha)
            pygame.draw.rect(final_surf, border_color, border_rect)

        # Draw background decoration
        if background_rect.width > 0 and background_rect.height > 0:
            bg_color = self._apply_alpha(self._parse_hex_color(content_element.background_color), content_element.background_alpha)
            pygame.draw.rect(final_surf, bg_color, background_rect)

        # Compose a final element node
        element_node = ContentNode(content_element, final_surf, (offset_pw, offset_ph), children=[content_node])

        # TODO: Should be fixed to function correctly
        def rotate_subtree(node: ContentNode, rotation: RotationType):
            x, y = node.offset
            if rotation == RotationType.LEFT:
                node.surf = pygame.transform.rotate(node.surf, 90)
                node.offset = (-y, x)
            elif rotation == RotationType.RIGHT:
                node.surf = pygame.transform.rotate(node.surf, -90)
                node.offset = (y, -x)
            elif rotation == RotationType.UPTURNED:
                node.surf = pygame.transform.rotate(node.surf, 180)
                node.offset = (-x, -y)

            for child in node.children:
                rotate_subtree(child, rotation)

        # Handle rotation on final element
        rotate_subtree(element_node, element.rotation)

        # Set element surf to this final composed surface
        return element_node

    """
    Content rendering.
    """

    def _compose_content_node(
        self,
        element: Element,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:

        if range_pw.stop == 0 and range_ph.stop == 0:
            return ContentNode()

        # Match the current element to its associated renderer by walking the MRO,
        # so subclasses fall back to the nearest registered parent composer.
        renderer: Callable[..., ContentNode] | None = None
        for cls in type(element).mro():
            renderer = self._NODE_COMPOSERS.get(cls)
            if renderer is not None:
                break

        if renderer is not None:
            return renderer(
                element,
                range_pw,
                range_ph,
                selection_id,
            )
        return ContentNode()

    def _compose_division_node(
        self,
        element: HorizontalDivision | VerticalDivision,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """
        Constructs a ContentNode for a horizontal or vertical division element
        by arranging its visible child elements with appropriate gaps,
        alignment, and offsets, based on available and restricted dimensions and
        selection state. Returns a node representing the composed division and
        its children.
        """

        is_selected = selection_id == element.id

        # Resolve gap parameter with respect to parent
        gap_pw, gap_ph = self._resolve_measure(
            element.gap,
            element.gap_measure,
            range_pw.stop,
            range_ph.stop,
        )

        # Collect child surfaces by collecting their nodes and accumulate size
        child_nodes: list[ContentNode] = []
        division_pw, division_ph = 0, 0
        for child in element.elements:
            if not child.is_visible:
                continue
            node = self._compose_element_node(
                child,
                range_pw,
                range_ph,
                selection_id if not is_selected else child.id,
            )
            child_nodes.append(node)

            # Do not evaluate for fixed elements
            if element.is_fixed:
                continue

            if isinstance(element, HorizontalDivision):
                division_pw += node.surf.width
                if len(child_nodes) > 1:
                    division_pw += gap_pw
                division_ph = max(division_ph, node.surf.height)

            elif isinstance(element, VerticalDivision):  # VerticalDivision
                division_ph += node.surf.height
                if len(child_nodes) > 1:
                    division_ph += gap_ph
                division_pw = max(division_pw, node.surf.width)

        if not child_nodes:
            return ContentNode(element, blank_surf())

        # Apply offsets to child nodes with respect to parent division
        node_offset_pw, node_offset_ph = 0, 0
        for node in child_nodes:

            # Do not evaluate for fixed elements
            if node.element.is_fixed:
                continue

            if isinstance(element, HorizontalDivision):
                if node.element.justify == JustifyType.START:
                    node_offset_ph = 0
                elif node.element.justify == JustifyType.CENTER:
                    node_offset_ph = (division_ph - node.surf.height) // 2
                elif node.element.justify == JustifyType.END:
                    node_offset_ph = division_ph - node.surf.height
                node.offset = (node_offset_pw, node_offset_ph)
                node_offset_pw += node.surf.width + gap_pw

            elif isinstance(element, VerticalDivision):
                if node.element.justify == JustifyType.START:
                    node_offset_pw = 0
                elif node.element.justify == JustifyType.CENTER:
                    node_offset_pw = (division_pw - node.surf.width) // 2
                elif node.element.justify == JustifyType.END:
                    node_offset_pw = division_pw - node.surf.width
                node.offset = (node_offset_pw, node_offset_ph)
                node_offset_ph += node.surf.height + gap_ph

        # Compose computed value and return division node
        return ContentNode(element, blank_surf(), children=child_nodes)

    def _compose_gap_node(
        self,
        element: Text,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """
        Creates a ContentNode representing a gap by generating a blank surface
        of the specified restricted size, filling it with the background color
        and alpha from the given element.
        """
        gap_surf = blank_surf((range_pw.start, range_ph.start))
        gap_surf.fill(element.background_color)
        gap_surf.set_alpha(element.background_alpha)
        return ContentNode(element, gap_surf)

    def _compose_text_node(
        self,
        element: Text,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """ """
        text_surf = self._make_text_surf(element, wraplength=range_pw.stop)
        return ContentNode(element, text_surf)

    def _compose_button_node(
        self,
        element: Button,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """
        Creates a ContentNode for a button element by composing its text node,
        determining selection state, and generating a blank surface sized to the
        text. The resulting node represents the button with its child text node.
        """

        is_selected = selection_id == element.id
        render_element = element if not is_selected else replace(element, label=replace(element.label, text_color=element.selected_text_color))
        render_element._interaction_target = element  # ensure clicks map to original element

        text_selection_id = render_element.label.id if is_selected else selection_id
        text_child = self._compose_element_node(render_element.label, range_pw, range_ph, text_selection_id)
        return ContentNode(render_element, blank_surf(), children=[text_child])

    def _compose_input_field_node(
        self,
        element: InputField,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """ """
        is_selected = selection_id == element.id
        eff_element = replace(element, border_color=element.selected_border_color) if is_selected else element
        text_child = replace(element.value, text=element.get_field() + element.get_cursor())
        eff_value_child = replace(text_child, text_decorations=TextDecorationTypes.ITALIC | TextDecorationTypes.ANTIALIASING) if element.is_open else replace(text_child, text_color=element.edited_text_color) if element.is_opened else text_child
        eff_value_child = replace(eff_value_child, text_color=element.invalid_text_color) if not element.authenticate() else replace(eff_value_child, text_color=element.edited_text_color) if element.is_altered() else eff_value_child
        text_selection_id = eff_element.label.id if is_selected else selection_id
        hint_node = self._compose_element_node(eff_element.hint, range_pw, range_ph, text_selection_id) if len(element.get_field()) == 0 else None
        text_node = self._compose_element_node(eff_value_child, range_pw, range_ph, text_selection_id)
        eff_element._interaction_target = element  # ensure clicks map to original element
        return ContentNode(eff_element, blank_surf(), children=[hint_node, text_node] if hint_node else [text_node])

    def _compose_toggle_node(
        self,
        element: Toggle,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """"""
        is_selected = selection_id == element.id
        eff_element = replace(element, border_color=element.selected_border_color) if is_selected else element
        eff_label = replace(element.label, text=element.toggled_text) if element.value else element.label
        eff_label = replace(eff_label, text_color=element.edited_text_color) if element.is_called else eff_label
        label_node = self._compose_element_node(eff_label, range_pw, range_ph, selection_id)
        eff_element._interaction_target = element  # route clicks on children to the toggle
        return ContentNode(eff_element, blank_surf(), children=[label_node])

    def _compose_fill_node(
        self,
        element: Fill,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """"""
        fill_surf = blank_surf((range_pw.stop, range_ph.stop))
        return ContentNode(element, fill_surf)

    def _compose_image_node(
        self,
        element: Image,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        """"""
        image_surf = self.images.get_image(element.image_path)
        return ContentNode(element, image_surf)

    def _compose_slider_node(
        self,
        element: Image,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        image_surf = blank_surf((1, 1))
        return ContentNode(element, image_surf)

    def _compose_selector_node(
        self,
        element: Selector,
        range_pw: range,
        range_ph: range,
        selection_id: str | None,
    ) -> ContentNode:
        is_selected = selection_id == element.id
        eff_element = replace(element, border_color=element.selected_border_color) if is_selected else element
        eff_element._interaction_target = element

        selection_text = eff_element.selection_text
        selection_text = replace(selection_text, text=element.selection())
        selection_text = replace(selection_text, text_decorations=TextDecorationTypes.ITALIC | TextDecorationTypes.ANTIALIASING) if element.is_open else selection_text
        selection_text = replace(selection_text, text_color=eff_element.altered_selection_color) if element.is_altered() else selection_text

        left_arrow = eff_element.left_arrow
        left_arrow = replace(left_arrow, text_color=eff_element.disabled_arrow_color) if element.buffer_index() == 0 else left_arrow

        right_arrow = eff_element.right_arrow
        right_arrow = replace(right_arrow, text_color=eff_element.disabled_arrow_color) if element.buffer_index() == len(element.selections) - 1 else right_arrow

        div_element = HorizontalDivision(elements=[left_arrow, selection_text, right_arrow])
        # left_arrow_node = self._compose_element_node(element.left_arrow, range_pw, range_ph, selection_id)
        # right_arrow_node = self._compose_element_node(element.right_arrow, range_pw, range_ph, selection_id)
        # selection_node = self._compose_element_node(element.selection_text, range_pw, range_ph, selection_id)
        div_node = self._compose_element_node(div_element, range_pw, range_ph, selection_id)
        return ContentNode(eff_element, blank_surf(), children=[div_node])

    """
    Utility helpers
    """

    def _make_text_surf(self, text_element: Text, text_color=None, background_color=None, wraplength=None) -> pygame.Surface:
        """Render a ``Text`` element's string to a surface."""
        wrap_px = (wraplength if text_element.is_wrapable else 0) or 0
        effective_text_color = text_color or text_element.text_color
        cache_key = (
            text_element.font_path,
            text_element.font_size,
            text_element.text,
            effective_text_color,
            background_color,
            text_element.text_background,
            text_element.text_decorations,
            wrap_px,
            text_element.is_wrapable,
            text_element.text_alpha,
        )
        cached = self._text_cache.get(cache_key)
        if cached is not None:
            return cached

        font = self.fonts.get_font(text_element.font_path, text_element.font_size)
        format = text_element.text_decorations
        self._apply_text_format(font, format)
        antialias = bool(format & TextDecorationTypes.ANTIALIASING)
        text = font.render(
            text_element.text or "",
            antialias,
            effective_text_color,
            background_color or None,
            wrap_px,
        ).convert_alpha()
        self._reset_text_format(font)
        trim = 2 * int(text_element.font_size / 18) if len(text_element.text) > 0 and text_element.text[-1].isupper() else 0

        surf = blank_surf((text.width - trim, text.height))
        if text_element.text_background != TRANSPARENT:
            bg_color = pygame.Color(text_element.text_background)
            surf.fill(bg_color)

        surf.blit(text, (0, 0))
        surf.set_alpha(text_element.text_alpha)
        self._text_cache[cache_key] = surf
        return surf

    def _parse_hex_color(self, rgba: RGBA):
        """
        Parses a hex RGBA color string (e.g., #RRGGBBAA) into a tuple of four
        integers (r, g, b, a), caching results for efficiency. Returns the
        cached tuple if available.
        """

        if rgba not in self._hex_color_cache:
            c = rgba.lstrip("#")
            r, g, b, a = (int(c[i : i + 2], 16) for i in (0, 2, 4, 6))
            self._hex_color_cache[rgba] = pygame.Color(r, g, b, a)
        return self._hex_color_cache[rgba]

    @staticmethod
    def _apply_text_format(font: pygame.font.Font, format: TextDecorationTypes | None) -> None:
        """Set bold/italic/underline/strikethrough on *font*."""
        if format is None:
            return
        font.set_bold(bool(format & TextDecorationTypes.BOLD))
        font.set_italic(bool(format & TextDecorationTypes.ITALIC))
        font.set_underline(bool(format & TextDecorationTypes.UNDERLINE))
        font.set_strikethrough(bool(format & TextDecorationTypes.STRIKETHROUGH))

    @staticmethod
    def _reset_text_format(font: pygame.font.Font) -> None:
        """Clear all style flags so the cached font is left clean."""
        font.set_bold(False)
        font.set_italic(False)
        font.set_underline(False)
        font.set_strikethrough(False)

    @staticmethod
    def _resolve_measure(
        value: Iterable[float | int],
        measure: MeasureType,
        available_pw: int,
        available_ph: int,
    ) -> tuple[int, int]:
        """Resolve a MEASURE value to pixel coordinates."""
        pixel_x, pixel_y = value

        if measure == MeasureType.ABSOLUTE:
            return int(pixel_x), int(pixel_y)
        elif measure == MeasureType.RELATIVE:
            return (
                math.floor(round(pixel_x * available_pw, _PRECISION)),
                math.floor(round(pixel_y * available_ph, _PRECISION)),
            )

        return int(pixel_x), int(pixel_y)

    @staticmethod
    def _apply_alpha(color: pygame.Color, alpha_factor: float) -> pygame.Color:
        """ """
        new_alpha = max(0, min(255, int(color.a * alpha_factor / 255)))
        return pygame.Color(color.r, color.g, color.b, new_alpha)


_blank_surf_cache: pygame.Surface | None = None


def blank_surf(size=(0, 0), flags=0, convert=True):
    global _blank_surf_cache

    surf_pw, surf_ph = (max(0, int(size[0])), max(0, int(size[1])))

    # Return cached empty surface
    if surf_pw == 0 and surf_ph == 0:
        if _blank_surf_cache is None:
            # TODO: Add support for None to save for efficiency
            _blank_surf_cache = pygame.Surface((0, 0), pygame.SRCALPHA).convert_alpha()
        return _blank_surf_cache.copy()

    surf = pygame.Surface((surf_pw, surf_ph), pygame.SRCALPHA | flags)

    # Only convert if a display surface exists
    if convert and pygame.display.get_surface():
        surf = surf.convert_alpha()

    return surf
