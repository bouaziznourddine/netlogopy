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

import math
import os
import threading
import warnings
import weakref
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

from . import _java
from .agents import Agent, Link, Patch, Turtle, assignments, variable_name
from .convert import Code, _c, from_java, to_netlogo
from .errors import NetLogoCompileError, NetLogoError, NetLogoRuntimeError
from .widgets import WidgetsMixin

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


def _java_context(exc: Any, message: str) -> Optional[str]:
    """What NetLogo adds to a runtime error: the agent, the primitive, the calling procedures."""
    try:
        full = str(exc.runtimeErrorMessage())
    except Exception:
        return None
    if full.startswith(message):
        full = full[len(message):]
    lines = [line.strip() for line in full.splitlines()]
    return "\n".join(line for line in lines if line and "__EVALUATOR" not in line) or None


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
    return NetLogoRuntimeError(message, source, _java_context(exc, message))


def _path(path: PathLike) -> str:
    return os.path.abspath(os.fspath(path))


def headless_forced() -> bool:
    """True when NETLOGOPY_HEADLESS=1: scripts written for the window run without it."""
    return os.environ.get("NETLOGOPY_HEADLESS", "").strip().lower() in ("1", "true", "yes", "on")


def _agents(agents: Any) -> Any:
    """NetLogo code (a string) unchanged; an agent or an iterable of agents as a list."""
    if isinstance(agents, str):
        return agents
    if isinstance(agents, Agent):
        return [agents]
    return list(agents)


def _same_session(agents: Sequence[Agent], nl: Any) -> None:
    """Refuse the agents of another session: their numbers would designate other agents here."""
    for agent in agents:
        if agent.nl is not nl:
            raise ValueError(f"{agent!r} belongs to another NetLogo session")


def _who_list(agents: Sequence[Agent]) -> str:
    return "[" + " ".join(str(agent.who) for agent in agents) + "]"


def _xy_list(agents: Sequence[Agent]) -> str:
    return "[" + " ".join(f"[{agent.pxcor} {agent.pycor}]" for agent in agents) + "]"


def _agentset(agents: Agents, empty: str = "no-turtles", nl: Any = None) -> str:
    """NetLogo agentset expression for a string, an agent or a list of agents.

    A list is written as numbers (who numbers, patch coordinates) rather than
    as one expression per agent, so that long lists stay small and fast to
    compile.  ``empty`` is the agentset an empty list stands for.
    """
    agents = _agents(agents)
    if isinstance(agents, str):
        return f"({_c(agents)})"
    if not agents:
        return empty
    kinds = {agent.kind for agent in agents}
    if len(kinds) > 1:
        raise TypeError("an agentset cannot mix turtles, patches and links")
    if nl is not None:
        _same_session(agents, nl)
    kind = kinds.pop()
    if len(agents) <= 4 or kind == "link":
        primitive = {"turtle": "turtle-set", "patch": "patch-set", "link": "link-set"}[kind]
        return f"({primitive} " + " ".join(agent.to_netlogo() for agent in agents) + ")"
    if kind == "turtle":
        return f"(turtle-set map [ __w -> turtle __w ] {_who_list(agents)})"
    return f"(patch-set map [ __p -> patch first __p last __p ] {_xy_list(agents)})"


def _iterate(collection: Any) -> Iterator[Any]:
    """Iterate a Scala collection."""
    iterator = collection.iterator()
    while iterator.hasNext():
        yield iterator.next()


def _with(agents: str, where: Optional[str]) -> str:
    return f"({_c(agents)}) with [ {_c(where)} ]" if where else f"({_c(agents)})"


def _named_reporters(reporters: Union[str, Sequence[str], Mapping[str, str]]
                     ) -> Tuple[List[str], List[str]]:
    if isinstance(reporters, str):
        return [reporters], [reporters]
    if isinstance(reporters, Mapping):
        return list(reporters.keys()), list(reporters.values())
    reporters = list(reporters)
    return reporters, reporters


def _require_pandas() -> Any:
    """pandas, or a clear ImportError: called before a run whose result must be a DataFrame."""
    try:
        import pandas
    except ImportError as exc:
        raise ImportError("as_dataframe=True needs pandas: pip install pandas") from exc
    return pandas


def _table(columns: Dict[str, list], as_dataframe: bool) -> Any:
    if not as_dataframe:
        return columns
    return _require_pandas().DataFrame(columns)


def _dispose_handle(box: List[Any]) -> None:
    """Free the workspace of a headless session that was dropped without ``close()``."""
    handle, box[0] = box[0], None
    if handle is not None:
        handle.close()


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
        self.halted = False                        # set by halt(): the step in progress was cut
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
                    if self.halted:                # an interrupted step is not a step made
                        break
                    self.steps += 1
                if self.interval:
                    self.stop_requested.wait(self.interval)
        except BaseException as exc:               # re-raised by stop() / wait()
            self.error = exc
        finally:
            _java.detach_thread()                  # or the JVM keeps a thread for this one


class NetLogo(WidgetsMixin):
    """A NetLogo model running inside this Python process.

    Parameters
    ----------
    model : str or os.PathLike, optional
        Path of the ``.nlogo`` / ``.nlogox`` file to open (default: the
        model bundled with netlogopy).
    gui : bool, default False
        Open the NetLogo window (True) or run headless (False).  One window
        per Python process; any number of headless sessions.  The
        environment variable ``NETLOGOPY_HEADLESS=1`` turns every window off
        (to run window scripts in tests, CI or on a server).
    netlogo_home : str or os.PathLike, optional
        NetLogo installation folder (default: ``NETLOGO_HOME``, else the
        newest installed NetLogo).
    java_home : str or os.PathLike, optional
        Java runtime to use (default: NetLogo's own runtime when it is
        Java 9+, else ``JAVA_HOME``...).
    jvm_args : sequence of str, optional
        Extra JVM options, e.g. ``["-Xmx8g"]``.
    setup : bool, default False
        Run the model's ``setup`` procedure right after opening it.

    Raises
    ------
    NetLogoNotFoundError
        No NetLogo installation or no suitable Java runtime was found.
    FileNotFoundError
        ``model`` does not exist.

    Examples
    --------
    >>> from netlogopy import NetLogo
    >>> with NetLogo() as nl:                 # bundled model, headless
    ...     nl.command("create-turtles 10")
    ...     nl.report("count turtles")
    10
    """

    def __init__(self, model: Optional[PathLike] = None, *, gui: bool = False,
                 netlogo_home: Optional[PathLike] = None, java_home: Optional[PathLike] = None,
                 jvm_args: Sequence[str] = (), setup: bool = False):
        self.gui = bool(gui) and not headless_forced()
        self.model_path: Optional[str] = None
        if model is not None and not os.path.isfile(_path(model)):
            # Checked before anything starts: a process can open the NetLogo window only once.
            raise FileNotFoundError(f"NetLogo model not found: {_path(model)}")
        self._lock = threading.RLock()
        self._cache: "OrderedDict[Tuple[bool, str], Any]" = OrderedDict()
        self._owner: Any = None
        self._patch_class: Any = None
        self._singulars: Dict[str, str] = {}
        self._alias_clash: Dict[str, bool] = {}    # alias -> the model has a variable spelled so
        self._handle: Optional[_java.WorkspaceHandle] = None
        self._runner: Optional[_BackgroundRun] = None
        self._directory: Optional[str] = None      # set by set_current_directory()
        self._procedures_id = 0                    # identity of the compiled model (window mode)
        self._handle_box: List[Any] = [None]       # the headless workspace, for the finalizer below
        self.netlogo_home = _java.ensure_jvm(
            os.fspath(netlogo_home) if netlogo_home else None,
            os.fspath(java_home) if java_home else None,
            jvm_args, headless=_java.prefer_headless_jvm(self.gui))
        import jpype
        self._java_exception = jpype.JException
        self._throwable = jpype.JClass("java.lang.Throwable")
        self._system = jpype.JClass("java.lang.System")
        _java.ensure_context_class_loader()
        if not self.gui:
            # A session dropped without close() frees its workspace when it is collected.
            weakref.finalize(self, _dispose_handle, self._handle_box)
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
        try:
            self.stop()                            # a background run ends with its model
        except Exception as exc:                   # the error of that run must not keep this model closed
            warnings.warn(f"the background run ended with an error: {exc}", RuntimeWarning, stacklevel=2)
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
                    self._handle_box[0] = handle
                    if previous is not None:
                        previous.close()
            except self._java_exception as exc:
                error = _error_from_java(exc, None)
                raise type(error)(f"cannot open {path}: {error.message}") from None
            self._cache.clear()
            self._singulars.clear()
            self._alias_clash.clear()
            self._owner = None
            self._directory = None
            self._procedures_id = self._procedures_identity()
            self.model_path = path
        return self

    def close(self) -> None:
        """Dispose the workspace (closes the window in GUI mode). Idempotent."""
        self._stop_quietly()
        handle, self._handle = self._handle, None
        self._handle_box[0] = None
        self._cache.clear()
        if handle is not None:
            handle.close()

    #: Alias kept for code written for netlogopy < 1.0.
    close_model = close

    @property
    def closed(self) -> bool:
        """True once the session is closed (:meth:`close` was called or the workspace is gone)."""
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
            reason = getattr(self._handle, "close_reason", None)
            raise NetLogoError("this NetLogo session is closed" + (f": {reason}" if reason else ""))

    def _ref(self, agent: Agent) -> str:
        """NetLogo code designating ``agent``, which must belong to this session."""
        _same_session([agent], self)
        return agent.to_netlogo()

    def _who(self, turtle: Union[Turtle, int]) -> int:
        """Who number of a turtle given as a handle of this session or as a number."""
        if isinstance(turtle, Turtle):
            _same_session([turtle], self)
            return turtle.who
        return int(turtle)

    def _set(self, agents: Agents, empty: str = "no-turtles") -> str:
        """NetLogo agentset for NetLogo code, an agent or a list of agents of this session."""
        return _agentset(agents, empty, self)

    def _procedures_identity(self) -> int:
        """A number that changes when NetLogo recompiles the model."""
        try:
            return int(self._system.identityHashCode(self._ws.procedures()))
        except Exception:
            return 0

    # ─── running code ─────────────────────────────────────────────────────────
    def command(self, *commands: str) -> None:
        """Run NetLogo commands in the observer context.

        Parameters
        ----------
        *commands : str
            NetLogo commands; several arguments are joined by new lines and
            run as one block.

        Raises
        ------
        NetLogoCompileError
            The code does not compile.
        NetLogoRuntimeError
            NetLogo raised an error while running it.

        Examples
        --------
        >>> nl.command("setup")
        >>> nl.command("crt 10", "ask turtles [ fd 1 ]")
        """
        source = "\n".join(commands)
        if not source.strip():
            self._check_open()
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

    # ─── agent variables through NetLogo's Java API ──────────────────────────
    # Reading or writing one variable of one agent does not need NetLogo code:
    # `agent.setVariable(index, value)` is what NetLogo's own `set` runs, with
    # the same checks (colour wrapping, heading, world edges, shapes...).  It
    # avoids compiling a new command for every new value.  Anything else
    # (links, lists, agents as values, an error) goes through NetLogo code.
    _NO_VALUE = object()

    def _java_agent(self, agent: Any) -> Any:
        from .agents import Patch, Turtle
        world = self._ws.world()
        if isinstance(agent, Turtle):
            return world.getTurtle(agent.who)
        if isinstance(agent, Patch):
            if (world.minPxcor() <= agent.pxcor <= world.maxPxcor()
                    and world.minPycor() <= agent.pycor <= world.maxPycor()):
                return world.fastGetPatchAt(agent.pxcor, agent.pycor)
        return None

    def _declares(self, name: str) -> bool:
        """True when the model has an agent variable spelled ``name``."""
        upper, world = name.upper(), self._ws.world()
        try:
            if max(world.turtlesOwnIndexOf(upper), world.patchesOwnIndexOf(upper),
                   world.linksOwnIndexOf(upper)) >= 0:
                return True
            if any(world.breedsOwnIndexOf(breed, upper) >= 0 for breed in world.breeds().values()):
                return True
            return any(world.linkBreedsOwnIndexOf(breed, upper) >= 0
                       for breed in world.linkBreeds().values())
        except Exception:                          # a NetLogo whose API differs: keep the alias
            return False

    def _variable_name(self, name: str) -> str:
        """NetLogo name of an agent variable.

        The Python-friendly aliases (``label_color`` for ``label-color``,
        ``hidden`` for ``hidden?``...) apply unless the model has a variable
        spelled exactly so: that one is then the variable meant.
        """
        alias = variable_name(name)
        if alias == name:
            return name
        clash = self._alias_clash.get(name)
        if clash is None:
            clash = self._alias_clash[name] = self._declares(name)
        return name if clash else alias

    def _variable_index(self, java_agent: Any, name: str) -> int:
        world = self._ws.world()
        upper = self._variable_name(name).upper()
        if isinstance(java_agent, self._java_patch_class()):
            return int(world.patchesOwnIndexOf(upper))
        index = int(world.turtlesOwnIndexOf(upper))
        if index < 0:
            index = int(world.breedsOwnIndexOf(java_agent.getBreed(), upper))
        return index

    def _java_patch_class(self) -> Any:
        if self._patch_class is None:
            import jpype
            self._patch_class = jpype.JClass("org.nlogo.agent.Patch")
        return self._patch_class

    def _fast_get(self, agent: Any, name: str) -> Any:
        """Value of one variable, or _NO_VALUE when NetLogo code is needed."""
        with self._lock:
            self._check_open()
            try:
                java_agent = self._java_agent(agent)
                if java_agent is None:
                    return self._NO_VALUE
                index = self._variable_index(java_agent, name)
                if index < 0:
                    return self._NO_VALUE
                return from_java(java_agent.getVariable(index), self)
            except self._java_exception:
                return self._NO_VALUE

    def _fast_set(self, agent: Any, values: Dict[str, Any]) -> bool:
        """Set simple values (numbers, strings, booleans); False when NetLogo code is needed."""
        import jpype
        converted = []
        for value in values.values():
            if type(value).__module__ == "numpy" and getattr(value, "ndim", 1) == 0:
                value = value.item()               # numpy scalar -> Python number or boolean
            if isinstance(value, bool):
                converted.append(jpype.JObject(value, "java.lang.Boolean"))
            elif isinstance(value, (int, float)) and not isinstance(value, Code):
                try:
                    number = float(value)
                except OverflowError:
                    return False
                if not math.isfinite(number):
                    return False                   # NaN, infinity: NetLogo code refuses them
                converted.append(jpype.JObject(number, "java.lang.Double"))
            elif isinstance(value, str) and not isinstance(value, Code):
                converted.append(jpype.JObject(value, "java.lang.String"))
            else:
                return False
        with self._lock:
            self._check_open()
            try:
                java_agent = self._java_agent(agent)
                if java_agent is None:
                    return False
                indexes = [self._variable_index(java_agent, name) for name in values]
                if min(indexes) < 0:
                    return False
                world = self._ws.world()
                with jpype.synchronized(world):
                    for index, value in zip(indexes, converted):
                        java_agent.setVariable(index, value)
            except self._java_exception:
                return False                       # NetLogo code reports the error
            if self.gui:
                self._ws.requestDisplayUpdate(False)
            return True

    def report(self, reporter: Union[str, Sequence[str]]) -> Any:
        """Evaluate a NetLogo reporter and return its value converted to Python.

        Parameters
        ----------
        reporter : str or sequence of str
            A NetLogo reporter, or a list of reporters evaluated in a single
            NetLogo call.

        Returns
        -------
        Any
            The value converted to Python (numbers, strings, booleans, lists,
            :class:`Turtle`, :class:`Patch`, :class:`Link`...), or a list of
            values when ``reporter`` is a list.

        Raises
        ------
        NetLogoCompileError
            The reporter does not compile.
        NetLogoRuntimeError
            NetLogo raised an error while evaluating it.

        Examples
        --------
        >>> nl.report("count turtles")
        10
        >>> nl.report(["count sheep", "count wolves"])
        [100, 50]
        """
        if isinstance(reporter, str):
            source = reporter
        else:
            reporters = list(reporter)
            if not reporters:
                self._check_open()
                return []
            source = "(list " + " ".join(f"({_c(r)})" for r in reporters) + ")"
        with self._lock:                           # converted before a background run changes the agents
            result = self.report_java(source)
            try:
                return from_java(result, self)
            except self._java_exception as exc:
                raise _error_from_java(exc, source) from None

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
                message = _java_message(result)
                raise NetLogoRuntimeError(message, reporter, _java_context(result, message))
            return result

    def _compile(self, source: str, reporter: bool) -> Any:
        self._check_open()
        if self.gui:
            # The user may have edited the code or the interface in the window:
            # NetLogo then recompiled the model, and what was compiled before
            # would run the old procedures and read the wrong variables.
            identity = self._procedures_identity()
            if identity != self._procedures_id:
                self._procedures_id = identity
                self._cache.clear()
                self._singulars.clear()
                self._alias_clash.clear()
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
            message = _java_message(exc)
            raise NetLogoRuntimeError(message, source, _java_context(exc, message))

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
            self.command(f"repeat {times} [ {_c(command)} ]")

    def run_until(self, condition: str, command: str = "go",
                  max_steps: Optional[int] = None) -> int:
        """Run ``command`` until the NetLogo ``condition`` reports true.

        Parameters
        ----------
        condition : str
            NetLogo reporter checked before each step, e.g. ``"not any? sheep"``.
        command : str, default "go"
            NetLogo commands run at each step.
        max_steps : int, optional
            Stop after this many steps even if ``condition`` is still false.

        Returns
        -------
        int
            The number of times ``command`` ran.
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

        Parameters
        ----------
        reporters : str, sequence of str or mapping
            A reporter, a list of reporters, or a dict
            ``{column name: reporter}``.
        steps : int
            Number of times ``command`` runs.
        command : str, default "go"
            NetLogo commands run at each step.
        every : int, default 1
            Record the reporters every ``every`` steps.
        include_initial : bool, default True
            Also record the reporters before the first step (step 0).
        until : str, optional
            NetLogo reporter tested before each step, as in :meth:`run_until`;
            the run stops once it is true, and the reporters are recorded at
            that step.
        as_dataframe : bool, default False
            Return a pandas DataFrame instead of a dict.

        Returns
        -------
        dict or pandas.DataFrame
            ``{"step": [...], column: [...]}``, one list per reporter.

        Raises
        ------
        ValueError
            Two reporters have the same name, or one is named ``step``.

        Examples
        --------
        >>> nl.setup()
        >>> data = nl.collect({"sheep": "count sheep"}, steps=100, every=10)
        >>> data["step"]
        [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        """
        names, exprs = _named_reporters(reporters)
        if "step" in names:
            raise ValueError('a reporter cannot be named "step": that column holds the step numbers')
        if len(set(names)) != len(names):
            raise ValueError("two reporters have the same name: name the columns with a dict")
        if as_dataframe:
            _require_pandas()                      # before the run, not after it
        every = max(1, int(every))
        steps = int(steps)
        columns: Dict[str, list] = {"step": []}
        columns.update((name, []) for name in names)

        def record(step: int) -> None:
            columns["step"].append(step)
            for name, value in zip(names, self.report(exprs)):
                columns[name].append(value)

        if include_initial:
            record(0)
        done = last = 0
        stopped = False
        while done < steps and not stopped:
            target = min(done + every, steps)
            if not until:
                self.go(target - done, command)
                done = target
            else:
                while done < target:
                    if self.report(until):
                        stopped = True
                        break
                    self.command(command)
                    done += 1
            if done != last:
                record(done)
                last = done
        return _table(columns, as_dataframe)

    def schedule_reporters(self, reporters: Sequence[str], start_at_tick: int = 0,
                           interval_ticks: int = 1, stop_at_tick: int = -1,
                           go_command: str = "go") -> List[List[Any]]:
        """Run ``go`` and record ``reporters`` on a tick schedule.

        Parameters
        ----------
        reporters : sequence of str
            NetLogo reporters recorded together.
        start_at_tick : int, default 0
            The reporters are recorded after a step, when the tick counter is
            ``start_at_tick``, ``start_at_tick + interval_ticks``, and so on.
            The state before the first step is not recorded: with the default
            values the first row is tick 1.
        interval_ticks : int, default 1
            Record every ``interval_ticks`` ticks (``> 0``).
        stop_at_tick : int
            Tick at which the run ends (required, ``>= 0``).  The run also
            ends when ``go`` no longer advances the ticks.
        go_command : str, default "go"
            NetLogo commands run at each step.

        Returns
        -------
        list of list
            One list of reporter values per recorded tick.
        """
        if stop_at_tick is None or stop_at_tick < 0:
            raise ValueError("stop_at_tick must be >= 0")
        if interval_ticks <= 0:
            raise ValueError("interval_ticks must be > 0")
        results: List[List[Any]] = []
        ticks = self.ticks
        while ticks < stop_at_tick:
            self.command(go_command)
            previous, ticks = ticks, self.ticks
            if ticks == previous:                  # go stopped: nothing new to record
                break
            if ticks >= start_at_tick and (ticks - start_at_tick) % interval_ticks == 0:
                results.append(self.report(list(reporters)))
        return results

    # --- background runs: start / pause / resume / stop ---------------------------
    def start(self, command: str = "go", *, interval: float = 0.0,
              max_steps: Optional[int] = None, until: Optional[str] = None) -> None:
        """Run ``command`` again and again in the background, like a forever button.

        Python keeps the hand: read reporters, move agents, :meth:`pause`,
        :meth:`resume` and :meth:`stop` while the model runs.

        Parameters
        ----------
        command : str, default "go"
            NetLogo commands run at each step.
        interval : float, default 0.0
            Delay in seconds between two steps.
        max_steps : int, optional
            The run ends by itself after this many steps.
        until : str, optional
            NetLogo reporter; the run ends by itself once it is true.

        Raises
        ------
        NetLogoError
            A background run is already active.

        See Also
        --------
        wait : wait for the run to end by itself.
        stop : end the run and get the number of steps.
        halt : end the run without waiting for the step in progress.
        """
        with self._lock:
            self._check_open()
            if self.running:
                raise NetLogoError("a background run is already active: stop() it first")
            previous = self._runner
            if previous is not None and previous.error is not None:
                warnings.warn("the previous background run ended with an error that stop() or wait() "
                              f"never reported: {previous.error}", RuntimeWarning, stacklevel=2)
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

    def stop(self, timeout: Optional[float] = None) -> int:
        """End the background run and return how many steps it made.

        The step in progress finishes first.

        Parameters
        ----------
        timeout : float, optional
            Seconds to wait for the step in progress.  When it has not
            finished by then, it is interrupted as by :meth:`halt`.  By
            default ``stop`` waits as long as the step needs.

        Returns
        -------
        int
            Steps made by the run (0 when no run was active).

        Raises
        ------
        Exception
            The error that interrupted the run, if any.
        """
        runner, self._runner = self._runner, None
        if runner is None:
            return 0
        runner.stop_requested.set()
        runner.resumed.set()
        if runner is not threading.current_thread():
            runner.join(timeout)
            if runner.is_alive() and not self._halt_runner(runner):
                self._runner = runner
                raise NetLogoError("NetLogo did not stop: the running code does not respond to halt")
        if runner.error is not None:
            raise runner.error
        return runner.steps

    def halt(self) -> int:
        """Interrupt the NetLogo code that is running, like *Halt* in NetLogo's Tools menu.

        Unlike :meth:`stop`, ``halt`` does not wait for the step in progress
        of a background run: use it for a step that takes too long or never
        ends.  Called from another Python thread, it also interrupts a
        :meth:`command` that does not return.

        Returns
        -------
        int
            Steps completed by the background run (0 when no run was active).

        Raises
        ------
        NetLogoError
            NetLogo did not stop within ten seconds.
        """
        runner, self._runner = self._runner, None
        if runner is None or runner is threading.current_thread():
            self._check_open()
            self._ws.halt()
            return 0
        runner.stop_requested.set()
        runner.resumed.set()
        if not self._halt_runner(runner):
            self._runner = runner
            raise NetLogoError("NetLogo did not stop: the running code does not respond to halt")
        return runner.steps

    def _halt_runner(self, runner: _BackgroundRun, patience: float = 10.0) -> bool:
        """Interrupt the step in progress of ``runner``; True once its thread has ended."""
        runner.halted = True
        waited = 0.0
        while runner.is_alive() and waited < patience:
            try:
                self._ws.halt()
            except Exception:                      # the workspace is being disposed
                pass
            runner.join(0.2)
            waited += 0.2
        return not runner.is_alive()

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
        """End the background run for good: never raises, never waits for an endless step."""
        runner, self._runner = self._runner, None
        if runner is None:
            return
        runner.stop_requested.set()
        runner.resumed.set()
        if runner is not threading.current_thread():
            runner.join(2)
            if runner.is_alive() and self._ws is not None:
                self._halt_runner(runner, patience=5.0)

    # ─── ticks ────────────────────────────────────────────────────────────────
    @property
    def ticks(self) -> float:
        """Current tick count (raises NetLogoRuntimeError before reset-ticks)."""
        return self.report("ticks")

    def tick(self) -> None:
        """Advance the tick counter by one and update the plots (NetLogo ``tick``)."""
        self.command("tick")

    def tick_advance(self, amount: float) -> None:
        """Advance the tick counter by ``amount``, which may be fractional (NetLogo ``tick-advance``)."""
        self.command(f"tick-advance {to_netlogo(amount)}")

    def reset_ticks(self) -> None:
        """Set the tick counter to zero and set up the plots (NetLogo ``reset-ticks``)."""
        self.command("reset-ticks")

    def clear_ticks(self) -> None:
        """Clear the tick counter; ``ticks`` raises until :meth:`reset_ticks` (NetLogo ``clear-ticks``)."""
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
        self._check_open()
        names = self._ws.world().program().globals()
        return [str(names.apply(jpype.JInt(i))).lower() for i in range(names.size())]

    @property
    def globals(self) -> "Globals":
        """Dict-like access to globals: ``nl.globals["speed"] = 3``."""
        return Globals(self)

    # ─── world ────────────────────────────────────────────────────────────────
    @property
    def min_pxcor(self) -> int:
        """Smallest patch x coordinate (NetLogo ``min-pxcor``)."""
        return int(self.report("min-pxcor"))

    @property
    def max_pxcor(self) -> int:
        """Largest patch x coordinate (NetLogo ``max-pxcor``)."""
        return int(self.report("max-pxcor"))

    @property
    def min_pycor(self) -> int:
        """Smallest patch y coordinate (NetLogo ``min-pycor``)."""
        return int(self.report("min-pycor"))

    @property
    def max_pycor(self) -> int:
        """Largest patch y coordinate (NetLogo ``max-pycor``)."""
        return int(self.report("max-pycor"))

    @property
    def world_width(self) -> int:
        """Number of patch columns (NetLogo ``world-width``)."""
        return int(self.report("world-width"))

    @property
    def world_height(self) -> int:
        """Number of patch rows (NetLogo ``world-height``)."""
        return int(self.report("world-height"))

    def resize_world(self, min_pxcor: int, max_pxcor: int, min_pycor: int, max_pycor: int) -> None:
        """Change the world size (kills every turtle)."""
        self.command(f"resize-world {int(min_pxcor)} {int(max_pxcor)} {int(min_pycor)} {int(max_pycor)}")

    @property
    def patch_size(self) -> float:
        """Size of a patch in the view, in pixels (NetLogo ``patch-size``)."""
        return self.report("patch-size")

    def set_patch_size(self, size: float) -> None:
        """Set the size of a patch in the view, in pixels (NetLogo ``set-patch-size``)."""
        self.command(f"set-patch-size {to_netlogo(size)}")

    @property
    def wrap_x(self) -> bool:
        """True when the world wraps horizontally."""
        self._check_open()
        return bool(self._ws.world().wrappingAllowedInX())

    @property
    def wrap_y(self) -> bool:
        """True when the world wraps vertically."""
        self._check_open()
        return bool(self._ws.world().wrappingAllowedInY())

    def set_topology(self, wrap_x: bool, wrap_y: bool) -> None:
        """Choose which edges wrap (torus, box, horizontal or vertical cylinder)."""
        def change() -> None:
            try:
                self._ws.changeTopology(bool(wrap_x), bool(wrap_y))    # the world and the view
            except AttributeError:
                self._ws.world().changeTopology(bool(wrap_x), bool(wrap_y))

        with self._lock:
            self._check_open()
            if self.gui:
                _java.run_on_edt(change)
            else:
                change()

    def random_seed(self, seed: int) -> None:
        """Seed NetLogo's random generator, for reproducible runs."""
        self.command(f"random-seed {int(seed)}")

    def new_seed(self) -> int:
        """A fresh seed for :meth:`random_seed` (NetLogo ``new-seed``)."""
        return int(self.report("new-seed"))

    def clear_all(self) -> None:
        """Reset the whole model: agents, patches, globals, ticks, drawing, plots, output (``clear-all``)."""
        self.command("clear-all")

    def clear_turtles(self) -> None:
        """Kill every turtle (NetLogo ``clear-turtles``)."""
        self.command("clear-turtles")

    def clear_patches(self) -> None:
        """Reset the patch variables to their default values (NetLogo ``clear-patches``)."""
        self.command("clear-patches")

    def clear_links(self) -> None:
        """Kill every link (NetLogo ``clear-links``)."""
        self.command("clear-links")

    def clear_globals(self) -> None:
        """Set the globals declared in the code to 0 (NetLogo ``clear-globals``)."""
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
        """The patch containing point (x, y); None outside a non-wrapping world.

        In a world that wraps, coordinates outside it designate the patch
        they wrap to, as NetLogo's ``patch`` does.
        """
        x, y = float(x), float(y)
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("NetLogo numbers must be finite")
        with self._lock:
            self._check_open()
            try:
                return from_java(self._ws.world().getPatchAt(x, y), self)
            except self._java_exception:           # outside a world that does not wrap
                return None

    def link(self, end1: Union[Turtle, int], end2: Union[Turtle, int],
             breed: Optional[str] = None) -> Optional[Link]:
        """The link from ``end1`` to ``end2`` (None when there is none).

        Without ``breed`` the link may be of any breed: a directed link from
        ``end1`` to ``end2``, or an undirected link between the two.  With
        ``breed`` (plural name, ``"links"`` for links without a breed) only
        that breed is looked at.
        """
        a, b = self._who(end1), self._who(end2)
        if breed is None:
            return self.report(f"ifelse-value (turtle {a} = nobody or turtle {b} = nobody) [ nobody ] "
                               f"[ [out-link-to turtle {b}] of turtle {a} ]")
        return self.report(f"{self._link_singular(breed)} {a} {b}")

    def turtles(self, breed: str = "turtles", where: Optional[str] = None) -> List[Turtle]:
        """Turtles of a breed, optionally filtered by a NetLogo condition, sorted by who."""
        return self.report(f"sort {_with(breed, where)}")

    def patches(self, where: Optional[str] = None) -> List[Patch]:
        """Patches (optionally filtered), from the top-left corner, row by row."""
        return self.report(f"sort {_with('patches', where)}")

    def links(self, breed: str = "links", where: Optional[str] = None) -> List[Link]:
        """Links of a breed, optionally filtered by a NetLogo condition, sorted."""
        return self.report(f"sort {_with(breed, where)}")

    def count(self, agents: str = "turtles", where: Optional[str] = None) -> int:
        """``count agents with [where]``."""
        return int(self.report(f"count {_with(agents, where)}"))

    def ask(self, agents: Agents, *commands: str) -> None:
        """``ask agents [ commands ]`` -- agents is NetLogo code, an agent or a list of agents."""
        agents = _agents(agents)
        if agents == []:
            return                                 # an empty list: nobody to ask
        self.command(f"ask {self._set(agents)} [\n" + "\n".join(commands) + "\n]")

    def of(self, agents: Agents, reporter: str) -> List[Any]:
        """``[reporter] of agents``, as a list.

        For NetLogo code (``"turtles"``, ``"sheep with [energy > 5]"``) the
        values come in the sorted order of :meth:`turtles`.  For a Python list
        of agents they come in the order of the list, one value per agent,
        so that ``zip(agents, nl.of(agents, ...))`` pairs them; the value is
        None for an agent that died.
        """
        agents = _agents(agents)
        body = f"[{_c(reporter)}] of"
        if isinstance(agents, str):
            return self.report(f"map [ __a -> {body} __a ] sort ({_c(agents)})")
        if not agents:
            return []
        _same_session(agents, self)
        kinds = {agent.kind for agent in agents}
        if kinds == {"turtle"}:
            return self.report(f"map [ __w -> ifelse-value (turtle __w = nobody) [ nobody ] "
                               f"[ {body} turtle __w ] ] {_who_list(agents)}")
        if kinds == {"patch"}:
            return self.report(f"map [ __p -> ifelse-value (patch first __p last __p = nobody) [ nobody ] "
                               f"[ {body} patch first __p last __p ] ] {_xy_list(agents)}")
        refs = " ".join(agent.to_netlogo() for agent in agents)
        return self.report(f"map [ __a -> ifelse-value (__a = nobody) [ nobody ] [ {body} __a ] ] (list {refs})")

    def create_turtles(self, count: int = 1, breed: Optional[str] = None, *,
                       ordered: bool = False, variables: Optional[Dict[str, Any]] = None,
                       **kwargs: Any) -> List[Turtle]:
        """Create turtles and return them.

        Parameters
        ----------
        count : int, default 1
            Number of turtles.
        breed : str, optional
            Plural breed name (default: plain turtles).
        ordered : bool, default False
            Spread their headings evenly (``create-ordered-turtles``).
        variables : dict, optional
            Variables whose name is not a Python identifier
            (``{"energy?": True}``).
        **kwargs
            Turtle variables to set, e.g. ``color=15``; use
            :class:`Code` for NetLogo expressions.

        Returns
        -------
        list of Turtle
            The new turtles, sorted by ``who``.

        Examples
        --------
        >>> sheep = nl.create_turtles(10, "sheep", color=15, xcor=Code("random-xcor"))
        """
        count = int(count)
        if count <= 0:
            return []
        primitive = "create-ordered-" if ordered else "create-"
        values = assignments({**(variables or {}), **kwargs}, self._variable_name)
        return self._create(f"{primitive}{breed or 'turtles'} {count} [ {values} ]")

    def _create(self, code: str) -> List[Turtle]:
        """Run ``code``, which creates turtles, and return exactly the turtles it created.

        NetLogo numbers the turtles in the order of their creation: the who
        counter is read before and after the command, under the session lock,
        so the turtles a background run creates are never returned.  When the
        command fails, the turtles it had created are removed before the
        error is raised.
        """
        with self._lock:
            self._check_open()
            world = self._ws.world()
            first, alive = int(world.nextTurtleIndex()), int(world.turtles().count())
            try:
                self.command(code)
            except NetLogoError:
                if int(world.nextTurtleIndex()) > first:
                    self.command(f"ask turtles with [ who >= {first} ] [ die ]")
                raise
            last = int(world.nextTurtleIndex())
            if int(world.turtles().count()) - alive == last - first:
                return [Turtle(self, who) for who in range(first, last)]
            # Some of the new turtles died in their own initialisation.
            return [Turtle(self, who) for who in range(first, last) if world.getTurtle(who) is not None]

    def create_link(self, end1: Union[Turtle, int], end2: Union[Turtle, int], *,
                    directed: Optional[bool] = None, breed: Optional[str] = None,
                    variables: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Link:
        """Create a link between two turtles and return it.

        Parameters
        ----------
        end1, end2 : Turtle or int
            The two turtles (or their ``who`` numbers).
        directed : bool, optional
            Directed link (``create-link-to``) or not; default: the
            directedness of ``breed``, undirected for plain links.
        breed : str, optional
            Plural link breed name.
        variables : dict, optional
            Variables whose name is not a Python identifier.
        **kwargs
            Link variables to set, e.g. ``color=15``.

        Returns
        -------
        Link
            The new link.  When the two turtles already have such a link,
            NetLogo creates nothing and does not set the variables again:
            that link is returned as it is.
        """
        a = end1 if isinstance(end1, Turtle) else Turtle(self, end1)
        b = end2 if isinstance(end2, Turtle) else Turtle(self, end2)
        _same_session([a, b], self)
        breed = breed or "links"
        if directed is None:
            directed = self._link_breed_directed(breed) if breed != "links" else False
        values = assignments({**(variables or {}), **kwargs}, self._variable_name)
        primitive = f"create-{breed}-{'to' if directed else 'with'}"
        with self._lock:                           # creation and lookup are one operation
            self._check_open()
            links = self._ws.world().links()
            before = int(links.count())
            try:
                self.command(f"ask {a.to_netlogo()} [ {primitive} (turtle-set {b.to_netlogo()}) [ {values} ] ]")
            except NetLogoError:
                if int(links.count()) > before:    # created, then its initialisation failed
                    created = self.link(a, b, breed) or self.link(b, a, breed)
                    if created is not None:
                        created.die()
                raise
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
        self._check_open()
        world = self._ws.world()
        return {"turtles": sorted(str(name).lower() for name in world.breeds().keySet()),
                "links": sorted(str(name).lower() for name in world.linkBreeds().keySet())}

    def shapes(self) -> List[str]:
        """Turtle shapes available in the model."""
        return self.report("shapes")

    def link_shapes(self) -> List[str]:
        """Link shapes available in the model (NetLogo ``link-shapes``)."""
        return self.report("link-shapes")

    def import_shapes(self, model: Optional[PathLike] = None, *, overwrite: bool = False) -> List[str]:
        """Copy the turtle and link shapes of another model into this one.

        The copy lasts for the session; the model file is not changed.

        Parameters
        ----------
        model : str or os.PathLike, optional
            Model to copy from (default: the model bundled with netlogopy,
            with car, person_0, machine...).
        overwrite : bool, default False
            Replace the shapes this model already has.

        Returns
        -------
        list of str
            Names of the turtle shapes added.
        """
        added: List[str] = []
        with NetLogo(model, netlogo_home=self.netlogo_home) as source:
            def copy() -> None:
                for kind in ("turtleShapes", "linkShapes"):
                    target = getattr(self._ws.world(), kind)()
                    existing = {str(name) for name in _iterate(target.shapeList().names())}
                    for shape in _iterate(getattr(source._ws.world(), kind)().shapeList().shapes()):
                        name = str(shape.name())
                        if overwrite or name not in existing:
                            target.add(shape)
                            if kind == "turtleShapes":
                                added.append(name)
            if self.gui:
                _java.run_on_edt(copy)
            else:
                copy()
        return sorted(added)

    # ─── patches in bulk ──────────────────────────────────────────────────────
    _GRID = ("map [ __y -> map [ __x -> [{var}] of patch __x __y ] "
             "(range min-pxcor (max-pxcor + 1)) ] (range max-pycor (min-pycor - 1) -1)")

    def patch_grid(self, variable: str = "pcolor", *, as_array: bool = False) -> Any:
        """A patch variable for the whole world, as rows from top (max-pycor) to bottom.

        Parameters
        ----------
        variable : str, default "pcolor"
            Patch variable to read.
        as_array : bool, default False
            Return a numpy array instead of nested lists.

        Returns
        -------
        list of list or numpy.ndarray
            ``grid[row][col]`` is the patch ``(min_pxcor + col, max_pycor - row)``.
        """
        grid = self.report(self._GRID.format(var=self._variable_name(variable)))
        if as_array:
            import numpy
            return numpy.array(grid)
        return grid

    def set_patch_grid(self, variable: str, grid: Any) -> None:
        """Set a patch variable from rows laid out like :meth:`patch_grid`."""
        height, width = self.world_height, self.world_width
        shape = ValueError(f"grid must have {height} rows of {width} values")
        try:
            rows = [list(row) for row in (grid.tolist() if hasattr(grid, "tolist") else grid)]
        except TypeError:                          # e.g. a one-dimensional array
            raise shape from None
        if len(rows) != height or any(len(row) != width for row in rows):
            raise shape
        name = self._variable_name(variable)
        try:
            self.command(
                f"(foreach (range max-pycor (min-pycor - 1) -1) {to_netlogo(rows)} [ [__y __row] -> "
                f"(foreach (range min-pxcor (max-pxcor + 1)) __row [ [__x __v] -> "
                f"ask patch __x __y [ set {name} __v ] ]) ])")
        except NetLogoError as exc:
            if "too large" not in exc.message:
                raise
            # A grid of agents is one NetLogo expression per cell, too many for a
            # single command (nothing ran: it did not compile).  Set it by pieces.
            with self._lock:
                top, left = self.max_pycor, self.min_pxcor
                for index, row in enumerate(rows):
                    for start in range(0, width, 200):
                        cells = row[start:start + 200]
                        self.command(
                            f"(foreach (range {left + start} {left + start + len(cells)}) {to_netlogo(cells)} "
                            f"[ [__x __v] -> ask patch __x {top - index} [ set {name} __v ] ])")

    def diffuse(self, variable: str, rate: float, neighbors: int = 8) -> None:
        """Share ``rate`` of each patch's ``variable`` with its 8 (or 4) neighbors."""
        if neighbors not in (4, 8):
            raise ValueError("neighbors must be 4 or 8")
        primitive = "diffuse4" if neighbors == 4 else "diffuse"
        self.command(f"{primitive} {self._variable_name(variable)} {to_netlogo(rate)}")

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
        """Save the text of the Output widget to a file (``export-output``); returns its absolute path."""
        path = _path(path)
        self.command(f"export-output {to_netlogo(path)}")
        return path

    def export_plot(self, plot: str, path: PathLike) -> str:
        """Save the data of plot ``plot`` as CSV (``export-plot``); returns the absolute path."""
        path = _path(path)
        self.command(f"export-plot {to_netlogo(plot)} {to_netlogo(path)}")
        return path

    def export_all_plots(self, path: PathLike) -> str:
        """Save the data of every plot as CSV (``export-all-plots``); returns the absolute path."""
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
        """Print a value to the Output widget, preceded by ``observer:`` (NetLogo ``output-show``)."""
        self.command(f"output-show {to_netlogo(value)}")

    def output_type(self, value: Any) -> None:
        """Print a value to the Output widget without a new line (NetLogo ``output-type``)."""
        self.command(f"output-type {to_netlogo(value)}")

    def output_write(self, value: Any) -> None:
        """Print a value to the Output widget as NetLogo code, without a new line (NetLogo ``output-write``)."""
        self.command(f"output-write {to_netlogo(value)}")

    def clear_output(self) -> None:
        """Erase the text of the Output widget (NetLogo ``clear-output``)."""
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
        """Choose the plot the next plotting commands act on (NetLogo ``set-current-plot``)."""
        self.command(f"set-current-plot {to_netlogo(plot)}")

    def set_current_plot_pen(self, pen: str) -> None:
        """Choose the pen of the current plot the next commands act on (``set-current-plot-pen``)."""
        self.command(f"set-current-plot-pen {to_netlogo(pen)}")

    def create_temporary_plot_pen(self, pen: str) -> None:
        """Create a pen in the current plot and make it current (``create-temporary-plot-pen``)."""
        self.command(f"create-temporary-plot-pen {to_netlogo(pen)}")

    def plot(self, y: float, *, plot: Optional[str] = None, pen: Optional[str] = None) -> None:
        """Add a point to the current (or given) plot pen."""
        self.command(self._plot_target(plot, pen) + f"plot {to_netlogo(y)}")

    def plotxy(self, x: float, y: float, *, plot: Optional[str] = None,
               pen: Optional[str] = None) -> None:
        """Add the point (x, y) to the current (or given) plot pen (NetLogo ``plotxy``)."""
        self.command(self._plot_target(plot, pen) + f"plotxy {to_netlogo(x)} {to_netlogo(y)}")

    def histogram(self, values: Union[str, Sequence[float]], *, plot: Optional[str] = None,
                  pen: Optional[str] = None) -> None:
        """Histogram of a list of numbers, or of a NetLogo list reporter."""
        source = values if isinstance(values, str) else to_netlogo(list(values))
        self.command(self._plot_target(plot, pen) + f"histogram {source}")

    def clear_plot(self, plot: Optional[str] = None) -> None:
        """Erase the current (or given) plot (NetLogo ``clear-plot``)."""
        self.command(self._plot_target(plot, None) + "clear-plot")

    def clear_all_plots(self) -> None:
        """Erase every plot of the model (NetLogo ``clear-all-plots``)."""
        self.command("clear-all-plots")

    def set_plot_pen_color(self, color: Any) -> None:
        """Set the color of the current plot pen (NetLogo ``set-plot-pen-color``)."""
        self.command(f"set-plot-pen-color {to_netlogo(color)}")

    def set_plot_pen_mode(self, mode: int) -> None:
        """0 = line, 1 = bar, 2 = point."""
        self.command(f"set-plot-pen-mode {int(mode)}")

    def set_plot_pen_interval(self, interval: float) -> None:
        """Set how far ``plot`` moves the current pen along x (NetLogo ``set-plot-pen-interval``)."""
        self.command(f"set-plot-pen-interval {to_netlogo(interval)}")

    def plot_pen_down(self) -> None:
        """Put the current plot pen down, so that it draws (NetLogo ``plot-pen-down``)."""
        self.command("plot-pen-down")

    def plot_pen_up(self) -> None:
        """Lift the current plot pen, so that it stops drawing (NetLogo ``plot-pen-up``)."""
        self.command("plot-pen-up")

    def plot_pen_reset(self) -> None:
        """Erase what the current plot pen drew and reset it (NetLogo ``plot-pen-reset``)."""
        self.command("plot-pen-reset")

    def set_histogram_num_bars(self, bars: int) -> None:
        """Set the number of bars of the current pen's histogram (NetLogo ``set-histogram-num-bars``)."""
        self.command(f"set-histogram-num-bars {int(bars)}")

    def set_plot_x_range(self, minimum: float, maximum: float) -> None:
        """Set the bounds of the x axis of the current plot (NetLogo ``set-plot-x-range``)."""
        self.command(f"set-plot-x-range {to_netlogo(minimum)} {to_netlogo(maximum)}")

    def set_plot_y_range(self, minimum: float, maximum: float) -> None:
        """Set the bounds of the y axis of the current plot (NetLogo ``set-plot-y-range``)."""
        self.command(f"set-plot-y-range {to_netlogo(minimum)} {to_netlogo(maximum)}")

    def auto_plot_on(self) -> None:
        """Let the current plot rescale its axes by itself (NetLogo ``auto-plot-on``)."""
        self.command("auto-plot-on")

    def auto_plot_off(self) -> None:
        """Stop the current plot from rescaling its axes (NetLogo ``auto-plot-off``)."""
        self.command("auto-plot-off")

    @property
    def plot_name(self) -> str:
        """Name of the current plot."""
        return self.report("plot-name")

    def plot_pen_exists(self, name: str) -> bool:
        """True when the current plot has a pen called ``name`` (NetLogo ``plot-pen-exists?``)."""
        return bool(self.report(f"plot-pen-exists? {to_netlogo(name)}"))

    def plot_x_range(self) -> Tuple[float, float]:
        """(minimum, maximum) of the x axis of the current plot."""
        low, high = self.report("(list plot-x-min plot-x-max)")
        return low, high

    def plot_y_range(self) -> Tuple[float, float]:
        """(minimum, maximum) of the y axis of the current plot."""
        low, high = self.report("(list plot-y-min plot-y-max)")
        return low, high

    @property
    def autoplot(self) -> bool:
        """True when the current plot rescales itself (NetLogo 7)."""
        return bool(self.report("autoplot?"))

    def setup_plots(self) -> None:
        """Run the setup code of every plot and pen (NetLogo ``setup-plots``)."""
        self.command("setup-plots")

    def update_plots(self) -> None:
        """Run the update code of every plot and pen (NetLogo ``update-plots``)."""
        self.command("update-plots")

    # ─── layouts ──────────────────────────────────────────────────────────────
    def layout_circle(self, agents: Agents = "turtles", radius: Optional[float] = None) -> None:
        """Place the agents on a circle around the world center.

        A Python list of turtles, or NetLogo code that reports a list, is laid
        out in the order of the list; an agentset is laid out by who number.
        """
        size = to_netlogo(radius) if radius is not None else \
            "(0.4 * min (list world-width world-height))"
        agents = _agents(agents)
        if agents == []:
            return
        if isinstance(agents, str):
            self.command(f"let __agents ({_c(agents)})\n"
                         f"layout-circle (ifelse-value (is-list? __agents) [ __agents ] [ sort __agents ]) {size}")
            return
        _same_session(agents, self)
        if {agent.kind for agent in agents} != {"turtle"}:
            raise TypeError("layout_circle places turtles")
        self.command("layout-circle filter [ __t -> __t != nobody ] "
                     f"map [ __w -> turtle __w ] {_who_list(agents)} {size}")

    def layout_spring(self, turtles: Agents = "turtles", links: Agents = "links",
                      spring_constant: float = 0.2, spring_length: float = 5,
                      repulsion_constant: float = 1, iterations: int = 1) -> None:
        """Force-directed layout of a network."""
        self.command(f"repeat {int(iterations)} [ layout-spring {self._set(turtles)} "
                     f"{self._set(links, 'no-links')} {to_netlogo(spring_constant)} "
                     f"{to_netlogo(spring_length)} {to_netlogo(repulsion_constant)} ]")

    def layout_radial(self, turtles: Agents, links: Agents, root: Turtle) -> None:
        """Tree layout around ``root``."""
        self.command(f"layout-radial {self._set(turtles)} {self._set(links, 'no-links')} {self._ref(root)}")

    def layout_tutte(self, turtles: Optional[Agents] = None, links: Optional[Agents] = None,
                     radius: Optional[float] = None, *, fixed_turtles: Optional[Agents] = None) -> None:
        """Tutte layout of a network (NetLogo ``layout-tutte``).

        Parameters
        ----------
        turtles : str, agent or list of agents
            The turtles the layout moves: each one goes to the centre of the
            turtles it is linked to.  The other turtles of the network are
            spread on the circle and stay there.
        links : str, agent or list of agents
            The links of the network.
        radius : float
            Radius of the circle.
        fixed_turtles : str, agent or list of agents, optional
            Former name of ``turtles``, kept for the scripts that use it.  The
            name was misleading: these are the turtles that move.
        """
        if turtles is None:
            turtles = fixed_turtles
        if turtles is None or links is None or radius is None:
            raise TypeError("layout_tutte() needs turtles, links and radius")
        self.command(f"layout-tutte {self._set(turtles)} {self._set(links, 'no-links')} {to_netlogo(radius)}")

    # ─── observer ─────────────────────────────────────────────────────────────
    def watch(self, agent: Agent) -> None:
        """Put the spotlight on an agent in the view (NetLogo ``watch``)."""
        self.command(f"watch {self._ref(agent)}")

    def follow(self, turtle: Turtle) -> None:
        """Make the observer follow a turtle (NetLogo ``follow``)."""
        self.command(f"follow {self._ref(turtle)}")

    def ride(self, turtle: Turtle) -> None:
        """Make the observer ride a turtle (NetLogo ``ride``)."""
        self.command(f"ride {self._ref(turtle)}")

    def inspect(self, agent: Agent) -> None:
        """Open an agent monitor (in the NetLogo window)."""
        self.command(f"inspect {self._ref(agent)}")

    def stop_inspecting(self, agent: Optional[Agent] = None) -> None:
        """Close the monitor of ``agent``, or the monitors of dead agents."""
        self.command(f"stop-inspecting {self._ref(agent)}" if agent is not None
                     else "stop-inspecting-dead-agents")

    # ─── choosing agents ──────────────────────────────────────────────────────
    # An empty Python list has no kind (turtles, patches or links), so the code
    # about its agents might not compile: the answer is given without NetLogo.
    def any(self, agents: Agents = "turtles", where: Optional[str] = None) -> bool:
        """``any? agents with [where]``."""
        agents = _agents(agents)
        if agents == []:
            return False
        return bool(self.report(f"any? {_with(self._set(agents), where)}"))

    def all(self, agents: Agents, condition: str) -> bool:
        """``all? agents [condition]``."""
        agents = _agents(agents)
        if agents == []:
            return True
        return bool(self.report(f"all? {self._set(agents)} [ {_c(condition)} ]"))

    def one_of(self, agents: Agents = "turtles", where: Optional[str] = None) -> Optional[Agent]:
        """A random agent (None if there is none)."""
        agents = _agents(agents)
        if agents == []:
            return None
        return self.report(f"one-of {_with(self._set(agents), where)}")

    def n_of(self, n: int, agents: Agents = "turtles", where: Optional[str] = None) -> List[Agent]:
        """``n`` random agents, or all of them if there are fewer (``up-to-n-of``)."""
        agents = _agents(agents)
        if agents == []:
            return []
        return self.report(f"[self] of up-to-n-of {int(n)} {_with(self._set(agents), where)}")

    def max_one_of(self, agents: Agents, reporter: str) -> Optional[Agent]:
        """The agent with the highest value of ``reporter``."""
        agents = _agents(agents)
        if agents == []:
            return None
        return self.report(f"max-one-of {self._set(agents)} [ {_c(reporter)} ]")

    def min_one_of(self, agents: Agents, reporter: str) -> Optional[Agent]:
        """The agent with the lowest value of ``reporter``."""
        agents = _agents(agents)
        if agents == []:
            return None
        return self.report(f"min-one-of {self._set(agents)} [ {_c(reporter)} ]")

    def max_n_of(self, n: int, agents: Agents, reporter: str) -> List[Agent]:
        """The ``n`` agents with the highest values, best first."""
        agents = _agents(agents)
        if agents == []:
            return []
        reporter = _c(reporter)
        return self.report(f"sort-on [ (- ({reporter})) ] max-n-of {int(n)} {self._set(agents)} [ {reporter} ]")

    def min_n_of(self, n: int, agents: Agents, reporter: str) -> List[Agent]:
        """The ``n`` agents with the lowest values, lowest first."""
        agents = _agents(agents)
        if agents == []:
            return []
        reporter = _c(reporter)
        return self.report(f"sort-on [ {reporter} ] min-n-of {int(n)} {self._set(agents)} [ {reporter} ]")

    def with_max(self, agents: Agents, reporter: str) -> List[Agent]:
        """Every agent holding the maximum of ``reporter``."""
        agents = _agents(agents)
        if agents == []:
            return []
        return self.report(f"sort {self._set(agents)} with-max [ {_c(reporter)} ]")

    def with_min(self, agents: Agents, reporter: str) -> List[Agent]:
        """Every agent holding the minimum of ``reporter``."""
        agents = _agents(agents)
        if agents == []:
            return []
        return self.report(f"sort {self._set(agents)} with-min [ {_c(reporter)} ]")

    def sort_on(self, agents: Agents, reporter: str) -> List[Agent]:
        """Agents sorted by the value of ``reporter``."""
        agents = _agents(agents)
        if agents == []:
            return []
        return self.report(f"sort-on [ {_c(reporter)} ] {self._set(agents)}")

    def turtles_on(self, agents: Agents, breed: str = "turtles") -> List[Turtle]:
        """Turtles standing on the given patches (or on the patches of the given turtles)."""
        agents = _agents(agents)
        if agents == []:
            return []
        return self.report(f"sort {breed}-on {self._set(agents)}")

    def set_default_shape(self, breed: str, shape: str) -> None:
        """Set the shape given to the new agents of ``breed`` (plural name; NetLogo ``set-default-shape``)."""
        self.command(f"set-default-shape {breed} {to_netlogo(shape)}")

    # ─── random numbers (NetLogo's generator, so runs stay reproducible) ──────
    def random(self, n: int) -> int:
        """Random integer in [0, n)."""
        return int(self.report(f"random {to_netlogo(n)}"))

    def random_float(self, n: float) -> float:
        """Random float in [0, n) (NetLogo ``random-float``)."""
        return self.report(f"random-float {to_netlogo(n)}")

    def random_normal(self, mean: float, standard_deviation: float) -> float:
        """Random float drawn from a normal distribution (NetLogo ``random-normal``)."""
        return self.report(f"random-normal {to_netlogo(mean)} {to_netlogo(standard_deviation)}")

    def random_poisson(self, mean: float) -> int:
        """Random integer drawn from a Poisson distribution (NetLogo ``random-poisson``)."""
        return int(self.report(f"random-poisson {to_netlogo(mean)}"))

    def random_exponential(self, mean: float) -> float:
        """Random float drawn from an exponential distribution (NetLogo ``random-exponential``)."""
        return self.report(f"random-exponential {to_netlogo(mean)}")

    def random_gamma(self, alpha: float, lambda_: float) -> float:
        """Random float drawn from a gamma distribution of parameters alpha and lambda (``random-gamma``)."""
        return self.report(f"random-gamma {to_netlogo(alpha)} {to_netlogo(lambda_)}")

    def random_xcor(self) -> float:
        """Random x coordinate inside the world (NetLogo ``random-xcor``)."""
        return self.report("random-xcor")

    def random_ycor(self) -> float:
        """Random y coordinate inside the world (NetLogo ``random-ycor``)."""
        return self.report("random-ycor")

    def random_pxcor(self) -> int:
        """Random patch x coordinate, an integer (NetLogo ``random-pxcor``)."""
        return int(self.report("random-pxcor"))

    def random_pycor(self) -> int:
        """Random patch y coordinate, an integer (NetLogo ``random-pycor``)."""
        return int(self.report("random-pycor"))

    # ─── colors, angles ───────────────────────────────────────────────────────
    def scale_color(self, color: float, value: float, minimum: float, maximum: float) -> float:
        """Shade of ``color`` proportional to ``value`` between two bounds."""
        return self.report(f"scale-color {to_netlogo(color)} {to_netlogo(value)} "
                           f"{to_netlogo(minimum)} {to_netlogo(maximum)}")

    def shade_of(self, color1: float, color2: float) -> bool:
        """True when the two colors are shades of the same hue (NetLogo ``shade-of?``)."""
        return bool(self.report(f"shade-of? {to_netlogo(color1)} {to_netlogo(color2)}"))

    def wrap_color(self, number: float) -> float:
        """Bring a number into NetLogo's color range, 0 to 140 excluded (NetLogo ``wrap-color``)."""
        return self.report(f"wrap-color {to_netlogo(number)}")

    def extract_rgb(self, color: Any) -> List[float]:
        """``[red, green, blue]`` of a NetLogo color (NetLogo ``extract-rgb``)."""
        return self.report(f"extract-rgb {to_netlogo(color)}")

    def extract_hsb(self, color: Any) -> List[float]:
        """``[hue, saturation, brightness]`` of a NetLogo color (NetLogo ``extract-hsb``)."""
        return self.report(f"extract-hsb {to_netlogo(color)}")

    def approximate_rgb(self, red: float, green: float, blue: float) -> float:
        """NetLogo color number closest to an RGB color."""
        return self.report(f"approximate-rgb {to_netlogo(red)} {to_netlogo(green)} {to_netlogo(blue)}")

    def approximate_hsb(self, hue: float, saturation: float, brightness: float) -> float:
        """NetLogo color number closest to an HSB color (NetLogo ``approximate-hsb``)."""
        return self.report(f"approximate-hsb {to_netlogo(hue)} {to_netlogo(saturation)} "
                           f"{to_netlogo(brightness)}")

    def hsb(self, hue: float, saturation: float, brightness: float) -> List[float]:
        """RGB list of an HSB color."""
        return self.report(f"hsb {to_netlogo(hue)} {to_netlogo(saturation)} {to_netlogo(brightness)}")

    def subtract_headings(self, heading1: float, heading2: float) -> float:
        """Smallest angle from ``heading2`` to ``heading1`` (-180 to 180)."""
        return self.report(f"subtract-headings {to_netlogo(heading1)} {to_netlogo(heading2)}")

    # ─── timer, clock, sound ──────────────────────────────────────────────────
    def reset_timer(self) -> None:
        """Set NetLogo's timer back to zero (NetLogo ``reset-timer``)."""
        self.command("reset-timer")

    @property
    def timer(self) -> float:
        """Seconds since ``reset_timer()`` (or since NetLogo started)."""
        return self.report("timer")

    def date_and_time(self) -> str:
        """Current date and time as a string (NetLogo ``date-and-time``)."""
        return self.report("date-and-time")

    def beep(self) -> None:
        """Emit a beep (NetLogo ``beep``)."""
        self.command("beep")

    # ─── files read and written by NetLogo ────────────────────────────────────
    def _file_path(self, path: PathLike) -> str:
        """Absolute path for ``file_open``, ``file_delete`` and ``file_exists``.

        A relative path starts from the folder given to
        :meth:`set_current_directory`, as in NetLogo; from Python's working
        folder when that method was not called.
        """
        path = os.fspath(path)
        if self._directory is not None and not os.path.isabs(path):
            path = os.path.join(self._directory, path)
        return os.path.abspath(path)

    def file_open(self, path: PathLike) -> None:
        """Open a file for the ``file_*`` methods, reading or writing (NetLogo ``file-open``)."""
        self.command(f"file-open {to_netlogo(self._file_path(path))}")

    def file_close(self) -> None:
        """Close the current file (NetLogo ``file-close``)."""
        self.command("file-close")

    def file_close_all(self) -> None:
        """Close every file opened by NetLogo (NetLogo ``file-close-all``)."""
        self.command("file-close-all")

    def file_flush(self) -> None:
        """Write the pending output of the open files to disk (NetLogo ``file-flush``)."""
        self.command("file-flush")

    def file_delete(self, path: PathLike) -> None:
        """Delete a file (NetLogo ``file-delete``)."""
        self.command(f"file-delete {to_netlogo(self._file_path(path))}")

    def file_exists(self, path: PathLike) -> bool:
        """True when the file exists (NetLogo ``file-exists?``)."""
        return bool(self.report(f"file-exists? {to_netlogo(self._file_path(path))}"))

    def file_print(self, value: Any) -> None:
        """Write a value and a new line to the open file (NetLogo ``file-print``)."""
        self.command(f"file-print {to_netlogo(value)}")

    def file_show(self, value: Any) -> None:
        """Write a value to the open file, preceded by ``observer:`` (NetLogo ``file-show``)."""
        self.command(f"file-show {to_netlogo(value)}")

    def file_type(self, value: Any) -> None:
        """Write a value to the open file without a new line (NetLogo ``file-type``)."""
        self.command(f"file-type {to_netlogo(value)}")

    def file_write(self, value: Any) -> None:
        """Write a value to the open file as NetLogo code, readable by :meth:`file_read` (``file-write``)."""
        self.command(f"file-write {to_netlogo(value)}")

    def file_read(self) -> Any:
        """Next NetLogo value of the open file."""
        return self.report("file-read")

    def file_read_line(self) -> str:
        """Next line of the open file (NetLogo ``file-read-line``)."""
        return self.report("file-read-line")

    def file_read_characters(self, count: int) -> str:
        """Next ``count`` characters of the open file (NetLogo ``file-read-characters``)."""
        return self.report(f"file-read-characters {int(count)}")

    @property
    def file_at_end(self) -> bool:
        """True when the open file has nothing left to read (NetLogo ``file-at-end?``)."""
        return bool(self.report("file-at-end?"))

    def set_current_directory(self, path: PathLike) -> None:
        """Set the folder of relative file names (NetLogo ``set-current-directory``).

        It is used by NetLogo's ``file-open``, ``file-delete`` and
        ``file-exists?``, and by :meth:`file_open`, :meth:`file_delete` and
        :meth:`file_exists`.
        """
        path = _path(path)
        self.command(f"set-current-directory {to_netlogo(path)}")
        self._directory = path

    # ─── mouse and dialogs (NetLogo window) ───────────────────────────────────
    @property
    def mouse_down(self) -> bool:
        """True while the mouse button is down in the view (NetLogo ``mouse-down?``)."""
        return bool(self.report("mouse-down?"))

    @property
    def mouse_inside(self) -> bool:
        """True while the mouse pointer is inside the view (NetLogo ``mouse-inside?``)."""
        return bool(self.report("mouse-inside?"))

    @property
    def mouse_xcor(self) -> float:
        """x coordinate of the mouse in the view (NetLogo ``mouse-xcor``)."""
        return self.report("mouse-xcor")

    @property
    def mouse_ycor(self) -> float:
        """y coordinate of the mouse in the view (NetLogo ``mouse-ycor``)."""
        return self.report("mouse-ycor")

    def user_message(self, message: Any) -> None:
        """Show a message box and wait for OK."""
        self.command(f"user-message {to_netlogo(message)}")

    def user_input(self, message: Any) -> str:
        """Ask the user for a text in a dialog and return it (NetLogo ``user-input``)."""
        return self.report(f"user-input {to_netlogo(message)}")

    def user_yes_or_no(self, message: Any) -> bool:
        """Ask the user a yes/no question; True for yes (NetLogo ``user-yes-or-no?``)."""
        return bool(self.report(f"user-yes-or-no? {to_netlogo(message)}"))

    def user_one_of(self, message: Any, choices: Sequence[Any]) -> Any:
        """Ask the user to pick one of ``choices`` and return it (NetLogo ``user-one-of``)."""
        return self.report(f"user-one-of {to_netlogo(message)} {to_netlogo(list(choices))}")

    def user_file(self) -> Optional[str]:
        """Ask for an existing file; None if the user cancels."""
        return self.report("user-file") or None

    def user_new_file(self) -> Optional[str]:
        """Ask for the name of a new file; None if the user cancels."""
        return self.report("user-new-file") or None

    def user_directory(self) -> Optional[str]:
        """Ask for a folder; None if the user cancels."""
        return self.report("user-directory") or None

    def reset_perspective(self) -> None:
        """Stop watching, following or riding: the observer looks at the world center again (``reset-perspective``)."""
        self.command("reset-perspective")

    # ─── information ──────────────────────────────────────────────────────────
    @property
    def netlogo_version(self) -> str:
        """Version of the running NetLogo, e.g. ``'6.3.0'`` (NetLogo ``netlogo-version``)."""
        return self.report("netlogo-version")


class Globals:
    """Dict-like view of a model's globals (interface widgets included)."""

    def __init__(self, nl: NetLogo):
        self._nl = nl

    def __getitem__(self, name: str) -> Any:
        try:
            return self._nl.get_global(name)
        except NetLogoCompileError:
            if name not in self:                   # like a dict: an unknown name is a KeyError
                raise KeyError(name) from None
            raise

    def __setitem__(self, name: str, value: Any) -> None:
        try:
            self._nl.set_global(name, value)
        except NetLogoCompileError:
            if name not in self:
                raise KeyError(name) from None
            raise

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name.lower() in self._nl.global_names()

    def __iter__(self) -> Iterator[str]:
        return iter(self._nl.global_names())

    def __len__(self) -> int:
        return len(self._nl.global_names())

    def keys(self) -> List[str]:
        """Names of the globals (lower case)."""
        return self._nl.global_names()

    def to_dict(self) -> Dict[str, Any]:
        """Every global and its value, read in one NetLogo call."""
        names = self._nl.global_names()
        return dict(zip(names, self._nl.report(names))) if names else {}

    def items(self) -> List[Tuple[str, Any]]:
        """``(name, value)`` pairs of every global."""
        return list(self.to_dict().items())

    def __repr__(self) -> str:
        return f"Globals({self.to_dict()!r})"
