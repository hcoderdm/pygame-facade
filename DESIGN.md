# Design

This document explains how Facade is put together and why. For installing and using it, see the [README](README.md).

## Goal

Facade draws menus for a pygame-ce game without owning the game. The game keeps its window, event loop and frame timing. Each frame it hands Facade its events and gets back one window-sized, transparent surface to blit over whatever it drew. Nothing else crosses the boundary.

## Modules

| Module | Role |
|---|---|
| `interface.py` | `Interface`, the only object a game needs. Owns one `MenuManager` and one `MenuRenderer`. |
| `manager.py` | `MenuManager` (the menu stack) and the `manage_menu_*` functions that apply one pygame event to a menu. |
| `renderer.py` | `MenuRenderer`, which turns a menu's element tree into the GUI surface and answers hit-tests. |
| `menus.py` | `MenuType`, the base class for a screen, and the built-in `Start`, `Pause`, `Settings` and `About`. |
| `elements.py` | Element dataclasses (layout, text, images, interactive controls) and their attribute types. |
| `assets.py` | `FontManager` and `ImageManager`, the caches the renderer loads fonts and images through. |

Dependencies point one way: `interface` uses `manager` and `renderer`; both use `menus` and `elements`; `renderer` also uses `assets`. `elements` depends on nothing else in the package. `__init__.py` re-exports the public names so users only ever import `facade`.

## Data model: elements are plain data

Elements are keyword-only dataclasses that describe what to draw and hold interaction state (an input field's edit buffer, a selector's index). They never touch pygame; drawing belongs to the renderer. This keeps menus easy to declare, inspect and test without a window.

Every element shares layout and styling fields from `Element`: `size`, `margin`, `padding` and `offset` (each a pair, measured in pixels or relative to the parent through a matching `*_measure` field), `justify`, `alignment`, `overflow`, background, border and shadow colours, and flags such as `is_selectable` and `is_visible`. Colours are `"#RRGGBBAA"` strings.

Containers (`VerticalDivision`, `HorizontalDivision`) hold child elements. Interactive elements derive from `InteractiveElement`, which gives them a `value` and an `action` callback. `Button` overrides this to call its action with no arguments, since buttons have no value.

## Menus and the stack

A menu (`MenuType`) is a screen: a root `VerticalDivision` built from `root_elements`, plus the index of the selected element and a scroll offset. Built-in menus fill `root_elements` in `__post_init__` from their callback fields (`on_start`, `on_return` and so on).

The selection is an index into the menu's selectable elements, found by walking the tree in order. Up and down move through that flat list, which is why keyboard navigation works for any layout without per-menu code.

`MenuManager` registers at most one menu per type and keeps a stack of open menus. Only the top menu is drawn and receives input. `Interface.pop` may empty the stack, which is how the game returns to play; Escape only pops when there is a menu underneath, so it cannot close a root menu such as the title screen.

`Settings` is generated rather than written by hand: it walks the UPPERCASE attributes of whatever object it is given and builds a `Selector` for enums and booleans, or an `InputField` with a type-matched validator for ints, floats and strings. Committed edits are written straight back with `setattr`.

## Input

`Interface.handle_event` looks up a handler by event type and applies it to the top menu. Each handler returns whether it used the event, and that result is passed straight back to the game, so the game only handles input the GUI ignored. With no menu open every event returns `False`.

- Keyboard: Up and Down move the selection. Return presses a button, toggles a toggle, or opens and commits an input field or selector. Escape cancels an open field, otherwise pops the stack.
- Mouse: hovering selects the element under the cursor, clicking an already selected element activates it, and a double click activates immediately. The wheel steps the selected selector or slider, otherwise scrolls the menu.
- Text: `TEXTINPUT` events append to the open input field.

Mouse hit-testing uses the layout from the last render, shifted by the scroll offset. Because the GUI surface is the size of the window and is blitted at `(0, 0)`, window coordinates need no other translation.

## Rendering

`MenuRenderer.render(menu, size)` works in three stages.

1. Compose. Starting from the menu's root division, each element becomes a `ContentNode` holding a surface, an offset and child nodes. `_compose_element_node` resolves the element's measures against the space its parent offers, asks a type-specific composer for the content, then draws the border and background around it. Composers are looked up by walking the element's class hierarchy, so subclasses such as `NormalText` reuse the `Text` composer. Divisions place their children in a row or column with a gap and per-child `justify`. A selected element is drawn from a copy made with `dataclasses.replace` using its `selected_*` colours, so selection never mutates the real element.
2. Flatten. `_render_element_tree` walks the node tree breadth first and blits each node's shadow and surface onto the root canvas. `_collect_element_layout` records the screen rectangle of every selectable node for hit-testing; a node drawn from a copy points back to the real element through `_interaction_target`.
3. Output. The visible part of the canvas, chosen by the scroll offset, is copied into a fresh window-sized `SRCALPHA` surface and the scrollbar is drawn on top.

The copy in stage 3 uses `BLEND_RGBA_MAX` onto a zeroed surface instead of a normal blit. A normal alpha blit onto a transparent surface multiplies colour by alpha a second time, so translucent menus such as `Pause` would come out darker than designed. For the same reason the root node is never blitted onto itself in stage 2.

## Caching

Rebuilding the tree every frame would be wasteful, so the renderer caches at two levels.

- The composed canvas is reused while the menu, the window size and `Element._iterative_version` are unchanged. `Element.__setattr__` increments that class-wide counter whenever any element attribute changes value, so any edit, selection change or toggle invalidates the cache without the renderer having to know what changed.
- The final surface is also reused while the scroll position and the open input field's cursor glyph are unchanged. The cursor blinks on a clock, so including its glyph in the key makes the renderer redraw exactly when the cursor flips and not every frame.

`render` therefore returns the same surface object across frames when nothing visible changed, and the game can blit it every frame at little cost.

## Assets

Each renderer owns its own `FontManager` and `ImageManager`, exposed as `Interface.fonts` and `Interface.images`, so two interfaces never share registrations. Fonts are registered by lower-cased file name, which is what `Text.font_path` names; an unregistered font falls back to pygame's default font rather than failing. No fonts ship with the package. Images load on first use from `Image.image_path`; a file that fails to load becomes a magenta placeholder, and a path that does not exist draws nothing.

## Decisions

- One window-sized surface instead of per-menu surfaces with positions. The game needs a single blit at `(0, 0)` and mouse positions need no translation; the cost is a full-window surface, which the caching keeps cheap.
- Events return whether they were used. This lets the GUI and the game share one event loop without either knowing the other's controls.
- No global state. Earlier versions used a module-level menu manager and asset singletons; now everything hangs off an `Interface`, so a game can create more than one and tests stay independent.
- Settings edits an object passed in rather than importing a config module, so the library has no idea where a game keeps its settings.
- The window must exist before rendering. Surfaces are converted to the display format, which pygame can only do once a display mode is set. Every game has a window by the time it draws, so this is documented rather than worked around.

## Current limitations

- Appending to or removing from a division's `elements` list does not change any attribute, so it does not invalidate the render cache. Assign a new list instead.
- `Slider` has no visual yet; it is drawn as an empty 1×1 surface, although its keyboard and wheel handling work.
- `anchor`, `rotation`, `is_flexible`, `is_expandable` and `SelectedModifier` are stored on elements but not used, or not fully supported, by the renderer.
- The mouse wheel scrolls a menu by only 2 pixels per notch.
- The built-in `Start` menu carries the Mountain of Tiles title.
