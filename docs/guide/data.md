# Data and experiments

## Time series

```python
data = nl.collect({"sheep": "count sheep", "wolves": "count wolves"},
                  steps=500, every=10, until="not any? wolves",
                  as_dataframe=True)            # pandas, or a dict of lists
data.plot(x="step")
```

`collect()` runs `go` (or the `command` given) and records the reporters every
`every` steps; the `step` column is added for you. `until` is tested before
each step: the run stops at the step where it becomes true, and that step is
recorded.

`schedule_reporters()` records on a tick schedule instead: it returns one row per
recorded tick, after each step (the state before the first step is not recorded).

!!! note "Recording does not change a run"
    NetLogo reads `[energy] of sheep` in a random order. `collect()`,
    `run_until()`, `run_experiment()` and the functions below draw that order
    from NetLogo's auxiliary random generator, the one its monitors use: for a
    given seed the model does the same thing whatever you record.
    `nl.observe(reporter)` reads any reporter this way; `nl.report(reporter)`
    still draws from the generator of the model, as NetLogo code does.
    (Before 1.1, recording such a reporter changed the rest of the run.)

## Agent data

```python
nl.agent_table("sheep", ["xcor", "ycor", "energy"], as_dataframe=True)
#    who   xcor   ycor  energy
# 0    0  -3.20   7.41     4.0
# 1    1  11.90  -2.08     6.0

data = nl.collect_agents("sheep", "energy", steps=100, every=10, as_dataframe=True)
data.groupby("step")["energy"].mean()        # one row per sheep and per recorded step
```

`agent_table()` reads several variables of many agents in one NetLogo call:
`who` identifies a turtle, `pxcor` and `pycor` a patch, `end1` and `end2` a
link. `collect_agents()` records such a table over time, like the agent-level
data of a data collector. The agents are NetLogo code (`"sheep with [energy >
5]"`) or a list of agents; a column can be any reporter, named with a dict:
`{"speed": "sqrt (vx * vx + vy * vy)"}`.

## Experiments

`run_experiment()` runs a parameter sweep like BehaviorSpace: every
combination of the parameters, with repetitions, seeds, stop conditions and
parallel workers (one headless session each).

```python
from netlogopy import run_experiment

rows = run_experiment(
    "Fire.nlogo",
    parameters={"density": [50, 55, 60, 65, 70]},   # every combination
    reporters={"burned": "burned-trees"},
    repetitions=10, steps=2000, until="not any? turtles",
    seed=1, workers=4, as_dataframe=True)

rows.groupby("density")["burned"].mean()
```

`parameter_grid({...})` gives the list of combinations without running them.
A list, a range or a numpy array gives the values to try; any other value is a
single choice.

- The reporters, `until`, `setup` and `go` are compiled before the first run:
  a typo is reported at once.
- The first run that fails ends the sweep; the error names the run and its
  parameters.
- `parameters` can also be an explicit list of runs,
  `[{"density": 50}, {"density": 70, "wind": 5}]`: a global that a run does not
  name gets the value it has in the model file.
- A worker opens the model once and reuses it for its runs: `setup` should
  start with `clear-all`, as NetLogo models usually do, so that nothing of a
  run reaches the next one.
- A run ends at `steps`, when `until` is true, or when the `go` procedure of
  the model calls `stop`, as in BehaviorSpace. `final="..."` runs commands at
  the end of each run.

## BehaviorSpace experiments of a model

The experiments saved in a model with NetLogo's BehaviorSpace run from Python,
in parallel, and come back as rows or as a DataFrame:

```python
from netlogopy import behaviorspace_experiments, run_behaviorspace

list(behaviorspace_experiments("Wolf Sheep Predation.nlogox"))
# ['New BehaviorSpace Features', 'Wolf Sheep Crossing', ...]

rows = run_behaviorspace("Wolf Sheep Predation.nlogox", "Wolf Sheep Crossing",
                         workers=4, seed=1, as_dataframe=True)
```

Both file formats are read (`.nlogo` of NetLogo 6, `.nlogox` of NetLogo 7):
value sets, constants and sub-experiments, repetitions, time limit, exit
condition, metrics, "run metrics when" and the commands after each run.
`repetitions=` and `steps=` replace those of the experiment, for a quick try.
The commands that an experiment runs once before or after all its runs are
not run (a warning says so).

## Experiment designs

Every combination of 5 parameters with 10 values each is 100 000 runs. A
design covers the same ranges with far fewer:

```python
from netlogopy import latin_hypercube, random_sample, run_experiment

bounds = {"initial-number-wolves": (20, 120),     # two whole numbers: whole values
          "wolf-gain-from-food": (10.0, 40.0),    # decimals
          "model-version": ["sheep-wolves", "sheep-wolves-grass"]}   # a choice

points = latin_hypercube(bounds, 50, seed=1)       # 50 parameter sets
rows = run_experiment("Wolf Sheep Predation.nlogo", points, "count sheep",
                      steps=200, workers=4, as_dataframe=True)
```

`latin_hypercube()` cuts each range in as many slices as there are samples and
uses each slice once; `random_sample()` draws the sets at random (Monte Carlo).
Both need nothing but Python.

## Sensitivity analysis

Which parameters change the result most?

```python
from netlogopy import sensitivity

result = sensitivity("Wolf Sheep Predation.nlogo",
                     {"initial-number-wolves": (20, 120),
                      "wolf-gain-from-food": (10.0, 40.0),
                      "sheep-reproduce": (2.0, 8.0)},
                     {"sheep": "count sheep"},
                     samples=32, steps=30, workers=4, seed=1)
result["sheep"]["ST"]
# {'initial-number-wolves': 0.28, 'wolf-gain-from-food': 0.12, 'sheep-reproduce': 0.66}
```

`method="sobol"` (default) gives the share of the variance of the result due
to each parameter: `S1` alone, `ST` with its interactions, and their
confidence intervals. `method="morris"` ranks the parameters with fewer runs
(`mu_star`, `sigma`). The parameter sets and their results are under
`result["runs"]`. The analysis is made by
[SALib](https://salib.readthedocs.io): `pip install "netlogopy[analysis]"`.
A noisy model needs more samples, or `repetitions=` (their mean is analysed).

## Calibration

`calibrate()` searches the parameter values that give the result you ask for:

```python
from netlogopy import calibrate

found = calibrate("Fire.nlogo", {"density": (30, 90)}, "burned-trees",
                  target=2000,                    # as close to 2000 burned trees as possible
                  steps=2000, until="not any? turtles",
                  population=12, generations=10, workers=4, seed=1)
found["parameters"], found["value"]
# ({'density': 60}, 2018.0)
```

Without `target` the result itself is made as small as possible
(`minimize=False`: as large as possible). The search is a differential
evolution, in pure Python: `population * (generations + 1)` parameter sets,
each generation run in parallel. `found["history"]` gives the best score after
each generation.

## Python libraries in the loop

The model and Python share the same process, so any Python library can take
part in the simulation: an optimiser re-plans a schedule, a trained model
decides the agents' moves, scipy fits a distribution to the agents' state...
Examples: a [bisection](../examples.md#calibrate) calibrates the
Fire model, a [Q-learning agent](../examples.md#q-learning) learns a NetLogo
maze, [Dijkstra](../examples.md#routes) routes cars on a NetLogo road network,
a [vaccination policy](../examples.md#python-policy) fights an epidemic, exits
are [assigned to a crowd](../examples.md#evacuation), a flood fill
[measures segregation](../examples.md#segregation) and a controller
[sets a wealth tax](../examples.md#wealth-tax).
