# Running a simulation

## Globals and interface widgets

```python
nl.globals["initial-number-sheep"] = 100      # sliders, switches, choosers, inputs
nl.globals["model-version"] = "sheep-wolves-grass"
nl.globals.to_dict()                          # every global and its value
```

## Stepping from Python

```python
nl.setup(); nl.go(); nl.go(100)               # go 100 times in one call
nl.run_until("not any? wolves", max_steps=1000)
nl.ticks, nl.tick(), nl.reset_ticks()
nl.random_seed(42)                            # reproducible runs
```

A Python loop is the usual way to mix the two: NetLogo moves its agents with
`go`, Python takes its own decisions between two steps.

```python
for step in range(300):
    nl.go()
    if step % 20 == 0:                        # every 20 ticks, Python decides
        queue = sorted(nl.turtles("jobs"), key=lambda job: job["remaining"])
        ...
```

## Starting, pausing and stopping

`start()` runs the model in the background, like a forever button, while
Python keeps reading and changing it:

```python
nl.start("go", interval=0.05)        # also: max_steps=500, until="not any? sheep"
while nl.running and nl.report("count sheep") < 300:
    time.sleep(0.5)
nl.pause()                           # the step in progress finishes first
nl.globals["wolf-reproduce"] = 8     # change the model while it is paused
nl.resume()
nl.wait(timeout=10)                  # wait for it to end by itself, at most 10 s
steps = nl.stop()                    # number of steps made
```

The run ends by itself after `max_steps`, when `until` becomes true, or when
the model's `go` calls `stop` (in the NetLogo window a `stop` of the model is
not seen: give `until` or `max_steps` there). Closing the session or opening
another model stops it first.

`stop()` waits for the step in progress. For a step that takes too long or
never ends, `nl.halt()` interrupts NetLogo, like *Halt* in its Tools menu, and
`nl.stop(timeout=5)` does it after five seconds. Called from another thread,
`halt()` also interrupts a `command()` that does not return.

While the model runs, each call is atomic: a list read with `nl.turtles()` or
`nl.report(...)` is complete, and `create_turtles`, `hatch` and `sprout` return
the turtles they created, not the ones the model created at the same time.

## Several models at once

Headless sessions are independent: open as many as needed, from as many
threads as needed.

```python
from concurrent.futures import ThreadPoolExecutor

def run(density):
    with NetLogo("Fire.nlogo") as nl:
        nl.globals["density"] = density
        nl.setup()
        nl.run_until("not any? turtles", max_steps=2000)
        return nl.report("burned-trees")

with ThreadPoolExecutor(4) as pool:
    print(list(pool.map(run, [50, 55, 60, 65])))
```

For parameter sweeps, [`run_experiment()`](data.md#experiments) does this for
you.

## A consistent look at a running model

While `start()` runs, each call sees the model at a different step. `hold()`
keeps the run still for a group of calls:

```python
with nl.hold():                       # no step runs inside the block
    sheep = nl.turtles("sheep")
    energy = nl.of(sheep, "energy")
```

## The view in memory, and in Jupyter

```python
nl                                    # last line of a Jupyter cell: shows the view
image = nl.view_array()               # numpy array (height, width, 3), 0-255
png = nl.view_png()                   # PNG data, no file written
nl.record_gif("run.gif", steps=200, every=2)     # runs the model, saves an animation
```

`view_array()` needs numpy and `record_gif()` needs Pillow
(`pip install "netlogopy[images]"`). They work headless and in the window.

## Reinforcement learning

`netlogopy.rl.NetLogoEnv` presents a model as a
[Gymnasium](https://gymnasium.farama.org) environment, so that a learning
library trains on it without glue code:

```python
from netlogopy.rl import NetLogoEnv

env = NetLogoEnv("Fire.nlogo",
                 observation=["burned-trees", "count fires"],     # numbers, or lists of numbers
                 actions=["", "ask up-to-n-of 2 fires [ die ]"],  # action 0, action 1
                 reward="0 - count fires",
                 done="not any? turtles", max_steps=400)

observation, info = env.reset(seed=1)
observation, reward, terminated, truncated, info = env.step(1)

from stable_baselines3 import PPO     # or any library that takes a Gymnasium environment
PPO("MlpPolicy", env).learn(20_000)
```

An action runs its NetLogo commands, then one step of the model. `actions` can
also be a function `actions(nl, action)`, with its `action_space`, and
`reward` a function `reward(nl)`. An episode ends when `done` is true or when
the model stops itself; `max_steps` cuts it short. `render_mode="rgb_array"`
gives the image of the view, and `gui=True` shows the agent at work in the
NetLogo window. Install with `pip install "netlogopy[rl]"`.
