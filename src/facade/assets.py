"""
assets.py

Asset management - loading and caching the fonts and images that menus use.

Each MenuRenderer owns one FontManager and one ImageManager:

    ui.fonts.add_dir("assets/fonts")   # registers e.g. editundo.ttf
    ui.images.add_dir("assets/images")
"""

import pygame

from pathlib import Path
from typing import Dict, Tuple


class FontManager:
    """Font registry: discovers font files, caches Font objects by
    (family, size), and falls back to the pygame default font.

    Fonts are registered under their lower-cased file name, which is what
    ``Text.font_name`` refers to. For example ``EditUndo.ttf`` is found as
    ``"editundo.ttf"``.
    """

    def __init__(self) -> None:
        self._paths: Dict[str, Path] = {}  # family -> file path
        self._cache: Dict[Tuple[str | None, int], pygame.font.Font] = {}  # (family, size) -> Font

    def __contains__(self, family: str) -> bool:
        return family.lower() in self._paths

    """Font mutations."""

    def add_dir(self, dirpath: str = "assets/fonts") -> None:
        """Recursively discover font files under *dirpath* and register them"""
        root = Path(dirpath)
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in {".ttf", ".otf"}:
                continue
            family = entry.name.lower()
            self._paths[family] = entry

    def add_path(self, family: str, filepath: str) -> None:
        """Manually register a single font file under the given *family* name."""
        self._paths[family.lower()] = Path(filepath)

    def clear_paths(self) -> None:
        """Forget all registered fonts and drop the cache."""
        self._paths.clear()
        self._cache.clear()

    """Font queries."""

    def get_font(self, family: str | None = None, size: int = 16) -> pygame.font.Font:
        """Return a ``pygame.font.Font`` for the requested *family* and *size*.

        Results are cached so repeated calls are essentially free.
        If *family* is ``None`` or not found, the pygame default font is used.
        """
        key = (family.lower() if family else None, size)
        if key not in self._cache:
            path = self._paths.get(key[0]) if key[0] else None
            self._cache[key] = pygame.font.Font(str(path) if path else None, size)
        return self._cache[key]


class ImageManager:
    """Simple image registry: loads images once, caches them, and provides
    reload/clear capabilities.
    """

    def __init__(self):
        self._placeholder: pygame.Surface | None = None
        self._paths: Dict[str, Path] = {}
        self._cache: Dict[str, pygame.Surface] = {}

    @property
    def placeholder(self) -> pygame.Surface:
        """Return a magenta placeholder surface for missing images."""
        if not self._placeholder:
            surf = pygame.Surface((32, 32), pygame.SRCALPHA).convert_alpha()
            surf.fill((255, 0, 255, 255))
            self._placeholder = surf
        return self._placeholder

    """Image mutations."""

    def add_dir(self, dirpath: str = "images") -> None:
        """Load all images from a directory recursively."""
        root = Path(dirpath)
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
                continue
            self.add_path(entry)

    def add_path(self, path: Path) -> None:
        """Load a single image file."""
        key = str(path)
        if key in self._cache:
            return
        try:
            surf = pygame.image.load(path)
            surf = surf.convert_alpha()
        except Exception:
            surf = self.placeholder
        self._cache[key] = surf

    def clear_paths(self) -> None:
        """Clear all loaded images."""
        self._cache.clear()

    "Image queries."

    def get_image(self, image: str) -> pygame.Surface | None:
        """Get an image by path, loading if necessary."""
        if image not in self._cache:
            path = Path(image)
            if path.exists():
                self.add_path(path)
        return self._cache.get(image)

