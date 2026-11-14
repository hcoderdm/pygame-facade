"""
test_theme.py
"""

from dataclasses import FrozenInstanceError, dataclass, replace

import pygame
import pytest

from facade import DEFAULT_THEME, DebugRenderer, Element, Gap, Interface, Menu, MenuRenderer, NormalText, ThemeColorType, mix_rgba

SIZE = (200, 100)
GREEN_THEME = replace(DEFAULT_THEME, background="#00FF00FF", text_normal="#0000FFFF", extras={"table": "#123456FF"})


@dataclass(kw_only=True)
class Panel(Menu):
    """A bare menu for the rules below."""


def counting_recomposes(interface):
    calls = []
    compose = interface.renderer._compose_tree
    interface.renderer._compose_tree = lambda *args: calls.append(1) or compose(*args)
    return calls


def test_261113211533_fa53db4c():
    # Roles are drawn in the interface theme.
    interface = Interface(size=SIZE, theme=GREEN_THEME)
    interface.push_stack(Panel())

    surf = interface.render()

    assert surf is not None
    assert surf.get_at((0, 0)) == pygame.Color("#00FF00FF")


def test_261113211533_364b3c47():
    # Switching theme redraws without counting as an edit.
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[NormalText(text="score")]))
    first = interface.render()
    version = Element._render_version

    interface.theme = GREEN_THEME
    second = interface.render()

    assert first is not None and second is not None
    assert first.get_at((0, 0)) == pygame.Color(DEFAULT_THEME.background)
    assert second.get_at((0, 0)) == pygame.Color("#00FF00FF")
    assert Element._render_version == version


def test_261113211533_d3427285():
    # Setting an equal theme keeps the composed menu.
    interface = Interface(size=SIZE)
    interface.push_stack(Panel())
    calls = counting_recomposes(interface)
    interface.render()

    interface.theme = replace(DEFAULT_THEME)
    interface.render()

    assert len(calls) == 1


def test_261113211533_3733ff27():
    # Text drawn before a theme change is not reused after it.
    text = NormalText(text="score", is_selectable=True)
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[Gap(is_selectable=True), text]))
    interface.render()

    interface.theme = GREEN_THEME
    surf = interface.render()

    tree = interface.renderer._menu_tree
    assert surf is not None and tree is not None
    rect = next(rect for hit, rect in tree.hit_rects if hit is text)
    pixels = {tuple(surf.get_at((px, py))) for px in range(rect.left, rect.right) for py in range(rect.top, rect.bottom)}
    assert (0, 0, 255, 255) in pixels  # The new theme's normal text colour.


def test_261113211533_8085e761():
    # Fixed colours ignore the theme.
    interface = Interface(size=SIZE, theme=GREEN_THEME)
    interface.push_stack(Panel(root_background_color="#FF0000FF"))

    surf = interface.render()

    assert surf is not None
    assert surf.get_at((0, 0)) == pygame.Color("#FF0000FF")


def test_261113211533_2c135d77():
    # Generated colours follow the theme.
    theme = replace(DEFAULT_THEME, heading="#FFFFFFFF", background="#000000FF", text_normal="#FFFFFFFF", surface_input="#000000FF")

    assert theme.get_rgba(ThemeColorType.HEADING_SHADOW) == mix_rgba("#FFFFFFFF", "#000000FF", 0.6) == "#666666FF"
    assert theme.get_rgba(ThemeColorType.TEXT_DISABLED) == mix_rgba("#FFFFFFFF", "#000000FF", 0.62)


def test_261113211533_e24e06c6():
    # Every role has a colour.
    for role in ThemeColorType:
        assert DEFAULT_THEME.get_rgba(role).startswith("#")


def test_261113211533_920a95ce():
    # Themes are frozen.
    with pytest.raises(FrozenInstanceError):
        DEFAULT_THEME.primary = "#FF0000FF"  # type: ignore[misc]


def test_261113211533_4989b12d():
    # Debug renderer passes its theme through.
    interface = Interface(size=SIZE)
    interface.renderer = DebugRenderer(MenuRenderer())
    interface.push_stack(Panel())

    interface.theme = GREEN_THEME

    assert interface.renderer.renderer.theme is GREEN_THEME
    surf = interface.render()
    assert surf is not None
    assert surf.get_at((0, 0)) == pygame.Color("#00FF00FF")


def test_261113211533_6bb4e5f8():
    # Games read their own colours from the theme.
    assert GREEN_THEME.get_extra("table") == "#123456FF"
