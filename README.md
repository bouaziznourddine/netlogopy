# netlogopy

[![PyPI](https://img.shields.io/pypi/v/netlogopy.svg)](https://pypi.org/project/netlogopy/)
[![Tests](https://github.com/bouaziznourddine/netlogopy/actions/workflows/tests.yml/badge.svg)](https://github.com/bouaziznourddine/netlogopy/actions/workflows/tests.yml)
[![DOI](https://img.shields.io/badge/DOI-10.36819%2FSW25.019-blue)](https://doi.org/10.36819/SW25.019)

`netlogopy` is a Python library that bridges NetLogo and Python, enabling advanced agent-based simulations by combining NetLogo's simulation environment with Python's powerful libraries for computation, optimization, and AI. `netlogopy` allows direct manipulation of NetLogo agents from Python.

## What's new in 0.2

- **NetLogo is found automatically**: `run_netlogo()` works without `netlogo_home` (it reads the `NETLOGO_HOME` environment variable, then looks in the usual install folders). If the `java` command is missing, the Java bundled with NetLogo is used.
- **Headless mode** for fast batch runs (experiments, optimization, replications): `run_netlogo(headless=True)` or `with netlogo_session(headless=True) as n:`.
- **Batch helpers**: `create_pyturtles()`, `get_all_xy()`, `run_commands()`, `report_value()`.
- **Clear errors**: a NetLogo error raises `NetLogoError` with NetLogo's message (and a hint when `base.nls` is missing) instead of a cryptic `ValueError`; a failed action emits a `NetLogoWarning` instead of failing silently.
- **Bug fixes**: `fd(0.5)` and `bk(0.5)` now move; `can_move()` can return `False`; `in_radius()` and `turtles_here()` work with several neighbours; `set_pen_color()` no longer changes the turtle color; `towards_point()` and `distance_to_point()` use the exact point; texts with quotes or backslashes (Windows paths) no longer break NetLogo; accented labels survive on Windows; `import netlogopy` works with setuptools 82+.
- **Compatible**: every function, class and parameter of 0.1.x still works the same way.

Details in [CHANGELOG.md](CHANGELOG.md).

## License

This project is licensed under the terms of the [MIT License](./LICENSE).

## Developed by
- **Nourddine Bouaziz** - [@bouaziznourddine](https://github.com/bouaziznourddine/netlogopy)

## Requirements

* netlogopy works with Python >= 3.6
* netlogopy works with NetLogo 6.0, 6.1, and 6.2
* netlogopy requires Java: a JDK 8 or 11 on the PATH (e.g., `openjdk=11`), otherwise the Java bundled with NetLogo is used
* netlogopy requires [nl4py](https://pypi.org/project/nl4py) (installed automatically)

## Installation

### Step 1: Install NetLogo
Download and install NetLogo from the official site.

[![NetLogo](https://ccl.northwestern.edu/netlogo/images/netlogo-title-wide-60.jpg)](https://ccl.northwestern.edu/netlogo/download.shtml)

### Step 2: Install Conda
If you do not already have Conda installed, download and install [Anaconda](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

### Step 3: Create the Conda Environment

Use the provided `environment.yml` file:
```bash
conda env create -f environment.yml
conda activate netlogopy-env
```

Or install manually:
```bash
conda install openjdk=11 -y
pip install netlogopy
```

To upgrade:
```bash
pip install netlogopy --upgrade
```

### Step 4: Check the installation
```bash
python -m netlogopy
```
It shows the nl4py version, the NetLogo folder and the Java that netlogopy will use, and what is missing.

### Configure IDE (Optional)
To set up VS Code for CLI compatibility:
- [Set Default Terminal](https://www.w3schools.io/editor/vscode-change-default-terminal/)
- [Change Default Terminal in VS Code](https://stackoverflow.com/questions/44435697/change-the-default-terminal-in-visual-studio-code)

---

## Quick start

```python
from netlogopy.netlogopy import *

n = run_netlogo()        # NetLogo is found automatically
# n = run_netlogo("C:/Program Files/NetLogo 6.2.2")   # or give its folder
resize_world(n, 0, 60, 0, 60)
car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01")
car01.fd(1.5)
print(car01.get_xy())    # (20.0, 21.5)
```

---

## Colors Reference
![Colors](https://ccl.northwestern.edu/netlogo/docs/images/colors.jpg)

---

## API Reference

### Starting NetLogo

| Function | Description |
|----------|-------------|
| `run_netlogo(netlogo_home=None, path_model="", headless=False, setup=True)` | Start NetLogo, open the model (the built-in one by default) and run `setup` |
| `run_netlogo_model(netlogo_home=None, path_model)` | Open an existing model without running `setup` |
| `netlogo_session(...)` | Same arguments as `run_netlogo`, used as `with netlogo_session(...) as n:`; frees NetLogo at the end |
| `close_netlogo(n)` | Free a headless workspace and forget the Python agents of `n` |
| `find_netlogo_home()` | Return the NetLogo folder that will be used, or `None` |
| `reset_base_file(folder)` | Copy `base.nls` into a folder, to use netlogopy with your own model |

### World functions

| Function | Description |
|----------|-------------|
| `resize_world(n, x0, xf, y0, yf)` | Resize the NetLogo world |
| `set_background(n, image_path)` | Set a background image |
| `run_command(n, command)` | Execute any NetLogo command |
| `run_commands(n, [command, ...])` | Execute several NetLogo commands in one call |
| `report_value(n, expression)` | Evaluate any NetLogo reporter and get a Python value (float, bool, str or list) |
| `netlogoshow(n, word)` | Print a message in the NetLogo console |
| `nl_output_print(n, word)` | Print a message in the NetLogo output window |
| `clear_drawing(n)` | Erase all pen traces |
| `clear_all(n)` | `clear-all`: remove all agents, patches, links and ticks |
| `clear_all_turtles(n)` | Remove all pyturtles from the world |
| `get_ticks(n)` / `do_tick(n)` / `reset_ticks(n)` / `tick_advance(n, amount)` | Simulation clock |
| `get_world_width(n)`, `get_max_pxcor(n)`, `get_random_xcor(n)`, ... | World dimensions and random coordinates |
| `set_patch_color(n, x, y, color)` / `get_patch_color(n, x, y)` | Patch color |

### Agent functions

| Function | Description |
|----------|-------------|
| `create_pyturtles(n, positions, shape, size_shape, color, names, labelcolor, fields)` | Create one pyturtle per `(x, y)` position in a single call |
| `get_all_xy(n)` | Positions of all pyturtles in a single call: `{who: (x, y)}` |
| `count_pyturtles(n)` | Return the number of pyturtles in the world |
| `get_all_pyturtles(n=None)` | Return the Python list of pyturtles (only those of `n`, if given) |
| `get_turtle_by_id(who, n=None)` | Return the pyturtle with this who number |
| `getxyturtle(n, turtle)` | Return `[x, y]` of a turtle |
| `distancebetween(n, t1, t2)` | Return the distance between two turtles |

### `pyturtle` class

`pyturtle(n, x=0, y=0, shape="car", size_shape=4, color=0, name="zn", labelcolor=0, fields=None)` creates a turtle; `pyturtle.from_id(n, who)` wraps a turtle created by the model. `PyTurtle` is the same class.

| Methods | Description |
|---------|-------------|
| `fd(steps)`, `bk(steps)` | Move forward / backward (fractions and negative values work) |
| `rt(angle)`, `lt(angle)` | Turn right / left (degrees) |
| `setxy(x, y)`, `set_xcor(x)`, `set_ycor(y)`, `home()`, `set_random_position()` | Teleport |
| `move_to(target)`, `face_to(target)`, `wander(steps)` | Move relative to other turtles, random walk |
| `can_move(distance)` | `True` if the turtle can move forward that far |
| `get_xy()`, `get_xcor()`, `get_ycor()` | Position |
| `distanceto(target)`, `distance_to_point(x, y)`, `towards_point(x, y)` | Distance and heading to a turtle or a point |
| `set_heading(angle)`, `get_heading()` | Heading (0=N, 90=E, 180=S, 270=W) |
| `set_shape(shape)`, `get_shape()`, `set_color(color)`, `get_color()`, `set_size(size)`, `get_size()` | Appearance |
| `set_label(text)`, `get_label()`, `set_label_color(color)` | Label |
| `hideturtle()`, `showturtle()`, `dieturtle()`, `is_alive()` | Visibility and life |
| `pen_down()`, `pen_up()`, `pen_erase()`, `set_pen_color(color)`, `set_pen_size(size)`, `stamp()`, `stamp_erase()` | Pen |
| `patch_here_color()`, `set_patch_here_color(color)` | Patch under the turtle |
| `in_radius(radius)`, `turtles_here()` | Who numbers of the neighbours |

### `street` class (directed link)

```python
s = street(n, fromm=car01, too=car02, label="street",
           labelcolor=35, color=35, shape="default", thickness=0.5)
s.set_color(15)      # also: set_label, set_label_color, set_thickness, set_shape, hide, show, die
```

### Widgets and plots

| Function | Description |
|----------|-------------|
| `get_slider` / `set_slider`, `get_switch` / `set_switch`, `get_chooser` / `set_chooser`, `get_input_box` / `set_input_box` | Read and write the global behind a widget |
| `get_monitor(n, expression)` | Raw text of any NetLogo reporter (use `report_value` for Python values) |
| `set_current_plot`, `set_plot_pen`, `create_plot_pen`, `plot_add`, `plot_xy`, `clear_plot`, `set_plot_pen_color`, `set_plot_pen_mode`, `auto_plot_on/off`, `set_plot_x_range`, `set_plot_y_range` | Plot widgets |

### Errors

| Name | When |
|------|------|
| `NetLogoError` | NetLogo answered with an error instead of a value (e.g. the turtle is dead) |
| `NetLogoWarning` | An action failed in NetLogo; make it an error with `warnings.simplefilter("error", NetLogoWarning)` |
| `NetLogoNotFoundError` | NetLogo was not found: pass `netlogo_home=...` or set `NETLOGO_HOME` |

---

## Usage Examples

### Example 1: `pyturtle`
Create an agent and move it.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(10):
        time.sleep(1)
        car01.fd(1)
    n.close_model()
```

### Example 2: `set_background`
Set a custom background image.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    set_background(n, "path/to/image.png")
    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(10):
        time.sleep(1)
        car01.fd(1)
    n.close_model()
```

### Example 3: `street`
Create a link between two agents.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
    car02 = pyturtle(n, x=5,  y=5,  shape="car", size_shape=4, color=55, name="car02", labelcolor=55)
    street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, shape="default", thickness=0.5)

    for i in range(10):
        time.sleep(1)
        car01.fd(1)
    n.close_model()
```

### Example 4: `fd` / `bk`
Move forward and backward.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(10):
        time.sleep(0.5)
        car01.fd(2)

    for i in range(10):
        time.sleep(0.5)
        car01.bk(2)
    n.close_model()
```

### Example 5: `rt` / `lt`
Turn right and left — full circle.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(36):       # full circle turning right
        time.sleep(0.2)
        car01.rt(10)
        car01.fd(1)

    for i in range(36):       # full circle turning left
        time.sleep(0.2)
        car01.lt(10)
        car01.fd(1)
    n.close_model()
```

### Example 6: `set_heading` / `get_heading`
Set and read the direction of a turtle.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for heading in [0, 90, 180, 270]:   # North, East, South, West
        time.sleep(1)
        car01.set_heading(heading)
        print(f"Heading → {car01.get_heading()}")
        car01.fd(5)
    n.close_model()
```

### Example 7: `set_color` / `get_color`
Change the turtle color dynamically.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    # NetLogo colors: 15=red, 55=green, 95=blue, 35=orange, 125=violet
    for c in [15, 55, 95, 35, 125]:
        time.sleep(1)
        car01.set_color(c)
        print(f"Color → {car01.get_color()}")
        car01.fd(3)
    n.close_model()
```

### Example 8: `set_size` / `get_size`
Grow a turtle progressively.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=10, shape="car", size_shape=2, color=15, name="car01", labelcolor=15)

    for i in range(8):
        time.sleep(0.8)
        car01.set_size(2 + i)
        print(f"Size → {car01.get_size()}")
        car01.fd(2)
    n.close_model()
```

### Example 9: `hideturtle` / `showturtle`
Hide then show a turtle.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(10):
        time.sleep(1)
        if i == 3:
            car01.hideturtle()
        if i == 7:
            car01.showturtle()
        car01.fd(2)
    n.close_model()
```

### Example 10: `pen_down` / `pen_up` / `stamp`
Draw a path and stamp shapes.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=10, y=10, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    car01.pen_down()
    for side in range(4):          # draw a square
        for _ in range(10):
            time.sleep(0.1)
            car01.fd(1)
        car01.rt(90)
    car01.pen_up()

    for pos in [(20, 20), (40, 20), (30, 40)]:
        time.sleep(0.5)
        car01.setxy(pos[0], pos[1])
        car01.stamp()
    n.close_model()
```

### Example 11: `distanceto` / `face_to`
Calculate distance and orient a turtle towards another.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15)
    car02 = pyturtle(n, x=5,  y=5,  shape="car", size_shape=4, color=55)

    for i in range(10):
        time.sleep(1)
        car01.face_to(car02)
        dist = car01.distanceto(car02)
        print(f"Distance to car02: {dist}")
        car01.fd(1)
    n.close_model()
```

### Example 12: `count_pyturtles` / `clear_all_turtles`
Count and remove all agents.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    turtles = [pyturtle(n, x=i*10, y=20, shape="car", size_shape=3, color=15+i*10, name=f"car{i:02d}") for i in range(5)]
    time.sleep(1)
    print(f"Turtles: {count_pyturtles(n)}")

    time.sleep(2)
    clear_all_turtles(n)
    print(f"After clear: {count_pyturtles(n)}")
    n.close_model()
```

### Example 13: `get_ticks` / `do_tick`
Use NetLogo ticks as a simulation clock.

```python
import time
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=10, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for _ in range(20):
        time.sleep(0.3)
        do_tick(n)
        tick = get_ticks(n)
        car01.fd(1)
        car01.set_label(f"t={tick}")
        print(f"Tick: {tick}  pos: ({car01.get_xcor():.1f}, {car01.get_ycor():.1f})")
    n.close_model()
```

### Example 14: Integrating an Existing NetLogo Model
Add Python-controlled agents on top of an existing NetLogo model.

```python
import time, os
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    path_model = os.path.join(os.path.dirname(__file__), "Wolf Sheep Predation.nlogo")
    n = run_netlogo(netlogo_home, path_model)
    resize_world(n, 0, 70, 0, 55)
    run_command(n, "setup")

    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
    car02 = pyturtle(n, x=5,  y=5,  shape="car", size_shape=4, color=55, name="car02", labelcolor=55)
    street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, shape="default", thickness=0.5)

    for i in range(100):
        run_command(n, "go")
        time.sleep(0.1)
        car01.fd(1)
        if i % 20 == 0:
            car01.setxy(10, 10)
```

---

### Example 15: Headless batch runs
Run replications without window, much faster than the GUI (full script: `Examples/simple/28-headless-batch.py`).

```python
from netlogopy.netlogopy import *

if __name__ == "__main__":
    for seed in range(3):
        with netlogo_session(headless=True) as n:
            run_command(n, f"random-seed {seed}")
            cars = create_pyturtles(n, [(10, 10), (20, 20), (30, 30)], shape="car", color=15)
            for _ in range(100):
                run_command(n, "ask pyturtles [ rt random 360 fd 1 ]")  # all cars in one call
                do_tick(n)
            print(seed, get_all_xy(n))
```

---

## Using your own NetLogo model

The procedures that netlogopy calls live in `base.nls`. To use `pyturtle` and `street` in your own model:

1. Copy `base.nls` next to your model: `reset_base_file("path/to/model/folder")`
2. Add `__includes ["base.nls"]` at the top of the model's Code tab.
3. Open it without running setup, configure it, then run its own setup:
   ```python
   n = run_netlogo_model(path_model="path/to/model/My Model.nlogo")
   set_slider(n, "initial-number-sheep", 100)
   run_command(n, "setup")
   ```

If `base.nls` is missing, netlogopy raises a `NetLogoError` that says so.

## Troubleshooting

* `python -m netlogopy` shows what netlogopy finds (nl4py, NetLogo, Java) and what is missing.
* `NetLogoNotFoundError`: pass `netlogo_home="..."` to `run_netlogo` or set the `NETLOGO_HOME` environment variable.
* To stop on the first NetLogo problem instead of a warning: `warnings.simplefilter("error", NetLogoWarning)`.

---

## Citation

If you use netlogopy in your research, please cite:

> Bouaziz, N., Bettayeb, B., Sahnoun, M., and Yassine, A. 2025. "Netlogopy: Unlocking Advanced Simulation and Integration for NetLogo Using Python". In *Proceedings of the Operational Research Society Simulation Workshop 2025 (SW25)*, Exeter, United Kingdom. https://doi.org/10.36819/SW25.019

```bibtex
@inproceedings{bouaziz2025netlogopy,
  title     = {Netlogopy: Unlocking Advanced Simulation and Integration for {NetLogo} Using {Python}},
  author    = {Bouaziz, Nourddine and Bettayeb, Belgacem and Sahnoun, M'hammed and Yassine, Adnan},
  booktitle = {Proceedings of the Operational Research Society Simulation Workshop 2025 ({SW25})},
  address   = {Exeter, United Kingdom},
  year      = {2025},
  doi       = {10.36819/SW25.019}
}
```

---

## Development

```bash
pip install -e .[test]
pytest
```

The tests do not need NetLogo or Java. The NetLogo procedures live in `netlogopy/base.nls`: after editing it, run `python tools/sync_nlogo.py` to update `netlogopy/netlogopy.nlogo` and the copies in `Examples/`.

## Download Examples

You can download all example files from [GitHub Examples](https://github.com/bouaziznourddine/netlogopy/tree/main/Examples).

---

**Happy simulating!** If you have any questions, issues, or ideas for new features, please open an [issue](https://github.com/bouaziznourddine/netlogopy/issues) or submit a [pull request](https://github.com/bouaziznourddine/netlogopy).
