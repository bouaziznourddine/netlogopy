"""Finding NetLogo and starting GUI or headless instances (the Java bridge is faked)."""
import pytest

import netlogopy.netlogopy as nlp
from conftest import FakeNetLogo
from netlogopy.netlogopy import (HeadlessNetLogo, NetLogoApp, NetLogoNotFoundError,
                                 find_netlogo_home, is_netlogo_home, netlogo_session,
                                 pyturtle, run_netlogo, run_netlogo_model)


def make_home(root, name="NetLogo 6.2.2", jar_dir="app"):
    home = root / name
    (home / jar_dir).mkdir(parents=True)
    (home / jar_dir / "netlogo-{}.jar".format(name.split()[-1])).write_bytes(b"")
    return home


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(nlp.platform, "system", lambda: "Linux")
    monkeypatch.delenv("NETLOGO_HOME", raising=False)


# ── Finding NetLogo ───────────────────────────────────────────────────────────

def test_is_netlogo_home(tmp_path, linux):
    assert is_netlogo_home(str(make_home(tmp_path)))
    assert not is_netlogo_home(str(tmp_path))
    assert not is_netlogo_home(None)


def test_macos_uses_the_java_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(nlp.platform, "system", lambda: "Darwin")
    assert is_netlogo_home(str(make_home(tmp_path, jar_dir="Java")))


def test_netlogo_home_environment_variable(tmp_path, linux, monkeypatch):
    home = make_home(tmp_path)
    monkeypatch.setenv("NETLOGO_HOME", str(home))
    assert find_netlogo_home() == str(home)


def test_prefers_netlogo_6_then_newest(tmp_path, linux, monkeypatch):
    homes = [make_home(tmp_path, name) for name in ("NetLogo 6.2.2", "NetLogo 6.4.0", "NetLogo 7.0.0")]
    monkeypatch.setattr(nlp, "_candidate_homes", lambda: [str(h) for h in homes])
    assert find_netlogo_home() == str(homes[1])


def test_nothing_found(linux, monkeypatch):
    monkeypatch.setattr(nlp, "_candidate_homes", lambda: [])
    assert find_netlogo_home() is None
    with pytest.raises(NetLogoNotFoundError, match="NETLOGO_HOME"):
        nlp._resolve_netlogo_home(None)


def test_explicit_wrong_folder(tmp_path, linux):
    with pytest.raises(NetLogoNotFoundError, match="netlogo-<version>.jar"):
        nlp._resolve_netlogo_home(str(tmp_path / "NetLogo 9"))


# ── Java ──────────────────────────────────────────────────────────────────────

def test_jvm_bundled_with_netlogo_is_preferred(tmp_path, linux, monkeypatch):
    home = make_home(tmp_path)
    jvm = home / "runtime" / "lib" / "server" / "libjvm.so"
    jvm.parent.mkdir(parents=True)
    jvm.write_bytes(b"")
    monkeypatch.delenv("NETLOGOPY_JVM", raising=False)
    assert nlp._bridge.jvm_path(str(home)) == str(jvm)
    monkeypatch.setenv("NETLOGOPY_JVM", "/my/jvm.so")
    assert nlp._bridge.jvm_path(str(home)) == "/my/jvm.so"


# ── Starting NetLogo with a fake bridge ───────────────────────────────────────

class FakeHeadless(FakeNetLogo):
    def __init__(self):
        super().__init__()
        self.disposed = False

    def dispose(self):
        self.disposed = True


class FakeGUI(FakeNetLogo):
    pass


@pytest.fixture
def fake_bridge(tmp_path, linux, monkeypatch):
    started = []
    monkeypatch.setattr(nlp._bridge, "start_jvm", started.append)
    monkeypatch.setattr(nlp._bridge, "HeadlessWorkspace", FakeHeadless)
    monkeypatch.setattr(nlp._bridge, "GuiApp", FakeGUI)
    monkeypatch.setenv("NETLOGO_HOME", str(make_home(tmp_path)))
    return started


def test_run_netlogo_gui(fake_bridge, tmp_path):
    n = run_netlogo()
    assert isinstance(n, NetLogoApp) and not n.headless
    assert fake_bridge == [str(tmp_path / "NetLogo 6.2.2")]
    assert n._target.model == nlp.BASE_MODEL_PATH
    assert n._target.commands == ["setup"]
    n.close_model()  # kept for old scripts
    assert n._target.closed


def test_command_error_raises(fake_bridge):
    n = run_netlogo()

    def fail(command):
        raise nlp._bridge.BridgeError("Nothing named FOO has been defined.")
    n._target.command = fail
    with pytest.raises(nlp.NetLogoError, match="FOO"):
        nlp.run_command(n, "foo")


def test_run_netlogo_headless(fake_bridge):
    n = run_netlogo(headless=True)
    assert isinstance(n, HeadlessNetLogo) and n.headless
    car = pyturtle(n)
    assert car.get_xy() == (20.0, 20.0)


def test_netlogo_session_frees_the_workspace(fake_bridge):
    with netlogo_session(headless=True) as n:
        pyturtle(n)
        workspace = n._target
    assert workspace.disposed and nlp.list_pyturtle == []


def test_run_netlogo_model_does_not_run_setup(fake_bridge, tmp_path):
    model = tmp_path / "My Model.nlogo"
    model.write_text("")
    n = run_netlogo_model(path_model=str(model))
    assert n._target.model == str(model)
    assert n._target.commands == []


def test_missing_model_fails_before_starting_java(fake_bridge, tmp_path):
    with pytest.raises(FileNotFoundError, match="model not found"):
        run_netlogo(path_model=str(tmp_path / "nope.nlogo"))
    assert fake_bridge == []
