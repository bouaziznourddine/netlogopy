"""
Example 3 : Appearance and drawing (0.x API)
============================================
Colors, sizes, shapes, labels, hiding and showing a turtle, and drawing with
its pen.

    set_color, get_color, set_size, get_size, set_shape, set_label,
    hideturtle, showturtle, pen_down, pen_up, stamp, clear_drawing
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=10, y=10, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

    # colors: 15 red, 55 green, 95 sky, 35 brown, 125 magenta
    for color in (15, 55, 95, 35, 125):
        car01.set_color(color)
        print(f"color {color} -> NetLogo reports {car01.get_color()}")
        car01.fd(2); time.sleep(0.3)

    # sizes, shapes and labels
    for size in range(2, 9, 2):
        car01.set_size(size)
        car01.set_label(f"size {car01.get_size():.0f}")
        time.sleep(0.3)
    for shape in ("truck", "airplane", "person_0", "car"):
        car01.set_shape(shape)
        time.sleep(0.4)
    car01.set_size(4)

    # hide and show
    car01.hideturtle(); time.sleep(0.5)
    car01.showturtle(); time.sleep(0.5)

    # draw a square with the pen, then stamp the shape three times
    car01.setxy(15, 15)
    car01.set_heading(0)
    car01.pen_down()
    for side in range(4):
        for _ in range(30):
            car01.fd(1); time.sleep(0.01)
        car01.rt(90)
    car01.pen_up()
    for x, y in ((20, 50), (30, 50), (40, 50)):
        car01.setxy(x, y)
        car01.stamp()
        time.sleep(0.3)
    time.sleep(2)
    clear_drawing(n)
    n.close_model()
