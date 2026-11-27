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

!!! note "Recording can change a run"
    NetLogo reads `[energy] of sheep` in a random order, drawn from the same
    random generator as the model. Recording such a reporter therefore changes
    the rest of the run, compared with a run that records nothing or only
    `count sheep`. A run stays reproducible for a given seed and a given set of
    recorded reporters.

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
