"""
Example 26 : Plot widget
=========================
Control a NetLogo Plot from Python.
The plot must exist in the model: the bundled model has "My Plot".

Functions:
  set_current_plot(n, name)      -> activate a plot by name
  set_plot_pen(n, pen)           -> activate a pen
  create_plot_pen(n, pen)        -> create a temporary pen
  plot_add(n, value)             -> add data point (auto x)
  plot_xy(n, x, y)               -> add data point at (x,y)
  set_plot_pen_color(n, color)   -> change pen color
  set_plot_pen_mode(n, mode)     -> 0=line, 1=bar, 2=point
  set_plot_x_range(n, min, max)  -> set x axis range
  set_plot_y_range(n, min, max)  -> set y axis range
  clear_plot(n)                  -> clear all data
  auto_plot_on(n) / auto_plot_off(n)
"""
import time, math, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    car01 = pyturtle(n, x=30, y=30, shape="car", size_shape=4, color=15, name="car01")

    # The bundled model has a Plot widget named "My Plot"
    set_current_plot(n, "My Plot")
    create_plot_pen(n, "distance")      # a temporary pen for this run
    set_plot_pen_color(n, 15)           # red
    set_plot_pen_mode(n, 0)             # line
    set_plot_x_range(n, 0, 30)
    set_plot_y_range(n, 0, 10)

    origin_x, origin_y = 30.0, 30.0
    for i in range(30):
        time.sleep(0.3)
        do_tick(n)
        car01.rt(12)
        car01.fd(1)
        x = car01.get_xcor()
        y = car01.get_ycor()
        dist = car01.distance_to_point(origin_x, origin_y)
        print(f"[tick {get_ticks(n):3d}]  pos=({x:.1f},{y:.1f})  dist={dist:.2f}")

        # Plot the distance over time
        set_current_plot(n, "My Plot")
        set_plot_pen(n, "distance")
        plot_add(n, dist)

    n.close_model()
