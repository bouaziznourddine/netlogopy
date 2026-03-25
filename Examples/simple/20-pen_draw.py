"""
Example 20 : pen_down / pen_up / stamp
Draw a path and stamp shapes on the world.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=10, y=10, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    # Draw a square path
    car01.pen_down()
    for side in range(4):
        for _ in range(10):
            time.sleep(0.1)
            car01.fd(1)
        car01.rt(90)

    car01.pen_up()

    # Stamp the shape at 3 positions
    for pos in [(20, 20), (40, 20), (30, 40)]:
        time.sleep(0.5)
        car01.setxy(pos[0], pos[1])
        car01.stamp()
        print(f"Stamped at {pos}")

    n.close_model()
