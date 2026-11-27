"""Defects fixed in 1.0.1, each pinned by a test against a real NetLogo (headless)."""

import gc
import threading
import time

import pytest
from conftest import FIRE_MODEL, WOLF_MODEL

from netlogopy import NetLogo, NetLogoError, NetLogoRuntimeError, Patch, Turtle, _java

pytestmark = pytest.mark.netlogo

ENDLESS = "while [ true ] [ tick ]"


def java_threads():
    import jpype
    return int(jpype.JClass("java.lang.Thread").getAllStackTraces().size())


# ─── values that NetLogo cannot hold ─────────────────────────────────────────────

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("variable", ["xcor", "heading", "size", "color", "label"])
def test_non_finite_numbers_are_refused(nl, variable, value):
    turtle = nl.create_turtles(1, xcor=30, ycor=30, size=2)[0]
    turtle.pen_down()                              # with the pen down NetLogo used to hang
    before = turtle.get(variable)
    with pytest.raises(ValueError, match="finite"):
        turtle.set(variable, value)
    with pytest.raises(ValueError, match="finite"):
        turtle[variable] = value
    assert turtle.get(variable) == before
    with pytest.raises(ValueError, match="finite"):
        nl.patch(1, 1).pcolor = value


def test_numpy_scalars_take_the_direct_path(nl):
    numpy = pytest.importorskip("numpy")
    turtle = nl.create_turtles(1)[0]
    compiled = len(nl._cache)
    turtle.color = numpy.int64(15)
    turtle.size = numpy.float32(2.5)
    turtle.hidden = numpy.bool_(True)
    turtle.xcor = numpy.float64(12.25)
    assert len(nl._cache) == compiled              # nothing was compiled for these values
    assert (turtle.color, turtle.size, turtle.hidden, turtle.xcor) == (15.0, 2.5, True, 12.25)
    with pytest.raises(ValueError, match="finite"):
        turtle.size = numpy.float64("nan")


# ─── background runs ─────────────────────────────────────────────────────────────

def test_halt_ends_a_step_that_never_ends(nl):
    nl.command("reset-ticks")
    nl.start(ENDLESS)
    time.sleep(0.3)
    began = time.perf_counter()
    assert nl.halt() == 0                          # the interrupted step is not a step made
    assert time.perf_counter() - began < 5 and not nl.running
    assert nl.report("1 + 1") == 2.0               # the session still works
    assert nl.ticks > 0
    assert nl.halt() == 0                          # nothing runs: nothing happens


def test_stop_with_a_timeout_interrupts_an_endless_step(nl):
    nl.command("reset-ticks")
    nl.start(ENDLESS)
    time.sleep(0.3)
    assert nl.stop(timeout=0.5) == 0
    assert not nl.running and nl.report("count patches") == 3721


def test_halt_from_another_thread_interrupts_a_command(nl):
    nl.command("reset-ticks")
    timer = threading.Timer(0.5, nl.halt)
    timer.start()
    began = time.perf_counter()
    nl.command(ENDLESS)                            # returns once halted
    timer.join()
    assert time.perf_counter() - began < 5
    assert nl.report("1 + 1") == 2.0


def test_close_does_not_wait_for_an_endless_step():
    session = NetLogo(FIRE_MODEL)
    session.setup()
    session.start(ENDLESS)
    time.sleep(0.3)
    began = time.perf_counter()
    session.close()
    assert time.perf_counter() - began < 10 and session.closed


def test_reading_agents_during_a_background_run():
    with NetLogo(WOLF_MODEL) as wolf:
        wolf.setup()
        wolf.start("go")
        try:
            for _ in range(40):
                assert None not in wolf.turtles()
                assert None not in wolf.report("turtles")
                assert None not in wolf.report("[self] of turtles")
        finally:
            wolf.stop()


def test_creations_during_a_background_run_return_their_own_turtles(nl):
    nl.start("crt 1 [ set color 99 ]")             # the model creates turtles at the same time
    try:
        for _ in range(40):
            mine = nl.create_turtles(3, color=15)
            assert nl.of(mine, "color") == [15.0] * 3
            assert nl.of(mine[0].hatch(2, size=7), "size") == [7.0, 7.0]
            assert nl.of(nl.patch(5, 5).sprout(2, size=3), "size") == [3.0, 3.0]
    finally:
        nl.stop()


def test_background_runs_do_not_leave_java_threads(nl):
    nl.command("reset-ticks")
    nl.start("tick", max_steps=2)
    nl.wait(10)
    nl.stop()                                      # the first run settles the count
    before = java_threads()
    for _ in range(10):
        nl.start("tick", max_steps=2)
        assert nl.wait(10)
        assert nl.stop() == 2
    assert java_threads() <= before + 1


def test_the_error_of_an_old_run_does_not_keep_the_next_model_closed():
    with NetLogo(FIRE_MODEL) as session:
        session.setup()
        session.start("ask turtle 999 [ fd 1 ]")
        time.sleep(0.5)
        with pytest.warns(RuntimeWarning, match="background run"):
            session.open_model(WOLF_MODEL)
        assert session.model_path == WOLF_MODEL
        session.setup()
        session.start("ask turtle 99999 [ fd 1 ]")
        time.sleep(0.5)
        with pytest.warns(RuntimeWarning, match="never reported"):
            session.start("go", max_steps=1)
        assert session.wait(10) and session.stop() == 1


# ─── sessions ────────────────────────────────────────────────────────────────────

def test_a_session_dropped_without_close_frees_its_workspace():
    before = len(_java._open_handles)
    session = NetLogo(FIRE_MODEL)
    assert len(_java._open_handles) == before + 1
    del session
    gc.collect()
    assert len(_java._open_handles) == before


def test_a_closed_session_refuses_every_call():
    session = NetLogo(FIRE_MODEL)
    session.close()
    for call in (session.global_names, session.breeds, lambda: session.wrap_x, lambda: session.wrap_y,
                 lambda: session.command("  "), lambda: session.report([]), lambda: session.patch(0, 0),
                 session.halt):
        with pytest.raises(NetLogoError, match="closed"):
            call()


def test_a_wrong_model_path_is_seen_before_the_window_opens(tmp_path, monkeypatch):
    def launch_gui():
        raise AssertionError("the window must not be opened for a model that does not exist")

    monkeypatch.delenv("NETLOGOPY_HEADLESS", raising=False)
    monkeypatch.setattr(_java, "launch_gui", launch_gui)
    with pytest.raises(FileNotFoundError):
        NetLogo(tmp_path / "typo.nlogo", gui=True)


def test_compiled_code_is_dropped_when_the_window_recompiles_the_model(nl, monkeypatch):
    monkeypatch.setattr(nl, "gui", True)           # the window wrapper works on a headless workspace
    assert nl.report("count patches") == 3721
    assert (True, "count patches") in nl._cache
    assert nl.report("max-pxcor") == 60.0 and (True, "count patches") in nl._cache
    monkeypatch.setattr(nl, "_procedures_identity", lambda: -1)     # as after a recompilation
    assert nl.report("max-pxcor") == 60.0
    assert (True, "count patches") not in nl._cache


# ─── errors ──────────────────────────────────────────────────────────────────────

def test_runtime_errors_say_where_they_happened(nl):
    nl.create_turtles(3)
    with pytest.raises(NetLogoRuntimeError) as info:
        nl.command("ask turtles [ set size 1 / (who - who) ]")
    assert info.value.message == "Division by zero."
    assert "error while turtle" in info.value.context
    assert "error while turtle" in str(info.value) and "__EVALUATOR" not in str(info.value)
    with pytest.raises(NetLogoRuntimeError) as info:
        nl.report("[1 / (who - who)] of turtle 1")
    assert "turtle 1" in info.value.context
    with pytest.raises(NetLogoRuntimeError) as info:
        nl.command("ask turtle 999 [ fd 1 ]")
    assert info.value.source == "ask turtle 999 [ fd 1 ]" and "NOBODY" in info.value.message


def test_globals_raise_keyerror_for_an_unknown_name(nl):
    with pytest.raises(KeyError):
        nl.globals["nope"]
    with pytest.raises(KeyError):
        nl.globals["nope"] = 3
    nl.globals["speed"] = 2
    assert nl.globals["speed"] == 2.0


# ─── agents ──────────────────────────────────────────────────────────────────────

def test_a_creation_that_fails_leaves_no_agent(nl):
    with pytest.raises(NetLogoRuntimeError, match="edge"):
        nl.create_turtles(3, xcor=1000)
    assert nl.count() == 0
    parent, other = nl.create_turtles(2)
    with pytest.raises(NetLogoRuntimeError, match="edge"):
        parent.hatch(2, xcor=1000)
    with pytest.raises(NetLogoRuntimeError, match="edge"):
        nl.patch(3, 3).sprout(2, xcor=1000)
    assert nl.count() == 2
    with pytest.raises(NetLogoRuntimeError):
        nl.create_link(parent, other, breed="streets", shape="no-such-shape")
    assert nl.count("links") == 0
    street = nl.create_link(parent, other, breed="streets", thickness=2)
    # NetLogo creates nothing for a link that exists and does not run the assignments again.
    assert nl.create_link(parent, other, breed="streets", shape="no-such-shape") == street
    assert nl.links() == [street] and street.thickness == 2


def test_create_returns_only_the_turtles_still_alive(nl):
    assert nl._create("create-turtles 6 [ if who mod 2 = 0 [ die ] ]") == [Turtle(nl, 1), Turtle(nl, 3), Turtle(nl, 5)]
    assert nl.create_turtles(2) == [Turtle(nl, 6), Turtle(nl, 7)]


def test_patch_outside_the_world(nl):
    assert nl.patch(61, 0) is None and nl.patch(100.4, 3) is None and nl.patch(-1, -1) is None
    assert nl.patch(60.4, 0) == Patch(nl, 60, 0) and nl.patch(2.5, 3.4) == Patch(nl, 3, 3)
    assert nl.patch(7, 9) == Patch(nl, 7, 9) == nl.report("patch 7 9")
    nl.set_topology(True, True)
    assert nl.patch(61, 0) == nl.patch(0, 0) == Patch(nl, 0, 0)
    assert nl.patch(61, -1) == nl.report("patch 61 -1") == Patch(nl, 0, 60)
    with pytest.raises(ValueError, match="finite"):
        nl.patch(float("nan"), 0)


def test_an_empty_list_of_agents_is_not_an_error(nl):
    nl.ask([], "set thickness 2")                  # link-only code: an empty list has no kind
    nl.ask(nl.patches("pxcor > 1000"), "sprout 1")
    assert nl.count() == 0
    assert nl.of([], "link-length") == []
    assert nl.any([]) is False and nl.all([], "thickness > 1") is True
    assert nl.one_of([]) is None and nl.max_one_of([], "link-length") is None
    assert nl.min_one_of([], "link-length") is None and nl.n_of(3, []) == []
    assert nl.max_n_of(2, [], "link-length") == [] == nl.min_n_of(2, [], "link-length")
    assert nl.with_max([], "link-length") == [] == nl.with_min([], "link-length")
    assert nl.sort_on([], "link-length") == [] == nl.turtles_on([])
    turtles = nl.create_turtles(3)
    nl.layout_spring(turtles, [])
    nl.layout_radial(turtles, [], turtles[0])
    nl.layout_circle([], 5)


def test_a_comment_does_not_swallow_the_closing_bracket(nl):
    nl.command("reset-ticks")
    nl.go(2, "tick ; one step")
    assert nl.ticks == 2
    assert nl.report(["count turtles ; how many", "ticks"]) == [0.0, 2.0]
    nl.create_turtles(3)
    assert len(nl.turtles(where="who > 0 ; not the first")) == 2
    assert nl.count("turtles ; all of them") == 3
    assert nl.of("turtles", "who ; its number") == [0.0, 1.0, 2.0]
    assert nl.all("turtles", "who >= 0 ; always") is True
    assert nl.max_one_of("turtles", "who ; its number") == Turtle(nl, 2)
    assert nl.any("turtles", "who = 2 ; the last") is True


def test_of_follows_the_order_of_a_python_list(nl):
    nl.command("crt 5 [ set size who * 2 ]")
    top = nl.max_n_of(3, "turtles", "size")
    assert top == [Turtle(nl, 4), Turtle(nl, 3), Turtle(nl, 2)]
    assert nl.of(top, "size") == [8.0, 6.0, 4.0]
    assert nl.of([top[0], top[0]], "who") == [4.0, 4.0]          # duplicates are kept
    top[1].die()
    assert nl.of(top, "size") == [8.0, None, 4.0]                # a dead agent keeps its place
    assert nl.of([nl.patch(3, 2), nl.patch(1, 1)], "pxcor") == [3.0, 1.0]
    assert nl.of(nl.turtle(0), "who") == [0.0]
    assert nl.of("turtles", "who") == [0.0, 1.0, 2.0, 4.0]       # NetLogo code: sorted as before
    street = nl.create_link(0, 1, breed="streets")
    assert nl.of([street, nl.turtle(2)], "color") == [street.color, nl.turtle(2).color]
    nl.ask(top, "set size 1")                                    # a dead turtle in the list is skipped
    assert nl.of("turtles", "size") == [0.0, 2.0, 1.0, 1.0]


def test_long_lists_of_agents(nl):
    turtles = nl.create_turtles(3000)
    nl.ask(turtles, "set size 3")
    assert nl.count("turtles", "size = 3") == 3000
    assert nl.of(turtles[::-1], "who")[:2] == [2999.0, 2998.0]
    assert nl.any(turtles, "size = 3") and nl.all(turtles, "size = 3")
    patches = nl.patches()
    nl.ask(patches, "set pcolor 5")
    assert nl.count("patches", "pcolor = 5") == len(patches) == 3721
    assert nl.of(patches[:3], "pcolor") == [5.0, 5.0, 5.0]


def test_agents_of_another_session_are_refused(nl):
    with NetLogo() as other:
        theirs = other.create_turtles(3)[2]
        mine = nl.create_turtles(3)
        for call in (lambda: nl.ask([theirs], "die"), lambda: nl.of(theirs, "who"), lambda: nl.any(theirs),
                     lambda: nl.of(mine + [theirs], "who"), lambda: nl.create_link(mine[0], theirs),
                     lambda: nl.link(mine[0], theirs), lambda: nl.watch(theirs),
                     lambda: nl.layout_radial(mine, "links", theirs), lambda: nl.layout_circle([theirs])):
            with pytest.raises(ValueError, match="another NetLogo session"):
                call()
        assert other.count() == 3 and nl.count() == 3


def test_n_of_with_a_random_filter(nl):
    nl.create_turtles(40)
    for _ in range(100):                           # the filter used to be evaluated twice
        assert len(nl.n_of(18, "turtles", "random 2 = 0")) <= 18
    assert len(nl.n_of(100, "turtles")) == 40 and len(nl.n_of(5, nl.turtles())) == 5


def test_link_without_a_breed_finds_links_of_any_breed(nl):
    a, b, c = nl.create_turtles(3)
    street = nl.create_link(a, b, breed="streets")              # a directed link breed
    assert nl.link(a, b) == street and nl.link(b, a) is None
    assert nl.link(a, c) is None and nl.link(a, 99) is None and nl.link(99, a) is None
    assert nl.link(a, b, "streets") == street
    with NetLogo(FIRE_MODEL) as fire:
        fire.command("clear-all", "crt 3")
        plain = fire.create_link(0, 1)                          # undirected, no breed
        assert fire.link(0, 1) == plain == fire.link(1, 0)
        assert fire.link(0, 1, "links") == plain and fire.link(0, 2) is None


def test_layout_tutte_moves_the_turtles_it_is_given(nl):
    hub, *rim = nl.create_turtles(7, xcor=30, ycor=30)
    for turtle in rim:
        nl.create_link(hub, turtle, breed="streets")
    for call in (lambda: nl.layout_tutte([hub], "streets", 10),
                 lambda: nl.layout_tutte(turtles=[hub], links="streets", radius=10),
                 lambda: nl.layout_tutte(fixed_turtles=[hub], links="streets", radius=10)):
        nl.ask("turtles", "setxy 30 30")
        call()
        assert all(abs(hub.distance(turtle) - 10) < 1e-6 for turtle in rim)
    with pytest.raises(TypeError):
        nl.layout_tutte(links="streets", radius=10)


def test_layout_circle_keeps_the_order_of_a_list(nl):
    def places(agents):
        return nl.of(agents, "xcor") + nl.of(agents, "ycor")

    turtles = nl.create_turtles(4)
    nl.layout_circle(turtles, 10)
    forward = places(turtles)
    assert len(set(zip(forward[:4], forward[4:]))) == 4          # four different places
    nl.layout_circle(turtles[::-1], 10)
    assert places(turtles[::-1]) == pytest.approx(forward)
    nl.layout_circle("sort-on [ (- who) ] turtles", 10)         # NetLogo code that reports a list
    assert places(turtles[::-1]) == pytest.approx(forward)
    nl.layout_circle("turtles", 10)                             # an agentset: by who number
    assert places(turtles) == pytest.approx(forward)


def test_set_topology_tells_the_view(nl, tmp_path):
    image = pytest.importorskip("PIL.Image")
    nl.set_topology(True, True)
    nl.command("crt 1 [ setxy 2 30 ] crt 1 [ setxy 58 30 ]",
               "ask turtle 0 [ create-street-to turtle 1 [ set color yellow set thickness 0.5 ] ]",
               "ask turtles [ hide-turtle ]")
    picture = image.open(nl.export_view(tmp_path / "view.png")).convert("RGB")
    width, height = picture.size
    yellow = [x for x in range(width) for y in range(height)
              if picture.getpixel((x, y))[0] > 200 and picture.getpixel((x, y))[1] > 200
              and picture.getpixel((x, y))[2] < 100]
    assert any(x < width * 0.05 for x in yellow) and any(x > width * 0.95 for x in yellow)


# ─── data ────────────────────────────────────────────────────────────────────────

def test_collect_stops_when_until_becomes_true(nl):
    nl.command("reset-ticks")
    data = nl.collect({"t": "ticks"}, steps=100, command="tick", every=10, until="ticks >= 25")
    assert data["step"] == [0, 10, 20, 25] and data["t"] == [0.0, 10.0, 20.0, 25.0]
    assert nl.collect("ticks", steps=5, command="tick", until="true") == {"step": [0], "ticks": [25.0]}
    assert nl.collect("ticks", steps=3, command="tick", include_initial=False)["step"] == [1, 2, 3]
    assert nl.collect("ticks", steps=25, command="tick", every=10)["step"] == [0, 10, 20, 25]
    with pytest.raises(ValueError, match="step"):
        nl.collect({"step": "ticks"}, 3, command="tick")
    with pytest.raises(ValueError, match="same name"):
        nl.collect(["ticks", "ticks"], 2, command="tick")


def test_schedule_reporters_rows(nl):
    nl.command("reset-ticks")
    assert nl.schedule_reporters(["ticks"], 0, 1, 3, "tick") == [[1.0], [2.0], [3.0]]
    nl.command("reset-ticks")                      # a go that stops: no duplicated last row
    assert nl.schedule_reporters(["ticks"], 0, 1, 10, "if ticks < 4 [ tick ]") == [[1.0], [2.0], [3.0], [4.0]]
    with pytest.raises(ValueError, match="interval_ticks"):
        nl.schedule_reporters(["ticks"], 0, 0, 3)


def test_set_current_directory_is_used_by_the_file_methods(tmp_path):
    with NetLogo(FIRE_MODEL) as session:
        session.set_current_directory(tmp_path)
        session.file_open("by_method.txt")
        session.file_print("x")
        session.file_close()
        assert (tmp_path / "by_method.txt").read_text().strip() == "x"
        session.command('file-open "by_command.txt"', "file-print 1", "file-close")
        assert session.file_exists("by_command.txt") and session.file_exists(tmp_path / "by_command.txt")
        session.file_delete("by_method.txt")
        assert not (tmp_path / "by_method.txt").exists()


def test_set_patch_grid_with_agents(nl):
    turtle = nl.create_turtles(1)[0]
    nl.command("ask patches [ set plabel one-of turtles ]")
    grid = nl.patch_grid("plabel")
    assert grid[0][0] == turtle
    nl.command("ask patches [ set plabel 0 ]")
    nl.set_patch_grid("plabel", grid)              # too large for one command: set by pieces
    assert nl.patch_grid("plabel") == grid
    with pytest.raises(ValueError, match="rows"):
        nl.set_patch_grid("pcolor", [1.0, 2.0])


def test_diffuse_refuses_a_wrong_number_of_neighbours(nl):
    with pytest.raises(ValueError, match="4 or 8"):
        nl.diffuse("pcolor", 0.5, neighbors=5)
    nl.diffuse("pcolor", 0.5, neighbors=4)
