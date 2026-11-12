"""
demo.py

A minimal game that uses facade for its menus. The "game" is a ball
bouncing around the window; the menus are drawn over it as one GUI surface.

Run from the repository root after `pip install -e .`:

    python examples/demo.py
"""

import pygame

import settings  # examples/settings.py, edited live by the Settings menu
from facade import About, Interface, Pause, Settings, Start


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("facade demo")
    clock = pygame.time.Clock()

    running = True
    ball = pygame.Vector2(400, 300)
    velocity = pygame.Vector2(240, 180)

    ui = Interface(size=screen.get_size())
    # ui.fonts.add_dir("assets/fonts")  # Register your own fonts, e.g. editundo.ttf

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
            if not 20 <= ball.x <= 780:
                velocity.x *= -1
            if not 20 <= ball.y <= 580:
                velocity.y *= -1

        # Draw the game, then the GUI over it
        screen.fill((24, 64, 48))
        pygame.draw.circle(screen, (230, 190, 60), ball, 20)
        if (gui := ui.render()) is not None:
            screen.blit(gui, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
