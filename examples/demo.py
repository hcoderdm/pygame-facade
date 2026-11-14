"""
demo.py

A minimal game that uses facade for its menus. The "game" is a ball
bouncing around the window; the menus are drawn over it as one GUI surface.

Run from the repository root after `pip install -e .`:

    python examples/demo.py
"""

from pathlib import Path

import pygame

import settings  # examples/settings.py, edited live by the Settings menu
from facade import DebugRenderer, Interface, MenuRenderer
from menus import About, Pause, Settings, Start  # examples/menus.py, this game's screens


# The Settings menu's boxes, in the order settings.py lists them
SETTINGS_SECTIONS = {
    "Display": ["FPS"],
    "Audio": ["MASTER_VOLUME", "MUSIC_VOLUME", "SFX_VOLUME", "MUTE_AUDIO"],
    "Gameplay": ["PLAYER_NAME", "DIFFICULTY", "INVERT_Y_AXIS"],
    "Debug": ["DEBUG_MODE", "SHOW_FPS", "SHOW_HITBOXES"],
}


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
    pygame.display.set_caption("facade demo")
    clock = pygame.time.Clock()

    running = True
    ball = pygame.Vector2(400, 300)
    velocity = pygame.Vector2(240, 180)

    interface = Interface(size=screen.get_size())
    # A renderer with debugging aids that the keys below switch on
    debug = DebugRenderer(MenuRenderer())
    interface.renderer = debug
    # Register the bundled pixel font; Text elements default to "editundo.ttf".
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
        interface.clear()
        interface.push(Start)

    interface.add_menu(Settings(settings=settings, sections=SETTINGS_SECTIONS, on_return=interface.pop))
    interface.add_menu(About(on_return=interface.pop))
    interface.add_menu(Pause(on_resume=interface.pop, on_restart=interface.pop, on_exit=back_to_title))
    interface.push(
        Start(
            on_start=interface.clear,  # Close every menu and play
            on_settings=lambda: interface.push(Settings),
            on_about=lambda: interface.push(About),
            on_quit=quit_game,
        )
    )

    while running:
        dt = clock.tick(settings.FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                interface.resize(event.size)  # Keep the GUI surface the size of the window
            elif event.type == pygame.KEYDOWN and event.key in debug_keybinds:
                debug_keybinds[event.key]()  # Checked before the menu so debug keys work while typing too
            elif interface.handle_event(event):
                continue  # The menu used this event
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Escape reaches the game when there is no menu to go back to
                if not interface.is_open:
                    interface.push(Pause)
                elif isinstance(interface.top(), Pause):
                    interface.pop()

        # Update the game only while no menu is open
        if not interface.is_open:
            ball += velocity * dt
            width, height = screen.get_size()
            if ball.x < 20 or ball.x > width - 20:
                velocity.x = abs(velocity.x) if ball.x < 20 else -abs(velocity.x)
            if ball.y < 20 or ball.y > height - 20:
                velocity.y = abs(velocity.y) if ball.y < 20 else -abs(velocity.y)

        # Draw the game, then the GUI over it
        screen.fill((24, 64, 48))
        pygame.draw.circle(screen, (230, 190, 60), ball, 20)
        if (gui := interface.render()) is not None:
            screen.blit(gui, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
