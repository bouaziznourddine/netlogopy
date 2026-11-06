"""
Example 31 : Collect time series (headless)
===========================================
Run Wolf Sheep Predation without a window and record the populations at
every step; with pandas installed the result is a DataFrame.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "complexe", "Wolf Sheep", "Wolf Sheep Predation.nlogo")

if __name__ == "__main__":
    with NetLogo(MODEL) as nl:                         # headless: fast
        nl.globals["model-version"] = "sheep-wolves-grass"
        nl.globals["initial-number-wolves"] = 40
        nl.random_seed(2024)                           # reproducible run
        nl.setup()
        data = nl.collect({"sheep": "count sheep",
                           "wolves": "count wolves",
                           "grass": "count patches with [pcolor = green] / 4"},
                          steps=300, until="not any? wolves or not any? sheep")

    print(" step   sheep  wolves  grass")
    for i in range(0, len(data["step"]), 25):
        print(f"{data['step'][i]:5d} {data['sheep'][i]:7.0f} {data['wolves'][i]:7.0f} {data['grass'][i]:6.0f}")
    print("max sheep:", max(data["sheep"]), "| max wolves:", max(data["wolves"]))

    try:
        import pandas
    except ImportError:
        pandas = None
    if pandas is not None:
        frame = pandas.DataFrame(data).set_index("step")
        print(frame.describe().loc[["mean", "min", "max"]].round(1))
