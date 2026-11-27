"""
Example 44 : Inequality in an exchange economy, a tax set by Python
===================================================================
500 people start with 25 coins each.  They walk around and, at each tick,
everyone who has money gives one coin to a random person nearby.  Nobody is
favoured, yet wealth becomes unequal: the Gini coefficient climbs from 0
towards 0.5.

Python is the regulator.  Every 10 ticks it computes the Gini coefficient
(in Python, from all the wealths read in one call) and adjusts a wealth tax
with a proportional controller to keep the Gini near a target; the tax is
shared equally between everybody.  The size and colour of a person show
their wealth (small and dark: poor, big and bright: rich).

    no tax    the economy alone
    regulated Python's tax, target Gini 0.25

The NetLogo model is written by Python (the bundled model with its Code tab
replaced).
"""
import atexit, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import BUNDLED_MODEL, Code, NetLogo, colors

PEOPLE, WEALTH, TICKS, EVERY, TARGET, GAIN = 500, 25, 600, 10, 0.25, 0.5

MODEL_CODE = """
breed [ pyturtles pyturtle ]
directed-link-breed [ streets street ]
turtles-own [ wealth ]

to setup
  clear-all
  resize-world 0 40 0 40
  reset-ticks
end

to go
  ask turtles [ rt random 60 - 30 fd 0.5 ]
  ask turtles with [ wealth > 0 ] [
    let partner one-of other turtles in-radius 2
    if partner != nobody [ set wealth wealth - 1  ask partner [ set wealth wealth + 1 ] ] ]
  recolor
  tick
end

to tax [ rate ]     ; take rate * wealth from everybody, share it equally
  let collected 0
  ask turtles [ let t floor (rate * wealth)  set wealth wealth - t  set collected collected + t ]
  let share floor (collected / count turtles)
  ask turtles [ set wealth wealth + share ]
end

to recolor
  ask turtles [ set color scale-color yellow wealth -30 90  set size min list 4 (0.8 + wealth / 20) ]
end
"""


def write_model():
    with open(BUNDLED_MODEL, encoding="utf-8") as source:
        widgets = source.read().split("@#$#@#$#@", 1)[1]
    folder = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, folder, ignore_errors=True)     # removed when the script ends
    path = os.path.join(folder, "economy.nlogo")
    with open(path, "w", encoding="utf-8") as model:
        model.write(MODEL_CODE + "@#$#@#$#@" + widgets)
    return path


def gini(values):
    """Gini coefficient: 0 when everybody has the same, 1 when one person has everything."""
    values = sorted(values)
    n, total = len(values), sum(values)
    if not total:
        return 0.0
    weighted = sum((2 * i - n + 1) * v for i, v in enumerate(values))
    return weighted / (n * total)


def run(nl, policy, pen_color, delay):
    nl.random_seed(5)
    nl.setup()
    nl.create_turtles(PEOPLE, shape="person", wealth=WEALTH,
                      xcor=Code("random-xcor"), ycor=Code("random-ycor"))
    nl.command("recolor")
    nl.set_current_plot("My Plot")
    nl.set_plot_y_range(0, 0.6)
    nl.create_temporary_plot_pen(policy)
    nl.set_plot_pen_color(pen_color)
    rate, history = 0.0, []
    for t in range(TICKS):
        nl.go()
        if t % EVERY == 0:
            g = gini(nl.report("[wealth] of turtles"))
            history.append(g)
            nl.plotxy(t, g)
            if policy == "regulated":               # proportional control of the tax rate
                rate = min(0.5, max(0.0, rate + GAIN * (g - TARGET) * EVERY / 100))
                if rate:
                    nl.command(f"tax {rate:.4f}", "recolor")
            time.sleep(delay)
    wealth = nl.report("[wealth] of turtles")
    richest = sorted(wealth, reverse=True)[:PEOPLE // 10]
    return {"policy": policy, "gini": sum(history[-10:]) / 10, "rate": rate,
            "top10": sum(richest) / sum(wealth), "poor": sum(1 for w in wealth if w < 5)}


if __name__ == "__main__":
    with NetLogo(write_model(), gui=True) as nl:    # gui=False: same run without the window
        results = [run(nl, "no tax", colors.RED, delay=0.03),
                   run(nl, "regulated", colors.BLUE, delay=0.03)]
        time.sleep(2)

    print("policy      Gini   richest 10 % own   people under 5 coins   final tax rate")
    for r in results:
        print(f"{r['policy']:10s} {r['gini']:5.2f}   {r['top10']:15.0%}   {r['poor']:20d}   {r['rate']:13.1%}")
