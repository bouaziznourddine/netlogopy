"""End-to-end test of the JPype bridge with a fake NetLogo written in Java.

tests/fake_netlogo holds tiny stand-ins for org.nlogo.headless.HeadlessWorkspace
and org.nlogo.app.App. They are compiled into a fake NetLogo folder, then a
separate Python process (one JVM per process) drives them through netlogopy.
Skipped when javac or JPype is missing.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

from conftest import ROOT

pytestmark = pytest.mark.skipif(
    shutil.which("javac") is None or shutil.which("jar") is None
    or importlib.util.find_spec("jpype") is None,
    reason="needs javac, jar and JPype")

SCRIPT = textwrap.dedent("""
    import sys, warnings
    sys.path.insert(0, {root!r})
    from netlogopy.netlogopy import *

    model = {model!r}

    # headless
    n = run_netlogo({home!r}, model, headless=True, setup=False)
    assert isinstance(n, HeadlessNetLogo)
    run_command(n, "tick")
    assert get_ticks(n) == 1
    assert report_value(n, "list") == [1.0, 2.5]
    car = pyturtle(n)
    car.fd(0.5)
    car.set_label("Vitesse élevée مرحبا")
    assert car.get_label() == "Vitesse élevée مرحبا", car.get_label()
    try:
        run_command(n, "bad command")
    except NetLogoError as error:
        assert "Nothing named BAD" in str(error)
    else:
        raise AssertionError("no NetLogoError")
    try:
        get_ticks.__globals__["_as_float"](n.report("nope"), "nope")
    except NetLogoError as error:
        assert "NOPE" in str(error)
    workspace = n._target._java
    close_netlogo(n)
    assert workspace.disposed

    # GUI (App.main is called once, the model is opened on the event thread)
    g1 = run_netlogo({home!r}, model)
    g2 = run_netlogo({home!r}, model)
    from jpype import JClass
    App = JClass("org.nlogo.app.App")
    assert App.mainCalls == 1
    assert App.app().openedOnEventThread
    assert str(App.app().model) == model
    print("ok")
""")


def test_bridge_with_fake_netlogo(tmp_path):
    classes = tmp_path / "classes"
    sources = [str(p) for p in (ROOT / "tests" / "fake_netlogo").rglob("*.java")]
    subprocess.run(["javac", "-encoding", "UTF-8", "-d", str(classes)] + sources, check=True)
    home = tmp_path / "NetLogo 6.2.2"
    (home / "app").mkdir(parents=True)
    subprocess.run(["jar", "cf", str(home / "app" / "netlogo-6.2.2.jar"), "-C", str(classes), "."],
                   check=True)
    model = tmp_path / "model.nlogo"
    model.write_text("")

    script = SCRIPT.format(root=str(ROOT), home=str(home), model=str(model))
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            encoding="utf-8", timeout=120,
                            env=dict(os.environ, NETLOGOPY_JVM_OPTIONS="-Djava.awt.headless=true"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("ok")
