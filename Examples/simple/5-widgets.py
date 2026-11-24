"""
Example 5 : Interface widgets (0.x API)
=======================================
Read and set the widgets of the bundled model: the speed slider, the
show-label switch, the scenario chooser, the user-text input, and monitor
expressions.

    get_slider, set_slider, get_switch, set_switch, get_chooser, set_chooser,
    get_input_box, set_input_box, get_monitor
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=5, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
    car01.set_heading(90)

    set_input_box(n, "user-text", "driven by Python")
    set_chooser(n, "scenario", "custom")
    print("scenario:", get_chooser(n, "scenario"), "| text:", get_input_box(n, "user-text"))

    set_slider(n, "speed", 1)
    for i in range(16):
        if i and i % 4 == 0:
            set_slider(n, "speed", get_slider(n, "speed") + 1)       # faster every 4 steps
            set_switch(n, "show-label", not get_switch(n, "show-label"))
        speed = get_slider(n, "speed")
        car01.set_label(f"speed {speed:.0f}" if get_switch(n, "show-label") else "")
        car01.fd(speed * 0.5)
        print(f"step {i:2d}: speed={speed:.0f}  label={get_switch(n, 'show-label')}  "
              f"x={get_monitor(n, '[xcor] of turtle 0'):.1f}  agents={get_monitor(n, 'count pyturtles'):.0f}")
        time.sleep(0.2)
    time.sleep(2)
    n.close_model()
