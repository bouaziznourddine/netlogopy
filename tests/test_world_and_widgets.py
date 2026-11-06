"""World, registry, street and widget helpers."""
import os

import pytest

import netlogopy.netlogopy as nlp
from conftest import FakeNetLogo
from netlogopy.netlogopy import (NetLogoError, NetLogoWarning, clear_all, clear_all_turtles,
                                 get_all_pyturtles, get_slider, get_switch, get_ticks,
                                 get_turtle_by_id, pyturtle, report_value, run_commands,
                                 set_background, set_chooser, set_current_plot, set_input_box,
                                 set_slider, set_switch, street, tick_advance)


# ── Registries with several NetLogo instances ─────────────────────────────────

def test_registry_is_per_instance():
    n1, n2 = FakeNetLogo(), FakeNetLogo()
    a, b = pyturtle(n1), pyturtle(n2)
    assert get_all_pyturtles(n1) == [a] and get_all_pyturtles(n2) == [b]
    assert get_all_pyturtles() == [a, b]
    assert get_turtle_by_id(0, n2) is b  # both have who number 0
    clear_all(n1)
    assert nlp.list_pyturtle == [b]


def test_clear_all_turtles_forgets_streets(n):
    a, b = pyturtle(n), pyturtle(n)
    street(n, fromm=a, too=b)
    clear_all_turtles(n)
    assert n.commands[-1] == "ask pyturtles [die]"
    assert nlp.list_pyturtle == [] and nlp.list_street == []


# ── street ────────────────────────────────────────────────────────────────────

def test_street_creation(n):
    a, b = pyturtle(n), pyturtle(n)
    s = street(n, fromm=a, too=b, label="rue", labelcolor=35, color=35, shape="default", thickness=0.5)
    assert n.last_report == 'create-street-ft [0 1 "rue" 35 35 "default" 0.5]'
    assert s.id == "0_1" and s.source is a and s.target is b
    assert nlp.list_street == [s]


def test_existing_street_warns(n):
    a, b = pyturtle(n), pyturtle(n)
    n.responses["create-street-ft"] = "0.0"
    with pytest.warns(NetLogoWarning, match="already exists"):
        s = street(n, fromm=a, too=b)
    assert s.id == "0_1"


def test_street_error_raises(n):
    a, b = pyturtle(n), pyturtle(n)
    n.responses["create-street-ft"] = "Nothing named CREATE-STREET-FT has been defined."
    with pytest.raises(NetLogoError):
        street(n, fromm=a, too=b)
    assert nlp.list_street == []


def test_street_methods(n):
    a, b = pyturtle(n), pyturtle(n)
    s = street(n, fromm=a, too=b)
    s.set_color(15)
    assert n.commands[-1] == "ask street 0 1 [ set color 15 ]"
    s.set_label('a "b"')
    assert n.commands[-1] == r'ask street 0 1 [ set label "a \"b\"" ]'
    s.die()
    assert n.commands[-1] == "ask street 0 1 [ die ]"
    assert nlp.list_street == []


# ── World and widgets ─────────────────────────────────────────────────────────

def test_get_ticks_error_is_explicit(n):
    n.responses["ticks"] = "The tick counter has not been started yet. Use RESET-TICKS."
    with pytest.raises(NetLogoError, match="RESET-TICKS"):
        get_ticks(n)


def test_slider_and_switch(n):
    set_slider(n, "speed", 2.5)
    assert n.commands[-1] == "set speed 2.5"
    set_slider(n, "speed", "10")  # strings are passed through, as before
    assert n.commands[-1] == "set speed 10"
    assert get_slider(n, "speed") == 10.0
    set_switch(n, "grass?", True)
    assert n.commands[-1] == "set grass? true"
    assert get_switch(n, "grass?") is True
    n.responses["missing?"] = "Nothing named MISSING? has been defined."
    with pytest.raises(NetLogoError):
        get_switch(n, "missing?")


def test_chooser_input_and_plot_escape_text(n):
    set_chooser(n, "strategy", 'FIFO "fast"')
    assert n.commands[-1] == r'set strategy "FIFO \"fast\""'
    set_input_box(n, "file", "C:\\data\\run.csv")
    assert n.commands[-1] == r'set file "C:\\data\\run.csv"'
    set_current_plot(n, "My Plot")
    assert n.commands[-1] == 'set-current-plot "My Plot"'
    tick_advance(n, 0.5)
    assert n.commands[-1] == "tick-advance 0.5"


def test_report_value_and_run_commands(n):
    n.responses["[who] of turtles"] = "[0.0, 1.0]"
    assert report_value(n, "[who] of turtles") == [0.0, 1.0]
    run_commands(n, ["setup", "go", "go"])
    assert n.commands[-1] == "setup\ngo\ngo"


def test_set_background_makes_existing_paths_absolute(n, tmp_path, monkeypatch):
    image = tmp_path / "map.png"
    image.write_bytes(b"png")
    monkeypatch.chdir(tmp_path)
    set_background(n, "map.png")
    assert n.last_report == "set_background " + nlp.list2nllist([os.path.abspath("map.png")])
    set_background(n, "not/here.png")
    assert n.last_report == 'set_background ["not/here.png"]'
