"""Turtle, Patch and Link handles against a real NetLogo (headless)."""

import pytest

from netlogopy import Link, NetLogoRuntimeError, Patch, Turtle

pytestmark = pytest.mark.netlogo


def test_turtle_variables(nl):
    turtle = nl.create_turtles(1, "pyturtles", xcor=10, ycor=20)[0]
    turtle.heading = 90
    turtle.color = 15
    turtle.size = 2
    turtle.shape = "car"
    turtle.label = "car 1"
    turtle.label_color = 45
    turtle.pen_size = 3
    turtle.hidden = True
    assert (turtle.xcor, turtle.ycor, turtle.heading, turtle.color, turtle.size) == (10, 20, 90, 15, 2)
    assert (turtle.shape, turtle.label, turtle.label_color, turtle.pen_size) == ("car", "car 1", 45, 3)
    assert turtle.hidden is True and turtle.pen_mode == "up"
    assert turtle.dx == pytest.approx(1) and turtle.dy == pytest.approx(0, abs=1e-12)
    with pytest.raises(AttributeError):
        turtle.dx = 3
    assert turtle.breed == "pyturtles"
    turtle.set_breed("turtles")
    assert turtle.breed == "turtles"
    turtle["color"] = 25
    assert turtle["color"] == 25 and turtle.get("label-color") == 45
    turtle.set(color=35, label_color=55).set("size", 4)
    assert turtle.get_many(["color", "label-color", "size"]) == {"color": 35, "label-color": 55, "size": 4}
    assert turtle.xy == [10, 20]


def test_turtle_movement(nl):
    turtle = nl.create_turtles(1, xcor=30, ycor=30)[0]
    turtle.heading = 0
    turtle.forward(5).right(90).fd(2).left(90).back(1).rt(180).lt(90).jump(1)
    assert turtle.xy == pytest.approx([33, 34])
    turtle.setxy(10, 10)
    turtle.facexy(10, 20)
    assert turtle.heading == 0
    target = nl.create_turtles(1, xcor=20, ycor=10)[0]
    turtle.face(target)
    assert turtle.heading == 90 and turtle.towards(target) == 90
    assert turtle.towardsxy(10, 0) == 180
    assert turtle.distance(target) == 10 and turtle.distancexy(10, 13) == 3
    turtle.move_to(target)
    assert turtle.xy == [20, 10]
    turtle.move_to(nl.patch(5, 6))
    assert turtle.xy == [5, 6]
    turtle.home()
    turtle.heading = 0
    assert turtle.xy == [0, 0]
    assert turtle.can_move(1) and not turtle.can_move(-1)        # bottom edge, no wrapping


def test_turtle_pen_and_appearance(nl):
    turtle = nl.create_turtles(1, xcor=30, ycor=30)[0]
    turtle.pen_down()
    assert turtle.pen_mode == "down"
    turtle.pen_erase()
    assert turtle.pen_mode == "erase"
    turtle.pu()
    assert turtle.pen_mode == "up"
    turtle.stamp()
    turtle.stamp_erase()
    turtle.ht()
    assert turtle.hidden
    turtle.show_turtle()
    assert not turtle.hidden


def test_turtle_patches_and_neighbours(nl):
    turtle = nl.create_turtles(1, xcor=30, ycor=30)[0]
    turtle.heading = 90
    assert turtle.patch_here() == Patch(nl, 30, 30)
    assert turtle.patch_ahead(2) == Patch(nl, 32, 30)
    assert turtle.patch_at(-1, 1) == Patch(nl, 29, 31)
    assert turtle.patch_left_and_ahead(90, 1) == Patch(nl, 30, 31)
    assert turtle.patch_right_and_ahead(90, 1) == Patch(nl, 30, 29)
    assert turtle.patch_ahead(100) is None                        # outside the world
    assert len(turtle.neighbors()) == 8 and len(turtle.neighbors4()) == 4
    near = nl.create_turtles(2, xcor=31, ycor=30)
    far = nl.create_turtles(1, xcor=50, ycor=50)
    assert turtle.in_radius(2) == [turtle] + near
    assert turtle.in_radius(2, other=True) == near
    assert turtle.in_radius(2, "patches") == nl.patches(where="distancexy 30 30 <= 2")
    assert turtle.in_cone(5, 60, other=True) == near
    assert near[0].turtles_here() == near
    assert far[0] not in turtle.in_radius(10)


def test_hatch_die_and_dead_handles(nl):
    parent = nl.create_turtles(1, "pyturtles", color=15, xcor=10, ycor=10)[0]
    children = parent.hatch(3, color=55)
    assert len(children) == 3 and nl.of(children, "color") == [55] * 3
    assert all(child.breed == "pyturtles" for child in children)
    plain = parent.hatch(1, "turtles")
    assert plain[0].breed == "turtles" and parent.hatch(0) == []
    assert parent.alive
    parent.die()
    assert not parent.alive
    with pytest.raises(NetLogoRuntimeError):
        parent.xcor
    assert nl.report("one-of turtles with [who = 0]") is None


def test_ask_and_of(nl):
    turtle = nl.create_turtles(1, xcor=1, ycor=2)[0]
    turtle.ask("set xcor xcor + 1", "set ycor ycor * 3")
    assert turtle.of("xcor + ycor") == 8
    turtle.watch()


def test_patches(nl):
    patch = nl.patch(10, 10)
    patch.pcolor = 15
    patch.plabel = "here"
    patch.plabel_color = 45
    assert (patch.pcolor, patch.plabel, patch.plabel_color) == (15, "here", 45)
    assert patch["pxcor"] == 10 and patch.alive
    assert len(patch.neighbors()) == 8 and len(patch.neighbors4()) == 4
    assert len(nl.patch(0, 0).neighbors()) == 3                    # corner, no wrapping
    assert patch.patch_at(1, -1) == Patch(nl, 11, 9)
    assert patch.distancexy(13, 14) == 5
    assert patch.in_radius(1, other=True) == nl.patch(10, 10).neighbors4()
    sprouts = patch.sprout(2, "pyturtles", shape="car")
    assert patch.turtles_here() == sprouts and patch.turtles_here("pyturtles") == sprouts
    assert nl.of(sprouts, "shape") == ["car", "car"]
    assert patch.distance(sprouts[0]) == 0 and patch.sprout(0) == []


def test_breeded_links(nl):
    a, b, c = nl.create_turtles(3, "pyturtles", xcor=10, ycor=10)
    b.setxy(13, 14)
    road = nl.create_link(a, b, breed="streets", color=35, label="ab", thickness=0.3)
    assert road == Link(nl, a.who, b.who, breed="streets", directed=True)
    assert road.directed and road.ref == f"street {a.who} {b.who}"
    assert (road.color, road.label, road.thickness) == (35, "ab", 0.3)
    road.label_color = 15
    road.shape = "default"
    road.hidden = True
    assert road.label_color == 15 and road.hidden
    road.show_link()
    assert not road.hidden
    assert road.length == 5 and road.heading == pytest.approx(36.8699, abs=1e-3)
    assert road.end1 == a and road.end2 == b and road.both_ends() == [a, b]
    assert road.other_end(a) == b
    c.create_link_from(a, breed="streets")
    b.create_link_to(c, breed="streets")
    assert a.out_link_neighbors("streets") == [b, c]
    assert c.in_link_neighbors("streets") == [a, b]
    assert b.link_neighbors("streets") == [a, c]
    assert [link.end2 for link in a.my_out_links("streets")] == [b, c]
    assert len(b.my_links("streets")) == 2 and len(b.my_in_links("streets")) == 1
    assert a.link_with(b, "streets") == road and a.link_with(a, "streets") is None
    assert nl.link(a, b, "streets") == road and nl.links("streets")[0] == road
    a.heading = 0                       # turn before tying: tied turtles swivel
    road.tie()
    assert road.tie_mode == "fixed"
    a.fd(1)
    assert b.xy == pytest.approx([13, 15])
    road.untie()
    road.die()
    assert not road.alive and nl.count("streets") == 2


def test_unbreeded_links(nl):
    a, b, c = nl.create_turtles(3)
    link = a.create_link_with(b, color=15)
    assert not link.directed and link.breed == "links" and link.ref == f"link {a.who} {b.who}"
    assert b.link_with(a) == link and link.color == 15
    assert nl.create_link(c, b) == Link(nl, b.who, c.who)          # undirected: lowest who first
    assert b.link_neighbors() == [a, c] and len(b.my_links()) == 2
    assert nl.links() == [link, Link(nl, b.who, c.who)]
    with pytest.raises(NetLogoRuntimeError):
        nl.create_link(a, c, breed="streets")                     # breeded + unbreeded links


def test_handles_compare_by_identity(nl):
    turtle = nl.create_turtles(1)[0]
    assert turtle == nl.turtle(turtle.who) == nl.report(f"turtle {turtle.who}")
    assert len({turtle, nl.turtle(turtle.who)}) == 1
    assert repr(turtle) == f"Turtle({turtle.who})" and isinstance(turtle, Turtle)


def test_variables_without_netlogo_code(nl):
    """Simple reads and writes go through NetLogo's Java API with NetLogo's own checks."""
    nl.command("crt 1")
    turtle = nl.turtle(0)
    before = len(nl._cache)
    for step in range(50):                     # new values do not compile new code
        turtle.xcor = step / 10
        turtle.set(ycor=step / 5, label=f"t{step}")
    assert len(nl._cache) == before
    assert (turtle.xcor, turtle.ycor, turtle.label) == (4.9, 9.8, "t49")
    turtle.color = 200                         # wrapped, as with `set color 200`
    turtle.heading = 370
    assert (turtle.color, turtle.heading) == (60, 10)
    with pytest.raises(NetLogoRuntimeError, match="beyond the world's edge"):
        turtle.xcor = 1000
    with pytest.raises(NetLogoRuntimeError, match="not a currently defined shape"):
        turtle.shape = "no-such-shape"
    with pytest.raises(NetLogoRuntimeError):
        turtle.set("who", 5)
    patch = nl.patch(2, 3)
    patch.pcolor = 250
    assert patch.pcolor == 110
    with pytest.raises(NetLogoRuntimeError):
        nl.patch(1000, 1000).pcolor = 15
    breeded = nl.create_turtles(1, "pyturtles")[0]
    nl.command("ask turtle 0 [ die ]")
    with pytest.raises(NetLogoRuntimeError):
        turtle.xcor
    breeded.xcor = 3.25                         # a breed variable and a built-in one
    assert breeded.xcor == 3.25
