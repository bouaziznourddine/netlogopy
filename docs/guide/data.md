# Data and experiments

## Time series

```python
data = nl.collect({"sheep": "count sheep", "wolves": "count wolves"},
                  steps=500, every=10, until="not any? wolves",
                  as_dataframe=True)            # pandas, or a dict of lists
data.plot(x="ticks")
```

`collect()` runs `go` (or the `command` given) and records the reporters every
`every` steps; the `ticks` column is added for you.

`schedule_reporters()` is the nl4py-compatible version: it returns one row per
recorded step.

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

## Python libraries in the loop

The model and Python share the same process, so any Python library can take
part in the simulation: an optimiser re-plans a schedule, a trained model
decides the agents' moves, scipy fits a distribution to the agents' state...
Examples: the [job shop](../examples.md#job-shop) re-optimises the machine
queues every 20 ticks, a [bisection](../examples.md#calibrate) calibrates the
Fire model, a [Q-learning agent](../examples.md#q-learning) learns a NetLogo
maze, [Dijkstra](../examples.md#routes) routes cars on a NetLogo road network,
and a [vaccination policy](../examples.md#python-policy) fights an epidemic.
