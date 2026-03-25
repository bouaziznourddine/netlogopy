"""
Example 15 : bk (backward)
Move a turtle backward.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=55, name="car01", labelcolor=55)

    for i in range(10):
        time.sleep(0.5)
        print(f"Step {i}: moving forward")
        car01.fd(2)

    for i in range(10):
        time.sleep(0.5)
        print(f"Step {i}: moving backward")
        car01.bk(2)

    n.close_model()
