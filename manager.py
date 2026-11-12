"""
manager.py

MenuManager - stack-based navigation over Menu dataclasses.

Usage
-----
from app.menus.manager import manager as menu_manager

menu_manager.register(my_menu)
menu_manager.push(my_menu)

# In the event loop:
for event in pygame.event.get():
    menu_manager.handle_event(event)
"""

import pygame

from collections.abc import Iterator
from typing import cast

from .elements import Button, InputField, Selector, Slider, Toggle
from .types import MenuType, Pause

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from renderer.passes.menu_pass import MenuPass


class MenuManager:
    """Manages a push/pop stack of Menu objects and routes input to them."""

    def __init__(self) -> None:
        self._menus: dict[type[MenuType], MenuType] = {}
        self._stack: list[MenuType] = []

    def __len__(self) -> int:
        """Returns the number of menus"""
        return len(self._menus.keys())

    """
    Menu mutations.
    """

    def add_menu(self, menu: MenuType) -> None:
        """"""
        self._menus[type(menu)] = menu

    def drop_menu(self, menu_type: type[MenuType]) -> None:
        """"""
        self._menus.pop(menu_type)

    def set_menu(self, menu: MenuType) -> None:
        """"""
        self._menus[type(menu)] = menu

    def clear_menus(self) -> None:
        """"""
        self._menus.clear()

    """
    Menu queries.
    """

    def get_menu[T: MenuType](self, menu_type: type[T]) -> T | None:
        """"""
        return cast("T | None", self._menus.get(menu_type))

    def has_menu(self, menu_type: type[MenuType]) -> bool:
        """"""
        return menu_type in self._menus

    def all_menus(self) -> Iterator[MenuType]:
        """"""
        return iter(self._menus.values())

    """
    Stack mutations.
    """

    def push_stack(self, menu_type: type[MenuType]) -> None:
        """Push a menu onto the stack by its type."""
        menu = self._menus.get(menu_type)
        if menu is not None:
            self._stack.append(menu)

    def pop_stack(self) -> MenuType | None:
        """Pop the top menu from the stack."""
        if len(self._stack) > 1:
            return self._stack.pop()
        return None

    def clear_stack(self) -> None:
        """Remove all menus from the stack."""
        self._stack.clear()

    """
    Stack queries.
    """

    def top(self) -> MenuType | None:
        """Returns the first (top) item in the stack"""
        if len(self._stack) >= 1:
            return self._stack[-1]
        return None

    def in_stack(self, menu_type: type[MenuType]) -> bool:
        """Returns whether a given `menu_type` is in the stack"""
        return menu_type in self._stack

    def depth_stack(self) -> int:
        """Returns the size of the stack"""
        return len(self._stack)

    @property
    def stack(self) -> Iterator[MenuType]:
        return iter(self._stack)


"""
Manage input events.
"""


def manage_menu_mousemotion(menu: MenuType, renderer: MenuPass, event: pygame.event.Event) -> bool:
    """"""
    if event.type != pygame.MOUSEMOTION:
        raise ValueError("Improper event handling")

    # Parse MOUSEMOTION event attributes
    position = event.pos
    relative = event.rel
    is_left, is_middle, is_right = event.buttons

    element = menu.get_selected_element()

    hovered = renderer.find_elements_at(menu, event.pos)
    if hovered != [] and hovered[0].is_selectable:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        menu.select_element_by_id(hovered[0].id)
        return True
    
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    return False


def manage_menu_mousebuttondown(menu: MenuType, renderer: MenuPass, event: pygame.event.Event) -> bool:
    """"""
    if event.type != pygame.MOUSEBUTTONDOWN:
        raise ValueError("Improper event handling")

    previously_selected = menu.get_selected_element()
    previously_selected_id = previously_selected.id if previously_selected is not None else None

    clicks = int(getattr(event, "clicks", 1) or 1)
    if hasattr(event, "dict"):
        clicks = int(event.dict.get("clicks", clicks) or clicks)
    clicks = max(1, clicks)

    element = renderer.select_element_at(menu, event.pos)
    if element is None:
        if isinstance(previously_selected, InputField) and previously_selected.is_open:
            previously_selected.cancel()
        return False

    if clicks >= 2 or previously_selected_id == element.id:
        if isinstance(element, Button):
            element()
        elif isinstance(element, Toggle):
            element()
        elif isinstance(element, InputField):
            if not element.is_open:
                element.open()
            else:
                element.close()
        elif isinstance(element, Selector):
            if not element.is_open:
                element.open()
            else:
                element.close()

    if previously_selected_id != element.id and isinstance(previously_selected, InputField) and previously_selected.is_open:
        previously_selected.cancel()

    return True


def manage_menu_mousebuttonup(menu: MenuType, renderer: MenuPass, event: pygame.event.Event) -> bool:
    """"""
    if event.type != pygame.MOUSEBUTTONUP:
        raise ValueError("Improper event handling")
    
    # Parse MOUSEBUTTONUP event attributes
    position = event.pos
    button = event.button
    is_touch = event.touch
    element = menu.get_selected_element()

    return False


def manage_menu_mousewheel(menu: MenuType, renderer: MenuPass, event: pygame.event.Event) -> bool:
    """"""
    if event.type != pygame.MOUSEWHEEL:
        raise ValueError("Improper event handling")

    # Parse MOUSEWHEEL event attributes
    y = event.y
    x = event.x
    precise_y = event.precise_y
    precise_x = event.precise_x
    is_flipped = event.flipped

    element = menu.get_selected_element()

    if isinstance(element, Selector):
        if not element.is_open:
            element.open()
        if precise_y > 0:
            element.next()
        elif precise_y < 0:
            element.previous()
        return True

    if isinstance(element, Slider):
        if precise_y > 0:
            element.increment()
        elif precise_y < 0:
            element.decrement()
        return True
    
    # TODO: Correct Implementation in MenuPass
    menu._scroll += -y * 2.0
    return True


def manage_menu_keydown(menu: MenuType, renderer: MenuPass, event: pygame.event.Event) -> bool:
    """"""
    if event.type != pygame.KEYDOWN:
        raise ValueError("Improper event handling")

    key = event.key
    element = menu.get_selected_element()

    # Match keydown with associated element

    if isinstance(element, Button):
        if key == pygame.K_RETURN:
            # Call the element action
            element()
            return True

    elif isinstance(element, InputField):
        if key == pygame.K_RETURN and not element.is_open:
            element.open()
            return True
        if element.is_open:
            if key == pygame.K_RETURN:
                element.close()
                return True
            if key == pygame.K_ESCAPE:
                element.cancel()
                return True
            if key == pygame.K_BACKSPACE:
                element.truncate()
                return True

    elif isinstance(element, Selector):
        if key == pygame.K_RETURN and not element.is_open:
            element.open()
            return True
        if element.is_open:
            if key == pygame.K_RETURN:
                element.close()
                return True
            if key == pygame.K_ESCAPE:
                element.cancel()
                return True
            if key == pygame.K_RIGHT:
                element.next()
                return True
            if key == pygame.K_LEFT:
                element.previous()
                return True

    elif isinstance(element, Slider):
        pass

    elif isinstance(element, Toggle):
        if key == pygame.K_RETURN:
            element()
            return True

    # Escape within menu stack
    if key == pygame.K_ESCAPE:
        menu_manager.pop_stack()
        return True

    # Navigate between elements
    if key == pygame.K_UP:
        menu.move_selected_up()
        return True

    elif key == pygame.K_DOWN:
        menu.move_selected_down()
        return True

    return False


def manage_menu_textinput(menu: MenuType, renderer: MenuPass, event: pygame.event.Event) -> bool:
    """"""
    if event.type != pygame.TEXTINPUT:
        raise ValueError("Improper event handling")
    
    text = event.text
    element = menu.get_selected_element()

    if isinstance(element, InputField) and element.is_open:
        element.append(text)
        return True

    return False


# Module-level singleton
menu_manager: MenuManager = MenuManager()
