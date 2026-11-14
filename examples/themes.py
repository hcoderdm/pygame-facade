"""
themes.py

The demo's theme. A game builds its own ``Theme`` the same way: pick a
handful of base colours, derive the rest with ``mix_rgba``, and add any
colours the game draws with itself to ``extras`` so the game and its menus
match.
"""

from __future__ import annotations

from facade import Theme, mix_rgba

FELT = "#184030FF"  # The pool table cloth
IVORY = "#FFF9DBFF"  # Open Color yellow 0, the colour of the cue ball
BLACK = "#000000FF"

_BACKGROUND = mix_rgba(FELT, BLACK, 0.45)
_SURFACE_INPUT = mix_rgba(FELT, BLACK, 0.25)

# Menus cut from the table: darker felt behind them, ivory text and fills, and the yellow of the
# 1-ball for focus, headings and changed values
TABLE_FELT = Theme(
    background=_BACKGROUND,
    surface_input=_SURFACE_INPUT,
    surface_display=mix_rgba(FELT, IVORY, 0.12),
    border_input=mix_rgba(IVORY, _SURFACE_INPUT, 0.15),
    border_display=mix_rgba(FELT, IVORY, 0.32),
    text_normal=IVORY,
    text_muted=mix_rgba(FELT, IVORY, 0.45),
    fill=IVORY,
    heading="#FFD43BFF",  # yellow 4
    shadow=mix_rgba(_BACKGROUND, BLACK, 0.55),
    primary="#FFD43BFF",  # yellow 4
    warning="#FFD43BFF",  # yellow 4
    danger="#FF6B6BFF",  # red 5
    success="#8CE99AFF",  # green 3
    info="#66D9E8FF",  # cyan 3
    extras={"table": FELT, "ball": "#FFD43BFF"},
)
