"""Static checks of the NetLogo code shipped with netlogopy (no NetLogo needed)."""
import importlib.util
import re

import pytest

from conftest import ROOT

BASE_NLS = ROOT / "netlogopy" / "base.nls"
MODEL = ROOT / "netlogopy" / "netlogopy.nlogo"
PYTHON = ROOT / "netlogopy" / "netlogopy.py"


def load_sync_tool():
    spec = importlib.util.spec_from_file_location("sync_nlogo", ROOT / "tools" / "sync_nlogo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_comments_and_strings(code):
    code = re.sub(r'"(\\.|[^"\\])*"', '""', code)
    return re.sub(r";[^\n]*", "", code)


def procedures(code):
    """{name: body} of every to / to-report procedure."""
    code = strip_comments_and_strings(code)
    found = {}
    for match in re.finditer(r"(?ims)^\s*(?:to-report|to)\s+([^\s\[]+)(.*?)^\s*end\b", code):
        name = match.group(1).lower()
        assert name not in found, "procedure defined twice: " + name
        found[name] = match.group(2)
    return found


def model_code():
    return MODEL.read_text(encoding="utf-8").split("\n@#$#@#$#@")[0]


def reporters_called_from_python():
    source = PYTHON.read_text(encoding="utf-8")
    return set(re.findall(r'_(?:void|report)\([^,]+,\s*"([^"]+)"', source))


def test_model_and_examples_are_in_sync_with_base_nls():
    assert load_sync_tool().main(["--check"]) == 0


@pytest.mark.parametrize("code", [BASE_NLS.read_text(encoding="utf-8"), model_code()],
                         ids=["base.nls", "netlogopy.nlogo"])
def test_every_reporter_used_by_python_exists(code):
    names = reporters_called_from_python()
    assert len(names) > 40
    missing = {name for name in names if name.lower() not in procedures(code)}
    assert not missing


@pytest.mark.parametrize("code", [BASE_NLS.read_text(encoding="utf-8"), model_code()],
                         ids=["base.nls", "netlogopy.nlogo"])
def test_brackets_and_ends_are_balanced(code):
    clean = strip_comments_and_strings(code)
    assert clean.count("[") == clean.count("]")
    starts = len(re.findall(r"(?im)^\s*to(?:-report)?\s", clean))
    ends = len(re.findall(r"(?im)^\s*end\s*$", clean))
    assert starts == ends
    for name, body in procedures(code).items():
        assert body.count("[") == body.count("]"), name


def test_model_keeps_setup_and_go():
    names = procedures(model_code())
    assert {"setup", "go", "test"} <= set(names)


def test_actions_report_zero():
    """Python treats any other result of an action as an error message."""
    python = PYTHON.read_text(encoding="utf-8")
    actions = set(re.findall(r'_void\([^,]+,\s*"([^"]+)"', python))
    bodies = procedures(BASE_NLS.read_text(encoding="utf-8"))
    for name in actions:
        assert re.search(r"report 0\s*$", bodies[name.lower()].strip()), name
