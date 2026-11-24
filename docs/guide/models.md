# Your own models

## Any model

Any NetLogo model (`.nlogo`, and `.nlogox` with NetLogo 7) works with
`NetLogo(...)`: its procedures, breeds, globals and widgets are all available.

```python
with NetLogo("Wolf Sheep Predation.nlogo", gui=True) as nl:
    nl.globals["model-version"] = "sheep-wolves-grass"
    nl.setup()
    car = nl.create_turtles(1, "sheep", shape="car", color=15)[0]
    for _ in range(100):
        nl.go()
        car.forward(1)
```

## Adding Python agents to an existing model

![Fire with two cars driven by Python](../assets/gifs/fire-with-python-agents.gif){ .demo width="420" }

The 0.x classes `pyturtle` and `street` need the `pyturtles` breed and the
`streets` link breed. The bundled model has them, and any model gets them by
including `base.nls`:

```python
from netlogopy import reset_base_file
reset_base_file("folder/of/your/model")      # copies base.nls there
```

Then add this line at the top of the model's Code tab:

```text
__includes [ "base.nls" ]
```

- The model must not declare these two breeds itself.
- Without the include, `pyturtle` and `street` raise an error that says what
  to add.
- An include file cannot hold shapes, so `run_netlogo(home, "your-model.nlogo")`
  copies netlogopy's shapes (`car`, `person_0`, `machine`...) into your model
  for the session. With the `NetLogo` class, call `nl.import_shapes()` (or
  `nl.import_shapes("other-model.nlogo")` to take the shapes of any model).

A complete 0.x script, written for the first releases:

```python
import time
from netlogopy.nelogopy import *

n = run_netlogo(netlogo_home, path_model)
resize_world(n, 0, 70, 0, 55)
run_command(n, "setup")                      # the model's own setup

car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
car02 = pyturtle(n, x=5, y=5, shape="car", size_shape=4, color=55, name="car02", labelcolor=55)
street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, thickness=0.5)

for i in range(100):
    run_command(n, "go")                     # one step of the model
    time.sleep(0.1)
    car01.fd(1)                              # Python moves its own agent
    if i % 20 == 0:
        car01.setxy(10, 10)
```

## A model that has no `setup`

`run_netlogo()` runs `setup` right after opening the model; use
`run_netlogo_model()` (or `NetLogo(model)`) to open it without running
anything, and set its widgets first.
