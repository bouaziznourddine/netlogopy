"""
Example 27 : Integrating an Existing NetLogo Model with Python
==============================================================
This example shows the correct way to control an *existing* NetLogo model
(one that was NOT created by netlogopy) from Python.

KEY DIFFERENCE vs the built-in model:
  • Use  run_netlogo_model()   instead of  run_netlogo()
    → does NOT call setup automatically; lets you configure widgets first
  • Use  resize_world_direct() instead of  resize_world()
    → uses a native NetLogo command; does not require base.nls

Workflow:
  1. run_netlogo_model()          ← open the .nlogo file
  2. set_slider() / set_switch()  ← configure parameters (before setup)
  3. run_command(n, "setup")      ← run the model's own setup
  4. add pyturtle agents          ← mix Python agents into the model
  5. loop: run_command(n, "go") + move pyturtles + read monitors

Widget functions used:
  get_slider / set_slider        → Slider  widgets (global variables)
  get_switch / set_switch        → Switch  widgets (boolean globals)
  get_chooser / set_chooser      → Chooser widgets
  get_monitor / get_monitor      → any NetLogo reporter expression
  set_current_plot / plot_add    → Plot    widgets

Note: This example targets the classic "Wolf Sheep Predation" model that
ships with NetLogo. Adjust path_model to point to any .nlogo file you want.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"

    # Path to an existing NetLogo model
    # (e.g. the Wolf Sheep model bundled with NetLogo)
    path_model = (
        "C:/Program Files/NetLogo 6.2.2/models/Sample Models/"
        "Biology/Wolf Sheep Predation.nlogo"
    )

    # ── Step 1 : open the model WITHOUT auto-setup ────────────────────────────
    n = run_netlogo_model(netlogo_home, path_model)
    print("Model opened.")

    # ── Step 2 : configure Slider / Switch widgets before setup ───────────────
    # These global variables must exist in the .nlogo model.
    set_slider(n, "initial-number-sheep", 100)
    set_slider(n, "initial-number-wolves", 50)
    set_slider(n, "grass-regrowth-time", 30)
    set_switch(n, "grass?", True)

    print("Sliders configured:")
    print(f"  sheep        = {get_slider(n, 'initial-number-sheep'):.0f}")
    print(f"  wolves       = {get_slider(n, 'initial-number-wolves'):.0f}")
    print(f"  grass-time   = {get_slider(n, 'grass-regrowth-time'):.0f}")
    print(f"  grass?       = {get_switch(n, 'grass?')}")

    # ── Step 3 : resize world (direct command — no base.nls needed) ──────────
    resize_world_direct(n, -25, 25, -25, 25)

    # ── Step 4 : run the model's own setup ───────────────────────────────────
    run_command(n, "setup")
    reset_ticks(n)
    print("Setup complete.")

    # ── Step 5 : add Python-controlled agents into the running model ──────────
    observer = pyturtle(n, x=0, y=0, shape="circle", size_shape=3,
                        color=105, name="observer")

    # ── Step 6 : main loop ────────────────────────────────────────────────────
    for i in range(40):
        time.sleep(0.2)

        # Advance the model one step
        run_command(n, "go")
        do_tick(n)

        # Read monitor values (any valid NetLogo reporter)
        sheep  = get_monitor(n, "count sheep")
        wolves = get_monitor(n, "count wolves")
        grass  = get_monitor(n, "count patches with [pcolor = green]")
        tick   = get_ticks(n)

        print(f"[tick {tick:3d}]  sheep={sheep}  wolves={wolves}  grass={grass}")

        # Move the Python observer in circles
        observer.rt(9)
        observer.fd(1)
        observer.set_label(f"t={tick}")

        # Dynamically adjust grass regrowth speed based on sheep population
        if isinstance(sheep, str):
            sheep_count = int(float(sheep)) if sheep else 0
        else:
            sheep_count = int(sheep)

        if sheep_count < 30:
            set_slider(n, "grass-regrowth-time", 10)   # speed up grass
        elif sheep_count > 150:
            set_slider(n, "grass-regrowth-time", 50)   # slow down grass

    print("Done.")
    n.close_model()
