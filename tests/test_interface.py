"""
Interface: events in, GUI surface out.
"""

import pygame
import pytest

from facade import Button, HorizontalDivision, InputField, Interface, Menu, PrimaryButton, Selector, Slider, Toggle
from sample_menus import Overlay, Title

SIZE = (800, 600)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def tap(ui, k):
    """Press and let go of ``k``, as a real key press does; returns whether the press was used."""
    is_used = ui.handle_event(key(k))
    ui.handle_event(pygame.event.Event(pygame.KEYUP, key=k, mod=0, unicode="", scancode=0))
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


def press_and_release(ui, pos, release_pos=None):
    ui.handle_event(click(pos))
    ui.render()
    ui.handle_event(release(pos if release_pos is None else release_pos))
    ui.render()


def rect_of(ui, element):
    return next(rect for hit, rect in ui.renderer._menu_tree.hit_rects if hit is element)


def center_of(ui, element):
    """Window position of ``element`` in the last rendered layout."""
    for hit, rect in ui.renderer._menu_tree.hit_rects:
        if hit is element:
            return rect.center
    raise LookupError(element)


@pytest.fixture
def ui():
    return Interface(size=SIZE, use_hand_cursor=False)


def test_no_menu_means_no_surface_and_no_events_used(ui):
    assert ui.render() is None
    assert tap(ui, pygame.K_RETURN) is False
    assert ui.handle_event(click((10, 10))) is False


def test_render_returns_window_sized_transparent_surface(ui):
    ui.push(Overlay())

    surface = ui.render()

    assert surface.get_size() == SIZE
    assert surface.get_flags() & pygame.SRCALPHA
    assert surface.get_at((SIZE[0] // 2, SIZE[1] - 1)).a == 0xC0  # Overlay's translucent background


def test_render_reuses_surface_until_something_changes(ui):
    menu = Title()
    ui.push(menu)

    first = ui.render()
    assert ui.render() is first

    menu.move_selected_down()
    assert ui.render() is not first


def test_return_key_presses_selected_button(ui):
    pressed = []
    ui.push(Title(on_start=lambda: pressed.append("start")))
    ui.render()

    assert tap(ui, pygame.K_RETURN) is True
    assert pressed == ["start"]


def test_clicking_a_button_presses_it_on_release(ui):
    pressed = []
    menu = Title(on_quit=lambda: pressed.append("quit"))
    ui.push(menu)
    ui.render()
    quit_button = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "QUIT")
    position = center_of(ui, quit_button)

    assert ui.handle_event(click(position)) is True
    assert pressed == []  # Nothing happens until the button is let go
    assert ui.handle_event(release(position)) is True
    assert pressed == ["quit"]


def test_releasing_off_the_button_cancels_the_press(ui):
    pressed = []
    menu = Title(on_quit=lambda: pressed.append("quit"))
    ui.push(menu)
    ui.render()
    quit_button = next(e for e in menu._selectable_elements if isinstance(e, Button) and e.label.text == "QUIT")

    press_and_release(ui, center_of(ui, quit_button), release_pos=(SIZE[0] - 2, SIZE[1] - 2))

    assert pressed == []
    assert menu._pressed is None


def test_escape_closes_overlay_but_leaves_root_to_the_game(ui):
    ui.push(Title())
    ui.push(Overlay())
    ui.render()

    assert tap(ui, pygame.K_ESCAPE) is True
    assert isinstance(ui.top(), Title)
    assert tap(ui, pygame.K_ESCAPE) is False
    assert isinstance(ui.top(), Title)


def test_pop_can_close_the_last_menu(ui):
    ui.push(Overlay())

    assert isinstance(ui.pop(), Overlay)
    assert ui.render() is None


def test_push_unknown_type_raises(ui):
    with pytest.raises(KeyError):
        ui.push(Overlay)


def test_left_and_right_adjust_at_once_and_return_leaves_a_slider_alone(ui):
    received = []
    slider = Slider(step=0.25, action=lambda value: received.append(value) or True)
    ui.push(Menu(root_elements=[slider]))
    ui.render()

    for k in (pygame.K_RIGHT, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RETURN):
        assert tap(ui, k) is True

    assert received == [0.25, 0.5, 0.25]


def test_left_and_right_set_a_toggle_and_step_a_selector(ui):
    toggle = Toggle()
    selector = Selector(selections=("A", "B", "C"))
    ui.push(Menu(root_elements=[toggle, selector]))
    ui.render()

    tap(ui, pygame.K_RIGHT)
    tap(ui, pygame.K_RIGHT)  # Already true, so nothing changes
    tap(ui, pygame.K_DOWN)
    tap(ui, pygame.K_RIGHT)
    tap(ui, pygame.K_RETURN)
    tap(ui, pygame.K_RETURN)  # Return steps forward and wraps

    assert toggle.value is True
    assert selector.value == 0


def test_up_down_and_tab_stop_at_the_ends(ui):
    menu = Title()
    ui.push(menu)
    ui.render()

    tap(ui, pygame.K_UP)
    assert menu.get_selected_element().label.text == "START"
    for _ in range(5):
        tap(ui, pygame.K_DOWN)
    assert menu.get_selected_element().label.text == "QUIT"
    tap(ui, pygame.K_TAB)
    assert menu.get_selected_element().label.text == "QUIT"


def test_left_and_right_move_between_buttons_in_a_row(ui):
    left, right = Button(label=Button.ButtonText(text="NO")), Button(label=Button.ButtonText(text="YES"))
    below = Button(label=Button.ButtonText(text="BACK"))
    menu = Menu(root_elements=[HorizontalDivision(elements=[left, right], gap=(6.0, 0.0)), below])
    ui.push(menu)
    ui.render()

    tap(ui, pygame.K_RIGHT)
    assert menu.get_selected_element() is right
    tap(ui, pygame.K_RIGHT)  # Nothing further right, and sideways moves do not wrap
    assert menu.get_selected_element() is right
    tap(ui, pygame.K_DOWN)
    assert menu.get_selected_element() is below


def test_moving_focus_scrolls_it_into_view():
    ui = Interface(size=(400, 120), use_hand_cursor=False)
    buttons = [Button(label=Button.ButtonText(text=f"B{idx}")) for idx in range(10)]
    menu = Menu(root_elements=buttons)
    ui.push(menu)
    ui.render()

    for _ in range(len(buttons)):
        tap(ui, pygame.K_DOWN)  # Down to the last button, far below the window
        ui.render()

    rect = rect_of(ui, buttons[-1])
    assert menu._scroll <= rect.top and rect.bottom <= menu._scroll + 120


def test_pointer_lights_what_it_is_over_and_nothing_over_empty_space(ui):
    menu = Title()
    ui.push(menu)
    ui.render()
    options = menu._selectable_elements[1]

    assert ui.handle_event(motion(center_of(ui, options))) is True
    assert menu.get_lit_id() == options.id

    assert ui.handle_event(motion((SIZE[0] - 2, SIZE[1] - 2))) is False
    assert menu.get_lit_id() is None


def test_moving_the_pointer_keeps_the_keys_place(ui):
    menu = Title()
    ui.push(menu)
    ui.render()
    start, options, quit_button = menu._selectable_elements[0], menu._selectable_elements[1], menu._selectable_elements[-1]
    tap(ui, pygame.K_DOWN)  # The keys are on OPTIONS

    ui.handle_event(motion(center_of(ui, quit_button)))
    assert menu.get_lit_id() == quit_button.id
    assert menu.get_selected_element() is options

    tap(ui, pygame.K_UP)  # The first press only shows the keys are still on OPTIONS
    assert menu.get_selected_element() is options and menu.get_lit_id() == options.id
    tap(ui, pygame.K_UP)  # Then carries on from there, not from where the pointer was
    assert menu.get_selected_element() is start


def test_clicking_a_control_moves_the_keys_there(ui):
    menu = Title()
    ui.push(menu)
    ui.render()
    quit_button = menu._selectable_elements[-1]

    press_and_release(ui, center_of(ui, quit_button))

    assert menu.get_selected_element() is quit_button


def test_a_bumped_pointer_does_not_take_over_from_the_keys(ui):
    menu = Title()
    ui.push(menu)
    ui.render()
    options = menu._selectable_elements[1]
    tap(ui, pygame.K_DOWN)
    tap(ui, pygame.K_DOWN)
    target = center_of(ui, options)
    menu._key_anchor_pos = target  # As if the pointer sat over OPTIONS when the key was pressed

    ui.handle_event(motion((target[0] + 3, target[1])))
    assert menu.get_lit_id() != options.id
    ui.handle_event(motion((target[0] + 20, target[1])))
    assert menu.get_lit_id() == options.id


def test_first_key_after_using_the_pointer_only_shows_the_keys_place(ui):
    pressed = []
    menu = Title(on_start=lambda: pressed.append("start"))
    ui.push(menu)
    ui.render()
    ui.handle_event(motion(center_of(ui, menu._selectable_elements[1])))
    ui.handle_event(motion((SIZE[0] - 2, SIZE[1] - 2)))

    tap(ui, pygame.K_RETURN)
    assert pressed == [] and menu.get_lit_id() == menu._selectable_elements[0].id
    tap(ui, pygame.K_RETURN)
    assert pressed == ["start"]


def test_held_arrow_repeats_after_a_delay_until_let_go(ui, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("facade.interface.time.monotonic", lambda: clock[0])
    slider = Slider(value=0.0, step=0.1)
    ui.push(Menu(root_elements=[slider]))
    ui.render()

    ui.handle_event(key(pygame.K_RIGHT))
    clock[0] += ui.repeat_delay / 2
    ui.render()
    assert slider.value == 0.1  # Not yet repeating
    for _ in range(3):
        clock[0] += ui.repeat_delay
        ui.render()
    assert slider.value == 0.4
    ui.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT, mod=0))
    clock[0] += 1.0
    ui.render()
    assert slider.value == 0.4


def test_held_character_and_backspace_repeat_while_typing(ui, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("facade.interface.time.monotonic", lambda: clock[0])
    field = InputField(value=InputField.InputValueText(text="AB"))
    ui.push(Menu(root_elements=[field]))
    ui.render()
    tap(ui, pygame.K_RETURN)

    ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x, mod=0, unicode="x", scancode=0))
    ui.handle_event(typed("x"))
    ui.handle_event(typed("x"))  # The system's own repeat is ignored; the interface times repeats
    clock[0] += ui.repeat_delay
    ui.render()
    assert field.get_field() == "ABXX"
    ui.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_x, mod=0))

    ui.handle_event(key(pygame.K_BACKSPACE))
    for _ in range(2):
        clock[0] += ui.repeat_delay
        ui.render()
    assert field.get_field() == "A"


def test_clicking_anywhere_on_a_toggle_flips_it(ui):
    toggle = Toggle()
    ui.push(Menu(root_elements=[toggle]))
    ui.render()
    rect = rect_of(ui, toggle)

    press_and_release(ui, (rect.left + 10, rect.centery))  # On the half that is already filled
    assert toggle.value is True
    press_and_release(ui, (rect.right - 10, rect.centery))
    assert toggle.value is False


def test_clicking_a_slider_side_steps_it_and_the_number_does_nothing(ui):
    slider = Slider(value=0.5)
    ui.push(Menu(root_elements=[slider]))
    ui.render()
    rect = rect_of(ui, slider)

    press_and_release(ui, (rect.left + 10, rect.centery))
    assert slider.value == 0.4
    press_and_release(ui, (rect.right - 10, rect.centery))  # The number box
    assert slider.value == 0.4


def test_the_wheel_scrolls_and_never_changes_a_value(ui):
    slider = Slider(value=0.5)
    ui.push(Menu(root_elements=[slider]))
    ui.render()
    ui.handle_event(motion(center_of(ui, slider)))

    ui.handle_event(wheel(1))

    assert slider.value == 0.5


def test_clicking_a_field_starts_typing_at_the_end_and_down_saves_it(ui):
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    below = Button(label=Button.ButtonText(text="OK"))
    menu = Menu(root_elements=[field, below])
    ui.push(menu)
    ui.render()

    press_and_release(ui, center_of(ui, field))
    assert field.is_open
    ui.handle_event(typed("x"))
    tap(ui, pygame.K_DOWN)

    assert field.value.text == "PLAYERX" and not field.is_open
    assert menu.get_selected_element() is below


def test_clicking_elsewhere_while_typing_cancels_invalid_text(ui):
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    ui.push(Menu(root_elements=[field]))
    ui.render()
    tap(ui, pygame.K_RETURN)
    ui.handle_event(typed("!"))

    ui.handle_event(click((SIZE[0] - 2, SIZE[1] - 2)))

    assert not field.is_open and field.value.text == "PLAYER"


def test_a_key_scrolls_back_to_the_keys_place_before_moving():
    ui = Interface(size=(400, 120), use_hand_cursor=False)
    buttons = [Button(label=Button.ButtonText(text=f"B{idx}")) for idx in range(10)]
    menu = Menu(root_elements=buttons)
    ui.push(menu)
    ui.render()
    menu._scroll = 200.0  # Scrolled down with the wheel, past the first button
    ui.render()

    tap(ui, pygame.K_DOWN)
    ui.render()

    rect = rect_of(ui, buttons[0])
    assert menu.get_selected_element() is buttons[0]  # Found, not moved
    assert menu._scroll <= rect.top and rect.bottom <= menu._scroll + 120


def test_clicking_a_selector_side_steps_it_and_the_counter_does_nothing(ui):
    selector = Selector(selections=("A", "B", "C"), value=1)
    ui.push(Menu(root_elements=[selector]))
    ui.render()
    rect = rect_of(ui, selector)

    press_and_release(ui, (rect.right - 10, rect.centery))  # The counter box
    assert selector.value == 1
    press_and_release(ui, (rect.left + 10, rect.centery))
    assert selector.value == 0


def test_finishing_typing_with_enter_unlights_the_field_until_the_pointer_moves(ui):
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    menu = Menu(root_elements=[field])
    ui.push(menu)
    ui.render()
    position = center_of(ui, field)

    ui.handle_event(motion(position))
    press_and_release(ui, position)
    ui.handle_event(typed("x"))
    tap(ui, pygame.K_RETURN)

    assert not field.is_open and menu.get_lit_id() is None
    ui.handle_event(motion((position[0] + 1, position[1])))
    assert menu.get_lit_id() == field.id


def test_finishing_typing_opened_by_the_keys_also_unlights_the_field(ui):
    field = InputField(value=InputField.InputValueText(text="PLAYER"))
    below = Button(label=Button.ButtonText(text="OK"))
    menu = Menu(root_elements=[field, below])
    ui.push(menu)
    ui.render()

    tap(ui, pygame.K_RETURN)
    ui.handle_event(typed("x"))
    tap(ui, pygame.K_RETURN)
    assert not field.is_open and menu.get_lit_id() is None

    tap(ui, pygame.K_DOWN)  # The first press only shows the keys are still on the field
    assert menu.get_lit_id() == field.id
    tap(ui, pygame.K_DOWN)
    assert menu.get_selected_element() is below


def test_return_key_presses_a_primary_button(ui):
    pressed = []
    ui.push(Menu(root_elements=[PrimaryButton(action=lambda: pressed.append("start"))]))
    ui.render()

    assert ui.handle_event(key(pygame.K_RETURN)) is True
    assert pressed == ["start"]

