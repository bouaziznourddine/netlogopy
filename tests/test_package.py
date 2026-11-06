"""Package metadata and public API."""
import re

import netlogopy
import netlogopy.netlogopy as nlp
from conftest import ROOT


def test_all_names_exist():
    missing = [name for name in nlp.__all__ if not hasattr(nlp, name)]
    assert not missing


def test_star_import_keeps_the_names_it_exported_before():
    namespace = {}
    exec("from netlogopy.netlogopy import *", namespace)
    for name in ("run_netlogo", "pyturtle", "street", "list_pyturtle", "copy",
                 "os", "shutil", "Any", "List", "Optional"):
        assert name in namespace, name
    assert "re" not in namespace and "_void" not in namespace


def test_package_exports_the_public_functions():
    public = [name for name in nlp.__all__ if name not in
              ("copy", "os", "shutil", "Any", "List", "Optional")]
    missing = [name for name in public if not hasattr(netlogopy, name)]
    assert not missing


def test_version_is_the_same_everywhere():
    version = netlogopy.__version__
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert re.search(r"^version: {}$".format(re.escape(version)), citation, re.M)
    assert "## {}".format(version) in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_diagnostics_command_runs(monkeypatch, capsys):
    from netlogopy import __main__ as diagnostics
    monkeypatch.setattr(nlp, "find_netlogo_home", lambda: None)
    assert diagnostics.main() == 1
    out = capsys.readouterr().out
    assert "netlogopy {}".format(netlogopy.__version__) in out and "NetLogo   NOT found" in out
