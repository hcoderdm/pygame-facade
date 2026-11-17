"""
main.py
"""

import argparse
from pathlib import Path

import pygame

import settings  # examples/settings.py, edited live by the Settings menu.
from elements import Panel, SettingLabel, SettingRow, TitleButton, TitlePrimaryButton
from facade import DebugRenderer, Interface, MenuRenderer, Theme, mix_rgba
from menus import About, Pause, Settings, Start


THEME = Theme(
    background="#0D231AFF",
    surface_input="#123024FF",
    surface_display="#345645FF",
    border_input="#DBDBC0FF",
    border_display="#627B67FF",
    text_normal="#FFF9DBFF",
    text_muted="#80937DFF",
    fill="#FFF9DBFF",
    heading="#FFD43BFF",  # yellow 4.
    shadow="#060F0CFF",
    primary="#FFD43BFF",  # yellow 4.
    warning="#FFD43BFF",  # yellow 4.
    danger="#FF6B6BFF",  # red 5.
    success="#8CE99AFF",  # green 3.
    info="#66D9E8FF",  # cyan 3.
    extras={"table": "#184030FF", "ball": "#FFD43BFF"},
)


def parse_args() -> argparse.Namespace:
    """Parse the arguments."""
    parser = argparse.ArgumentParser(description="Run a small game with facade menus over it.")
    parser.add_argument("--size", type=int, nargs=2, default=(800, 600), metavar=("PW", "PH"), help="")

    args = parser.parse_args()
    check_args(args)
    return args


def check_args(args: argparse.Namespace) -> None:
    """Check the arguments."""
    if min(args.size) < 1:
        raise SystemExit(f"Invalid {args.size=}")


# -----------------------------------------------------------------------------


def init_facade() -> Interface:
    """Build the interface, register fonts and elements, and add the menus."""

    renderer = DebugRenderer(MenuRenderer(THEME))
    interface = Interface(size=pygame.display.get_window_size(), renderer=renderer)

    interface.fonts.add_dir(str(Path(__file__).parent / "assets" / "fonts"))
    interface.images.add_dir(str(Path(__file__).parent / "assets" / "images"))

    for element_type in (TitleButton, TitlePrimaryButton, Panel, SettingLabel, SettingRow):
        interface.elements.add(element_type)

    # -------------------------------------------------------------------------

    def _on_about():
        interface.push_stack(About)

    def _on_exit():
        interface.clear_stack()
        interface.push_stack(Start)

    def _on_quit():
        # Equivalent to pygame.quit() and sys.exit().
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _on_restart():
        interface.pop_stack()

    def _on_resume():
        interface.pop_stack()

    def _on_return():
        interface.pop_stack()

    def _on_settings():
        interface.push_stack(Settings)

    def _on_start():
        interface.clear_stack()

    interface.add(Settings(settings=settings, sections=settings.SECTIONS, on_return=_on_return))
    interface.add(About(on_return=_on_return))
    interface.add(Pause(on_resume=_on_resume, on_restart=_on_restart, on_exit=_on_exit))
    interface.add(Start(on_start=_on_start, on_settings=_on_settings, on_about=_on_about, on_quit=_on_quit))

    return interface


def main() -> int:
    args = parse_args()

    # Open the window.
    pygame.init()
    screen = pygame.display.set_mode(args.size, pygame.RESIZABLE)
    pygame.display.set_caption("facade demo")
    clock = pygame.time.Clock()

    running = True
    ball = pygame.Vector2(400, 300)
    velocity = pygame.Vector2(240, 180)

    # Build the interface and its menus.
    interface = init_facade()
    interface.push_stack(Start)

    # Run the game.
    while running:
        dt = clock.tick(settings.FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                interface.resize(event.size)
            elif interface.handle_event(event):
                continue
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if not interface.is_showing:
                    interface.push_stack(Pause)
                elif isinstance(interface.top_stack(), Pause):
                    interface.pop_stack()

        if not interface.is_showing or isinstance(interface.top_stack(), Start):
            ball += velocity * dt
            width, height = screen.get_size()
            if ball.x < 20 or ball.x > width - 20:
                velocity.x = abs(velocity.x) if ball.x < 20 else -abs(velocity.x)
            if ball.y < 20 or ball.y > height - 20:
                velocity.y = abs(velocity.y) if ball.y < 20 else -abs(velocity.y)

        screen.fill(interface.theme.get_extra("table"))
        pygame.draw.circle(screen, interface.theme.get_extra("ball"), ball, 20)
        
        if (gui := interface.render()) is not None:
            screen.blit(gui, (0, 0))
        
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
