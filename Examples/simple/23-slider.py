"""
Example 23 : Slider widget
==========================
Read and write NetLogo Slider values from Python.
A Slider is backed by a global variable in NetLogo.

How to add a Slider to your .nlogo model:
  Right-click on the Interface tab → Slider
  Give it a variable name, e.g. "speed"
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=10, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    # Simulate a slider called "speed" (global variable in NetLogo)
    # First create the variable in NetLogo
    run_command(n, "set speed 1")          # initial value

    for i in range(20):
        time.sleep(0.4)

        # Read slider value
        speed = get_slider(n, "speed")

        # Increase slider every 5 steps
        if i % 5 == 0 and i > 0:
            set_slider(n, "speed", speed + 1)
            speed = get_slider(n, "speed")

        print(f"[step {i:2d}]  speed = {speed}")
        car01.set_label(f"spd={speed:.0f}")

        # Move the car by slider value
        for _ in range(int(speed)):
            car01.fd(1)

    n.close_model()
