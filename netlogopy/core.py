"""The :class:`NetLogo` session: open a model, run NetLogo code, read results.

>>> from netlogopy import NetLogo
>>> with NetLogo("Wolf Sheep Predation.nlogo") as nl:      # headless by default
...     nl.setup()
...     nl.go(100)
...     print(nl.report("count sheep"))

``NetLogo(gui=True)`` opens the NetLogo window instead.  Every NetLogo
primitive stays reachable through :meth:`NetLogo.command` and
:meth:`NetLogo.report`; the other methods are typed shortcuts for them.
"""

import os
import threading
import weakref
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

from . import _java
from .agents import Agent, Link, Patch, Turtle, assignments, variable_name
from .convert import from_java, to_netlogo
from .errors import NetLogoCompileError, NetLogoError, NetLogoRuntimeError

__all__ = ["NetLogo", "Globals", "BUNDLED_MODEL", "BUNDLED_MODEL_NLOGOX", "bundled_model"]

#: The model shipped with netlogopy (pyturtles/streets breeds and demo widgets).
BUNDLED_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlogopy.nlogo")
#: The same model in NetLogo 7's format, used with NetLogo 7 and newer.
BUNDLED_MODEL_NLOGOX = os.path.splitext(BUNDLED_MODEL)[0] + ".nlogox"


def bundled_model(netlogo_version: Optional[str] = None) -> str:
    """Path of the bundled model suited to a NetLogo version (.nlogox from NetLogo 7)."""
    major = _java._version_tuple(netlogo_version)[0] if netlogo_version else 0
    return BUNDLED_MODEL_NLOGOX if major >= 7 else BUNDLED_MODEL

_CACHE_SIZE = 1024          # compiled procedures kept per session
_CACHE_MAX_SOURCE = 4000    # longer code (big literals) is compiled but not cached

PathLike = Union[str, "os.PathLike[str]"]
Agents = Union[str, Agent, Sequence[Agent]]


def _java_message(exc: Any) -> str:
    try:
        message = exc.getMessage()
    except Exception:
        message = None
    return str(message) if message is not None else str(exc)


def _error_from_java(exc: Any, source: Optional[str]) -> NetLogoError:
    message = _java_message(exc)
    class_name = ""
    try:
        class_name = str(exc.getClass().getName())
    except Exception:
        pass
    if message.startswith("Runtime error: "):
        return NetLogoRuntimeError(message[len("Runtime error: "):], source)
    if class_name.endswith("CompilerException"):
        return NetLogoCompileError(message, source)
    return NetLogoRuntimeError(message, source)


def _path(path: PathLike) -> str:
    return os.path.abspath(os.fspath(path))


def headless_forced() -> bool:
    """True when NETLOGOPY_HEADLESS=1: scripts written for the window run without it."""
    return os.environ.get("NETLOGOPY_HEADLESS", "").strip().lower() in ("1", "true", "yes", "on")


def _agentset(agents: Agents) -> str:
    """NetLogo agentset expression for a string, an agent or a list of agents."""
    if isinstance(agents, str):
        return f"({agents})"
    if isinstance(agents, Agent):
        agents = [agents]
    agents = list(agents)
    kinds = {agent.kind for agent in agents}
    if not agents:
        return "no-turtles"
    if len(kinds) > 1:
        raise TypeError("an agentset cannot mix turtles, patches and links")
    primitive = {"turtle": "turtle-set", "patch": "patch-set", "link": "link-set"}[kinds.pop()]
    return f"({primitive} " + " ".join(agent.to_netlogo() for agent in agents) + ")"


def _with(agents: str, where: Optional[str]) -> str:
    return f"({agents}) with [ {where} ]" if where else f"({agents})"


def _named_reporters(reporters: Union[str, Sequence[str], Mapping[str, str]]
                     ) -> Tuple[List[str], List[str]]:
    if isinstance(reporters, str):
        return [reporters], [reporters]
    if isinstance(reporters, Mapping):
        return list(reporters.keys()), list(reporters.values())
    reporters = list(reporters)
    return reporters, reporters


def _table(columns: Dict[str, list], as_dataframe: bool) -> Any:
    if not as_dataframe:
        return columns
    try:
        import pandas
    except ImportError as exc:
        raise ImportError("as_dataframe=True needs pandas: pip install pandas") from exc
    return pandas.DataFrame(columns)


class _BackgroundRun(threading.Thread):
    """Runs a command again and again on a session (see :meth:`NetLogo.start`)."""

    def __init__(self, nl: "NetLogo", command: str, interval: float,
                 max_steps: Optional[int], until: Optional[str]):
        super().__init__(name="netlogopy-run", daemon=True)
        self.nl = nl
        self.command = command
        self.interval = interval
        self.max_steps = max_steps
        self.until = until
        self.steps = 0
        self.error: Optional[BaseException] = None
        self.stop_requested = threading.Event()
        self.resumed = threading.Event()
        self.resumed.set()

    def run(self) -> None:
        try:
            while not self.stop_requested.is_set():
                self.resumed.wait()
                if self.max_steps is not None and self.steps >= self.max_steps:
                    break
                with self.nl._lock:                # a step is never cut by pause()
                    if self.stop_requested.is_set() or not self.resumed.is_set():
                        continue
                    if self.until and self.nl.report(self.until):
                        break
                    self.nl.command(self.command)
                    self.steps += 1
                if self.interval:
                    self.stop_requested.wait(self.interval)
        except BaseException as exc:               # re-raised by stop() / wait()
            self.error = exc


class NetLogo:
    """A NetLogo model running inside this Python process.

    Parameters
    ----------
    model : path of the ``.nlogo`` / ``.nlogox`` file to open
        (default: the model bundled with netlogopy).
    gui : open the NetLogo window (True) or run headless (False, default).
        One window per Python process; any number of headless sessions.
        The environment variable ``NETLOGOPY_HEADLESS=1`` turns every
        window off (to run window scripts in tests, CI or on a server).
    netlogo_home : NetLogo installation folder (default: ``NETLOGO_HOME``,
        else the newest installed NetLogo).
    java_home : Java runtime to use (default: NetLogo's own runtime when
        it is Java 9+, else ``JAVA_HOME``...).
    jvm_args : extra JVM options, e.g. ``["-Xmx8g"]``.
    setup : run the model's ``setup`` procedure right after opening it.
    """

    def __init__(self, model: Optional[PathLike] = None, *, gui: bool = False,
                 netlogo_home: Optional[PathLike] = None, java_home: Optional[PathLike] = None,
                 jvm_args: Sequence[str] = (), setup: bool = False):
        self.gui = bool(gui) and not headless_forced()
        self.model_path: Optional[str] = None
        self._lock = threading.RLock()
        self._cache: "OrderedDict[Tuple[bool, str], Any]" = OrderedDict()
        self._owner: Any = None
        self._singulars: Dict[str, str] = {}
        self._handle: Optional[_java.WorkspaceHandle] = None
        self._runner: Optional[_BackgroundRun] = None
        self.netlogo_home = _java.ensure_jvm(
            os.fspath(netlogo_home) if netlogo_home else None,
            os.fspath(java_home) if java_home else None,
            jvm_args, headless=_java.prefer_headless_jvm(self.gui))
        import jpype
        self._java_exception = jpype.JException
        self._throwable = jpype.JClass("java.lang.Throwable")
        _java.ensure_context_class_loader()
        if self.gui:
            self._app = _java.launch_gui()
            self._ws = self._app.workspace()
            self._handle = _java.WorkspaceHandle(self._ws, app=self._app)
            self._handle.owner = weakref.ref(self)
        else:
            self._app = None
            self._ws = None
        try:
            self.open_model(model if model is not None
                            else bundled_model(_java.jvm_info().get("version")))
            if setup:
                self.setup()
        except BaseException:
            self.close()
            raise

    # ─── life cycle ───────────────────────────────────────────────────────────
    def open_model(self, path: PathLike) -> "NetLogo":
        """Open another model in this session (replaces the current one)."""
        path = _path(path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"NetLogo model not found: {path}")
        self.stop()                                # a background run ends with its model
        with self._lock:
            if self.gui:
                self._check_open()
            elif self.model_path is not None and self.closed:
                raise NetLogoError("this NetLogo session is closed")
            _java.ensure_context_class_loader()
            try:
                if self.gui:
                    _java.open_in_gui(self._app, path)
                else:
                    # A headless workspace opens a single model: use a new one.
                    import jpype
                    workspace = jpype.JClass("org.nlogo.headless.HeadlessWorkspace").newInstance()
                    handle = _java.WorkspaceHandle(workspace)
                    try:
                        _java.call_open(workspace, path)
                    except BaseException:
                        handle.close()
                        raise
                    handle.owner = weakref.ref(self)
                    previous, self._ws, self._handle = self._handle, workspace, handle
                    if previous is not None:
                        previous.close()
            except self._java_exception as exc:
                error = _error_from_java(exc, None)
                raise type(error)(f"cannot open {path}: {error.message}") from None
            self._cache.clear()
            self._singulars.clear()
            self._owner = None
            self.model_path = path
        return self

    def close(self) -> None:
        """Dispose the workspace (closes the window in GUI mode). Idempotent."""
        self._stop_quietly()
        handle, self._handle = self._handle, None
        self._cache.clear()
        if handle is not None:
            handle.close()

    #: Alias kept for code written for nl4py / netlogopy < 1.0.
    close_model = close

    @property
    def closed(self) -> bool:
        return self._handle is None or self._handle.closed

    def __enter__(self) -> "NetLogo":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        mode = "gui" if self.gui else "headless"
        state = "closed" if self.closed else os.path.basename(self.model_path or "")
        return f"<NetLogo {mode} {state!r}>"

    def _check_open(self) -> None:
        if self.closed:
            raise NetLogoError("this NetLogo session is closed")

    # ─── running code ─────────────────────────────────────────────────────────
    def command(self, *commands: str) -> None:
        """Run NetLogo commands in the observer context.

        ``nl.command("setup")``, ``nl.command("crt 10", "ask turtles [ fd 1 ]")``.
        Raises :class:`NetLogoCompileError` or :class:`NetLogoRuntimeError`.
        """
        source = "\n".join(commands)
        if not source.strip():
            return
        with self._lock:
            if self.gui:
                self._gui_command(source)
                return
            procedure = self._compile(source, reporter=False)
            try:
                self._ws.runCompiledCommands(self._job_owner(), procedure)
            except self._java_exception as exc:
                raise _error_from_java(exc, source) from None
            self._raise_logo_exception(source)

    # In the NetLogo window, runtime errors only reach NetLogo's error dialog.
    # Commands therefore run inside `carefully`; on error the message is parked
    # in the plabel of the corner patch, read back, and the plabel restored.
    _GUI_MARK = "__netlogopy_error__"
    _GUI_SINK = "patch min-pxcor min-pycor"

    def _gui_command(self, source: str) -> None:
        self._compile(source, reporter=False)      # compile errors name the user's code
        wrapped = (f"let __netlogopy-plabel [plabel] of {self._GUI_SINK}\n"
                   f"carefully [\n{source}\n] [ ask {self._GUI_SINK} [ set plabel "
                   f"(list {to_netlogo(self._GUI_MARK)} error-message __netlogopy-plabel) ] ]")
        self._run_commands(wrapped, source)
        sink = self.report(f"[plabel] of {self._GUI_SINK}")
        if isinstance(sink, list) and len(sink) == 3 and sink[0] == self._GUI_MARK:
            self._run_commands(f"ask {self._GUI_SINK} [ set plabel item 2 plabel ]", source)
            raise NetLogoRuntimeError(str(sink[1]), source)

    def _run_commands(self, code: str, source: str) -> None:
        procedure = self._compile(code, reporter=False)
        try:
            self._ws.runCompiledCommands(self._job_owner(), procedure)
        except self._java_exception as exc:
            raise _error_from_java(exc, source) from None

    def report(self, reporter: Union[str, Sequence[str]]) -> Any:
        """Evaluate a NetLogo reporter and return its value converted to Python.

        Pass a list of reporters to get a list of values in a single call:
        ``nl.report(["count sheep", "count wolves"])``.
        """
        if isinstance(reporter, str):
            source = reporter
        else:
            reporters = list(reporter)
            if not reporters:
                return []
            source = "(list " + " ".join(f"({r})" for r in reporters) + ")"
        return from_java(self.report_java(source), self)

    def report_java(self, reporter: str) -> Any:
        """Like :meth:`report` but return the raw Java object."""
        with self._lock:
            procedure = self._compile(reporter, reporter=True)
            try:
                result = self._ws.runCompiledReporter(self._job_owner(), procedure)
            except self._java_exception as exc:
                raise _error_from_java(exc, reporter) from None
            self._raise_logo_exception(reporter)
            if isinstance(result, self._throwable):  # error returned as the value
                raise NetLogoRuntimeError(_java_message(result), reporter)
            return result

    def _compile(self, source: str, reporter: bool) -> Any:
        self._check_open()
        key = (reporter, source)
        procedure = self._cache.get(key)
        if procedure is not None:
            self._cache.move_to_end(key)
            return procedure
        _java.ensure_context_class_loader()
        try:
            procedure = (self._ws.compileReporter(source) if reporter
                         else self._ws.compileCommands(source))
        except self._java_exception as exc:
            raise _error_from_java(exc, source) from None
        if len(source) <= _CACHE_MAX_SOURCE:
            self._cache[key] = procedure
            if len(self._cache) > _CACHE_SIZE:
                self._cache.popitem(last=False)
        return procedure

    def _job_owner(self) -> Any:
        if self._owner is None:
            try:
                self._owner = self._ws.defaultOwner()
            except AttributeError:
                import jpype
                owner_class = jpype.JClass("org.nlogo.api.SimpleJobOwner")
                kind = jpype.JClass("org.nlogo.core.AgentKindJ").Observer()
                self._owner = owner_class("netlogopy", self._ws.world().mainRNG(), kind)
        return self._owner

    def _raise_logo_exception(self, source: str) -> None:
        try:
            exc = self._ws.lastLogoException()
        except AttributeError:
            return
        if exc is not None:
            try:
                self._ws.clearLastLogoException()
            except AttributeError:
                pass
            raise NetLogoRuntimeError(_java_message(exc), source)

    # ─── simulation control ───────────────────────────────────────────────────
    def setup(self, command: str = "setup") -> None:
        """Run the model's setup procedure."""
        self.command(command)

    def go(self, times: int = 1, command: str = "go") -> None:
        """Run the model's go procedure ``times`` times (in a single NetLogo call)."""
        times = int(times)
        if times == 1:
            self.command(command)
        elif times > 1:
            self.command(f"repeat {times} [ {command} ]")

    def run_until(self, condition: str, command: str = "go",
                  max_steps: Optional[int] = None) -> int:
        """Run ``command`` until the NetLogo ``condition`` reports true.

        Returns the number of times ``command`` ran.
        """
        steps = 0
        while (max_steps is None or steps < max_steps) and not self.report(condition):
            self.command(command)
            steps += 1
        return steps

    def collect(self, reporters: Union[str, Sequence[str], Mapping[str, str]], steps: int, *,
                command: str = "go", every: int = 1, include_initial: bool = True,
                until: Optional[str] = None, as_dataframe: bool = False) -> Any:
        """Run the model and record reporters over time.

        ``reporters`` is a reporter, a list of reporters, or a dict
        ``{column name: reporter}``.  Runs ``command`` ``steps`` times and
        records the reporters every ``every`` steps (and before the first
        step when ``include_initial``).  Stops early once the ``until``
        reporter is true.  Returns ``{"step": [...], column: [...]}`` or a
        pandas DataFrame.
        """
        names, exprs = _named_reporters(reporters)
        every = max(1, int(every))
        columns: Dict[str, list] = {"step": []}
        columns.update((name, []) for name in names)

        def record(step: int) -> None:
            columns["step"].append(step)
            for name, value in zip(names, self.report(exprs)):
                columns[name].append(value)

        if include_initial:
            record(0)
        done = 0
        while done < steps:
            chunk = min(every, steps - done)
            self.go(chunk, command)
            done += chunk
            record(done)
            if until and self.report(until):
                break
        return _table(columns, as_dataframe)

    def schedule_reporters(self, reporters: Sequence[str], start_at_tick: int = 0,
                           interval_ticks: int = 1, stop_at_tick: int = -1,
                           go_command: str = "go") -> List[List[Any]]:
        """nl4py-compatible: run ``go`` and record ``reporters`` on a tick schedule.

        Records every ``interval_ticks`` ticks from ``start_at_tick`` until
        ``stop_at_tick``; also stops when ``go`` no longer advances the ticks.
        """
        if stop_at_tick is None or stop_at_tick < 0:
            raise ValueError("stop_at_tick must be >= 0")
        results: List[List[Any]] = []
        ticks = self.ticks
        while ticks < stop_at_tick:
            self.command(go_command)
            previous, ticks = ticks, self.ticks
            if ticks >= start_at_tick and (ticks - start_at_tick) % interval_ticks == 0:
                results.append(self.report(list(reporters)))
            if ticks == previous:
                break
        return results

    # --- background runs: start / pause / resume / stop ---------------------------
    def start(self, command: str = "go", *, interval: float = 0.0,
              max_steps: Optional[int] = None, until: Optional[str] = None) -> None:
        """Run ``command`` again and again in the background, like a forever button.

        Python keeps the hand: read reporters, move agents, :meth:`pause`,
        :meth:`resume` and :meth:`stop` while the model runs.  ``interval`` is
        a delay in seconds between two steps; the run ends by itself after
        ``max_steps`` steps or once the NetLogo condition ``until`` is true.
        """
        with self._lock:
            self._check_open()
            if self.running:
                raise NetLogoError("a background run is already active: stop() it first")
            self._runner = _BackgroundRun(self, command, max(0.0, float(interval)), max_steps, until)
            self._runner.start()

    def pause(self) -> None:
        """Suspend the background run (the step in progress finishes first)."""
        runner = self._runner
        if runner is not None:
            runner.resumed.clear()
            with self._lock:                       # wait for the step in progress
                pass

    def resume(self) -> None:
        """Continue a paused background run."""
        runner = self._runner
        if runner is not None:
            runner.resumed.set()

    def stop(self) -> int:
        """End the background run and return how many steps it made.

        Raises the error that interrupted the run, if any.
        """
        runner, self._runner = self._runner, None
        if runner is None:
            return 0
        runner.stop_requested.set()
        runner.resumed.set()
        if runner is not threading.current_thread():
            runner.join()
        if runner.error is not None:
            raise runner.error
        return runner.steps

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for the background run to end by itself; False if ``timeout`` expired first."""
        runner = self._runner
        if runner is None:
            return True
        runner.join(timeout)
        if runner.is_alive():
            return False
        if runner.error is not None:
            self._runner = None
            raise runner.error
        return True

    @property
    def running(self) -> bool:
        """True while a background run is active (paused or not)."""
        runner = self._runner
        return runner is not None and runner.is_alive()

    @property
    def paused(self) -> bool:
        """True while the background run is suspended by :meth:`pause`."""
        runner = self._runner
        return runner is not None and runner.is_alive() and not runner.resumed.is_set()

    @property
    def steps_run(self) -> int:
        """Steps made so far by the current background run."""
        runner = self._runner
        return runner.steps if runner is not None else 0

    def _stop_quietly(self) -> None:
        try:
            self.stop()
        except Exception:                          # closing must not fail on a run's error
            pass

    # ─── ticks ────────────────────────────────────────────────────────────────
    @property
    def ticks(self) -> float:
        """Current tick count (raises NetLogoRuntimeError before reset-ticks)."""
        return self.report("ticks")

    def tick(self) -> None:
        self.command("tick")

    def tick_advance(self, amount: float) -> None:
        self.command(f"tick-advance {to_netlogo(amount)}")

    def reset_ticks(self) -> None:
        self.command("reset-ticks")

    def clear_ticks(self) -> None:
        self.command("clear-ticks")

    # ─── globals and interface widgets ────────────────────────────────────────
    def get_global(self, name: str) -> Any:
        """Value of a global variable or of a slider/switch/chooser/input widget."""
        return self.report(name)

    def set_global(self, name: str, value: Any) -> None:
        """Set a global variable (sliders, switches, choosers and inputs included)."""
        self.command(f"set {name} {to_netlogo(value)}")

    def global_names(self) -> List[str]:
        """Names of the model's globals, interface widgets included (lower case)."""
        import jpype
        names = self._ws.world().program().globals()
        return [str(names.apply(jpype.JInt(i))).lower() for i in range(names.size())]

    @property
    def globals(self) -> "Globals":
        """Dict-like access to globals: ``nl.globals["speed"] = 3``."""
        return Globals(self)

    # ─── world ────────────────────────────────────────────────────────────────
    @property
    def min_pxcor(self) -> int:
        return int(self.report("min-pxcor"))

    @property
    def max_pxcor(self) -> int:
        return int(self.report("max-pxcor"))

    @property
    def min_pycor(self) -> int:
        return int(self.report("min-pycor"))

    @property
    def max_pycor(self) -> int:
        return int(self.report("max-pycor"))

    @property
    def world_width(self) -> int:
        return int(self.report("world-width"))

    @property
    def world_height(self) -> int:
        return int(self.report("world-height"))

    def resize_world(self, min_pxcor: int, max_pxcor: int, min_pycor: int, max_pycor: int) -> None:
        """Change the world size (kills every turtle)."""
        self.command(f"resize-world {int(min_pxcor)} {int(max_pxcor)} {int(min_pycor)} {int(max_pycor)}")

    @property
    def patch_size(self) -> float:
        return self.report("patch-size")

    def set_patch_size(self, size: float) -> None:
        self.command(f"set-patch-size {to_netlogo(size)}")

    @property
    def wrap_x(self) -> bool:
        """True when the world wraps horizontally."""
        return bool(self._ws.world().wrappingAllowedInX())

    @property
    def wrap_y(self) -> bool:
        return bool(self._ws.world().wrappingAllowedInY())

    def set_topology(self, wrap_x: bool, wrap_y: bool) -> None:
        """Choose which edges wrap (torus, box, horizontal or vertical cylinder)."""
        with self._lock:
            self._check_open()
            self._ws.world().changeTopology(bool(wrap_x), bool(wrap_y))

    def random_seed(self, seed: int) -> None:
        """Seed NetLogo's random generator, for reproducible runs."""
        self.command(f"random-seed {int(seed)}")

    def new_seed(self) -> int:
        return int(self.report("new-seed"))

    def clear_all(self) -> None:
        self.command("clear-all")

    def clear_turtles(self) -> None:
        self.command("clear-turtles")

    def clear_patches(self) -> None:
        self.command("clear-patches")

    def clear_links(self) -> None:
        self.command("clear-links")

    def clear_globals(self) -> None:
        self.command("clear-globals")

    def clear_drawing(self) -> None:
        """Erase pen traces, stamps and imported drawings."""
        self.command("clear-drawing")

    def display(self) -> None:
        """Force a view update."""
        self.command("display")

    def no_display(self) -> None:
        """Freeze the view until :meth:`display` (faster GUI runs)."""
        self.command("no-display")

    # ─── agents ───────────────────────────────────────────────────────────────
    def turtle(self, who: int) -> Turtle:
        """Handle on turtle ``who`` (any breed)."""
        return Turtle(self, who)

    def patch(self, x: float, y: float) -> Optional[Patch]:
        """The patch containing point (x, y); None outside a non-wrapping world."""
        if float(x).is_integer() and float(y).is_integer():
            return Patch(self, int(x), int(y))
        return self.report(f"patch {to_netlogo(x)} {to_netlogo(y)}")

    def link(self, end1: Union[Turtle, int], end2: Union[Turtle, int],
             breed: Optional[str] = None) -> Optional[Link]:
        """The link from ``end1`` to ``end2`` (None when there is none)."""
        a = end1.who if isinstance(end1, Turtle) else int(end1)
        b = end2.who if isinstance(end2, Turtle) else int(end2)
        singular = self._link_singular(breed or "links")
        return self.report(f"{singular} {a} {b}")

    def turtles(self, breed: str = "turtles", where: Optional[str] = None) -> List[Turtle]:
        """Turtles of a breed, optionally filtered by a NetLogo condition, sorted by who."""
        return self.report(f"sort {_with(breed, where)}")

    def patches(self, where: Optional[str] = None) -> List[Patch]:
        """Patches (optionally filtered), from the top-left corner, row by row."""
        return self.report(f"sort {_with('patches', where)}")

    def links(self, breed: str = "links", where: Optional[str] = None) -> List[Link]:
        return self.report(f"sort {_with(breed, where)}")

    def count(self, agents: str = "turtles", where: Optional[str] = None) -> int:
        """``count agents with [where]``."""
        return int(self.report(f"count {_with(agents, where)}"))

    def ask(self, agents: Agents, *commands: str) -> None:
        """``ask agents [ commands ]`` -- agents is NetLogo code, an agent or a list of agents."""
        self.command(f"ask {_agentset(agents)} [\n" + "\n".join(commands) + "\n]")

    def of(self, agents: Agents, reporter: str) -> List[Any]:
        """``[reporter] of agents``, in the same (sorted) order as :meth:`turtles`."""
        return self.report(f"map [ __a -> [{reporter}] of __a ] sort {_agentset(agents)}")

    def create_turtles(self, count: int = 1, breed: Optional[str] = None, *,
                       ordered: bool = False, variables: Optional[Dict[str, Any]] = None,
                       **kwargs: Any) -> List[Turtle]:
        """Create turtles and return them.

        ``nl.create_turtles(10, "sheep", color=15, xcor=Code("random-xcor"))``.
        ``ordered=True`` spreads their headings evenly (``create-ordered-turtles``).
        Variables whose name is not a Python identifier go in ``variables``.
        """
        count = int(count)
        if count <= 0:
            return []
        primitive = "create-ordered-" if ordered else "create-"
        values = assignments({**(variables or {}), **kwargs})
        self.command(f"{primitive}{breed or 'turtles'} {count} [ {values} ]")
        return self._newest_turtles(count)

    def _newest_turtles(self, count: int) -> List[Turtle]:
        return self.report(f"sort max-n-of {int(count)} turtles [who]")

    def create_link(self, end1: Union[Turtle, int], end2: Union[Turtle, int], *,
                    directed: Optional[bool] = None, breed: Optional[str] = None,
                    variables: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Link:
        """Create a link between two turtles and return it.

        ``breed`` is the plural link breed name; its directedness is used
        when ``directed`` is not given.
        """
        a = end1 if isinstance(end1, Turtle) else Turtle(self, end1)
        b = end2 if isinstance(end2, Turtle) else Turtle(self, end2)
        breed = breed or "links"
        if directed is None:
            directed = self._link_breed_directed(breed) if breed != "links" else False
        values = assignments({**(variables or {}), **kwargs})
        primitive = f"create-{breed}-{'to' if directed else 'with'}"
        self.command(f"ask {a.to_netlogo()} [ {primitive} (turtle-set {b.to_netlogo()}) [ {values} ] ]")
        link = self.link(a, b, breed) or self.link(b, a, breed)
        if link is None:
            raise NetLogoRuntimeError(f"the {breed} link between {a} and {b} was not created")
        return link

    def _link_singular(self, breed: str, java_breed: Any = None) -> str:
        if breed == "links":
            return "link"
        singular = self._singulars.get(breed)
        if singular is None:
            world = self._ws.world()
            if java_breed is None:
                java_breed = world.getLinkBreed(breed.upper())
                if java_breed is None:
                    raise NetLogoError(f"unknown link breed {breed!r}")
            singular = str(world.getLinkBreedSingular(java_breed)).lower()
            self._singulars[breed] = singular
        return singular

    def _link_breed_directed(self, breed: str) -> bool:
        java_breed = self._ws.world().getLinkBreed(breed.upper())
        if java_breed is None:
            raise NetLogoError(f"unknown link breed {breed!r}")
        return bool(java_breed.isDirected())

    def breeds(self) -> Dict[str, List[str]]:
        """Breeds of the model: ``{"turtles": [...], "links": [...]}`` (plural names)."""
        world = self._ws.world()
        return {"turtles": sorted(str(name).lower() for name in world.breeds().keySet()),
                "links": sorted(str(name).lower() for name in world.linkBreeds().keySet())}

    def shapes(self) -> List[str]:
        """Turtle shapes available in the model."""
        return self.report("shapes")

    def link_shapes(self) -> List[str]:
        return self.report("link-shapes")

    # ─── patches in bulk ──────────────────────────────────────────────────────
    _GRID = ("map [ __y -> map [ __x -> [{var}] of patch __x __y ] "
             "(range min-pxcor (max-pxcor + 1)) ] (range max-pycor (min-pycor - 1) -1)")

    def patch_grid(self, variable: str = "pcolor", *, as_array: bool = False) -> Any:
        """A patch variable for the whole world, as rows from top (max-pycor) to bottom.

        ``grid[row][col]`` is the patch ``(min_pxcor + col, max_pycor - row)``.
        ``as_array=True`` returns a numpy array.
        """
        grid = self.report(self._GRID.format(var=variable_name(variable)))
        if as_array:
            import numpy
            return numpy.array(grid)
        return grid

    def set_patch_grid(self, variable: str, grid: Any) -> None:
        """Set a patch variable from rows laid out like :meth:`patch_grid`."""
        rows = [list(row) for row in (grid.tolist() if hasattr(grid, "tolist") else grid)]
        height, width = self.world_height, self.world_width
        if len(rows) != height or any(len(row) != width for row in rows):
            raise ValueError(f"grid must have {height} rows of {width} values")
        self.command(
            f"(foreach (range max-pycor (min-pycor - 1) -1) {to_netlogo(rows)} [ [__y __row] -> "
            f"(foreach (range min-pxcor (max-pxcor + 1)) __row [ [__x __v] -> "
            f"ask patch __x __y [ set {variable_name(variable)} __v ] ]) ])")

    def diffuse(self, variable: str, rate: float, neighbors: int = 8) -> None:
        """Share ``rate`` of each patch's ``variable`` with its 8 (or 4) neighbors."""
        primitive = "diffuse4" if neighbors == 4 else "diffuse"
        self.command(f"{primitive} {variable_name(variable)} {to_netlogo(rate)}")

    def import_pcolors(self, path: PathLike, rgb: bool = False) -> None:
        """Color the patches from an image."""
        primitive = "import-pcolors-rgb" if rgb else "import-pcolors"
        self.command(f"{primitive} {to_netlogo(_path(path))}")

    def import_drawing(self, path: PathLike) -> None:
        """Show an image in the drawing layer (a background behind the turtles)."""
        self.command(f"import-drawing {to_netlogo(_path(path))}")

    # ─── files ────────────────────────────────────────────────────────────────
    def export_view(self, path: PathLike) -> str:
        """Save an image (PNG) of the view; returns its absolute path."""
        path = _path(path)
        self.command(f"export-view {to_netlogo(path)}")
        return path

    def export_interface(self, path: PathLike) -> str:
        """Save an image of the whole interface (GUI mode only)."""
        if not self.gui:
            raise NetLogoError("export_interface needs the NetLogo window (gui=True)")
        path = _path(path)
        self.command(f"export-interface {to_netlogo(path)}")
        return path

    def export_world(self, path: PathLike) -> str:
        """Save the complete state of the model (CSV)."""
        path = _path(path)
        self.command(f"export-world {to_netlogo(path)}")
        return path

    def import_world(self, path: PathLike) -> None:
        """Restore a state saved by :meth:`export_world`."""
        self.command(f"import-world {to_netlogo(_path(path))}")

    def export_output(self, path: PathLike) -> str:
        path = _path(path)
        self.command(f"export-output {to_netlogo(path)}")
        return path

    def export_plot(self, plot: str, path: PathLike) -> str:
        path = _path(path)
        self.command(f"export-plot {to_netlogo(plot)} {to_netlogo(path)}")
        return path

    def export_all_plots(self, path: PathLike) -> str:
        path = _path(path)
        self.command(f"export-all-plots {to_netlogo(path)}")
        return path

    # ─── output ───────────────────────────────────────────────────────────────
    def show(self, value: Any) -> None:
        """NetLogo ``show`` (command center in the GUI, stdout when headless)."""
        self.command(f"show {to_netlogo(value)}")

    def output_print(self, value: Any) -> None:
        """Print to the model's Output widget."""
        self.command(f"output-print {to_netlogo(value)}")

    def output_show(self, value: Any) -> None:
        self.command(f"output-show {to_netlogo(value)}")

    def output_type(self, value: Any) -> None:
        self.command(f"output-type {to_netlogo(value)}")

    def output_write(self, value: Any) -> None:
        self.command(f"output-write {to_netlogo(value)}")

    def clear_output(self) -> None:
        self.command("clear-output")

    # ─── plots ────────────────────────────────────────────────────────────────
    def _plot_target(self, plot: Optional[str], pen: Optional[str]) -> str:
        parts = []
        if plot is not None:
            parts.append(f"set-current-plot {to_netlogo(plot)}")
        if pen is not None:
            parts.append(f"set-current-plot-pen {to_netlogo(pen)}")
        return " ".join(parts) + (" " if parts else "")

    def set_current_plot(self, plot: str) -> None:
        self.command(f"set-current-plot {to_netlogo(plot)}")

    def set_current_plot_pen(self, pen: str) -> None:
        self.command(f"set-current-plot-pen {to_netlogo(pen)}")

    def create_temporary_plot_pen(self, pen: str) -> None:
        self.command(f"create-temporary-plot-pen {to_netlogo(pen)}")

    def plot(self, y: float, *, plot: Optional[str] = None, pen: Optional[str] = None) -> None:
        """Add a point to the current (or given) plot pen."""
        self.command(self._plot_target(plot, pen) + f"plot {to_netlogo(y)}")

    def plotxy(self, x: float, y: float, *, plot: Optional[str] = None,
               pen: Optional[str] = None) -> None:
        self.command(self._plot_target(plot, pen) + f"plotxy {to_netlogo(x)} {to_netlogo(y)}")

    def histogram(self, values: Union[str, Sequence[float]], *, plot: Optional[str] = None,
                  pen: Optional[str] = None) -> None:
        """Histogram of a list of numbers, or of a NetLogo list reporter."""
        source = values if isinstance(values, str) else to_netlogo(list(values))
        self.command(self._plot_target(plot, pen) + f"histogram {source}")

    def clear_plot(self, plot: Optional[str] = None) -> None:
        self.command(self._plot_target(plot, None) + "clear-plot")

    def clear_all_plots(self) -> None:
        self.command("clear-all-plots")

    def set_plot_pen_color(self, color: Any) -> None:
        self.command(f"set-plot-pen-color {to_netlogo(color)}")

    def set_plot_pen_mode(self, mode: int) -> None:
        """0 = line, 1 = bar, 2 = point."""
        self.command(f"set-plot-pen-mode {int(mode)}")

    def set_plot_pen_interval(self, interval: float) -> None:
        self.command(f"set-plot-pen-interval {to_netlogo(interval)}")

    def plot_pen_down(self) -> None:
        self.command("plot-pen-down")

    def plot_pen_up(self) -> None:
        self.command("plot-pen-up")

    def plot_pen_reset(self) -> None:
        self.command("plot-pen-reset")

    def set_histogram_num_bars(self, bars: int) -> None:
        self.command(f"set-histogram-num-bars {int(bars)}")

    def set_plot_x_range(self, minimum: float, maximum: float) -> None:
        self.command(f"set-plot-x-range {to_netlogo(minimum)} {to_netlogo(maximum)}")

    def set_plot_y_range(self, minimum: float, maximum: float) -> None:
        self.command(f"set-plot-y-range {to_netlogo(minimum)} {to_netlogo(maximum)}")

    def auto_plot_on(self) -> None:
        self.command("auto-plot-on")

    def auto_plot_off(self) -> None:
        self.command("auto-plot-off")

    def setup_plots(self) -> None:
        self.command("setup-plots")

    def update_plots(self) -> None:
        self.command("update-plots")

    # ─── layouts ──────────────────────────────────────────────────────────────
    def layout_circle(self, agents: Agents = "turtles", radius: Optional[float] = None) -> None:
        """Place the agents on a circle around the world center."""
        size = to_netlogo(radius) if radius is not None else \
            "(0.4 * min (list world-width world-height))"
        self.command(f"layout-circle sort {_agentset(agents)} {size}")

    def layout_spring(self, turtles: Agents = "turtles", links: Agents = "links",
                      spring_constant: float = 0.2, spring_length: float = 5,
                      repulsion_constant: float = 1, iterations: int = 1) -> None:
        """Force-directed layout of a network."""
        self.command(f"repeat {int(iterations)} [ layout-spring {_agentset(turtles)} "
                     f"{_agentset(links)} {to_netlogo(spring_constant)} "
                     f"{to_netlogo(spring_length)} {to_netlogo(repulsion_constant)} ]")

    def layout_radial(self, turtles: Agents, links: Agents, root: Turtle) -> None:
        """Tree layout around ``root``."""
        self.command(f"layout-radial {_agentset(turtles)} {_agentset(links)} {root.to_netlogo()}")

    def layout_tutte(self, fixed_turtles: Agents, links: Agents, radius: float) -> None:
        self.command(f"layout-tutte {_agentset(fixed_turtles)} {_agentset(links)} {to_netlogo(radius)}")

    # ─── observer ─────────────────────────────────────────────────────────────
    def watch(self, agent: Agent) -> None:
        self.command(f"watch {agent.to_netlogo()}")

    def follow(self, turtle: Turtle) -> None:
        self.command(f"follow {turtle.to_netlogo()}")

    def ride(self, turtle: Turtle) -> None:
        self.command(f"ride {turtle.to_netlogo()}")

    def reset_perspective(self) -> None:
        self.command("reset-perspective")

    # ─── information ──────────────────────────────────────────────────────────
    @property
    def netlogo_version(self) -> str:
        return self.report("netlogo-version")


class Globals:
    """Dict-like view of a model's globals (interface widgets included)."""

    def __init__(self, nl: NetLogo):
        self._nl = nl

    def __getitem__(self, name: str) -> Any:
        return self._nl.get_global(name)

    def __setitem__(self, name: str, value: Any) -> None:
        self._nl.set_global(name, value)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name.lower() in self._nl.global_names()

    def __iter__(self) -> Iterator[str]:
        return iter(self._nl.global_names())

    def __len__(self) -> int:
        return len(self._nl.global_names())

    def keys(self) -> List[str]:
        return self._nl.global_names()

    def to_dict(self) -> Dict[str, Any]:
        """Every global and its value, read in one NetLogo call."""
        names = self._nl.global_names()
        return dict(zip(names, self._nl.report(names))) if names else {}

    def items(self) -> List[Tuple[str, Any]]:
        return list(self.to_dict().items())

    def __repr__(self) -> str:
        return f"Globals({self.to_dict()!r})"
