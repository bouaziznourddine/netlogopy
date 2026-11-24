"""
Example 39 : Calibrate a NetLogo model with a Python optimiser
==============================================================
Which tree density makes the fire of the Fire model burn half of the
forest?  Python searches the answer by bisection: each evaluation runs the
model several times in parallel headless sessions (run_experiment), and the
optimiser narrows the interval from the mean result.  The model is then run
in the NetLogo window at the density found.

The answer is close to the percolation threshold of the square lattice
(about 59 %): below it the fire dies out, above it the fire crosses the
forest, so the burned share jumps around there and each evaluation averages
several runs.

Any Python optimiser fits the same loop (scipy.optimize, optuna, a genetic
algorithm...): it proposes parameters, NetLogo simulates, Python scores.
"""
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, run_experiment

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "complexe", "Fire", "Fire.nlogo")
TARGET = 50.0          # % of the forest burned
REPETITIONS = 16       # runs per evaluation (the fire is random)


def burned_percent(density, seed):
    """Mean % of the forest burned at this density (REPETITIONS runs, 4 in parallel)."""
    rows = run_experiment(MODEL, parameters={"density": [density]},
                          reporters={"burned": "burned-trees", "trees": "initial-trees"},
                          repetitions=REPETITIONS, steps=3000, until="not any? turtles",
                          seed=seed, workers=4)
    return sum(100 * row["burned"] / row["trees"] for row in rows) / len(rows)


def bisection(low, high, iterations=7):
    """Density giving TARGET % burned; the burned share grows with the density."""
    history = []
    for iteration in range(iterations):
        middle = (low + high) / 2
        score = burned_percent(middle, seed=1 + 100 * iteration)
        history.append((middle, score))
        print(f"  try {iteration + 1}: density {middle:6.2f} -> {score:5.1f} % burned")
        if score < TARGET:
            low = middle
        else:
            high = middle
    return (low + high) / 2, history


if __name__ == "__main__":
    started = time.monotonic()
    print(f"searching the density that burns {TARGET:.0f} % of the forest")
    density, history = bisection(45.0, 75.0)
    runs = len(history) * REPETITIONS
    print(f"density = {density:.2f} ({runs} runs in {time.monotonic() - started:.0f} s)")

    with NetLogo(MODEL, gui=True) as nl:           # watch one run at that density
        nl.globals["density"] = density
        nl.random_seed(7)
        nl.setup()
        while nl.report("any? turtles"):
            nl.go(4)
            time.sleep(0.03)
        print(f"one run at {density:.2f}: {nl.report('burned-trees / initial-trees * 100'):.1f} % burned")
        time.sleep(2)
