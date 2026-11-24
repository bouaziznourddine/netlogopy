"""
Example 43 : Evacuating a room, exits chosen by Python
======================================================
A crowd leaves a hall with two exits.  NetLogo moves the people (one step
per tick, nobody walks through someone else) and lets at most two people
through each exit per tick.  Python chooses each person's exit:

    nearest   everybody goes to the nearest exit
    balanced  every 3 ticks, Python gives each person the exit with the
              shortest expected time: walking time + people already
              heading there and closer to it (queue / exit capacity)

The crowd starts near the left exit: with "nearest" it queues there while
the right exit stays empty; Python's assignment splits the crowd.

The NetLogo model is written by Python (the bundled model with its Code tab
replaced).
"""
import math, os, sys, tempfile, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import BUNDLED_MODEL, Code, NetLogo

PEOPLE, SPEED, CAPACITY, EVERY, MAX_TICKS = 200, 0.5, 2, 3, 400
EXITS = {"left": (0, 12), "right": (44, 12)}

MODEL_CODE = """
breed [ pyturtles pyturtle ]
directed-link-breed [ streets street ]
turtles-own [ exit-x exit-y ]

to setup
  clear-all
  resize-world 0 44 0 24
  ask patches [ set pcolor ifelse-value wall? [ gray - 2 ] [ white ] ]
  ask patches with [ (pxcor = 0 or pxcor = max-pxcor) and abs (pycor - 12) <= 1 ] [ set pcolor lime ]
  reset-ticks
end

to-report wall?
  report pxcor = 0 or pxcor = max-pxcor or pycor = 0 or pycor = max-pycor
end

to-report free? [ step-length ]
  let ahead patch-ahead step-length
  report ahead != nobody and [ pcolor ] of ahead != gray - 2
         and not any? other turtles in-cone 0.9 70
end

to go [ step-length exit-capacity ]
  ask turtles [
    facexy exit-x exit-y
    if not free? step-length [ rt one-of [ -50 50 ] ]   ; blocked: try a step aside
    if free? step-length [ fd step-length ] ]
  foreach [ 0 44 ] [ x ->
    ask up-to-n-of exit-capacity turtles with [ exit-x = x and distancexy x 12 < 1.6 ] [ die ] ]
  tick
end
"""


def write_model():
    with open(BUNDLED_MODEL, encoding="utf-8") as source:
        widgets = source.read().split("@#$#@#$#@", 1)[1]
    path = os.path.join(tempfile.mkdtemp(), "evacuation.nlogo")
    with open(path, "w", encoding="utf-8") as model:
        model.write(MODEL_CODE + "@#$#@#$#@" + widgets)
    return path


def assign(nl, policy):
    """Give each person an exit; one call to read the crowd, one per exit to set it."""
    people = nl.turtles()
    if not people:
        return
    positions = nl.of(people, "(list xcor ycor)")
    choice = {name: [] for name in EXITS}
    if policy == "nearest":
        for person, (x, y) in zip(people, positions):
            name = min(EXITS, key=lambda e: math.dist((x, y), EXITS[e]))
            choice[name].append(person)
    else:   # balanced: closest people first, each takes the exit that gets them out soonest
        queue = {name: 0 for name in EXITS}
        order = sorted(zip(people, positions), key=lambda p: min(math.dist(p[1], e) for e in EXITS.values()))
        for person, (x, y) in order:
            cost = {name: max(math.dist((x, y), xy) / SPEED, queue[name] / CAPACITY)
                    for name, xy in EXITS.items()}
            name = min(cost, key=cost.get)
            queue[name] += 1
            choice[name].append(person)
    for name, chosen in choice.items():
        if chosen:
            x, y = EXITS[name]
            nl.ask(chosen, f"set exit-x {x}", f"set exit-y {y}", f"set color {15 if name == 'left' else 105}")


def run(nl, policy, delay):
    nl.random_seed(3)
    nl.setup()
    nl.create_turtles(PEOPLE, shape="person", size=1.2, xcor=Code("2 + random-float 14"),
                      ycor=Code("2 + random-float 20"))
    nl.ask("turtles", "move-to patch-here")      # one person per place to start
    nl.ask("turtles", "while [ any? other turtles-here ] [ move-to one-of patches with "
                      "[ pxcor > 1 and pxcor < 30 and pycor > 1 and pycor < 23 and not any? turtles-here ] ]")
    nl.set_current_plot("My Plot")
    nl.create_temporary_plot_pen(policy)
    nl.set_plot_pen_color(15 if policy == "nearest" else 105)
    while nl.count("turtles") and nl.ticks < MAX_TICKS:
        if nl.ticks % EVERY == 0:
            assign(nl, policy)
        nl.command(f"go {SPEED} {CAPACITY}")
        nl.plot(nl.count("turtles"))
        time.sleep(delay)
    return {"policy": policy, "ticks": nl.ticks, "left": nl.count("turtles")}


if __name__ == "__main__":
    with NetLogo(write_model(), gui=True) as nl:    # gui=False: same run without the window
        results = [run(nl, policy, delay=0.02) for policy in ("nearest", "balanced")]
        time.sleep(2)

    print("policy     evacuation time")
    for r in results:
        print(f"{r['policy']:9s}  {r['ticks']:4.0f} ticks" + (f"  ({r['left']:.0f} still inside)" if r["left"] else ""))
