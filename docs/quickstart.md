# Quick start

![Eight cars driven by Python](assets/gifs/quickstart.gif){ .demo width="380" }

```python
import time
from netlogopy import NetLogo, colors

nl = NetLogo(gui=True)               # the bundled model, in the NetLogo window
nl.setup()

cars = nl.create_turtles(8, "pyturtles", ordered=True, shape="car", size=4,
                         color=colors.RED, xcor=30, ycor=30)
for step in range(40):
    for car in cars:
        car.forward(0.5).right(3)    # methods can be chained
    nl.tick()
    time.sleep(0.05)

leader = cars[0]
leader.color = colors.BLUE           # turtle variables are properties
print(leader.xy, leader.heading)
print(leader.in_radius(10, "pyturtles", other=True))   # a list of Turtle objects
print(nl.report("mean [xcor] of pyturtles"))            # a float
print(nl.report(["count turtles", "ticks"]))            # [8.0, 40.0]

nl.command("ask pyturtles with [xcor > 30] [ set color green ]")
nl.close()                           # also done automatically at exit
```

The same script runs without a window with `NetLogo()` (or `gui=False`).

## The three things to know

1. **A session is a model.** `NetLogo(model)` opens a model, headless by
   default, in the window with `gui=True`. Without a model, it opens the model
   bundled with netlogopy (a 61 x 61 world, the `pyturtles` and `streets`
   breeds, and demo widgets).
2. **Any NetLogo code runs.** `nl.command("...")` runs commands,
   `nl.report("...")` evaluates a reporter and returns a Python value.
3. **Agents are Python objects.** `create_turtles`, `turtle(who)`,
   `patch(x, y)` and every agentset reporter return `Turtle`, `Patch` and
   `Link` objects, with properties and methods.

Next: the [guide](guide/sessions.md), or the [examples](examples.md).
