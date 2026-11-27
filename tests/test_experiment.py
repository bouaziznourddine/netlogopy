"""run_experiment: parameter sweeps over the Fire model (headless, parallel)."""

import builtins
import time

import pytest
from conftest import FIRE_MODEL

from netlogopy import NetLogo, NetLogoCompileError, NetLogoRuntimeError, _java, run_experiment

pytestmark = pytest.mark.netlogo

REPORTERS = {"burned": "burned-trees", "trees": "initial-trees"}
SLOW_GO = "ask patches [ set pcolor pcolor ]"      # some milliseconds per step, for runs that must not finish


def java_threads():
    import jpype
    return int(jpype.JClass("java.lang.Thread").getAllStackTraces().size())


def test_final_values_in_parallel_are_reproducible():
    kwargs = dict(parameters={"density": [40, 75]}, reporters=REPORTERS, repetitions=2,
                  steps=1000, until="not any? turtles", seed=7)
    progress = []
    rows = run_experiment(FIRE_MODEL, workers=2, progress=lambda done, total: progress.append((done, total)),
                          **kwargs)
    assert [(r["run"], r["repetition"], r["density"]) for r in rows] == [
        (1, 1, 40), (2, 2, 40), (3, 1, 75), (4, 2, 75)]
    assert sorted(progress) == [(1, 4), (2, 4), (3, 4), (4, 4)]
    assert all(set(r) == {"run", "repetition", "density", "step", "burned", "trees"} for r in rows)
    low = [r["burned"] / r["trees"] for r in rows if r["density"] == 40]
    high = [r["burned"] / r["trees"] for r in rows if r["density"] == 75]
    assert max(low) < 0.5 < min(high)
    assert all(r["step"] < 1000 for r in rows)                  # stopped by `until`
    assert run_experiment(FIRE_MODEL, workers=1, **kwargs) == rows


def test_time_series_and_explicit_combinations():
    rows = run_experiment(FIRE_MODEL, [{"density": 60}], "burned-trees", steps=20, every=5)
    assert [r["step"] for r in rows] == [0, 5, 10, 15, 20]
    assert rows[0]["burned-trees"] <= rows[-1]["burned-trees"]
    pandas = pytest.importorskip("pandas")
    frame = run_experiment(FIRE_MODEL, {"density": 50}, ["ticks"], steps=3, as_dataframe=True)
    assert isinstance(frame, pandas.DataFrame) and frame["ticks"].tolist() == [3]


def test_a_numpy_array_gives_one_run_per_value():
    numpy = pytest.importorskip("numpy")
    rows = run_experiment(FIRE_MODEL, {"density": numpy.array([50, 60, 70])}, "density", steps=1)
    assert [(r["run"], r["density"]) for r in rows] == [(1, 50), (2, 60), (3, 70)]


def test_until_is_tested_before_the_first_step():
    rows = run_experiment(FIRE_MODEL, None, {"ticks": "ticks"}, steps=10, until="true")
    assert rows == [{"run": 1, "repetition": 1, "step": 0, "ticks": 0.0}]
    rows = run_experiment(FIRE_MODEL, None, {"ticks": "ticks"}, steps=10, every=2, until="ticks >= 3")
    assert [(r["step"], r["ticks"]) for r in rows] == [(0, 0.0), (2, 2.0), (3, 3.0)]


@pytest.mark.parametrize("arguments, message", [
    (dict(every=-1), "every"), (dict(every=1.5), "every"), (dict(steps=-1), "steps"),
    (dict(repetitions=-2), "repetitions"), (dict(reporters={"step": "ticks"}), "step"),
    (dict(reporters={"run": "ticks"}), "run"), (dict(parameters={"repetition": [1]}), "repetition"),
    (dict(reporters=["ticks", "ticks"]), "same name")])
def test_wrong_arguments_are_refused_before_any_run(arguments, message):
    before = len(_java._open_handles)
    with pytest.raises(ValueError, match=message):
        run_experiment(FIRE_MODEL, **{"steps": 2, **arguments})
    assert len(_java._open_handles) == before


@pytest.mark.parametrize("arguments", [dict(reporters="count turtlez"), dict(until="tickz > 3"),
                                       dict(go="goo"), dict(setup="set-up")])
def test_a_typo_is_reported_before_the_first_run(arguments):
    began = time.perf_counter()
    with pytest.raises(NetLogoCompileError):
        run_experiment(FIRE_MODEL, {"density": [50, 60, 70, 80]}, workers=2,
                       **{"steps": 5000, "go": SLOW_GO, **arguments})
    assert time.perf_counter() - began < 20


def test_a_failing_run_names_itself_and_ends_the_sweep():
    before = len(_java._open_handles)
    began = time.perf_counter()
    with pytest.raises(NetLogoRuntimeError) as info:
        run_experiment(FIRE_MODEL, {"density": [50, 60, 70, 80, 90, 95]}, "burned-trees", steps=20000, workers=3,
                       go='if density = 60 [ error "boom" ] ' + SLOW_GO)
    assert "boom" in info.value.message
    assert "run 2, repetition 1" in info.value.message and "'density': 60" in info.value.message
    assert time.perf_counter() - began < 60                     # the other runs were interrupted
    assert len(_java._open_handles) == before


def test_an_error_in_the_progress_callback_ends_the_sweep():
    def progress(done, total):
        raise RuntimeError("stop here")

    before = len(_java._open_handles)
    began = time.perf_counter()
    with pytest.raises(RuntimeError, match="stop here"):
        run_experiment(FIRE_MODEL, {"density": [50, 60, 70, 80, 90, 95]}, "burned-trees", steps=20000, workers=3,
                       go="if density > 50 [ " + SLOW_GO + " ]", progress=progress)
    assert time.perf_counter() - began < 60 and len(_java._open_handles) == before


def test_runs_given_as_a_list_do_not_inherit_the_values_of_other_runs():
    with NetLogo(FIRE_MODEL) as fire:
        default = fire.globals["density"]
    assert default != 20
    for workers in (1, 2):
        rows = run_experiment(FIRE_MODEL, [{"density": 20}, {}, {}, {}], {"d": "density"}, steps=1,
                              workers=workers)
        assert [r["d"] for r in rows] == [20.0, default, default, default]
        assert "density" in rows[0] and "density" not in rows[1]


def test_the_workers_leave_no_java_thread_and_no_session():
    run_experiment(FIRE_MODEL, {"density": [50, 60]}, "burned-trees", steps=5, workers=2)   # settles the count
    threads, handles = java_threads(), len(_java._open_handles)
    for _ in range(3):
        run_experiment(FIRE_MODEL, {"density": [50, 60, 70, 80]}, "burned-trees", steps=5, workers=4)
    assert java_threads() <= threads + 1 and len(_java._open_handles) == handles


def test_pandas_is_asked_for_before_the_runs(monkeypatch):
    real_import = builtins.__import__

    def no_pandas(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("no pandas here")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pandas)
    began = time.perf_counter()
    with pytest.raises(ImportError, match="pip install pandas"):
        run_experiment(FIRE_MODEL, {"density": [50, 60]}, "burned-trees", steps=5000, go=SLOW_GO,
                       as_dataframe=True)
    assert time.perf_counter() - began < 10
