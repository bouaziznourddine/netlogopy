"""
Example 2 : Moving a turtle (0.x API)
=====================================
Forward and back, turns, headings, jumps to a point or to another turtle,
facing a turtle, positions and distances.

    fd, bk, rt, lt, set_heading, get_heading, setxy, move_to, face_to,
    getxyturtle, distanceto, distancebetween
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
    target = pyturtle(n, x=50, y=10, shape="flag", size_shape=4, color=55, name="target", labelcolor=55)

    # forward and back
    for _ in range(10):
        car01.fd(1); time.sleep(0.05)
    for _ in range(10):
        car01.bk(1); time.sleep(0.05)

    # a circle to the right, then to the left: 36 turns of 10 degrees
    for turn in (car01.rt, car01.lt):
        for _ in range(36):
            turn(10); car01.fd(1); time.sleep(0.03)

    # the four headings
    for heading in (0, 90, 180, 270):
        car01.set_heading(heading)
        print(f"heading {heading} -> NetLogo reports {car01.get_heading()}")
        car01.fd(5); time.sleep(0.3)

    # jump to a point, face another turtle, walk to it
    car01.setxy(10, 50)
    print("position after setxy:", getxyturtle(n, car01))
    car01.face_to(target)
    while car01.distanceto(target) > 1:
        car01.fd(1); time.sleep(0.05)
    print("distance to target:", round(distancebetween(n, car01, target), 2))

    # or jump straight onto it
    car01.setxy(30, 30)
    car01.move_to(target)
    print("after move_to:", getxyturtle(n, car01), "=", getxyturtle(n, target))
    time.sleep(2)
    n.close_model()
