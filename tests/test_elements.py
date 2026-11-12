"""
Element behaviour that needs no rendering.
"""

import time

from facade import Button, InputField, Selector, Slider, Toggle


def test_button_calls_action_without_arguments():
    calls = []
    button = Button(action=lambda: calls.append("pressed"))

    button()

    assert calls == ["pressed"]
    assert button.is_called


def test_toggle_flips_value_and_passes_it():
    received = []
    toggle = Toggle(action=lambda value: received.append(value) or True)

    toggle()
    toggle()

    assert received == [True, False]


def test_slider_steps_within_range_and_calls_action():
    received = []
    slider = Slider(range=(0.0, 0.5), step=0.25, action=lambda value: received.append(value) or True)

    slider.increment()
    slider.increment()
    slider.increment()  # Clamped at the maximum
    slider.decrement()

    assert received == [0.25, 0.5, 0.5, 0.25]


def test_input_field_commits_text_once():
    received = []
    field = InputField(action=lambda value: received.append(value) or True)

    field.open()
    field.append("ab")
    field.append("1")
    field.truncate()
    field.close()

    assert received == ["AB"]
    assert field.value.text == "AB"
    assert not field.is_open


def test_input_field_rejects_invalid_text_and_stays_open():
    received = []
    field = InputField(action=lambda value: received.append(value) or True)

    field.open()
    field.append("a b")  # The default validator only accepts letters and digits
    field.close()

    assert received == []
    assert field.is_open


def test_input_field_cancel_discards_edit():
    field = InputField(value=InputField.InputValueText(text="OLD"))

    field.open()
    field.append("X")
    field.cancel()

    assert field.value.text == "OLD"
    assert field.get_field() == "OLD"


def test_input_field_does_not_call_action_when_unchanged():
    received = []
    field = InputField(value=InputField.InputValueText(text="SAME"), action=lambda value: received.append(value) or True)

    field.open()
    field.close()

    assert received == []


def test_input_field_cursor_blinks_on_a_clock(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    field = InputField()

    assert field.get_cursor() == ""  # Closed
    field.open()
    shown = field.get_cursor()
    now[0] += InputField._cursor_period
    hidden = field.get_cursor()

    assert (shown, hidden) == ("_", "")


def test_selector_commits_new_index_once():
    received = []
    selector = Selector(selections=("A", "B", "C"), action=lambda index: received.append(index) or True)

    selector.open()
    selector.next()
    selector.next()
    selector.next()  # Clamped at the last option
    selector.close()

    assert received == [2]
    assert selector.selection() == "C"


def test_element_repr_is_short():
    assert repr(Button(id="play")) == "Button(id='play')"
