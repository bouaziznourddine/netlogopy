"""Parameter sweeps over a NetLogo model (like BehaviorSpace), optionally in parallel.

>>> from netlogopy import run_experiment
>>> rows = run_experiment(
...     "Fire.nlogo",
...     parameters={"density": [50, 60, 70]},
...     reporters={"burned": "burned-trees"},
...     repetitions=5, steps=500, until="not any? turtles", workers=4)
"""

import itertools
import queue
import threading
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

from . import _java
from .core import NetLogo, PathLike, _named_reporters, _require_pandas
from .errors import NetLogoError

__all__ = ["run_experiment", "parameter_grid"]

Parameters = Union[None, Mapping[str, Any], Sequence[Mapping[str, Any]]]

#: Columns that run_experiment adds to every row.
_RESERVED = ("run", "repetition", "step")


class _Cancelled(Exception):
    """Raised inside a run when another run of the sweep has failed."""


def _choices(value: Any) -> List[Any]:
    """The values to try for one parameter: the items of any collection, else the value itself."""
    if isinstance(value, (str, bytes, bytearray, Mapping)):
        return [value]
    if hasattr(value, "tolist"):           # numpy array or scalar, pandas Series
        value = value.tolist()
        return value if isinstance(value, list) else [value]
    try:
        return list(value)
    except TypeError:                      # a number, a boolean...
        return [value]


def parameter_grid(parameters: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Every combination of the parameter values.

    A list, tuple, range, set, numpy array or any other collection gives the
    values to try; a single value (a number, a string...) counts as one choice.

    >>> parameter_grid({"a": [1, 2], "b": True})
    [{'a': 1, 'b': True}, {'a': 2, 'b': True}]
    """
    names = list(parameters)
    choices = [_choices(value) for value in parameters.values()]
    return [dict(zip(names, combination)) for combination in itertools.product(*choices)]


def run_experiment(model: PathLike, parameters: Parameters = None,
                   reporters: Union[str, Sequence[str], Mapping[str, str]] = "count turtles", *,
                   steps: int = 100, repetitions: int = 1, setup: str = "setup", go: str = "go",
                   every: Optional[int] = None, until: Optional[str] = None,
                   seed: Optional[int] = None, workers: int = 1,
                   netlogo_home: Optional[PathLike] = None, java_home: Optional[PathLike] = None,
                   jvm_args: Sequence[str] = (), as_dataframe: bool = False,
                   progress: Optional[Callable[[int, int], None]] = None) -> Any:
    """Run ``model`` for every parameter combination and repetition (headless).

    Parameters
    ----------
    model : str or os.PathLike
        The ``.nlogo`` / ``.nlogox`` file.
    parameters : mapping or sequence of mapping, optional
        ``{"global": [values...]}`` (every combination is run, see
        :func:`parameter_grid`) or an explicit list of ``{"global": value}``
        dicts.  Globals are set before ``setup`` runs.  In an explicit list, a
        global that a dict does not name keeps the value it has in the model.
    reporters : str, sequence of str or mapping, default "count turtles"
        A reporter, a list of reporters, or ``{column: reporter}``.
    steps : int, default 100
        Maximum number of ``go`` per run.
    repetitions : int, default 1
        Runs per parameter combination.
    setup, go : str
        Setup and step commands (default: ``"setup"`` and ``"go"``).
    every : int, optional
        Record the reporters every ``every`` steps (and at step 0); ``None``
        records only the final values.
    until : str, optional
        NetLogo condition that ends a run early (e.g. ``"not any? turtles"``),
        tested before each step.
    seed : int, optional
        Runs use ``random-seed seed + run - 1`` for reproducible results.
    workers : int, default 1
        NetLogo workspaces running in parallel threads.
    netlogo_home, java_home, jvm_args
        As for :class:`NetLogo`.
    as_dataframe : bool, default False
        Return a pandas DataFrame instead of a list of dicts.
    progress : callable, optional
        ``callback(finished_runs, total_runs)``, called after each run.

    Returns
    -------
    list of dict or pandas.DataFrame
        One row per record: ``run``, ``repetition``, the parameters,
        ``step`` and one column per reporter.

    Raises
    ------
    ValueError
        A wrong ``steps``, ``repetitions`` or ``every``, or a parameter or
        reporter named like one of the columns ``run``, ``repetition``, ``step``.
    NetLogoCompileError
        A reporter, ``until``, ``setup`` or ``go`` does not compile: it is
        raised before the first run.
    NetLogoRuntimeError
        A run failed; the message names the run and its parameters, and the
        other runs are abandoned.

    Examples
    --------
    >>> rows = run_experiment("Wolf Sheep Predation.nlogo",
    ...                       {"initial-number-sheep": [50, 100]},
    ...                       {"sheep": "count sheep"}, steps=50, repetitions=3, seed=1)
    """
    if parameters is None:
        combinations: List[Dict[str, Any]] = [{}]
    elif isinstance(parameters, Mapping):
        combinations = parameter_grid(parameters)
    else:
        combinations = [dict(combination) for combination in parameters]
    names, exprs = _named_reporters(reporters)
    steps, repetitions = int(steps), int(repetitions)
    if steps < 0 or repetitions < 0:
        raise ValueError("steps and repetitions must be >= 0")
    if every:
        if int(every) != every or every < 1:
            raise ValueError("every must be a whole number of steps >= 1")
        every = int(every)
    # In an explicit list a run only names some globals: the others must get back
    # the value of the model, not the one a previous run left in the session.
    parameter_names = list(dict.fromkeys(name for combination in combinations for name in combination))
    restore = [name for name in parameter_names if any(name not in c for c in combinations)]
    reserved = sorted(set(_RESERVED) & (set(names) | set(parameter_names)))
    if reserved:
        raise ValueError(f"{', '.join(reserved)}: run_experiment adds a column of that name, "
                         "give the parameter or the reporter another name")
    if len(set(names)) != len(names):
        raise ValueError("two reporters have the same name: name the columns with a dict")
    if as_dataframe:
        _require_pandas()                  # before the runs, not after them
    tasks = [(index, repetition, combination)
             for index, (combination, repetition) in enumerate(
                 ((c, r) for c in combinations for r in range(repetitions)), start=1)]

    local = threading.local()
    sessions: List[NetLogo] = []
    spare: List[NetLogo] = []              # opened for the checks below, used by the first worker
    sessions_lock = threading.Lock()
    failed = threading.Event()

    def open_session() -> NetLogo:
        nl = NetLogo(model, netlogo_home=netlogo_home, java_home=java_home, jvm_args=jvm_args)
        with sessions_lock:
            sessions.append(nl)
        nl._experiment_defaults = dict(zip(restore, nl.report(restore))) if restore else {}
        return nl

    def session() -> NetLogo:
        nl = getattr(local, "nl", None)
        if nl is None:
            with sessions_lock:
                nl = spare.pop() if spare else None
            local.nl = nl = nl or open_session()
        return nl

    def halt_all() -> None:
        """Interrupt the runs in progress: a sweep that failed does not go on."""
        failed.set()
        with sessions_lock:
            running = list(sessions)
        for nl in running:
            try:
                nl._ws.halt()
            except Exception:                  # a session that is being opened or closed
                pass

    def run(task: tuple) -> List[Dict[str, Any]]:
        run_id, repetition, combination = task
        nl = session()
        try:
            for name, value in {**nl._experiment_defaults, **combination}.items():
                nl.set_global(name, value)
            if seed is not None:
                nl.random_seed(seed + run_id - 1)
            nl.setup(setup)
            base = {"run": run_id, "repetition": repetition + 1, **combination}
            rows: List[Dict[str, Any]] = []

            def record(step: int) -> None:
                rows.append({**base, "step": step, **dict(zip(names, nl.report(exprs)))})

            if every:
                record(0)
            chunk_size = 1 if until else (every or max(1, steps))
            done = 0
            finished = bool(until) and bool(nl.report(until))
            while done < steps and not finished:
                if failed.is_set():
                    raise _Cancelled()
                chunk = min(chunk_size, steps - done)
                nl.go(chunk, go)
                done += chunk
                finished = bool(until) and bool(nl.report(until))
                if every and (done % every == 0 or done == steps or finished):
                    record(done)
            if not every:
                record(done)
            return rows
        except NetLogoError as exc:        # say which run it was
            where = f"run {run_id}, repetition {repetition + 1}, parameters {combination}"
            raise type(exc)(f"{exc.message} ({where})", exc.source, exc.context) from None

    results: Dict[int, List[Dict[str, Any]]] = {}
    try:
        if tasks:
            # A typo must not wait for the end of the first run, or of the whole sweep.
            first = open_session()
            spare.append(first)
            for code, is_reporter in [(expr, True) for expr in exprs + ([until] if until else [])] + \
                                     [(setup, False), (go, False)]:
                first._compile(code, reporter=is_reporter)
        threads = min(int(workers), len(tasks))
        if threads <= 1:
            for count, task in enumerate(tasks, start=1):
                results[task[0]] = run(task)
                if progress:
                    progress(count, len(tasks))
        else:
            _run_in_threads(tasks, threads, run, local, failed, halt_all, results, progress)
    finally:
        for nl in sessions:
            nl.close()

    rows = [row for run_id in sorted(results) for row in results[run_id]]
    if as_dataframe:
        return _require_pandas().DataFrame(rows)
    return rows


def _run_in_threads(tasks: List[tuple], threads: int, run: Callable[[tuple], List[Dict[str, Any]]],
                    local: Any, failed: threading.Event, halt_all: Callable[[], None],
                    results: Dict[int, List[Dict[str, Any]]],
                    progress: Optional[Callable[[int, int], None]]) -> None:
    """Run the tasks in ``threads`` worker threads; the first error ends the sweep."""
    todo: "queue.Queue[tuple]" = queue.Queue()
    for task in tasks:
        todo.put(task)
    finished: "queue.Queue[Any]" = queue.Queue()
    errors: List[BaseException] = []

    def work() -> None:
        try:
            while not failed.is_set():
                try:
                    task = todo.get_nowait()
                except queue.Empty:
                    break
                try:
                    finished.put((task[0], run(task)))
                except _Cancelled:
                    break
                except BaseException as exc:       # re-raised in the calling thread
                    errors.append(exc)
                    halt_all()
        finally:
            nl = getattr(local, "nl", None)
            if nl is not None:
                nl.close()
            _java.detach_thread()                  # or the JVM keeps a thread for this one
            finished.put(None)

    pool = [threading.Thread(target=work, name=f"netlogopy-experiment-{index}", daemon=True)
            for index in range(threads)]
    for thread in pool:
        thread.start()
    count = 0
    try:
        ended = 0
        while ended < threads:
            try:
                item = finished.get(timeout=0.2)   # a short wait keeps Ctrl+C responsive
            except queue.Empty:
                continue
            if item is None:
                ended += 1
                continue
            results[item[0]] = item[1]
            count += 1
            if progress and not failed.is_set():
                progress(count, len(tasks))
    except BaseException:                          # the callback failed, or Ctrl+C
        halt_all()
        raise
    finally:
        for thread in pool:
            thread.join()
    if errors:
        raise errors[0]
