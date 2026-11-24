"""The code of the tutorial page runs as written (headless, no sleeping)."""

import os
import re

import pytest

from conftest import ROOT

TUTORIAL = os.path.join(ROOT, "docs", "tutorial.md")


def code_blocks(path):
    with open(path, encoding="utf-8") as file:
        return re.findall(r"^```python\n(.*?)^```", file.read(), re.S | re.M)


def test_tutorial_has_code():
    assert len(code_blocks(TUTORIAL)) >= 5


@pytest.mark.netlogo
def test_tutorial_runs(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("NETLOGOPY_HEADLESS", "1")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.chdir(tmp_path)
    try:
        import matplotlib  # noqa: F401
        has_matplotlib = True
    except ImportError:
        has_matplotlib = False
    namespace = {"__name__": "__main__"}
    for block in code_blocks(TUTORIAL):
        if "matplotlib" in block and not has_matplotlib:
            block = re.sub(r"^(import matplotlib|plt\.).*$", "", block, flags=re.M)
        exec(compile(block, TUTORIAL, "exec"), namespace)
    output = capsys.readouterr().out
    assert output.splitlines()[0] == "61 61 0.0"
    assert (tmp_path / "my-plot.csv").is_file()
    if has_matplotlib:
        assert (tmp_path / "walkers.png").is_file()
