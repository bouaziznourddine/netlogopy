"""
Example 34 : Save and restore
=============================
Export an image of the view, the plots and the whole model state, then
restore the state later with import_world.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, Code

if __name__ == "__main__":
    out = os.path.join(os.getcwd(), "netlogopy-output")
    os.makedirs(out, exist_ok=True)
    with NetLogo() as nl:
        nl.setup()
        nl.create_turtles(30, "pyturtles", shape="car", size=3,
                          xcor=Code("random-xcor"), ycor=Code("random-ycor"))
        for _ in range(10):
            nl.ask("pyturtles", "rt random 30 fd 1")
            nl.tick()
            nl.plot(nl.report("mean [xcor] of pyturtles"), plot="My Plot")

        print("view image :", nl.export_view(os.path.join(out, "view.png")))
        print("plot data  :", nl.export_plot("My Plot", os.path.join(out, "plot.csv")))
        state = nl.export_world(os.path.join(out, "world.csv"))
        print("world state:", state)
        before = nl.of("pyturtles", "(list xcor ycor)")

        nl.clear_all()
        print("after clear-all:", nl.count("pyturtles"), "cars")
        nl.import_world(state)
        print("after import-world:", nl.count("pyturtles"), "cars, ticks =", nl.ticks)
        assert nl.of("pyturtles", "(list xcor ycor)") == before
