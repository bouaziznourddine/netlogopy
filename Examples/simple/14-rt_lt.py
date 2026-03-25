"""
Example 14 : rt / lt
Turn a turtle right and left.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(36):
        time.sleep(0.2)
        car01.rt(10)   # turn 10 degrees right  →  full circle in 36 steps
        car01.fd(1)

    # Now go left
    for i in range(36):
        time.sleep(0.2)
        car01.lt(10)   # turn 10 degrees left
        car01.fd(1)

    n.close_model()
