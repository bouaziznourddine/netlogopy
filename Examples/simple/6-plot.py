"""
Example 6 : Plotting from Python (0.x API)
==========================================
Draw, in the "My Plot" widget of the bundled model, the distance of a car to
the centre while it drives a circle.

    set_current_plot, create_plot_pen, set_plot_pen, set_plot_pen_color,
    set_plot_pen_mode, set_plot_x_range, set_plot_y_range, plot_add, plot_xy
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01")

    set_current_plot(n, "My Plot")
    create_plot_pen(n, "distance")       # a temporary pen for this run
    set_plot_pen_color(n, 15)            # red
    set_plot_pen_mode(n, 0)              # 0 line, 1 bar, 2 point
    set_plot_x_range(n, 0, 60)
    set_plot_y_range(n, 0, 10)

    for i in range(60):
        do_tick(n)
        car01.rt(12)
        car01.fd(1)
        distance = car01.distance_to_point(30, 30)
        set_plot_pen(n, "distance")
        plot_add(n, distance)            # next point of the pen
        time.sleep(0.05)
    print(f"distance to the centre after {get_ticks(n):.0f} ticks: {distance:.2f}")

    create_plot_pen(n, "points")         # plot_xy: explicit coordinates
    set_plot_pen_mode(n, 2)
    set_plot_pen_color(n, 105)
    for x in range(0, 60, 5):
        plot_xy(n, x, 5)
    time.sleep(2)
    n.close_model()
