"""What 1.1 adds: reading without disturbing, agent tables, the view in memory,
BehaviorSpace experiments, experiment designs, sensitivity, calibration, Gymnasium."""

import os
import shutil
import time

import pytest
from conftest import FIRE_MODEL, WOLF_MODEL

from netlogopy import (
    NetLogo,
    NetLogoError,
    behaviorspace_experiments,
    calibrate,
    latin_hypercube,
    random_sample,
    run_behaviorspace,
    run_experiment,
    sensitivity,
)

FIRE = dict(steps=300, until="not any? turtles")


@pytest.fixture
def wolf():
    nl = NetLogo(WOLF_MODEL)
    yield nl
    nl.close()


def sheep_after(nl, read):
    nl.random_seed(1)
    nl.setup()
    for _ in range(30):
        read(nl)
        nl.go()
    return nl.report("count sheep")


# ─── reading without disturbing ──────────────────────────────────────────────

@pytest.mark.netlogo
def test_observe_does_not_change_the_run(wolf):
    alone = sheep_after(wolf, lambda nl: None)
    assert sheep_after(wolf, lambda nl: nl.observe("[energy] of sheep")) == alone
    assert sheep_after(wolf, lambda nl: nl.report("[energy] of sheep", observe=True)) == alone
    assert sheep_after(wolf, lambda nl: nl.agent_table("sheep", "energy")) == alone
    # report() draws from the generator of the model: the run goes another way
    assert sheep_after(wolf, lambda nl: nl.report("[energy] of sheep")) != alone


@pytest.mark.netlogo
def test_collect_gives_the_same_run_whatever_is_recorded(wolf):
    def run(reporters):
        wolf.random_seed(3)
        wolf.setup()
        return wolf.collect(reporters, steps=25, every=5)["sheep"]

    assert run({"sheep": "count sheep"}) == run({"sheep": "count sheep", "energy": "[energy] of sheep"})


@pytest.mark.netlogo
def test_run_experiment_gives_the_same_run_whatever_is_recorded():
    def run(reporters):
        return [row["sheep"] for row in run_experiment(WOLF_MODEL, None, reporters, steps=20, every=5, seed=2)]

    assert run({"sheep": "count sheep"}) == run({"sheep": "count sheep", "who": "[who] of one-of wolves"})


# ─── tables of agents ────────────────────────────────────────────────────────

@pytest.mark.netlogo
def test_agent_table(wolf):
    wolf.random_seed(1)
    wolf.setup()
    table = wolf.agent_table("sheep", ["xcor", "energy"])
    assert list(table) == ["who", "xcor", "energy"]
    assert table["who"] == sorted(table["who"]) and len(table["who"]) == wolf.count("sheep")
    assert table["energy"] == wolf.of("sheep", "energy")
    assert list(wolf.agent_table("patches with [pxcor = 0]", "pcolor")) == ["pxcor", "pycor", "pcolor"]
    two = wolf.turtles("wolves")[:2]
    assert wolf.agent_table(two, {"e": "energy * 2"})["who"] == [agent.who for agent in two]
    assert wolf.agent_table("turtles with [who < 0]", "xcor") == {"xcor": []}
    assert wolf.agent_table([], "xcor") == {"xcor": []}
    with pytest.raises(ValueError, match="who"):
        wolf.agent_table("sheep", "who")
    with pytest.raises(ValueError, match="same name"):
        wolf.agent_table("sheep", ["xcor", "xcor"])


@pytest.mark.netlogo
def test_agent_table_as_dataframe(wolf):
    pytest.importorskip("pandas")
    wolf.setup()
    frame = wolf.agent_table("wolves", ["xcor", "ycor"], as_dataframe=True)
    assert list(frame.columns) == ["who", "xcor", "ycor"] and len(frame) == wolf.count("wolves")


@pytest.mark.netlogo
def test_collect_agents(wolf):
    wolf.random_seed(1)
    wolf.setup()
    wolves = wolf.count("wolves")
    data = wolf.collect_agents("wolves", "energy", steps=4, every=2)
    assert list(data) == ["step", "who", "energy"]
    assert sorted(set(data["step"])) == [0, 2, 4]
    assert data["step"].count(0) == wolves
    assert len(data["step"]) == len(data["who"]) == len(data["energy"])
    assert wolf.collect_agents("turtles with [who < 0]", "xcor", steps=2) == {"step": [], "xcor": []}
    with pytest.raises(ValueError, match="step"):
        wolf.collect_agents("wolves", {"step": "energy"}, steps=1)


# ─── a background run held still ─────────────────────────────────────────────

@pytest.mark.netlogo
def test_hold_keeps_a_background_run_still(wolf):
    wolf.setup()
    wolf.start()
    try:
        with wolf.hold():
            ticks = wolf.ticks
            time.sleep(0.2)
            assert wolf.ticks == ticks
        time.sleep(0.2)
        assert wolf.ticks > ticks
    finally:
        wolf.stop()


# ─── the view in memory ──────────────────────────────────────────────────────

@pytest.mark.netlogo
def test_view_in_memory(wolf, tmp_path):
    numpy = pytest.importorskip("numpy")
    wolf.setup()
    png = wolf.view_png()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and wolf._repr_png_() == png
    image = wolf.view_array()
    assert image.ndim == 3 and image.shape[2] == 3 and image.dtype == numpy.uint8
    assert image.max() > 0
    pytest.importorskip("PIL")
    from PIL import Image
    path = wolf.record_gif(tmp_path / "run.gif", 6, every=2)
    with Image.open(path) as gif:
        assert gif.n_frames == 4 and gif.size == (image.shape[1], image.shape[0])
    assert wolf.ticks == 6


@pytest.mark.netlogo
def test_a_closed_session_has_no_image():
    nl = NetLogo()
    nl.close()
    assert nl._repr_png_() is None
    with pytest.raises(NetLogoError):
        nl.view_png()


# ─── BehaviorSpace experiments of the model ──────────────────────────────────

NLOGO_6 = """<experiments>
  <experiment name="density" repetitions="2" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <final>set density 1</final>
    <timeLimit steps="300"/>
    <exitCondition>not any? turtles</exitCondition>
    <metric>burned-trees</metric>
    <steppedValueSet variable="density" first="40" step="20" last="80"/>
  </experiment>
  <experiment name="steps" repetitions="1" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="3"/>
    <metric>ticks</metric>
    <enumeratedValueSet variable="density">
      <value value="50"/>
      <value value="60"/>
    </enumeratedValueSet>
  </experiment>
</experiments>"""


@pytest.fixture(scope="module")
def fire_with_experiments(tmp_path_factory):
    folder = tmp_path_factory.mktemp("behaviorspace")
    with open(FIRE_MODEL, encoding="utf-8") as handle:
        text = handle.read()
    sections = text.split("@#$#@#$#@")
    assert "<experiments>" not in text and len(sections) > 7
    sections[7] = "\n" + NLOGO_6 + "\n"
    shutil.copy(os.path.join(os.path.dirname(FIRE_MODEL), "base.nls"), folder)   # the model includes it
    path = folder / "Fire.nlogo"
    path.write_text("@#$#@#$#@".join(sections), encoding="utf-8")
    return str(path)


def test_behaviorspace_experiments_of_a_nlogo_file(fire_with_experiments):
    experiments = behaviorspace_experiments(fire_with_experiments)
    assert list(experiments) == ["density", "steps"]
    density = experiments["density"]
    assert density["parameters"] == [{"density": 40}, {"density": 60}, {"density": 80}]
    assert (density["repetitions"], density["steps"], density["until"]) == (2, 300, "not any? turtles")
    assert density["metrics"] == ["burned-trees"] and density["final"] == "set density 1"
    assert not density["every_step"] and experiments["steps"]["every_step"]
    assert behaviorspace_experiments(FIRE_MODEL) == {}


def test_behaviorspace_experiments_of_a_nlogox_file(tmp_path):
    path = tmp_path / "model.nlogox"
    path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<model version="NetLogo 7.0.0">
  <code><![CDATA[to setup end]]></code>
  <experiments>
    <experiment name="seven" repetitions="3" runMetricsEveryStep="false" timeLimit="200">
      <setup>setup</setup>
      <go>go</go>
      <postRun>show 1</postRun>
      <runMetricsCondition>ticks mod 2 = 0</runMetricsCondition>
      <metrics><metric>count sheep</metric></metrics>
      <constants>
        <enumeratedValueSet variable="kind"><value value="&quot;grass&quot;"></value></enumeratedValueSet>
        <enumeratedValueSet variable="on?"><value value="true"></value></enumeratedValueSet>
      </constants>
      <subExperiments>
        <subExperiment>
          <steppedValueSet variable="gain" first="0.5" step="0.5" last="1.5"></steppedValueSet>
        </subExperiment>
        <subExperiment>
          <enumeratedValueSet variable="kind"><value value="&quot;none&quot;"></value></enumeratedValueSet>
        </subExperiment>
      </subExperiments>
    </experiment>
  </experiments>
</model>""", encoding="utf-8")
    spec = behaviorspace_experiments(path)["seven"]
    assert spec["parameters"] == [
        {"kind": "grass", "on?": True, "gain": 0.5}, {"kind": "grass", "on?": True, "gain": 1.0},
        {"kind": "grass", "on?": True, "gain": 1.5}, {"kind": "none", "on?": True}]
    assert (spec["steps"], spec["repetitions"], spec["final"]) == (200, 3, "show 1")
    assert spec["record_when"] == "ticks mod 2 = 0" and spec["metrics"] == ["count sheep"]


@pytest.mark.netlogo
def test_run_behaviorspace(fire_with_experiments):
    rows = run_behaviorspace(fire_with_experiments, "density", seed=5, workers=2)
    assert [(row["run"], row["repetition"], row["density"]) for row in rows] == [
        (1, 1, 40), (2, 2, 40), (3, 1, 60), (4, 2, 60), (5, 1, 80), (6, 2, 80)]
    same = run_experiment(fire_with_experiments, {"density": [40, 60, 80]}, "burned-trees",
                          repetitions=2, seed=5, **FIRE)
    assert [row["burned-trees"] for row in rows] == [row["burned-trees"] for row in same]
    steps = run_behaviorspace(fire_with_experiments, "steps", repetitions=1)
    assert [row["step"] for row in steps] == [0, 1, 2, 3] * 2
    with pytest.raises(ValueError, match="several experiments"):
        run_behaviorspace(fire_with_experiments)
    with pytest.raises(ValueError, match="no experiment named"):
        run_behaviorspace(fire_with_experiments, "nothing")
    with pytest.raises(NetLogoError, match="no BehaviorSpace"):
        run_behaviorspace(FIRE_MODEL)


@pytest.mark.netlogo
def test_a_run_ends_when_the_model_stops():
    # The go procedure of the Fire model calls stop when the fire is out.
    row = run_experiment(FIRE_MODEL, {"density": 30}, "ticks", steps=10000, seed=1)[0]
    assert row["step"] < 10000 and row["step"] == row["ticks"] + 1


@pytest.mark.netlogo
def test_final_commands_run_after_each_run():
    with pytest.raises(NetLogoError, match="run 1"):
        run_experiment(FIRE_MODEL, None, "ticks", steps=1, final='error "the end"')


# ─── experiment designs ──────────────────────────────────────────────────────

def test_latin_hypercube_uses_every_slice_once():
    points = latin_hypercube({"n": (1, 10), "x": (0.0, 1.0), "kind": ["a", "b"]}, 10, seed=1)
    assert sorted(point["n"] for point in points) == list(range(1, 11))
    assert sorted(int(point["x"] * 10) for point in points) == list(range(10))
    assert sorted(point["kind"] for point in points) == ["a"] * 5 + ["b"] * 5
    assert points == latin_hypercube({"n": (1, 10), "x": (0.0, 1.0), "kind": ["a", "b"]}, 10, seed=1)
    assert points != latin_hypercube({"n": (1, 10), "x": (0.0, 1.0), "kind": ["a", "b"]}, 10, seed=2)


def test_random_sample_stays_in_the_ranges():
    points = random_sample({"n": (3, 5), "x": (2.0, 2.5)}, 200, seed=4)
    assert {point["n"] for point in points} == {3, 4, 5}
    assert all(isinstance(point["n"], int) and 2.0 <= point["x"] < 2.5 for point in points)


@pytest.mark.parametrize("bounds", [{}, {"a": (2, 1)}, {"a": []}, {"a": "text"}, {"a": 5}])
def test_wrong_bounds(bounds):
    with pytest.raises(ValueError):
        latin_hypercube(bounds, 3)


def test_wrong_number_of_samples():
    with pytest.raises(ValueError):
        random_sample({"a": (0, 1)}, 0)


@pytest.mark.netlogo
def test_a_design_runs_as_an_experiment():
    points = latin_hypercube({"density": (40, 80)}, 4, seed=1)
    rows = run_experiment(FIRE_MODEL, points, "burned-trees", seed=1, workers=2, **FIRE)
    assert [row["density"] for row in rows] == [point["density"] for point in points]


# ─── sensitivity ─────────────────────────────────────────────────────────────

@pytest.mark.netlogo
def test_sensitivity_sobol():
    pytest.importorskip("SALib")
    result = sensitivity(FIRE_MODEL, {"density": (40, 80)}, {"burned": "burned-trees"},
                         samples=8, seed=1, workers=2, **FIRE)
    assert set(result["burned"]) == {"S1", "S1_conf", "ST", "ST_conf"}
    assert result["burned"]["ST"]["density"] > 0.5         # the only parameter explains the result
    assert len(result["runs"]) == 8 * 3 and set(result["runs"][0]) == {"density", "burned"}
    assert all(isinstance(run["density"], int) and 40 <= run["density"] <= 80 for run in result["runs"])


@pytest.mark.netlogo
def test_sensitivity_morris():
    pytest.importorskip("SALib")
    result = sensitivity(FIRE_MODEL, {"density": (40.0, 80.0)}, "burned-trees", method="morris",
                         samples=4, seed=1, **FIRE)
    assert result["burned-trees"]["mu_star"]["density"] > 0


def test_sensitivity_checks_its_arguments():
    with pytest.raises(ValueError, match="method"):
        sensitivity(FIRE_MODEL, {"density": (40, 80)}, "burned-trees", method="other")
    with pytest.raises(ValueError, match="range"):
        sensitivity(FIRE_MODEL, {"density": [40, 80]}, "burned-trees")
    with pytest.raises(TypeError, match="every"):
        sensitivity(FIRE_MODEL, {"density": (40, 80)}, "burned-trees", every=1)


# ─── calibration ─────────────────────────────────────────────────────────────

@pytest.mark.netlogo
def test_calibrate_finds_the_density_that_burns_most():
    seen = []
    result = calibrate(FIRE_MODEL, {"density": (20, 90)}, "burned-trees", minimize=False,
                       population=5, generations=3, seed=2, workers=2,
                       progress=lambda generation, score: seen.append(generation), **FIRE)
    assert seen == [0, 1, 2, 3] and result["evaluations"] == 20
    assert result["history"] == sorted(result["history"], reverse=True)
    assert result["parameters"]["density"] >= 60 and result["score"] == -result["value"]
    again = calibrate(FIRE_MODEL, {"density": (20, 90)}, "burned-trees", minimize=False,
                      population=5, generations=3, seed=2, **FIRE)
    assert again["parameters"] == result["parameters"] and again["value"] == result["value"]


@pytest.mark.netlogo
def test_calibrate_towards_a_target():
    result = calibrate(FIRE_MODEL, {"density": (20, 90)}, "initial-trees", target=30000,
                       population=6, generations=4, seed=1, steps=0)
    assert result["score"] == abs(result["value"] - 30000)
    assert result["history"][-1] <= result["history"][0]


def test_calibrate_checks_its_arguments():
    with pytest.raises(ValueError, match="population"):
        calibrate(FIRE_MODEL, {"density": (20, 90)}, "burned-trees", population=3)
    with pytest.raises(ValueError):
        calibrate(FIRE_MODEL, {}, "burned-trees")


# ─── Gymnasium ───────────────────────────────────────────────────────────────

@pytest.mark.netlogo
def test_gymnasium_environment():
    pytest.importorskip("gymnasium")
    numpy = pytest.importorskip("numpy")
    from netlogopy.rl import NetLogoEnv
    env = NetLogoEnv(FIRE_MODEL, observation=["burned-trees", "count turtles"],
                     actions=["", "ask n-of 1 turtles [ die ]"], reward="0 - count turtles",
                     done="not any? turtles", max_steps=5, render_mode="rgb_array")
    try:
        assert env.action_space.n == 2 and env.observation_space.shape == (2,)
        first, info = env.reset(seed=1)
        assert first.dtype == numpy.float32 and info == {}
        for step in range(1, 6):
            observation, reward, terminated, truncated, info = env.step(0)
            assert reward == -observation[1] and info == {"steps": step}
        assert truncated and not terminated
        again, _ = env.reset(seed=1)
        assert again.tolist() == first.tolist()
        assert env.render().shape[2] == 3
        with pytest.warns(UserWarning):        # the bounds of the observations are not given
            from gymnasium.utils.env_checker import check_env
            check_env(env, skip_render_check=True)
    finally:
        env.close()
    assert env.nl.closed


@pytest.mark.netlogo
def test_gymnasium_environment_with_a_function_and_the_end_of_the_model():
    gymnasium = pytest.importorskip("gymnasium")
    from netlogopy.rl import NetLogoEnv
    env = NetLogoEnv(FIRE_MODEL, observation="count turtles",
                     actions=lambda nl, action: nl.set_global("density", float(action[0])),
                     action_space=gymnasium.spaces.Box(0.0, 99.0, (1,)),
                     reward=lambda nl: nl.report("burned-trees"))
    try:
        env.reset(seed=1)
        ended = False
        for _ in range(2000):
            _, _, ended, _, _ = env.step([10.0])
            if ended:
                break
        assert ended                               # the go procedure called stop
    finally:
        env.close()
    with pytest.raises(ValueError, match="action_space"):
        NetLogoEnv(FIRE_MODEL, observation="ticks", actions=lambda nl, action: None, reward="0")


def test_new_names_are_exported():
    import netlogopy
    for name in ("behaviorspace_experiments", "run_behaviorspace", "latin_hypercube", "random_sample",
                 "sensitivity", "calibrate"):
        assert name in netlogopy.__all__ and callable(getattr(netlogopy, name))
    assert os.path.exists(FIRE_MODEL)
