"""
netlogopy -- drive NetLogo agents from Python.

Every function takes ``n``, the NetLogo instance returned by :func:`run_netlogo`.
Agents created from Python are :class:`pyturtle` objects and the links between
them are :class:`street` objects.

The NetLogo side of the library lives in ``base.nls`` (procedures called from
Python). The built-in model ``netlogopy.nlogo`` contains a copy of them; to use
your own model, copy ``base.nls`` next to it with :func:`reset_base_file` and add
``__includes ["base.nls"]`` at the top of its Code tab.
"""
import codecs
import contextlib
import copy
import glob
import importlib
import math
import numbers
import os
import platform
import re
import shutil
import sys
import types
import warnings
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

__all__ = [
    # Errors and warnings
    "NetLogoError", "NetLogoNotFoundError", "NetLogoWarning",
    # Initialisation
    "find_netlogo_home", "is_netlogo_home", "run_netlogo", "run_netlogo_base",
    "run_netlogo_model", "close_netlogo", "netlogo_session", "reset_base_file",
    "create_ntlg_file", "NetLogoApp", "HeadlessNetLogo",
    "BASE_MODEL_PATH", "BASE_NLS_PATH",
    # Utilities
    "list2nllist", "de_copy", "get_turtle_by_id",
    # World
    "run_command", "run_commands", "report_value", "resize_world", "resize_world_direct",
    "set_background", "set_background_direct", "netlogoshow", "nl_output_print",
    "clear_drawing", "clear_all", "clear_all_turtles",
    # Ticks
    "get_ticks", "do_tick", "reset_ticks", "tick_advance",
    # World dimensions
    "get_world_width", "get_world_height", "get_max_pxcor", "get_min_pxcor",
    "get_max_pycor", "get_min_pycor", "get_random_xcor", "get_random_ycor",
    # Patches
    "set_patch_color", "get_patch_color",
    # Agents
    "getxyturtle", "distancebetween", "count_pyturtles", "get_all_pyturtles",
    "get_all_xy", "create_pyturtles", "list_pyturtle", "list_street",
    # UI widgets
    "get_slider", "set_slider", "get_switch", "set_switch", "get_chooser", "set_chooser",
    "get_input_box", "set_input_box", "get_monitor",
    # Plot widget
    "set_current_plot", "set_plot_pen", "create_plot_pen", "plot_add", "plot_xy",
    "clear_plot", "set_plot_pen_color", "set_plot_pen_mode", "auto_plot_on",
    "auto_plot_off", "set_plot_x_range", "set_plot_y_range",
    # Classes
    "turtle", "pyturtle", "street", "Turtle", "PyTurtle", "Street",
    # Names that `from netlogopy.netlogopy import *` exported before 0.2
    "copy", "nl4py", "os", "shutil", "Any", "List", "Optional",
]

list_pyturtle: List[Any] = []
list_street:   List[Any] = []

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_MODEL_PATH = os.path.join(PACKAGE_DIR, "netlogopy.nlogo")
BASE_NLS_PATH = os.path.join(PACKAGE_DIR, "base.nls")


# ─── Errors ────────────────────────────────────────────────────────────────────

class NetLogoError(RuntimeError):
    """NetLogo answered with an error message instead of the expected value."""


class NetLogoNotFoundError(FileNotFoundError):
    """No usable NetLogo installation was found."""


class NetLogoWarning(UserWarning):
    """A NetLogo action that returns nothing reported an error.

    Turn these warnings into exceptions with
    ``warnings.simplefilter("error", NetLogoWarning)``.
    """


# ─── nl4py import ──────────────────────────────────────────────────────────────

def _resource_filename(package: str, resource: str) -> str:
    """Minimal replacement for ``pkg_resources.resource_filename`` (used by nl4py)."""
    module = sys.modules.get(package) or importlib.import_module(package)
    base = os.path.dirname(os.path.abspath(module.__file__))
    return os.path.join(base, *resource.split("/"))


def _import_nl4py() -> Any:
    """Import nl4py, even when setuptools no longer ships ``pkg_resources``.

    nl4py 0.9 imports ``pkg_resources``, which setuptools removed in version 82,
    but it only uses ``resource_filename``. A tiny stand-in is provided while
    nl4py is imported and removed right after, so other libraries are unaffected.
    """
    shim = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # pkg_resources deprecation noise
        try:
            import pkg_resources  # noqa: F401
        except ImportError:
            shim = types.ModuleType("pkg_resources")
            shim.resource_filename = _resource_filename
            sys.modules["pkg_resources"] = shim
        try:
            module = importlib.import_module("nl4py")
        finally:
            if shim is not None and sys.modules.get("pkg_resources") is shim:
                del sys.modules["pkg_resources"]
    return module


try:
    nl4py = _import_nl4py()
    _NL4PY_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _error:  # pragma: no cover - depends on the environment
    nl4py = None
    _NL4PY_IMPORT_ERROR = _error


def _require_nl4py() -> Any:
    if nl4py is None:
        raise ImportError(
            "netlogopy needs the 'nl4py' package to talk to NetLogo "
            "(importing it failed: {!r}). Install it with:  pip install nl4py"
            .format(_NL4PY_IMPORT_ERROR)
        ) from _NL4PY_IMPORT_ERROR
    return nl4py


# ─── Finding NetLogo and Java ──────────────────────────────────────────────────

def _jar_dir(home: str) -> str:
    """Folder that holds netlogo-<version>.jar (same rule as nl4py)."""
    return os.path.join(home, "Java" if platform.system() == "Darwin" else "app")


def is_netlogo_home(path: Optional[str]) -> bool:
    """Return True if `path` is a NetLogo installation folder that nl4py can use."""
    if not path:
        return False
    jar_dir = _jar_dir(os.path.expanduser(str(path)))
    return bool(glob.glob(os.path.join(glob.escape(jar_dir), "netlogo-[0-9]*.jar")))


def _netlogo_version(path: str) -> Tuple[int, ...]:
    """Version number read from a folder name such as 'NetLogo 6.2.2'."""
    match = re.search(r"(\d+(?:\.\d+)*)", os.path.basename(os.path.normpath(path)))
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def _candidate_homes() -> List[str]:
    """Folders where NetLogo is usually installed on this operating system."""
    system = platform.system()
    roots: List[str] = []
    if system == "Windows":
        for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            if os.environ.get(var):
                roots.append(os.environ[var])
        roots.append("C:/Program Files")
        if os.environ.get("LOCALAPPDATA"):
            roots.append(os.path.join(os.environ["LOCALAPPDATA"], "Programs"))
    elif system == "Darwin":
        roots += ["/Applications", os.path.expanduser("~/Applications")]
    else:
        roots += [os.path.expanduser("~"), "/opt", "/usr/local", "/usr/share",
                  os.path.expanduser("~/Applications")]
    homes: List[str] = []
    seen = set()
    for root in roots:
        for pattern in ("NetLogo*", "netlogo*"):
            for path in glob.glob(os.path.join(glob.escape(root), pattern)):
                key = os.path.normcase(os.path.abspath(path))
                if key not in seen and os.path.isdir(path):
                    seen.add(key)
                    homes.append(path)
    return homes


def find_netlogo_home() -> Optional[str]:
    """Locate a NetLogo installation; return its folder, or None.

    The NETLOGO_HOME environment variable wins; otherwise the usual install
    folders are searched. NetLogo 6.x is preferred (nl4py supports it), and the
    most recent version is chosen when several are installed.
    """
    env_home = os.environ.get("NETLOGO_HOME")
    if env_home and is_netlogo_home(env_home):
        return os.path.abspath(os.path.expanduser(env_home))
    homes = [home for home in _candidate_homes() if is_netlogo_home(home)]
    if not homes:
        return None

    def preference(home: str) -> Tuple[bool, Tuple[int, ...]]:
        version = _netlogo_version(home)
        return (bool(version) and version[0] == 6, version)

    return os.path.abspath(max(homes, key=preference))


def _resolve_netlogo_home(netlogo_home: Optional[str]) -> str:
    if netlogo_home:
        home = os.path.abspath(os.path.expanduser(str(netlogo_home)))
        if not is_netlogo_home(home):
            raise NetLogoNotFoundError(
                "No NetLogo installation in '{}' (expected a file {}). Pass the folder "
                "NetLogo is installed in, e.g. 'C:/Program Files/NetLogo 6.2.2', or call "
                "run_netlogo() without netlogo_home to detect it automatically."
                .format(home, os.path.join(_jar_dir(home), "netlogo-<version>.jar")))
        return home
    home = find_netlogo_home()
    if home is None:
        raise NetLogoNotFoundError(
            "NetLogo was not found. Install NetLogo 6 "
            "(https://ccl.northwestern.edu/netlogo/download.shtml), then pass its "
            "folder as netlogo_home=... or set the NETLOGO_HOME environment variable.")
    return home


def _ensure_java(netlogo_home: str) -> None:
    """nl4py starts the command 'java': if it is not on PATH, use the JAVA_HOME
    or the Java runtime bundled with NetLogo."""
    if shutil.which("java"):
        return
    folders = []
    if os.environ.get("JAVA_HOME"):
        folders.append(os.path.join(os.environ["JAVA_HOME"], "bin"))
    for relative in ("runtime/bin", "runtime/Contents/Home/bin", "lib/runtime/bin", "jre/bin"):
        folders.append(os.path.join(netlogo_home, *relative.split("/")))
    for folder in folders:
        if shutil.which("java", path=folder):
            os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
            return
    raise FileNotFoundError(
        "Java was not found. nl4py needs the 'java' command: install a JDK "
        "(e.g. 'conda install openjdk=11') or add Java's bin folder to PATH.")


# ─── NetLogo instances ─────────────────────────────────────────────────────────

class _NetLogoInstance:
    """Wrapper around an nl4py object (GUI app or headless workspace).

    It keeps the nl4py interface (``open_model``, ``command``, ``report``...)
    and makes ``report`` return the raw text of the result, using the JVM's
    character encoding so that accented labels survive the round trip.
    Unknown attributes are forwarded to the wrapped nl4py object.
    """

    headless = False

    def __init__(self, target: Any):
        self._target = target
        self._charset: Optional[str] = None

    @property
    def nl4py_object(self) -> Any:
        """The underlying nl4py object."""
        return self._target

    def open_model(self, path: str) -> None:
        self._target.open_model(path)

    def command(self, command: str) -> None:
        self._target.command(command)

    def report(self, reporter: str) -> str:
        controller = self._controller()
        if controller is None:
            return str(self._target.report(reporter))
        charset = self._jvm_charset()
        result = controller.report(reporter.encode(charset, "replace"))
        if isinstance(result, (bytes, bytearray)):
            return bytes(result).decode(charset, "replace")
        return str(result)

    def close_model(self) -> None:
        self._target.close_model()

    def _controller(self) -> Any:
        return None

    def _jvm_charset(self) -> str:
        """Charset Java uses to turn bytes into text (cp1252 with Java < 18 on Windows)."""
        if self._charset is None:
            charset = "utf-8"
            try:
                name = str(self._target.gateway.jvm.java.nio.charset.Charset.defaultCharset().name())
                codecs.lookup(name)
                charset = name
            except Exception:
                pass
            self._charset = charset
        return self._charset

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") or name in ("_target", "_charset"):
            raise AttributeError(name)
        return getattr(self._target, name)

    def __repr__(self) -> str:
        return "<{}>".format(type(self).__name__)


class NetLogoApp(_NetLogoInstance):
    """The NetLogo application with its window (returned by run_netlogo())."""

    def _controller(self) -> Any:
        return getattr(self._target, "app", None)


class HeadlessNetLogo(_NetLogoInstance):
    """A NetLogo workspace without window, for fast batch runs (run_netlogo(headless=True))."""

    headless = True

    def _controller(self) -> Any:
        # nl4py 0.9 converts every headless result with float(), which fails
        # for lists and text: read the raw result from the controller instead.
        return getattr(self._target, "hwc", None)

    def export_view(self, filename: str) -> None:
        """Save the current view as a PNG image."""
        self._target.export_view(filename)

    def dispose(self) -> None:
        """Free the workspace in Java. It cannot be used afterwards."""
        try:
            _require_nl4py().delete_headless_workspace(self._target)
        except Exception:
            self._target.deleteWorkspace()


def _start_netlogo(netlogo_home: Optional[str], headless: bool) -> Any:
    home = _resolve_netlogo_home(netlogo_home)
    nl = _require_nl4py()
    _ensure_java(home)
    nl.initialize(home)
    if headless:
        return HeadlessNetLogo(nl.create_headless_workspace())
    return NetLogoApp(nl.netlogo_app())


def _resolve_model(path_model: Optional[str]) -> str:
    if not path_model:
        return BASE_MODEL_PATH
    path = os.path.abspath(os.path.expanduser(str(path_model)))
    if not os.path.isfile(path):
        raise FileNotFoundError("NetLogo model not found: '{}'".format(path))
    return path


# ─── Initialisation ────────────────────────────────────────────────────────────

def run_netlogo(netlogo_home: Optional[str] = None, path_model: str = "",
                headless: bool = False, setup: bool = True) -> Any:
    """Start NetLogo, open a model and run its ``setup``. Returns the NetLogo instance.

    netlogo_home : NetLogo folder; detected automatically when omitted
                   (NETLOGO_HOME environment variable, then usual install folders).
    path_model   : .nlogo file to open; the built-in netlogopy model by default.
    headless     : True to run without window (much faster, for batch runs).
    setup        : False to open the model without running ``setup``.
    """
    model = _resolve_model(path_model)
    n = _start_netlogo(netlogo_home, headless)
    n.open_model(model)
    if setup:
        n.command("setup")
    return n


def run_netlogo_base(netlogo_home: Optional[str] = None) -> Any:
    """Start NetLogo with the built-in netlogopy model."""
    return run_netlogo(netlogo_home)


def run_netlogo_model(netlogo_home: Optional[str] = None, path_model: str = "",
                      headless: bool = False) -> Any:
    """
    Start NetLogo and open an *existing* .nlogo model WITHOUT calling setup.
    Use this instead of run_netlogo() when integrating an external model that
    already has its own setup/go procedures.
    """
    return run_netlogo(netlogo_home, path_model, headless=headless, setup=False)


def close_netlogo(n: Any) -> None:
    """Release a NetLogo instance created by run_netlogo().

    The Python agents of `n` are forgotten and a headless workspace is freed.
    The NetLogo window (GUI) stays open until Python exits.
    """
    _forget_instance(n)
    if isinstance(n, HeadlessNetLogo):
        n.dispose()


@contextlib.contextmanager
def netlogo_session(netlogo_home: Optional[str] = None, path_model: str = "",
                    headless: bool = False, setup: bool = True) -> Iterator[Any]:
    """Context manager: ``with netlogo_session(headless=True) as n: ...``

    Same arguments as run_netlogo(); close_netlogo() is called at the end,
    even if an error occurs.
    """
    n = run_netlogo(netlogo_home, path_model, headless=headless, setup=setup)
    try:
        yield n
    finally:
        close_netlogo(n)


def reset_base_file(dest: str) -> None:
    """Copy base.nls to dest folder."""
    shutil.copy2(BASE_NLS_PATH, os.path.join(dest, "base.nls"))


def create_ntlg_file(dest: str) -> None:
    """Copy base.nls as base2.nls to dest folder."""
    shutil.copy2(BASE_NLS_PATH, os.path.join(dest, "base2.nls"))


# ─── Python ⇄ NetLogo values ───────────────────────────────────────────────────

def _nl_escape(text: str) -> str:
    """Escape a Python string for a NetLogo string literal."""
    return (text.replace("\\", "\\\\").replace('"', '\\"')
            .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
            .replace("\t", "\\t"))


def _nl_literal(value: Any) -> str:
    """Write a Python value as NetLogo source code."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + _nl_escape(value) + '"'
    if isinstance(value, numbers.Real):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("NetLogo has no value for {!r}".format(value))
        if isinstance(value, numbers.Integral):
            return str(int(value))
        return repr(number)
    if isinstance(value, (list, tuple)):
        return "[" + " ".join(_nl_literal(item) for item in value) + "]"
    return str(value)


def _nl_number(value: Any) -> str:
    """Like _nl_literal, but a str is passed through unchanged (it was always
    inserted as-is, e.g. set_slider(n, 'speed', '10'))."""
    return value if isinstance(value, str) else _nl_literal(value)


def list2nllist(lis: Sequence[Any]) -> str:
    """Convert a Python list to a NetLogo list literal (strings are quoted and escaped)."""
    return _nl_literal(list(lis))


_NUMBER_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
_ESCAPE_RE = re.compile(r"\\(.)")
_UNESCAPES = {"n": "\n", "t": "\t", "r": "\r"}


def _matching_bracket(text: str, start: int) -> int:
    """Index of the ']' closing the '[' at `start`, or -1."""
    depth, in_string, escaped = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _split_top_level(text: str, separator: Optional[str]) -> List[str]:
    """Split at `separator` (None: whitespace) outside nested lists and strings."""
    parts, current = [], []
    depth, in_string, escaped = 0, False, False
    for char in text:
        if in_string:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        is_separator = char.isspace() if separator is None else char == separator
        if is_separator and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    if separator is None:
        parts = [part for part in parts if part]
    return parts


def _is_netlogo_token(token: str) -> bool:
    token = token.strip()
    return bool(_NUMBER_RE.match(token) or token.lower() in ("true", "false")
                or (len(token) >= 2 and token[0] == token[-1] == '"')
                or (token.startswith("[") and token.endswith("]")))


def _parse_atom(token: str) -> Any:
    text = token.strip()
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if _NUMBER_RE.match(text):
        return float(text)
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return _ESCAPE_RE.sub(lambda m: _UNESCAPES.get(m.group(1), m.group(1)), text[1:-1])
    return text


def _parse_nl_value(result: Any) -> Any:
    """Turn the text nl4py returns into Python: float, bool, str or (nested) list.

    nl4py gives Java's text of a NetLogo value: numbers as '20.0', booleans as
    'true', lists as '[20.0, 5.0]'. NetLogo's own '[20 5]' format is understood too.
    """
    if not isinstance(result, str):
        return result
    text = result.strip()
    if text.startswith("[") and _matching_bracket(text, 0) == len(text) - 1:
        inner = text[1:-1]
        if not inner.strip():
            return []
        parts = _split_top_level(inner, ",")
        if len(parts) == 1:
            words = _split_top_level(inner, None)
            if len(words) > 1 and all(_is_netlogo_token(word) for word in words):
                parts = words
        return [_parse_nl_value(part) for part in parts]
    return _parse_atom(text)


# ─── Calling base.nls reporters ────────────────────────────────────────────────

def _error_message(result: Any, what: str) -> str:
    message = "NetLogo could not evaluate `{}`: {}".format(what, result)
    text = str(result)
    if "Nothing named" in text and "has been defined" in text:
        message += ("\nHint: this procedure comes from netlogopy's base.nls. If you opened "
                    "your own model, copy base.nls next to it with reset_base_file(folder) "
                    "and add  __includes [\"base.nls\"]  at the top of its Code tab.")
    return message


def _report(n: Any, reporter: str, args: Sequence[Any]) -> Any:
    return n.report(reporter + " " + list2nllist(args))


def _void(n: Any, reporter: str, args: Sequence[Any]) -> None:
    """Call a base.nls reporter used as an action (it reports 0 when it succeeds)."""
    result = _report(n, reporter, args)
    try:
        ok = float(result) == 0
    except (TypeError, ValueError):
        ok = False
    if not ok:
        warnings.warn(_error_message(result, reporter), NetLogoWarning, stacklevel=3)


def _as_float(result: Any, what: str) -> float:
    if isinstance(result, bool):
        raise NetLogoError(_error_message(result, what))
    try:
        return float(result)
    except (TypeError, ValueError):
        raise NetLogoError(_error_message(result, what)) from None


def _as_int(result: Any, what: str) -> int:
    return int(_as_float(result, what))


def _as_bool(result: Any, what: str) -> bool:
    if isinstance(result, bool):
        return result
    text = str(result).strip().lower()
    if text in ("true", "false"):
        return text == "true"
    raise NetLogoError(_error_message(result, what))


def _as_list(result: Any, what: str) -> list:
    if isinstance(result, (list, tuple)):
        return list(result)
    value = _parse_nl_value(result)
    if isinstance(value, list):
        return value
    raise NetLogoError(_error_message(result, what))


# ─── Utilities ─────────────────────────────────────────────────────────────────

def de_copy(a: Any) -> Any:
    """Return a deep copy of the object."""
    return copy.deepcopy(a)


def _belongs_to(obj: Any, n: Any) -> bool:
    return n is None or getattr(obj, "n", None) is n


def get_turtle_by_id(turtle_id: int, n: Any = None) -> Optional[Any]:
    """Return the pyturtle with this NetLogo who number (in NetLogo instance `n`, if given)."""
    for t in list_pyturtle:
        if t.id == turtle_id and _belongs_to(t, n):
            return t
    return None


def _forget_instance(n: Any) -> None:
    """Remove the Python agents of NetLogo instance `n` from the global lists."""
    list_pyturtle[:] = [t for t in list_pyturtle if not _belongs_to(t, n)]
    list_street[:] = [s for s in list_street if not _belongs_to(s, n)]


# ─── World ─────────────────────────────────────────────────────────────────────

def run_command(n: Any, command: str) -> None:
    """Execute any NetLogo command string."""
    n.command(command)


def run_commands(n: Any, commands: Iterable[str]) -> None:
    """Execute several NetLogo commands in a single call (faster than a loop)."""
    n.command("\n".join(commands))


def report_value(n: Any, expression: str) -> Any:
    """Evaluate any NetLogo reporter and convert the result to Python
    (float, bool, str or list). Example: report_value(n, '[who] of turtles')."""
    return _parse_nl_value(n.report(expression))


def resize_world(n: Any, x0: int, xf: int, y0: int, yf: int) -> None:
    """Resize the NetLogo world to [x0..xf] × [y0..yf]."""
    _void(n, "resize_world", [x0, xf, y0, yf])


def _image_path(image: str) -> str:
    # NetLogo resolves relative paths from the model's folder: make paths that
    # exist from Python's current folder absolute.
    image = str(image)
    return os.path.abspath(image) if os.path.exists(image) else image


def set_background(n: Any, image: str) -> None:
    """Import an image as the world background."""
    _void(n, "set_background", [_image_path(image)])


def netlogoshow(n: Any, word: Any) -> None:
    """Print a message in the NetLogo console (show)."""
    _void(n, "netlogoshow", [word])


def nl_output_print(n: Any, word: Any) -> None:
    """Print a message in the NetLogo output window."""
    _void(n, "outputprint", [word])


def clear_drawing(n: Any) -> None:
    """Erase all pen traces (clear-drawing)."""
    n.command("clear-drawing")


def clear_all(n: Any) -> None:
    """Full clear-all: remove all agents, patches, links, ticks."""
    n.command("clear-all")
    _forget_instance(n)


def clear_all_turtles(n: Any) -> None:
    """Remove all pyturtles (and their streets) from the world."""
    n.command("ask pyturtles [die]")
    list_pyturtle[:] = [t for t in list_pyturtle if not _belongs_to(t, n)]
    list_street[:] = [s for s in list_street if not _belongs_to(s, n)]


# ── Ticks ──────────────────────────────────────────────────────────────────────

def get_ticks(n: Any) -> int:
    """Return the current tick count."""
    return _as_int(n.report("ticks"), "ticks")


def do_tick(n: Any) -> None:
    """Advance the simulation clock by one tick."""
    n.command("tick")


def reset_ticks(n: Any) -> None:
    """Reset the tick counter to 0."""
    n.command("reset-ticks")


def tick_advance(n: Any, amount: float) -> None:
    """Advance the tick counter by a given amount (can be fractional)."""
    n.command("tick-advance " + _nl_number(amount))


# ── World dimensions ───────────────────────────────────────────────────────────

def get_world_width(n: Any) -> int:
    """Return the width of the world (max-pxcor - min-pxcor + 1)."""
    return _as_int(n.report("world-width"), "world-width")


def get_world_height(n: Any) -> int:
    """Return the height of the world (max-pycor - min-pycor + 1)."""
    return _as_int(n.report("world-height"), "world-height")


def get_max_pxcor(n: Any) -> int:
    """Return the maximum x-coordinate (max-pxcor)."""
    return _as_int(n.report("max-pxcor"), "max-pxcor")


def get_min_pxcor(n: Any) -> int:
    """Return the minimum x-coordinate (min-pxcor)."""
    return _as_int(n.report("min-pxcor"), "min-pxcor")


def get_max_pycor(n: Any) -> int:
    """Return the maximum y-coordinate (max-pycor)."""
    return _as_int(n.report("max-pycor"), "max-pycor")


def get_min_pycor(n: Any) -> int:
    """Return the minimum y-coordinate (min-pycor)."""
    return _as_int(n.report("min-pycor"), "min-pycor")


def get_random_xcor(n: Any) -> float:
    """Return a random x-coordinate inside world bounds."""
    return _as_float(n.report("random-xcor"), "random-xcor")


def get_random_ycor(n: Any) -> float:
    """Return a random y-coordinate inside world bounds."""
    return _as_float(n.report("random-ycor"), "random-ycor")


# ── Patches ────────────────────────────────────────────────────────────────────

def set_patch_color(n: Any, x: int, y: int, color: float) -> None:
    """Set the pcolor of patch (x, y)."""
    _void(n, "set_patch_color_r", [x, y, color])


def get_patch_color(n: Any, x: int, y: int) -> float:
    """Return the pcolor of patch (x, y)."""
    return _as_float(_report(n, "get_patch_color_r", [x, y]), "get_patch_color_r")


# ── Agents ─────────────────────────────────────────────────────────────────────

def getxyturtle(n: Any, turtle_obj: Any) -> list:
    """Return [xcor, ycor] of the turtle."""
    xy = _as_list(_report(n, "getxyturtle", [turtle_obj.id]), "getxyturtle")
    return [_as_float(value, "getxyturtle") for value in xy]


def distancebetween(n: Any, fromm: Any, target: Any) -> float:
    """Return the distance between two turtle objects."""
    return _as_float(_report(n, "distanceto", [fromm.id, target.id]), "distanceto")


def count_pyturtles(n: Any) -> int:
    """Return the number of pyturtles currently in the world."""
    return _as_int(n.report("count pyturtles"), "count pyturtles")


def get_all_pyturtles(n: Any = None) -> List[Any]:
    """Return the pyturtles created from Python (only those of NetLogo instance `n`, if given)."""
    if n is None:
        return list_pyturtle
    return [t for t in list_pyturtle if _belongs_to(t, n)]


def get_all_xy(n: Any) -> Dict[int, Tuple[float, float]]:
    """Positions of all pyturtles in a single call: {who: (x, y)}."""
    what = "positions of pyturtles"
    positions = {}
    for row in _as_list(n.report("[ (list who xcor ycor) ] of pyturtles"), what):
        row = _as_list(row, what)
        positions[_as_int(row[0], what)] = (_as_float(row[1], what), _as_float(row[2], what))
    return positions


def create_pyturtles(n: Any, positions: Iterable[Sequence[float]], shape: str = "car",
                     size_shape: float = 4, color: float = 0,
                     names: Any = None, labelcolor: float = 0,
                     fields: Optional[dict] = None) -> List[Any]:
    """Create one pyturtle per (x, y) position in a single NetLogo call.

    names  : one label for all turtles (str) or one label per turtle (list).
    fields : extra attributes copied onto each Python object.
    Much faster than calling pyturtle(...) in a loop.
    """
    coords = [[x, y] for x, y in positions]
    if not coords:
        return []
    if names is None:
        labels = [""] * len(coords)
    elif isinstance(names, str):
        labels = [names] * len(coords)
    else:
        labels = list(names)
        if len(labels) != len(coords):
            raise ValueError("names must have one label per position")
    result = _report(n, "create-pyturtles-xyid",
                     [coords, shape, size_shape, color, labels, labelcolor])
    ids = _as_list(result, "create-pyturtles-xyid")
    return [pyturtle.from_id(n, _as_int(who, "create-pyturtles-xyid"),
                             fields=copy.deepcopy(fields) if fields else None)
            for who in ids]


# ─── Classes ───────────────────────────────────────────────────────────────────

class turtle:
    """
    Base class representing a NetLogo turtle controlled from Python.
    Do not instantiate directly — use `pyturtle` instead.
    """

    def __init__(self, n: Any, turtle_id: int = 0):
        self.id: int = _as_int(turtle_id, "turtle id")
        self.n = n

    def __repr__(self) -> str:
        return "{}(id={})".format(type(self).__name__, self.id)

    # ── Movement ───────────────────────────────────────────────────────────────

    def fd(self, steps: float = 1) -> None:
        """Move forward `steps` units (forward). Fractions and negative values work."""
        _void(self.n, "fdfd", [self.id, steps])

    def bk(self, steps: float = 1) -> None:
        """Move backward `steps` units (back)."""
        _void(self.n, "bkbk", [self.id, steps])

    def rt(self, angle: float) -> None:
        """Turn right by `angle` degrees (right)."""
        _void(self.n, "rtrt", [self.id, angle])

    def lt(self, angle: float) -> None:
        """Turn left by `angle` degrees (left)."""
        _void(self.n, "ltlt", [self.id, angle])

    def setxy(self, x: float, y: float) -> None:
        """Teleport to coordinates (x, y) — setxy."""
        _void(self.n, "turtle_setxy", [self.id, x, y])

    def set_xcor(self, x: float) -> None:
        """Set the x-coordinate only."""
        _void(self.n, "set_xcor_turtle", [self.id, x])

    def set_ycor(self, y: float) -> None:
        """Set the y-coordinate only."""
        _void(self.n, "set_ycor_turtle", [self.id, y])

    def home(self) -> None:
        """Move to (0, 0) and set heading to 0 (north) — home."""
        _void(self.n, "home_turtle", [self.id])

    def set_random_position(self) -> None:
        """Teleport to a random position inside the world bounds."""
        _void(self.n, "random_pos_turtle", [self.id])

    def can_move(self, distance: float = 1) -> bool:
        """Return True if the turtle can move forward `distance` units (can-move?)."""
        return _as_bool(_report(self.n, "can_move_turtle", [self.id, distance]),
                        "can_move_turtle")

    def move_to(self, target: Any) -> None:
        """Move to the same position as `target` turtle (move-to)."""
        _void(self.n, "moveto", [self.id, target.id])

    def wander(self, steps: float = 1) -> None:
        """Set a random heading then move forward `steps` units."""
        _void(self.n, "wander_turtle", [self.id, steps])

    # ── Heading / orientation ──────────────────────────────────────────────────

    def face_to(self, target: Any) -> None:
        """Face towards another turtle (face)."""
        _void(self.n, "faceto", [self.id, target.id])

    def set_heading(self, angle: float) -> None:
        """Set heading in degrees (0=North, 90=East, 180=South, 270=West)."""
        _void(self.n, "set_heading_turtle", [self.id, angle])

    def get_heading(self) -> float:
        """Return the current heading in degrees."""
        return _as_float(_report(self.n, "get_heading_turtle", [self.id]), "get_heading_turtle")

    def towards_point(self, x: float, y: float) -> float:
        """Return the heading from this turtle towards point (x, y) — towardsxy."""
        return _as_float(_report(self.n, "towards_point_turtle", [self.id, x, y]),
                         "towards_point_turtle")

    # ── Position ───────────────────────────────────────────────────────────────

    def get_xy(self) -> Tuple[float, float]:
        """Return (xcor, ycor) in a single call."""
        x, y = getxyturtle(self.n, self)
        return x, y

    def get_xcor(self) -> float:
        """Return the current x-coordinate."""
        return getxyturtle(self.n, self)[0]

    def get_ycor(self) -> float:
        """Return the current y-coordinate."""
        return getxyturtle(self.n, self)[1]

    def distanceto(self, target: Any) -> float:
        """Return the distance to another turtle (distance)."""
        return _as_float(_report(self.n, "distanceto", [self.id, target.id]), "distanceto")

    def distance_to_point(self, x: float, y: float) -> float:
        """Return the distance from this turtle to point (x, y) — distancexy."""
        return _as_float(_report(self.n, "distance_point_turtle", [self.id, x, y]),
                         "distance_point_turtle")

    def is_alive(self) -> bool:
        """Return True while the turtle exists in NetLogo (False after it died)."""
        return _as_bool(self.n.report("is-turtle? turtle " + _nl_literal(self.id)),
                        "is-turtle?")

    # ── Appearance ─────────────────────────────────────────────────────────────

    def set_shape(self, shape: str) -> None:
        """Change the shape (e.g. 'car', 'default', 'person')."""
        _void(self.n, "set_shape", [self.id, shape])

    def get_shape(self) -> str:
        """Return the current shape name."""
        return str(_report(self.n, "get_shape_turtle", [self.id]))

    def set_color(self, color: float) -> None:
        """Change the color (NetLogo color code, see colors chart)."""
        _void(self.n, "set_color_turtle", [self.id, color])

    def get_color(self) -> float:
        """Return the current color code."""
        return _as_float(_report(self.n, "get_color_turtle", [self.id]), "get_color_turtle")

    def set_size(self, size: float) -> None:
        """Change the size of the turtle."""
        _void(self.n, "set_size_turtle", [self.id, size])

    def get_size(self) -> float:
        """Return the current size."""
        return _as_float(_report(self.n, "get_size_turtle", [self.id]), "get_size_turtle")

    def set_label(self, text: str) -> None:
        """Set the text label displayed on the turtle."""
        _void(self.n, "set_label_turtle", [self.id, str(text)])

    def get_label(self) -> str:
        """Return the current label text."""
        return str(_report(self.n, "get_label_turtle", [self.id]))

    def set_label_color(self, color: float) -> None:
        """Set the color of the label text."""
        _void(self.n, "set_label_color_turtle", [self.id, color])

    def hideturtle(self) -> None:
        """Hide the turtle (hide-turtle)."""
        _void(self.n, "hideturtle", [self.id])

    def showturtle(self) -> None:
        """Make the turtle visible (show-turtle)."""
        _void(self.n, "showturtle", [self.id])

    def dieturtle(self) -> None:
        """Remove the turtle from the world (die). Its streets disappear with it."""
        _void(self.n, "dieturtle", [self.id])
        if self in list_pyturtle:
            list_pyturtle.remove(self)
        list_street[:] = [s for s in list_street
                          if getattr(s, "source", None) is not self
                          and getattr(s, "target", None) is not self]

    # ── Pen ────────────────────────────────────────────────────────────────────

    def pen_down(self) -> None:
        """Activate the pen — trace the path (pen-down)."""
        _void(self.n, "pen_down_turtle", [self.id])

    def pen_up(self) -> None:
        """Deactivate the pen (pen-up)."""
        _void(self.n, "pen_up_turtle", [self.id])

    def pen_erase(self) -> None:
        """Set pen to erase mode — erases as the turtle moves (pen-erase)."""
        _void(self.n, "pen_erase_turtle", [self.id])

    def set_pen_color(self, color: float) -> None:
        """Set the pen color (set pen-color)."""
        _void(self.n, "set_pen_color_turtle", [self.id, color])

    def set_pen_size(self, size: float) -> None:
        """Set the pen line thickness (set pen-size)."""
        _void(self.n, "set_pen_size_turtle", [self.id, size])

    def stamp(self) -> None:
        """Stamp the turtle's shape onto the patches below (stamp)."""
        _void(self.n, "stamp_turtle", [self.id])

    def stamp_erase(self) -> None:
        """Erase the stamp at the turtle's current location (stamp-erase)."""
        _void(self.n, "stamp_erase_turtle", [self.id])

    # ── Patch interaction ──────────────────────────────────────────────────────

    def patch_here_color(self) -> float:
        """Return the pcolor of the patch the turtle is currently on."""
        return _as_float(_report(self.n, "patch_here_color_turtle", [self.id]),
                         "patch_here_color_turtle")

    def set_patch_here_color(self, color: float) -> None:
        """Set the pcolor of the patch the turtle is currently on."""
        _void(self.n, "set_patch_here_color_turtle", [self.id, color])

    # ── Neighborhood ───────────────────────────────────────────────────────────

    def in_radius(self, radius: float) -> List[int]:
        """Return the NetLogo who-numbers of all other turtles within `radius` (in-radius)."""
        result = _as_list(_report(self.n, "in_radius_turtle", [self.id, radius]),
                          "in_radius_turtle")
        return [_as_int(who, "in_radius_turtle") for who in result]

    def turtles_here(self) -> List[int]:
        """Return the who-numbers of all other turtles on the same patch (turtles-here)."""
        result = _as_list(_report(self.n, "turtles_here_turtle", [self.id]),
                          "turtles_here_turtle")
        return [_as_int(who, "turtles_here_turtle") for who in result]


# ─── street ────────────────────────────────────────────────────────────────────

class street:
    """
    Directed link between two pyturtles (NetLogo directed-link-breed).

    Parameters
    ----------
    n          : NetLogo app returned by run_netlogo()
    fromm      : source pyturtle
    too        : target pyturtle
    label      : link label text
    labelcolor : label color code
    color      : link color code
    shape      : link shape name
    thickness  : link line thickness
    """

    def __init__(self, n: Any, fromm: Any, too: Any,
                 label: str = "street", labelcolor: float = 0,
                 color: float = 0, shape: str = "default",
                 thickness: float = 0.5):
        self.n = n
        self.source = fromm
        self.target = too
        expected = "{}_{}".format(fromm.id, too.id)
        result = str(_report(n, "create-street-ft",
                             [fromm.id, too.id, label, labelcolor, color, shape, thickness])).strip()
        if result in ("0", "0.0"):
            warnings.warn("A street from turtle {} to turtle {} already exists; it was "
                          "kept unchanged.".format(fromm.id, too.id), NetLogoWarning, stacklevel=2)
        elif result != expected:
            raise NetLogoError(_error_message(result, "create-street-ft"))
        self.id = expected
        list_street.append(self)

    def __repr__(self) -> str:
        return "street({} -> {})".format(self.source.id, self.target.id)

    def _ask(self, commands: str) -> None:
        self.n.command("ask street {} {} [ {} ]".format(
            _nl_literal(self.source.id), _nl_literal(self.target.id), commands))

    def set_color(self, color: float) -> None:
        """Change the link color."""
        self._ask("set color " + _nl_literal(color))

    def set_label(self, text: str) -> None:
        """Change the link label."""
        self._ask("set label " + _nl_literal(str(text)))

    def set_label_color(self, color: float) -> None:
        """Change the color of the link label."""
        self._ask("set label-color " + _nl_literal(color))

    def set_thickness(self, thickness: float) -> None:
        """Change the line thickness."""
        self._ask("set thickness " + _nl_literal(thickness))

    def set_shape(self, shape: str) -> None:
        """Change the link shape (a link shape defined in the model)."""
        self._ask("set shape " + _nl_literal(shape))

    def hide(self) -> None:
        """Hide the link (hide-link)."""
        self._ask("hide-link")

    def show(self) -> None:
        """Show the link again (show-link)."""
        self._ask("show-link")

    def die(self) -> None:
        """Remove the link from the world."""
        self._ask("die")
        if self in list_street:
            list_street.remove(self)


# ─── UI Widgets ────────────────────────────────────────────────────────────────

def get_slider(n: Any, name: str) -> float:
    """Read the current value of a NetLogo Slider widget (backed by a global)."""
    return _as_float(n.report(name), name)


def set_slider(n: Any, name: str, value: float) -> None:
    """Write a value to a NetLogo Slider widget (backed by a global)."""
    n.command("set {} {}".format(name, _nl_number(value)))


def get_switch(n: Any, name: str) -> bool:
    """Read the current state of a NetLogo Switch widget (backed by a boolean global)."""
    return _as_bool(n.report(name), name)


def set_switch(n: Any, name: str, value: bool) -> None:
    """Set the state of a NetLogo Switch widget."""
    n.command("set {} {}".format(name, _nl_literal(bool(value))))


def get_chooser(n: Any, name: str) -> Any:
    """Read the current value of a NetLogo Chooser widget (backed by a global)."""
    return n.report(name)


def set_chooser(n: Any, name: str, value: Any) -> None:
    """Set the value of a NetLogo Chooser widget."""
    n.command("set {} {}".format(name, _nl_literal(value)))


def get_input_box(n: Any, name: str) -> Any:
    """Read the current value of a NetLogo Input widget (backed by a global)."""
    return n.report(name)


def set_input_box(n: Any, name: str, value: Any) -> None:
    """Set the value of a NetLogo Input widget."""
    n.command("set {} {}".format(name, _nl_literal(value)))


def get_monitor(n: Any, expression: str) -> Any:
    """
    Evaluate any NetLogo reporter expression — equivalent to a Monitor widget.
    Returns the raw text; use report_value() to get Python numbers and lists.
    Examples: get_monitor(n, 'count turtles'), get_monitor(n, 'ticks')
    """
    return n.report(expression)


# ─── External models ───────────────────────────────────────────────────────────

def resize_world_direct(n: Any, x0: int, xf: int, y0: int, yf: int) -> None:
    """
    Resize the world using a direct NetLogo command (no base.nls required).
    Use this with external models that do not include base.nls.
    """
    n.command("resize-world {} {} {} {}".format(*(_nl_number(v) for v in (x0, xf, y0, yf))))


def set_background_direct(n: Any, image: str) -> None:
    """Set background image without relying on base.nls."""
    n.command("import-drawing " + _nl_literal(_image_path(image)))


# ─── Plot widget ────────────────────────────────────────────────────────────────

def set_current_plot(n: Any, plot_name: str) -> None:
    """Activate a plot by name (set-current-plot)."""
    n.command("set-current-plot " + _nl_literal(plot_name))


def set_plot_pen(n: Any, pen_name: str) -> None:
    """Activate a pen in the current plot (set-current-plot-pen)."""
    n.command("set-current-plot-pen " + _nl_literal(pen_name))


def create_plot_pen(n: Any, pen_name: str) -> None:
    """Create a temporary pen in the current plot (create-temporary-plot-pen)."""
    n.command("create-temporary-plot-pen " + _nl_literal(pen_name))


def plot_add(n: Any, value: float) -> None:
    """Add a data point at the current x position, then advance x (plot)."""
    n.command("plot " + _nl_number(value))


def plot_xy(n: Any, x: float, y: float) -> None:
    """Add a data point at explicit (x, y) coordinates (plotxy)."""
    n.command("plotxy {} {}".format(_nl_number(x), _nl_number(y)))


def clear_plot(n: Any) -> None:
    """Clear all data from the current plot (clear-plot)."""
    n.command("clear-plot")


def set_plot_pen_color(n: Any, color: float) -> None:
    """Set the color of the current plot pen (set-plot-pen-color)."""
    n.command("set-plot-pen-color " + _nl_number(color))


def set_plot_pen_mode(n: Any, mode: int) -> None:
    """Set the mode of the current plot pen: 0=line, 1=bar, 2=point (set-plot-pen-mode)."""
    n.command("set-plot-pen-mode " + _nl_number(mode))


def auto_plot_on(n: Any) -> None:
    """Enable automatic plot range adjustment (auto-plot-on)."""
    n.command("auto-plot-on")


def auto_plot_off(n: Any) -> None:
    """Disable automatic plot range adjustment (auto-plot-off)."""
    n.command("auto-plot-off")


def set_plot_x_range(n: Any, x_min: float, x_max: float) -> None:
    """Set the x-axis range of the current plot (set-plot-x-range)."""
    n.command("set-plot-x-range {} {}".format(_nl_number(x_min), _nl_number(x_max)))


def set_plot_y_range(n: Any, y_min: float, y_max: float) -> None:
    """Set the y-axis range of the current plot (set-plot-y-range)."""
    n.command("set-plot-y-range {} {}".format(_nl_number(y_min), _nl_number(y_max)))


# ─── pyturtle ──────────────────────────────────────────────────────────────────

class pyturtle(turtle):
    """
    A Python-controlled NetLogo turtle (pyturtle breed).

    Parameters
    ----------
    n          : NetLogo app returned by run_netlogo()
    x, y       : initial coordinates
    shape      : shape name (default 'car')
    size_shape : size
    color      : NetLogo color code
    name       : label text
    labelcolor : label color code
    fields     : dict of extra attributes to attach to the Python object
    """

    def __init__(self, n: Any, x: float = 0, y: float = 0,
                 shape: str = "car", size_shape: float = 4,
                 color: float = 0, name: str = "zn",
                 labelcolor: float = 0, fields: Optional[dict] = None):
        # create-pyturtle-xyid creates the turtle and reports its who number
        # in one atomic call.
        result = _report(n, "create-pyturtle-xyid",
                         [x, y, shape, size_shape, color, name, labelcolor])
        super().__init__(n, turtle_id=_as_int(result, "create-pyturtle-xyid"))
        if fields:
            self.__dict__.update(fields)
        list_pyturtle.append(self)

    @classmethod
    def from_id(cls, n: Any, turtle_id: int, fields: Optional[dict] = None) -> "pyturtle":
        """Wrap a turtle that already exists in NetLogo (e.g. created by the model's setup)."""
        obj = cls.__new__(cls)
        turtle.__init__(obj, n, turtle_id)
        if fields:
            obj.__dict__.update(fields)
        list_pyturtle.append(obj)
        return obj


# ─── PEP 8 names ───────────────────────────────────────────────────────────────

Turtle = turtle
PyTurtle = pyturtle
Street = street
