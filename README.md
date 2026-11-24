# netlogopy

[![Documentation](https://img.shields.io/badge/docs-bouaziznourddine.github.io%2Fnetlogopy-00897b)](https://bouaziznourddine.github.io/netlogopy/)
[![tests](https://github.com/bouaziznourddine/netlogopy/actions/workflows/tests.yml/badge.svg)](https://github.com/bouaziznourddine/netlogopy/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/netlogopy)](https://pypi.org/project/netlogopy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.36819%2FSW25.019-informational)](https://doi.org/10.36819/SW25.019)

`netlogopy` drives [NetLogo](https://ccl.northwestern.edu/netlogo/) models from
Python. It combines NetLogo's agent-based simulation environment with Python's
libraries for computation, optimization and AI: create and move agents from
Python, read any NetLogo value as a Python value, run experiments in parallel,
and collect data, in the NetLogo window or headless.

```python
from netlogopy import NetLogo

with NetLogo("Wolf Sheep Predation.nlogo") as nl:    # headless by default
    nl.globals["initial-number-wolves"] = 40
    nl.setup()
    data = nl.collect({"sheep": "count sheep", "wolves": "count wolves"}, steps=200)
```

<p align="center">
  <img src="docs/assets/gifs/job-shop.gif" width="300" alt="Job shop with human operators: NetLogo shows the workshop, Python re-optimises the queues">
  <img src="docs/assets/gifs/wolf-sheep-with-python-agents.gif" width="300" alt="Wolf Sheep Predation with two cars driven by Python">
  <img src="docs/assets/gifs/add-widgets.gif" width="300" alt="Interface widgets added from Python">
</p>

**Documentation, guide and examples: <https://bouaziznourddine.github.io/netlogopy/>**

## Features

- **The whole NetLogo language**: `command()` and `report()` run any NetLogo
  code; results come back as Python values (numbers, strings, booleans, lists,
  agents, `None` for `nobody`).
- **Agents as Python objects**: `Turtle`, `Patch` and `Link`, with properties
  (`turtle.color = 15`) and methods (`forward`, `face`, `in_radius`, `hatch`,
  `sprout`, `create_link_with`...).
- **Window or headless**: watch the simulation in the NetLogo window, or run
  any number of headless models in parallel threads.
- **Simulation management**: step the model from Python, or start it in the
  background and pause, resume and stop it while Python reads and changes it.
- **Interface widgets**: sliders, switches, choosers, inputs, monitors, plots
  and output areas.
- **Experiments**: parameter sweeps with repetitions, seeds and stop
  conditions, spread over several workers (like BehaviorSpace), and time
  series collection, as dicts or pandas DataFrames.
- **Bulk patch data**: read and write a patch variable for the whole world
  in one call (lists or numpy arrays).
- **Errors as exceptions**: `NetLogoCompileError` and `NetLogoRuntimeError`,
  with the NetLogo code that failed.
- NetLogo 6 and 7 (tested with 6.2.2, 6.3.0 and 7.0.0, on Windows). The
  Linux and macOS installation layouts are supported too; on macOS only
  headless sessions are possible.
- The 0.x API (`run_netlogo`, `pyturtle`, `street`...) still works.

## Requirements

- Python 3.8 or newer.
- [NetLogo](https://ccl.northwestern.edu/netlogo/download.shtml) 6.x or 7.x.
- Java: NetLogo 6.3 and newer include a suitable Java runtime. NetLogo 6.2 and
  older include Java 8, which is too old for JPype: install Java 11+ (for
  example `conda install -c conda-forge openjdk=17`) or set `JAVA_HOME`.
- [JPype1](https://pypi.org/project/JPype1/) (installed automatically).

## Installation

```bash
pip install netlogopy
```

With pandas and numpy (DataFrames and array grids):

```bash
pip install "netlogopy[data]"
```

Or create a conda environment with Python, Java 17 and netlogopy:

```bash
conda env create -f environment.yml
```

```bash
conda activate netlogopy-env
```

netlogopy finds NetLogo by itself: the `netlogo_home` argument, else the
`NETLOGO_HOME` environment variable, else the newest NetLogo installed in the
usual places (`C:/Program Files/NetLogo *`, `/Applications/NetLogo *`,
`~/NetLogo *`, `/opt/NetLogo *`). The Java runtime is found the same way:
`java_home`, NetLogo's own runtime, `JAVA_HOME`, the active conda
environment, then other NetLogo installations.

Check what netlogopy finds, and that NetLogo starts:

```bash
python -m netlogopy
```

## Quick start

```python
import time
from netlogopy import NetLogo, colors

nl = NetLogo(gui=True)               # the bundled model, in the NetLogo window
nl.setup()

cars = nl.create_turtles(8, "pyturtles", ordered=True, shape="car", size=4,
                         color=colors.RED, xcor=30, ycor=30)
for step in range(40):
    for car in cars:
        car.forward(0.5).right(3)
    nl.tick()
    time.sleep(0.05)

leader = cars[0]
leader.color = colors.BLUE
print(leader.xy, leader.heading)
print(leader.in_radius(10, "pyturtles", other=True))   # a list of Turtle objects
print(nl.report("mean [xcor] of pyturtles"))            # a float
print(nl.report(["count turtles", "ticks"]))            # [8.0, 40.0]

nl.command("ask pyturtles with [xcor > 30] [ set color green ]")
nl.close()                           # also done automatically at exit
```

## Guide

### Sessions

```python
from netlogopy import NetLogo

nl = NetLogo()                                   # bundled model, headless
nl = NetLogo("my_model.nlogo", gui=True)         # your model, in the window
nl = NetLogo("my_model.nlogo", setup=True)       # run its setup right away
nl = NetLogo(netlogo_home="C:/Program Files/NetLogo 6.4.0", jvm_args=["-Xmx8g"])

nl.open_model("other.nlogo")                     # switch model
with NetLogo("model.nlogo") as nl:               # closed at the end of the block
    ...
```

- One NetLogo installation (one JVM) per Python process.
- One NetLogo window per process, and any number of headless sessions. Each
  session can be used from its own thread.
- Closing a session in the window closes the window without saving the model.
- `NETLOGOPY_HEADLESS=1` turns every window off, to run window scripts in
  tests, in CI or on a server.
- NetLogo 7 asks to resize the widgets of models saved by NetLogo 6 when it
  opens them in its window; netlogopy answers "Resize and adjust positions".

### Running NetLogo code

```python
nl.command("crt 10 [ setxy random-xcor random-ycor ]")
nl.command("ask turtles [ fd 1 ]", "tick")        # several commands
nl.report("count turtles")                        # 10.0
nl.report(["count turtles", "ticks"])             # several reporters, one call
```

| NetLogo value             | Python value                        |
|---------------------------|-------------------------------------|
| number                    | `float`                             |
| string                    | `str`                               |
| boolean                   | `bool`                              |
| list                      | `list` (converted recursively)      |
| turtle / patch / link     | `Turtle` / `Patch` / `Link`         |
| agentset                  | `list` of agents                    |
| `nobody`, a dead agent    | `None`                              |
| anything else             | `str` (NetLogo's printed form)      |

Python values passed to netlogopy are converted the other way by
`to_netlogo()`: `None` becomes `nobody`, strings are quoted, lists become
NetLogo lists, agents become `(turtle 3)`... To pass NetLogo code instead of a
value, wrap it in `Code`:

```python
from netlogopy import Code
nl.create_turtles(100, xcor=Code("random-xcor"), ycor=Code("random-ycor"))
```

Errors raise Python exceptions:

```python
from netlogopy import NetLogoCompileError, NetLogoRuntimeError
try:
    nl.command("ask turtle 999 [ fd 1 ]")
except NetLogoRuntimeError as error:
    print(error.message)     # ASK expected input to be an agent ... but got NOBODY
    print(error.source)      # ask turtle 999 [ fd 1 ]
```

### Agents

```python
wolves = nl.create_turtles(5, "wolves", color=15, size=2)  # breed in plural form
t = nl.turtle(0)                     # any turtle by who number
p = nl.patch(3, 4)
link = nl.create_link(t, wolves[1])  # breed=..., directed=...

t.xcor, t.heading, t.color, t.label = 10, 90, 15, "hello"   # built-in variables
t["energy"] = 5                      # any variable (turtles-own, breed-own)
t.set(color=55, label_color=45)      # several at once; label_color -> label-color
t.get_many(["xcor", "ycor", "energy"])

t.forward(2).right(45).back(1)       # fd, bk, rt, lt, jump, setxy, move_to, face...
t.distance(p), t.towards(wolves[1]), t.patch_here(), t.patch_ahead(1)
t.in_radius(3, "sheep"), t.in_cone(5, 60), t.turtles_here(), t.neighbors()
babies = t.hatch(2, color=45)        # new Turtle objects
p.sprout(3, "sheep")
t.ask("rt random 360 fd 1")          # NetLogo code run by the agent
t.of("xcor + ycor")                  # NetLogo reporter evaluated by the agent
t.die(); t.alive                     # False
```

Queries on the whole model:

```python
nl.turtles()                          # every turtle, sorted by who
nl.turtles("sheep", where="energy > 5")
nl.patches(where="pcolor = green")
nl.links("roads")
nl.count("wolves"), nl.count("patches", "pcolor = green")
nl.ask("sheep with [energy < 2]", "die")
nl.ask(babies, "set color red")       # a list of agents works too
nl.of("turtles", "energy")            # values in the same order as nl.turtles()
nl.breeds()                           # {'turtles': ['sheep', 'wolves'], 'links': []}
```

### Globals, interface widgets and ticks

```python
nl.globals["initial-number-sheep"] = 100      # sliders, switches, choosers, inputs
nl.globals["model-version"] = "sheep-wolves-grass"
nl.globals.to_dict()                          # every global and its value
nl.setup(); nl.go(); nl.go(100)               # go 100 times in one call
nl.run_until("not any? wolves", max_steps=1000)
nl.ticks, nl.tick(), nl.reset_ticks()
nl.random_seed(42)                            # reproducible runs
```

### Starting, pausing and stopping

`start()` runs the model in the background, like a forever button, while
Python keeps reading and changing it:

```python
nl.start("go", interval=0.05)        # also: max_steps=500, until="not any? sheep"
while nl.running and nl.report("count sheep") < 300:
    time.sleep(0.5)
nl.pause()                           # the step in progress finishes first
nl.globals["wolf-reproduce"] = 8     # change the model while it is paused
nl.resume()
nl.wait(timeout=10)                  # wait for it to end by itself, at most 10 s
steps = nl.stop()                    # number of steps made
```

### World and patches

```python
nl.resize_world(-50, 50, -50, 50)
nl.set_topology(wrap_x=True, wrap_y=False)
nl.world_width, nl.max_pxcor, nl.patch_size

grid = nl.patch_grid("pcolor")                 # rows, top row first
array = nl.patch_grid("elevation", as_array=True)
nl.set_patch_grid("pcolor", grid)              # lists or numpy arrays
nl.diffuse("chemical", 0.5)
nl.import_pcolors("map.png")
nl.import_drawing("background.png")
```

### Adding interface widgets

In the NetLogo window, Python can add the items of NetLogo's *Add* menu. Each
slider, switch, chooser and input becomes a global of the model:

```python
with NetLogo(gui=True, setup=True) as nl:
    nl.add_slider("walkers", 1, 200, 50, 1)
    nl.add_switch("trails", True)
    nl.add_chooser("walker-color", ["red", "blue"], 0)
    nl.add_input("label-text", "hello")
    nl.add_button("walk", "rt random 50 - 25 fd 1", agents="turtles", forever=True)
    nl.add_monitor("count turtles", "walkers")
    nl.add_plot("Spread", {"distance": "plot mean [distancexy 0 0] of turtles"})
    nl.add_note("Added by Python")
    nl.globals["walkers"] = 80          # set it like any widget
    nl.press_button("walk")             # click it (again to stop a forever button)
```

Widgets go in a column to the right of the model's own widgets, unless `x=`
and `y=` are given. The model keeps its agents and ticks when they are added.
They last for the session (File > Save As in NetLogo keeps them), and need the
window: headless sessions raise `NetLogoError`.

### Plots, output, files and layouts

```python
nl.plot(3.2, plot="My Plot", pen="default")
nl.plotxy(1, 2); nl.histogram([1, 2, 2, 3]); nl.clear_all_plots()
nl.output_print("hello"); nl.show("in the command center")

nl.export_view("view.png")
nl.export_interface("interface.png")           # window only
state = nl.export_world("state.csv"); nl.import_world(state)
nl.export_plot("My Plot", "plot.csv")

nl.layout_circle("turtles", 20)
nl.layout_spring("turtles", "links", iterations=50)
```

### Collecting data and experiments

```python
data = nl.collect({"sheep": "count sheep", "wolves": "count wolves"},
                  steps=500, every=10, until="not any? wolves",
                  as_dataframe=True)            # pandas, or a dict of lists
```

```python
from netlogopy import run_experiment

rows = run_experiment(
    "Fire.nlogo",
    parameters={"density": [50, 55, 60, 65, 70]},   # every combination
    reporters={"burned": "burned-trees"},
    repetitions=10, steps=2000, until="not any? turtles",
    seed=1, workers=4, as_dataframe=True)
```

### Using your own models

Any model works with `NetLogo(...)`. The 0.x classes `pyturtle` and `street`
need the `pyturtles` breed and the `streets` link breed: the bundled model has
them, and any model gets them by including `base.nls`:

```python
from netlogopy import reset_base_file
reset_base_file("folder/of/your/model")      # copies base.nls there
```

then add `__includes [ "base.nls" ]` at the top of the model's Code tab. The
model must not declare these two breeds itself; without the include, `pyturtle`
and `street` raise an error that says what to add.

An include file cannot hold shapes, so `run_netlogo(home, "your-model.nlogo")`
copies netlogopy's shapes (`car`, `person_0`, `machine`...) into your model for
the session. With the `NetLogo` class, call `nl.import_shapes()` (or
`nl.import_shapes("other-model.nlogo")` to take the shapes of any model).

## API reference

### `NetLogo` session

| Group | Members |
|---|---|
| Session | `NetLogo(model=None, gui=False, netlogo_home=None, java_home=None, jvm_args=(), setup=False)`, `open_model`, `close` / `close_model`, `closed`, `gui`, `model_path`, `netlogo_version` |
| Code | `command(*commands)`, `report(reporter or list)`, `report_java` |
| Simulation | `setup`, `go(times)`, `run_until(condition, max_steps)`, `collect(...)`, `schedule_reporters(...)` |
| Background run | `start(command, interval, max_steps, until)`, `pause`, `resume`, `stop`, `wait(timeout)`, `running`, `paused`, `steps_run` |
| Ticks | `ticks`, `tick`, `tick_advance`, `reset_ticks`, `clear_ticks` |
| Globals | `globals[...]`, `get_global`, `set_global`, `global_names` |
| World | `min_pxcor`, `max_pxcor`, `min_pycor`, `max_pycor`, `world_width`, `world_height`, `resize_world`, `patch_size`, `set_patch_size`, `wrap_x`, `wrap_y`, `set_topology`, `random_seed`, `new_seed`, `clear_all`, `clear_turtles`, `clear_patches`, `clear_links`, `clear_globals`, `clear_drawing`, `display`, `no_display` |
| Agents | `turtle`, `patch`, `link`, `turtles`, `patches`, `links`, `count`, `ask`, `of`, `create_turtles`, `create_link`, `breeds`, `shapes`, `link_shapes`, `import_shapes`, `set_default_shape` |
| Choosing agents | `any`, `all`, `one_of`, `n_of`, `max_one_of`, `min_one_of`, `max_n_of`, `min_n_of`, `with_max`, `with_min`, `sort_on`, `turtles_on` |
| Random numbers | `random`, `random_float`, `random_normal`, `random_poisson`, `random_exponential`, `random_gamma`, `random_xcor`, `random_ycor`, `random_pxcor`, `random_pycor` |
| Colors, angles | `scale_color`, `shade_of`, `wrap_color`, `extract_rgb`, `extract_hsb`, `approximate_rgb`, `approximate_hsb`, `hsb`, `subtract_headings` |
| Patches | `patch_grid`, `set_patch_grid`, `diffuse`, `import_pcolors`, `import_drawing` |
| Files | `export_view`, `export_interface`, `export_world`, `import_world`, `export_output`, `export_plot`, `export_all_plots` |
| NetLogo file I/O | `file_open`, `file_close`, `file_close_all`, `file_flush`, `file_delete`, `file_exists`, `file_print`, `file_show`, `file_type`, `file_write`, `file_read`, `file_read_line`, `file_read_characters`, `file_at_end`, `set_current_directory` |
| Output | `show`, `output_print`, `output_show`, `output_type`, `output_write`, `clear_output` |
| Plots | `plot`, `plotxy`, `histogram`, `set_current_plot`, `set_current_plot_pen`, `create_temporary_plot_pen`, `clear_plot`, `clear_all_plots`, `set_plot_pen_color`, `set_plot_pen_mode`, `set_plot_pen_interval`, `plot_pen_up`, `plot_pen_down`, `plot_pen_reset`, `set_histogram_num_bars`, `set_plot_x_range`, `set_plot_y_range`, `auto_plot_on`, `auto_plot_off`, `setup_plots`, `update_plots`, `plot_name`, `plot_pen_exists`, `plot_x_range`, `plot_y_range`, `autoplot` (NetLogo 7) |
| Layouts | `layout_circle`, `layout_spring`, `layout_radial`, `layout_tutte` |
| Observer | `watch`, `follow`, `ride`, `reset_perspective`, `inspect`, `stop_inspecting` |
| Interface widgets (window) | `add_button`, `add_slider`, `add_switch`, `add_chooser`, `add_input`, `add_monitor`, `add_plot`, `add_output`, `add_note`, `press_button` |
| Timer, clock | `reset_timer`, `timer`, `date_and_time`, `beep` |
| Mouse, dialogs (window) | `mouse_down`, `mouse_inside`, `mouse_xcor`, `mouse_ycor`, `user_message`, `user_input`, `user_yes_or_no`, `user_one_of`, `user_file`, `user_new_file`, `user_directory` |

Primitives without a method of their own (maths, lists, strings, control flow, HubNet) are the ones
Python already has; they remain available in any NetLogo code passed to `command()` and `report()`.

### Agents

| Class | Members |
|---|---|
| all agents | `get`, `set`, `agent[name]`, `get_many`, `ask`, `of`, `alive`, `watch`, `ref` |
| `Turtle` | `who`, `breed`, `set_breed`, `xcor`, `ycor`, `xy`, `heading`, `color`, `size`, `shape`, `label`, `label_color`, `hidden`, `pen_mode`, `pen_size`, `dx`, `dy`; `forward`/`fd`, `back`/`bk`, `right`/`rt`, `left`/`lt`, `jump`, `setxy`, `move_to`, `face`, `facexy`, `home`, `can_move`, `die`, `hide_turtle`/`ht`, `show_turtle`/`st`, `pen_down`/`pd`, `pen_up`/`pu`, `pen_erase`/`pe`, `stamp`, `stamp_erase`, `distance`, `distancexy`, `towards`, `towardsxy`, `patch_here`, `patch_ahead`, `patch_at`, `patch_right_and_ahead`, `patch_left_and_ahead`, `neighbors`, `neighbors4`, `turtles_here`, `in_radius`, `in_cone`, `hatch`, `create_link_with`, `create_link_to`, `create_link_from`, `link_neighbors`, `in_link_neighbors`, `out_link_neighbors`, `my_links`, `my_in_links`, `my_out_links`, `link_with`, `create_links_with`, `create_links_to`, `create_links_from`, `is_link_neighbor`, `is_in_link_neighbor`, `is_out_link_neighbor`, `in_link_from`, `out_link_to`, `uphill`, `uphill4`, `downhill`, `downhill4`, `turtles_at`, `patch_at_heading_and_distance`, `follow`, `ride` |
| `Patch` | `pxcor`, `pycor`, `pcolor`, `plabel`, `plabel_color`; `neighbors`, `neighbors4`, `turtles_here`, `turtles_at`, `patch_at`, `patch_at_heading_and_distance`, `distance`, `distancexy`, `in_radius`, `sprout` |
| `Link` | `end1`, `end2`, `both_ends`, `other_end`, `breed`, `directed`, `color`, `label`, `label_color`, `thickness`, `shape`, `hidden`, `tie_mode`, `length`, `heading`; `die`, `hide_link`, `show_link`, `tie`, `untie` |

### Module

| Name | Purpose |
|---|---|
| `run_experiment`, `parameter_grid` | parameter sweeps |
| `Code`, `to_netlogo` | NetLogo code and literals |
| `colors` | `RED`, `GREEN`, ..., `BASE_COLORS`, `rgb`, `rgba`, `shade` |
| `NetLogoError`, `NetLogoCompileError`, `NetLogoRuntimeError`, `NetLogoNotFoundError` | exceptions |
| `find_netlogo_home`, `netlogo_version`, `jvm_info` | installation details |
| `BUNDLED_MODEL`, `BUNDLED_MODEL_NLOGOX`, `bundled_model` | the bundled model |

## The 0.x API

Scripts written for netlogopy 0.x keep working (`from netlogopy.netlogopy import *`
also gives the new classes). `run_netlogo()` now returns a `NetLogo` session,
so the new methods are available on it, and `pyturtle` objects are `Turtle`
objects. The code printed in the [SW25 paper](#citation) runs as it is,
including its import spelling `from netlogopy.nelogopy import *`.

| Function | Description |
|---|---|
| `run_netlogo(netlogo_home=None, path_model="", gui=None)` | open a model in the window and run `setup` |
| `run_netlogo_model(netlogo_home, path_model, gui=None)` | open a model without running `setup` |
| `run_netlogo_base(netlogo_home=None)` | open the bundled model |
| `run_command(n, code)` | run NetLogo commands |
| `resize_world(n, x0, xf, y0, yf)`, `resize_world_direct` | resize the world |
| `set_background(n, image)`, `set_background_direct` | background image |
| `netlogoshow(n, value)`, `nl_output_print(n, value)` | command center / output area |
| `clear_drawing`, `clear_all`, `clear_all_turtles` | clearing |
| `get_ticks`, `do_tick`, `reset_ticks`, `tick_advance` | ticks |
| `get_world_width`, `get_world_height`, `get_min_pxcor`, `get_max_pxcor`, `get_min_pycor`, `get_max_pycor`, `get_random_xcor`, `get_random_ycor` | world |
| `set_patch_color`, `get_patch_color` | patch colors |
| `getxyturtle`, `distancebetween`, `count_pyturtles`, `get_all_pyturtles`, `get_turtle_by_id` | agents |
| `get_slider`, `set_slider`, `get_switch`, `set_switch`, `get_chooser`, `set_chooser`, `get_input_box`, `set_input_box`, `get_monitor` | widgets |
| `set_current_plot`, `set_plot_pen`, `create_plot_pen`, `plot_add`, `plot_xy`, `clear_plot`, `set_plot_pen_color`, `set_plot_pen_mode`, `set_plot_x_range`, `set_plot_y_range`, `auto_plot_on`, `auto_plot_off` | plots |
| `reset_base_file(dest)`, `create_ntlg_file(dest)` | copy base.nls |
| `list2nllist`, `de_copy` | utilities |
| `pyturtle(n, x, y, shape, size_shape, color, name, labelcolor, fields)` | a Python-driven turtle: `fd`, `bk`, `rt`, `lt`, `setxy`, `move_to`, `face_to`, `set_heading`, `get_xy`, `distanceto`, `set_color`, `set_shape`, `set_size`, `set_label`, `hideturtle`, `showturtle`, `dieturtle`, `pen_down`, `pen_up`, `stamp`, `in_radius`, `turtles_here`... |
| `street(n, fromm, too, label, labelcolor, color, shape, thickness)` | a directed link between two pyturtles |
| `PyTurtle`, `Street` | CamelCase names of `pyturtle` and `street` |
| `car.fields` | the extra attributes given with `fields=`, as a live dict (`car.fields["busy"]` is `car.busy`) |

Changes in 1.0: `n.report()` returns Python values instead of strings, and
`base.nls` only declares the two breeds (see the [changelog](CHANGELOG.md)).

## Examples

| Folder | Examples |
|---|---|
| [Examples/simple](Examples/simple) | the 0.x API: 1 first agents, 2 movement, 3 appearance and drawing, 4 ticks and output, 5 widgets, 6 plots |
| [Examples/complexe](Examples/complexe) | 27: controlling an existing model; Fire and Wolf Sheep with Python agents |
| [Examples/advanced](Examples/advanced) | 28 quick start, 29 patch grids, 30 networks and layouts, 31 time series, 32 parameter sweep, 33 several models at once, 34 save and restore, 35 job shop with human operators (the SW25 application: simulation + re-optimisation), 36 interface widgets added from Python, 37 start, pause and stop a running model, 38 a Python vaccination policy in an epidemic, 39 calibrating a model with an optimiser, 40 reinforcement learning in a maze, 41 shortest routes on a road network, 42 Schelling segregation measured by Python, 43 evacuating a room with exits chosen by Python, 44 inequality and a wealth tax set by Python |

```bash
python Examples/advanced/28-quickstart.py
```

The [examples page](https://bouaziznourddine.github.io/netlogopy/examples/) of
the documentation shows each of them in an animation;
`python tools/record_gifs.py` records the animations again from the scripts.

## Documentation

The site is built with MkDocs Material from `docs/` and published on GitHub
Pages by `.github/workflows/docs.yml`. To build it locally:

```bash
pip install -r docs/requirements.txt
```

```bash
mkdocs serve
```

## Tests

The tests start NetLogo through JPype; they are skipped when NetLogo or Java
is missing. `pytest -m examples` runs every example headless.

```bash
pip install -e ".[test,data]"
```

```bash
pytest
```

## How it works

netlogopy starts a Java virtual machine inside the Python process with
JPype, with NetLogo's jars on the classpath, and calls NetLogo's own API:
`org.nlogo.headless.HeadlessWorkspace` for headless sessions and
`org.nlogo.app.App` for the window. NetLogo code is compiled once and the
compiled procedure is reused, so repeated calls are fast.

- The window is not available on macOS (AWT must own the main thread there);
  headless sessions work.
- When it closes the NetLogo window, netlogopy discards NetLogo's autosave of
  the model (changing a slider from Python is enough to make one), so NetLogo
  7 does not offer to recover it next time.
- `tools/make_nlogox.py` regenerates `netlogopy.nlogox` (NetLogo 7 format)
  after a change of the bundled `netlogopy.nlogo`.

## Colors

![NetLogo colors](https://ccl.northwestern.edu/netlogo/docs/images/colors.jpg)

`netlogopy.colors` has the named colors (`colors.RED == 15`...), `rgb()` and
`rgba()` lists, and `shade(color, amount)`.

## Citation

If you use netlogopy in your research, please cite:

> Nourddine Bouaziz, Belgacem Bettayeb, M'Hammed Sahnoun, Adnan Yassine.
> *Netlogopy: Unlocking Advanced Simulation and Integration for NetLogo Using
> Python.* Simulation Workshop 2025 (SW25), March 2025, Exeter, United Kingdom.
> [doi:10.36819/SW25.019](https://doi.org/10.36819/SW25.019) —
> [hal-04982069](https://hal.science/hal-04982069) ([PDF](paper/netlogopy-SW25-paper.pdf))

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

More references: [paper/references.bib](paper/references.bib).

## License

netlogopy is under the [MIT License](LICENSE).

It does not include NetLogo: it uses the NetLogo you install, which is free
software under the GNU GPL (version 2 or later), and JPype (Apache 2.0). MIT
code may be combined with GPL code, so using netlogopy with NetLogo is allowed,
for research and for commercial work. If you distribute a program that bundles
NetLogo itself, the GPL applies to that distribution.

The two example models in `Examples/complexe` (Fire and Wolf Sheep Predation)
come from the NetLogo Models Library: Copyright 1997 Uri Wilensky, under
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/) (credit
the author, no commercial use, share alike); their Info tab gives the full
notice. The SW25 paper in `paper/` is the authors' publication.

## Developed by

- **Nourddine Bouaziz** - [@bouaziznourddine](https://github.com/bouaziznourddine/netlogopy)

Questions, issues and ideas are welcome on the
[issue tracker](https://github.com/bouaziznourddine/netlogopy/issues).
