# Changelog

## 1.0.1

A release of corrections, after a review of the whole code. A script that
worked with 1.0.0 gives the same results, except where 1.0.0 was wrong.

### Fixed: data loss, hangs, a process that ends

- **The NetLogo window no longer ends Python.** Closing the window, or
  *File > Quit*, made NetLogo end the process: the script stopped without a
  message. The session is closed instead; the next call raises `NetLogoError`.
- **NetLogo 7 no longer writes over the model file.** When it found an autosave
  newer than the model (left by a script that was killed), NetLogo 7 asked
  "Recover Autosave" and then saved over the model, whatever the answer.
  Nothing is asked any more, the model file is not written, and a session no
  longer makes NetLogo autosave the model.
- **NaN and infinite numbers are refused** when a variable is set
  (`turtle.xcor = float("nan")`): they corrupted the turtle, and NetLogo never
  returned when its pen was down. (Introduced in 1.0.0.)
- **A background run can always be ended**: `halt()` interrupts the step in
  progress, `stop(timeout=...)` does it after a delay, and `close()` and the
  end of the script no longer wait for a step that never ends.
- **`start("go")` ends when the model's `go` calls `stop`**, as documented
  (headless sessions).

### Fixed: wrong or misleading results

- `nl.of(agents, ...)` gives its values in the order of a Python list, one per
  agent (`None` for a dead agent): `zip(agents, values)` pairs them. It used
  to sort them by who number and drop the duplicates.
- Reading agents during a background run: no more `None` in the lists, no more
  Java exception.
- `create_turtles`, `hatch`, `sprout` and `create_link` return their own agents
  during a background run, and leave no agent behind when they fail.
- `nl.patch(x, y)` with whole numbers outside the world gives `None` (or the
  patch it wraps to), like the other coordinates.
- `nl.link(a, b)` without a breed finds links of any breed.
- `collect(until=...)` stops at the step where the condition becomes true, not
  at the next multiple of `every`; it refuses two columns of the same name.
- `schedule_reporters()` no longer repeats its last row when `go` stops.
- `n_of()` evaluated a random filter twice and could fail; `layout_circle()`
  ignored the order of a list; `set_topology()` did not tell the view;
  `set_current_directory()` was ignored by `file_open`, `file_delete` and
  `file_exists`; `diffuse(neighbors=5)` silently used 8.
- An empty Python list of agents is no longer an error; a `;` comment at the
  end of NetLogo code no longer breaks the command; lists of thousands of
  agents compile; `set_patch_grid()` accepts agents.
- Agents of another session are refused instead of designating other agents.
- `turtle.set(value=5)` sets the variable `value` (the keyword was taken for a
  parameter); a model variable spelled like an alias (`hidden`, `label_color`)
  is that variable; `turtle.breed = "wolves"` works.
- In the window, code compiled before the user edited the model is no longer
  reused.

### Fixed: experiments

- `parameter_grid()` and `run_experiment()` take a numpy array, a range or any
  collection as the values to try (an array was one value: one run instead of
  several).
- A typo in a reporter, `until`, `setup` or `go` is reported before the first
  run; the first run that fails ends the sweep, and the error names the run.
- In an explicit list of runs, a run no longer inherits the globals set by the
  previous run of the same worker.
- `until` is tested before the first step; `every`, `steps` and `repetitions`
  are checked.

### Fixed: scripts written for 0.x

- `car.fd(steps=2)`, `car.bk(steps=1)` and `car.move_to(target=other)` work
  again.
- `pyturtle(fields={"color": ...})`: a field named like a `Turtle` attribute
  no longer breaks the object (it is read through `car.fields[...]`).
- `list_pyturtle` and `list_street` follow a `setup`, a street asked twice,
  several sessions and `clear_all_turtles`.
- `set_background("image.png")` finds an image of the current folder;
  `de_copy()` copies a pyturtle.

### Fixed: installation and window

- A wrong model path with `gui=True` is reported before the window opens (the
  process could no longer open a window afterwards).
- NetLogo is found from a folder above or inside its installation; a release
  is preferred to its pre-releases; an installation folder with accents keeps
  its extensions.
- `jvm_args` and `java_home` given when the Java VM already runs produce a
  warning instead of being ignored silently.
- When NetLogo 7 shows its "Data Consent" question (at its first window on a
  computer), a warning says that the script waits for the answer;
  `tools/netlogo_no_statistics.py` records "No" where nobody can click.
- A widget named like a breed, a procedure or a primitive is refused (the
  model no longer compiled); so is a button or a monitor whose code does not
  compile.
- Sessions dropped without `close()`, background runs and `run_experiment`
  workers no longer leave Java threads or workspaces behind.

### Added

- `nl.halt()` and `nl.stop(timeout=...)`.
- `error.context` on `NetLogoRuntimeError`: the agent, the primitive and the
  procedures that NetLogo names for a runtime error.
- Tests of the NetLogo window in continuous integration; Python 3.8 and 3.14.

### Changed

- `nl.globals["unknown"]` raises `KeyError`, as a dict does (it raised
  `NetLogoCompileError`).
- `link.other_end(turtle)` raises `ValueError` for a turtle that is not an end
  of the link (it returned an end).
- The package is credited to "The netlogopy developers".
- The package description on PyPI no longer says that 1.0 is not published.

## 1.0.0

A rewrite of the engine: netlogopy now runs NetLogo inside the Python process
and covers the whole NetLogo language. Scripts written for 0.x keep working.

### New

- **NetLogo in the Python process.** netlogopy talks to NetLogo's own Java API through
  [JPype](https://jpype.readthedocs.io): no Java server, no socket, no port.
  Compiled NetLogo code is cached, so a repeated call takes a few hundredths of a millisecond
  instead of the 3 to 5 ms needed to compile it every time.
- **Quality**: a docstring on every public class, method and function, code style
  checked with Ruff, and test coverage measured in continuous integration.
- **Agent variables without NetLogo code**: reading or writing a variable of a
  turtle or a patch (`turtle.xcor = x`, `patch.pcolor`, `agent.set(...)`) uses
  NetLogo's Java API directly, with NetLogo's own checks, so a new value no
  longer compiles a new command (about 0.05 ms instead of 3 to 5 ms).
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
- `netlogopy.nelogopy`, the module name of the first releases, is back, and a
  test runs the scripts written for them.
- `PyTurtle` and `Street` class names, and `pyturtle.fields` (the extra
  attributes as a live dict).
- Tests against a real NetLogo, a GitHub Actions workflow, type information
  (`py.typed`), and seventeen new examples (`Examples/advanced`), including the
  job shop with human operators (simulation and
  re-optimisation of the machine queues), interface widgets added from
  Python, a background run paused and changed by Python (37), and a Python
  vaccination policy in an epidemic (38), calibration with an optimiser (39),
  reinforcement learning in a maze (40), routing on a road network (41),
  Schelling segregation measured by Python (42), a room evacuated with exits
  chosen by Python (43) and a wealth tax set by a Python controller (44), and nine turtles that
  write NETLOGOPY (45).
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
- Repository: `.gitignore` and `.gitattributes`.

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

- The dependency on [NL4Py](https://github.com/chathika/NL4Py), which 0.x used to start NetLogo behind a Java server and send it
  commands; thanks to its authors (Gunaratne and Garibay, *NL4Py: Agent-based modeling in Python with parallelizable NetLogo workspaces*, SoftwareX 16, 2021, [doi:10.1016/j.softx.2021.100801](https://doi.org/10.1016/j.softx.2021.100801)).
- `setup.py`, build artifacts and stray files from the repository.
