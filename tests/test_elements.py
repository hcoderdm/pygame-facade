"""
Element behaviour that needs no rendering.
"""

import time

from facade import Button, InputField, ProgressBar, Selector, Slider, Toggle


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


def test_slider_commits_stepped_value_once():
    received = []
    slider = Slider(range=(0.0, 0.5), step=0.25, action=lambda value: received.append(value) or True)

    slider.open()
    slider.increment()
    slider.increment()
    slider.increment()  # Clamped at the maximum
    slider.decrement()
    slider.close()

    assert received == [0.25]
    assert slider.value == 0.25
    assert slider.is_edited and not slider.is_open


def test_slider_steps_only_while_open():
    slider = Slider(step=0.5)

    slider.increment()

    assert slider.get_buffer_value() == 0.0


def test_slider_cancel_discards_steps():
    received = []
    slider = Slider(value=0.5, action=lambda value: received.append(value) or True)

    slider.open()
    slider.decrement()
    slider.cancel()

    assert received == []
    assert slider.get_buffer_value() == 0.5
    assert not slider.is_altered()


def test_slider_does_not_call_action_when_unchanged():
    received = []
    slider = Slider(action=lambda value: received.append(value) or True)

    slider.open()
    slider.increment()
    slider.decrement()
    slider.close()

    assert received == []
    assert not slider.is_edited


def test_progress_bar_fraction_is_clamped_to_its_range():
    assert ProgressBar(value=15.0, range=(10.0, 20.0)).get_fraction() == 0.5
    assert ProgressBar(value=-1.0).get_fraction() == 0.0
    assert ProgressBar(value=2.0).get_fraction() == 1.0
    assert ProgressBar(value=1.0, range=(1.0, 1.0)).get_fraction() == 0.0


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

    assert field.get_cursor_glyph() == ""  # Closed
    field.open()
    shown = field.get_cursor_glyph()
    now[0] += InputField._cursor_period
    hidden = field.get_cursor_glyph()

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
