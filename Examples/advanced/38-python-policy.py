"""
Example 38 : A Python policy inside a NetLogo epidemic
======================================================
NetLogo simulates an epidemic: people walk, the sick infect the people
around them, and recover after 20 ticks.  Every 5 ticks, Python looks at the
population and decides who gets one of its few vaccine doses.  Three
policies are compared on the same scenario:

    none      no vaccination
    random    doses given to random healthy people
    targeted  doses given to the healthy people with the most sick neighbours

Any Python code can take the decision: a heuristic as here, an optimiser, or
a trained model.  The NetLogo model itself is written by Python: the
bundled model with its Code tab replaced.
"""
import os, random, sys, tempfile, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import BUNDLED_MODEL, Code, NetLogo, colors

PEOPLE, SICK_AT_START, DOSES, EVERY, HORIZON = 300, 5, 6, 5, 150
PENS = [("none", colors.RED), ("random", colors.ORANGE), ("targeted", colors.BLUE)]
CURVES = {}                                         # policy -> number of sick per tick

MODEL_CODE = """
breed [ pyturtles pyturtle ]
directed-link-breed [ streets street ]
turtles-own [ state days-sick ]        ; state: "healthy", "sick", "immune"

to setup
  clear-all
  resize-world 0 40 0 40
  reset-ticks
end

to go
  ask turtles [ rt random 60 - 30 fd 0.5 ]
  ask turtles with [ state = "sick" ] [
    ask other turtles in-radius 1.5 with [ state = "healthy" ] [
      if random-float 1 < 0.25 [ become "sick" ] ]
    set days-sick days-sick + 1
    if days-sick > 20 [ become "immune" ] ]
  tick
end

to become [ new-state ]
  set state new-state
  set color ifelse-value state = "healthy" [ green ] [ ifelse-value state = "sick" [ red ] [ sky ] ]
end
"""


def write_model():
    """The bundled model (view, plot, widgets) with MODEL_CODE as its Code tab."""
    with open(BUNDLED_MODEL, encoding="utf-8") as source:
        widgets = source.read().split("@#$#@#$#@", 1)[1]
    path = os.path.join(tempfile.mkdtemp(), "epidemic.nlogo")
    with open(path, "w", encoding="utf-8") as model:
        model.write(MODEL_CODE + "@#$#@#$#@" + widgets)
    return path


def vaccinate(nl, policy, rng):
    healthy = nl.turtles(where='state = "healthy"')
    if policy == "none" or not healthy:
        return
    if policy == "random":
        chosen = rng.sample(healthy, min(DOSES, len(healthy)))
    else:   # targeted: one NetLogo call gives the exposure of every healthy person
        exposure = nl.of(healthy, 'count other turtles in-radius 3 with [ state = "sick" ]')
        ranked = sorted(zip(exposure, healthy), key=lambda pair: -pair[0])
        chosen = [person for count, person in ranked[:DOSES] if count > 0]
    if chosen:
        nl.ask(chosen, 'become "immune"')


def run(nl, policy, pen_color, delay):
    nl.random_seed(11)                              # same people, same first cases
    nl.setup()                                      # clear-all also clears the plot
    nl.set_current_plot("My Plot")
    nl.set_plot_x_range(0, HORIZON)
    nl.set_plot_y_range(0, PEOPLE // 2)
    for pen, color in PENS:                         # every curve, the past ones redrawn
        nl.create_temporary_plot_pen(pen)
        nl.set_plot_pen_color(color)
        for value in CURVES.get(pen, []):
            nl.plot(value)
    nl.set_current_plot_pen(policy)
    nl.create_turtles(PEOPLE, shape="person", size=2, xcor=Code("random-xcor"),
                      ycor=Code("random-ycor"))
    nl.ask("turtles", 'become "healthy"')
    nl.ask(f"n-of {SICK_AT_START} turtles", 'become "sick"')
    rng = random.Random(11)
    peak, sick = 0, SICK_AT_START
    for t in range(HORIZON):
        if t % EVERY == 0:
            vaccinate(nl, policy, rng)
        nl.go()
        sick = nl.count("turtles", 'state = "sick"')
        peak = max(peak, sick)
        CURVES.setdefault(policy, []).append(sick)
        nl.plot(sick, plot="My Plot", pen=policy)
        time.sleep(delay)
        if sick == 0:
            break
    return {"policy": policy, "peak": peak, "ill": nl.count("turtles", "days-sick > 0"),
            "ticks": t + 1}


if __name__ == "__main__":
    with NetLogo(write_model(), gui=True) as nl:    # gui=False: same run without the window
        results = [run(nl, policy, color, delay=0.02) for policy, color in PENS]
        time.sleep(2)

    print(f"{'policy':10s} {'peak sick':>9s} {'fell ill':>9s} {'ticks':>6s}")
    for r in results:
        print(f"{r['policy']:10s} {r['peak']:9d} {r['ill']:9d} {r['ticks']:6d}")
