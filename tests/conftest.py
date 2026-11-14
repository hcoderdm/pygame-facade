"""
conftest.py
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def display():
    """A window must exist before rendering, as in a real game."""
    pygame.init()
    surf = pygame.display.set_mode((1, 1))
    yield surf
    pygame.quit()
