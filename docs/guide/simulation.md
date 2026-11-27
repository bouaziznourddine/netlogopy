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
