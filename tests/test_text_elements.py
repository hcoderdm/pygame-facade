"""
Text blocks, bullet lists, credit lists and section headers.
"""

from dataclasses import dataclass
from pathlib import Path

import pygame

from facade import BulletList, CreditList, Element, Interface, Menu, NormalText, SectionHeader, TextBlock

SIZE = (800, 600)
FONTS = Path(__file__).resolve().parents[1] / "examples" / "assets" / "fonts"
RED, BLUE, GREEN = "#FF0000FF", "#0000FFFF", "#00FF00FF"


@dataclass(kw_only=True)
class Panel(Menu):
    """A bare menu for the layout rules below."""


def rendered(element):
    """Render ``element`` alone and return the output surface and the element's rect."""
    ui = Interface(size=SIZE)
    ui.fonts.add_dir(str(FONTS))
    ui.push(Panel(root_elements=[element]))
    surface = ui.render()
    rect = next(rect for hit, rect in ui.renderer._menu_tree.element_rects if hit is element)
    return ui, surface, rect


def ink(surface, rect, color):
    """Every pixel of ``color`` inside ``rect``."""
    target = pygame.Color(color)
    return [(px, py) for px in range(rect.left, rect.right) for py in range(rect.top, rect.bottom) if surface.get_at((px, py)) == target]


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


def test_text_block_wraps_inside_its_width_with_the_line_gap():
    block = TextBlock(size=(120.0, 0.0), body_text=body(), paragraphs=["ONE TWO THREE FOUR FIVE SIX SEVEN"])
    _, surface, rect = rendered(block)
    pixels = ink(surface, rect, RED)
    lines = bands(py for _, py in pixels)

    assert len(lines) >= 3
    assert max(px for px, _ in pixels) < rect.left + 120
    assert all(last - first + 1 == 8 for first, last in lines)  # Capital height at the native size
    assert all(lines[i + 1][0] - lines[i][1] - 1 == block.line_gap_ph for i in range(len(lines) - 1))


def test_paragraphs_are_spaced_by_the_paragraph_gap():
    block = TextBlock(body_text=body(), paragraphs=["ONE", "TWO"])
    _, surface, rect = rendered(block)
    (_, first_end), (second_start, _) = bands(py for _, py in ink(surface, rect, RED))

    assert second_start - first_end - 1 == block.paragraph_gap_ph


def test_spans_keep_their_colours_and_the_spacing_of_plain_text():
    mixed = TextBlock(body_text=body(), paragraphs=[["AB", NormalText(text="CD", text_color=BLUE)]])
    plain = TextBlock(body_text=body(), paragraphs=["AB CD"])
    _, mixed_surf, mixed_rect = rendered(mixed)
    _, plain_surf, plain_rect = rendered(plain)

    red = [px - mixed_rect.left for px, _ in ink(mixed_surf, mixed_rect, RED)]
    blue = [px - mixed_rect.left for px, _ in ink(mixed_surf, mixed_rect, BLUE)]
    plain_columns = sorted({px - plain_rect.left for px, _ in ink(plain_surf, plain_rect, RED)})

    assert red and blue
    assert sorted(set(red)) + sorted(set(blue)) == plain_columns  # Same pixels as the one-colour line, split by colour


def test_bullet_is_centred_on_the_first_line():
    items = BulletList(body_text=body(), bullet_color=GREEN, paragraphs=["FIRST ITEM", "SECOND"])
    _, surface, rect = rendered(items)
    (line_top, line_bottom), *_ = bands(py for _, py in ink(surface, rect, RED))
    (bullet_top, bullet_bottom), *_ = bands(py for _, py in ink(surface, rect, GREEN))

    assert bullet_top - line_top == line_bottom - bullet_bottom


def test_wrapped_bullet_lines_indent_under_the_text():
    items = BulletList(size=(110.0, 0.0), body_text=body(), bullet_color=GREEN, paragraphs=["ONE TWO THREE FOUR FIVE"])
    _, surface, rect = rendered(items)
    pixels = ink(surface, rect, RED)
    lines = bands(py for _, py in pixels)
    starts = [min(px for px, py in pixels if first <= py <= last) for first, last in lines]

    assert len(lines) >= 2
    assert len(set(starts)) == 1


def test_credit_names_end_at_the_edge_and_the_leader_sits_on_the_baseline():
    credits = CreditList(
        size=(200.0, 0.0), credits=[("ART", "SOMEONE")],
        role_text=CreditList.RoleText(text_color=BLUE), name_text=CreditList.NameText(text_color=RED), leader_color=GREEN,
    )
    _, surface, rect = rendered(credits)
    name = ink(surface, rect, RED)
    leader = ink(surface, rect, GREEN)

    assert max(px for px, _ in name) == rect.left + 199
    assert max(py for _, py in leader) == max(py for _, py in name)
    assert max(px for px, _ in leader) == min(px for px, _ in name) - credits.leader_gap_pw - 1


def test_section_header_rule_reaches_the_edge_centred_on_the_label():
    header = SectionHeader(size=(200.0, 0.0), label=SectionHeader.HeaderText(text="CREDITS", text_color=RED), rule_color=GREEN)
    _, surface, rect = rendered(header)
    label = ink(surface, rect, RED)
    rule = ink(surface, rect, GREEN)
    label_top, label_bottom = min(py for _, py in label), max(py for _, py in label)
    rule_top, rule_bottom = min(py for _, py in rule), max(py for _, py in rule)

    assert max(px for px, _ in rule) == rect.left + 199
    assert min(px for px, _ in rule) == max(px for px, _ in label) + header.rule_gap_pw + 1
    assert rule_top - label_top == label_bottom - rule_bottom


def test_rendering_text_elements_is_not_an_edit():
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[
        TextBlock(paragraphs=["ONE", ["TWO", TextBlock.EmphasisText(text="THREE")]]),
        BulletList(paragraphs=["ITEM"]),
        CreditList(credits=[("ROLE", "NAME")]),
        SectionHeader(label=SectionHeader.HeaderText(text="HEADER")),
    ]))
    version = Element._render_version

    ui.render()

    assert Element._render_version == version


def test_assigning_new_paragraphs_redraws():
    block = TextBlock(paragraphs=["BEFORE"])
    ui = Interface(size=SIZE)
    ui.push(Panel(root_elements=[block]))
    first = ui.render()

    block.paragraphs = ["AFTER"]

    assert ui.render() is not first
