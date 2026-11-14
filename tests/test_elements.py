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


def test_slider_saves_every_step_and_stops_at_its_ends():
    received = []
    slider = Slider(range=(0.0, 0.5), step=0.25, action=lambda value: received.append(value) or True)

    slider.increment()
    slider.increment()
    is_moved = slider.increment()  # Already at the maximum
    slider.decrement()

    assert received == [0.25, 0.5, 0.25]
    assert not is_moved
    assert slider.value == 0.25 and slider.is_edited


def test_slider_at_an_end_does_not_call_action():
    received = []
    slider = Slider(value=0.0, action=lambda value: received.append(value) or True)

    slider.decrement()

    assert received == []
    assert not slider.is_edited


def test_toggle_set_value_only_acts_on_a_change():
    received = []
    toggle = Toggle(action=lambda value: received.append(value) or True)

    toggle.set_value(False)
    toggle.set_value(True)
    toggle.set_value(True)

    assert received == [True]


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


def test_selector_saves_every_step_and_wraps_only_when_asked():
    received = []
    selector = Selector(selections=("A", "B", "C"), action=lambda index: received.append(index) or True)

    selector.next()
    selector.next()
    selector.next()  # Stops at the last option
    selector.next(is_wrapping=True)

    assert received == [1, 2, 0]
    assert selector.get_selection() == "A"


def test_input_field_close_reports_invalid_text_and_stays_open():
    field = InputField(value=InputField.InputValueText(text="OK"))

    field.open()
    field.append("!")

    assert field.close() is False
    assert field.is_open


def test_element_repr_is_short():
    assert repr(Button(id="play")) == "Button(id='play')"
