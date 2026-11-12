# Facade

Menus for pygame-ce games. Your game keeps its window and loop; Facade takes your events and returns one window-sized surface to draw over your frame.

![Facade screenshot](image.png "An example interface")

## Setup

You need Python 3.14 or newer. Check with `python3.14 --version`; if it is missing, install it from [python.org](https://www.python.org/downloads/) or with `uv python install 3.14`.

```bash
git clone https://github.com/hcoderdm/pygame-facade.git
cd pygame-facade
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
python examples/demo.py
pytest
```

```bash
pip install -e /path/to/pygame-facade
```

The `-e` (editable) install means changes you make to Facade apply to your game without reinstalling.

## Example

```python
from facade import Interface, Pause, Start

ui = Interface(size=screen.get_size())
ui.add_menu(Pause(on_resume=ui.pop))
ui.push(Start(on_start=ui.clear, on_quit=quit_game))

# In your game loop
for event in pygame.event.get():
    if ui.handle_event(event):
        continue  # The menu used this event
    ...  # Your game's own input

draw_game(screen)
if (gui := ui.render()) is not None:
    screen.blit(gui, (0, 0))
```

`render()` returns `None` while no menu is open. [examples/demo.py](examples/demo.py) is a complete example, and [DESIGN.md](DESIGN.md) explains how Facade works.

## License

Facade is released under the [MIT License](LICENSE). The demo's Edit Undo font is freeware by Brian Kent; see [its license](examples/assets/fonts/editundo.txt).
