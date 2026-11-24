"""
Example 1 : First agents (0.x API)
==================================
Open the bundled model in the NetLogo window, put an image behind the world,
and create two Python-driven turtles (pyturtle) joined by a street.

    run_netlogo, resize_world, set_background, pyturtle, street, close_model
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    # An image shown behind the agents
    set_background(n, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "netlogopy.png"))

    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=6, color=15, name="car01", labelcolor=15)
    car02 = pyturtle(n, x=40, y=35, shape="car", size_shape=6, color=55, name="car02", labelcolor=55)
    street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, thickness=0.5)
    print("who numbers:", car01.id, car02.id)

    for i in range(20):
        car01.fd(0.5)
        time.sleep(0.1)
    time.sleep(2)
    n.close_model()
