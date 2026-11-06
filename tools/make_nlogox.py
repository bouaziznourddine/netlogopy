"""Regenerate netlogopy/netlogopy.nlogox (NetLogo 7 format) from netlogopy/netlogopy.nlogo.

    python tools/make_nlogox.py ["C:/Program Files/NetLogo 7.0.0"]

NetLogo 7 opens .nlogo files only after asking to resize their widgets, so
netlogopy ships the bundled model in both formats.  This script opens the
.nlogo in the NetLogo 7 window (netlogopy answers "Resize and adjust
positions"), then saves the converted model as .nlogox.  Run it after every
change of netlogopy.nlogo.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jpype  # noqa: E402

from netlogopy import NetLogo, _java  # noqa: E402

SOURCE = os.path.join(ROOT, "netlogopy", "netlogopy.nlogo")
TARGET = os.path.join(ROOT, "netlogopy", "netlogopy.nlogox")
MARKER = "; netlogopy demo model"


def _remove_netlogo_leftovers() -> None:
    """Temporary copies and autosaves NetLogo 7 makes of the converted model."""
    paths = glob.glob(os.path.join(ROOT, "netlogopy", ".netlogopy.tmp.*"))
    for path in glob.glob(os.path.expanduser("~/.nlogo/modelConfigs/*/autosaves/*")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            if MARKER in fh.read(500):
                paths.append(path)
    for path in paths:
        os.remove(path)


def main() -> None:
    _remove_netlogo_leftovers()          # an old autosave would make NetLogo ask questions
    nl = NetLogo(SOURCE, gui=True, netlogo_home=sys.argv[1] if len(sys.argv) > 1 else None)
    try:
        version = nl.netlogo_version
        if int(version.split(".")[0]) < 7:
            sys.exit("NetLogo 7 or newer is needed to write .nlogox files")
        app = nl._app
        model = _java.run_on_edt(lambda: app.fileManager().currentModel())
        file_format = jpype.JClass("org.nlogo.fileformat.FileFormat")
        loader = file_format.standardXMLLoader(False, app.workspace().compiler().utilities(), False)
        text = str(loader.sourceString(model, "nlogox").get())
        # the conversion marked the model as modified: do not autosave it on exit
        _java.run_on_edt(lambda: app.dirtyMonitor().discardNewAutoSaves())
    finally:
        nl.close()
    text = re.sub(r'<model version="NetLogo [^"]*"', f'<model version="NetLogo {version}"',
                  text, count=1)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {TARGET} ({len(text)} characters)")
    _remove_netlogo_leftovers()
    # NetLogo 7 autosaves the converted (modified) model from a JVM shutdown hook:
    # stop the JVM without running the hooks.
    sys.stdout.flush()
    jpype.JClass("java.lang.Runtime").getRuntime().halt(0)


if __name__ == "__main__":
    main()
