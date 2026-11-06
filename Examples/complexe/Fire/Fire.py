"""
Fire model + Python agents
==========================
Opens NetLogo's classic Fire model (Fire.nlogo, next to this file), which
includes base.nls to get the pyturtles and streets breeds, and drives two
Python cars while the fire spreads.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    path_model = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Fire.nlogo")

    n = run_netlogo_model(netlogo_home, path_model)   # open without running setup
    resize_world(n, 0, 70, 0, 55)
    set_slider(n, "density", 62)
    run_command(n, "setup")

    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
    car02 = pyturtle(n, x=5, y=5, shape="car", size_shape=4, color=55, name="car02", labelcolor=55)
    street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, shape="default", thickness=0.5)

    for i in range(100):
        run_command(n, "go")
        time.sleep(0.1)
        car01.fd(1)
        if i % 20 == 0:
            car01.setxy(10, 10)
        burned = get_monitor(n, "burned-trees")
        print(f"step {i:3d}: {burned:.0f} trees burned")

    n.close_model()
