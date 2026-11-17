"""
interface.py
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

import pygame

from .assets import FontManager, ImageManager
from .elements import InputField
from .manager import (
    ElementManager,
    MenuManager,
    handle_menu_keydown,
    handle_menu_mousebuttondown,
    handle_menu_mousebuttonup,
    handle_menu_mousemotion,
    handle_menu_mousewheel,
    handle_menu_textinput,
)
from .menus import Menu
from .renderer import DebugRenderer, MenuRenderer
from .theme import DEFAULT_THEME, Theme


_REPEAT_KEYS = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_BACKSPACE, pygame.K_DELETE)


class Interface:
    """
    A stack of menus drawn as one window-sized overlay.

    The GUI surface returned by ``render`` is the size of the window and is
    blitted at ``(0, 0)``, so mouse positions in events are used as-is. When
    no menu is open, ``render`` returns ``None`` and ``handle_event`` returns
    ``False`` for every event, leaving input to the game.
    """

    def __init__(self, size: tuple[int, int], theme: Theme = DEFAULT_THEME, use_hand_cursor: bool = True, repeat_delay: float = 0.4, repeat_interval: float = 0.05) -> None:
        """
        ``size`` is the window size in pixels. With ``use_hand_cursor`` the system
        cursor shows a hand over a selectable element, a text beam over an
        input field, and an arrow everywhere else. A held arrow key, Backspace,
        Delete or typed character repeats after ``repeat_delay`` seconds, then
        every ``repeat_interval`` seconds; repeats are applied in ``render``.
        ``theme`` gives the colours that elements' ``ThemeColorType`` roles are
        drawn in.
        """
        self.size: tuple[int, int] = (int(size[0]), int(size[1]))
        self.use_hand_cursor: bool = use_hand_cursor
        self.repeat_delay: float = repeat_delay
        self.repeat_interval: float = repeat_interval
        self._held_key: HeldKey | None = None
        self.menus: MenuManager = MenuManager()
        self.elements: ElementManager = ElementManager()
        self.renderer: MenuRenderer | DebugRenderer = MenuRenderer(theme)

        self._event_handlers: dict[int, Callable[[Menu, pygame.event.Event], bool]] = {
            pygame.MOUSEMOTION: lambda menu, event: handle_menu_mousemotion(menu, self.renderer, event, use_hand_cursor=self.use_hand_cursor),
            pygame.MOUSEBUTTONDOWN: lambda menu, event: handle_menu_mousebuttondown(menu, self.renderer, event),
            pygame.MOUSEBUTTONUP: lambda menu, event: handle_menu_mousebuttonup(menu, self.renderer, event),
            pygame.MOUSEWHEEL: lambda menu, event: handle_menu_mousewheel(menu, self.renderer, event),
            pygame.KEYDOWN: lambda menu, event: handle_menu_keydown(menu, self.renderer, event, manager=self.menus),
            pygame.TEXTINPUT: lambda menu, event: handle_menu_textinput(menu, self.renderer, event),
        }

    # -------------------------------------------------------------------------

    @property
    def fonts(self) -> FontManager:
        """Font registry used for ``Text.font_name`` lookups."""
        return self.renderer.fonts

    @property
    def images(self) -> ImageManager:
        """Image registry used for ``Image.image_path`` lookups."""
        return self.renderer.images

    @property
    def theme(self) -> Theme:
        """The colours menus are drawn in. Setting a different theme redraws the open menu with it."""
        return self.renderer.theme

    @theme.setter
    def theme(self, theme: Theme) -> None:
        self.renderer.theme = theme

    # -------------------------------------------------------------------------

    def add(self, menu: Menu) -> None:
        """Register ``menu`` so it can later be pushed by its type."""
        self.menus.add(menu)

    def push_stack(self, menu: Menu | type[Menu]) -> None:
        """
        Open a menu on top of the stack. Pass a menu instance (registered
        automatically) or the type of a menu registered with ``add``.
        """
        if isinstance(menu, Menu):
            self.menus.add(menu)
            menu = type(menu)
        if not self.menus.has(menu):
            raise KeyError(f"Invalid {menu=}")
        self.menus.push_stack(menu)

    def pop_stack(self) -> Menu | None:
        """Close the top menu and return it, or ``None`` if none is open."""
        return self.menus.pop_stack(keep_root=False)

    def clear_stack(self) -> None:
        """Close every open menu."""
        self.menus.clear_stack()

    def top_stack(self) -> Menu | None:
        """The menu currently shown, or ``None``."""
        return self.menus.top_stack()

    @property
    def is_showing(self) -> bool:
        """Whether any menu is shown."""
        return self.menus.top_stack() is not None

    # -------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Apply ``event`` to the top menu. Returns ``True`` if the GUI used the
        event, in which case the game should ignore it.
        """
        if event.type in (pygame.KEYUP, pygame.WINDOWFOCUSLOST):
            return self._release_key(event)
        menu = self.menus.top_stack()
        handler = self._event_handlers.get(event.type)
        if menu is None or handler is None:
            return False

        held = self._held_key
        if event.type == pygame.KEYDOWN:
            if held is not None and held.key == event.key:
                return True  # A repeat from pygame itself, when the game turned those on. The interface times its own.
            text = event.unicode if self._is_typing(menu) and event.unicode and event.unicode.isprintable() else ""
            is_used = handler(menu, event)
            is_repeating = is_used and (event.key in _REPEAT_KEYS or bool(text))
            self._held_key = HeldKey(event.key, event.mod, text, time.monotonic() + self.repeat_delay) if is_repeating else None
            return is_used
        if event.type == pygame.TEXTINPUT and held is not None and held.text and event.text == held.text:
            # The system repeats text on its own schedule too. Only the first press's text is used.
            if held.is_text_seen:
                return True
            held.is_text_seen = True
        return handler(menu, event)

    def _release_key(self, event: pygame.event.Event) -> bool:
        held = self._held_key
        if held is None or (event.type == pygame.KEYUP and event.key != held.key):
            return False
        self._held_key = None
        return event.type == pygame.KEYUP

    def _repeat_held_key(self, menu: Menu) -> None:
        held = self._held_key
        now = time.monotonic()
        if held is None or now < held.next_time:
            return
        # One repeat per frame at most, so a slow frame never fires a burst.
        held.next_time = max(held.next_time + self.repeat_interval, now)
        if held.text:
            if not self._is_typing(menu):
                self._held_key = None
                return
            handle_menu_textinput(menu, self.renderer, pygame.event.Event(pygame.TEXTINPUT, text=held.text))
        else:
            event = pygame.event.Event(pygame.KEYDOWN, key=held.key, mod=held.mod, unicode="", scancode=0)
            handle_menu_keydown(menu, self.renderer, event, manager=self.menus)

    @staticmethod
    def _is_typing(menu: Menu) -> bool:
        element = menu.get_selected_element()
        return isinstance(element, InputField) and element.is_open

    def resize(self, size: tuple[int, int]) -> None:
        """Set the GUI surface size, e.g. after the window is resized."""
        self.size = (int(size[0]), int(size[1]))

    def render(self) -> pygame.Surface | None:
        """
        Return the GUI surface for the top menu, or ``None`` when no menu is
        open. A menu that paints the whole window opaquely comes back without
        per-pixel alpha, so blitting it is a plain copy; otherwise the surface
        is ``SRCALPHA`` and transparent outside the menu. The same surface is
        returned while nothing visible has changed.
        """
        menu = self.menus.top_stack()
        if menu is None:
            return None
        self._repeat_held_key(menu)
        menu = self.menus.top_stack()  # A repeated key can close the menu.
        if menu is None:
            return None
        return self.renderer.render(menu, self.size)


# -----------------------------------------------------------------------------


@dataclass
class HeldKey:
    key: int
    mod: int
    text: str  # The character it types while a field is open, or "" for a key that is replayed as a key press.
    next_time: float  # When it next repeats, on the time.monotonic clock.
    is_text_seen: bool = False  # Whether the system's text event for the first press has arrived.
