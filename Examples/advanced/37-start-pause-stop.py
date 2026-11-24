"""
Example 37 : Start, pause, change and stop a running model
==========================================================
start() runs the model's go in the background, like a forever button, while
Python keeps watching it.  Here Python watches Wolf Sheep Predation, pauses
it when the sheep population explodes, makes the wolves more efficient,
resumes it, and stops it after a fixed number of steps.

    start(command, interval, max_steps, until), running, paused, pause(),
    resume(), stop(), wait(), steps_run
"""
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "complexe",
                     "Wolf Sheep", "Wolf Sheep Predation.nlogo")

if __name__ == "__main__":
    with NetLogo(MODEL, gui=True) as nl:           # gui=False: same run without the window
        nl.globals["model-version"] = "sheep-wolves-grass"
        nl.globals["initial-number-wolves"] = 30
        nl.random_seed(3)
        nl.setup()

        nl.start("go", interval=0.03, max_steps=400)   # runs in the background
        while nl.running and nl.report("count sheep") < 250:
            time.sleep(0.1)                         # Python is free in the meantime
        nl.pause()                                  # the step in progress finishes first
        print(f"paused at tick {nl.ticks:.0f}: {nl.report('count sheep'):.0f} sheep, "
              f"{nl.report('count wolves'):.0f} wolves")

        nl.globals["wolf-gain-from-food"] = 40      # Python's intervention
        nl.globals["wolf-reproduce"] = 8
        nl.ask("wolves", "set color red")
        time.sleep(1)
        nl.resume()

        for _ in range(10):                         # watch while it runs
            time.sleep(0.5)
            print(f"  tick {nl.ticks:4.0f}: {nl.report('count sheep'):4.0f} sheep, "
                  f"{nl.report('count wolves'):3.0f} wolves")
            if not nl.running:
                break

        ended = nl.wait(timeout=30)                 # True if it ended by itself
        steps = nl.stop()
        print(f"{'ended' if ended else 'stopped'} after {steps} steps, at tick {nl.ticks:.0f}")
        time.sleep(2)
