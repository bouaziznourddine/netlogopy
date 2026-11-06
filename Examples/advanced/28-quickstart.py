"""
Example 28 : Quick start with the NetLogo class
===============================================
The netlogopy 1.0 API: a NetLogo session object, agents as Python objects,
and NetLogo values converted to Python values.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

if __name__ == "__main__":
    # The bundled model in the NetLogo window (gui=False runs without a window)
    with NetLogo(gui=True) as nl:
        nl.setup()

        # Create 8 cars at the centre, headings spread evenly
        cars = nl.create_turtles(8, "pyturtles", ordered=True, shape="car", size=4,
                                 color=colors.RED, xcor=30, ycor=30)

        for step in range(40):
            for car in cars:
                car.forward(0.5).right(3)        # methods can be chained
            nl.tick()
            time.sleep(0.05)

        leader = cars[0]
        leader.color = colors.BLUE              # turtle variables are properties
        leader.label = "leader"
        print("leader position:", leader.xy, "heading:", leader.heading)
        print("cars near the leader:", leader.in_radius(10, "pyturtles", other=True))

        # Any NetLogo reporter; the result is converted to Python
        print("mean x:", nl.report("mean [xcor] of pyturtles"))
        print("several values:", nl.report(["count turtles", "ticks", "max-pxcor"]))
        print("closest to the centre:", nl.report("min-one-of turtles [distancexy 30 30]"))

        # Any NetLogo command
        nl.command("ask pyturtles with [xcor > 30] [ set color green ]")
        print("green cars:", nl.count("pyturtles", "color = green"))
        time.sleep(2)
