"""
Example 25 : Monitor widget
============================
Read any NetLogo expression from Python — exactly what a Monitor widget displays.
get_monitor(n, expression) evaluates any valid NetLogo reporter.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    # Create 5 cars at random positions
    cars = [pyturtle(n, x=i*10, y=30, shape="car", size_shape=3,
                     color=15 + i*20, name=f"c{i}") for i in range(5)]

    for i in range(20):
        time.sleep(0.5)

        # Monitor expressions — same as NetLogo Monitor widgets
        total      = get_monitor(n, "count pyturtles")
        world_w    = get_monitor(n, "world-width")
        world_h    = get_monitor(n, "world-height")
        ticks_now  = get_monitor(n, "ticks")

        print(f"[tick {i:2d}]  agents={total}  world={world_w}×{world_h}  ticks={ticks_now}")

        do_tick(n)
        for car in cars:
            car.rt(15)
            car.fd(1)

    n.close_model()
