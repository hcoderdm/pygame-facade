"""
Renderer output format and caching.
"""

from types import SimpleNamespace

from facade import Element, Interface, NormalText, Pause, Settings, Start

SIZE = (800, 600)


def counting_recomposes(ui):
    """Wrap the renderer's compose step and return a list counting its calls."""
    calls = []
    compose = ui.renderer._compose_menu_tree
    ui.renderer._compose_menu_tree = lambda *args: calls.append(1) or compose(*args)
    return calls


def test_composing_a_menu_is_not_an_edit():
    ui = Interface(size=SIZE)
    ui.push(Settings(settings=SimpleNamespace(VOLUME=1.0, MUTE=False)))
    version = Element._iterative_version

    ui.render()

    assert Element._iterative_version == version


def test_creating_elements_elsewhere_keeps_the_cache():
    ui = Interface(size=SIZE)
    ui.push(Pause())
    first = ui.render()

    NormalText(text="score: 10")  # e.g. a game building its own elements each frame

    assert ui.render() is first


def test_two_interfaces_keep_their_own_caches():
    a, b = Interface(size=SIZE), Interface(size=SIZE)
    a.push(Pause())
    b.push(Start())
    calls_a, calls_b = counting_recomposes(a), counting_recomposes(b)

    for _ in range(5):
        a.render()
        b.render()

    assert (len(calls_a), len(calls_b)) == (1, 1)
