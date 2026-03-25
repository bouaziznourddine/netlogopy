"""
Example 24 : Switch widget
==========================
Read and write NetLogo Switch values from Python.
A Switch is backed by a boolean global variable (true / false).

How to add a Switch to your .nlogo model:
  Right-click on Interface → Switch
  Variable name, e.g. "show-labels?"
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=10, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    # Create a boolean global (simulates a Switch)
    run_command(n, "set show-label true")

    for i in range(16):
        time.sleep(0.5)

        # Toggle switch every 4 steps
        if i % 4 == 0 and i > 0:
            current = get_switch(n, "show-label")
            set_switch(n, "show-label", not current)

        show = get_switch(n, "show-label")
        print(f"[step {i:2d}]  show-label = {show}")

        # Apply switch effect: show or hide label
        if show:
            car01.set_label(f"i={i}")
        else:
            car01.set_label("")

        car01.fd(2)

    n.close_model()
