"""
Example 4 : Ticks, counting and output (0.x API)
================================================
Advance the simulation clock, count the Python turtles, and write to the
command center and to the output area.

    do_tick, get_ticks, reset_ticks, count_pyturtles, get_all_pyturtles,
    netlogoshow, nl_output_print, run_command
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)
    cars = [pyturtle(n, x=5 + 10 * i, y=10, shape="car", size_shape=3, color=15 + 20 * i,
                     name=f"car{i}") for i in range(5)]
    print("pyturtles in NetLogo:", count_pyturtles(n))
    print("pyturtles in Python:", [car.id for car in get_all_pyturtles()])

    reset_ticks(n)
    for _ in range(20):
        do_tick(n)                                  # advance the clock
        tick = get_ticks(n)
        for car in cars:
            car.set_heading(0)
            car.fd(1)
        cars[0].set_label(f"t={tick:.0f}")
        netlogoshow(n, f"tick {tick:.0f}")          # command center
        nl_output_print(n, f"tick {tick:.0f}: car0 at {cars[0].get_ycor():.0f}")   # output area
        time.sleep(0.1)

    run_command(n, "ask pyturtles with [who mod 2 = 0] [ die ]")   # any NetLogo code
    print("after removing the even ones:", count_pyturtles(n))
    time.sleep(2)
    n.close_model()
