"""Smoke test: every simple example runs against a fake NetLogo without error.

This guards backward compatibility of the public API used by the examples.
"""
import runpy
import time
import types

import pytest

import netlogopy.netlogopy as nlp
from conftest import ROOT, FakeNetLogo

EXAMPLES = sorted((ROOT / "Examples" / "simple").glob("*.py"))


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_runs(path, monkeypatch, capsys):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(nlp, "is_netlogo_home", lambda home: True)
    monkeypatch.setattr(nlp, "_ensure_java", lambda home: None)
    monkeypatch.setattr(nlp, "nl4py", types.SimpleNamespace(
        initialize=lambda home: None, netlogo_app=FakeNetLogo,
        create_headless_workspace=FakeNetLogo, delete_headless_workspace=lambda ws: None))
    monkeypatch.setattr(nlp, "find_netlogo_home", lambda: "NetLogo 6.2.2")
    runpy.run_path(str(path), run_name="__main__")
