"""
menus.py
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
import math
import uuid

from .elements import (
    RGBA,
    AlignmentType,
    Element,
    JustifyType,
    Measure,
    MeasureType,
    VerticalDivision,
)


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
    _dscroll: float = 0.0
    _d2scroll: float = 0.0

    # Root division config — controls how elements are laid out inside the menu
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
    root_background_color: RGBA = "#0C0E14FF"
    root_background_alpha: int = 0xFF
    root_border_thickness: int = 0
    root_border_color: RGBA = "#00000000"
    root_is_flexible: bool = False
    root_is_selectable: bool = False
    root_is_visible: bool = True
 
    _div: VerticalDivision = field(init=False, repr=False, compare=False)
    _selected_index: int = field(init=False, repr=False, compare=False, default=0)

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

    """Scroll helpers"""

    def apply_scroll_impulse(self, accel: float) -> None:
        self._d2scroll += accel

    def integrate_scroll(self, max_scroll: float, dt: float, drag: float, deadzone: float) -> None:
        self._dscroll += self._d2scroll * dt
        self._dscroll *= math.exp(-drag * dt)

        if abs(self._dscroll) < deadzone:
            self._dscroll *= 0.5

        self._scroll += self._dscroll * dt

        if self._scroll < 0.0:
            if self._dscroll < 0:
                self._dscroll = 0.0
            self._scroll = 0.0
        elif self._scroll > max_scroll:
            if self._dscroll > 0:
                self._dscroll = 0.0
            self._scroll = max_scroll

        self._d2scroll = 0.0

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
