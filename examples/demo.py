"""
demo.py
"""

import argparse
from pathlib import Path

import pygame

import settings  # examples/settings.py, edited live by the Settings menu.
from facade import DebugRenderer, Interface, MenuRenderer
from menus import About, Pause, Settings, Start  # examples/menus.py, this game's screens.
from themes import TABLE_FELT  # examples/themes.py, the colours the menus and the table share.


# The Settings menu's boxes, in the order settings.py lists them.
SETTINGS_SECTIONS = {
    "Display": ["FPS"],
    "Audio": ["MASTER_VOLUME", "MUSIC_VOLUME", "SFX_VOLUME", "MUTE_AUDIO"],
    "Gameplay": ["PLAYER_NAME", "DIFFICULTY", "INVERT_Y_AXIS"],
    "Debug": ["DEBUG_MODE", "SHOW_FPS", "SHOW_HITBOXES"],
}


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
    interface = Interface(size=screen.get_size(), theme=TABLE_FELT)
    # A renderer with debugging aids that the keys below switch on.
    debug = DebugRenderer(MenuRenderer(TABLE_FELT))
    interface.renderer = debug
    # Register the bundled pixel font. Text elements default to "editundo.ttf".
    interface.fonts.add_dir(str(Path(__file__).parent / "assets" / "fonts"))

    debug_keybinds = {
        pygame.K_F3: debug.toggle_stats_overlay,
        pygame.K_F4: debug.toggle_hover_border,
        pygame.K_F5: debug.toggle_hit_rects,
    }

    def quit_game() -> None:
        nonlocal running
        running = False

    def back_to_title() -> None:
        interface.clear_stack()
        interface.push_stack(Start)

    interface.add_menu(Settings(settings=settings, sections=SETTINGS_SECTIONS, on_return=interface.pop_stack))
    interface.add_menu(About(on_return=interface.pop_stack))
    interface.add_menu(Pause(on_resume=interface.pop_stack, on_restart=interface.pop_stack, on_exit=back_to_title))
    interface.push_stack(
        Start(
            on_start=interface.clear_stack,  # Close every menu and play.
            on_settings=lambda: interface.push_stack(Settings),
            on_about=lambda: interface.push_stack(About),
            on_quit=quit_game,
        )
    )

    # Run the game.
    while running:
        dt = clock.tick(settings.FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                interface.resize(event.size)  # Keep the GUI surface the size of the window.
            elif event.type == pygame.KEYDOWN and event.key in debug_keybinds:
                debug_keybinds[event.key]()  # Checked before the menu so debug keys work while typing too.
            elif interface.handle_event(event):
                continue  # The menu used this event.
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Escape reaches the game when there is no menu to go back to.
                if not interface.is_showing:
                    interface.push_stack(Pause)
                elif isinstance(interface.top_stack(), Pause):
                    interface.pop_stack()

        # The ball keeps rolling behind the see-through title screen, and stops under every other menu.
        if not interface.is_showing or isinstance(interface.top_stack(), Start):
            ball += velocity * dt
            width, height = screen.get_size()
            if ball.x < 20 or ball.x > width - 20:
                velocity.x = abs(velocity.x) if ball.x < 20 else -abs(velocity.x)
            if ball.y < 20 or ball.y > height - 20:
                velocity.y = abs(velocity.y) if ball.y < 20 else -abs(velocity.y)

        # Draw the game, then the GUI over it
        # The game draws with the theme's own colours, so it matches the menus over it.
        screen.fill(interface.theme.get_extra("table"))
        pygame.draw.circle(screen, interface.theme.get_extra("ball"), ball, 20)
        if (gui := interface.render()) is not None:
            screen.blit(gui, (0, 0))
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
