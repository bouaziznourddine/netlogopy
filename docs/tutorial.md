# Your first simulation in 5 steps

This tutorial builds a small simulation from Python: thirty walkers wander in
the world of the model bundled with netlogopy, one of them is led by Python,
and the number of walkers in the right half of the world is read and plotted.

Each code block continues the previous one: paste them one after the other in
a Python console, or put them in a single script. You need netlogopy and
NetLogo installed ([Installation](installation.md)).

## 1. Open the bundled model

```python
import time
from netlogopy import NetLogo, colors

nl = NetLogo(gui=True)       # the model bundled with netlogopy, in the NetLogo window
nl.setup()                   # its setup procedure: clear-all, a 61 x 61 world, reset-ticks
nl.random_seed(42)           # the same random numbers at every run
print(nl.world_width, nl.world_height, nl.ticks)     # 61 61 0.0
```

`NetLogo(gui=True)` opens the NetLogo window; `NetLogo()` runs the same model
headless (no window: on a server, in a notebook, on macOS). Everything below
works the same way in both modes.

To open your own model instead, give its path: `NetLogo("my-model.nlogo")`.

## 2. Create agents

```python
walkers = nl.create_turtles(30, "pyturtles", shape="person", size=3,
                            color=colors.BLUE, xcor=30, ycor=30)
leader = walkers[0]
leader.color = colors.RED        # turtle variables are Python properties
leader.size = 5
print(len(walkers), leader, leader.xy)               # 30 Turtle(0) [30.0, 30.0]
```

`create_turtles` returns `Turtle` objects. `pyturtles` is a breed of the
bundled model; any breed of your model works, and `nl.create_turtles(30)`
creates plain turtles. Keyword arguments set turtle variables, your model's
own variables included.

## 3. Move them in a loop

```python
for step in range(100):
    nl.ask("pyturtles", "rt random 50 - 25", "fd 0.5")   # every walker, one NetLogo call
    leader.right(5).forward(0.5)                        # the leader, from Python
    nl.tick()
    time.sleep(0.02)                                    # only to watch it in the window
```

Two ways of moving agents, to mix as you like:

- `nl.ask(agents, commands...)` runs NetLogo code for a whole agentset in a
  single call: fast, whatever the number of agents;
- the methods of a `Turtle` (`forward`, `right`, `move_to`, `face`...) move
  one agent from Python logic; they can be chained.

A model with a `go` procedure is run with `nl.go()` or `nl.go(100)`, and any
NetLogo code with `nl.command("...")`.

## 4. Read values

```python
print(nl.ticks)                                         # 100.0
print(leader.xy, leader.heading)                        # NetLogo variables, read live
print(nl.report("count pyturtles with [xcor > 30]"))    # any NetLogo reporter
xs = nl.of("pyturtles", "xcor")                         # one value per walker, by who
print(round(min(xs), 1), round(max(xs), 1))
near = leader.in_radius(5, "pyturtles", other=True)     # a list of Turtle objects
print(len(near), "walkers near the leader")
```

`nl.report()` converts NetLogo values to Python: numbers are floats, lists are
lists, agents are `Turtle`, `Patch` and `Link` objects. A list of reporters is
evaluated in a single call: `nl.report(["count pyturtles", "ticks"])`.

## 5. Plot

In the model's own plot (*My Plot* in the bundled model), one point per tick:

```python
right_half = "count pyturtles with [xcor > 30]"
nl.set_current_plot("My Plot")
for step in range(100):
    nl.ask("pyturtles", "rt random 50 - 25", "fd 0.5")
    nl.tick()
    nl.plot(nl.report(right_half))
nl.export_plot("My Plot", "my-plot.csv")                # the points, as a CSV file
```

Or in Python: `collect()` runs the model and records reporters over time, and
the result goes to matplotlib (or pandas, with `as_dataframe=True`):

```python
import matplotlib.pyplot as plt

data = nl.collect({"right half": right_half, "mean x": "mean [xcor] of pyturtles"},
                  steps=200, every=5,
                  command="ask pyturtles [ rt random 50 - 25 fd 0.5 ] tick")
plt.plot(data["step"], data["right half"], label="walkers in the right half")
plt.xlabel("step")
plt.legend()
plt.savefig("walkers.png")
nl.close()                                              # also done at exit
```

## Next

- [Quick start](quickstart.md): the same ideas on one page.
- [Guide](guide/sessions.md): sessions, agents, simulations, data, your own
  models.
- [Examples](examples.md): complete applications with their code.
