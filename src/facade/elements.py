"""
elements.py
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
import re
import time
from typing import Annotated, Any, Callable, ClassVar
import uuid


FLOAT_REGEX = r"^[+-]?(\d+(\.\d*)?|\.\d+)$"
INT_REGEX = r"^[+-]?\d+$"
LETTERS_REGEX = r"^[A-Za-z]+$"
ALPHANUMERIC_REGEX = r"^[A-Za-z0-9]+$"
RGBA_REGEX = r"^#[0-9a-fA-F]{8}$"
BOOL_REGEX = r"^[01]$"

RGBA = Annotated[str, f"regex:{RGBA_REGEX}"]
Measure = Annotated[tuple[float, float], ""]
Angle = Annotated[float, "radians", "range: [0, 2π]"]

COLOR_PALETTE_BASE: RGBA = "#0C0E14FF"  # Menu background
COLOR_PALETTE_SECONDARY: RGBA = "#181C27FF"  # Inside an input's box
COLOR_PALETTE_ACCENT: RGBA = "#EC4662FF"  # The selected element
COLOR_PALETTE_NEUTRAL: RGBA = "#30384EFF"  # Read-only boxes, unavailable parts and shadows
COLOR_PALETTE_TEXT: RGBA = "#E0E0E0FF"
COLOR_PALETTE_EDITED: RGBA = "#F0B443FF"  # A value that differs from the original
COLOR_PALETTE_BORDER: RGBA = "#606060FF"  # Border of read-only boxes
COLOR_PALETTE_MUTED: RGBA = "#6E7896FF"  # Secondary text, readable where NEUTRAL would vanish
COLOR_PALETTE_HEADING: RGBA = "#F0B443FF"  # Headings and picked-out words

TRANSPARENT: RGBA = "#00000000"
BLACK: RGBA = "#000000FF"
RED: RGBA = "#FF0000FF"
GREEN: RGBA = "#00FF00FF"
BLUE: RGBA = "#0000FFFF"
YELLOW: RGBA = "#FFFF00FF"
MAGENTA: RGBA = "#FF00FFFF"
CYAN: RGBA = "#00FFFFFF"
WHITE: RGBA = "#FFFFFFFF"

# The bundled pixel font draws one font pixel per screen pixel at 14px, and stays
# crisp only at whole multiples of it; other sizes give uneven strokes
NATIVE_FONT_SIZE: int = 14

# Every input shares one box: 8px capitals with 6px of padding and a 1px border on each side
_CONTROL_SIZE: Measure = (148.0, 22.0)
_CONTROL_PADDING: Measure = (6.0, 6.0)
_CONTROL_SHADOW_ALPHA: int = 0xB0

_UNSET = object()  # Marks an attribute not yet assigned on an instance


# -----------------------------------------------------------------------------


class MeasureType(Enum):
    """
    Represents types of measurement, with possible values ABSOLUTE and
    RELATIVE.
    """

    ABSOLUTE = auto()
    RELATIVE = auto()


class JustifyType(Enum):
    """
    Represents text justification options with three enum members: START,
    CENTER, and END. Use JustifyType to specify alignment in layouts or
    formatting contexts.
    """

    START = auto()
    CENTER = auto()
    END = auto()


class AlignmentType(Enum):
    """
    Represents possible alignment positions, such as TOPLEFT, CENTER, and
    BOTTOMRIGHT, for layout or positioning purposes.
    """

    TOPLEFT = auto()
    MIDTOP = auto()
    TOPRIGHT = auto()
    MIDLEFT = auto()
    CENTER = auto()
    MIDRIGHT = auto()
    BOTTOMLEFT = auto()
    MIDBOTTOM = auto()
    BOTTOMRIGHT = auto()


class TextDecorationType(Flag):
    """
    Represents a set of text decoration options using a flag enumeration,
    including NONE, ANTIALIASING, BOLD, ITALIC, STRIKETHROUGH, and
    UNDERLINE. Multiple decorations can be combined using bitwise
    operations.
    """

    NONE = 0
    ANTIALIASING = auto()
    BOLD = auto()
    ITALIC = auto()
    STRIKETHROUGH = auto()
    UNDERLINE = auto()


class ImageTransformType(Flag):
    """"""

    NONE = 0
    FLIP_X = auto()  # Flip sprite horizontally
    FLIP_Y = auto()  # Flip sprite vertically
    ROTATE_CCW_90 = auto()  # Rotate 90 degrees counterclockwise
    ROTATE_CCW_180 = auto()  # Rotate 180 degrees counterclockwise
    ROTATE_CCW_270 = auto()  # Rotate 270 degrees counterclockwise


class OverflowType(Enum):
    """
    Represents the type of overflow handling, with options: CLIP, EXTEND,
    and OVERFLOW.
    """

    CLIP = auto()
    EXTEND = auto()
    OVERFLOW = auto()


class RotationType(Enum):
    """"""

    NONE = 0
    LEFT = auto()
    RIGHT = auto()
    UPTURNED = auto()


"""
Base Element. The class is the foundational building block for all menu components
in the game. It defines the core properties and behaviors that are shared across
different types of UI elements, including positioning, styling, text rendering,
and interaction states. By inheriting from this abstract base class, specific
element types can focus on their unique functionality while leveraging a
consistent interface for layout and appearance customization.
"""


@dataclass(kw_only=True, repr=False)
class Element(ABC):
    """
    Represents an abstract UI element with configurable layout, appearance,
    and interaction properties, including size, alignment, color, border,
    shadow, and visibility. Designed for subclassing to define specific UI
    components.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    size: Measure = (0.0, 0.0)
    anchor: Measure = (0.0, 0.0)
    margin: Measure = (0.0, 0.0)
    offset: Measure = (0.0, 0.0)
    padding: Measure = (0.0, 0.0)

    size_measure: MeasureType = MeasureType.ABSOLUTE
    anchor_measure: MeasureType = MeasureType.ABSOLUTE
    margin_measure: MeasureType = MeasureType.ABSOLUTE
    offset_measure: MeasureType = MeasureType.ABSOLUTE
    padding_measure: MeasureType = MeasureType.ABSOLUTE

    justify: JustifyType = JustifyType.CENTER
    alignment: AlignmentType = AlignmentType.TOPLEFT
    overflow: OverflowType = OverflowType.EXTEND
    rotation: RotationType = RotationType.NONE

    background_color: RGBA = WHITE
    background_alpha: int = 0xFF

    border_thickness: int = 0  # Width of border in pixels, 0 is no border
    border_color: RGBA = TRANSPARENT
    border_alpha: int = 0xFF

    shadow_color: RGBA = TRANSPARENT
    shadow_alpha: int = 0x80
    shadow_scale: float = 1.0
    shadow_offset: Measure = (3.0, 3.0)
    shadow_offset_measure: MeasureType = MeasureType.ABSOLUTE

    is_selectable: bool = True  # Whether the element can be selected for interaction
    is_visible: bool = True  # Whether the element should be rendered
    is_fixed: bool = False

    _render_version: ClassVar[int] = 0

    # Element dataclasses are declared with repr=False; otherwise @dataclass
    # would generate a field-by-field __repr__ for every subclass, replacing
    # this one and printing whole element trees
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(id={self.id!r})"

    def __setattr__(self, name, value):
        # Only a change to an attribute the instance already has is an edit.
        # The first assignment of each field, in __init__ or replace(), is
        # construction: creating elements must not invalidate render caches
        current = self.__dict__.get(name, _UNSET)
        if current is not _UNSET and current is not value and current != value:
            Element._render_version += 1
        object.__setattr__(self, name, value)


# -----------------------------------------------------------------------------


@dataclass(kw_only=True, repr=False)
class SelectedModifier(Element):
    """Per-element overrides applied when the element is the current selection.

    Every field mirrors an ``Element`` property but defaults to ``None``,
    meaning "keep the element's own value."  Only non-``None`` fields take
    effect while the element is selected.
    """

    text_color: RGBA = COLOR_PALETTE_ACCENT


# -----------------------------------------------------------------------------


@dataclass(kw_only=True, repr=False)
class Division(Element):
    """
    Represents a container element that groups multiple Element instances
    with configurable spacing, background, and shadow colors. The Division
    is not directly selectable or expandable.
    """

    elements: list[Element] = field(default_factory=lambda: [])

    gap: Measure = (4.0, 4.0)  # Spacing between internal elements
    gap_measure: MeasureType = MeasureType.ABSOLUTE

    background_color: RGBA = TRANSPARENT
    shadow_color: RGBA = TRANSPARENT

    is_selectable: bool = False  # Containers are not directly selectable
    is_expandable: bool = False


@dataclass(kw_only=True, repr=False)
class HorizontalDivision(Division):
    """
    Represents a horizontal division, inheriting from Division. This class
    is a dataclass with keyword-only initialization and currently does not
    add additional attributes or methods.
    """

    pass


@dataclass(kw_only=True, repr=False)
class VerticalDivision(Division):
    """
    Represents a specialized Division that models a vertical partition;
    inherits all behavior from Division without adding new attributes or
    methods.
    """

    pass



@dataclass(kw_only=True, repr=False)
class Gap(Element):
    """
    Represents a layout element with configurable anchor, margin, offset,
    padding, background and shadow colors, and flags for flexibility,
    selectability, and expandability. Inherits from Element.
    """

    anchor: Measure = (0.0, 0.0)
    margin: Measure = (0.0, 0.0)
    offset: Measure = (0.0, 0.0)
    padding: Measure = (0.0, 0.0)

    background_color: RGBA = TRANSPARENT
    shadow_color: RGBA = TRANSPARENT

    is_flexible: bool = False
    is_selectable: bool = False
    is_expandable: bool = False


@dataclass(kw_only=True, repr=False)
class Fill(Element):
    """"""

    pass


"""
Static elements. Non-interactive components that provide visual structure
and information display within menus. These elements do not respond to user
input but serve important roles in organizing menu layouts and presenting
content. They include dividers for visual separation, text blocks for labels
and descriptions, and images for decorative or illustrative purposes. Static
elements help create clear visual hierarchy and improve the overall user
experience by providing context and organization to interactive components.
"""


@dataclass(kw_only=True, repr=False)
class Text(Element):
    """
    Represents a text element with customizable content, color, background,
    font, size, decorations, and selection or wrapping options. Inherits
    from Element.
    """
    """"""

    text: str = ""  # Text content to display
    text_color: RGBA = WHITE
    text_background: RGBA = TRANSPARENT  # Highlight color
    text_alpha: int = 0xFF
    text_decorations: TextDecorationType = TextDecorationType.NONE

    font_name: str = "editundo.ttf"  # Font family filename for text rendering
    font_size: int = NATIVE_FONT_SIZE  # Font size in pixels for text rendering

    background_color: RGBA = TRANSPARENT
    is_selectable: bool = False  # Static labels are not selectable
    is_wrappable: bool = False


Paragraph = str | list[str | Text]  # One paragraph of a TextBlock: plain text, or strings mixed with styled spans


@dataclass(kw_only=True, repr=False)
class NormalText(Text):
    """
    Represents a text element at the native font size in the palette's text
    colour. Inherits from Text.
    """

    font_size: int = NATIVE_FONT_SIZE
    text_color: RGBA = COLOR_PALETTE_TEXT
    # Plain weight: pygame's synthetic bold thickens the pixel font's strokes
    text_decorations: TextDecorationType = TextDecorationType.NONE


@dataclass(kw_only=True, repr=False)
class TitleText(Text):
    """
    Represents a styled text element for titles, extending Text with a
    larger default font_size, customizable text_color, and optional
    text_decorations.
    """

    font_size: int = NATIVE_FONT_SIZE * 5
    text_color: RGBA = WHITE
    text_decorations: TextDecorationType = TextDecorationType.NONE


@dataclass(kw_only=True, repr=False)
class SubtitleText(Text):
    """
    Represents styled subtitle text with customizable font_size, text_color,
    text_background, and text_decorations. Inherits from Text. Defaults to the
    native font size, with black text on a white background and no decoration.
    """

    font_size: int = NATIVE_FONT_SIZE
    text_color: RGBA = BLACK
    text_background: RGBA = WHITE
    text_decorations: TextDecorationType = TextDecorationType.NONE


@dataclass(kw_only=True, repr=False)
class HeadingOneText(Text):
    """
    Represents a level-one heading text style with customizable font, size,
    color, shadow, and text decoration options. Inherits from Text.
    """

    font_name: str = "editundo.ttf"
    font_size: int = NATIVE_FONT_SIZE * 4

    text_color: RGBA = "#F0B443FF"
    shadow_color: RGBA = "#E6A23EFF"
    shadow_offset: Measure = (4.0, 4.0)  # One font pixel at this size
    text_decorations: TextDecorationType = TextDecorationType.NONE


@dataclass(kw_only=True, repr=False)
class HeadingTwoText(Text):
    """
    Represents a level-two heading text style with customizable font, size,
    color, shadow, and text decoration options. Inherits from Text.
    """

    font_name: str = "editundo.ttf"
    font_size: int = NATIVE_FONT_SIZE * 2

    text_color: RGBA = "#F0B443FF"
    shadow_color: RGBA = "#E6A23EFF"
    shadow_offset: Measure = (2.0, 2.0)
    text_decorations: TextDecorationType = TextDecorationType.NONE


@dataclass(kw_only=True, repr=False)
class HeadingThreeText(Text):
    """
    Represents a level-three heading text style with customizable font,
    size, color, shadow, and text decoration options. Inherits from Text.
    """

    font_name: str = "editundo.ttf"
    font_size: int = NATIVE_FONT_SIZE

    text_color: RGBA = "#F0B443FF"
    shadow_color: RGBA = "#E6A23EFF"
    shadow_offset: Measure = (1.0, 1.0)
    text_decorations: TextDecorationType = TextDecorationType.NONE


@dataclass(kw_only=True, repr=False)
class Image(Element):
    """"""

    image_path: str  # Path to the sprite image file

    scale: tuple[float, float] = (1.0, 1.0)  # Scale factors for image resizing
    transform: ImageTransformType = ImageTransformType.NONE  # Built-in transformation flags for flipping/rotating
    tint: RGBA = TRANSPARENT  # Color tint (RGBA) applied to image
    alpha: float = 1.0  # Transparency level (0.0 = transparent, 1.0 = opaque)

    alignment: AlignmentType = AlignmentType.BOTTOMRIGHT

    is_fixed: bool = True
    background_color: RGBA = TRANSPARENT

    is_selectable: bool = False  # Images are not selectable


@dataclass(kw_only=True, repr=False)
class TextBlock(Element):
    """
    Paragraphs wrapped to the element's width, or to all the room it is given
    when ``size`` has no width. A paragraph is a string in ``body_text``'s
    style, or a list of strings and ``Text`` spans, where each span keeps its
    own colour so single words can be picked out. Lines are spaced by the
    gap between one line's capitals and the next, not by the font's line
    height.
    """

    @dataclass(kw_only=True, repr=False)
    class BodyText(NormalText):
        """The style of plain strings in ``paragraphs``."""

    @dataclass(kw_only=True, repr=False)
    class EmphasisText(NormalText):
        """A span picked out in the heading colour."""

        text_color: RGBA = COLOR_PALETTE_HEADING

    @dataclass(kw_only=True, repr=False)
    class AsideText(NormalText):
        """A span set back in the muted colour."""

        text_color: RGBA = COLOR_PALETTE_MUTED

    paragraphs: list[Paragraph] = field(default_factory=list)
    body_text: Text = field(default_factory=BodyText)
    line_gap_ph: int = 6  # From the baseline of one line to the capitals of the next
    paragraph_gap_ph: int = 14

    background_color: RGBA = TRANSPARENT
    is_selectable: bool = False


@dataclass(kw_only=True, repr=False)
class BulletList(TextBlock):
    """
    A ``TextBlock`` whose paragraphs are list items, each marked with a
    square bullet centred on its first line. Wrapped lines indent under the
    item's text, not under the bullet.
    """

    paragraph_gap_ph: int = 8
    bullet_color: RGBA = COLOR_PALETTE_HEADING
    bullet_pw: int = 4
    bullet_gap_pw: int = 6  # Between the bullet and the item's text


@dataclass(kw_only=True, repr=False)
class CreditList(Element):
    """
    Rows of a role on the left and a name on the right, across the element's
    width, joined by a dotted leader that sits on the baseline.
    """

    @dataclass(kw_only=True, repr=False)
    class RoleText(NormalText):
        """The style of each role."""

        text_color: RGBA = COLOR_PALETTE_MUTED

    @dataclass(kw_only=True, repr=False)
    class NameText(NormalText):
        """The style of each name."""

    credits: list[tuple[str, str]] = field(default_factory=list)  # (role, name) pairs
    role_text: Text = field(default_factory=RoleText)
    name_text: Text = field(default_factory=NameText)

    leader_color: RGBA = COLOR_PALETTE_NEUTRAL
    dot_pw: int = 2  # Each dot is square
    dot_gap_pw: int = 2
    leader_gap_pw: int = 6  # Kept clear between the leader and the text on either side
    row_gap_ph: int = 6

    background_color: RGBA = TRANSPARENT
    is_selectable: bool = False


@dataclass(kw_only=True, repr=False)
class SectionHeader(Element):
    """
    A label in the heading colour followed by a rule to the element's width,
    centred on the label's capitals, for splitting a menu into sections.
    """

    @dataclass(kw_only=True, repr=False)
    class HeaderText(NormalText):
        """The style of the section's name."""

        text_color: RGBA = COLOR_PALETTE_HEADING

    label: Text = field(default_factory=HeaderText)
    rule_color: RGBA = COLOR_PALETTE_BORDER
    rule_ph: int = 2
    rule_gap_pw: int = 6  # Between the label and the rule

    background_color: RGBA = TRANSPARENT
    is_selectable: bool = False


@dataclass(kw_only=True, repr=False)
class ProgressBar(Element):
    """
    A read-only row of segments filled in proportion to ``value`` within
    ``range``, with the number in its own box to the right. ``size`` covers
    both boxes, and each is drawn with the element's padding, background,
    border and shadow. It is drawn like a label so it reads as something to
    look at, not something to adjust.
    """

    @dataclass(kw_only=True, repr=False)
    class NumberText(NormalText):
        """The number in the box beside the bar."""

    value: float = 0.0  # Current value; values outside the range are clamped when drawn
    range: tuple[float, float] = (0.0, 1.0)  # Values drawn as an empty and a full bar

    segments: int = 10  # The segments share whatever width the bar box has
    segment_gap_pw: int = 2
    segment_ph: int = 8  # The height of a capital at the native font size
    fill_color: RGBA = COLOR_PALETTE_TEXT
    empty_color: RGBA = COLOR_PALETTE_SECONDARY

    number_text: Text = field(default_factory=NumberText)
    value_format: str = "{fraction:.0%}"  # str.format pattern given ``value`` and ``fraction``
    number_pw: int = 40  # Fits "100%"
    box_gap_pw: int = 6  # Between the bar box and the number box
    use_number: bool = True

    size: Measure = _CONTROL_SIZE
    padding: Measure = _CONTROL_PADDING
    alignment: AlignmentType = AlignmentType.CENTER
    background_color: RGBA = COLOR_PALETTE_NEUTRAL
    border_color: RGBA = COLOR_PALETTE_BORDER
    border_thickness: int = 1
    shadow_color: RGBA = COLOR_PALETTE_NEUTRAL
    shadow_alpha: int = _CONTROL_SHADOW_ALPHA

    is_selectable: bool = False

    def get_fraction(self, value: float | None = None) -> float:
        """How full the bar is for ``value``, or for the current value, from 0.0 to 1.0."""
        value = self.value if value is None else value
        low, high = self.range
        if high == low:
            return 0.0
        return min(1.0, max(0.0, (value - low) / (high - low)))

    def get_number(self, value: float | None = None) -> str:
        """The text shown in the number box for ``value``, or for the current value."""
        value = self.value if value is None else value
        return self.value_format.format(value=value, fraction=self.get_fraction(value))


"""
Interactive elements. User-controllable components that enable player
input and decision-making within menus. These elements respond to keyboard
and other input methods, allowing players to navigate, make selections, and
modify settings. They include buttons for triggering actions, toggles for
binary choices, sliders for numeric adjustments, and input fields for text
entry. Each interactive element provides visual feedback and maintains state
to ensure clear communication of available options and current selections.
"""


@dataclass(kw_only=True, repr=False)
class InteractiveElement(Element):
    """
    All interactive elements have a value and an action function that takes in
    that value and returns a boolean. They are all callable with that action.
    """

    value: Any = ""
    action: Callable[..., Any] = field(default=lambda v: True)

    is_called: bool = False

    def __call__(self) -> bool:
        self.is_called = True
        return self.action(self.value)


@dataclass(kw_only=True, repr=False)
class Button(InteractiveElement):
    """
    A fixed-size box with a centred label that runs ``action`` when pressed.
    The border and label turn the accent colour while it is selected.
    """

    @dataclass(kw_only=True, repr=False)
    class ButtonText(NormalText):
        """The label of a button."""

    label: Text = field(default_factory=ButtonText)  # Text element used for rendering the button label
    action: Callable[[], Any] = field(default=lambda: None)  # Called with no arguments when the button is pressed

    size: Measure = _CONTROL_SIZE
    padding: Measure = _CONTROL_PADDING
    alignment: AlignmentType = AlignmentType.CENTER
    background_color: RGBA = COLOR_PALETTE_SECONDARY
    border_color: RGBA = COLOR_PALETTE_TEXT
    border_thickness: int = 1
    shadow_color: RGBA = COLOR_PALETTE_NEUTRAL
    shadow_alpha: int = _CONTROL_SHADOW_ALPHA

    selected_border_color: RGBA = COLOR_PALETTE_ACCENT
    selected_text_color: RGBA = COLOR_PALETTE_ACCENT

    def __call__(self) -> Any:
        """Run the button's action. Buttons have no value, so no argument is passed."""
        self.is_called = True
        return self.action()


@dataclass(kw_only=True, repr=False)
class Toggle(InteractiveElement):
    """
    An on/off switch drawn as two halves, ``false_text`` and ``true_text``,
    with the current one filled. The fill turns the edited colour once the
    toggle has been used.
    """

    @dataclass(kw_only=True, repr=False)
    class ToggleText(NormalText):
        """The style of both halves' text; the filled half recolours it."""

        text_color: RGBA = COLOR_PALETTE_NEUTRAL

    value: bool = False  # Current boolean state
    action: Callable[[Any], bool] = field(default=lambda v: True)

    label: Toggle.ToggleText = field(default_factory=ToggleText)
    false_text: str = "FALSE"
    true_text: str = "TRUE"

    size: Measure = _CONTROL_SIZE
    padding: Measure = (3.0, 3.0)  # Gap around the filled half, the same on every side
    alignment: AlignmentType = AlignmentType.CENTER
    background_color: RGBA = COLOR_PALETTE_SECONDARY
    border_color: RGBA = COLOR_PALETTE_TEXT
    border_thickness: int = 1
    shadow_color: RGBA = COLOR_PALETTE_NEUTRAL
    shadow_alpha: int = _CONTROL_SHADOW_ALPHA

    fill_color: RGBA = COLOR_PALETTE_TEXT
    edited_fill_color: RGBA = COLOR_PALETTE_EDITED
    filled_text_color: RGBA = COLOR_PALETTE_SECONDARY
    selected_border_color: RGBA = COLOR_PALETTE_ACCENT

    def __call__(self) -> bool:
        """Inverse value and call action with value."""

        self.value = not self.value
        self.is_called = True
        return self.action(self.value)


@dataclass(kw_only=True, repr=False)
class Slider(InteractiveElement, ProgressBar):
    """
    A ``ProgressBar`` adjusted in steps, with arrows either side of the
    segments. Opening it copies ``value`` to a buffer that the steps change,
    and closing it commits the buffer and calls ``action`` once, like
    ``Selector``. Only the bar box shows the selection; the number box keeps
    its border.
    """

    value: float = 0.0  # Current committed value within the range
    range: tuple[float, float] = (0, 1)  # Minimum and maximum allowed values
    step: float = 0.1  # Increment/decrement amount per adjustment

    left_arrow: Text = field(default_factory=lambda: Selector.LeftShiftArrow())
    right_arrow: Text = field(default_factory=lambda: Selector.RightShiftArrow())
    gap: Measure = (5.0, 0.0)  # Between each arrow and the segments

    action: Callable[[Any], bool] = field(default=lambda v: True)

    empty_color: RGBA = COLOR_PALETTE_NEUTRAL

    # InteractiveElement restores Element's defaults over ProgressBar's, so the box is declared again
    size: Measure = _CONTROL_SIZE
    padding: Measure = _CONTROL_PADDING
    alignment: AlignmentType = AlignmentType.CENTER
    background_color: RGBA = COLOR_PALETTE_SECONDARY
    border_color: RGBA = COLOR_PALETTE_TEXT
    border_thickness: int = 1
    shadow_color: RGBA = COLOR_PALETTE_NEUTRAL
    shadow_alpha: int = _CONTROL_SHADOW_ALPHA

    selected_border_color: RGBA = COLOR_PALETTE_ACCENT
    selected_arrow_color: RGBA = COLOR_PALETTE_ACCENT
    disabled_arrow_color: RGBA = COLOR_PALETTE_NEUTRAL
    altered_color: RGBA = COLOR_PALETTE_EDITED  # Segments and number while the value differs from the original

    is_selectable: bool = True
    is_edited: bool = field(default=False, init=False, repr=False)
    is_open: bool = field(default=False, init=False, repr=False)
    _open_value: float = field(default=0.0, init=False, repr=False)

    def get_buffer_value(self) -> float:
        """The buffer while open, or the committed value otherwise."""
        return self._open_value if self.is_open else self.value

    def is_altered(self) -> bool:
        """"""
        if self.is_open and not self.is_edited:
            return self._open_value != self.value
        else:
            return self.is_edited

    def open(self) -> None:
        """Enter edit mode, copying the current value to the buffer."""
        self.is_open = True
        self._open_value = self.value

    def increment(self) -> None:
        """Raise the buffer by one step, clamped to the maximum, if open."""
        if self.is_open:
            self._open_value = min(self.range[1], round(self._open_value + self.step, 10))

    def decrement(self) -> None:
        """Lower the buffer by one step, clamped to the minimum, if open."""
        if self.is_open:
            self._open_value = max(self.range[0], round(self._open_value - self.step, 10))

    def cancel(self) -> None:
        """Discard the buffer and exit edit mode without saving."""
        self.is_open = False
        self._open_value = self.value

    def close(self) -> None:
        """Commit the buffer as the new value and exit edit mode."""
        if self.is_open:
            if self._open_value != self.value:
                self.is_edited = True
                self.value = self._open_value
                self.is_called = True
                self.action(self.value)  # Call action once, with the new value
            self.is_open = False


@dataclass(kw_only=True, repr=False)
class Selector(InteractiveElement):
    """
    One of ``selections``, stepped through with arrows pinned to the edges of
    a fixed-size box, with the option centred between them.
    """

    @dataclass(kw_only=True, repr=False)
    class LeftShiftArrow(NormalText):
        """"""

        text: str = "<"

    @dataclass(kw_only=True, repr=False)
    class RightShiftArrow(NormalText):
        """"""

        text: str = ">"

    @dataclass(kw_only=True, repr=False)
    class SelectionText(NormalText):
        """"""

        text: str = "[SELECTION]"

    value: int = 0
    selections: tuple[str, ...] = ("",)

    selection_text: SelectionText = field(default_factory=SelectionText)
    left_arrow: LeftShiftArrow = field(default_factory=LeftShiftArrow)
    right_arrow: RightShiftArrow = field(default_factory=RightShiftArrow)
    gap: Measure = (5.0, 0.0)  # Between each arrow and the option's slot

    action: Callable[[Any], bool] = field(default=lambda v: True)

    size: Measure = _CONTROL_SIZE
    padding: Measure = _CONTROL_PADDING
    alignment: AlignmentType = AlignmentType.CENTER
    background_color: RGBA = COLOR_PALETTE_SECONDARY
    border_color: RGBA = COLOR_PALETTE_TEXT
    border_thickness: int = 1
    shadow_color: RGBA = COLOR_PALETTE_NEUTRAL
    shadow_alpha: int = _CONTROL_SHADOW_ALPHA

    selected_border_color: RGBA = COLOR_PALETTE_ACCENT
    selected_arrow_color: RGBA = COLOR_PALETTE_ACCENT
    altered_selection_color: RGBA = COLOR_PALETTE_EDITED
    disabled_arrow_color: RGBA = COLOR_PALETTE_NEUTRAL

    is_open: bool = field(default=False, init=False, repr=False)
    is_edited: bool = field(default=False, init=False, repr=False)
    _open_index: int = field(default=0, init=False, repr=False)

    def is_altered(self) -> bool:
        """"""
        if self.is_open and not self.is_edited:
            return self._open_index != self.value
        else:
            return self.is_edited

    def buffer_index(self) -> int:
        if self.is_open:
            return self._open_index
        else:
            return self.value

    def selection(self) -> str:
        """"""
        if self.is_open:
            return self.selections[self._open_index]
        return self.selections[self.value]

    def open(self) -> None:
        """Enter edit mode, copying the current value to the edit buffer."""
        self.is_open = True
        self._open_index = self.value

    def next(self) -> None:
        if self.is_open:
            self._open_index = min((self._open_index + 1), len(self.selections) - 1)

    def previous(self) -> None:
        if self.is_open:
            self._open_index = max((self._open_index - 1), 0)

    def cancel(self) -> None:
        """Discard the open buffer and exit open mode without saving."""
        self._open_index = 0
        self.is_open = False

    def close(self) -> None:
        """Commit the open buffer as the new value and exit open mode."""
        if self.is_open:
            if self.is_altered():
                self.is_edited = True
                self.value = self._open_index
                self.is_called = True
                self.action(self.value)  # Call action once, with the new index
            self.is_open = False


@dataclass(kw_only=True, repr=False)
class InputField(InteractiveElement):
    """
    Text typed after a terminal-style prompt, edited in a buffer that is
    committed on close when ``validator`` accepts it. Only the border shows
    the selection; the prompt stays the neutral colour.
    """

    @dataclass(kw_only=True, repr=False)
    class InputPromptText(NormalText):
        """The prompt drawn before the value."""

        text: str = ">"
        text_color: RGBA = COLOR_PALETTE_NEUTRAL

    @dataclass(kw_only=True, repr=False)
    class InputHintText(NormalText):
        """Shown after the prompt while the field is empty."""

        text: str = "[RETURN]"
        text_color: RGBA = COLOR_PALETTE_NEUTRAL

    @dataclass(kw_only=True, repr=False)
    class InputValueText(NormalText):
        """The committed value, or the buffer while editing."""

    prompt: Text = field(default_factory=InputPromptText)
    hint: Text = field(default_factory=InputHintText)
    value: Text = field(default_factory=InputValueText)  # Current committed text value
    action: Callable[[Any], bool] = field(default=lambda v: True)  # Function called with new value when committed
    validator: Callable[[str], bool] = field(default=lambda s: bool(re.fullmatch(ALPHANUMERIC_REGEX, s)))
    gap: Measure = (6.0, 0.0)  # Between the prompt and the value

    size: Measure = _CONTROL_SIZE
    padding: Measure = _CONTROL_PADDING
    alignment: AlignmentType = AlignmentType.MIDLEFT
    background_color: RGBA = COLOR_PALETTE_SECONDARY
    border_color: RGBA = COLOR_PALETTE_TEXT
    border_thickness: int = 1
    shadow_color: RGBA = COLOR_PALETTE_NEUTRAL
    shadow_alpha: int = _CONTROL_SHADOW_ALPHA

    selected_border_color: RGBA = COLOR_PALETTE_ACCENT
    invalid_text_color: RGBA = COLOR_PALETTE_ACCENT
    edited_text_color: RGBA = COLOR_PALETTE_EDITED

    is_edited: bool = field(default=False, init=False, repr=False)
    is_open: bool = field(default=False, init=False, repr=False)
    _open_buffer: str = field(default="", init=False, repr=False)  # Internal buffer for text being edited

    _cursor_glyphs: ClassVar[tuple[str, ...]] = ("_", "")  # Cursor glyphs cycled while editing
    _cursor_period: ClassVar[float] = 0.5  # Seconds each cursor glyph is shown
    _cursor_epoch: float = field(default=0.0, init=False, repr=False)  # Time the blink cycle last restarted

    def authenticate(self) -> bool:
        """"""
        return self.validator(self.get_field())

    def get_field(self) -> str:
        """Buffer while editing, or the committed value otherwise."""
        return self._open_buffer if self.is_open else self.value.text

    def get_cursor_glyph(self) -> str:
        """Return the blinking cursor glyph for the current time, or "" when closed."""
        if not self.is_open:
            return ""
        elapsed = time.monotonic() - self._cursor_epoch
        return self._cursor_glyphs[int(elapsed / self._cursor_period) % len(self._cursor_glyphs)]

    def _restart_cursor(self) -> None:
        self._cursor_epoch = time.monotonic()

    def is_altered(self) -> bool:
        """"""
        if self.is_open and not self.is_edited:
            return self._open_buffer != self.value.text
        else:
            return self.is_edited

    """
    Change value. Provide functionality for modifying the input field's text 
    content when the input is open. Until the input is closed, the new version
    of the text is stored in a buffer.
    """

    def open(self) -> None:
        """Enter edit mode, copying the current value to the edit buffer."""
        self.is_open = True
        self._open_buffer = self.value.text
        self._restart_cursor()

    def append(self, character: str) -> None:
        """Add a character to the edit buffer if currently editing."""
        if self.is_open:
            self._open_buffer += character.upper()
        self._restart_cursor()

    def truncate(self) -> None:
        """Remove the last character from the edit buffer if currently editing."""
        if self.is_open and self._open_buffer:
            self._open_buffer = self._open_buffer[:-1]
        self._restart_cursor()

    def cancel(self) -> None:
        """Discard the edit buffer and exit edit mode without saving."""
        self.is_open = False
        self._open_buffer = ""

    def close(self) -> None:
        """Commit the edit buffer as the new value and exit edit mode."""
        if self.is_open and self.authenticate():
            if self.is_altered():
                self.is_edited = True
                self.value.text = self._open_buffer
                self.is_called = True
                self.action(self.value.text)  # Call action once, with the new text
            self.is_open = False
