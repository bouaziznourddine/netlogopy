"""Experiment designs, sensitivity analysis and calibration of a NetLogo model.

>>> from netlogopy import latin_hypercube, run_experiment, sensitivity, calibrate
>>> bounds = {"density": (40, 80)}
>>> points = latin_hypercube(bounds, 20, seed=1)          # 20 parameter sets
>>> rows = run_experiment("Fire.nlogo", points, {"burned": "burned-trees"}, steps=200)
>>> sensitivity("Fire.nlogo", bounds, {"burned": "burned-trees"}, samples=64, steps=200)
>>> calibrate("Fire.nlogo", bounds, "burned-trees", target=5000, steps=200)

A parameter range is ``(low, high)``; two whole numbers give whole values,
``(0.0, 1.0)`` gives decimals.  A list gives the values to choose from.
The samplers need nothing but Python; :func:`sensitivity` needs SALib.
"""

import random
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .core import PathLike
from .experiment import run_experiment

__all__ = ["latin_hypercube", "random_sample", "sensitivity", "calibrate"]

Bounds = Mapping[str, Any]


def _is_range(value: Any) -> bool:
    return (isinstance(value, tuple) and len(value) == 2
            and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value))


def _check(bounds: Bounds) -> None:
    if not bounds:
        raise ValueError("bounds is empty: give {parameter: (low, high)}")
    for name, value in bounds.items():
        if _is_range(value):
            if value[0] > value[1]:
                raise ValueError(f"{name}: the low bound {value[0]} is above the high bound {value[1]}")
        elif isinstance(value, (str, bytes)) or not hasattr(value, "__len__") or len(value) == 0:
            raise ValueError(f"{name}: give a range (low, high) or a list of values to choose from")


def _place(value: Any, unit: float) -> Any:
    """The parameter value at position ``unit`` (0 <= unit < 1) of its range or of its list."""
    if _is_range(value):
        low, high = value
        if isinstance(low, int) and isinstance(high, int):
            return min(high, low + int(unit * (high - low + 1)))
        return low + unit * (high - low)
    choices = list(value)
    return choices[min(len(choices) - 1, int(unit * len(choices)))]


def latin_hypercube(bounds: Bounds, samples: int, *, seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """Parameter sets spread over the ranges: a Latin hypercube sample.

    Each range is cut in ``samples`` slices and every slice is used once, so
    few runs already cover every parameter from its lowest to its highest value.

    Parameters
    ----------
    bounds : mapping
        ``{parameter: (low, high)}`` or ``{parameter: [choices...]}``.
    samples : int
        Number of parameter sets.
    seed : int, optional
        For the same sample at each call.

    Returns
    -------
    list of dict
        Parameter sets for :func:`~netlogopy.run_experiment`.
    """
    _check(bounds)
    samples = int(samples)
    if samples < 1:
        raise ValueError("samples must be >= 1")
    rng = random.Random(seed)
    columns = {}
    for name, value in bounds.items():
        units = [(index + rng.random()) / samples for index in range(samples)]
        rng.shuffle(units)
        columns[name] = [_place(value, unit) for unit in units]
    return [{name: columns[name][index] for name in bounds} for index in range(samples)]


def random_sample(bounds: Bounds, samples: int, *, seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """Parameter sets drawn uniformly at random in the ranges (Monte Carlo).

    Parameters and result as :func:`latin_hypercube`.
    """
    _check(bounds)
    samples = int(samples)
    if samples < 1:
        raise ValueError("samples must be >= 1")
    rng = random.Random(seed)
    return [{name: _place(value, rng.random()) for name, value in bounds.items()} for _ in range(samples)]


def _mean_by_point(rows: List[Dict[str, Any]], names: List[str], points: int, repetitions: int,
                   ) -> Dict[str, List[float]]:
    """The mean over the repetitions of the final value of each reporter, per parameter set."""
    last: Dict[int, Dict[str, Any]] = {}
    for row in rows:                       # the last record of each run
        last[row["run"]] = row
    means: Dict[str, List[float]] = {name: [] for name in names}
    for point in range(points):
        runs = [last[point * repetitions + repetition + 1] for repetition in range(repetitions)]
        for name in names:
            values = [run[name] for run in runs]
            if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
                raise ValueError(f"{name}: the reporter must give a number, it gave {values[0]!r}")
            means[name].append(sum(values) / len(values))
    return means


def sensitivity(model: PathLike, bounds: Mapping[str, Tuple[float, float]],
                reporters: Union[str, Sequence[str], Mapping[str, str]], *,
                method: str = "sobol", samples: int = 64, seed: Optional[int] = None,
                **experiment: Any) -> Dict[str, Any]:
    """Which parameters change the results most: a global sensitivity analysis.

    Parameters
    ----------
    model : str or os.PathLike
        The model file.
    bounds : mapping
        ``{parameter: (low, high)}``; two whole numbers give whole values.
    reporters : str, sequence of str or mapping
        The results to explain; each must be a number.  With repetitions,
        the mean of the runs is analysed.
    method : {"sobol", "morris"}, default "sobol"
        ``"sobol"`` gives the share of the variance due to each parameter
        (``S1`` alone, ``ST`` with its interactions) and makes
        ``samples * (parameters + 2)`` parameter sets.  ``"morris"`` ranks
        the parameters with fewer runs (``mu_star``, ``sigma``):
        ``samples * (parameters + 1)`` parameter sets.
    samples : int, default 64
        Base number of samples (a power of 2 for ``"sobol"``).
    seed : int, optional
        For the same parameter sets and the same runs at each call.
    **experiment
        The other arguments of :func:`~netlogopy.run_experiment`: ``steps``,
        ``repetitions``, ``setup``, ``go``, ``until``, ``workers``...

    Returns
    -------
    dict
        ``{reporter: {index: {parameter: value}}}``, e.g.
        ``result["burned"]["ST"]["density"]``, and under the key ``"runs"``
        the list of parameter sets with the result of each.

    Notes
    -----
    Needs SALib: ``pip install SALib``.
    """
    if method not in ("sobol", "morris"):
        raise ValueError('method must be "sobol" or "morris"')
    for name, value in bounds.items():
        if not _is_range(value):
            raise ValueError(f"{name}: sensitivity needs a range (low, high)")
    _check(bounds)
    for name in ("every", "as_dataframe", "parameters"):
        if name in experiment:
            raise TypeError(f"sensitivity() does not take {name}")
    try:
        import numpy
        if method == "sobol":
            from SALib.analyze import sobol as analyze
            try:
                from SALib.sample import sobol as sample
            except ImportError:            # SALib < 1.4.6
                from SALib.sample import saltelli as sample
        else:
            from SALib.analyze import morris as analyze
            from SALib.sample import morris as sample
    except ImportError as exc:
        raise ImportError("sensitivity() needs SALib: pip install SALib") from exc

    names = list(bounds)
    whole = {name for name in names if all(isinstance(item, int) for item in bounds[name])}
    # A whole-number range is sampled as decimals over [low - 0.5, high + 0.5) and rounded,
    # so that every whole value has the same share of the samples.
    problem = {"num_vars": len(names), "names": names,
               "bounds": [[bounds[name][0] - 0.5, bounds[name][1] + 0.5 - 1e-9] if name in whole
                          else [float(bounds[name][0]), float(bounds[name][1])] for name in names]}
    if method == "sobol":
        try:
            matrix = sample.sample(problem, int(samples), calc_second_order=False, seed=seed)
        except TypeError:                  # saltelli.sample has no seed
            matrix = sample.sample(problem, int(samples), calc_second_order=False)
    else:
        matrix = sample.sample(problem, int(samples), seed=seed)
    points = [{name: (int(round(value)) if name in whole else float(value))
               for name, value in zip(names, row)} for row in matrix.tolist()]

    from .core import _named_reporters
    columns, _ = _named_reporters(reporters)
    repetitions = int(experiment.get("repetitions", 1))
    rows = run_experiment(model, points, reporters, seed=seed, **experiment)
    means = _mean_by_point(rows, columns, len(points), repetitions)

    result: Dict[str, Any] = {}
    for column in columns:
        values = numpy.array(means[column], dtype=float)
        if method == "sobol":
            indices = analyze.analyze(problem, values, calc_second_order=False, seed=seed)
            keys = ("S1", "S1_conf", "ST", "ST_conf")
        else:
            indices = analyze.analyze(problem, matrix, values, seed=seed)
            keys = ("mu", "mu_star", "mu_star_conf", "sigma")
        result[column] = {key: {name: float(value) for name, value in zip(names, indices[key])}
                          for key in keys}
    result["runs"] = [{**point, **{column: means[column][index] for column in columns}}
                      for index, point in enumerate(points)]
    return result


def calibrate(model: PathLike, bounds: Bounds, objective: str, *, target: Optional[float] = None,
              minimize: bool = True, population: int = 12, generations: int = 10,
              seed: Optional[int] = None, progress: Optional[Callable[[int, float], None]] = None,
              **experiment: Any) -> Dict[str, Any]:
    """Search the parameter values that give the best result (differential evolution).

    Parameters
    ----------
    model : str or os.PathLike
        The model file.
    bounds : mapping
        ``{parameter: (low, high)}`` or ``{parameter: [choices...]}``.
    objective : str
        A NetLogo reporter giving a number at the end of a run.
    target : float, optional
        Look for the parameters whose result is closest to ``target``
        (for instance a measured value).  Without it the result itself is
        made as small, or as large, as possible.
    minimize : bool, default True
        Without ``target``: look for the smallest result (False: the largest).
    population : int, default 12
        Parameter sets tried per generation (at least 4).
    generations : int, default 10
        Number of generations after the first one; the search makes
        ``population * (generations + 1)`` parameter sets.
    seed : int, optional
        For the same search at each call.
    progress : callable, optional
        ``callback(generation, best_score)``, called after each generation.
    **experiment
        The other arguments of :func:`~netlogopy.run_experiment`: ``steps``,
        ``repetitions`` (the mean of the repetitions is used), ``setup``,
        ``go``, ``until``, ``workers``...

    Returns
    -------
    dict
        ``parameters`` (the best set), ``value`` (its result), ``score``
        (what was minimised: the distance to ``target``, or the result),
        ``evaluations`` and ``history`` (the best score after each generation).
    """
    _check(bounds)
    population, generations = int(population), int(generations)
    if population < 4:
        raise ValueError("population must be >= 4")
    if generations < 0:
        raise ValueError("generations must be >= 0")
    for name in ("every", "as_dataframe", "parameters"):
        if name in experiment:
            raise TypeError(f"calibrate() does not take {name}")
    rng = random.Random(seed)
    names = list(bounds)
    repetitions = int(experiment.get("repetitions", 1))
    evaluations = 0

    def evaluate(units: List[List[float]]) -> Tuple[List[float], List[float]]:
        """The results and the scores of parameter sets given as positions in [0, 1)."""
        nonlocal evaluations
        points = [{name: _place(bounds[name], unit) for name, unit in zip(names, row)} for row in units]
        run_seed = None if seed is None else seed + evaluations * repetitions
        rows = run_experiment(model, points, {"objective": objective}, seed=run_seed, **experiment)
        evaluations += len(points)
        values = _mean_by_point(rows, ["objective"], len(points), repetitions)["objective"]
        if target is not None:
            return values, [abs(value - target) for value in values]
        return values, [value if minimize else -value for value in values]

    # First generation: a Latin hypercube, so that every range is covered.
    slices = []
    for _ in names:
        column = [(index + rng.random()) / population for index in range(population)]
        rng.shuffle(column)
        slices.append(column)
    members = [[slices[axis][index] for axis in range(len(names))] for index in range(population)]
    values, scores = evaluate(members)
    history = [min(scores)]
    if progress:
        progress(0, history[-1])

    for generation in range(1, generations + 1):
        best = members[scores.index(min(scores))]
        trials = []
        for index, member in enumerate(members):
            first, second = rng.sample([other for other in range(population) if other != index], 2)
            weight = 0.5 + rng.random() * 0.5
            forced = rng.randrange(len(names))
            trial = []
            for axis in range(len(names)):
                if axis == forced or rng.random() < 0.7:
                    unit = best[axis] + weight * (members[first][axis] - members[second][axis])
                    if not 0.0 <= unit < 1.0:      # out of the range: draw again inside it
                        unit = rng.random()
                else:
                    unit = member[axis]
                trial.append(unit)
            trials.append(trial)
        trial_values, trial_scores = evaluate(trials)
        for index in range(population):
            if trial_scores[index] <= scores[index]:
                members[index], values[index], scores[index] = trials[index], trial_values[index], trial_scores[index]
        history.append(min(scores))
        if progress:
            progress(generation, history[-1])

    winner = scores.index(min(scores))
    return {"parameters": {name: _place(bounds[name], unit) for name, unit in zip(names, members[winner])},
            "value": values[winner], "score": scores[winner],
            "evaluations": evaluations, "history": history}
