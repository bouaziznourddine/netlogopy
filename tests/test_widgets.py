"""Interface widgets created from Python.

The widget descriptions are checked headless (NetLogo parses them without a
window).  The test that opens the NetLogo window and adds every kind of widget
runs only with NETLOGOPY_GUI_TESTS=1:

    NETLOGOPY_GUI_TESTS=1 pytest tests/test_widgets.py
"""

import os
import time

import pytest

from netlogopy import NetLogo, NetLogoError
from netlogopy.widgets import _color_rgb, _escape, _label

pytestmark = pytest.mark.netlogo


def _source(widget, name):
    value = getattr(widget, name)()
    return str(value.get()) if hasattr(value, "get") else str(value)


def test_code_with_quotes_backslashes_and_lines_survives(session):
    code = 'output-print "a\\\\b"\nprint "c"'
    widget = session._parse_widget(["BUTTON", "0", "0", "10", "10", _label('say "hi"'), _escape(code),
                                    "NIL", "1", "T", "OBSERVER", "NIL", "NIL", "NIL", "NIL", "1"])
    assert _source(widget, "source") == code and _source(widget, "display") == 'say "hi"'


def test_labels_are_kept_as_written(session):
    widget = session._parse_widget(["SLIDER", "0", "0", "10", "10", _label('rate "a" \\ b'), "rate",
                                    "0", "100", "50", "1", "1", _label("km/h"), "HORIZONTAL"])
    assert _source(widget, "display") == 'rate "a" \\ b' and _source(widget, "units") == "km/h"
    assert _label("") == "NIL" and _label("two\nlines") == "two lines"


def test_pen_colors_use_netlogo_rgb(session):
    assert _color_rgb(15) == _color_rgb([215, 50, 41])
    assert _color_rgb([0, 0, 0]) == -16777216


def test_widgets_need_the_window(session):
    with pytest.raises(NetLogoError, match="gui=True"):
        session.add_button("go")
    with pytest.raises(NetLogoError, match="gui=True"):
        session.press_button("go")


@pytest.mark.skipif(os.environ.get("NETLOGOPY_GUI_TESTS") != "1",
                    reason="opens the NetLogo window: set NETLOGOPY_GUI_TESTS=1")
def test_every_widget_in_the_window(tmp_path):
    with NetLogo(gui=True, setup=True) as nl:
        turtles = nl.create_turtles(5, "pyturtles")
        nl.tick()
        nl.add_slider("my-rate", 0, 100, 25, 5, units="%")
        nl.add_switch("my-flag", False)
        nl.add_chooser("my-mode", ["slow", "fast", 3], 1)
        nl.add_input("my-count", 12)
        nl.add_input("my-name", 'say "hi"')
        nl.add_button("hello", 'output-print (word "hello \\"you\\" " my-rate)')
        nl.add_button("turn", "rt 90", agents="turtles", forever=True)
        nl.add_monitor("my-rate * 2", "double")
        nl.add_plot("Agents", {"turtles": "plot count turtles"}, legend=True)
        nl.add_note("Added from Python")

        # the model keeps its state when it is recompiled
        assert nl.count("turtles") == 5 and nl.ticks == 1 and turtles[0].alive
        assert (nl.globals["my-rate"], nl.globals["my-flag"], nl.globals["my-mode"]) == (25, False, "fast")
        assert (nl.globals["my-count"], nl.globals["my-name"]) == (12, 'say "hi"')

        nl.globals["my-rate"] = 60
        nl.clear_output()
        nl.press_button("hello")
        output = tmp_path / "output.txt"
        nl.export_output(output)
        assert output.read_text().strip() == 'hello "you" 60'

        headings = nl.report("[heading] of turtles")
        nl.press_button("turn")
        time.sleep(0.5)
        nl.press_button("turn")
        assert nl.report("[heading] of turtles") != headings

        with pytest.raises(ValueError, match="already"):
            nl.add_slider("my-rate")
        with pytest.raises(ValueError, match="output area"):
            nl.add_output()
        with pytest.raises(NetLogoError, match="no button"):
            nl.press_button("missing")
