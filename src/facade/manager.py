"""
manager.py

MenuManager - stack-based navigation over Menu dataclasses - and the
manage_menu_* functions that apply one pygame event to the top menu.

Most projects use these through ``facade.Interface``, which owns a
MenuManager and a MenuRenderer and dispatches events to these handlers.
"""

import pygame

from collections.abc import Iterator
from typing import cast

from .elements import Button, InputField, Selector, Slider, Toggle
from .menus import Menu

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .renderer import DebugRenderer, MenuRenderer


class MenuManager:
    """Manages a push/pop stack of Menu objects and routes input to them."""

    def __init__(self) -> None:
        self._menus: dict[type[Menu], Menu] = {}
        self._stack: list[Menu] = []

    # -------------------------------------------------------------------------

    def add_menu(self, menu: Menu) -> None:
        """"""
        self._menus[type(menu)] = menu

    def drop_menu(self, menu_type: type[Menu]) -> None:
        """"""
        self._menus.pop(menu_type)

    def clear_menus(self) -> None:
        """"""
        self._menus.clear()

    # -------------------------------------------------------------------------

    def get_menu[T: Menu](self, menu_type: type[T]) -> T | None:
        """"""
        return cast("T | None", self._menus.get(menu_type))

    def has_menu(self, menu_type: type[Menu]) -> bool:
        """"""
        return menu_type in self._menus

    def all_menus(self) -> Iterator[Menu]:
        """"""
        return iter(self._menus.values())

    # -------------------------------------------------------------------------

    def push_stack(self, menu_type: type[Menu]) -> None:
        """Push a menu onto the stack by its type."""
        menu = self._menus.get(menu_type)
        if menu is not None:
            self._stack.append(menu)

    def pop_stack(self, keep_root: bool = True) -> Menu | None:
        """Pop the top menu from the stack.

        With ``keep_root`` (the default) the bottom menu is never popped, so
        Escape cannot close e.g. the title screen. Pass ``keep_root=False``
        to allow emptying the stack.
        """
        if len(self._stack) > (1 if keep_root else 0):
            return self._stack.pop()
        return None

    def clear_stack(self) -> None:
        """Remove all menus from the stack."""
        self._stack.clear()

    # -------------------------------------------------------------------------

    def top_stack(self) -> Menu | None:
        """Returns the first (top) item in the stack"""
        if len(self._stack) >= 1:
            return self._stack[-1]
        return None

    def in_stack(self, menu_type: type[Menu]) -> bool:
        """Returns whether a menu of type `menu_type` is in the stack"""
        return any(type(menu) is menu_type for menu in self._stack)

    def depth_stack(self) -> int:
        """Returns the size of the stack"""
        return len(self._stack)

    @property
    def stack(self) -> Iterator[Menu]:
        return iter(self._stack)


# -----------------------------------------------------------------------------


_POINTER_DEADZONE_PW = 8  # After a key press the pointer must travel this far before it takes focus back
_ARROW_DIRECTIONS = {pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right"}
_ACTIVATE_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)


def _set_system_cursor(cursor: int) -> None:
    # A platform without system cursors is not an error
    try:
        pygame.mouse.set_cursor(cursor)
    except pygame.error:
        pass


def _get_typing_field(menu: Menu) -> InputField | None:
    element = menu.get_selected_element()
    return element if isinstance(element, InputField) and element.is_open else None


def _finish_typing(field: InputField) -> None:
    # Leaving a field saves what was typed if it is valid and throws it away if not, so nothing is left open
    if not field.close():
        field.cancel()


def _move_focus(menu: Menu, renderer: MenuRenderer | DebugRenderer, direction: str, is_wrapping: bool) -> bool:
    element = menu.get_selected_element()
    if element is None:
        return False
    neighbour = renderer.find_neighbour(menu, element, direction, is_wrapping)
    if neighbour is None:
        # Before the first render there is no layout, so fall back to reading order
        if renderer.get_element_rect(menu, element) is not None:
            return False
        menu.move_selected_by(1 if direction in ("down", "right") else -1, is_wrapping)
    else:
        menu.select_element_by_id(neighbour.id)
    selected = menu.get_selected_element()
    if selected is not None:
        renderer.reveal_element(menu, selected)
    return True


def _adjust(element: object, step: int) -> bool:
    # Left and Right change a value at once; controls without one let the arrows move focus instead
    if isinstance(element, Toggle):
        element.set_value(step > 0)
        return True
    if isinstance(element, Selector):
        element.next() if step > 0 else element.previous()
        return True
    if isinstance(element, Slider):
        element.increment() if step > 0 else element.decrement()
        return True
    return False


def _activate(element: object) -> None:
    if isinstance(element, (Button, Toggle)):
        element()
    elif isinstance(element, Selector):
        element.next(is_wrapping=True)
    elif isinstance(element, InputField):
        element.open()


def _activate_part(menu: Menu, renderer: MenuRenderer | DebugRenderer, element: object, part: str, pos: tuple[int, int]) -> None:
    if isinstance(element, Button):
        element()
    elif isinstance(element, Toggle):
        element()
    elif isinstance(element, (Selector, Slider)) and part in ("left", "right"):
        _adjust(element, 1 if part == "right" else -1)
    elif isinstance(element, InputField):
        element.open()


# -----------------------------------------------------------------------------


def handle_menu_mousemotion(menu: Menu, renderer: MenuRenderer | DebugRenderer, event: pygame.event.Event, use_hand_cursor: bool = True) -> bool:
    """
    Light the selectable element under the pointer, or nothing over empty
    space. The keys' place is kept for when they are used again. Ignored until
    the pointer has moved a few pixels since the last key press, so a bumped
    mouse cannot take over from the keys.
    """
    if event.type != pygame.MOUSEMOTION:
        raise ValueError("Improper event handling")

    anchor = menu._key_anchor_pos
    if anchor is not None:
        if abs(event.pos[0] - anchor[0]) < _POINTER_DEADZONE_PW and abs(event.pos[1] - anchor[1]) < _POINTER_DEADZONE_PW:
            return False
        menu._key_anchor_pos = None

    element = renderer.find_selectable_at(menu, event.pos)
    typing_field = _get_typing_field(menu)
    if use_hand_cursor:
        is_text = isinstance(element, InputField)
        _set_system_cursor(pygame.SYSTEM_CURSOR_IBEAM if is_text else pygame.SYSTEM_CURSOR_HAND if element is not None else pygame.SYSTEM_CURSOR_ARROW)

    menu.set_pointer_leading(True)
    if typing_field is not None and element is not typing_field:
        # While typing, only the field is lit wherever the pointer wanders
        menu.set_hovered(None)
        return element is not None
    menu.set_hovered(element, renderer.get_part_at(menu, element, event.pos) if element is not None else "")
    return element is not None


def handle_menu_mousebuttondown(menu: Menu, renderer: MenuRenderer | DebugRenderer, event: pygame.event.Event) -> bool:
    """Focus the clicked element and hold down the part under the pointer; it acts on release."""
    if event.type != pygame.MOUSEBUTTONDOWN:
        raise ValueError("Improper event handling")
    if getattr(event, "button", 1) != 1:
        return False

    menu._key_anchor_pos = None
    element = renderer.find_selectable_at(menu, event.pos)
    typing_field = _get_typing_field(menu)
    if typing_field is not None and element is not typing_field:
        _finish_typing(typing_field)
    if element is None:
        return False

    # Clicking a control is choosing it, so the keys carry on from there
    menu.select_element_by_id(element.id)
    menu.set_pointer_leading(True)
    part = renderer.get_part_at(menu, element, event.pos)
    menu.set_hovered(element, part)
    if element is typing_field:
        return True
    menu.set_pressed_part(element, part)
    return True


def handle_menu_mousebuttonup(menu: Menu, renderer: MenuRenderer | DebugRenderer, event: pygame.event.Event) -> bool:
    """Act on the held part if the pointer is still over it; releasing anywhere else cancels the press."""
    if event.type != pygame.MOUSEBUTTONUP:
        raise ValueError("Improper event handling")
    if getattr(event, "button", 1) != 1:
        return False

    pressed = menu._pressed
    menu.set_pressed_part(None)
    if pressed is None:
        return False
    element = renderer.find_selectable_at(menu, event.pos)
    if element is None or element.id != pressed[0]:
        return True
    part = renderer.get_part_at(menu, element, event.pos)
    if part == pressed[1]:
        _activate_part(menu, renderer, element, part, event.pos)
    return True


def handle_menu_mousewheel(menu: Menu, renderer: MenuRenderer | DebugRenderer, event: pygame.event.Event) -> bool:
    """Scroll the menu. The wheel never changes a value."""
    if event.type != pygame.MOUSEWHEEL:
        raise ValueError("Improper event handling")

    # TODO: Correct Implementation in MenuRenderer
    menu._scroll += -event.y * 2.0
    return True


def handle_menu_keydown(menu: Menu, renderer: MenuRenderer | DebugRenderer, event: pygame.event.Event, manager: MenuManager | None = None) -> bool:
    """
    Up and Down move focus to the nearest element above or below, stopping at
    the ends. Left and Right adjust the focused element, or move focus sideways
    when it has nothing to adjust. Return activates it, Tab steps through
    elements in reading order and Escape goes back a menu. While a field is
    being typed into, the keys edit it instead.
    """
    if event.type != pygame.KEYDOWN:
        raise ValueError("Improper event handling")

    key = event.key
    typing_field = _get_typing_field(menu)
    if typing_field is not None:
        if _handle_typing_key(typing_field, event):
            return True
        _finish_typing(typing_field)

    # The keys take over from where they left off, and the pointer must move a little before it can take over again
    element = menu.get_selected_element()
    # The keys' place is hidden while the pointer leads, unless a field is being typed into, and is lost
    # from sight when the menu has been scrolled away from it
    is_out_of_view = element is not None and not renderer.is_element_in_view(menu, element)
    was_hidden = (menu._is_pointer_leading and typing_field is None) or is_out_of_view
    menu.set_pointer_leading(False)
    menu._key_anchor_pos = pygame.mouse.get_pos()

    if key == pygame.K_ESCAPE:
        return manager is not None and manager.pop_stack() is not None
    if was_hidden and key in (*_ARROW_DIRECTIONS, pygame.K_TAB, *_ACTIVATE_KEYS):
        # The first press only finds where the keys are, scrolling up or down to it, so nothing moves or acts unseen
        if element is not None:
            renderer.reveal_element(menu, element)
        return True
    if key in (pygame.K_UP, pygame.K_DOWN):
        _move_focus(menu, renderer, _ARROW_DIRECTIONS[key], is_wrapping=False)
        return True
    if key == pygame.K_TAB:
        menu.move_selected_by(-1 if event.mod & pygame.KMOD_SHIFT else 1, is_wrapping=False)
        selected = menu.get_selected_element()
        if selected is not None:
            renderer.reveal_element(menu, selected)
        return True
    if key in (pygame.K_LEFT, pygame.K_RIGHT):
        step = 1 if key == pygame.K_RIGHT else -1
        if not _adjust(element, step):
            _move_focus(menu, renderer, _ARROW_DIRECTIONS[key], is_wrapping=False)
        return True
    if key in _ACTIVATE_KEYS:
        _activate(element)
        return True
    return False


def _handle_typing_key(field: InputField, event: pygame.event.Event) -> bool:
    # Keys that edit the field; anything else saves or cancels it and is then handled as navigation
    key = event.key
    if key in _ACTIVATE_KEYS:
        field.close()  # An invalid buffer stays open so it can be fixed
    elif key == pygame.K_ESCAPE:
        field.cancel()
    elif key == pygame.K_BACKSPACE:
        field.truncate()
    elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
        return False
    return True  # Character keys arrive as text input; their key presses are still the menu's


def handle_menu_textinput(menu: Menu, renderer: MenuRenderer | DebugRenderer, event: pygame.event.Event) -> bool:
    """Type into the focused field, if one is open."""
    if event.type != pygame.TEXTINPUT:
        raise ValueError("Improper event handling")

    field = _get_typing_field(menu)
    if field is None:
        return False
    field.append(event.text)
    return True
