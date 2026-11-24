"""``python -m netlogopy [netlogo_home]``: check that netlogopy can run NetLogo.

Shows the Python, JPype, NetLogo and Java that netlogopy uses, then starts
NetLogo headless on the bundled model.  Exits with status 1 when something
is missing.
"""

import platform
import sys
import time

from . import __version__
from ._java import find_jvm, find_netlogo_home, netlogo_version
from .errors import NetLogoError


def main(argv=None) -> int:
    """Print the versions netlogopy uses and try to start NetLogo headless.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments (default: ``sys.argv[1:]``); the first one,
        if any, is the NetLogo folder.

    Returns
    -------
    int
        0 when NetLogo started, 1 when something is missing or failed.
    """
    argv = sys.argv[1:] if argv is None else argv
    print(f"netlogopy {__version__}")
    print(f"Python    {sys.version.split()[0]} ({platform.system()}, {platform.architecture()[0]})")

    try:
        import jpype
    except ImportError:
        print("JPype     NOT installed: pip install JPype1")
        return 1
    print(f"JPype     {jpype.__version__}")

    try:
        home = find_netlogo_home(argv[0] if argv else None)
    except NetLogoError as error:
        print(f"NetLogo   NOT found: {error}")
        return 1
    print(f"NetLogo   {netlogo_version(home)} in {home}")

    try:
        jvm = find_jvm(home)
    except NetLogoError as error:
        print(f"Java      NOT found: {error}")
        return 1
    print(f"Java      {jvm}")

    from .core import NetLogo
    started = time.time()
    try:
        with NetLogo(netlogo_home=home) as nl:
            nl.setup()
            patches = int(nl.report("count patches"))
    except NetLogoError as error:
        print(f"Start     FAILED: {error}")
        return 1
    print(f"Start     OK in {time.time() - started:.1f} s "
          f"(bundled model, {patches} patches)")
    print("Ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
