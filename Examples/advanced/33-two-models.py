"""
Example 33 : Several models at once
===================================
Any number of headless NetLogo sessions can run in the same Python process,
here Fire and Wolf Sheep side by side in two threads.  (One NetLogo window
at most per process: start another Python process for a second window.)
"""
import os, sys, threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo

HERE = os.path.dirname(os.path.abspath(__file__))
FIRE = os.path.join(HERE, "..", "complexe", "Fire", "Fire.nlogo")
WOLF = os.path.join(HERE, "..", "complexe", "Wolf Sheep", "Wolf Sheep Predation.nlogo")


def run_fire(results):
    with NetLogo(FIRE) as fire:
        fire.globals["density"] = 65
        fire.setup()
        steps = fire.run_until("not any? turtles", max_steps=2000)
        results["fire"] = f"{fire.report('burned-trees'):.0f} trees burned in {steps} steps"


def run_wolf_sheep(results):
    with NetLogo(WOLF) as wolf:
        wolf.setup()
        wolf.go(100)
        sheep, wolves = wolf.report(["count sheep", "count wolves"])
        results["wolf sheep"] = f"{sheep:.0f} sheep and {wolves:.0f} wolves after 100 ticks"


if __name__ == "__main__":
    results = {}
    threads = [threading.Thread(target=run_fire, args=(results,)),
               threading.Thread(target=run_wolf_sheep, args=(results,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for name, summary in sorted(results.items()):
        print(f"{name:10s}: {summary}")
