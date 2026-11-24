"""
Example 36 : Add interface widgets from Python
==============================================
The items of NetLogo's "Add" menu (button, slider, switch, chooser, input,
monitor, plot, output, note) created by Python in the NetLogo window.

The widgets are placed in a column to the right of the model's own widgets
(or where x= and y= say).  Each slider, switch, chooser and input becomes a
global of the model, read and changed with nl.globals[...].  They last for
the session: File > Save As in NetLogo keeps them in a model.
"""
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

with NetLogo(gui=True) as nl:                 # widgets need the window
    nl.setup()
    if nl.gui:                                # False with NETLOGOPY_HEADLESS=1
        nl.add_note("Widgets added by Python", font_size=13)
        nl.add_slider("walkers", 1, 200, 50, 1)
        nl.add_slider("step-size", 0.1, 2, 0.5, 0.1, units="patches")
        nl.add_switch("trails", True)
        nl.add_chooser("walker-color", ["red", "blue", "green"], 0)
        nl.add_button("create", "clear-turtles clear-drawing\n"
                                "create-pyturtles walkers [\n"
                                "  set color runresult walker-color\n"
                                "  set shape \"circle\" set size 1\n"
                                "  if trails [ pen-down ] ]")
        nl.add_button("walk", "rt random 50 - 25 fd step-size",
                      agents="turtles", forever=True, key="W")
        nl.add_monitor("mean [distancexy 30 30] of pyturtles", "mean distance", decimals=2)
        nl.add_plot("Spread", {"distance": "plot mean [distancexy 30 30] of pyturtles"},
                    x_label="tick", y_label="patches", colors={"distance": colors.RED})

        # Python sets the widgets and presses the buttons like a user would
        nl.globals["walkers"] = 80
        nl.globals["walker-color"] = "blue"
        nl.press_button("create")
        nl.command("ask pyturtles [ setxy 30 30 ]")
        for _ in range(60):
            nl.command("ask pyturtles [ rt random 50 - 25 fd step-size ]")
            nl.command("update-plots")
            time.sleep(0.03)
        print("mean distance from the centre:",
              round(nl.report("mean [distancexy 30 30] of pyturtles"), 2))
        time.sleep(3)
    else:
        print("interface widgets need the NetLogo window (NETLOGOPY_HEADLESS is set)")
