"""
Example 16 : set_heading / get_heading
Set and read the heading (direction) of a turtle.
NetLogo heading: 0=North, 90=East, 180=South, 270=West.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    headings = [0, 90, 180, 270]   # North, East, South, West
    for h in headings:
        time.sleep(1)
        car01.set_heading(h)
        current = car01.get_heading()
        print(f"Heading set to {h} → NetLogo reports: {current}")
        car01.fd(5)

    n.close_model()
