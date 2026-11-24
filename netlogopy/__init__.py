"""netlogopy -- drive NetLogo models from Python.

>>> from netlogopy import NetLogo
>>> nl = NetLogo(gui=True)                       # bundled model, NetLogo window
>>> cars = nl.create_turtles(5, "pyturtles", shape="car", size=4)
>>> cars[0].forward(10)
>>> nl.report("mean [xcor] of turtles")

NetLogo runs inside the Python process through JPype (no server, no socket).
The 0.x functions (``run_netlogo``, ``pyturtle``, ``street``...) are still
available from ``netlogopy`` and ``netlogopy.netlogopy``.
"""

from . import colors
from ._java import find_netlogo_home, jvm_info, netlogo_version
from .agents import Agent, Link, Patch, Turtle
from .convert import Code, to_netlogo
from .core import BUNDLED_MODEL, BUNDLED_MODEL_NLOGOX, Globals, NetLogo, bundled_model
from .errors import NetLogoCompileError, NetLogoError, NetLogoNotFoundError, NetLogoRuntimeError
from .experiment import parameter_grid, run_experiment
from .netlogopy import (
    PyTurtle,
    Street,
    auto_plot_off,
    auto_plot_on,
    clear_all,
    clear_all_turtles,
    clear_drawing,
    clear_plot,
    count_pyturtles,
    create_ntlg_file,
    create_plot_pen,
    de_copy,
    distancebetween,
    do_tick,
    get_all_pyturtles,
    get_chooser,
    get_input_box,
    get_max_pxcor,
    get_max_pycor,
    get_min_pxcor,
    get_min_pycor,
    get_monitor,
    get_patch_color,
    get_random_xcor,
    get_random_ycor,
    # ── UI Widgets ──────────────────────────────────────────────────────────────
    get_slider,
    get_switch,
    # ── Ticks ───────────────────────────────────────────────────────────────────
    get_ticks,
    get_turtle_by_id,
    get_world_height,
    # ── World dimensions ────────────────────────────────────────────────────────
    get_world_width,
    # ── Agents ──────────────────────────────────────────────────────────────────
    getxyturtle,
    # ── Utilities ───────────────────────────────────────────────────────────────
    list2nllist,
    # ── Global lists ────────────────────────────────────────────────────────────
    list_pyturtle,
    list_street,
    netlogoshow,
    nl_output_print,
    plot_add,
    plot_xy,
    pyturtle,
    reset_base_file,
    reset_ticks,
    resize_world,
    resize_world_direct,
    # ── World ───────────────────────────────────────────────────────────────────
    run_command,
    # ── Initialisation ──────────────────────────────────────────────────────────
    run_netlogo,
    run_netlogo_base,
    run_netlogo_model,
    set_background,
    set_background_direct,
    set_chooser,
    # ── Plot widget ─────────────────────────────────────────────────────────────
    set_current_plot,
    set_input_box,
    # ── Patches ─────────────────────────────────────────────────────────────────
    set_patch_color,
    set_plot_pen,
    set_plot_pen_color,
    set_plot_pen_mode,
    set_plot_x_range,
    set_plot_y_range,
    set_slider,
    set_switch,
    street,
    tick_advance,
    # ── Classes ─────────────────────────────────────────────────────────────────
    turtle,
)

__all__ = [
    # new API
    "NetLogo", "Globals", "Agent", "Turtle", "Patch", "Link", "Code", "to_netlogo",
    "run_experiment", "parameter_grid", "colors",
    "NetLogoError", "NetLogoNotFoundError", "NetLogoCompileError", "NetLogoRuntimeError",
    "find_netlogo_home", "netlogo_version", "jvm_info",
    "BUNDLED_MODEL", "BUNDLED_MODEL_NLOGOX", "bundled_model",
    # netlogopy 0.x API
    "run_netlogo", "run_netlogo_base", "run_netlogo_model", "reset_base_file", "create_ntlg_file",
    "list2nllist", "de_copy", "get_turtle_by_id",
    "run_command", "resize_world", "resize_world_direct", "set_background", "set_background_direct",
    "netlogoshow", "nl_output_print", "clear_drawing", "clear_all", "clear_all_turtles",
    "get_ticks", "do_tick", "reset_ticks", "tick_advance",
    "get_world_width", "get_world_height", "get_max_pxcor", "get_min_pxcor",
    "get_max_pycor", "get_min_pycor", "get_random_xcor", "get_random_ycor",
    "set_patch_color", "get_patch_color",
    "getxyturtle", "distancebetween", "count_pyturtles", "get_all_pyturtles",
    "list_pyturtle", "list_street",
    "get_slider", "set_slider", "get_switch", "set_switch", "get_chooser", "set_chooser",
    "get_input_box", "set_input_box", "get_monitor",
    "set_current_plot", "set_plot_pen", "create_plot_pen", "plot_add", "plot_xy", "clear_plot",
    "set_plot_pen_color", "set_plot_pen_mode", "auto_plot_on", "auto_plot_off",
    "set_plot_x_range", "set_plot_y_range",
    "turtle", "pyturtle", "street", "PyTurtle", "Street",
]

__version__ = "1.0.0"
__author__  = "Nourddine Bouaziz"
__email__   = "nourddine.bouaziz.dz@gmail.com"
