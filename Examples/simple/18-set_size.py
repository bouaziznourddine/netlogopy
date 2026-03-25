"""
Example 18 : set_size / get_size
Change and read the size of a turtle.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=30, y=10, shape="car", size_shape=2, color=15, name="car01", labelcolor=15)

    for i in range(8):
        time.sleep(0.8)
        new_size = 2 + i          # grows from 2 to 9
        car01.set_size(new_size)
        current = car01.get_size()
        print(f"Size set to {new_size} → NetLogo reports: {current}")
        car01.fd(2)

    n.close_model()
