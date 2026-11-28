"""
Example 46 : Which parameters matter?  Designs, sensitivity, calibration
========================================================================
Wolf Sheep Predation has many sliders.  Three questions, three functions:

1. latin_hypercube : 24 parameter sets that cover every range, run in
   parallel, with one row per run.
2. sensitivity     : the share of the variation of the result that each
   parameter explains (Sobol indices; needs `pip install SALib`).  The model
   is noisy: more samples give steadier shares.
3. calibrate       : the parameter values for which the model gives a result
   we ask for (here: about 150 sheep after 30 ticks).
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import calibrate, latin_hypercube, run_experiment, sensitivity

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "complexe", "Wolf Sheep",
                     "Wolf Sheep Predation.nlogo")
BOUNDS = {
    "initial-number-wolves": (20, 120),        # two whole numbers: whole values
    "wolf-gain-from-food": (10.0, 40.0),       # decimals
    "sheep-reproduce": (2.0, 8.0),
}
RUN = dict(steps=30, workers=4, seed=1)

if __name__ == "__main__":
    # 1. a design that covers the ranges with few runs
    points = latin_hypercube(BOUNDS, 24, seed=1)
    rows = run_experiment(MODEL, points, {"sheep": "count sheep", "wolves": "count wolves"}, **RUN)
    extinct = sum(1 for row in rows if row["wolves"] == 0)
    print(f"{len(rows)} runs; the wolves died out in {extinct} of them")
    best = max(rows, key=lambda row: row["sheep"])
    print("most sheep:", {name: round(best[name], 1) for name in BOUNDS}, "->", int(best["sheep"]), "sheep")

    # 2. which parameter explains the number of sheep?
    try:
        result = sensitivity(MODEL, BOUNDS, {"sheep": "count sheep"}, samples=32, **RUN)
    except ImportError as exc:
        print("sensitivity analysis skipped:", exc)
    else:
        print("\nshare of the variation of the number of sheep (total Sobol index)")
        for name, share in sorted(result["sheep"]["ST"].items(), key=lambda item: -item[1]):
            print(f"  {name:24s} {share:5.2f}  " + "#" * int(max(0.0, share) * 30))

    # 3. the parameters that give about 150 sheep
    found = calibrate(MODEL, BOUNDS, "count sheep", target=150, population=8, generations=5,
                      progress=lambda generation, score: print(f"\rgeneration {generation}: "
                                                                f"{score:.0f} sheep from the target", end=""),
                      **RUN)
    print()
    print("calibrated:", {name: round(value, 1) for name, value in found["parameters"].items()},
          "->", int(found["value"]), "sheep, after", found["evaluations"], "runs")
