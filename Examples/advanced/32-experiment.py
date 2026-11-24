"""
Example 32 : Parameter sweep (like BehaviorSpace)
=================================================
Fire model: how much of the forest burns, for each tree density?
Each combination is repeated, runs are spread over 4 headless NetLogo
workspaces, and each run stops as soon as the fire is out.  The answer
jumps around 59 %, the percolation threshold of the square lattice: below it
the fire dies out, above it the fire crosses the forest.  Then the NetLogo
window shows one fire on each side of the threshold.
"""
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, run_experiment

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "complexe", "Fire", "Fire.nlogo")

if __name__ == "__main__":
    rows = run_experiment(
        MODEL,
        parameters={"density": [50, 55, 58, 60, 62, 65, 70]},
        reporters={"burned": "burned-trees", "trees": "initial-trees"},
        repetitions=3,
        steps=2000,
        until="not any? turtles",          # the fire is out
        seed=1,                            # reproducible
        workers=4,
        progress=lambda done, total: print(f"\r{done}/{total} runs", end=""),
    )
    print()
    print("density  % burned (mean of 3 runs)")
    for density in sorted({row["density"] for row in rows}):
        burned = [100 * r["burned"] / r["trees"] for r in rows if r["density"] == density]
        print(f"{density:7d}  {sum(burned) / len(burned):6.1f}  " + "#" * int(sum(burned) / len(burned) / 2))

    # watch one run below, at and above the threshold
    with NetLogo(MODEL, gui=True) as nl:   # gui=False: the same runs without the window
        for density in (55, 60, 65):
            nl.globals["density"] = density
            nl.random_seed(1)
            nl.setup()
            while nl.report("any? turtles"):
                nl.go()
                time.sleep(0.01)
            burned = 100 * nl.report("burned-trees") / nl.report("initial-trees")
            print(f"density {density}: {burned:.0f} % burned in {nl.ticks:.0f} ticks")
            time.sleep(1)
