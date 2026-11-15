# Changelog

## 1.0.0

A rewrite of the engine: netlogopy now runs NetLogo inside the Python process
and covers the whole NetLogo language. Scripts written for 0.x keep working.

### New

- **No more nl4py.** netlogopy talks to NetLogo's own Java API through
  [JPype](https://jpype.readthedocs.io): no Java server, no socket, no port 25333.
  Compiled NetLogo code is cached, so a repeated call takes about 0.1 to 0.3 ms
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
  DataFrame); `run_until()`; nl4py-compatible `schedule_reporters()`.
- **Experiments**: `run_experiment()` runs parameter sweeps like BehaviorSpace,
  with repetitions, seeds, stop conditions and parallel workers.
- **Simulation management**: `start()` runs the model in the background;
  `pause()`, `resume()`, `stop()` and `wait()` control it while Python reads
  and changes the model.
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
  (`py.typed`), and eight new examples (`Examples/advanced`), including the
  job shop with human operators presented at SW25 (simulation and
  re-optimisation of the machine queues).

### Changed

- `report()` returns Python values instead of strings (`float(n.report(...))`
  still works).
- `base.nls` now only declares the `pyturtles` and `streets` breeds: the
  reporters it used to define are no longer needed by netlogopy, and its
  `extensions` and `globals` declarations clashed with the models including it.
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

- The nl4py dependency, `setup.py`, build artifacts and stray files from the repository.
