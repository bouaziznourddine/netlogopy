"""run_experiment: parameter sweeps over the Fire model (headless, parallel)."""

import pytest
from conftest import FIRE_MODEL

from netlogopy import run_experiment

pytestmark = pytest.mark.netlogo

REPORTERS = {"burned": "burned-trees", "trees": "initial-trees"}


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
