"""Parameter sweeps over a NetLogo model (like BehaviorSpace), optionally in parallel.

>>> from netlogopy import run_experiment
>>> rows = run_experiment(
...     "Fire.nlogo",
...     parameters={"density": [50, 60, 70]},
...     reporters={"burned": "burned-trees"},
...     repetitions=5, steps=500, until="not any? turtles", workers=4)
"""

import itertools
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

from .core import NetLogo, PathLike, _named_reporters

__all__ = ["run_experiment", "parameter_grid"]

Parameters = Union[None, Mapping[str, Any], Sequence[Mapping[str, Any]]]


def parameter_grid(parameters: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Every combination of the parameter values (a single value counts as one choice).

    >>> parameter_grid({"a": [1, 2], "b": True})
    [{'a': 1, 'b': True}, {'a': 2, 'b': True}]
    """
    names = list(parameters)
    choices = [list(value) if isinstance(value, (list, tuple, range)) else [value]
               for value in parameters.values()]
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
    parameters : ``{"global": [values...]}`` (every combination is run) or an
        explicit list of ``{"global": value}`` dicts.  Globals are set
        before ``setup`` runs.
    reporters : a reporter, a list of reporters, or ``{column: reporter}``.
    steps : maximum number of ``go`` per run.
    repetitions : runs per parameter combination.
    every : record the reporters every ``every`` steps (and at step 0);
        ``None`` records only the final values.
    until : NetLogo condition that ends a run early (e.g. ``"not any? turtles"``).
    seed : runs use ``random-seed seed + run - 1`` for reproducible results.
    workers : NetLogo workspaces running in parallel threads.
    progress : ``callback(finished_runs, total_runs)``.

    Returns a list of row dicts (``run``, ``repetition``, the parameters,
    ``step`` and one column per reporter), or a pandas DataFrame.
    """
    if parameters is None:
        combinations: List[Dict[str, Any]] = [{}]
    elif isinstance(parameters, Mapping):
        combinations = parameter_grid(parameters)
    else:
        combinations = [dict(combination) for combination in parameters]
    names, exprs = _named_reporters(reporters)
    tasks = [(index, repetition, combination)
             for index, (combination, repetition) in enumerate(
                 ((c, r) for c in combinations for r in range(int(repetitions))), start=1)]

    local = threading.local()
    sessions: List[NetLogo] = []
    sessions_lock = threading.Lock()

    def session() -> NetLogo:
        nl = getattr(local, "nl", None)
        if nl is None:
            nl = NetLogo(model, netlogo_home=netlogo_home, java_home=java_home, jvm_args=jvm_args)
            local.nl = nl
            with sessions_lock:
                sessions.append(nl)
        return nl

    def run(task: tuple) -> List[Dict[str, Any]]:
        run_id, repetition, combination = task
        nl = session()
        for name, value in combination.items():
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
        while done < steps:
            chunk = min(chunk_size, steps - done)
            nl.go(chunk, go)
            done += chunk
            finished = bool(until) and bool(nl.report(until))
            if every and (done % every == 0 or done == steps or finished):
                record(done)
            if finished:
                break
        if not every:
            record(done)
        return rows

    results: Dict[int, List[Dict[str, Any]]] = {}
    try:
        if int(workers) <= 1:
            for count, task in enumerate(tasks, start=1):
                results[task[0]] = run(task)
                if progress:
                    progress(count, len(tasks))
        else:
            with ThreadPoolExecutor(max_workers=int(workers)) as pool:
                futures = {pool.submit(run, task): task[0] for task in tasks}
                for count, future in enumerate(as_completed(futures), start=1):
                    results[futures[future]] = future.result()
                    if progress:
                        progress(count, len(tasks))
    finally:
        for nl in sessions:
            nl.close()

    rows = [row for run_id in sorted(results) for row in results[run_id]]
    if as_dataframe:
        try:
            import pandas
        except ImportError as exc:
            raise ImportError("as_dataframe=True needs pandas: pip install pandas") from exc
        return pandas.DataFrame(rows)
    return rows
