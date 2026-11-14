"""
test_elements.py
"""

import time

from facade import Button, InputField, ProgressBar, Selector, Slider, Toggle


def test_261111232812_f5760838():
    # Button calls action without arguments.
    calls = []
    button = Button(action=lambda: calls.append("pressed"))

    button()

    assert calls == ["pressed"]
    assert button.is_called


def test_261111232812_e1bf7864():
    # Toggle flips value and passes it.
    received = []
    toggle = Toggle(action=lambda value: received.append(value) or True)

    toggle()
    toggle()

    assert received == [True, False]


def test_261111232812_2bcc496a():
    # Input field commits text once.
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


def test_261111232812_cd135070():
    # Input field rejects invalid text and stays open.
    received = []
    field = InputField(action=lambda value: received.append(value) or True)

    field.open()
    field.append("a b")  # The default validator only accepts letters and digits.
    field.close()

    assert received == []
    assert field.is_open


def test_261111232812_0e17961a():
    # Input field cancel discards edit.
    field = InputField(value=InputField.InputValueText(text="OLD"))

    field.open()
    field.append("X")
    field.cancel()

    assert field.value.text == "OLD"
    assert field.get_field() == "OLD"


def test_261111232812_04f94fe4():
    # Input field does not call action when unchanged.
    received = []
    field = InputField(value=InputField.InputValueText(text="SAME"), action=lambda value: received.append(value) or True)

    field.open()
    field.close()

    assert received == []


def test_261111232812_4e62e685(monkeypatch):
    # Input field cursor blinks on a clock.
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    field = InputField()

    assert field.get_cursor_glyph() == ""  # Closed.
    field.open()
    shown = field.get_cursor_glyph()
    now[0] += InputField._cursor_period
    hidden = field.get_cursor_glyph()

    assert (shown, hidden) == ("_", "")


def test_261111232812_eca4639a():
    # Element repr is short.
    assert repr(Button(id="play")) == "Button(id='play')"


def test_261113152542_8bc68536():
    # Progress bar fraction is clamped to its range.
    assert ProgressBar(value=15.0, range=(10.0, 20.0)).get_fraction() == 0.5
    assert ProgressBar(value=-1.0).get_fraction() == 0.0
    assert ProgressBar(value=2.0).get_fraction() == 1.0
    assert ProgressBar(value=1.0, range=(1.0, 1.0)).get_fraction() == 0.0


def test_261113211043_44a4210b():
    # Slider saves every step and stops at its ends.
    received = []
    slider = Slider(range=(0.0, 0.5), step=0.25, action=lambda value: received.append(value) or True)

    slider.increment()
    slider.increment()
    is_moved = slider.increment()  # Already at the maximum.
    slider.decrement()

    assert received == [0.25, 0.5, 0.25]
    assert not is_moved
    assert slider.value == 0.25 and slider.is_edited


def test_261113211043_9a4f5cf7():
    # Slider at an end does not call action.
    received = []
    slider = Slider(value=0.0, action=lambda value: received.append(value) or True)

    slider.decrement()

    assert received == []
    assert not slider.is_edited


def test_261113211043_b1e6e0e5():
    # Toggle set value only acts on a change.
    received = []
    toggle = Toggle(action=lambda value: received.append(value) or True)

    toggle.set_value(False)
    toggle.set_value(True)
    toggle.set_value(True)

    assert received == [True]


def test_261113211043_d782f4f2():
    # Selector saves every step and wraps only when asked.
    received = []
    selector = Selector(selections=("A", "B", "C"), action=lambda index: received.append(index) or True)

    selector.next()
    selector.next()
    selector.next()  # Stops at the last option.
    selector.next(is_wrapping=True)

    assert received == [1, 2, 0]
    assert selector.get_selection() == "A"


def test_261113211043_4f9e7339():
    # Input field close reports invalid text and stays open.
    field = InputField(value=InputField.InputValueText(text="OK"))

    field.open()
    field.append("!")

    assert field.close() is False
    assert field.is_open
