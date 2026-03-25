"""
Example 19 : hideturtle / showturtle
Hide then show a turtle.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    for i in range(10):
        time.sleep(1)
        if i == 3:
            print("Hiding car01...")
            car01.hideturtle()
        if i == 7:
            print("Showing car01...")
            car01.showturtle()
        car01.fd(2)

    n.close_model()
