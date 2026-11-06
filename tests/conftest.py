"""Shared fixtures.

Tests marked ``netlogo`` start NetLogo through JPype; they are skipped when
JPype, NetLogo or a suitable Java runtime is missing.  NetLogo is found like
netlogopy does it: NETLOGO_HOME, else the newest installed version.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "Examples")
FIRE_MODEL = os.path.join(EXAMPLES, "complexe", "Fire", "Fire.nlogo")
WOLF_MODEL = os.path.join(EXAMPLES, "complexe", "Wolf Sheep", "Wolf Sheep Predation.nlogo")

sys.path.insert(0, ROOT)

_skip_reason = None
_checked = False


def netlogo_skip_reason():
    """Why NetLogo tests cannot run here (None when they can)."""
    global _checked, _skip_reason
    if not _checked:
        _checked = True
        try:
            __import__("jpype")
            from netlogopy import NetLogoNotFoundError, find_netlogo_home
            from netlogopy._java import find_jvm
            find_jvm(find_netlogo_home())
        except ImportError as exc:
            _skip_reason = f"JPype is not installed ({exc})"
        except NetLogoNotFoundError as exc:
            _skip_reason = str(exc)
    return _skip_reason


def pytest_collection_modifyitems(config, items):
    reason = None
    for item in items:
        if "netlogo" in item.keywords or "examples" in item.keywords:
            reason = reason or netlogo_skip_reason()
            if reason:
                item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture(scope="session")
def session():
    """One headless session on the bundled model, shared by the tests."""
    from netlogopy import NetLogo
    nl = NetLogo()
    yield nl
    nl.close()


@pytest.fixture
def nl(session):
    """The shared session with a fresh world (``setup``) and default topology."""
    session.setup()
    session.set_topology(False, False)
    return session
