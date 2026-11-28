"""Run the BehaviorSpace experiments saved in a model, from Python.

>>> from netlogopy import behaviorspace_experiments, run_behaviorspace
>>> list(behaviorspace_experiments("Wolf Sheep Predation.nlogox"))
['New BehaviorSpace Features', 'Wolf Sheep Crossing', ...]
>>> rows = run_behaviorspace("Wolf Sheep Predation.nlogox", "Wolf Sheep Crossing", workers=4)

The experiment is read from the model file (``.nlogo`` and ``.nlogox``) and
run by :func:`~netlogopy.run_experiment`: the runs go in parallel threads and
the result is a list of rows or a pandas DataFrame, with no file to read back.
"""

import itertools
import os
import re
import warnings
import xml.etree.ElementTree as ElementTree
from typing import Any, Callable, Dict, List, Optional, Sequence

from .convert import Code
from .core import PathLike
from .errors import NetLogoError
from .experiment import run_experiment

__all__ = ["behaviorspace_experiments", "run_behaviorspace"]

_SECTION = "@#$#@#$#@"
_NUMBER = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
_WHEN = "netlogopy-record-condition"       # no NetLogo reporter can have this name


def _value(text: str) -> Any:
    """A NetLogo literal of an experiment as a Python value (other code stays code)."""
    text = text.strip()
    if _NUMBER.match(text):
        number = float(text)
        return int(number) if number.is_integer() and "." not in text and "e" not in text.lower() else number
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if len(text) >= 2 and text[0] == text[-1] == '"' and '"' not in text[1:-1].replace('\\"', ""):
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return Code(text)


def _stepped(element: Any) -> List[Any]:
    first, step, last = (float(element.get(name)) for name in ("first", "step", "last"))
    if step == 0 or (last - first) / step < 0:
        raise NetLogoError(f"{element.get('variable')}: the stepped values never reach the last one")
    count = int(round((last - first) / step + 1e-9)) + 1
    values = [first + index * step for index in range(count) if (first + index * step - last) * step <= 1e-9]
    return [int(value) if float(value).is_integer() else round(value, 10) for value in values]


def _value_sets(parent: Any) -> Dict[str, List[Any]]:
    """The value sets directly under ``parent``: ``{variable: [values]}``."""
    sets: Dict[str, List[Any]] = {}
    if parent is None:
        return sets
    for element in parent:
        if element.tag == "enumeratedValueSet":
            sets[element.get("variable")] = [_value(value.get("value")) for value in element.findall("value")]
        elif element.tag == "steppedValueSet":
            sets[element.get("variable")] = _stepped(element)
    return sets


def _text(element: Any, tag: str) -> Optional[str]:
    child = element.find(tag)
    text = child.text.strip() if child is not None and child.text else ""
    return text or None


def _experiment(element: Any) -> Dict[str, Any]:
    """One ``<experiment>`` element as a dict (NetLogo 6 and NetLogo 7 layouts)."""
    limit = element.find("timeLimit")
    steps = element.get("timeLimit") or (limit.get("steps") if limit is not None else None)
    constants = {**_value_sets(element), **_value_sets(element.find("constants"))}
    names = list(constants)
    choices = [constants[name] for name in names]
    base = [dict(zip(names, combination)) for combination in itertools.product(*choices)]
    subs = element.find("subExperiments")
    parameters: List[Dict[str, Any]] = []
    for sub in (subs.findall("subExperiment") if subs is not None else []):
        own = {**constants, **_value_sets(sub)}
        keys = list(own)
        parameters.extend(dict(zip(keys, combination))
                          for combination in itertools.product(*(own[key] for key in keys)))
    metrics = element.find("metrics")
    metric_parent = metrics if metrics is not None else element
    return {
        "name": element.get("name"),
        "repetitions": int(element.get("repetitions") or 1),
        "every_step": (element.get("runMetricsEveryStep") or "true").lower() == "true",
        "record_when": _text(element, "runMetricsCondition"),
        "steps": int(float(steps)) if steps else 0,
        "setup": _text(element, "setup") or "",
        "go": _text(element, "go") or "",
        "final": _text(element, "postRun") or _text(element, "final"),
        "until": _text(element, "exitCondition"),
        "before": _text(element, "preExperiment"),
        "after": _text(element, "postExperiment"),
        "metrics": [metric.text.strip() for metric in metric_parent.findall("metric") if metric.text],
        "parameters": parameters or base,
    }


def behaviorspace_experiments(model: PathLike) -> Dict[str, Dict[str, Any]]:
    """The BehaviorSpace experiments saved in a model file.

    Parameters
    ----------
    model : str or os.PathLike
        A ``.nlogo``, ``.nlogo3d`` or ``.nlogox`` file.

    Returns
    -------
    dict
        ``{experiment name: description}``.  A description has the keys
        ``repetitions``, ``steps`` (0: no limit), ``setup``, ``go``, ``final``,
        ``until``, ``metrics``, ``every_step``, ``record_when`` and
        ``parameters`` (the list of ``{global: value}`` combinations).
    """
    path = os.fspath(model)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if path.lower().endswith(".nlogox"):
        root = ElementTree.fromstring(text.encode("utf-8")).find("experiments")
    else:
        match = re.search(r"<experiments>.*?</experiments>", text, re.DOTALL)
        root = ElementTree.fromstring(match.group(0)) if match else None
    if root is None:
        return {}
    return {element.get("name"): _experiment(element) for element in root.findall("experiment")}


def run_behaviorspace(model: PathLike, experiment: Optional[str] = None, *,
                      repetitions: Optional[int] = None, steps: Optional[int] = None,
                      seed: Optional[int] = None, workers: int = 1,
                      netlogo_home: Optional[PathLike] = None, java_home: Optional[PathLike] = None,
                      jvm_args: Sequence[str] = (), as_dataframe: bool = False,
                      progress: Optional[Callable[[int, int], None]] = None) -> Any:
    """Run a BehaviorSpace experiment saved in ``model`` and return its results.

    Parameters
    ----------
    model : str or os.PathLike
        The model file.
    experiment : str, optional
        Name of the experiment; may be left out when the model has only one.
    repetitions, steps : int, optional
        Replace the repetitions and the time limit of the experiment.
    seed : int, optional
        Runs use ``random-seed seed + run - 1`` for reproducible results.
    workers : int, default 1
        NetLogo workspaces running in parallel threads.
    netlogo_home, java_home, jvm_args
        As for :class:`~netlogopy.NetLogo`.
    as_dataframe : bool, default False
        Return a pandas DataFrame instead of a list of dicts.
    progress : callable, optional
        ``callback(finished_runs, total_runs)``.

    Returns
    -------
    list of dict or pandas.DataFrame
        As :func:`~netlogopy.run_experiment`: ``run``, ``repetition``, the
        parameters, ``step`` and one column per metric.

    Notes
    -----
    The runs are made by netlogopy, not by BehaviorSpace: the commands that an
    experiment runs once before and after all its runs are not run (a warning
    says so), and a metric is read without changing the course of the model.
    """
    experiments = behaviorspace_experiments(model)
    if not experiments:
        raise NetLogoError(f"{os.fspath(model)} has no BehaviorSpace experiment")
    if experiment is None:
        if len(experiments) > 1:
            raise ValueError("the model has several experiments, name one: " + ", ".join(experiments))
        experiment = next(iter(experiments))
    if experiment not in experiments:
        raise ValueError(f"no experiment named {experiment!r}; the model has: " + ", ".join(experiments))
    spec = experiments[experiment]
    if spec["before"] or spec["after"]:
        warnings.warn(f"experiment {experiment!r}: the commands run once before or after all the runs "
                      "are not run by run_behaviorspace", UserWarning, stacklevel=2)
    limit = spec["steps"] if steps is None else int(steps)
    if limit <= 0:
        limit = 10 ** 9                    # no time limit: the exit condition or `stop` ends the run
    reporters = {metric: metric for metric in spec["metrics"]}
    when = spec["record_when"]
    if when:
        reporters[_WHEN] = when
    every = 1 if (spec["every_step"] or when) else None
    rows = run_experiment(
        model, spec["parameters"] or None, reporters or "ticks",
        steps=limit, repetitions=spec["repetitions"] if repetitions is None else repetitions,
        setup=spec["setup"], go=spec["go"], every=every, until=spec["until"], final=spec["final"],
        seed=seed, workers=workers, netlogo_home=netlogo_home, java_home=java_home,
        jvm_args=jvm_args, progress=progress)
    if when:
        rows = [{name: value for name, value in row.items() if name != _WHEN}
                for row in rows if row[_WHEN] is True]
    if as_dataframe:
        from .core import _require_pandas
        return _require_pandas().DataFrame(rows)
    return rows
