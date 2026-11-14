"""
test_text_elements.py
"""

from dataclasses import dataclass
from pathlib import Path

import pygame

from facade import DEFAULT_THEME, BulletList, CreditList, Element, Interface, Menu, NormalText, SectionHeader, TextBlock

SIZE = (800, 600)
FONTS = Path(__file__).resolve().parents[1] / "examples" / "assets" / "fonts"
RED, BLUE, GREEN = "#FF0000FF", "#0000FFFF", "#00FF00FF"


@dataclass(kw_only=True)
class Panel(Menu):
    """A bare menu for the layout rules below."""


def rendered(element):
    """Render ``element`` alone and return the output surf and the element's rect."""
    interface = Interface(size=SIZE)
    interface.fonts.add_dir(str(FONTS))
    interface.push_stack(Panel(root_elements=[element]))
    surf = interface.render()
    tree = interface.renderer._menu_tree
    assert tree is not None
    rect = next(rect for hit, rect in tree.element_rects if hit is element)
    return interface, surf, rect


def ink(surf, rect, color):
    """Every pixel of ``color`` inside ``rect``."""
    target = pygame.Color(DEFAULT_THEME.get_rgba(color))
    return [(px, py) for px in range(rect.left, rect.right) for py in range(rect.top, rect.bottom) if surf.get_at((px, py)) == target]


def bands(values):
    """Consecutive runs in sorted ``values``, as (first, last) pairs."""
    runs = []
    for value in sorted(set(values)):
        if runs and value == runs[-1][1] + 1:
            runs[-1][1] = value
        else:
            runs.append([value, value])
    return [tuple(run) for run in runs]


def body(color=RED):
    return TextBlock.BodyText(text_color=color)


def test_261113202742_01dc8a89():
    # Text block wraps inside its width with the line gap.
    block = TextBlock(size=(120.0, 0.0), body_text=body(), paragraphs=["ONE TWO THREE FOUR FIVE SIX SEVEN"])
    _, surf, rect = rendered(block)
    pixels = ink(surf, rect, RED)
    lines = bands(py for _, py in pixels)

    assert len(lines) >= 3
    assert max(px for px, _ in pixels) < rect.left + 120
    assert all(last - first + 1 == 8 for first, last in lines)  # Capital height at the native size.
    assert all(lines[i + 1][0] - lines[i][1] - 1 == block.line_gap_ph for i in range(len(lines) - 1))


def test_261113202742_17c406a4():
    # Paragraphs are spaced by the paragraph gap.
    block = TextBlock(body_text=body(), paragraphs=["ONE", "TWO"])
    _, surf, rect = rendered(block)
    (_, first_end), (second_start, _) = bands(py for _, py in ink(surf, rect, RED))

    assert second_start - first_end - 1 == block.paragraph_gap_ph


def test_261113202742_40fdf0ae():
    # Spans keep their colours and the spacing of plain text.
    mixed = TextBlock(body_text=body(), paragraphs=[["AB", NormalText(text="CD", text_color=BLUE)]])
    plain = TextBlock(body_text=body(), paragraphs=["AB CD"])
    _, mixed_surf, mixed_rect = rendered(mixed)
    _, plain_surf, plain_rect = rendered(plain)

    red = [px - mixed_rect.left for px, _ in ink(mixed_surf, mixed_rect, RED)]
    blue = [px - mixed_rect.left for px, _ in ink(mixed_surf, mixed_rect, BLUE)]
    plain_columns = sorted({px - plain_rect.left for px, _ in ink(plain_surf, plain_rect, RED)})

    assert red and blue
    assert sorted(set(red)) + sorted(set(blue)) == plain_columns  # Same pixels as the one-colour line, split by colour.


def test_261113202742_d59980b2():
    # Bullet is centred on the first line.
    items = BulletList(body_text=body(), bullet_color=GREEN, paragraphs=["FIRST ITEM", "SECOND"])
    _, surf, rect = rendered(items)
    (line_top, line_bottom), *_ = bands(py for _, py in ink(surf, rect, RED))
    (bullet_top, bullet_bottom), *_ = bands(py for _, py in ink(surf, rect, GREEN))

    assert bullet_top - line_top == line_bottom - bullet_bottom


def test_261113202742_6e469507():
    # Wrapped bullet lines indent under the text.
    items = BulletList(size=(110.0, 0.0), body_text=body(), bullet_color=GREEN, paragraphs=["ONE TWO THREE FOUR FIVE"])
    _, surf, rect = rendered(items)
    pixels = ink(surf, rect, RED)
    lines = bands(py for _, py in pixels)
    starts = [min(px for px, py in pixels if first <= py <= last) for first, last in lines]

    assert len(lines) >= 2
    assert len(set(starts)) == 1


def test_261113202742_cb72d9d4():
    # Credit names end at the edge and the leader sits on the baseline.
    credits = CreditList(
        size=(200.0, 0.0), credits=[("ART", "SOMEONE")],
        role_text=CreditList.RoleText(text_color=BLUE), name_text=CreditList.NameText(text_color=RED), leader_color=GREEN,
    )
    _, surf, rect = rendered(credits)
    name = ink(surf, rect, RED)
    leader = ink(surf, rect, GREEN)

    assert max(px for px, _ in name) == rect.left + 199
    assert max(py for _, py in leader) == max(py for _, py in name)
    assert max(px for px, _ in leader) == min(px for px, _ in name) - credits.leader_gap_pw - 1


def test_261113202742_7c06eaed():
    # Section header rule reaches the edge centred on the label.
    header = SectionHeader(size=(200.0, 0.0), label=SectionHeader.HeaderText(text="CREDITS", text_color=RED), rule_color=GREEN)
    _, surf, rect = rendered(header)
    label = ink(surf, rect, RED)
    rule = ink(surf, rect, GREEN)
    label_top, label_bottom = min(py for _, py in label), max(py for _, py in label)
    rule_top, rule_bottom = min(py for _, py in rule), max(py for _, py in rule)

    assert max(px for px, _ in rule) == rect.left + 199
    assert min(px for px, _ in rule) == max(px for px, _ in label) + header.rule_gap_pw + 1
    assert rule_top - label_top == label_bottom - rule_bottom


def test_261113202742_c247afbd():
    # Rendering text elements is not an edit.
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[
        TextBlock(paragraphs=["ONE", ["TWO", TextBlock.EmphasisText(text="THREE")]]),
        BulletList(paragraphs=["ITEM"]),
        CreditList(credits=[("ROLE", "NAME")]),
        SectionHeader(label=SectionHeader.HeaderText(text="HEADER")),
    ]))
    version = Element._render_version

    interface.render()

    assert Element._render_version == version


def test_261113202742_628902b5():
    # Assigning new paragraphs redraws.
    block = TextBlock(paragraphs=["BEFORE"])
    interface = Interface(size=SIZE)
    interface.push_stack(Panel(root_elements=[block]))
    first = interface.render()

    block.paragraphs = ["AFTER"]

    assert interface.render() is not first
