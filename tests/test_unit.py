"""Unit tests that need neither Java nor NetLogo."""

import os
import platform

import pytest

from netlogopy import Code, NetLogoNotFoundError, _java, colors, list2nllist, parameter_grid, to_netlogo
from netlogopy.agents import Link, Patch, Turtle, assignments, variable_name
from netlogopy.core import BUNDLED_MODEL, BUNDLED_MODEL_NLOGOX, bundled_model

# ─── to_netlogo ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, expected", [
    (None, "nobody"),
    (True, "true"),
    (False, "false"),
    (3, "3"),
    (-2, "-2"),
    (2.5, "2.5"),
    (1e-05, "1e-05"),
    ("car", '"car"'),
    ('say "hi"', '"say \\"hi\\""'),
    ("a\\b", '"a\\\\b"'),
    ("line1\nline2\ttab", '"line1\\nline2\\ttab"'),
    ("windows\r\nline", '"windows\\nline"'),
    ([], "[]"),
    ([1, "a", True, [2, 3]], '[1 "a" true [2 3]]'),
    ((1, 2), "[1 2]"),
    (range(3), "[0 1 2]"),
    ([1, None], "(list 1 nobody)"),
    (Code("random-xcor"), "random-xcor"),
    ([Code("ticks"), 1], "(list ticks 1)"),
])
def test_to_netlogo(value, expected):
    assert to_netlogo(value) == expected


def test_to_netlogo_agents():
    assert to_netlogo(Turtle(None, 3)) == "(turtle 3)"
    assert to_netlogo(Patch(None, -1, 2)) == "(patch -1 2)"
    assert to_netlogo(Link(None, 0, 1)) == "(link 0 1)"
    assert to_netlogo(Link(None, 0, 1, breed="streets", singular="street")) == "(street 0 1)"
    assert to_netlogo([Turtle(None, 1), 2]) == "(list (turtle 1) 2)"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {"a": 1}, object()])
def test_to_netlogo_rejects(value):
    with pytest.raises((TypeError, ValueError)):
        to_netlogo(value)


def test_to_netlogo_numpy():
    numpy = pytest.importorskip("numpy")
    assert to_netlogo(numpy.int64(4)) == "4"
    assert to_netlogo(numpy.float32(0.5)) == "0.5"
    assert to_netlogo(numpy.bool_(True)) == "true"
    assert to_netlogo(numpy.array([[1, 2], [3, 4]])) == "[[1 2] [3 4]]"


def test_variable_aliases_and_assignments():
    assert variable_name("label_color") == "label-color"
    assert variable_name("hidden") == "hidden?"
    assert variable_name("energy") == "energy"
    assert assignments({"color": 15, "label": "a", "pen_size": 2}) == \
        'set color 15 set label "a" set pen-size 2'


def test_agent_identity():
    a, b = Turtle(None, 1), Turtle(None, 1)
    assert a == b and hash(a) == hash(b) and a != Turtle(None, 2)
    assert Patch(None, 1, 2) == Patch(None, 1, 2)
    assert {Turtle(None, 1), Turtle(None, 1)} == {Turtle(None, 1)}
    assert repr(Link(None, 0, 1, directed=True)) == "Link(0 -> 1)"
    link = Link(None, 3, 5)
    assert link.other_end(3).who == 5 and link.other_end(Turtle(None, 5)).who == 3


def test_list2nllist_keeps_the_0x_format():
    assert list2nllist([1, 2.5, "a", True]) == '[ 1  2.5  "a"  true ]'


def test_parameter_grid():
    assert parameter_grid({"a": [1, 2], "b": True, "c": range(2)}) == [
        {"a": 1, "b": True, "c": 0}, {"a": 1, "b": True, "c": 1},
        {"a": 2, "b": True, "c": 0}, {"a": 2, "b": True, "c": 1}]


def test_parameter_grid_takes_any_collection():
    numpy = pytest.importorskip("numpy")
    grid = parameter_grid({"a": numpy.array([1, 2, 3]), "b": numpy.linspace(0, 1, 2), "c": "text", "d": 5})
    assert grid == [{"a": a, "b": b, "c": "text", "d": 5} for a in (1, 2, 3) for b in (0.0, 1.0)]
    assert all(type(row["a"]) is int and type(row["b"]) is float for row in grid)   # plain Python values
    assert parameter_grid({"a": numpy.float64(2.5), "b": numpy.int64(3)}) == [{"a": 2.5, "b": 3}]
    assert len(parameter_grid({"a": (letter for letter in "xy"), "b": {1}, "c": {"k": "v"}})) == 2


def test_colors():
    assert colors.RED == 15 and len(colors.BASE_COLORS) == 14
    assert colors.shade(colors.RED, -3) == 12
    assert colors.shade(colors.RED, 20) == 19.9
    assert colors.rgb(255, 0, 0) == [255, 0, 0]
    assert colors.rgba(0, 0, 0, 128) == [0, 0, 0, 128]
    with pytest.raises(ValueError):
        colors.rgb(256, 0, 0)


def test_bundled_models():
    assert os.path.isfile(BUNDLED_MODEL) and os.path.isfile(BUNDLED_MODEL_NLOGOX)
    assert bundled_model("6.2.2") == BUNDLED_MODEL
    assert bundled_model("7.0.0") == BUNDLED_MODEL_NLOGOX
    assert bundled_model(None) == BUNDLED_MODEL


def test_bundled_model_formats_share_their_code():
    with open(BUNDLED_MODEL, encoding="utf-8") as fh:
        code = fh.read().split("@#$#@#$#@")[0].strip()
    with open(BUNDLED_MODEL_NLOGOX, encoding="utf-8") as fh:
        xml = fh.read()
    assert code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") in xml


# ─── NetLogo / Java discovery ──────────────────────────────────────────────────

def _fake_netlogo(root, version, layout="app"):
    home = root / f"NetLogo {version}"
    jar_dir = home.joinpath(*layout.split("/"))
    jar_dir.mkdir(parents=True)
    (jar_dir / f"netlogo-{version}.jar").write_bytes(b"")
    (jar_dir / "scala-library.jar").write_bytes(b"")
    return home


def _fake_java(folder, version):
    relative = {"Windows": "bin/server/jvm.dll", "Darwin": "lib/server/libjvm.dylib"}.get(
        platform.system(), "lib/server/libjvm.so")
    library = folder.joinpath(*relative.split("/"))
    library.parent.mkdir(parents=True, exist_ok=True)
    library.write_bytes(b"")
    if version == 8:
        (folder / "lib").mkdir(exist_ok=True)
        (folder / "lib" / "rt.jar").write_bytes(b"")
    else:
        (folder / "release").write_text(f'JAVA_VERSION="{version}.0.2"\n')
    return str(library)


@pytest.mark.parametrize("layout", ["app", "lib/app", "Java", "NetLogo.app/Contents/Java"])
def test_find_jar_dir_layouts(tmp_path, layout):
    home = _fake_netlogo(tmp_path, "6.3.0", layout)
    assert os.path.samefile(_java.find_jar_dir(str(home)), str(home.joinpath(*layout.split("/"))))
    assert _java.netlogo_version(str(home)) == "6.3.0"


def test_find_netlogo_home(tmp_path, monkeypatch):
    old = _fake_netlogo(tmp_path, "6.2.2")
    new = _fake_netlogo(tmp_path, "7.0.0")
    monkeypatch.delenv("NETLOGO_HOME", raising=False)
    monkeypatch.setattr(_java, "_candidate_homes", lambda: [str(old), str(new)])
    assert _java.find_netlogo_home() == str(new)                 # newest wins
    assert _java.find_netlogo_home(str(old)) == str(old)        # explicit argument
    monkeypatch.setenv("NETLOGO_HOME", str(old))
    assert _java.find_netlogo_home() == str(old)                # environment variable
    with pytest.raises(NetLogoNotFoundError):
        _java.find_netlogo_home(str(tmp_path / "missing"))
    monkeypatch.delenv("NETLOGO_HOME")
    monkeypatch.setattr(_java, "_candidate_homes", lambda: [])
    with pytest.raises(NetLogoNotFoundError):
        _java.find_netlogo_home()


def test_java_version(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "release").write_text('JAVA_VERSION="1.8.0_302"\n')
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "release").write_text('IMPLEMENTOR="x"\nJAVA_VERSION="17.0.3"\n')
    _fake_java(tmp_path / "c", 8)
    (tmp_path / "d").mkdir()
    assert _java._java_version(str(tmp_path / "a")) == 8
    assert _java._java_version(str(tmp_path / "b")) == 17
    assert _java._java_version(str(tmp_path / "c")) == 8
    assert _java._java_version(str(tmp_path / "d")) is None


def _isolate_jvm_search(monkeypatch, tmp_path):
    monkeypatch.setattr(_java, "_candidate_homes", lambda: [])
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.setenv("CONDA_PREFIX", str(tmp_path / "no-conda"))
    monkeypatch.setattr(_java.sys, "prefix", str(tmp_path / "no-prefix"))
    monkeypatch.setattr(_java.sys, "base_prefix", str(tmp_path / "no-base"))


def test_find_jvm_skips_bundled_java_8(tmp_path, monkeypatch):
    _isolate_jvm_search(monkeypatch, tmp_path)
    home = _fake_netlogo(tmp_path, "6.2.2")
    _fake_java(home / "runtime", 8)
    java17 = _fake_java(tmp_path / "jdk17", 17)
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk17"))
    assert os.path.samefile(_java.find_jvm(str(home)), java17)


def test_find_jvm_prefers_bundled_runtime(tmp_path, monkeypatch):
    _isolate_jvm_search(monkeypatch, tmp_path)
    home = _fake_netlogo(tmp_path, "6.3.0")
    bundled = _fake_java(home / "runtime", 17)
    _fake_java(tmp_path / "jdk11", 11)
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk11"))
    assert os.path.samefile(_java.find_jvm(str(home)), bundled)


def test_find_jvm_netlogo7_needs_java17(tmp_path, monkeypatch):
    _isolate_jvm_search(monkeypatch, tmp_path)
    home = _fake_netlogo(tmp_path, "7.0.0")
    _fake_java(tmp_path / "jdk11", 11)
    with pytest.raises(NetLogoNotFoundError):
        _java.find_jvm(str(home), java_home=str(tmp_path / "jdk11"))


def test_find_jvm_explicit_java_home(tmp_path, monkeypatch):
    _isolate_jvm_search(monkeypatch, tmp_path)
    home = _fake_netlogo(tmp_path, "6.2.2")
    java11 = _fake_java(tmp_path / "jdk11", 11)
    assert os.path.samefile(_java.find_jvm(str(home), java_home=str(tmp_path / "jdk11")), java11)
    assert os.path.samefile(_java.find_jvm(str(home), java_home=java11), java11)  # library path
    _fake_java(tmp_path / "jre8", 8)
    with pytest.raises(NetLogoNotFoundError):
        _java.find_jvm(str(home), java_home=str(tmp_path / "jre8"))


def test_find_netlogo_home_gives_the_installation_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("NETLOGO_HOME", raising=False)
    home = _fake_netlogo(tmp_path / "netlogo", "6.4.0", "lib/app")
    assert _java.find_netlogo_home(str(home)) == str(home)
    assert _java.find_netlogo_home(str(tmp_path / "netlogo")) == str(home)      # a folder above it
    assert _java.find_netlogo_home(str(home / "lib" / "app")) == str(home)      # a folder inside it
    mac = _fake_netlogo(tmp_path / "mac", "6.3.0", "NetLogo.app/Contents/Java")
    assert _java.find_netlogo_home(str(mac)) == str(mac)
    windows = _fake_netlogo(tmp_path / "windows", "7.0.0", "app")
    assert _java._install_root(str(windows / "app")) == str(windows)


def test_candidate_homes_look_inside_a_folder_of_installations(tmp_path, monkeypatch):
    _fake_netlogo(tmp_path / "netlogo", "6.4.0", "lib/app")       # the layout of the CI recipe
    _fake_netlogo(tmp_path / "netlogo", "7.0.0", "lib/app")
    monkeypatch.setattr(_java.platform, "system", lambda: "Linux")
    monkeypatch.setattr(_java.os.path, "expanduser", lambda path: path.replace("~", str(tmp_path)))
    here = [home for home in _java._candidate_homes() if home.startswith(str(tmp_path))]
    assert sorted(os.path.basename(home) for home in here) == ["NetLogo 6.4.0", "NetLogo 7.0.0"]


def test_a_release_is_preferred_to_its_pre_releases(tmp_path, monkeypatch):
    monkeypatch.delenv("NETLOGO_HOME", raising=False)
    older = _fake_netlogo(tmp_path, "6.4.0")
    release = _fake_netlogo(tmp_path, "7.0.0")
    beta = tmp_path / "NetLogo 7.0.0-beta1"
    (beta / "app").mkdir(parents=True)
    (beta / "app" / "netlogo-7.0.0-beta1.jar").write_bytes(b"")
    assert _java.netlogo_version(str(beta)) == "7.0.0"
    assert _java._is_release(str(release)) and not _java._is_release(str(beta))
    for order in ([older, beta, release], [release, beta, older]):
        monkeypatch.setattr(_java, "_candidate_homes", lambda order=order: [str(home) for home in order])
        assert _java.find_netlogo_home() == str(release)
