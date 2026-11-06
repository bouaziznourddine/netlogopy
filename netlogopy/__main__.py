"""``python -m netlogopy``: check that netlogopy can find JPype, NetLogo and Java."""
import platform
import sys

from . import __version__
from . import _bridge
from . import netlogopy as _nlp


def _jpype_version():
    try:
        import jpype
        return jpype.__version__
    except ImportError:
        return None


def main() -> int:
    ok = True
    print("netlogopy {}".format(__version__))
    print("Python    {} ({}, {})".format(sys.version.split()[0], platform.system(),
                                         platform.architecture()[0]))

    jpype_version = _jpype_version()
    if jpype_version is None:
        ok = False
        print("JPype     NOT installed: pip install JPype1")
    else:
        print("JPype     {}".format(jpype_version))

    home = _nlp.find_netlogo_home()
    if home is None:
        ok = False
        print("NetLogo   NOT found: set NETLOGO_HOME or pass netlogo_home=... to run_netlogo()")
        return 1
    print("NetLogo   {}".format(home))

    jvm = _bridge.jvm_path(home) if jpype_version else None
    if jvm is None:
        ok = False
        print("Java      NOT found: install a JDK, set JAVA_HOME, or set NETLOGOPY_JVM")
    else:
        print("Java      {}".format(jvm))

    print("Ready." if ok else "Not ready: fix the lines marked NOT above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
