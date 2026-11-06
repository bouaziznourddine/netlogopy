"""
Example 17 : set_color / get_color
Change and read the color of a turtle.
See NetLogo color chart: https://ccl.northwestern.edu/netlogo/docs/images/colors.jpg
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    # NetLogo color codes: 15=red, 55=green, 95=blue, 35=orange, 125=violet
    colors = [15, 55, 95, 35, 125]
    for c in colors:
        time.sleep(1)
        car01.set_color(c)
        current = car01.get_color()
        print(f"Color set to {c} -> NetLogo reports: {current}")
        car01.fd(3)

    n.close_model()
