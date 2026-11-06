"""Run every example script headless (NETLOGOPY_HEADLESS=1, no sleeping).

    pytest -m examples
"""

import glob
import os
import runpy

import pytest

from conftest import EXAMPLES

SCRIPTS = sorted(glob.glob(os.path.join(EXAMPLES, "**", "*.py"), recursive=True))


@pytest.mark.examples
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: os.path.relpath(path, EXAMPLES))
def test_example_runs(script, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("NETLOGOPY_HEADLESS", "1")
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.chdir(tmp_path)
    runpy.run_path(script, run_name="__main__")
    assert "Traceback" not in capsys.readouterr().err


def test_every_example_is_collected():
    assert len(SCRIPTS) >= 34
