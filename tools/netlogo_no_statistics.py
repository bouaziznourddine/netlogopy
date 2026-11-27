"""Decline NetLogo 7's usage statistics on this computer, without opening NetLogo.

At its first launch on a computer, NetLogo 7 asks in a dialog ("Data Consent")
whether it may send anonymous usage statistics, and waits for the answer.  On
a machine where nobody can click (continuous integration, a server), run this
once before a script that opens the NetLogo window:

    python tools/netlogo_no_statistics.py

It records the answer "No" in NetLogo's own preferences; *Tools > Preferences*
in NetLogo changes it.  NetLogo 6 asks nothing: the script then does nothing.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netlogopy import _java  # noqa: E402

_java.ensure_jvm(headless=True)

import jpype  # noqa: E402

try:
    preferences = getattr(jpype.JClass("org.nlogo.core.NetLogoPreferences$"), "MODULE$")
except Exception:                          # the class came with NetLogo 7
    print("NetLogo", _java.jvm_info().get("version"), "asks nothing: nothing to do")
else:
    preferences.putBoolean("sendAnalytics", False)
    jpype.JClass("java.util.prefs.Preferences").userRoot().flush()
    print("NetLogo", _java.jvm_info().get("version"), "will not send usage statistics from this computer;",
          "question pending:", _java._consent_pending())
