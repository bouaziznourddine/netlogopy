"""nl4py 0.9 imports pkg_resources, which setuptools removed in version 82."""
import importlib.util
import os
import subprocess
import sys
import textwrap

import pytest

import netlogopy.netlogopy as nlp
from conftest import ROOT


def test_stand_in_pkg_resources(tmp_path, monkeypatch):
    package = tmp_path / "nl4py"
    package.mkdir()
    (package / "__init__.py").write_text(textwrap.dedent("""
        import pkg_resources
        SERVER_PATH = pkg_resources.resource_filename('nl4py', 'nl4pyServer/')
    """))
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "nl4py", raising=False)
    monkeypatch.setitem(sys.modules, "pkg_resources", None)  # "not installed"

    module = nlp._import_nl4py()

    assert module.SERVER_PATH == os.path.join(str(package), "nl4pyServer", "")
    assert sys.modules.get("pkg_resources") is None  # the stand-in was removed


@pytest.mark.skipif(importlib.util.find_spec("nl4py") is None, reason="nl4py not installed")
def test_real_nl4py_imports_without_pkg_resources():
    code = textwrap.dedent("""
        import sys
        sys.modules["pkg_resources"] = None   # as with setuptools >= 82
        sys.path.insert(0, {root!r})
        import netlogopy.netlogopy as nlp
        assert nlp.nl4py is not None, nlp._NL4PY_IMPORT_ERROR
        starter = sys.modules["nl4py.NetLogoControllerServerStarter"]
        path = starter.pkg_resources.resource_filename("nl4py", "nl4pyServer/")
        import glob, os
        assert glob.glob(os.path.join(path, "py4j*.jar")), path
        print("ok")
    """).format(root=str(ROOT))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
