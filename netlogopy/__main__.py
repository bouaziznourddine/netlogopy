"""``python -m netlogopy``: check that netlogopy can find nl4py, NetLogo and Java."""
import platform
import shutil
import sys

from . import __version__
from . import netlogopy as _nlp


def _nl4py_version() -> str:
    try:
        from importlib.metadata import version  # novm (Python 3.8+, guarded)
        return version("nl4py")
    except Exception:
        return "installed"


def main() -> int:
    ok = True
    print("netlogopy {}".format(__version__))
    print("Python    {} ({})".format(sys.version.split()[0], platform.system()))

    if _nlp.nl4py is None:
        ok = False
        print("nl4py     NOT available: {!r}".format(_nlp._NL4PY_IMPORT_ERROR))
    else:
        print("nl4py     {}".format(_nl4py_version()))

    home = _nlp.find_netlogo_home()
    if home is None:
        ok = False
        print("NetLogo   NOT found: set NETLOGO_HOME or pass netlogo_home=... to run_netlogo()")
    else:
        print("NetLogo   {}".format(home))

    java = shutil.which("java")
    if java is None and home is not None:
        try:
            _nlp._ensure_java(home)
            java = shutil.which("java")
        except FileNotFoundError:
            java = None
    if java is None:
        ok = False
        print("Java      NOT found: install a JDK (e.g. 'conda install openjdk=11') or add it to PATH")
    else:
        print("Java      {}".format(java))

    print("Ready." if ok else "Not ready: fix the lines marked NOT above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
