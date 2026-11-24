"""netlogopy 0.x API, kept so existing scripts keep working.

``from netlogopy.netlogopy import *`` still provides ``run_netlogo``,
``pyturtle``, ``street``, ``resize_world``... They now run on the
:class:`~netlogopy.NetLogo` engine (no nl4py, no base.nls reporters needed),
and also export the new API (``NetLogo``, ``Turtle``, ``Code``...).

``pyturtle`` needs the ``pyturtles`` breed and ``street`` the ``streets``
link breed: they exist in the bundled model, and any model gets them by
including base.nls (``__includes [ "base.nls" ]``, see :func:`reset_base_file`).
"""

import copy
import os
import shutil
from typing import Any, List, Optional

from .agents import Link, Patch, Turtle
from .convert import Code, to_netlogo
from .core import NetLogo, headless_forced
from .errors import NetLogoCompileError, NetLogoError, NetLogoNotFoundError, NetLogoRuntimeError

__all__ = [
    # new API, re-exported for star imports
    "NetLogo", "Turtle", "Patch", "Link", "Code", "NetLogoError", "NetLogoCompileError",
    "NetLogoRuntimeError", "NetLogoNotFoundError",
    # 0.x API
    "list_pyturtle", "list_street",
    "run_netlogo", "run_netlogo_base", "run_netlogo_model", "reset_base_file", "create_ntlg_file",
    "list2nllist", "de_copy", "get_turtle_by_id",
    "run_command", "resize_world", "resize_world_direct", "set_background", "set_background_direct",
    "netlogoshow", "nl_output_print", "clear_drawing", "clear_all", "clear_all_turtles",
    "get_ticks", "do_tick", "reset_ticks", "tick_advance",
    "get_world_width", "get_world_height", "get_max_pxcor", "get_min_pxcor",
    "get_max_pycor", "get_min_pycor", "get_random_xcor", "get_random_ycor",
    "set_patch_color", "get_patch_color",
    "getxyturtle", "distancebetween", "count_pyturtles", "get_all_pyturtles",
    "get_slider", "set_slider", "get_switch", "set_switch", "get_chooser", "set_chooser",
    "get_input_box", "set_input_box", "get_monitor",
    "set_current_plot", "set_plot_pen", "create_plot_pen", "plot_add", "plot_xy", "clear_plot",
    "set_plot_pen_color", "set_plot_pen_mode", "auto_plot_on", "auto_plot_off",
    "set_plot_x_range", "set_plot_y_range",
    "turtle", "pyturtle", "street", "PyTurtle", "Street",
]

#: Every ``pyturtle`` created (removed again by dieturtle / clear_all*).
list_pyturtle: List["pyturtle"] = []
#: Every ``street`` created.
list_street: List["street"] = []

_BASE_NLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base.nls")


def _default_gui() -> bool:
    """The window by default; NETLOGOPY_HEADLESS=1 runs scripts headless (CI, tests)."""
    return not headless_forced()


# ─── Initialisation ────────────────────────────────────────────────────────────

def run_netlogo(netlogo_home: Optional[str] = None, path_model: str = "",
                gui: Optional[bool] = None) -> NetLogo:
    """Open a model (default: the bundled one) in the NetLogo window and run ``setup``.

    netlogo_home : NetLogo folder (default: NETLOGO_HOME, else the newest installed).
    path_model   : model to open; it must define a ``setup`` procedure.
    gui          : False for headless (default: window, unless NETLOGOPY_HEADLESS=1).
    """
    nl = run_netlogo_model(netlogo_home, path_model, gui=gui)
    nl.command("setup")
    return nl


def run_netlogo_base(netlogo_home: Optional[str] = None) -> NetLogo:
    """Open the bundled netlogopy model and run ``setup``."""
    return run_netlogo(netlogo_home)


def run_netlogo_model(netlogo_home: Optional[str], path_model: str = "",
                      gui: Optional[bool] = None) -> NetLogo:
    """Open a model WITHOUT running setup (to configure its widgets first).

    A model of your own also receives netlogopy's shapes (car, person_0,
    machine...) for the session, so pyturtles look the same in every model.
    """
    list_pyturtle.clear()
    list_street.clear()
    nl = NetLogo(path_model or None, gui=_default_gui() if gui is None else gui,
                 netlogo_home=netlogo_home)
    if path_model:
        nl.import_shapes()
    return nl


def _require_breed(n: NetLogo, kind: str, breed: str) -> None:
    if breed not in n.breeds()[kind]:
        raise NetLogoCompileError(
            f"this model has no '{breed}' breed: add  __includes [ \"base.nls\" ]  at the top of "
            f"its Code tab and copy base.nls next to it with reset_base_file(folder)")


def reset_base_file(dest: str) -> None:
    """Copy base.nls (pyturtles and streets breeds) into folder ``dest``."""
    shutil.copy2(_BASE_NLS, os.path.join(dest, "base.nls"))


def create_ntlg_file(dest: str) -> None:
    """Copy base.nls as base2.nls into folder ``dest``."""
    shutil.copy2(_BASE_NLS, os.path.join(dest, "base2.nls"))


# ─── Utilities ─────────────────────────────────────────────────────────────────

def list2nllist(lis: List[Any]) -> str:
    """Python list -> NetLogo list literal (``[ 1  "a"  true ]``)."""
    return "[" + "".join(" " + to_netlogo(item) + " " for item in lis) + "]"


def de_copy(a: Any) -> Any:
    """Deep copy of an object."""
    return copy.deepcopy(a)


def get_turtle_by_id(turtle_id: int) -> Optional["pyturtle"]:
    """The pyturtle with this who number, or None."""
    for item in list_pyturtle:
        if item.id == turtle_id:
            return item
    return None


# ─── World ─────────────────────────────────────────────────────────────────────

def run_command(n: NetLogo, command: str) -> None:
    """Run any NetLogo command."""
    n.command(command)


def resize_world(n: NetLogo, x0: int, xf: int, y0: int, yf: int) -> None:
    """Resize the world to [x0..xf] x [y0..yf]."""
    n.resize_world(x0, xf, y0, yf)


resize_world_direct = resize_world


def set_background(n: NetLogo, image: str) -> None:
    """Draw an image behind the agents (relative paths: relative to the model)."""
    n.command(f"import-drawing {to_netlogo(image)}")


set_background_direct = set_background


def netlogoshow(n: NetLogo, word: Any) -> None:
    """``show`` a value in the NetLogo command center."""
    n.show(word)


def nl_output_print(n: NetLogo, word: Any) -> None:
    """Print in the model's Output widget."""
    n.output_print(word)


def clear_drawing(n: NetLogo) -> None:
    """Erase pen traces and stamps."""
    n.clear_drawing()


def clear_all(n: NetLogo) -> None:
    """``clear-all``: agents, patches, globals, ticks, drawing, plots."""
    n.clear_all()
    list_pyturtle.clear()
    list_street.clear()


def clear_all_turtles(n: NetLogo) -> None:
    """Kill every pyturtle."""
    n.command("ask pyturtles [ die ]")
    list_pyturtle.clear()


def get_ticks(n: NetLogo) -> int:
    return int(n.ticks)


def do_tick(n: NetLogo) -> None:
    n.tick()


def reset_ticks(n: NetLogo) -> None:
    n.reset_ticks()


def tick_advance(n: NetLogo, amount: float) -> None:
    n.tick_advance(amount)


def get_world_width(n: NetLogo) -> int:
    return n.world_width


def get_world_height(n: NetLogo) -> int:
    return n.world_height


def get_max_pxcor(n: NetLogo) -> int:
    return n.max_pxcor


def get_min_pxcor(n: NetLogo) -> int:
    return n.min_pxcor


def get_max_pycor(n: NetLogo) -> int:
    return n.max_pycor


def get_min_pycor(n: NetLogo) -> int:
    return n.min_pycor


def get_random_xcor(n: NetLogo) -> float:
    return n.report("random-xcor")


def get_random_ycor(n: NetLogo) -> float:
    return n.report("random-ycor")


def set_patch_color(n: NetLogo, x: int, y: int, color: float) -> None:
    n.command(f"ask patch {to_netlogo(x)} {to_netlogo(y)} [ set pcolor {to_netlogo(color)} ]")


def get_patch_color(n: NetLogo, x: int, y: int) -> float:
    return n.report(f"[pcolor] of patch {to_netlogo(x)} {to_netlogo(y)}")


def getxyturtle(n: NetLogo, turtle_obj: Turtle) -> List[float]:
    """[xcor, ycor] of a turtle."""
    return n.turtle(turtle_obj.who).xy


def distancebetween(n: NetLogo, fromm: Turtle, target: Turtle) -> float:
    return n.turtle(fromm.who).distance(target)


def count_pyturtles(n: NetLogo) -> int:
    return n.count("pyturtles")


def get_all_pyturtles() -> List["pyturtle"]:
    return list_pyturtle


# ─── Interface widgets ─────────────────────────────────────────────────────────

def get_slider(n: NetLogo, name: str) -> float:
    return float(n.get_global(name))


def set_slider(n: NetLogo, name: str, value: float) -> None:
    n.set_global(name, value)


def get_switch(n: NetLogo, name: str) -> bool:
    return bool(n.get_global(name))


def set_switch(n: NetLogo, name: str, value: bool) -> None:
    n.set_global(name, bool(value))


def get_chooser(n: NetLogo, name: str) -> Any:
    return n.get_global(name)


def set_chooser(n: NetLogo, name: str, value: Any) -> None:
    n.set_global(name, value)


def get_input_box(n: NetLogo, name: str) -> Any:
    return n.get_global(name)


def set_input_box(n: NetLogo, name: str, value: Any) -> None:
    n.set_global(name, value)


def get_monitor(n: NetLogo, expression: str) -> Any:
    """Value of any NetLogo reporter, like a Monitor widget."""
    return n.report(expression)


# ─── Plots ─────────────────────────────────────────────────────────────────────

def set_current_plot(n: NetLogo, plot_name: str) -> None:
    n.set_current_plot(plot_name)


def set_plot_pen(n: NetLogo, pen_name: str) -> None:
    n.set_current_plot_pen(pen_name)


def create_plot_pen(n: NetLogo, pen_name: str) -> None:
    n.create_temporary_plot_pen(pen_name)


def plot_add(n: NetLogo, value: float) -> None:
    n.plot(value)


def plot_xy(n: NetLogo, x: float, y: float) -> None:
    n.plotxy(x, y)


def clear_plot(n: NetLogo) -> None:
    n.clear_plot()


def set_plot_pen_color(n: NetLogo, color: float) -> None:
    n.set_plot_pen_color(color)


def set_plot_pen_mode(n: NetLogo, mode: int) -> None:
    n.set_plot_pen_mode(mode)


def auto_plot_on(n: NetLogo) -> None:
    n.auto_plot_on()


def auto_plot_off(n: NetLogo) -> None:
    n.auto_plot_off()


def set_plot_x_range(n: NetLogo, x_min: float, x_max: float) -> None:
    n.set_plot_x_range(x_min, x_max)


def set_plot_y_range(n: NetLogo, y_min: float, y_max: float) -> None:
    n.set_plot_y_range(y_min, y_max)


# ─── Classes ───────────────────────────────────────────────────────────────────

class turtle(Turtle):
    """0.x turtle API: ``id`` / ``n`` attributes and get_/set_ methods.

    It is a :class:`~netlogopy.Turtle`, so the new methods work too.
    """

    def __init__(self, n: NetLogo, turtle_id: int = 0):
        Turtle.__init__(self, n, turtle_id)

    @property
    def id(self) -> int:
        """NetLogo who number."""
        return self.who

    @id.setter
    def id(self, value: int) -> None:
        self.who = int(value)

    @property
    def n(self) -> NetLogo:
        """The NetLogo session."""
        return self.nl

    @n.setter
    def n(self, value: NetLogo) -> None:
        self.nl = value

    # movement
    def set_xcor(self, x: float) -> None:
        self.xcor = x

    def set_ycor(self, y: float) -> None:
        self.ycor = y

    def set_random_position(self) -> None:
        self.ask("setxy random-xcor random-ycor")

    def wander(self, steps: float = 1) -> None:
        """Random heading, then ``steps`` forward."""
        self.ask(f"set heading random 360 fd {to_netlogo(steps)}")

    def face_to(self, target: Turtle) -> None:
        self.face(target)

    def set_heading(self, angle: float) -> None:
        self.heading = angle

    def get_heading(self) -> float:
        return self.heading

    def towards_point(self, x: float, y: float) -> float:
        return self.towardsxy(x, y)

    # position
    def get_xcor(self) -> float:
        return self.xcor

    def get_ycor(self) -> float:
        return self.ycor

    def get_xy(self) -> List[float]:
        return self.xy

    def distanceto(self, target: Turtle) -> float:
        return self.distance(target)

    def distance_to_point(self, x: float, y: float) -> float:
        return self.distancexy(x, y)

    # appearance
    def set_shape(self, shape: str) -> None:
        self.shape = shape

    def get_shape(self) -> str:
        return str(self.shape)

    def set_color(self, color: float) -> None:
        self.color = color

    def get_color(self) -> float:
        return self.color

    def set_size(self, size: float) -> None:
        self.size = size

    def get_size(self) -> float:
        return self.size

    def set_label(self, text: Any) -> None:
        self.label = str(text)

    def get_label(self) -> str:
        return str(self.label)

    def set_label_color(self, color: float) -> None:
        self.label_color = color

    def hideturtle(self) -> None:
        self.hide_turtle()

    def showturtle(self) -> None:
        self.show_turtle()

    def dieturtle(self) -> None:
        self.die()
        if self in list_pyturtle:
            list_pyturtle.remove(self)

    # pen (NetLogo draws with the turtle's own color)
    def set_pen_color(self, color: float) -> None:
        self.color = color

    def set_pen_size(self, size: float) -> None:
        self.pen_size = size

    # patches and neighbours
    def patch_here_color(self) -> float:
        return self.of("pcolor")

    def set_patch_here_color(self, color: float) -> None:
        self.ask(f"set pcolor {to_netlogo(color)}")

    def in_radius(self, radius: float) -> List[int]:  # type: ignore[override]
        """Who numbers of the OTHER turtles within ``radius``."""
        return [int(w) for w in self.of(f"sort [who] of other turtles in-radius {to_netlogo(radius)}")]

    def turtles_here(self) -> List[int]:  # type: ignore[override]
        """Who numbers of the OTHER turtles on the same patch."""
        return [int(w) for w in self.of("sort [who] of other turtles-here")]


class pyturtle(turtle):
    """A turtle of the ``pyturtles`` breed, created from Python.

    n          : session returned by run_netlogo()
    x, y       : position
    shape      : shape name (default 'car')
    size_shape : size
    color      : NetLogo color
    name       : label text
    labelcolor : label color
    fields     : extra Python attributes stored on the object, readable as
                 attributes (``car.busy``) or through ``car.fields["busy"]``
    """

    def __init__(self, n: NetLogo, x: float = 0, y: float = 0, shape: str = "car",
                 size_shape: float = 4, color: float = 0, name: str = "zn",
                 labelcolor: float = 0, fields: Optional[dict] = None):
        _require_breed(n, "turtles", "pyturtles")
        created = n.create_turtles(1, "pyturtles", ordered=True, xcor=x, ycor=y, shape=shape,
                                   size=size_shape, color=color, label=name,
                                   label_color=labelcolor)
        turtle.__init__(self, n, created[0].who)
        if fields:
            self.__dict__.update(fields)
        list_pyturtle.append(self)

    @property
    def fields(self) -> dict:
        """The extra Python attributes, as a live dict: ``car.fields["busy"]`` is ``car.busy``."""
        return self.__dict__


class street(Link):
    """A directed link of the ``streets`` breed between two turtles."""

    def __init__(self, n: NetLogo, fromm: Turtle, too: Turtle, label: str = "street",
                 labelcolor: float = 0, color: float = 0, shape: str = "default",
                 thickness: float = 0.5):
        _require_breed(n, "links", "streets")
        link = n.create_link(fromm, too, directed=True, breed="streets", label=label,
                             label_color=labelcolor, color=color, shape=shape,
                             thickness=thickness)
        Link.__init__(self, n, link.end1_who, link.end2_who, breed="streets",
                      directed=True, singular="street")
        list_street.append(self)

    @property
    def id(self) -> str:
        """``"<end1>_<end2>"``, as in netlogopy 0.x."""
        return f"{self.end1_who}_{self.end2_who}"

    @property
    def n(self) -> NetLogo:
        return self.nl


#: CamelCase names of the 0.x classes.
PyTurtle = pyturtle
Street = street
