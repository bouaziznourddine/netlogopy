# The 0.x API

Scripts written for netlogopy 0.x keep working: `from netlogopy.netlogopy import *`
(or `from netlogopy import *`) gives the old functions and the new classes.
`run_netlogo()` returns a `NetLogo` session, so every new method is available
on it, and `pyturtle` objects are `Turtle` objects. The code printed in the
[SW25 paper](../paper.md) runs as it is, including its import spelling
`from netlogopy.nelogopy import *`.

```python
from netlogopy.netlogopy import *

n = run_netlogo()                              # bundled model, window, setup
car = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01")
other = pyturtle(n, x=5, y=5, shape="car", color=55)
street(n, fromm=car, too=other, label="street", color=35)
car.face_to(other); car.fd(3)
print(getxyturtle(n, car), car.distanceto(other))
set_slider(n, "speed", 5)
```

| Function | Description |
|---|---|
| `run_netlogo(netlogo_home=None, path_model="", gui=None)` | open a model in the window and run `setup` |
| `run_netlogo_model(netlogo_home, path_model, gui=None)` | open a model without running `setup` |
| `run_netlogo_base(netlogo_home=None)` | open the bundled model |
| `run_command(n, code)` | run NetLogo commands |
| `resize_world(n, x0, xf, y0, yf)`, `resize_world_direct` | resize the world |
| `set_background(n, image)`, `set_background_direct` | background image |
| `netlogoshow(n, value)`, `nl_output_print(n, value)` | command center / output area |
| `clear_drawing`, `clear_all`, `clear_all_turtles` | clearing |
| `get_ticks`, `do_tick`, `reset_ticks`, `tick_advance` | ticks |
| `get_world_width`, `get_world_height`, `get_min_pxcor`, `get_max_pxcor`, `get_min_pycor`, `get_max_pycor`, `get_random_xcor`, `get_random_ycor` | world |
| `set_patch_color`, `get_patch_color` | patch colors |
| `getxyturtle`, `distancebetween`, `count_pyturtles`, `get_all_pyturtles`, `get_turtle_by_id` | agents |
| `get_slider`, `set_slider`, `get_switch`, `set_switch`, `get_chooser`, `set_chooser`, `get_input_box`, `set_input_box`, `get_monitor` | widgets |
| `set_current_plot`, `set_plot_pen`, `create_plot_pen`, `plot_add`, `plot_xy`, `clear_plot`, `set_plot_pen_color`, `set_plot_pen_mode`, `set_plot_x_range`, `set_plot_y_range`, `auto_plot_on`, `auto_plot_off` | plots |
| `reset_base_file(dest)`, `create_ntlg_file(dest)` | copy base.nls |
| `list2nllist`, `de_copy` | utilities |
| `pyturtle(n, x, y, shape, size_shape, color, name, labelcolor, fields)` | a Python-driven turtle: `fd`, `bk`, `rt`, `lt`, `setxy`, `move_to`, `face_to`, `set_heading`, `get_xy`, `distanceto`, `set_color`, `set_shape`, `set_size`, `set_label`, `hideturtle`, `showturtle`, `dieturtle`, `pen_down`, `pen_up`, `stamp`, `in_radius`, `turtles_here`... |
| `street(n, fromm, too, label, labelcolor, color, shape, thickness)` | a directed link between two pyturtles |
| `PyTurtle`, `Street` | CamelCase names of `pyturtle` and `street` |
| `car.fields` | the extra attributes given with `fields=`, as a live dict (`car.fields["busy"]` is `car.busy`) |

## What changed in 1.0

- `n.report()` returns Python values instead of strings (`float(n.report(...))`
  still works).
- nl4py is no longer needed: NetLogo runs in the Python process.
- `base.nls` only declares the two breeds.
- Python 3.8 or newer.

See the [changelog](../changelog.md) for the full list.
