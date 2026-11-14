"""
test_interface.py
"""

import pygame
import pytest

from facade import Button, Element, HorizontalDivision, InputField, Interface, Menu, PrimaryButton, Selector, Slider, Toggle
from sample_menus import Overlay, Title, selected_label

SIZE = (800, 600)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def tap(interface, k):
    """Press and let go of ``k``, as a real key press does; returns whether the press was used."""
    is_used = interface.handle_event(key(k))
    interface.handle_event(pygame.event.Event(pygame.KEYUP, key=k, mod=0, unicode="", scancode=0))
    return is_used


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1, clicks=1)


def release(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)


def motion(pos):
    return pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))


def wheel(y):
    return pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=y, precise_x=0.0, precise_y=float(y), flipped=False)


def typed(text):
    return pygame.event.Event(pygame.TEXTINPUT, text=text)


def press_and_release(interface, pos, release_pos=None):
    interface.handle_event(click(pos))
    interface.render()
    interface.handle_event(release(pos if release_pos is None else release_pos))
    interface.render()


def rect_of(interface, element):
    return next(rect for hit, rect in interface.renderer._menu_tree.hit_rects if hit is element)


def center_of(interface, element):
    """Window position of ``element`` in the last rendered layout."""
    for hit, rect in interface.renderer._menu_tree.hit_rects:
        if hit is element:
            return rect.center
    raise LookupError(f"Invalid {element=}")


@pytest.fixture
def interface():
    return Interface(size=SIZE, use_hand_cursor=False)


def test_261111232812_eff5b499(interface):
    # No menu means no surface and no events used.
    assert interface.render() is None
    assert tap(interface, pygame.K_RETURN) is False
    assert interface.handle_event(click((10, 10))) is False


def test_261111232812_686248a9(interface):
    # Render returns window sized transparent surface.
    interface.push_stack(Overlay())

    surf = interface.render()

    assert surf.get_size() == SIZE
    assert surf.get_flags() & pygame.SRCALPHA
    assert surf.get_at((SIZE[0] // 2, SIZE[1] - 1)).a == 0xC0  # Overlay's translucent background.


def test_261111232812_dccd16f7(interface):
    # Render reuses surface until something changes.
    menu = Title()
    interface.push_stack(menu)

    first = interface.render()
    assert interface.render() is first

    menu.move_selected_down()
    assert interface.render() is not first


def test_261111232812_b042245f(interface):
    # Return key presses selected button.
    pressed = []
    interface.push_stack(Title(on_start=lambda: pressed.append("start")))
    interface.render()

    assert tap(interface, pygame.K_RETURN) is True
    assert pressed == ["start"]


def test_261111232812_e46db7f3(interface):
    # Escape closes overlay but leaves root to the game.
    interface.push_stack(Title())
    interface.push_stack(Overlay())
    interface.render()

    assert tap(interface, pygame.K_ESCAPE) is True
    assert isinstance(interface.top_stack(), Title)
    assert tap(interface, pygame.K_ESCAPE) is False
    assert isinstance(interface.top_stack(), Title)


def test_261111232812_0628aa04(interface):
    # Pop can close the last menu.
    interface.push_stack(Overlay())

    assert isinstance(interface.pop_stack(), Overlay)
    assert interface.render() is None


def test_261111232812_b3cf9345(interface):
    # Push unknown type raises.
    with pytest.raises(KeyError):
        interface.push_stack(Overlay)


def test_261113211043_9a5e1f96(interface):
    # Clicking a button presses it on release.
    pressed = []
    menu = Title(on_quit=lambda: pressed.append("quit"))
    interface.push_stack(menu)
    interface.render()
    quit_button = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "QUIT")
    position = center_of(interface, quit_button)

    assert interface.handle_event(click(position)) is True
    assert pressed == []  # Nothing happens until the button is let go.
    assert interface.handle_event(release(position)) is True
    assert pressed == ["quit"]


def test_261113211043_38722331(interface):
    # Releasing off the button cancels the press.
    pressed = []
    menu = Title(on_quit=lambda: pressed.append("quit"))
    interface.push_stack(menu)
    interface.render()
    quit_button = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "QUIT")

    press_and_release(interface, center_of(interface, quit_button), release_pos=(SIZE[0] - 2, SIZE[1] - 2))

    assert pressed == []
    assert menu._pressed is None


def test_261113211043_1d8e23bb(interface):
    # Left and right adjust at once and return leaves a slider alone.
    received = []
    slider = Slider(step=0.25, action=lambda value: received.append(value) or True)
    interface.push_stack(Menu(root_elements=[slider]))
    interface.render()

    for k in (pygame.K_RIGHT, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RETURN):
        assert tap(interface, k) is True

    assert received == [0.25, 0.5, 0.25]


def test_261113211043_7ed082ff(interface):
    # Left and right set a toggle and step a selector.
    toggle = Toggle()
    selector = Selector(selections=("A", "B", "C"))
    interface.push_stack(Menu(root_elements=[toggle, selector]))
    interface.render()

    tap(interface, pygame.K_RIGHT)
    tap(interface, pygame.K_RIGHT)  # Already true, so nothing changes.
    tap(interface, pygame.K_DOWN)
    tap(interface, pygame.K_RIGHT)
    tap(interface, pygame.K_RETURN)
    tap(interface, pygame.K_RETURN)  # Return steps forward and wraps.

    assert toggle.value is True
    assert selector.value == 0


def test_261113211043_158778b0(interface):
    # Up down and tab stop at the ends.
    menu = Title()
    interface.push_stack(menu)
    interface.render()

    tap(interface, pygame.K_UP)
    assert selected_label(menu) == "START"
    for _ in range(5):
        tap(interface, pygame.K_DOWN)
    assert selected_label(menu) == "QUIT"
    tap(interface, pygame.K_TAB)
    assert selected_label(menu) == "QUIT"


def test_261113211043_12dacc62(interface):
    # Left and right move between buttons in a row.
    left, right = Button(label=Button.ButtonText(text="NO")), Button(label=Button.ButtonText(text="YES"))
    below = Button(label=Button.ButtonText(text="BACK"))
    menu = Menu(root_elements=[HorizontalDivision(elements=[left, right], gap=(6.0, 0.0)), below])
    interface.push_stack(menu)
    interface.render()

    tap(interface, pygame.K_RIGHT)
    assert menu.get_selected_element() is right
    tap(interface, pygame.K_RIGHT)  # Nothing further right, and sideways moves do not wrap.
    assert menu.get_selected_element() is right
    tap(interface, pygame.K_DOWN)
    assert menu.get_selected_element() is below


def test_261113211043_3204740c():
    # Moving focus scrolls it into view.
    interface = Interface(size=(400, 120), use_hand_cursor=False)
    buttons: list[Element] = [Button(label=Button.ButtonText(text=f"B{idx}")) for idx in range(10)]
    menu = Menu(root_elements=buttons)
    interface.push_stack(menu)
    interface.render()

    for _ in range(len(buttons)):
        tap(interface, pygame.K_DOWN)  # Down to the last button, far below the window.
        interface.render()

    rect = rect_of(interface, buttons[-1])
    assert menu._scroll <= rect.top and rect.bottom <= menu._scroll + 120


def test_261113211043_5854488a(interface):
    # Pointer lights what it is over and nothing over empty space.
    menu = Title()
    interface.push_stack(menu)
    interface.render()
    options = menu._selectable_elements[1]

    assert interface.handle_event(motion(center_of(interface, options))) is True
    assert menu.get_lit_id() == options.id

    assert interface.handle_event(motion((SIZE[0] - 2, SIZE[1] - 2))) is False
    assert menu.get_lit_id() is None


def test_261113211043_6a246bef(interface):
    # Moving the pointer keeps the keys place.
    menu = Title()
    interface.push_stack(menu)
    interface.render()
    start, options, quit_button = menu._selectable_elements[0], menu._selectable_elements[1], menu._selectable_elements[-1]
    tap(interface, pygame.K_DOWN)  # The keys are on OPTIONS.

    interface.handle_event(motion(center_of(interface, quit_button)))
    assert menu.get_lit_id() == quit_button.id
    assert menu.get_selected_element() is options

    tap(interface, pygame.K_UP)  # The first press only shows the keys are still on OPTIONS.
    assert menu.get_selected_element() is options and menu.get_lit_id() == options.id
    tap(interface, pygame.K_UP)  # Then carries on from there, not from where the pointer was.
    assert menu.get_selected_element() is start


def test_261113211043_a13a73c8(interface):
    # Clicking a control moves the keys there.
    menu = Title()
    interface.push_stack(menu)
    interface.render()
    quit_button = menu._selectable_elements[-1]

    press_and_release(interface, center_of(interface, quit_button))

    assert menu.get_selected_element() is quit_button


def test_261113211043_6e3e4cb0(interface):
    # A bumped pointer does not take over from the keys.
    menu = Title()
    interface.push_stack(menu)
    interface.render()
    options = menu._selectable_elements[1]
    tap(interface, pygame.K_DOWN)
    tap(interface, pygame.K_DOWN)
    target = center_of(interface, options)
    menu._key_anchor_pos = target  # As if the pointer sat over OPTIONS when the key was pressed.

    interface.handle_event(motion((target[0] + 3, target[1])))
    assert menu.get_lit_id() != options.id
    interface.handle_event(motion((target[0] + 20, target[1])))
    assert menu.get_lit_id() == options.id


def test_261113211043_f0ebb332(interface):
    # First key after using the pointer only shows the keys place.
    pressed = []
    menu = Title(on_start=lambda: pressed.append("start"))
    interface.push_stack(menu)
    interface.render()
    interface.handle_event(motion(center_of(interface, menu._selectable_elements[1])))
    interface.handle_event(motion((SIZE[0] - 2, SIZE[1] - 2)))

    tap(interface, pygame.K_RETURN)
    assert pressed == [] and menu.get_lit_id() == menu._selectable_elements[0].id
    tap(interface, pygame.K_RETURN)
    assert pressed == ["start"]


def test_261113211043_aff243de(interface, monkeypatch):
    # Held arrow repeats after a delay until let go.
    clock = [100.0]
    monkeypatch.setattr("facade.interface.time.monotonic", lambda: clock[0])
    slider = Slider(value=0.0, step=0.1)
    interface.push_stack(Menu(root_elements=[slider]))
    interface.render()

    interface.handle_event(key(pygame.K_RIGHT))
    clock[0] += interface.repeat_delay / 2
    interface.render()
    assert slider.value == 0.1  # Not yet repeating.
    for _ in range(3):
        clock[0] += interface.repeat_delay
        interface.render()
    assert slider.value == 0.4
    interface.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT, mod=0))
    clock[0] += 1.0
    interface.render()
    assert slider.value == 0.4


def test_261113211043_d52b7d66(interface, monkeypatch):
    # Held character and backspace repeat while typing.
    clock = [100.0]
    monkeypatch.setattr("facade.interface.time.monotonic", lambda: clock[0])
    field = InputField(value=InputField.InputValueText(text="AB"))
    interface.push_stack(Menu(root_elements=[field]))
    interface.render()
    tap(interface, pygame.K_RETURN)

    interface.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x, mod=0, unicode="x", scancode=0))
    interface.handle_event(typed("x"))
    interface.handle_event(typed("x"))  # The system's own repeat is ignored; the interface times repeats.
    clock[0] += interface.repeat_delay
    interface.render()
    assert field.get_field() == "ABXX"
    interface.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_x, mod=0))

    interface.handle_event(key(pygame.K_BACKSPACE))
    for _ in range(2):
        clock[0] += interface.repeat_delay
        interface.render()
    assert field.get_field() == "A"


def test_261113211043_4cd10c53(interface):
    # Clicking anywhere on a toggle flips it.
    toggle = Toggle()
    interface.push_stack(Menu(root_elements=[toggle]))
    interface.render()
    rect = rect_of(interface, toggle)

    press_and_release(interface, (rect.left + 10, rect.centery))  # On the half that is already filled.
    assert toggle.value is True
    press_and_release(interface, (rect.right - 10, rect.centery))
    assert toggle.value is False


def test_261113211043_62b9b659(interface):
    # Clicking a slider side steps it and the number does nothing.
    slider = Slider(value=0.5)
    interface.push_stack(Menu(root_elements=[slider]))
    interface.render()
    rect = rect_of(interface, slider)

    press_and_release(interface, (rect.left + 10, rect.centery))
    assert slider.value == 0.4
    press_and_release(interface, (rect.right - 10, rect.centery))  # The number box.
    assert slider.value == 0.4


def test_261113211043_9b0b1dd0(interface):
    # The wheel scrolls and never changes a value.
    slider = Slider(value=0.5)
    interface.push_stack(Menu(root_elements=[slider]))
    interface.render()
    interface.handle_event(motion(center_of(interface, slider)))

    interface.handle_event(wheel(1))

    assert slider.value == 0.5


def test_261113211043_12ad64ea(interface):
    # Clicking a field starts typing at the end and down saves it.
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    below = Button(label=Button.ButtonText(text="OK"))
    menu = Menu(root_elements=[field, below])
    interface.push_stack(menu)
    interface.render()

    press_and_release(interface, center_of(interface, field))
    assert field.is_open
    interface.handle_event(typed("x"))
    tap(interface, pygame.K_DOWN)

    assert field.value.text == "PLAYERX" and not field.is_open
    assert menu.get_selected_element() is below


def test_261113211043_b0b40056(interface):
    # Clicking elsewhere while typing cancels invalid text.
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    interface.push_stack(Menu(root_elements=[field]))
    interface.render()
    tap(interface, pygame.K_RETURN)
    interface.handle_event(typed("!"))

    interface.handle_event(click((SIZE[0] - 2, SIZE[1] - 2)))

    assert not field.is_open and field.value.text == "PLAYER"


def test_261113211043_01f16e3f():
    # A key scrolls back to the keys place before moving.
    interface = Interface(size=(400, 120), use_hand_cursor=False)
    buttons: list[Element] = [Button(label=Button.ButtonText(text=f"B{idx}")) for idx in range(10)]
    menu = Menu(root_elements=buttons)
    interface.push_stack(menu)
    interface.render()
    menu._scroll = 200.0  # Scrolled down with the wheel, past the first button.
    interface.render()

    tap(interface, pygame.K_DOWN)
    interface.render()

    rect = rect_of(interface, buttons[0])
    assert menu.get_selected_element() is buttons[0]  # Found, not moved.
    assert menu._scroll <= rect.top and rect.bottom <= menu._scroll + 120


def test_261113212818_49ba69cd(interface):
    # Return key presses a primary button.
    pressed = []
    interface.push_stack(Menu(root_elements=[PrimaryButton(action=lambda: pressed.append("start"))]))
    interface.render()

    assert interface.handle_event(key(pygame.K_RETURN)) is True
    assert pressed == ["start"]


def test_261113213323_d6e7d786(interface):
    # Clicking a selector side steps it and the counter does nothing.
    selector = Selector(selections=("A", "B", "C"), value=1)
    interface.push_stack(Menu(root_elements=[selector]))
    interface.render()
    rect = rect_of(interface, selector)

    press_and_release(interface, (rect.right - 10, rect.centery))  # The counter box.
    assert selector.value == 1
    press_and_release(interface, (rect.left + 10, rect.centery))
    assert selector.value == 0


def test_261113213323_4ad884aa(interface):
    # Finishing typing with enter unlights the field until the pointer moves.
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    menu = Menu(root_elements=[field])
    interface.push_stack(menu)
    interface.render()
    position = center_of(interface, field)

    interface.handle_event(motion(position))
    press_and_release(interface, position)
    interface.handle_event(typed("x"))
    tap(interface, pygame.K_RETURN)

    assert not field.is_open and menu.get_lit_id() is None
    interface.handle_event(motion((position[0] + 1, position[1])))
    assert menu.get_lit_id() == field.id


def test_261113213323_075062ae(interface):
    # Finishing typing opened by the keys also unlights the field.
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    below = Button(label=Button.ButtonText(text="OK"))
    menu = Menu(root_elements=[field, below])
    interface.push_stack(menu)
    interface.render()

    tap(interface, pygame.K_RETURN)
    interface.handle_event(typed("x"))
    tap(interface, pygame.K_RETURN)
    assert not field.is_open and menu.get_lit_id() is None

    tap(interface, pygame.K_DOWN)  # The first press only shows the keys are still on the field.
    assert menu.get_lit_id() == field.id
    tap(interface, pygame.K_DOWN)
    assert menu.get_selected_element() is below
