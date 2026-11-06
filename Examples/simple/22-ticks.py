"""
Example 22 : get_ticks / do_tick
Use NetLogo ticks as a simulation clock.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=10, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for _ in range(20):
        time.sleep(0.3)
        do_tick(n)                        # advance simulation clock
        tick = get_ticks(n)
        car01.fd(1)
        car01.set_label(f"t={tick}")      # show tick on turtle
        print(f"Tick: {tick}  |  pos: ({car01.get_xcor():.1f}, {car01.get_ycor():.1f})")

    n.close_model()
