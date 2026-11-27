# Why netlogopy

netlogopy runs NetLogo inside Python, headless or in the NetLogo window, with
agents as Python objects. This page shows what that gives, how fast a call
is, and how it compares with [pynetlogo](https://github.com/quaquel/pyNetLogo)
(formerly pyNetLogo), the other maintained library, as its own documentation
describes it (checked in November 2026).

## At a glance

| | netlogopy 1.0 | pynetlogo 0.5.2 |
|---|---|---|
| Install | `pip install netlogopy` | `pip install pynetlogo` |
| Depends on | JPype | JPype, NumPy, SciPy, pandas |
| NetLogo versions | 6.x and 7.x | 6.1 and newer (6.3 support added in 0.5) |
| Java | NetLogo's own runtime from NetLogo 6.3; Java 11+ for older NetLogo | the JVM found by JPype (`jvm_path` to choose one) |
| How NetLogo runs | JVM inside the Python process (JPype), NetLogo's own classes | JVM inside the Python process (JPype), through a Java bridge (`netlogolink.jar`) |
| NetLogo window | yes (Windows, Linux; not macOS) | yes, `gui=True` (not macOS) |
| Several models at once | any number of headless sessions, in threads; `run_experiment(workers=...)` | no built-in API; its examples run in parallel with ipyparallel or multiprocessing |
| Agent classes | `Turtle`, `Patch`, `Link` objects | none (NetLogo code) |
| Background runs | `start`, `pause`, `resume`, `stop` | no |
| Interface widgets from Python | add buttons, sliders, plots..., press buttons | no |
| Results | Python values (lists, agents), pandas optional | Python values, NumPy arrays, pandas DataFrames |
| License | MIT | BSD-3-Clause |
| Latest release | 1.0.2 | 0.5.2 (February 2024) |

## How NetLogo is run

netlogopy starts a Java virtual machine inside the Python process with
[JPype](https://jpype.readthedocs.io) and calls NetLogo's own classes
(`HeadlessWorkspace`, and `App` for the window): a call to NetLogo is a Java
method call, with no server and no port. See [How it works](how-it-works.md).

## Speed of a call

Measured with [`tools/benchmark.py`](https://github.com/bouaziznourddine/netlogopy/blob/main/tools/benchmark.py)
(headless, bundled model with 100 turtles, median of 2000 calls after a
warm-up, Windows 11, Python 3.13):

| Repeated call | NetLogo 7.0.0 | NetLogo 6.2.2 |
|---|---|---|
| `nl.command("tick")` | 0.04 ms | 0.04 ms |
| `nl.report("count turtles")` | 0.03 ms | 0.02 ms |
| `turtle.xcor` | 0.02 ms | 0.03 ms |
| `nl.command("ask turtles [ fd 1 ]")` | 0.18 ms | 0.17 ms |
| `nl.report([...])`, 3 reporters at once | 0.03 ms | 0.12 ms |

Two things make this fast: the call stays in the process, and netlogopy keeps
the compiled code, so a command or reporter is compiled by NetLogo once and
then only runs. A Python loop can therefore drive the simulation step by
step (decide, move agents, read values) without slowing it down.

These numbers are for netlogopy only: pynetlogo publishes no time per call.
Run `python tools/benchmark.py` to measure on your own machine.

## The NetLogo window

netlogopy opens the full NetLogo application with `NetLogo(gui=True)`: the
view, the widgets, the plots and the Code tab. Python can also add widgets
to the interface ([Interface widgets](guide/widgets.md)) and press its buttons.
A runtime error in code run from Python comes back to Python as
`NetLogoRuntimeError` instead of opening NetLogo's error dialog.

On macOS, neither netlogopy nor pynetlogo opens the window (Java's AWT needs
the main thread there); headless sessions work.

## License

netlogopy is MIT: it can be used in any project, open or closed.
pynetlogo is BSD-3-Clause, also permissive.

## When to pick which

- **netlogopy**: NetLogo 7, the NetLogo window driven from Python, agents as
  Python objects, background runs (`start` / `pause` / `stop`), widgets added
  from Python, parallel experiments in one process.
- **pynetlogo**: existing code written for it, the EMA Workbench, or its
  NumPy / pandas results (`patch_report`, `repeat_report`).

## Sources

- pynetlogo: [documentation](https://pynetlogo.readthedocs.io),
  [repository](https://github.com/quaquel/pyNetLogo),
  [PyPI](https://pypi.org/project/pynetlogo/), paper: Jaxa-Rozen and
  Kwakkel, [*PyNetLogo: Linking NetLogo with Python*](https://www.jasss.org/21/2/4.html),
  JASSS 21(2), 2018.
