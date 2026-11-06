"""netlogopy -- bridge NetLogo and Python for agent-based simulations."""

__version__ = "0.2.0"
__author__  = "Nourddine Bouaziz"
__email__   = "nourddine.bouaziz.dz@gmail.com"

from .netlogopy import (
    # ── Errors and warnings ─────────────────────────────────────────────────────
    NetLogoError,
    NetLogoNotFoundError,
    NetLogoWarning,

    # ── Initialisation ──────────────────────────────────────────────────────────
    find_netlogo_home,
    is_netlogo_home,
    run_netlogo,
    run_netlogo_base,
    run_netlogo_model,
    close_netlogo,
    netlogo_session,
    reset_base_file,
    create_ntlg_file,
    NetLogoApp,
    HeadlessNetLogo,
    BASE_MODEL_PATH,
    BASE_NLS_PATH,

    # ── Utilities ───────────────────────────────────────────────────────────────
    list2nllist,
    de_copy,
    get_turtle_by_id,

    # ── World ───────────────────────────────────────────────────────────────────
    run_command,
    run_commands,
    report_value,
    resize_world,
    resize_world_direct,
    set_background,
    set_background_direct,
    netlogoshow,
    nl_output_print,
    clear_drawing,
    clear_all,
    clear_all_turtles,

    # ── Ticks ───────────────────────────────────────────────────────────────────
    get_ticks,
    do_tick,
    reset_ticks,
    tick_advance,

    # ── World dimensions ────────────────────────────────────────────────────────
    get_world_width,
    get_world_height,
    get_max_pxcor,
    get_min_pxcor,
    get_max_pycor,
    get_min_pycor,
    get_random_xcor,
    get_random_ycor,

    # ── Patches ─────────────────────────────────────────────────────────────────
    set_patch_color,
    get_patch_color,

    # ── Agents ──────────────────────────────────────────────────────────────────
    getxyturtle,
    distancebetween,
    count_pyturtles,
    get_all_pyturtles,
    get_all_xy,
    create_pyturtles,

    # ── Global lists ────────────────────────────────────────────────────────────
    list_pyturtle,
    list_street,

    # ── UI Widgets ──────────────────────────────────────────────────────────────
    get_slider,
    set_slider,
    get_switch,
    set_switch,
    get_chooser,
    set_chooser,
    get_input_box,
    set_input_box,
    get_monitor,

    # ── Plot widget ─────────────────────────────────────────────────────────────
    set_current_plot,
    set_plot_pen,
    create_plot_pen,
    plot_add,
    plot_xy,
    clear_plot,
    set_plot_pen_color,
    set_plot_pen_mode,
    auto_plot_on,
    auto_plot_off,
    set_plot_x_range,
    set_plot_y_range,

    # ── Classes ─────────────────────────────────────────────────────────────────
    turtle,
    pyturtle,
    street,
    Turtle,
    PyTurtle,
    Street,
)
