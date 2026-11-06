"""Smoke test: every simple example runs against a fake NetLogo without error.

This guards backward compatibility of the public API used by the examples.
"""
import runpy
import time
import pytest

import netlogopy.netlogopy as nlp
from conftest import ROOT, FakeNetLogo

class HeadlessFake(FakeNetLogo):
    def dispose(self):
        pass


EXAMPLES = sorted((ROOT / "Examples" / "simple").glob("*.py"))


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_runs(path, monkeypatch, capsys):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(nlp, "is_netlogo_home", lambda home: True)
    monkeypatch.setattr(nlp._bridge, "start_jvm", lambda home: None)
    monkeypatch.setattr(nlp._bridge, "GuiApp", FakeNetLogo)
    monkeypatch.setattr(nlp._bridge, "HeadlessWorkspace", HeadlessFake)
    monkeypatch.setattr(nlp, "find_netlogo_home", lambda: "NetLogo 6.2.2")
    runpy.run_path(str(path), run_name="__main__")
