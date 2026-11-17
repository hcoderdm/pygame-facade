"""
assets.py
"""

from pathlib import Path
from typing import Dict, Tuple

import pygame


class FontManager:
    def __init__(self) -> None:
        self._paths: Dict[str, Path] = {}  # family -> file path.
        self._cache: Dict[Tuple[str | None, int], pygame.font.Font] = {}  # (family, size) -> Font.

    def __contains__(self, family: str) -> bool:
        return family.lower() in self._paths

    # -------------------------------------------------------------------------

    def add_dir(self, dirpath: str = "assets/fonts") -> None:
        root = Path(dirpath)
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in {".ttf", ".otf"}:
                continue
            family = entry.name.lower()
            self._paths[family] = entry

    def add_path(self, family: str, filepath: str) -> None:
        self._paths[family.lower()] = Path(filepath)

    def clear_paths(self) -> None:
        self._paths.clear()
        self._cache.clear()

    # -------------------------------------------------------------------------

    def get_font(self, family: str | None = None, size: int = 16) -> pygame.font.Font:
        key = (family.lower() if family else None, size)
        if key not in self._cache:
            path = self._paths.get(key[0]) if key[0] else None
            self._cache[key] = pygame.font.Font(str(path) if path else None, size)
        return self._cache[key]


class ImageManager:
    def __init__(self):
        self._placeholder: pygame.Surface | None = None
        self._paths: Dict[str, Path] = {}
        self._cache: Dict[str, pygame.Surface] = {}

    def get_placeholder(self) -> pygame.Surface:
        if not self._placeholder:
            surf = pygame.Surface((32, 32), pygame.SRCALPHA).convert_alpha()
            surf.fill((255, 0, 255, 255))
            self._placeholder = surf
        return self._placeholder

    # -------------------------------------------------------------------------

    def add_dir(self, dirpath: str = "images") -> None:
        root = Path(dirpath)
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
                continue
            self.add_path(entry)

    def add_path(self, path: Path) -> None:
        key = str(path)
        if key in self._cache:
            return
        try:
            surf = pygame.image.load(path)
            surf = surf.convert_alpha()
        except Exception:
            surf = self.get_placeholder()
        self._cache[key] = surf

    def clear_paths(self) -> None:
        self._cache.clear()

    # -------------------------------------------------------------------------

    def get_image(self, image: str) -> pygame.Surface | None:
        if image not in self._cache:
            path = Path(image)
            if path.exists():
                self.add_path(path)
        return self._cache.get(image)
