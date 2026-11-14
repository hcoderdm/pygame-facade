"""
Themes: roles resolved when drawing, switching themes, and generated colours.
"""

from dataclasses import FrozenInstanceError, dataclass, replace

import pygame
import pytest

from facade import DEFAULT_THEME, DebugRenderer, Element, Gap, Interface, Menu, MenuRenderer, NormalText, Theme, ThemeColorType, mix_rgba

SIZE = (200, 100)
GREEN_THEME = replace(DEFAULT_THEME, background="#00FF00FF", text_normal="#0000FFFF", extras={"table": "#123456FF"})


@dataclass(kw_only=True)
class Panel(Menu):
    """A bare menu for the rules below."""


def counting_recomposes(ui):
    calls = []
    compose = ui.renderer._compose_tree
    ui.renderer._compose_tree = lambda *args: calls.append(1) or compose(*args)
    return calls


def test_roles_are_drawn_in_the_interface_theme():
    ui = Interface(size=SIZE, theme=GREEN_THEME)
    ui.push(Panel())

    surface = ui.render()

    assert surface.get_at((0, 0)) == pygame.Color("#00FF00FF")


def test_switching_theme_redraws_without_counting_as_an_edit():
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[NormalText(text="score")]))
    first = ui.render()
    version = Element._render_version

    ui.theme = GREEN_THEME
    second = ui.render()

    assert first.get_at((0, 0)) == pygame.Color(DEFAULT_THEME.background)
    assert second.get_at((0, 0)) == pygame.Color("#00FF00FF")
    assert Element._render_version == version


def test_setting_an_equal_theme_keeps_the_composed_menu():
    ui = Interface(size=SIZE)
    ui.push(Panel())
    calls = counting_recomposes(ui)
    ui.render()

    ui.theme = replace(DEFAULT_THEME)
    ui.render()

    assert len(calls) == 1


def test_text_drawn_before_a_theme_change_is_not_reused_after_it():
    text = NormalText(text="score", is_selectable=True)
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[Gap(is_selectable=True), text]))
    ui.render()

    ui.theme = GREEN_THEME
    surface = ui.render()

    rect = next(rect for hit, rect in ui.renderer._menu_tree.hit_rects if hit is text)
    pixels = {tuple(surface.get_at((px, py))) for px in range(rect.left, rect.right) for py in range(rect.top, rect.bottom)}
    assert (0, 0, 255, 255) in pixels  # The new theme's normal text colour


def test_fixed_colours_ignore_the_theme():
    ui = Interface(size=SIZE, theme=GREEN_THEME)
    ui.push(Panel(root_background_color="#FF0000FF"))

    assert ui.render().get_at((0, 0)) == pygame.Color("#FF0000FF")


def test_generated_colours_follow_the_theme():
    theme = replace(DEFAULT_THEME, heading="#FFFFFFFF", background="#000000FF", text_normal="#FFFFFFFF", surface_input="#000000FF")

    assert theme.get_rgba(ThemeColorType.HEADING_SHADOW) == mix_rgba("#FFFFFFFF", "#000000FF", 0.6) == "#666666FF"
    assert theme.get_rgba(ThemeColorType.TEXT_DISABLED) == mix_rgba("#FFFFFFFF", "#000000FF", 0.62)


def test_every_role_has_a_colour():
    for role in ThemeColorType:
        assert DEFAULT_THEME.get_rgba(role).startswith("#")


def test_themes_are_frozen():
    with pytest.raises(FrozenInstanceError):
        DEFAULT_THEME.primary = "#FF0000FF"  # type: ignore[misc]


def test_debug_renderer_passes_its_theme_through():
    ui = Interface(size=SIZE)
    ui.renderer = DebugRenderer(MenuRenderer())
    ui.push(Panel())

    ui.theme = GREEN_THEME

    assert ui.renderer.renderer.theme is GREEN_THEME
    assert ui.render().get_at((0, 0)) == pygame.Color("#00FF00FF")


def test_games_read_their_own_colours_from_the_theme():
    assert GREEN_THEME.get_extra("table") == "#123456FF"
