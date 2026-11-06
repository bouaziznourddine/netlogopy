"""
Example 28 : headless batch runs (no window)
============================================
Headless NetLogo is much faster than the GUI: use it for experiments,
optimisation loops (e.g. with DEAP) or many replications.

New in netlogopy 0.2:
  netlogo_session(headless=True)   -> start NetLogo without window, freed at the end
  create_pyturtles(n, positions)   -> create many agents in one call
  run_command(n, "ask pyturtles [...]") -> move all agents in one call
  get_all_xy(n)                    -> positions of all agents in one call
  report_value(n, expression)      -> any NetLogo reporter, converted to Python
"""
import random

from netlogopy.netlogopy import *


def run_replication(seed, steps=50):
    """One simulation run; returns the mean x position of the cars at the end."""
    rng = random.Random(seed)
    # NetLogo is found automatically; or pass netlogo_home="C:/Program Files/NetLogo 6.2.2"
    with netlogo_session(headless=True) as n:
        run_command(n, "random-seed {}".format(seed))
        positions = [(rng.uniform(0, 60), rng.uniform(0, 60)) for _ in range(20)]
        create_pyturtles(n, positions, shape="car", size_shape=2, color=15)

        for _ in range(steps):
            # one call moves every car: much faster than a Python loop over cars
            run_command(n, "ask pyturtles [ rt random 360 fd 1 ]")
            do_tick(n)

        xy = get_all_xy(n)                      # {who: (x, y)}
        print("  pyturtles:", report_value(n, "count pyturtles"))
        return sum(x for x, _ in xy.values()) / len(xy)


if __name__ == "__main__":
    for seed in range(3):
        print("seed {}: mean x = {:.2f}".format(seed, run_replication(seed)))
