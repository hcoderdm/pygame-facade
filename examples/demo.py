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
from facade import About, Interface, Pause, Settings, Start


def draw_fps(screen: pygame.Surface, font: pygame.font.Font, fps: float) -> None:
    """Draw an FPS readout in a black box at the top right of the window."""
    padding = 8
    text = font.render(f"{fps:.0f} FPS", True, (240, 240, 240))
    box = pygame.Rect(0, 0, text.get_width() + 2 * padding, text.get_height() + 2 * padding)
    box.topright = (screen.get_width() - padding, padding)
    pygame.draw.rect(screen, (0, 0, 0), box)
    screen.blit(text, (box.left + padding, box.top + padding))


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
    pygame.display.set_caption("facade demo")
    clock = pygame.time.Clock()

    running = True
    ball = pygame.Vector2(400, 300)
    velocity = pygame.Vector2(240, 180)

    ui = Interface(size=screen.get_size())
    # Register the bundled pixel font; Text elements default to "editundo.ttf".
    ui.fonts.add_dir(str(Path(__file__).parent / "assets" / "fonts"))
    fps_font = pygame.font.Font(None, 16)

    def quit_game() -> None:
        nonlocal running
        running = False

    def back_to_title() -> None:
        ui.clear()
        ui.push(Start)

    ui.add_menu(Settings(settings=settings, on_return=ui.pop))
    ui.add_menu(About(on_return=ui.pop))
    ui.add_menu(Pause(on_resume=ui.pop, on_restart=ui.pop, on_exit=back_to_title))
    ui.push(
        Start(
            on_start=ui.clear,  # Close every menu and play
            on_settings=lambda: ui.push(Settings),
            on_about=lambda: ui.push(About),
            on_quit=quit_game,
        )
    )

    while running:
        dt = clock.tick(settings.FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                ui.resize(event.size)  # Keep the GUI surface the size of the window
            elif ui.handle_event(event):
                continue  # The menu used this event
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Escape reaches the game when there is no menu to go back to
                if not ui.is_open:
                    ui.push(Pause)
                elif isinstance(ui.top(), Pause):
                    ui.pop()

        # Update the game only while no menu is open
        if not ui.is_open:
            ball += velocity * dt
            width, height = screen.get_size()
            if ball.x < 20 or ball.x > width - 20:
                velocity.x = abs(velocity.x) if ball.x < 20 else -abs(velocity.x)
            if ball.y < 20 or ball.y > height - 20:
                velocity.y = abs(velocity.y) if ball.y < 20 else -abs(velocity.y)

        # Draw the game, then the GUI over it
        screen.fill((24, 64, 48))
        pygame.draw.circle(screen, (230, 190, 60), ball, 20)
        if (gui := ui.render()) is not None:
            screen.blit(gui, (0, 0))
            draw_fps(screen, fps_font, clock.get_fps())
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
