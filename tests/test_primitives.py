"""Primitives that got a Python method late: choosing agents, random numbers,
colors, timer, files, gradients, link queries."""

import pytest

from netlogopy import NetLogoCompileError, NetLogoRuntimeError

pytestmark = pytest.mark.netlogo


def test_choosing_agents(nl):
    turtles = nl.create_turtles(5, "pyturtles", xcor=0, ycor=0)
    for index, turtle in enumerate(turtles):
        turtle.size = index + 1
    assert nl.any("pyturtles") and not nl.any("pyturtles", "size > 5")
    assert nl.all("pyturtles", "size >= 1") and not nl.all("pyturtles", "size > 1")
    assert nl.one_of("pyturtles") in turtles and nl.one_of("pyturtles", "size > 5") is None
    assert nl.one_of(turtles[:2]) in turtles[:2]
    assert len(nl.n_of(3, "pyturtles")) == 3 and len(nl.n_of(9, "pyturtles")) == 5
    assert nl.max_one_of("pyturtles", "size") == turtles[4]
    assert nl.min_one_of(turtles, "size") == turtles[0]
    assert nl.max_n_of(2, "pyturtles", "size") == [turtles[4], turtles[3]]
    assert nl.min_n_of(2, "pyturtles", "size") == turtles[:2]
    turtles[3].size = 5
    assert nl.with_max("pyturtles", "size") == turtles[3:]
    assert nl.with_min("pyturtles", "size") == turtles[:1]
    assert nl.sort_on("pyturtles", "(- who)") == turtles[::-1]
    assert nl.turtles_on(nl.patch(0, 0)) == turtles and nl.turtles_on(nl.patch(1, 1)) == []


def test_random_numbers_are_reproducible(nl):
    def draw():
        nl.random_seed(42)
        return [nl.random(10), nl.random_float(1), nl.random_normal(0, 1), nl.random_poisson(3),
                nl.random_exponential(2), nl.random_gamma(2, 1), nl.random_xcor(), nl.random_ycor(),
                nl.random_pxcor(), nl.random_pycor()]
    first = draw()
    assert first == draw()
    assert 0 <= first[0] < 10 and 0 <= first[1] < 1
    assert nl.min_pxcor <= first[8] <= nl.max_pxcor and isinstance(first[8], int)


def test_colors_and_angles(nl):
    assert nl.scale_color(15, 5, 0, 10) == pytest.approx(15)
    assert nl.shade_of(15, 17) and not nl.shade_of(15, 25)
    assert nl.wrap_color(145) == 5
    assert nl.extract_rgb(15) == [215, 50, 41]
    assert nl.approximate_rgb(215, 50, 41) == pytest.approx(15, abs=0.2)
    assert len(nl.extract_hsb(15)) == 3 and len(nl.hsb(0, 100, 100)) == 3
    assert nl.approximate_hsb(0, 0, 0) == 0
    assert nl.subtract_headings(10, 350) == 20 and nl.subtract_headings(350, 10) == -20


def test_timer_and_clock(nl):
    nl.reset_timer()
    assert 0 <= nl.timer < 5
    assert isinstance(nl.date_and_time(), str) and nl.date_and_time()
    assert nl.mouse_down is False and nl.mouse_inside is False


def test_files(nl, tmp_path):
    path = tmp_path / "données.txt"
    assert not nl.file_exists(path)
    nl.file_open(path)
    nl.file_write(42)
    nl.file_write("two words")
    nl.file_print("")
    nl.file_print("a line")
    nl.file_type("ab")
    nl.file_type("cd")
    nl.file_flush()
    nl.file_close()
    assert nl.file_exists(path)
    nl.file_open(path)
    assert nl.file_read() == 42 and nl.file_read() == "two words"
    assert nl.file_read_line().strip() == "a line"   # file-read stops after the value
    assert nl.file_read_characters(3) == "abc" and not nl.file_at_end
    assert nl.file_read_characters(1) == "d" and nl.file_at_end
    nl.file_close_all()
    nl.file_delete(path)
    assert not nl.file_exists(path)
    with pytest.raises(NetLogoRuntimeError):
        nl.file_delete(path)


def test_plot_information(nl):
    nl.set_current_plot("My Plot")
    assert nl.plot_name == "My Plot"
    nl.set_plot_x_range(0, 50)
    nl.set_plot_y_range(-2, 2)
    assert nl.plot_x_range() == (0, 50) and nl.plot_y_range() == (-2, 2)
    nl.create_temporary_plot_pen("extra")
    assert nl.plot_pen_exists("extra") and not nl.plot_pen_exists("missing")
    try:
        nl.autoplot
    except NetLogoCompileError:
        return                          # autoplot? is a NetLogo 7 primitive
    nl.auto_plot_off()
    assert nl.autoplot is False
    nl.auto_plot_on()
    assert nl.autoplot is True


def test_gradients_and_patches_around(nl):
    nl.command("ask patches [ set pcolor pxcor + pycor ]")
    turtle = nl.create_turtles(1, "pyturtles", xcor=10, ycor=10, heading=0)[0]
    turtle.uphill("pcolor")
    assert turtle.xy == [11, 11]
    turtle.downhill("pcolor")
    assert turtle.xy == [10, 10]
    turtle.uphill4("pcolor")
    assert sum(turtle.xy) == 21
    turtle.downhill4("pcolor")
    assert sum(turtle.xy) == 20
    turtle.setxy(10, 10)
    other = nl.create_turtles(1, "pyturtles", xcor=12, ycor=10)[0]
    assert turtle.turtles_at(2, 0) == [other] and turtle.turtles_at(0, 2) == []
    assert turtle.patch_at_heading_and_distance(90, 2) == nl.patch(12, 10)
    assert nl.patch(10, 10).turtles_at(2, 0, "pyturtles") == [other]
    assert nl.patch(10, 10).patch_at_heading_and_distance(0, 3) == nl.patch(10, 13)


def test_link_queries(nl):
    a, b, c, d = nl.create_turtles(4, "pyturtles")
    links = a.create_links_to([b, c])
    assert len(links) == 2 and all(link.directed for link in links)
    assert a.is_out_link_neighbor(b) and b.is_in_link_neighbor(a) and not a.is_in_link_neighbor(b)
    assert a.is_link_neighbor(c) and not a.is_link_neighbor(d)
    assert a.out_link_to(b) == links[0] and b.in_link_from(a) == links[0]
    assert a.out_link_to(d) is None and a.in_link_from(b) is None
    assert len(d.create_links_from([b, c])) == 2 and d.is_in_link_neighbor(b)
    nl.clear_links()
    assert len(a.create_links_with([b, c])) == 2 and b.is_link_neighbor(a)
    nl.clear_links()                    # breeded and unbreeded links cannot coexist
    streets = a.create_links_to([b, c], "streets")                  # streets are directed
    assert len(streets) == 2 and a.is_out_link_neighbor(b, "streets")
    assert not b.is_out_link_neighbor(c, "streets") and a.out_link_to(c, "streets") == streets[1]


def test_default_shape_and_inspect_headless(nl):
    nl.set_default_shape("pyturtles", "car")
    assert nl.create_turtles(1, "pyturtles")[0].shape == "car"
    nl.set_default_shape("pyturtles", "default")
