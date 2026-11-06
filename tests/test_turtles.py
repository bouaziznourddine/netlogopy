"""pyturtle: what is sent to NetLogo and how results are read back."""
import warnings

import pytest

import netlogopy.netlogopy as nlp
from netlogopy.netlogopy import (NetLogoError, NetLogoWarning, create_pyturtles,
                                 get_all_xy, getxyturtle, pyturtle, street)


def test_pyturtle_creation_sends_one_reporter(n):
    car = pyturtle(n, x=20, y=20, shape="car", size_shape=9, color=15, name="car01", labelcolor=15)
    assert n.last_report == 'create-pyturtle-xyid [20 20 "car" 9 15 "car01" 15]'
    assert car.id == 0 and car.n is n
    assert nlp.list_pyturtle == [car]


def test_pyturtle_fields_default_is_not_shared(n):
    a = pyturtle(n)
    b = pyturtle(n, fields={"speed": 3})
    assert b.speed == 3 and not hasattr(a, "speed")


def test_fd_sends_fractional_and_negative_steps(n):
    car = pyturtle(n)
    car.fd(0.5)
    assert n.last_report == "fdfd [0 0.5]"
    car.bk(-2)
    assert n.last_report == "bkbk [0 -2]"


def test_can_move_reads_false_correctly(n):
    car = pyturtle(n)
    n.responses["can_move_turtle"] = "false"
    assert car.can_move(3) is False
    n.responses["can_move_turtle"] = "true"
    assert car.can_move(3) is True


def test_in_radius_parses_several_neighbours(n):
    car = pyturtle(n)
    n.responses["in_radius_turtle"] = "[1.0, 2.0, 7.0]"
    assert car.in_radius(5) == [1, 2, 7]
    n.responses["in_radius_turtle"] = "[]"
    assert car.in_radius(5) == []


def test_getxyturtle_and_get_xy(n):
    car = pyturtle(n)
    n.responses["getxyturtle"] = "[20.0, 5.5]"
    assert getxyturtle(n, car) == [20.0, 5.5]
    assert car.get_xy() == (20.0, 5.5)
    assert car.get_xcor() == 20.0 and car.get_ycor() == 5.5


def test_towards_and_distance_to_point(n):
    car = pyturtle(n)
    n.responses["towards_point_turtle"] = "45.0"
    assert car.towards_point(1.5, 2.5) == 45.0
    assert n.last_report == "towards_point_turtle [0 1.5 2.5]"


def test_value_error_becomes_netlogo_error(n):
    car = pyturtle(n)
    n.responses["get_heading_turtle"] = (
        "OF expected input to be a turtle agentset or turtle but got NOBODY instead.")
    with pytest.raises(NetLogoError, match="got NOBODY"):
        car.get_heading()


def test_missing_base_nls_gives_a_hint(n):
    n.responses["create-pyturtle-xyid"] = "Nothing named CREATE-PYTURTLE-XYID has been defined."
    with pytest.raises(NetLogoError, match="base.nls"):
        pyturtle(n)


def test_failed_action_warns(n):
    car = pyturtle(n)
    n.responses["fdfd"] = "Nothing named FDFD has been defined."
    with pytest.warns(NetLogoWarning, match="FDFD"):
        car.fd(1)


def test_successful_action_does_not_warn(n):
    car = pyturtle(n)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        car.fd(1)
        car.set_color(15)


def test_set_label_escapes_text(n):
    car = pyturtle(n)
    car.set_label('il a dit "ok"')
    assert n.last_report == r'set_label_turtle [0 "il a dit \"ok\""]'


def test_set_pen_color_uses_its_own_reporter(n):
    car = pyturtle(n)
    car.set_pen_color(55)
    assert n.last_report == "set_pen_color_turtle [0 55]"


def test_dieturtle_forgets_turtle_and_its_streets(n):
    a, b, c = pyturtle(n), pyturtle(n), pyturtle(n)
    s_ab = street(n, fromm=a, too=b)
    s_bc = street(n, fromm=b, too=c)
    a.dieturtle()
    assert n.last_report == "dieturtle [0]"
    assert a not in nlp.list_pyturtle
    assert nlp.list_street == [s_bc] and s_ab not in nlp.list_street


def test_is_alive(n):
    car = pyturtle(n)
    n.responses["is-turtle?"] = "false"
    assert car.is_alive() is False
    assert n.last_report == "is-turtle? turtle 0"


def test_repr(n):
    assert repr(pyturtle(n)) == "pyturtle(id=0)"


def test_from_id_wraps_an_existing_turtle(n):
    t = pyturtle.from_id(n, 12, fields={"kind": "sheep"})
    assert t.id == 12 and t.kind == "sheep" and t in nlp.list_pyturtle
    assert n.reports == []  # nothing created in NetLogo


def test_create_pyturtles_in_one_call(n):
    n.responses["create-pyturtles-xyid"] = "[0.0, 1.0, 2.0]"
    cars = create_pyturtles(n, [(1, 2), (3, 4), (5, 6)], shape="car", color=15,
                            names=["a", "b", "c"], fields={"path": []})
    assert n.reports == ['create-pyturtles-xyid [[[1 2] [3 4] [5 6]] "car" 4 15 ["a" "b" "c"] 0]']
    assert [car.id for car in cars] == [0, 1, 2]
    cars[0].path.append("x")
    assert cars[1].path == []  # each turtle has its own copy of the fields
    assert nlp.list_pyturtle == cars


def test_create_pyturtles_label_options(n):
    n.responses["create-pyturtles-xyid"] = "[0.0, 1.0]"
    create_pyturtles(n, [(0, 0), (1, 1)], names="car")
    assert '["car" "car"]' in n.last_report
    with pytest.raises(ValueError):
        create_pyturtles(n, [(0, 0), (1, 1)], names=["only one"])
    assert create_pyturtles(n, []) == []


def test_get_all_xy(n):
    n.responses["[ (list who xcor ycor) ] of pyturtles"] = "[[0.0, 20.0, 20.0], [1.0, 5.0, 7.5]]"
    assert get_all_xy(n) == {0: (20.0, 20.0), 1: (5.0, 7.5)}
    n.responses["[ (list who xcor ycor) ] of pyturtles"] = "[]"
    assert get_all_xy(n) == {}


def test_pep8_aliases():
    assert nlp.PyTurtle is pyturtle and nlp.Street is street and nlp.Turtle is nlp.turtle
