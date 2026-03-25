import copy
import nl4py
import os
import shutil
from typing import Any, List, Optional

list_pyturtle: List[Any] = []
list_street:   List[Any] = []


# ─── Internal helper ───────────────────────────────────────────────────────────

def _parse_nl_list(result) -> list:
    """Converts a nl4py result (list or string) into a Python list."""
    if isinstance(result, (list, tuple)):
        return list(result)
    if isinstance(result, str):
        # Strip brackets using replace — avoids linter issues with slice notation
        tokens = result.strip().replace('[', '').replace(']', '').split()
        return tokens if tokens else []
    return []


# ─── Initialisation ────────────────────────────────────────────────────────────

def run_netlogo(netlogo_home: str = "C:/Program Files/NetLogo 6.2.2",
                path_model: str = "") -> Any:
    """Start NetLogo, open the model and run setup. Returns the NetLogo app."""
    nl4py.initialize(netlogo_home)
    model = (os.path.join(os.path.dirname(__file__), "netlogopy.nlogo")
             if path_model == "" else path_model)
    n = nl4py.netlogo_app()
    n.open_model(model)
    n.command("setup")
    return n


def run_netlogo_base(netlogo_home: str = "C:/Program Files/NetLogo 6.2.2") -> Any:
    """Start NetLogo with the built-in netlogopy model."""
    nl4py.initialize(netlogo_home)
    model = os.path.join(os.path.dirname(__file__), "netlogopy.nlogo")
    n = nl4py.netlogo_app()
    n.open_model(model)
    n.command("setup")
    return n


def reset_base_file(dest: str) -> None:
    """Copy base.nls to dest folder."""
    shutil.copy2(os.path.join(os.path.dirname(__file__), "base.nls"),
                 os.path.join(dest, "base.nls"))


def create_ntlg_file(dest: str) -> None:
    """Copy base.nls as base2.nls to dest folder."""
    shutil.copy2(os.path.join(os.path.dirname(__file__), "base.nls"),
                 os.path.join(dest, "base2.nls"))


# ─── Utilities ─────────────────────────────────────────────────────────────────

def list2nllist(lis: List[Any]) -> str:
    """Convert a Python list to a NetLogo list string."""
    s = "["
    for i in lis:
        s += (' "' + i + '" ') if isinstance(i, str) else (' ' + str(i) + ' ')
    return s + "]"


def de_copy(a: Any) -> Any:
    """Return a deep copy of the object."""
    return copy.deepcopy(a)


def get_turtle_by_id(turtle_id: int) -> Optional[Any]:
    """Return the Python pyturtle object that has the given NetLogo who number."""
    for t in list_pyturtle:
        if t.id == turtle_id:
            return t
    return None


# ─── World ─────────────────────────────────────────────────────────────────────

def run_command(n: Any, command: str) -> None:
    """Execute any NetLogo command string."""
    n.command(command)


def resize_world(n: Any, x0: int, xf: int, y0: int, yf: int) -> None:
    """Resize the NetLogo world to [x0..xf] × [y0..yf]."""
    n.report("resize_world " + list2nllist([x0, xf, y0, yf]))


def set_background(n: Any, image: str) -> None:
    """Import an image as the world background."""
    n.report("set_background " + list2nllist([image]))


def netlogoshow(n: Any, word: Any) -> None:
    """Print a message in the NetLogo console (show)."""
    n.report("netlogoshow " + list2nllist([word]))


def nl_output_print(n: Any, word: Any) -> None:
    """Print a message in the NetLogo output window."""
    n.report("outputprint " + list2nllist([word]))


def clear_drawing(n: Any) -> None:
    """Erase all pen traces (clear-drawing)."""
    n.command("clear-drawing")


def clear_all(n: Any) -> None:
    """Full clear-all: remove all agents, patches, links, ticks."""
    n.command("clear-all")
    list_pyturtle.clear()
    list_street.clear()


def clear_all_turtles(n: Any) -> None:
    """Remove all pyturtles from the world."""
    n.command("ask pyturtles [die]")
    list_pyturtle.clear()


# ── Ticks ──────────────────────────────────────────────────────────────────────

def get_ticks(n: Any) -> int:
    """Return the current tick count."""
    return int(float(n.report("ticks")))


def do_tick(n: Any) -> None:
    """Advance the simulation clock by one tick."""
    n.command("tick")


def reset_ticks(n: Any) -> None:
    """Reset the tick counter to 0."""
    n.command("reset-ticks")


def tick_advance(n: Any, amount: float) -> None:
    """Advance the tick counter by a given amount (can be fractional)."""
    n.command(f"tick-advance {amount}")


# ── World dimensions ───────────────────────────────────────────────────────────

def get_world_width(n: Any) -> int:
    """Return the width of the world (max-pxcor - min-pxcor + 1)."""
    return int(float(n.report("world-width")))


def get_world_height(n: Any) -> int:
    """Return the height of the world (max-pycor - min-pycor + 1)."""
    return int(float(n.report("world-height")))


def get_max_pxcor(n: Any) -> int:
    """Return the maximum x-coordinate (max-pxcor)."""
    return int(float(n.report("max-pxcor")))


def get_min_pxcor(n: Any) -> int:
    """Return the minimum x-coordinate (min-pxcor)."""
    return int(float(n.report("min-pxcor")))


def get_max_pycor(n: Any) -> int:
    """Return the maximum y-coordinate (max-pycor)."""
    return int(float(n.report("max-pycor")))


def get_min_pycor(n: Any) -> int:
    """Return the minimum y-coordinate (min-pycor)."""
    return int(float(n.report("min-pycor")))


def get_random_xcor(n: Any) -> float:
    """Return a random x-coordinate inside world bounds."""
    return float(n.report("random-xcor"))


def get_random_ycor(n: Any) -> float:
    """Return a random y-coordinate inside world bounds."""
    return float(n.report("random-ycor"))


# ── Patches ────────────────────────────────────────────────────────────────────

def set_patch_color(n: Any, x: int, y: int, color: float) -> None:
    """Set the pcolor of patch (x, y)."""
    n.report("set_patch_color_r " + list2nllist([x, y, color]))


def get_patch_color(n: Any, x: int, y: int) -> float:
    """Return the pcolor of patch (x, y)."""
    return float(n.report("get_patch_color_r " + list2nllist([x, y])))


# ── Agents ─────────────────────────────────────────────────────────────────────

def getxyturtle(n: Any, turtle_obj: Any) -> list:
    """Return [xcor, ycor] of the turtle."""
    c = n.report("getxyturtle " + list2nllist([turtle_obj.id]))
    if isinstance(c, (list, tuple)):
        return list(c)
    return eval(c)


def distancebetween(n: Any, fromm: Any, target: Any) -> float:
    """Return the distance between two turtle objects."""
    return float(n.report("distanceto " + list2nllist([fromm.id, target.id])))


def count_pyturtles(n: Any) -> int:
    """Return the number of pyturtles currently in the world."""
    return int(float(n.report("count pyturtles")))


def get_all_pyturtles() -> List[Any]:
    """Return the Python list of all pyturtle instances."""
    return list_pyturtle


# ─── Classes ───────────────────────────────────────────────────────────────────

class turtle:
    """
    Base class representing a NetLogo turtle controlled from Python.
    Do not instantiate directly — use `pyturtle` instead.
    """

    def __init__(self, n: Any, turtle_id: int = 0):
        self.id: int = turtle_id
        self.n  = n

    # ── Movement ───────────────────────────────────────────────────────────────

    def fd(self, steps: float = 1) -> None:
        """Move forward `steps` units (forward)."""
        self.n.report("fdfd " + list2nllist([self.id, steps]))

    def bk(self, steps: float = 1) -> None:
        """Move backward `steps` units (back)."""
        self.n.report("bkbk " + list2nllist([self.id, steps]))

    def rt(self, angle: float) -> None:
        """Turn right by `angle` degrees (right)."""
        self.n.report("rtrt " + list2nllist([self.id, angle]))

    def lt(self, angle: float) -> None:
        """Turn left by `angle` degrees (left)."""
        self.n.report("ltlt " + list2nllist([self.id, angle]))

    def setxy(self, x: float, y: float) -> None:
        """Teleport to coordinates (x, y) — setxy."""
        self.n.report("turtle_setxy " + list2nllist([self.id, x, y]))

    def set_xcor(self, x: float) -> None:
        """Set the x-coordinate only."""
        self.n.report("set_xcor_turtle " + list2nllist([self.id, x]))

    def set_ycor(self, y: float) -> None:
        """Set the y-coordinate only."""
        self.n.report("set_ycor_turtle " + list2nllist([self.id, y]))

    def home(self) -> None:
        """Move to (0, 0) and set heading to 0 (north) — home."""
        self.n.report("home_turtle " + list2nllist([self.id]))

    def set_random_position(self) -> None:
        """Teleport to a random position inside the world bounds."""
        self.n.report("random_pos_turtle " + list2nllist([self.id]))

    def can_move(self, distance: float = 1) -> bool:
        """Return True if the turtle can move forward `distance` units (can-move?)."""
        return bool(self.n.report("can_move_turtle " + list2nllist([self.id, distance])))

    def move_to(self, target: Any) -> None:
        """Move to the same position as `target` turtle (move-to)."""
        self.n.report("moveto " + list2nllist([self.id, target.id]))

    def wander(self, steps: float = 1) -> None:
        """Set a random heading then move forward `steps` units."""
        self.n.report("wander_turtle " + list2nllist([self.id, steps]))

    # ── Heading / orientation ──────────────────────────────────────────────────

    def face_to(self, target: Any) -> None:
        """Face towards another turtle (face)."""
        self.n.report("faceto " + list2nllist([self.id, target.id]))

    def set_heading(self, angle: float) -> None:
        """Set heading in degrees (0=North, 90=East, 180=South, 270=West)."""
        self.n.report("set_heading_turtle " + list2nllist([self.id, angle]))

    def get_heading(self) -> float:
        """Return the current heading in degrees."""
        return float(self.n.report("get_heading_turtle " + list2nllist([self.id])))

    def towards_point(self, x: float, y: float) -> float:
        """Return the heading from this turtle towards point (x, y) — towards."""
        return float(self.n.report("towards_point_turtle " + list2nllist([self.id, x, y])))

    # ── Position ───────────────────────────────────────────────────────────────

    def get_xcor(self) -> float:
        """Return the current x-coordinate."""
        return getxyturtle(self.n, self)[0]

    def get_ycor(self) -> float:
        """Return the current y-coordinate."""
        return getxyturtle(self.n, self)[1]

    def distanceto(self, target: Any) -> float:
        """Return the distance to another turtle (distance)."""
        return float(self.n.report("distanceto " + list2nllist([self.id, target.id])))

    def distance_to_point(self, x: float, y: float) -> float:
        """Return the distance from this turtle to point (x, y) — distancexy."""
        return float(self.n.report("distance_point_turtle " + list2nllist([self.id, x, y])))

    # ── Appearance ─────────────────────────────────────────────────────────────

    def set_shape(self, shape: str) -> None:
        """Change the shape (e.g. 'car', 'default', 'person')."""
        self.n.report("set_shape " + list2nllist([self.id, shape]))

    def get_shape(self) -> str:
        """Return the current shape name."""
        return str(self.n.report("get_shape_turtle " + list2nllist([self.id])))

    def set_color(self, color: float) -> None:
        """Change the color (NetLogo color code, see colors chart)."""
        self.n.report("set_color_turtle " + list2nllist([self.id, color]))

    def get_color(self) -> float:
        """Return the current color code."""
        return float(self.n.report("get_color_turtle " + list2nllist([self.id])))

    def set_size(self, size: float) -> None:
        """Change the size of the turtle."""
        self.n.report("set_size_turtle " + list2nllist([self.id, size]))

    def get_size(self) -> float:
        """Return the current size."""
        return float(self.n.report("get_size_turtle " + list2nllist([self.id])))

    def set_label(self, text: str) -> None:
        """Set the text label displayed on the turtle."""
        self.n.report("set_label_turtle " + list2nllist([self.id, str(text)]))

    def get_label(self) -> str:
        """Return the current label text."""
        return str(self.n.report("get_label_turtle " + list2nllist([self.id])))

    def set_label_color(self, color: float) -> None:
        """Set the color of the label text."""
        self.n.report("set_label_color_turtle " + list2nllist([self.id, color]))

    def hideturtle(self) -> None:
        """Hide the turtle (hide-turtle)."""
        self.n.report("hideturtle " + list2nllist([self.id]))

    def showturtle(self) -> None:
        """Make the turtle visible (show-turtle)."""
        self.n.report("showturtle " + list2nllist([self.id]))

    def dieturtle(self) -> None:
        """Remove the turtle from the world (die)."""
        self.n.report("dieturtle " + list2nllist([self.id]))
        if self in list_pyturtle:
            list_pyturtle.remove(self)

    # ── Pen ────────────────────────────────────────────────────────────────────

    def pen_down(self) -> None:
        """Activate the pen — trace the path (pen-down)."""
        self.n.report("pen_down_turtle " + list2nllist([self.id]))

    def pen_up(self) -> None:
        """Deactivate the pen (pen-up)."""
        self.n.report("pen_up_turtle " + list2nllist([self.id]))

    def pen_erase(self) -> None:
        """Set pen to erase mode — erases as the turtle moves (pen-erase)."""
        self.n.report("pen_erase_turtle " + list2nllist([self.id]))

    def set_pen_color(self, color: float) -> None:
        """Set the pen color (set pen-color)."""
        self.n.report("set_pen_color_turtle " + list2nllist([self.id, color]))

    def set_pen_size(self, size: float) -> None:
        """Set the pen line thickness (set pen-size)."""
        self.n.report("set_pen_size_turtle " + list2nllist([self.id, size]))

    def stamp(self) -> None:
        """Stamp the turtle's shape onto the patches below (stamp)."""
        self.n.report("stamp_turtle " + list2nllist([self.id]))

    def stamp_erase(self) -> None:
        """Erase the stamp at the turtle's current location (stamp-erase)."""
        self.n.report("stamp_erase_turtle " + list2nllist([self.id]))

    # ── Patch interaction ──────────────────────────────────────────────────────

    def patch_here_color(self) -> float:
        """Return the pcolor of the patch the turtle is currently on."""
        return float(self.n.report("patch_here_color_turtle " + list2nllist([self.id])))

    def set_patch_here_color(self, color: float) -> None:
        """Set the pcolor of the patch the turtle is currently on."""
        self.n.report("set_patch_here_color_turtle " + list2nllist([self.id, color]))

    # ── Neighborhood ───────────────────────────────────────────────────────────

    def in_radius(self, radius: float) -> List[int]:
        """Return the NetLogo who-numbers of all other turtles within `radius` (in-radius)."""
        result = self.n.report("in_radius_turtle " + list2nllist([self.id, radius]))
        return [int(float(x)) for x in _parse_nl_list(result)]

    def turtles_here(self) -> List[int]:
        """Return the who-numbers of all other turtles on the same patch (turtles-here)."""
        result = self.n.report("turtles_here_turtle " + list2nllist([self.id]))
        return [int(float(x)) for x in _parse_nl_list(result)]


# ─── street ────────────────────────────────────────────────────────────────────

class street:
    """
    Directed link between two pyturtles (NetLogo directed-link-breed).

    Parameters
    ----------
    n          : NetLogo app returned by run_netlogo()
    fromm      : source pyturtle
    too        : target pyturtle
    label      : link label text
    labelcolor : label color code
    color      : link color code
    shape      : link shape name
    thickness  : link line thickness
    """

    def __init__(self, n: Any, fromm: Any, too: Any,
                 label: str = "street", labelcolor: float = 0,
                 color: float = 0, shape: str = "default",
                 thickness: float = 0.5):
        self.id = None
        c = "create-street-ft " + list2nllist(
            [fromm.id, too.id, label, labelcolor, color, shape, thickness])
        self.id = n.report(c)
        list_street.append(self)


# ─── pyturtle ──────────────────────────────────────────────────────────────────

# ─── External model integration ────────────────────────────────────────────────

def run_netlogo_model(netlogo_home: str, path_model: str) -> Any:
    """
    Start NetLogo and open an *existing* .nlogo model WITHOUT calling setup.
    Use this instead of run_netlogo() when integrating an external model that
    already has its own setup/go procedures.
    """
    nl4py.initialize(netlogo_home)
    n = nl4py.netlogo_app()
    n.open_model(path_model)
    return n


def resize_world_direct(n: Any, x0: int, xf: int, y0: int, yf: int) -> None:
    """
    Resize the world using a direct NetLogo command (no base.nls required).
    Use this with external models that do not include base.nls.
    """
    n.command(f"resize-world {x0} {xf} {y0} {yf}")


def set_background_direct(n: Any, image: str) -> None:
    """Set background image without relying on base.nls."""
    n.command(f'import-drawing "{image}"')


# ─── UI Widgets ────────────────────────────────────────────────────────────────

def get_slider(n: Any, name: str) -> float:
    """Read the current value of a NetLogo Slider widget (backed by a global)."""
    return float(n.report(name))


def set_slider(n: Any, name: str, value: float) -> None:
    """Write a value to a NetLogo Slider widget (backed by a global)."""
    n.command(f"set {name} {value}")


def get_switch(n: Any, name: str) -> bool:
    """Read the current state of a NetLogo Switch widget (backed by a boolean global)."""
    val = n.report(name)
    if isinstance(val, bool):
        return val
    return str(val).lower() == "true"


def set_switch(n: Any, name: str, value: bool) -> None:
    """Set the state of a NetLogo Switch widget."""
    n.command(f"set {name} {'true' if value else 'false'}")


def get_chooser(n: Any, name: str) -> Any:
    """Read the current value of a NetLogo Chooser widget (backed by a global)."""
    return n.report(name)


def set_chooser(n: Any, name: str, value: Any) -> None:
    """Set the value of a NetLogo Chooser widget."""
    if isinstance(value, str):
        n.command(f'set {name} "{value}"')
    else:
        n.command(f"set {name} {value}")


def get_input_box(n: Any, name: str) -> Any:
    """Read the current value of a NetLogo Input widget (backed by a global)."""
    return n.report(name)


def set_input_box(n: Any, name: str, value: Any) -> None:
    """Set the value of a NetLogo Input widget."""
    if isinstance(value, str):
        n.command(f'set {name} "{value}"')
    else:
        n.command(f"set {name} {value}")


def get_monitor(n: Any, expression: str) -> Any:
    """
    Evaluate any NetLogo reporter expression — equivalent to a Monitor widget.
    Examples: get_monitor(n, 'count turtles'), get_monitor(n, 'ticks')
    """
    return n.report(expression)


# ─── Plot widget ────────────────────────────────────────────────────────────────

def set_current_plot(n: Any, plot_name: str) -> None:
    """Activate a plot by name (set-current-plot)."""
    n.command(f'set-current-plot "{plot_name}"')


def set_plot_pen(n: Any, pen_name: str) -> None:
    """Activate a pen in the current plot (set-current-plot-pen)."""
    n.command(f'set-current-plot-pen "{pen_name}"')


def create_plot_pen(n: Any, pen_name: str) -> None:
    """Create a temporary pen in the current plot (create-temporary-plot-pen)."""
    n.command(f'create-temporary-plot-pen "{pen_name}"')


def plot_add(n: Any, value: float) -> None:
    """Add a data point at the current x position, then advance x (plot)."""
    n.command(f"plot {value}")


def plot_xy(n: Any, x: float, y: float) -> None:
    """Add a data point at explicit (x, y) coordinates (plotxy)."""
    n.command(f"plotxy {x} {y}")


def clear_plot(n: Any) -> None:
    """Clear all data from the current plot (clear-plot)."""
    n.command("clear-plot")


def set_plot_pen_color(n: Any, color: float) -> None:
    """Set the color of the current plot pen (set-plot-pen-color)."""
    n.command(f"set-plot-pen-color {color}")


def set_plot_pen_mode(n: Any, mode: int) -> None:
    """Set the mode of the current plot pen: 0=line, 1=bar, 2=point (set-plot-pen-mode)."""
    n.command(f"set-plot-pen-mode {mode}")


def auto_plot_on(n: Any) -> None:
    """Enable automatic plot range adjustment (auto-plot-on)."""
    n.command("auto-plot-on")


def auto_plot_off(n: Any) -> None:
    """Disable automatic plot range adjustment (auto-plot-off)."""
    n.command("auto-plot-off")


def set_plot_x_range(n: Any, x_min: float, x_max: float) -> None:
    """Set the x-axis range of the current plot (set-plot-x-range)."""
    n.command(f"set-plot-x-range {x_min} {x_max}")


def set_plot_y_range(n: Any, y_min: float, y_max: float) -> None:
    """Set the y-axis range of the current plot (set-plot-y-range)."""
    n.command(f"set-plot-y-range {y_min} {y_max}")


# ─── pyturtle ──────────────────────────────────────────────────────────────────

class pyturtle(turtle):
    """
    A Python-controlled NetLogo turtle (pyturtle breed).

    Parameters
    ----------
    n          : NetLogo app returned by run_netlogo()
    x, y       : initial coordinates
    shape      : shape name (default 'car')
    size_shape : size
    color      : NetLogo color code
    name       : label text
    labelcolor : label color code
    fields     : dict of extra attributes to attach to the Python object
    """

    def __init__(self, n: Any, x: float = 0, y: float = 0,
                 shape: str = "car", size_shape: float = 4,
                 color: float = 0, name: str = "zn",
                 labelcolor: float = 0, fields: dict = {}):
        # Create the NetLogo agent via the create-pyturtle-xyid reporter defined
        # in netlogopy.nlogo / base.nls.  The reporter creates the turtle and
        # returns its who number in one atomic call, which is the most reliable
        # way to get the id back without depending on globals or agentset max.
        c = "create-pyturtle-xyid " + list2nllist(
            [x, y, shape, size_shape, color, name, labelcolor]
        )
        new_id = int(float(n.report(c)))
        # Pass id to parent so self.id is only assigned once, in turtle.__init__
        super().__init__(n, turtle_id=new_id)
        self.__dict__.update(fields)
        list_pyturtle.append(self)
