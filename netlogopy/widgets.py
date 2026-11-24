"""Interface widgets created from Python (NetLogo window).

The same items as NetLogo's "Add" menu: button, slider, switch, chooser,
input, monitor, plot, output, note.  A widget is described in NetLogo's own
text format, parsed by NetLogo (``WidgetReader``) and loaded in the Interface
tab; the model is then recompiled so the new variables exist.  The widgets
last for the session: use File > Save As in NetLogo to keep them in a model.
"""

from __future__ import annotations

import re
from typing import Any, List, Mapping, Optional, Sequence, Tuple, Union

from . import _java
from .convert import to_netlogo
from .errors import NetLogoError

__all__ = ["WidgetsMixin"]

_NAME = re.compile(r"^[^\s\[\]\(\)\"{};,]+$")
_AGENTS = {"observer": "OBSERVER", "turtles": "TURTLE", "turtle": "TURTLE", "patches": "PATCH",
           "patch": "PATCH", "links": "LINK", "link": "LINK"}
_INPUT_KINDS = {"number": "Number", "string": "String", "color": "Color",
                "reporter": "String (reporter)", "commands": "String (commands)"}
_PEN_MODES = {"line": 0, "bar": 1, "point": 2}
_GAP = 8


def _escape(text: Any) -> str:
    """One line of the widget format: backslashes, quotes and line breaks escaped."""
    text = str(text).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    return text if text else "NIL"


def _label(text: Any) -> str:
    """One line of the widget format that NetLogo reads as it is (labels, units, axes)."""
    text = " ".join(str(text).splitlines())
    return text if text else "NIL"


def _quoted(text: Any) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"') + '"'


def _number(value: Any) -> str:
    return to_netlogo(float(value)) if not isinstance(value, bool) else to_netlogo(value)


def _color_rgb(color: Any) -> int:
    """NetLogo color number (or [r g b]) -> the signed RGB integer used in the widget format."""
    if isinstance(color, (list, tuple)):
        red, green, blue = (int(channel) for channel in color[:3])
    else:
        import jpype
        rgb = jpype.JClass("org.nlogo.api.Color").getColor(jpype.JDouble(float(color)))
        red, green, blue = rgb.getRed(), rgb.getGreen(), rgb.getBlue()
    value = (255 << 24) | (red << 16) | (green << 8) | blue
    return value - (1 << 32)


class WidgetsMixin:
    """``add_button``, ``add_slider``... for :class:`netlogopy.NetLogo`."""

    # set by NetLogo
    gui: bool
    _ws: Any
    _app: Any

    # ─── plumbing ─────────────────────────────────────────────────────────────
    def _interface_panel(self) -> Any:
        if not self.gui:
            raise NetLogoError("interface widgets need the NetLogo window: NetLogo(gui=True)")
        self._check_open()                                    # type: ignore[attr-defined]
        manager = getattr(self._app, "tabManager", None)
        manager = manager() if manager is not None else None
        tab = manager.interfaceTab() if manager is not None and hasattr(manager, "interfaceTab") \
            else self._app.tabs().interfaceTab()
        return tab.iP()

    def _parse_widget(self, lines: Sequence[str]) -> Any:
        """NetLogo's own reading of a widget description (works without a window)."""
        import jpype
        module = lambda name: getattr(jpype.JClass(name), "MODULE$")       # noqa: E731
        scala_list = module("scala.collection.immutable.Nil$")
        for line in reversed(list(lines)):
            scala_list = getattr(scala_list, "$colon$colon")(jpype.JString(line))
        try:
            return module("org.nlogo.core.model.WidgetReader$").read(
                scala_list, module("org.nlogo.parse.CompilerUtilities$"),
                module("scala.collection.immutable.Map$").empty(),
                getattr(module("scala.Predef$"), "$conforms")())
        except jpype.JException as exc:
            raise NetLogoError(f"NetLogo refused the widget: {exc}") from None

    def _add_widget(self, lines: List[str], x: Optional[int], y: Optional[int],
                    width: int, height: int, variable: Optional[str] = None) -> None:
        panel = self._interface_panel()
        if variable is not None:
            if not _NAME.match(variable):
                raise ValueError(f"{variable!r} is not a valid NetLogo name")
            if variable.lower() in self.global_names():       # type: ignore[attr-defined]
                raise ValueError(f"the model already has a global or a widget named {variable!r}")
        self._stop_quietly()                                  # type: ignore[attr-defined]

        def load() -> None:
            boxes = [(c.getX(), c.getY(), c.getX() + c.getWidth(), c.getY() + c.getHeight())
                     for c in panel.getComponents() if hasattr(c, "widget")]
            left, top = x, y
            if left is None:                 # a column of its own, right of the model's widgets
                column = getattr(self, "_widget_column", None)
                if column is None or column[0] != int(panel.hashCode()):
                    column = (int(panel.hashCode()), max([box[2] for box in boxes] or [0]) + _GAP)
                    self._widget_column = column
                left = column[1]
            if top is None:                  # under the widgets already in that column
                below = [box[3] for box in boxes if box[0] < left + width and box[2] > left]
                top = max(below) + _GAP if below else 10
            position = [str(int(left)), str(int(top)), str(int(left + width)), str(int(top + height))]
            panel.loadWidget(self._parse_widget([lines[0]] + position + lines[1:]))
            panel.revalidate()
            panel.repaint()
            self._app.compile()

        _java.run_on_edt(load)
        self._cache.clear()                                   # type: ignore[attr-defined]

    # ─── the "Add" menu ───────────────────────────────────────────────────────
    def add_button(self, label: str, commands: Optional[str] = None, *, forever: bool = False,
                   agents: str = "observer", key: Optional[str] = None,
                   disable_until_ticks: bool = False, x: Optional[int] = None,
                   y: Optional[int] = None, width: int = 115, height: int = 33) -> None:
        """Add a button to the interface (NetLogo window only).

        Parameters
        ----------
        label : str
            Text of the button.
        commands : str, optional
            NetLogo commands it runs (default: the procedure named ``label``).
        forever : bool, default False
            Make it a forever button.
        agents : str, default "observer"
            "observer", "turtles", "patches" or "links".
        key : str, optional
            Action key (one letter).
        disable_until_ticks : bool, default False
            Disable the button until the ticks start.
        x, y : int, optional
            Position in pixels (default: a column right of the model's widgets,
            under the widgets already added there).
        width, height : int
            Size in pixels.
        """
        self._add_widget(
            ["BUTTON", _label(label), _escape(commands if commands is not None else label),
             "T" if forever else "NIL", "1", "T", _AGENTS[agents.lower()], "NIL",
             key.upper() if key else "NIL", "NIL", "NIL", "0" if disable_until_ticks else "1"],
            x, y, width, height)

    def add_slider(self, name: str, minimum: Any = 0, maximum: Any = 100, value: float = 50,
                   step: Any = 1, *, units: Optional[str] = None, vertical: bool = False,
                   x: Optional[int] = None, y: Optional[int] = None,
                   width: Optional[int] = None, height: Optional[int] = None) -> None:
        """Add a slider; ``name`` becomes a global.  Bounds and step may be NetLogo reporters."""
        bound = lambda v: v if isinstance(v, str) else _number(v)          # noqa: E731
        default_size = (33, 150) if vertical else (240, 33)
        self._add_widget(
            ["SLIDER", _label(name), _label(name), bound(minimum), bound(maximum),
             _number(value), bound(step), "1", _label(units) if units else "NIL",
             "VERTICAL" if vertical else "HORIZONTAL"],
            x, y, width or default_size[0], height or default_size[1], variable=name)

    def add_switch(self, name: str, on: bool = True, *, x: Optional[int] = None,
                   y: Optional[int] = None, width: int = 240, height: int = 33) -> None:
        """Add an on/off switch; ``name`` becomes a boolean global."""
        self._add_widget(["SWITCH", _label(name), _label(name), "0" if on else "1", "1", "-1000"],
                         x, y, width, height, variable=name)

    def add_chooser(self, name: str, choices: Sequence[Any], selected: int = 0, *,
                    x: Optional[int] = None, y: Optional[int] = None,
                    width: int = 240, height: int = 45) -> None:
        """Add a drop-down list; ``selected`` is the index of the initial choice."""
        choices = list(choices)
        if not choices or not 0 <= int(selected) < len(choices):
            raise ValueError("a chooser needs choices, and 'selected' must be one of their indexes")
        self._add_widget(["CHOOSER", _label(name), _label(name),
                          " ".join(to_netlogo(choice) for choice in choices), str(int(selected))],
                         x, y, width, height, variable=name)

    def add_input(self, name: str, value: Any = "", *, kind: Optional[str] = None,
                  multiline: bool = False, x: Optional[int] = None, y: Optional[int] = None,
                  width: int = 240, height: int = 60) -> None:
        """Add an input box; ``name`` becomes a global (NetLogo window only).

        Parameters
        ----------
        name : str
            Name of the global.
        value : Any, default ""
            Initial value.
        kind : str, optional
            "number", "string", "color", "reporter" or "commands" (default:
            "number" for numbers, "string" otherwise).
        multiline : bool, default False
            Allow several lines of text.
        x, y : int, optional
            Position in pixels (default: a column right of the model's widgets,
            under the widgets already added there).
        width, height : int
            Size in pixels.
        """
        if kind is None:
            kind = "number" if isinstance(value, (int, float)) and not isinstance(value, bool) else "string"
        text = _number(value) if kind in ("number", "color") else _escape(value)
        self._add_widget(["INPUTBOX", _label(name), text, "1", "1" if multiline else "0",
                          _INPUT_KINDS[kind.lower()]], x, y, width, height, variable=name)

    def add_monitor(self, reporter: str, label: Optional[str] = None, *, decimals: int = 17,
                    font_size: int = 11, x: Optional[int] = None, y: Optional[int] = None,
                    width: int = 115, height: int = 45) -> None:
        """Add a monitor showing the value of ``reporter``."""
        self._add_widget(["MONITOR", _label(label) if label else "NIL", _escape(reporter),
                          str(int(decimals)), "1", str(int(font_size))], x, y, width, height)

    def add_plot(self, name: str, pens: Union[None, Sequence[str], Mapping[str, str]] = None, *,
                 x_label: str = "", y_label: str = "", x_range: Tuple[float, float] = (0, 10),
                 y_range: Tuple[float, float] = (0, 10), autoplot: bool = True,
                 legend: bool = False, setup: str = "", update: str = "",
                 colors: Optional[Mapping[str, Any]] = None, mode: str = "line",
                 x: Optional[int] = None, y: Optional[int] = None,
                 width: int = 240, height: int = 160) -> None:
        """Add a plot to the interface (NetLogo window only).

        Parameters
        ----------
        name : str
            Name of the plot.
        pens : sequence of str or mapping, optional
            Pen names, or ``{pen name: update commands}`` such as
            ``{"sheep": "plot count sheep"}`` (run at each tick).  Default:
            one pen named "default".
        x_label, y_label : str
            Axis labels.
        x_range, y_range : tuple of float, default (0, 10)
            Initial ranges of the axes.
        autoplot : bool, default True
            Widen the ranges to fit the points.
        legend : bool, default False
            Show the pen legend.
        setup, update : str
            Plot setup and update commands.
        colors : mapping, optional
            A NetLogo color per pen name.
        mode : str, default "line"
            "line", "bar" or "point".
        x, y : int, optional
            Position in pixels (default: a column right of the model's widgets,
            under the widgets already added there).
        width, height : int
            Size in pixels.

        Examples
        --------
        >>> nl.add_plot("population", {"sheep": "plot count sheep"}, colors={"sheep": 15})
        """
        if pens is None:
            pens = ["default"]
        if not isinstance(pens, Mapping):
            pens = {pen: "" for pen in pens}
        palette = [0, 15, 105, 55, 25, 115, 85, 35, 125, 45]
        lines = ["PLOT", _label(name), _label(x_label), _label(y_label),
                 _number(x_range[0]), _number(x_range[1]), _number(y_range[0]), _number(y_range[1]),
                 "true" if autoplot else "false", "true" if legend else "false",
                 f"{_quoted(setup)} {_quoted(update)}", "PENS"]
        for index, (pen, code) in enumerate(pens.items()):
            color = (colors or {}).get(pen, palette[index % len(palette)])
            lines.append(f"{_quoted(pen)} 1.0 {_PEN_MODES[mode.lower()]} {_color_rgb(color)} true "
                         f'"" {_quoted(code)}')
        self._add_widget(lines, x, y, width, height)

    def add_output(self, *, font_size: int = 12, x: Optional[int] = None, y: Optional[int] = None,
                   width: int = 240, height: int = 100) -> None:
        """Add the output area (a model has one at most)."""
        panel = self._interface_panel()
        if _java.run_on_edt(lambda: any(
                hasattr(c, "widget") and str(c.widget().getClass().getSimpleName()) == "OutputWidget"
                for c in panel.getComponents())):
            raise ValueError("the interface already has an output area")
        self._add_widget(["OUTPUT", str(int(font_size))], x, y, width, height)

    def add_note(self, text: str, *, font_size: int = 11, color: Any = 0,
                 transparent: bool = True, x: Optional[int] = None, y: Optional[int] = None,
                 width: int = 240, height: int = 30) -> None:
        """Add a text note."""
        self._add_widget(["TEXTBOX", _escape(text), str(int(font_size)), _number(color),
                          "1" if transparent else "0"], x, y, width, height)

    def press_button(self, label: str, *, wait: float = 10.0) -> None:
        """Click a button of the interface (NetLogo window only).

        Parameters
        ----------
        label : str
            Text of the button.
        wait : float, default 10.0
            A normal button is waited for, at most ``wait`` seconds; a
            forever button starts, and stops when pressed again.

        Raises
        ------
        NetLogoError
            The interface has no button with this label.
        """
        import time
        panel = self._interface_panel()

        def find() -> Any:
            for component in panel.getComponents():
                widget = component.widget() if hasattr(component, "widget") else None
                if (widget is not None and hasattr(widget, "keyTriggered")
                        and str(widget.displayName()) == label):
                    return widget
            return None

        button = _java.run_on_edt(find)
        if button is None:
            raise NetLogoError(f"the interface has no button named {label!r}")
        forever = bool(button.forever())
        _java.run_on_edt(button.keyTriggered)
        if not forever:
            deadline = time.monotonic() + wait
            time.sleep(0.05)
            while bool(button.running()) and time.monotonic() < deadline:
                time.sleep(0.01)
