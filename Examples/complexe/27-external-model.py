"""
Example 27 : Integrating an Existing NetLogo Model with Python
==============================================================
Control an existing NetLogo model (one not written for netlogopy) from Python.

  - run_netlogo_model() opens the model WITHOUT running setup, so its
    widgets can be configured first (run_netlogo() runs setup right away).
  - pyturtle and street need the pyturtles / streets breeds: the model's
    Code tab must include base.nls (  __includes [ "base.nls" ]  ).
    reset_base_file(folder) copies base.nls next to your model.

Workflow:
  1. run_netlogo_model()                      <- open the .nlogo file
  2. set_slider() / set_switch() / set_chooser()  <- configure parameters
  3. run_command(n, "setup")                  <- the model's own setup
  4. add pyturtle agents                      <- Python agents in the model
  5. loop: run_command(n, "go") + move pyturtles + read monitors

This example uses the copy of NetLogo's "Wolf Sheep Predation" model stored
in "Wolf Sheep/" (it includes base.nls).
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    path_model = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "Wolf Sheep", "Wolf Sheep Predation.nlogo")

    # Step 1 : open the model WITHOUT setup
    n = run_netlogo_model(netlogo_home, path_model)
    print("Model opened.")

    # Step 2 : configure the widgets (they are global variables of the model)
    set_chooser(n, "model-version", "sheep-wolves-grass")
    set_slider(n, "initial-number-sheep", 100)
    set_slider(n, "initial-number-wolves", 50)
    set_slider(n, "grass-regrowth-time", 30)
    set_switch(n, "show-energy?", False)
    print("Widgets configured:")
    print(f"  model-version = {get_chooser(n, 'model-version')}")
    print(f"  sheep         = {get_slider(n, 'initial-number-sheep'):.0f}")
    print(f"  wolves        = {get_slider(n, 'initial-number-wolves'):.0f}")
    print(f"  grass-time    = {get_slider(n, 'grass-regrowth-time'):.0f}")
    print(f"  show-energy?  = {get_switch(n, 'show-energy?')}")

    # Step 3 : the model's own setup (it resets the ticks)
    run_command(n, "setup")
    print("Setup complete.")

    # Step 4 : a Python-controlled agent inside the running model
    observer = pyturtle(n, x=0, y=0, shape="circle", size_shape=3, color=105, name="observer")

    # Step 5 : main loop
    for i in range(40):
        time.sleep(0.2)
        run_command(n, "go")                    # the model's go also ticks

        sheep = get_monitor(n, "count sheep")
        wolves = get_monitor(n, "count wolves")
        grass = get_monitor(n, "count patches with [pcolor = green]")
        tick = get_ticks(n)
        print(f"[tick {tick:3d}]  sheep={sheep:.0f}  wolves={wolves:.0f}  grass={grass:.0f}")

        # Move the Python observer in circles
        observer.rt(9)
        observer.fd(1)

        # Adjust the grass regrowth time from Python, based on the sheep population
        if sheep < 30:
            set_slider(n, "grass-regrowth-time", 10)   # grass grows back faster
        elif sheep > 150:
            set_slider(n, "grass-regrowth-time", 50)   # slower

    print("Done.")
    n.close_model()
