<h1 align="center">
  <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/draw-netlogopy.gif" width="720" alt="netlogopy: nine NetLogo turtles, moved by Python, write the word NETLOGOPY">
</h1>

<p align="center">
  <b>Run NetLogo models from Python, and let Python decide, optimise, learn and measure inside the simulation.</b>
</p>

<p align="center">
  <a href="https://bouaziznourddine.github.io/netlogopy/"><img src="https://img.shields.io/badge/docs-bouaziznourddine.github.io%2Fnetlogopy-00897b" alt="Documentation"></a>
  <a href="https://github.com/bouaziznourddine/netlogopy/actions/workflows/tests.yml"><img src="https://github.com/bouaziznourddine/netlogopy/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="https://pypi.org/project/netlogopy/"><img src="https://img.shields.io/pypi/v/netlogopy" alt="PyPI"></a>
  <a href="https://github.com/bouaziznourddine/netlogopy/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"></a>
  <a href="https://doi.org/10.36819/SW25.019"><img src="https://img.shields.io/badge/DOI-10.36819%2FSW25.019-informational" alt="DOI"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/python-policy.gif" width="32%" alt="An epidemic in NetLogo, vaccine doses given by Python">
  <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/q-learning.gif" width="32%" alt="A robot learns to cross a NetLogo maze with Q-learning in Python">
  <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/shortest-routes.gif" width="32%" alt="Cars routed by Python on a NetLogo road network">
</p>

[NetLogo](https://ccl.northwestern.edu/netlogo/) is the simplest way to build
and watch an agent-based model; Python has the libraries for optimisation,
statistics and AI. netlogopy joins them: NetLogo runs **inside the Python
process**, in its own window or headless, and every NetLogo value, agent and
widget is reachable from Python.

```python
from netlogopy import NetLogo

with NetLogo("Wolf Sheep Predation.nlogo") as nl:    # headless by default
    nl.globals["initial-number-wolves"] = 40
    nl.setup()
    data = nl.collect({"sheep": "count sheep", "wolves": "count wolves"},
                      steps=200, as_dataframe=True)
```

**Documentation, tutorial and examples: <https://bouaziznourddine.github.io/netlogopy/>**

## Why netlogopy

- **Fast, in-process calls**: a call is a Java method call, not a message to a
  server (about 0.02–0.05 ms for a simple command or reporter). A Python loop
  can drive the model tick by tick.
- **Python values back**: numbers, strings, lists, agents, `None` for `nobody`.
- **Agents as Python objects**: `Turtle`, `Patch` and `Link`, with properties
  (`turtle.color = 15`) and methods (`forward`, `face`, `in_radius`, `hatch`...).
- **The NetLogo window, driven from Python**: watch the model while Python
  plays in it, add sliders, buttons and plots to its interface, press its
  buttons.
- **Background runs**: `start`, `pause`, `resume` and `stop` a model while
  Python keeps reading and changing it.
- **Experiments**: parameter sweeps with repetitions and seeds over parallel
  headless sessions (like BehaviorSpace), time series as dicts or pandas
  DataFrames.
- **Clear errors**: `NetLogoCompileError` and `NetLogoRuntimeError`, with the
  NetLogo code that failed.
- **NetLogo 6 and 7**, any model, MIT license.

How it compares with pynetlogo: [Why netlogopy](https://bouaziznourddine.github.io/netlogopy/why/).

## Installation

```bash
pip install netlogopy
```

Version 1.0 is not on PyPI yet; until it is, install it from GitHub:

```bash
pip install git+https://github.com/bouaziznourddine/netlogopy
```

Add `[data]` for pandas and numpy (`pip install "netlogopy[data]"`). You also
need [NetLogo](https://ccl.northwestern.edu/netlogo/download.shtml) 6.x or
7.x. netlogopy finds it by itself (`NETLOGO_HOME`, or the usual install
folders) and uses the Java runtime that comes with NetLogo 6.3 and newer; for
NetLogo 6.2 and older, install Java 11+ (for example
`conda install -c conda-forge openjdk=17`).

Check what netlogopy finds, and that NetLogo starts:

```bash
python -m netlogopy
```

Details: [Installation](https://bouaziznourddine.github.io/netlogopy/installation/).

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
print(leader.in_radius(10, "pyturtles", other=True))   # a list of Turtle objects
print(nl.report("mean [xcor] of pyturtles"))            # a float
print(nl.report(["count turtles", "ticks"]))            # [8.0, 40.0]

nl.command("ask pyturtles with [xcor > 30] [ set color green ]")
nl.close()
```

`NetLogo(gui=False)`, the default, runs the same code without the window. Next
step: the [tutorial](https://bouaziznourddine.github.io/netlogopy/tutorial/),
a first simulation in five steps.

## Examples

In every example NetLogo simulates and shows the world, and Python decides,
optimises, learns or measures. The [examples page](https://bouaziznourddine.github.io/netlogopy/examples/)
of the documentation explains each one, with its results and its code.

```bash
python Examples/advanced/38-python-policy.py
```

Set `NETLOGOPY_HEADLESS=1` to run any example without the window.

### Applications

| | |
|---|---|
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/python-policy.gif" width="240" alt="A vaccination policy in an epidemic"> | **[A vaccination policy in an epidemic](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/38-python-policy.py)**<br>Python gives 6 vaccine doses every 5 ticks to the most exposed people: 50 people fall ill instead of 153.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#python-policy) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/q-learning.gif" width="240" alt="Reinforcement learning in a maze"> | **[Reinforcement learning in a maze](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/40-q-learning.py)**<br>NetLogo is the environment, a Python Q-table the learner; after 120 episodes the robot takes the shortest route.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#q-learning) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/evacuation.gif" width="240" alt="Evacuating a room"> | **[Evacuating a room](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/43-evacuation.py)**<br>Python sends each person to the exit that gets them out soonest: 77 ticks instead of 92.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#evacuation) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/segregation.gif" width="240" alt="Schelling segregation"> | **[Schelling segregation](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/42-segregation.py)**<br>Python measures the segregation and finds the largest blocks by flood fill.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#segregation) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/wealth-tax.gif" width="240" alt="Inequality and a wealth tax"> | **[Inequality and a wealth tax](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/44-wealth-tax.py)**<br>A Python controller sets the tax from the Gini coefficient: 0.28 instead of 0.42.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#wealth-tax) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/calibrate-model.gif" width="240" alt="Calibrating a model"> | **[Calibrating a model](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/39-calibrate-model.py)**<br>A bisection over 112 Fire runs in 4 parallel sessions finds the density that burns half the forest.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#calibrate) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/shortest-routes.gif" width="240" alt="Routing cars"> | **[Routing cars](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/41-shortest-routes.py)**<br>Dijkstra in Python on the NetLogo road network, rerouting when a road closes.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#routes) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/start-pause-stop.gif" width="240" alt="Start, pause, change and stop"> | **[Start, pause, change and stop](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/37-start-pause-stop.py)**<br>Wolf Sheep runs in the background; Python pauses it, changes the wolves and resumes it.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#start-pause-stop) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/fire-with-python-agents.gif" width="240" alt="Python agents in the Fire model"> | **[Python agents in the Fire model](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/complexe/Fire/Fire.py)**<br>The NetLogo Models Library model, with two cars and a street driven by Python.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#existing-models) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/wolf-sheep-with-python-agents.gif" width="240" alt="Python agents in Wolf Sheep Predation"> | **[Python agents in Wolf Sheep Predation](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/complexe/Wolf%20Sheep/Wolf.py)**<br>The same, in Wolf Sheep Predation.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#existing-models) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/external-model.gif" width="240" alt="Controlling an existing model"> | **[Controlling an existing model](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/complexe/27-external-model.py)**<br>Open a model without its setup, set its widgets, add Python agents.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#existing-models) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/add-widgets.gif" width="240" alt="Interface widgets added from Python"> | **[Interface widgets added from Python](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/36-add-widgets.py)**<br>Sliders, switches, buttons, monitors and a plot added to the NetLogo window, then used by Python.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#widgets) |

### The `NetLogo` class

| | |
|---|---|
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/quickstart.gif" width="240" alt="Quick start"> | **[Quick start](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/28-quickstart.py)**<br>Agents as Python objects, `command`, `report`, Python values.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#quickstart) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/patches-diffuse.gif" width="240" alt="Patches as a grid"> | **[Patches as a grid](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/29-patches-grid.py)**<br>A whole patch variable written and read in one call, `diffuse`.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#patches-grid) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/network-layout.gif" width="240" alt="Networks and layouts"> | **[Networks and layouts](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/30-network-layout.py)**<br>A network grown by Python, NetLogo's spring layout, nodes sized by degree.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#network-layout) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/collect-data.gif" width="240" alt="Time series, headless"> | **[Time series, headless](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/31-collect-data.py)**<br>`collect()` records Wolf Sheep at every step, as a dict or a DataFrame.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#collect-data) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/experiment.gif" width="240" alt="A parameter sweep"> | **[A parameter sweep](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/32-experiment.py)**<br>`run_experiment()`: 21 Fire runs on 4 workers, the percolation threshold.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#experiment) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/two-models.gif" width="240" alt="Several models at once"> | **[Several models at once](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/33-two-models.py)**<br>Fire and Wolf Sheep in two threads of the same process.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#two-models) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/export-import.gif" width="240" alt="Save and restore"> | **[Save and restore](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/34-export-import.py)**<br>Export the view, the plot and the world; restore the world.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#export-import) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/draw-netlogopy.gif" width="240" alt="Agents that write NETLOGOPY"> | **[Agents that write NETLOGOPY](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/advanced/45-draw-netlogopy.py)**<br>Nine turtles moved by Python along the strokes of the letters.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#draw-netlogopy) |

### The 0.x API

| | |
|---|---|
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/first-agents.gif" width="240" alt="First agents"> | **[First agents](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/simple/1-first-agents.py)**<br>`run_netlogo`, `pyturtle`, `street`, a background image.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#first-agents) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/movement.gif" width="240" alt="Moving a turtle"> | **[Moving a turtle](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/simple/2-movement.py)**<br>`fd`, `rt`, `setxy`, `move_to`, `face_to`, distances.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#movement) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/appearance.gif" width="240" alt="Appearance and drawing"> | **[Appearance and drawing](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/simple/3-appearance.py)**<br>Colours, shapes, labels, the pen and stamps.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#appearance) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/ticks-and-output.gif" width="240" alt="Ticks, counting and output"> | **[Ticks, counting and output](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/simple/4-ticks-and-output.py)**<br>Ticks, the command center and the output area.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#ticks-and-output) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/widgets-0x.gif" width="240" alt="Interface widgets"> | **[Interface widgets](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/simple/5-widgets.py)**<br>Sliders, switches, choosers, inputs and monitors.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#widgets-0x) |
| <img src="https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/docs/assets/gifs/plot-0x.gif" width="240" alt="Plotting from Python"> | **[Plotting from Python](https://github.com/bouaziznourddine/netlogopy/blob/main/Examples/simple/6-plot.py)**<br>Pens, colours and ranges of a NetLogo plot.<br>[Details](https://bouaziznourddine.github.io/netlogopy/examples/#plot-0x) |

## A short tour of the API

```python
from netlogopy import NetLogo, Code, run_experiment

nl = NetLogo("my_model.nlogo", gui=True)          # or headless: gui=False

# NetLogo code, Python values
nl.command("crt 10 [ setxy random-xcor random-ycor ]", "tick")
nl.report("count turtles")                        # 10.0
nl.report(["count turtles", "ticks"])             # several reporters in one call

# agents
wolves = nl.create_turtles(5, "wolves", color=15, xcor=Code("random-xcor"))
w = wolves[0]
w.forward(2).right(45)
w["energy"] = 5                                   # any turtles-own variable
nl.turtles("sheep", where="energy > 5")

# globals, widgets, simulation
nl.globals["initial-number-sheep"] = 100
nl.setup(); nl.go(100)
nl.run_until("not any? wolves", max_steps=1000)
nl.start("go", interval=0.05); nl.pause(); nl.resume(); nl.stop()

# interface widgets, added from Python (window only)
nl.add_slider("walkers", 1, 200, 50, 1)
nl.add_button("walk", "ask turtles [ fd 1 ]", forever=True)

# data and experiments
grid = nl.patch_grid("pcolor", as_array=True)
rows = run_experiment("Fire.nlogo", parameters={"density": [50, 60, 70]},
                      reporters={"burned": "burned-trees"},
                      repetitions=10, steps=2000, workers=4, as_dataframe=True)
```

Everything else is in the [guide](https://bouaziznourddine.github.io/netlogopy/guide/sessions/)
and the [API reference](https://bouaziznourddine.github.io/netlogopy/api/).

## Compatibility

- Python 3.8 or newer; [JPype1](https://pypi.org/project/JPype1/) is
  installed automatically.
- NetLogo 6.x and 7.x, tested with 6.2.2, 6.3.0 and 7.0.0 on Windows and with
  6.4.0 and 7.0.0 on Linux.
- On macOS, headless sessions work; the NetLogo window does not (Java's AWT
  needs the main thread there).
- Scripts written for netlogopy 0.x (`run_netlogo`, `pyturtle`, `street`...)
  keep working, and the code of the SW25 paper runs as printed: see
  [The 0.x API](https://bouaziznourddine.github.io/netlogopy/guide/legacy/)
  and the [changelog](https://github.com/bouaziznourddine/netlogopy/blob/main/CHANGELOG.md).

## Development

```bash
pip install -e ".[test,data]"
```

```bash
pytest
```

The tests are skipped when NetLogo or Java is missing; `pytest -m examples`
runs every example headless. The documentation is built from `docs/` with
MkDocs Material (`pip install -r docs/requirements.txt`, then `mkdocs serve`),
and `python tools/record_gifs.py` records the animations again from the
example scripts.

Questions, issues and ideas are welcome on the
[issue tracker](https://github.com/bouaziznourddine/netlogopy/issues).

## Citation

If you use netlogopy in your research, please cite:

> Nourddine Bouaziz, Belgacem Bettayeb, M'Hammed Sahnoun, Adnan Yassine.
> *Netlogopy: Unlocking Advanced Simulation and Integration for NetLogo Using
> Python.* Simulation Workshop 2025 (SW25), March 2025, Exeter, United Kingdom.
> [doi:10.36819/SW25.019](https://doi.org/10.36819/SW25.019) —
> [hal-04982069](https://hal.science/hal-04982069)
> ([PDF](https://github.com/bouaziznourddine/netlogopy/blob/main/paper/netlogopy-SW25-paper.pdf))

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

## History and acknowledgements

Versions 0.x of netlogopy were a layer of agent classes on top of [NL4Py](https://github.com/chathika/NL4Py)
(Gunaratne and Garibay, *NL4Py: Agent-based modeling in Python with parallelizable NetLogo workspaces*, SoftwareX 16, 2021, [doi:10.1016/j.softx.2021.100801](https://doi.org/10.1016/j.softx.2021.100801)), which started NetLogo behind a Java server and sent it commands.
We thank its authors for the work the first versions relied on. Since 1.0,
netlogopy talks to NetLogo's own Java API through JPype and no longer depends
on NL4Py.

## License

netlogopy is under the [MIT License](https://github.com/bouaziznourddine/netlogopy/blob/main/LICENSE). It does not include NetLogo:
it uses the NetLogo you install (GNU GPL, version 2 or later) and JPype
(Apache 2.0), which allows using netlogopy with NetLogo for research and for
commercial work. If you distribute a program that bundles NetLogo itself, the
GPL applies to that distribution.

The Fire and Wolf Sheep Predation models in `Examples/complexe` come from the
NetLogo Models Library (Copyright 1997 Uri Wilensky,
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/)).

Developed by **Nourddine Bouaziz** ([@bouaziznourddine](https://github.com/bouaziznourddine)).
