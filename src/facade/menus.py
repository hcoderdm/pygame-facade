"""
menus.py
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
import uuid

from .elements import (
    Color,
    AlignmentType,
    Element,
    JustifyType,
    Measure,
    MeasureType,
    VerticalDivision,
)
from .theme import ThemeColorType


@dataclass(kw_only=True)
class Menu(ABC):
    """
    Represents an abstract menu type with configurable layout, scrolling,
    and selection logic. Manages a root container of elements, supports
    smooth scrolling, and provides methods to navigate and select among
    selectable elements.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    _scroll: float = 0.0

    # Root division config — controls how elements are laid out inside the menu.
    root_elements: list[Element] = field(default_factory=list)
    root_justify: JustifyType = JustifyType.CENTER
    root_alignment: AlignmentType = AlignmentType.TOPLEFT
    root_size: Measure = (1.0, 1.0)
    root_anchor: Measure = (0.0, 0.0)
    root_margin: Measure = (0.0, 0.0)
    root_offset: Measure = (0.0, 0.0)
    root_padding: Measure = (16.0, 16.0)
    root_gap: Measure = (8.0, 8.0)
    root_size_measure = MeasureType.RELATIVE
    root_anchor_measure = MeasureType.ABSOLUTE
    root_margin_measure = MeasureType.ABSOLUTE
    root_offset_measure = MeasureType.ABSOLUTE
    root_padding_measure = MeasureType.ABSOLUTE
    root_gap_measure = MeasureType.ABSOLUTE
    root_background_color: Color = ThemeColorType.BACKGROUND
    root_background_alpha: int = 0xFF
    root_border_thickness: int = 0
    root_border_color: Color = "#00000000"
    root_is_selectable: bool = False
    root_is_visible: bool = True
    # A menu drawn at fixed sizes, such as one already built large, ignores the renderer's scale.
    is_scaled: bool = True
 
    _div: VerticalDivision = field(init=False, repr=False, compare=False)
    _selected_index: int = field(init=False, repr=False, compare=False, default=0)

    # The keys keep their place in ``_selected_index`` and the pointer has its own hover. Whichever was
    # used last is lit, so moving the mouse never loses the keyboard's place.
    _is_pointer_leading: bool = field(init=False, repr=False, compare=False, default=False)
    _hovered_id: str | None = field(init=False, repr=False, compare=False, default=None)
    _pointer_part: str | None = field(init=False, repr=False, compare=False, default=None)
    _pressed: tuple[str, str] | None = field(init=False, repr=False, compare=False, default=None)  # Element id and part held down.
    _key_anchor_pos: tuple[int, int] | None = field(init=False, repr=False, compare=False, default=None)  # Pointer position at the last key press.

    def __post_init__(self):
        self._div = VerticalDivision(
            elements=self.root_elements,
            justify=self.root_justify,
            alignment=self.root_alignment,
            size=self.root_size,
            anchor=self.root_anchor,
            margin=self.root_margin,
            offset=self.root_offset,
            padding=self.root_padding,
            gap=self.root_gap,
            size_measure=self.root_size_measure,
            anchor_measure=self.root_anchor_measure,
            margin_measure=self.root_margin_measure,
            offset_measure=self.root_offset_measure,
            padding_measure=self.root_padding_measure,
            gap_measure=self.root_gap_measure,
            background_color=self.root_background_color,
            background_alpha=self.root_background_alpha,
            border_thickness=self.root_border_thickness,
            border_color=self.root_border_color,
            is_selectable=self.root_is_selectable,
            is_visible=self.root_is_visible,
        )
        self._selected_index = 0

    # -------------------------------------------------------------------------

    @property
    def _selectable_elements(self) -> list[Element]:
        def walk(elements):
            for e in elements:
                if e.is_selectable:
                    yield e
                if hasattr(e, "elements") and e.elements:
                    yield from walk(e.elements)

        return list(walk(self.root_elements))

    def get_selected_element(self) -> Element | None:
        items = self._selectable_elements
        if not items:
            return None
        idx = self._selected_index % len(items)
        return items[idx]

    def get_selection_id(self) -> str | None:
        items = self._selectable_elements
        if not items:
            return None
        idx = self._selected_index % len(items)
        return items[idx].id

    def select_element_by_id(self, element_id: str) -> bool:
        for idx, element in enumerate(self._selectable_elements):
            if element.id == element_id:
                if self._selected_index != idx:
                    self._selected_index = idx
                    Element._render_version += 1
                return True
        return False

    def move_selected_down(self) -> None:
        items = self._selectable_elements
        if not items:
            return
        new_idx = min((self._selected_index + 1), len(items) - 1)
        if new_idx != self._selected_index:
            self._selected_index = new_idx
            Element._render_version += 1

    def move_selected_up(self) -> None:
        items = self._selectable_elements
        if not items:
            return
        new_idx = max((self._selected_index - 1), 0)
        if new_idx != self._selected_index:
            self._selected_index = new_idx
            Element._render_version += 1

    def move_selected_by(self, offset: int, is_wrapping: bool = True) -> None:
        """Move the selection ``offset`` places in reading order, wrapping past the ends when ``is_wrapping``."""
        items = self._selectable_elements
        if not items:
            return
        idx = self._selected_index % len(items) + offset
        new_idx = idx % len(items) if is_wrapping else max(0, min(idx, len(items) - 1))
        if new_idx != self._selected_index:
            self._selected_index = new_idx
            Element._render_version += 1

    # -------------------------------------------------------------------------

    def get_lit_id(self) -> str | None:
        """The element drawn with the focused look: the hovered one while the pointer leads, otherwise the selection."""
        return self._hovered_id if self._is_pointer_leading else self.get_selection_id()

    def set_pointer_leading(self, is_leading: bool) -> None:
        """Hand the lit look to the pointer's hover, or back to the keys' selection."""
        if is_leading != self._is_pointer_leading:
            self._is_pointer_leading = is_leading
            Element._render_version += 1

    def get_pointer_part(self) -> str | None:
        """The part of the hovered element under the pointer, ``""`` for none, or ``None`` while the keys lead."""
        return self._pointer_part if self._is_pointer_leading else None

    def set_hovered(self, element: Element | None, part: str = "") -> None:
        """Record the element under the pointer and the part of it there, or that the pointer is over nothing."""
        hovered_id = element.id if element is not None else None
        part_or_none = part if element is not None else None
        if (hovered_id, part_or_none) != (self._hovered_id, self._pointer_part):
            self._hovered_id, self._pointer_part = hovered_id, part_or_none
            Element._render_version += 1

    def get_pressed_part(self, element: Element) -> str | None:
        """The part of ``element`` held down by the pointer, or ``None``."""
        if self._pressed is not None and self._pressed[0] == element.id:
            return self._pressed[1]
        return None

    def set_pressed_part(self, element: Element | None, part: str = "") -> None:
        """Hold ``part`` of ``element`` down, or release whatever is held when ``element`` is ``None``."""
        # Holding looks the same as pointing, so nothing is redrawn.
        self._pressed = (element.id, part) if element is not None else None
