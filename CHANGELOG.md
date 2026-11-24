# Changelog

## 1.0.0

A rewrite of the engine: netlogopy now runs NetLogo inside the Python process
and covers the whole NetLogo language. Scripts written for 0.x keep working.

### New

- **NetLogo in the Python process.** netlogopy talks to NetLogo's own Java API through
  [JPype](https://jpype.readthedocs.io): no Java server, no socket, no port.
  Compiled NetLogo code is cached, so a repeated call takes a few hundredths of a millisecond
  instead of the 3 to 5 ms needed to compile it every time.
- **`NetLogo` class**: a session on a model, in the NetLogo window (`gui=True`)
  or headless (default). Any number of headless sessions can run in one process,
  in parallel threads.
- **Typed results**: `report()` returns floats, strings, booleans, nested lists,
  `Turtle` / `Patch` / `Link` objects, lists of agents for agentsets and `None`
  for `nobody`, instead of strings.
- **Python errors**: `NetLogoCompileError` and `NetLogoRuntimeError` (with the
  failing NetLogo code), in headless mode and in the window alike.
- **Agents**: `Turtle`, `Patch` and `Link` classes with properties for the
  built-in variables, generic `get` / `set` / `agent[name]` for any variable,
  and methods for movement, geometry, neighbourhoods, `hatch`, `sprout`, links,
  pen and appearance.
- **World and model**: `create_turtles`, `create_link`, `turtles`, `patches`,
  `links`, `count`, `ask`, `of`, globals and interface widgets (`nl.globals`),
  ticks, world size, topology, random seeds, perspective, breeds and shapes.
- **Patches in bulk**: `patch_grid` / `set_patch_grid` (lists or numpy arrays),
  `diffuse`, `import_pcolors`.
- **Plots, output, files**: every plot primitive, output area, `export_view`,
  `export_world` / `import_world`, `export_plot`, `export_interface`...
- **Network layouts**: `layout_circle`, `layout_spring`, `layout_radial`, `layout_tutte`.
- **Data collection**: `collect()` records reporters over time (dict or pandas
  DataFrame); `run_until()`; `schedule_reporters()` on a tick schedule.
- **Experiments**: `run_experiment()` runs parameter sweeps like BehaviorSpace,
  with repetitions, seeds, stop conditions and parallel workers.
- **Simulation management**: `start()` runs the model in the background;
  `pause()`, `resume()`, `stop()` and `wait()` control it while Python reads
  and changes the model.
- **More primitives as methods**: choosing agents (`one_of`, `n_of`, `max_one_of`,
  `with_max`, `turtles_on`...), NetLogo's random numbers, color conversions,
  NetLogo file I/O (`file_open`, `file_read`...), timer, mouse, user dialogs,
  `inspect`, `uphill` / `downhill`, link queries (`in_link_from`, `is_link_neighbor`...).
- `import_shapes()` copies the shapes of the bundled model (or of any model)
  into the open model; `run_netlogo()` does it for a model of your own, so
  `pyturtle(shape="person_0")` works in every model.
- **Interface widgets from Python** (NetLogo window): `add_button`,
  `add_slider`, `add_switch`, `add_chooser`, `add_input`, `add_monitor`,
  `add_plot`, `add_output`, `add_note`, and `press_button` to click a button.
- **Documentation site** (MkDocs Material, GitHub Pages): installation,
  tutorial, guide, examples with their code and animations, API reference
  (NumPy-style docstrings), comparison with pynetlogo, paper.
  `tools/record_gifs.py` records the animations from the example scripts and
  `tools/benchmark.py` times repeated calls.
- **NetLogo 7** support (tested with NetLogo 6.2.2, 6.3.0 and 7.0.0); the
  bundled model also ships in the `.nlogox` format. NetLogo and Java are found
  automatically (`NETLOGO_HOME`, `JAVA_HOME`, the newest NetLogo installed).
- `netlogopy.colors`, `Code` (raw NetLogo code as a value), `NETLOGOPY_HEADLESS=1`
  (run window scripts without a window, e.g. in CI).
- The bundled model has demo widgets: `speed` slider, `show-label` switch,
  `scenario` chooser, `user-text` input, monitors, `My Plot` and an output area.
- `python -m netlogopy` checks the installation: JPype, NetLogo, Java, and a
  headless start of NetLogo.
- The code printed in the SW25 paper runs as it is: `netlogopy.nelogopy` (the
  paper's import spelling) is back, and a test executes the paper's listings.
- `PyTurtle` and `Street` class names, and `pyturtle.fields` (the extra
  attributes as a live dict).
- Tests against a real NetLogo, a GitHub Actions workflow, type information
  (`py.typed`), and seventeen new examples (`Examples/advanced`), including the
  job shop with human operators presented at SW25 (simulation and
  re-optimisation of the machine queues), interface widgets added from
  Python, a background run paused and changed by Python (37), and a Python
  vaccination policy in an epidemic (38), calibration with an optimiser (39),
  reinforcement learning in a maze (40), routing on a road network (41),
  Schelling segregation measured by Python (42), a room evacuated with exits
  chosen by Python (43) and a wealth tax set by a Python controller (44).
- A PyPI publishing workflow (trusted publishing on a GitHub release).
- The 26 one-function examples of `Examples/simple` are merged into six
  (first agents, movement, appearance, ticks and output, widgets, plots),
  which still show every 0.x function.

### Changed

- `report()` returns Python values instead of strings (`float(n.report(...))`
  still works).
- `base.nls` now only declares the `pyturtles` and `streets` breeds: the
  reporters it used to define are no longer needed by netlogopy, and its
  `extensions` and `globals` declarations clashed with the models including it.
- `pyturtle` and `street` in a model that does not include `base.nls` raise an
  error that says what to add.
- `run_netlogo()` finds NetLogo by itself; `netlogo_home` is optional.
- Python 3.8+ (was 3.6+); the only dependency is JPype1.
- Packaging: `pyproject.toml` is the only source of metadata, with an SPDX
  license and the version read from `netlogopy.__version__`; the project URLs
  point to `github.com/bouaziznourddine/netlogopy`.
- Repository: `.gitignore` and `.gitattributes`; the SW25 paper and the BibTeX
  references are in `paper/`.

### Fixed

- `set_pen_color` in base.nls used a variable that does not exist in NetLogo.
- `fd` / `bk` / `wander` ignored fractional and negative distances.
- `towards_point` and `distance_to_point` used the patch centre instead of the point.
- `can_move` could report True for "false"; `getxyturtle` used `eval`.
- Strings containing quotes or backslashes broke the generated NetLogo code;
  accents and non-Latin characters are now kept on every platform.
- `in_radius()` and `turtles_here()` failed as soon as there were two
  neighbours or more.
- `pyturtle(fields=...)` shared one default dict between all turtles.
- `__version__` said 0.1.0 while the package was 0.1.6.
- Examples 23, 24, 26 and 27 referred to widgets or breeds that did not exist.
- The build backend in pyproject.toml did not exist, so the package did not build.

### Removed

- The Java server dependency, `setup.py`, build artifacts and stray files from the repository.
