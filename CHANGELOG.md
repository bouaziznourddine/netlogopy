# Changelog

## 0.2.0

### nl4py replaced by netlogopy's own bridge
- netlogopy no longer depends on nl4py (GPL-3.0, unmaintained since 2021). It talks to NetLogo's public API (`HeadlessWorkspace`, `App`) through a small bridge written for netlogopy on top of JPype (Apache-2.0); Java runs inside the Python process.
- The Java bundled with NetLogo is used (then `JAVA_HOME`, or `NETLOGOPY_JVM`); extra JVM options with `NETLOGOPY_JVM_OPTIONS`.
- NetLogo errors in commands now raise `NetLogoError` (nl4py printed them in the Java console and continued).
- Texts are exchanged as Java strings: accents and non-Latin characters are kept on every platform.
- The GUI is started once per Python process; `run_netlogo()` can be called again to open another model in the same window. GUI mode is not available on macOS (use `headless=True`).
- `n.close_model()` still exists (it does nothing, as with nl4py). The scripts of `Examples/complexe/test` now use netlogopy (headless) instead of nl4py.

Existing code keeps working: every function, class and parameter of 0.1.x is still there and behaves the same, except for the bug fixes below.

### Fixed
- `fd()`, `bk()` and `wander()` ignored fractions: `fd(0.5)` did not move and `fd(2.5)` moved 2. Negative values now move in the opposite direction, as in NetLogo.
- `can_move()` always returned `True` (the text `"false"` was converted with `bool()`).
- `in_radius()` and `turtles_here()` failed as soon as there were two neighbours or more.
- `set_pen_color()` changed the turtle color instead of the pen color in the built-in model (`netlogopy.nlogo` had its own, outdated copy of the procedures).
- `towards_point()` and `distance_to_point()` used the center of the patch instead of the exact point (`towardsxy`, `distancexy`).
- Texts sent to NetLogo are escaped: quotes, backslashes (Windows paths in `set_background`) and new lines no longer break the command.
- `getxyturtle()` no longer uses `eval()` on the text returned by NetLogo.
- `pyturtle(fields=...)` no longer uses a mutable default argument.
- `__version__` said 0.1.0 while the package was 0.1.6; the version now has a single source.
- `Examples/simple/23-slider.py` and `24-switch.py` used globals (`speed`, `show-label`) that the built-in model did not define.

### Added
- `run_netlogo()` finds NetLogo by itself when `netlogo_home` is omitted (`NETLOGO_HOME`, then the usual install folders; NetLogo 6 preferred) and gives a clear `NetLogoNotFoundError` otherwise.
- Headless mode: `run_netlogo(headless=True)`, `run_netlogo_model(..., headless=True)`.
- `netlogo_session(...)` context manager and `close_netlogo(n)`.
- Batch helpers: `create_pyturtles()`, `get_all_xy()`, `run_commands()`, `report_value()`.
- `pyturtle.from_id()`, `get_xy()`, `is_alive()`; `street` methods `set_color`, `set_label`, `set_label_color`, `set_thickness`, `set_shape`, `hide`, `show`, `die`, and attributes `source` / `target`.
- `NetLogoError` (with a hint when `base.nls` is missing) and `NetLogoWarning` for failed actions, instead of silent failures or `ValueError: could not convert string to float`.
- `get_all_pyturtles(n)`, `get_turtle_by_id(who, n)`: filter by NetLogo instance; `clear_all(n)` only forgets the agents of `n`.
- PEP 8 aliases `Turtle`, `PyTurtle`, `Street`.
- `python -m netlogopy` checks the installation (JPype, NetLogo, Java).
- Example `Examples/simple/28-headless-batch.py`.
- Tests (no NetLogo needed, plus an end-to-end test of the bridge with a fake NetLogo in Java), GitHub Actions workflow, `CITATION.cff`.

### Changed
- `base.nls` is the single source of the NetLogo procedures: `tools/sync_nlogo.py` copies them into `netlogopy.nlogo` and into the examples (whose copies were outdated).
- Packaging: `pyproject.toml` is the only source of metadata (SPDX license, no deprecated settings); `setup.py` is a minimal shim. Project URLs point to `github.com/bouaziznourddine/netlogopy`.
- Repository: `.gitignore` and `.gitattributes` added; build outputs, `__pycache__`, `*.egg-info` and editor settings are no longer tracked; the BibTeX snippets are gathered in `paper/references.bib`.
