"""Finding NetLogo/Java and starting GUI or headless instances (nl4py is faked)."""
import os
import types

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

def test_java_from_netlogo_runtime(tmp_path, monkeypatch):
    home = tmp_path / "NetLogo 6.2.2"
    java = home / "runtime" / "bin" / ("java.exe" if os.name == "nt" else "java")
    java.parent.mkdir(parents=True)
    java.write_text("#!/bin/sh\n")
    java.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.delenv("JAVA_HOME", raising=False)
    nlp._ensure_java(str(home))
    assert os.environ["PATH"].split(os.pathsep)[0] == str(java.parent)


def test_java_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.delenv("JAVA_HOME", raising=False)
    with pytest.raises(FileNotFoundError, match="Java"):
        nlp._ensure_java(str(tmp_path))


# ── Starting NetLogo with a fake nl4py ────────────────────────────────────────

class FakeController:
    """Mimics nl4py's Java controllers: report() takes and returns bytes."""

    def __init__(self, charset):
        self.charset = charset
        self.received = []

    def report(self, data):
        text = data.decode(self.charset)
        self.received.append(text)
        if text.startswith("get_label_turtle"):
            return "Vitesse élevée".encode(self.charset)
        if text.startswith("getxyturtle"):
            return b"[1.0, 2.0]"
        return b"0.0"


def fake_gateway(charset_name):
    charset = types.SimpleNamespace(name=lambda: charset_name)
    java_charset = types.SimpleNamespace(defaultCharset=lambda: charset)
    jvm = types.SimpleNamespace(java=types.SimpleNamespace(
        nio=types.SimpleNamespace(charset=types.SimpleNamespace(Charset=java_charset))))
    return types.SimpleNamespace(jvm=jvm)


class FakeGUI(FakeNetLogo):
    def __init__(self, charset="windows-1252"):
        super().__init__()
        self.app = FakeController(charset)
        self.gateway = fake_gateway(charset)


class FakeHeadless(FakeNetLogo):
    def __init__(self):
        super().__init__()
        self.hwc = FakeController("UTF-8")
        self.gateway = fake_gateway("UTF-8")
        self.deleted = False

    def deleteWorkspace(self):
        self.deleted = True


@pytest.fixture
def fake_nl4py(tmp_path, linux, monkeypatch):
    calls = []
    module = types.SimpleNamespace(
        initialize=lambda home: calls.append(("initialize", home)),
        netlogo_app=lambda: FakeGUI(),
        create_headless_workspace=lambda: FakeHeadless(),
        delete_headless_workspace=lambda ws: (calls.append(("delete", ws)), ws.deleteWorkspace()),
        calls=calls,
    )
    monkeypatch.setattr(nlp, "nl4py", module)
    monkeypatch.setattr(nlp, "_ensure_java", lambda home: None)
    monkeypatch.setenv("NETLOGO_HOME", str(make_home(tmp_path)))
    return module


def test_run_netlogo_gui(fake_nl4py, tmp_path):
    n = run_netlogo()
    assert isinstance(n, NetLogoApp) and not n.headless
    assert fake_nl4py.calls == [("initialize", str(tmp_path / "NetLogo 6.2.2"))]
    assert n.nl4py_object.model == nlp.BASE_MODEL_PATH
    assert n.nl4py_object.commands == ["setup"]
    n.close_model()  # forwarded to nl4py
    assert n.nl4py_object.closed


def test_gui_report_uses_the_java_charset(fake_nl4py):
    n = run_netlogo()
    car = pyturtle(n)
    car.set_label("Vitesse élevée")
    assert n.app.received[-1] == 'set_label_turtle [0 "Vitesse élevée"]'
    assert car.get_label() == "Vitesse élevée"


def test_run_netlogo_headless_reads_raw_results(fake_nl4py):
    n = run_netlogo(headless=True)
    assert isinstance(n, HeadlessNetLogo) and n.headless
    car = pyturtle(n)
    assert car.get_xy() == (1.0, 2.0)  # nl4py's own headless report() would fail here


def test_netlogo_session_frees_the_workspace(fake_nl4py):
    with netlogo_session(headless=True) as n:
        pyturtle(n)
        workspace = n.nl4py_object
    assert workspace.deleted and nlp.list_pyturtle == []


def test_run_netlogo_model_does_not_run_setup(fake_nl4py, tmp_path):
    model = tmp_path / "My Model.nlogo"
    model.write_text("")
    n = run_netlogo_model(path_model=str(model))
    assert n.nl4py_object.model == str(model)
    assert n.nl4py_object.commands == []


def test_missing_model_fails_before_starting_java(fake_nl4py, tmp_path):
    with pytest.raises(FileNotFoundError, match="model not found"):
        run_netlogo(path_model=str(tmp_path / "nope.nlogo"))
    assert fake_nl4py.calls == []
