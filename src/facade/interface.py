"""
interface.py

Interface - the one object a game uses. It owns a menu stack and a renderer,
takes the game's pygame events, and returns a GUI surface to blit over the
game's frame.

    ui = Interface(size=screen.get_size())
    ui.push(Start(on_start=start_game, on_quit=quit_game))

    for event in pygame.event.get():
        if ui.handle_event(event):
            continue
        ...  # the game's own input

    draw_game(screen)
    if (gui := ui.render()) is not None:
        screen.blit(gui, (0, 0))
"""

from __future__ import annotations

import pygame

from typing import Callable

from .assets import FontManager, ImageManager
from .manager import (
    MenuManager,
    handle_menu_keydown,
    handle_menu_mousebuttondown,
    handle_menu_mousebuttonup,
    handle_menu_mousemotion,
    handle_menu_mousewheel,
    handle_menu_textinput,
)
from .menus import Menu
from .renderer import MenuRenderer


class Interface:
    """
    A stack of menus drawn as one window-sized overlay.

    The GUI surface returned by ``render`` is the size of the window and is
    blitted at ``(0, 0)``, so mouse positions in events are used as-is. When
    no menu is open, ``render`` returns ``None`` and ``handle_event`` returns
    ``False`` for every event, leaving input to the game.
    """

    def __init__(self, size: tuple[int, int], use_hand_cursor: bool = True) -> None:
        """
        ``size`` is the window size in pixels. With ``use_hand_cursor`` the system
        cursor switches to a hand while hovering a selectable element.
        """
        self.size: tuple[int, int] = (int(size[0]), int(size[1]))
        self.use_hand_cursor: bool = use_hand_cursor
        self.manager: MenuManager = MenuManager()
        self.renderer: MenuRenderer = MenuRenderer()

        self._event_handlers: dict[int, Callable[[Menu, pygame.event.Event], bool]] = {
            pygame.MOUSEMOTION: lambda menu, event: handle_menu_mousemotion(menu, self.renderer, event, use_hand_cursor=self.use_hand_cursor),
            pygame.MOUSEBUTTONDOWN: lambda menu, event: handle_menu_mousebuttondown(menu, self.renderer, event),
            pygame.MOUSEBUTTONUP: lambda menu, event: handle_menu_mousebuttonup(menu, self.renderer, event),
            pygame.MOUSEWHEEL: lambda menu, event: handle_menu_mousewheel(menu, self.renderer, event),
            pygame.KEYDOWN: lambda menu, event: handle_menu_keydown(menu, self.renderer, event, manager=self.manager),
            pygame.TEXTINPUT: lambda menu, event: handle_menu_textinput(menu, self.renderer, event),
        }

    """
    Assets.
    """

    @property
    def fonts(self) -> FontManager:
        """Font registry used for ``Text.font_name`` lookups."""
        return self.renderer.fonts

    @property
    def images(self) -> ImageManager:
        """Image registry used for ``Image.image_path`` lookups."""
        return self.renderer.images

    """
    Menu stack.
    """

    def add_menu(self, menu: Menu) -> None:
        """Register ``menu`` so it can later be pushed by its type."""
        self.manager.add_menu(menu)

    def push(self, menu: Menu | type[Menu]) -> None:
        """
        Open a menu on top of the stack. Pass a menu instance (registered
        automatically) or the type of a menu registered with ``add_menu``.
        """
        if isinstance(menu, Menu):
            self.manager.add_menu(menu)
            menu = type(menu)
        if not self.manager.has_menu(menu):
            raise KeyError(f"No {menu.__name__} menu has been added")
        self.manager.push_stack(menu)

    def pop(self) -> Menu | None:
        """Close the top menu and return it, or ``None`` if none is open."""
        return self.manager.pop_stack(keep_root=False)

    def clear(self) -> None:
        """Close every open menu."""
        self.manager.clear_stack()

    def top(self) -> Menu | None:
        """The menu currently shown, or ``None``."""
        return self.manager.top_stack()

    @property
    def is_open(self) -> bool:
        """Whether any menu is shown."""
        return self.manager.top_stack() is not None

    """
    Frame loop.
    """

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Apply ``event`` to the top menu. Returns ``True`` if the GUI used the
        event, in which case the game should ignore it.
        """
        menu = self.manager.top_stack()
        handler = self._event_handlers.get(event.type)
        if menu is None or handler is None:
            return False
        return handler(menu, event)

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
        menu = self.manager.top_stack()
        if menu is None:
            return None
        return self.renderer.render(menu, self.size)
