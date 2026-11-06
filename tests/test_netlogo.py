"""The NetLogo session API against a real NetLogo (headless)."""

import os
import threading

import pytest

from conftest import FIRE_MODEL
from netlogopy import (Code, Link, NetLogo, NetLogoCompileError, NetLogoError,
                       NetLogoRuntimeError, Patch, Turtle, jvm_info, to_netlogo)

pytestmark = pytest.mark.netlogo


def test_report_types(nl):
    nl.create_turtles(2, "pyturtles")
    nl.create_link(0, 1, breed="streets")
    assert nl.report("1 + 1") == 2.0
    assert nl.report('"text"') == "text"
    assert nl.report("true") is True and nl.report("false") is False
    assert nl.report('[1 "a" [true]]') == [1.0, "a", [True]]
    assert nl.report("nobody") is None
    assert nl.report("turtle 1") == Turtle(nl, 1)
    assert nl.report("patch 2 3") == Patch(nl, 2, 3)
    assert nl.report("street 0 1") == Link(nl, 0, 1, breed="streets", directed=True)
    assert nl.report("turtles") == [Turtle(nl, 0), Turtle(nl, 1)]
    assert nl.report(["count turtles", "max-pxcor"]) == [2.0, 60.0]
    assert nl.report([]) == []
    assert isinstance(nl.report("[ x -> x ]"), str)        # anonymous reporter: printed form


@pytest.mark.parametrize("text", ['plain', 'say "hi"', "back\\slash", "two\nlines\ttab", "é ü 中 ✓", ""])
def test_strings_round_trip(nl, text):
    assert nl.report(to_netlogo(text)) == text
    turtle = nl.create_turtles(1, label=text)[0]
    assert turtle.label == text


@pytest.mark.parametrize("number", [0, -3, 2.5, 1e-05, 1e20, -0.125, 123456789])
def test_numbers_round_trip(nl, number):
    assert nl.report(to_netlogo(number)) == float(number)


def test_errors(nl):
    with pytest.raises(NetLogoCompileError) as info:
        nl.command("foo-bar 3")
    assert "FOO-BAR" in info.value.message and info.value.source == "foo-bar 3"
    with pytest.raises(NetLogoRuntimeError, match="NOBODY"):
        nl.command("ask turtle 999 [ fd 1 ]")
    with pytest.raises(NetLogoRuntimeError, match="NOBODY"):
        nl.report("[xcor] of turtle 999")
    with pytest.raises(NetLogoRuntimeError, match="[Dd]ivision by zero"):
        nl.command("let x 0 show 1 / x")
    with pytest.raises(NetLogoCompileError):
        nl.report("count")
    assert nl.report("count patches") == 3721     # the session still works


def test_compiled_code_cache_is_bounded(nl):
    for i in range(1200):
        nl.command(f"tick-advance {i}")
    assert len(nl._cache) <= 1024


def test_globals_and_widgets(nl):
    assert {"speed", "show-label", "scenario", "user-text"} <= set(nl.global_names())
    nl.globals["speed"] = 7
    nl.set_global("show-label", False)
    nl.globals["scenario"] = "custom"
    nl.globals["user-text"] = 'with "quotes"'
    assert nl.get_global("speed") == 7.0
    assert nl.globals["show-label"] is False
    assert nl.globals.to_dict() == {"speed": 7.0, "show-label": False,
                                    "scenario": "custom", "user-text": 'with "quotes"'}
    assert "speed" in nl.globals and "nope" not in nl.globals and len(nl.globals) == 4
    nl.globals["speed"] = 1
    nl.globals["show-label"] = True
    nl.globals["scenario"] = "default"


def test_ticks(nl):
    assert nl.ticks == 0
    nl.tick()
    nl.tick_advance(0.5)
    assert nl.ticks == 1.5
    nl.go(3)                     # the bundled go procedure ticks
    assert nl.ticks == 4.5
    nl.reset_ticks()
    assert nl.ticks == 0
    nl.clear_ticks()
    with pytest.raises(NetLogoRuntimeError):
        nl.ticks


def test_world(nl):
    assert (nl.min_pxcor, nl.max_pxcor, nl.world_width, nl.world_height) == (0, 60, 61, 61)
    nl.resize_world(-10, 10, -5, 5)
    assert (nl.min_pxcor, nl.max_pxcor, nl.min_pycor, nl.max_pycor) == (-10, 10, -5, 5)
    assert nl.count("patches") == 21 * 11
    nl.set_topology(True, False)
    assert nl.wrap_x and not nl.wrap_y
    size = nl.patch_size
    nl.set_patch_size(5)
    assert nl.patch_size == 5
    nl.set_patch_size(size)
    nl.display()
    nl.no_display()
    nl.display()


def test_random_seed_makes_runs_reproducible(nl):
    def positions():
        nl.clear_turtles()
        nl.random_seed(42)
        nl.create_turtles(5, xcor=Code("random-xcor"), ycor=Code("random-ycor"))
        return nl.of("turtles", "(list xcor ycor)")
    assert positions() == positions()
    assert isinstance(nl.new_seed(), int)


def test_agents_queries(nl):
    cars = nl.create_turtles(4, "pyturtles", ordered=True, color=15, xcor=10, ycor=10)
    others = nl.create_turtles(2, color=55)
    assert [t.who for t in cars] == [0, 1, 2, 3] and [t.who for t in others] == [4, 5]
    assert [t.heading for t in cars] == [0, 90, 180, 270]
    assert nl.turtles() == cars + others
    assert nl.turtles("pyturtles") == cars
    assert nl.turtles(where="color = 55") == others
    assert nl.count() == 6 and nl.count("pyturtles", "heading > 100") == 2
    assert nl.of("pyturtles", "who") == [0, 1, 2, 3]
    nl.ask(cars[:2], "set color 105")
    nl.ask("turtles with [color = 55]", "die")
    assert nl.of(cars, "color") == [105, 105, 15, 15] and nl.count() == 4
    assert nl.turtle(2) == cars[2] and nl.patch(3, 4) == Patch(nl, 3, 4)
    assert nl.patch(3.4, 3.6) == Patch(nl, 3, 4)
    assert nl.patches(where="pxcor = 0 and pycor < 2") == [Patch(nl, 0, 1), Patch(nl, 0, 0)]
    assert nl.of([], "who") == []


def test_create_turtles_variables(nl):
    turtle = nl.create_turtles(1, "pyturtles", xcor=5, ycor=6, shape="car", size=3,
                               label="a", label_color=45, hidden=True,
                               variables={"pen-size": 2})[0]
    assert turtle.get_many(["xcor", "ycor", "shape", "size", "label", "label-color",
                            "hidden?", "pen-size"]) == {
        "xcor": 5, "ycor": 6, "shape": "car", "size": 3, "label": "a", "label-color": 45,
        "hidden?": True, "pen-size": 2}
    assert nl.create_turtles(0) == []


def test_patch_grid(nl):
    numbers = [[(x * 3 + y) % 140 for x in range(61)] for y in range(61)]
    nl.set_patch_grid("pcolor", numbers)
    grid = nl.patch_grid()
    assert grid == numbers
    assert nl.patch(0, 60).pcolor == numbers[0][0]          # row 0 is the top row
    assert nl.patch(60, 0).pcolor == numbers[60][60]
    with pytest.raises(ValueError):
        nl.set_patch_grid("pcolor", [[0]])
    numpy = pytest.importorskip("numpy")
    array = nl.patch_grid(as_array=True)
    assert array.shape == (61, 61)
    nl.set_patch_grid("pcolor", numpy.zeros((61, 61)))
    assert nl.count("patches", "pcolor != 0") == 0


def test_diffuse(nl):
    nl.patch(30, 30).pcolor = 100
    nl.diffuse("pcolor", 0.5)
    assert nl.patch(30, 30).pcolor == 50
    assert nl.report("sum [pcolor] of patches") == pytest.approx(100)
    nl.diffuse("pcolor", 1, neighbors=4)


def test_collect(nl):
    data = nl.collect({"t": "ticks", "n": "count turtles"}, 5)
    assert data == {"step": [0, 1, 2, 3, 4, 5], "t": [0, 1, 2, 3, 4, 5], "n": [0] * 6}
    data = nl.collect("ticks", 10, every=4, include_initial=False)
    assert data == {"step": [4, 8, 10], "ticks": [9, 13, 15]}
    data = nl.collect(["ticks"], 100, until="ticks >= 18")
    assert data["step"][-1] == 3 and data["ticks"][-1] == 18
    pandas = pytest.importorskip("pandas")
    frame = nl.collect(["ticks", "count patches"], 2, as_dataframe=True)
    assert isinstance(frame, pandas.DataFrame) and list(frame.columns) == ["step", "ticks", "count patches"]


def test_run_until_and_schedule_reporters(nl):
    assert nl.run_until("ticks >= 5") == 5
    assert nl.run_until("ticks >= 100", max_steps=3) == 3
    nl.reset_ticks()
    results = nl.schedule_reporters(["ticks", "count turtles"], start_at_tick=2,
                                    interval_ticks=2, stop_at_tick=6)
    assert results == [[2, 0], [4, 0], [6, 0]]
    with pytest.raises(ValueError):
        nl.schedule_reporters(["ticks"])


def test_files(nl, tmp_path):
    nl.create_turtles(3, "pyturtles", xcor=Code("random-xcor"))
    view = nl.export_view(tmp_path / "view.png")
    assert os.path.getsize(view) > 1000
    world = nl.export_world(tmp_path / "world.csv")
    positions = nl.of("turtles", "xcor")
    nl.clear_all()
    assert nl.count() == 0
    nl.import_world(world)
    assert nl.of("turtles", "xcor") == positions
    nl.output_print("hello")
    assert os.path.isfile(nl.export_output(tmp_path / "output.txt"))
    nl.plot(1, plot="My Plot")
    assert os.path.isfile(nl.export_plot("My Plot", tmp_path / "plot.csv"))
    assert os.path.isfile(nl.export_all_plots(tmp_path / "plots.csv"))
    nl.import_drawing(os.path.join(os.path.dirname(FIRE_MODEL), "..", "..", "netlogopy.png"))
    nl.import_pcolors(view)
    nl.clear_drawing()
    with pytest.raises(NetLogoError):
        nl.export_interface(tmp_path / "interface.png")     # needs the window


def test_output_and_plots(nl):
    nl.show("shown")
    nl.output_print([1, 2])
    nl.output_show("x")
    nl.output_type("y")
    nl.output_write(3)
    nl.clear_output()
    nl.set_current_plot("My Plot")
    nl.create_temporary_plot_pen("extra")
    nl.set_current_plot_pen("default")
    nl.set_plot_pen_color(15)
    nl.set_plot_pen_mode(1)
    nl.set_plot_pen_interval(2)
    nl.set_plot_x_range(0, 50)
    nl.set_plot_y_range(-1, 1)
    nl.plot_pen_up()
    nl.plot_pen_down()
    nl.plot(0.5)
    nl.plotxy(3, 0.25, plot="My Plot", pen="extra")
    nl.set_histogram_num_bars(5)
    nl.histogram([1, 2, 2, 3])
    nl.histogram("[xcor] of turtles")
    nl.plot_pen_reset()
    nl.auto_plot_off()
    nl.auto_plot_on()
    nl.clear_plot("My Plot")
    nl.update_plots()
    nl.setup_plots()
    nl.clear_all_plots()
    with pytest.raises(NetLogoRuntimeError):
        nl.set_current_plot("No such plot")


def test_layouts(nl):
    hub, *spokes = nl.create_turtles(6, "pyturtles")
    for spoke in spokes:
        nl.create_link(hub, spoke, breed="streets")
    before = nl.of("turtles", "(list xcor ycor)")
    nl.layout_circle("pyturtles", 20)
    assert nl.of("turtles", "distancexy 30 30") == pytest.approx([20] * 6)
    nl.layout_spring("pyturtles", "streets", iterations=10)
    nl.layout_radial("pyturtles", "streets", hub)
    nl.layout_tutte(spokes, "streets", 10)
    nl.layout_circle(spokes)
    assert nl.of("turtles", "(list xcor ycor)") != before


def test_observer_perspective(nl):
    turtle = nl.create_turtles(1)[0]
    nl.watch(turtle)
    nl.follow(turtle)
    nl.ride(turtle)
    nl.reset_perspective()
    assert nl.report("subject") is None


def test_information(nl):
    assert nl.breeds() == {"turtles": ["pyturtles"], "links": ["streets"]}
    assert "car" in nl.shapes() and "default" in nl.link_shapes()
    version = nl.netlogo_version
    assert version == jvm_info()["version"] and version.split(".")[0] in ("6", "7")
    assert repr(nl).startswith("<NetLogo headless 'netlogopy.nlogo")


def test_other_models_and_closing():
    with NetLogo(FIRE_MODEL) as fire:
        assert fire.breeds()["turtles"] == ["embers", "fires", "pyturtles"]
        fire.set_global("density", 70)
        fire.setup()
        fire.run_until("not any? turtles", max_steps=1000)
        assert fire.report("burned-trees") > 0
        fire.open_model(os.path.join(os.path.dirname(FIRE_MODEL), "..", "Wolf Sheep",
                                     "Wolf Sheep Predation.nlogo"))
        assert "wolves" in fire.breeds()["turtles"]
    assert fire.closed
    with pytest.raises(NetLogoError):
        fire.command("clear-all")
    with pytest.raises(FileNotFoundError):
        NetLogo("missing.nlogo")


def test_sessions_run_in_parallel():
    def run(density, results):
        with NetLogo(FIRE_MODEL) as fire:
            fire.random_seed(1)
            fire.set_global("density", density)
            fire.setup()
            fire.run_until("not any? turtles", max_steps=2000)
            results[density] = fire.report("burned-trees") / fire.report("initial-trees")

    results = {}
    threads = [threading.Thread(target=run, args=(d, results)) for d in (40, 75)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results[40] < 0.5 < results[75]
