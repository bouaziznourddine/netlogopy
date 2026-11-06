"""The netlogopy 0.x API (run_netlogo, pyturtle, street...) on the new engine."""

import os

import pytest

import netlogopy.netlogopy as legacy
from conftest import EXAMPLES, WOLF_MODEL

pytestmark = pytest.mark.netlogo


@pytest.fixture
def n():
    session = legacy.run_netlogo(gui=False)
    yield session
    session.close_model()


def test_star_import_exposes_old_and_new_names():
    namespace = {}
    exec("from netlogopy.netlogopy import *", namespace)
    for name in ("run_netlogo", "pyturtle", "street", "resize_world", "get_slider",
                 "plot_add", "NetLogo", "Turtle", "Code"):
        assert name in namespace


def test_pyturtle_and_street(n):
    legacy.resize_world(n, 0, 60, 0, 60)
    car01 = legacy.pyturtle(n, x=20, y=20, shape="car", size_shape=9, color=15,
                            name="car01", labelcolor=15, fields={"speed": 3})
    car02 = legacy.pyturtle(n, x=5, y=5, color=55, name="car02")
    road = legacy.street(n, fromm=car01, too=car02, label="street", labelcolor=35,
                         color=35, shape="default", thickness=0.5)
    assert (car01.id, car02.id) == (0, 1) and car01.n is n and car01.speed == 3
    assert car01.get_shape() == "car" and car01.get_size() == 9 and car01.get_label() == "car01"
    assert car01.get_heading() == 0                       # create-ordered with 1 turtle
    assert road.id == "0_1" and road.n is n and road.label == "street" and road.directed
    assert legacy.get_all_pyturtles() == [car01, car02] and legacy.list_street == [road]
    assert legacy.get_turtle_by_id(1) is car02 and legacy.get_turtle_by_id(9) is None
    assert legacy.count_pyturtles(n) == 2


def test_turtle_methods(n):
    car = legacy.pyturtle(n, x=30, y=30)
    other = legacy.pyturtle(n, x=31, y=30)
    car.set_heading(90)
    car.fd(2)
    car.bk(1)
    car.rt(90)
    car.lt(90)
    assert car.get_xy() == [31, 30] and car.get_xcor() == 31 and car.get_ycor() == 30
    assert legacy.getxyturtle(n, car) == [31, 30]
    car.set_xcor(10)
    car.set_ycor(12)
    car.setxy(10, 30)
    assert car.distanceto(other) == 21 and legacy.distancebetween(n, car, other) == 21
    assert car.distance_to_point(13, 34) == 5 and car.towards_point(10, 40) == 0
    car.face_to(other)
    assert car.get_heading() == 90
    car.move_to(other)
    assert car.get_xy() == [31, 30]
    assert car.in_radius(1) == [other.id] and car.turtles_here() == [other.id]
    car.set_color(25)
    car.set_size(3)
    car.set_label(7)
    car.set_label_color(45)
    car.set_shape("default")
    assert (car.get_color(), car.get_size(), car.get_label(), car.get_shape()) == (25, 3, "7", "default")
    car.set_pen_color(105)
    car.set_pen_size(2)
    assert car.get_color() == 105 and car.pen_size == 2
    car.pen_down()
    car.wander(1)
    car.pen_erase()
    car.pen_up()
    car.stamp()
    car.stamp_erase()
    car.home()
    car.set_heading(0)
    assert car.get_xy() == [0, 0]
    n.set_topology(False, False)
    assert car.can_move(1) and not car.can_move(-1)
    car.set_random_position()
    car.set_patch_here_color(15)
    assert car.patch_here_color() == 15
    car.hideturtle()
    assert car.hidden
    car.showturtle()
    car.dieturtle()
    assert car not in legacy.list_pyturtle and legacy.count_pyturtles(n) == 1


def test_world_functions(n, tmp_path):
    legacy.resize_world_direct(n, 0, 20, 0, 10)
    assert (legacy.get_world_width(n), legacy.get_world_height(n)) == (21, 11)
    assert (legacy.get_min_pxcor(n), legacy.get_max_pxcor(n),
            legacy.get_min_pycor(n), legacy.get_max_pycor(n)) == (0, 20, 0, 10)
    for _ in range(20):            # random-xcor: from min-pxcor - 0.5 to max-pxcor + 0.5
        assert -0.5 <= legacy.get_random_xcor(n) < 20.5 and -0.5 <= legacy.get_random_ycor(n) < 10.5
    legacy.set_patch_color(n, 3, 4, 15)
    assert legacy.get_patch_color(n, 3, 4) == 15
    legacy.set_background(n, os.path.join(EXAMPLES, "netlogopy.png"))
    legacy.set_background_direct(n, os.path.join(EXAMPLES, "netlogopy.png"))
    legacy.clear_drawing(n)
    legacy.netlogoshow(n, "shown")
    legacy.nl_output_print(n, "printed")
    legacy.run_command(n, "crt 2")
    legacy.reset_ticks(n)
    legacy.do_tick(n)
    legacy.tick_advance(n, 2)
    assert legacy.get_ticks(n) == 3
    legacy.pyturtle(n)
    legacy.clear_all_turtles(n)
    assert legacy.count_pyturtles(n) == 0 and legacy.list_pyturtle == []
    legacy.clear_all(n)
    assert n.count() == 0
    legacy.reset_base_file(str(tmp_path))
    legacy.create_ntlg_file(str(tmp_path))
    assert (tmp_path / "base.nls").is_file() and (tmp_path / "base2.nls").is_file()
    assert legacy.de_copy([1, [2]]) == [1, [2]]


def test_widgets_and_plots(n):
    legacy.set_slider(n, "speed", 4)
    legacy.set_switch(n, "show-label", False)
    legacy.set_chooser(n, "scenario", "custom")
    legacy.set_input_box(n, "user-text", "hello")
    assert legacy.get_slider(n, "speed") == 4.0 and legacy.get_switch(n, "show-label") is False
    assert legacy.get_chooser(n, "scenario") == "custom" and legacy.get_input_box(n, "user-text") == "hello"
    assert legacy.get_monitor(n, "count patches") == 3721
    legacy.set_current_plot(n, "My Plot")
    legacy.create_plot_pen(n, "distance")
    legacy.set_plot_pen(n, "distance")
    legacy.set_plot_pen_color(n, 15)
    legacy.set_plot_pen_mode(n, 0)
    legacy.set_plot_x_range(n, 0, 30)
    legacy.set_plot_y_range(n, 0, 60)
    legacy.auto_plot_off(n)
    legacy.auto_plot_on(n)
    legacy.plot_add(n, 2)
    legacy.plot_xy(n, 1, 3)
    legacy.clear_plot(n)
    legacy.set_switch(n, "show-label", True)
    legacy.set_slider(n, "speed", 1)
    legacy.set_chooser(n, "scenario", "default")
    legacy.set_input_box(n, "user-text", "netlogopy")


def test_external_model_with_base_nls():
    n = legacy.run_netlogo_model(None, WOLF_MODEL, gui=False)
    try:
        legacy.set_chooser(n, "model-version", "sheep-wolves-grass")
        legacy.set_slider(n, "initial-number-sheep", 80)
        legacy.run_command(n, "setup")
        observer = legacy.pyturtle(n, x=0, y=0, shape="circle", color=105, name="observer")
        assert observer.get_label() == "observer"
        legacy.street(n, observer, legacy.pyturtle(n, x=5, y=5), label="road")
        legacy.run_command(n, "repeat 5 [ go ]")        # the model's go also moves pyturtles
        assert legacy.get_ticks(n) == 5 and legacy.get_monitor(n, "count sheep") > 0
        assert observer.alive and observer.get_shape() == "circle"
    finally:
        n.close_model()


def test_run_netlogo_honours_netlogopy_headless(monkeypatch):
    monkeypatch.setenv("NETLOGOPY_HEADLESS", "1")
    n = legacy.run_netlogo_base()
    try:
        assert not n.gui and n.ticks == 0
    finally:
        n.close()
