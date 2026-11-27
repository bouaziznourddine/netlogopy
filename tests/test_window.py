"""The NetLogo window: closing it by hand, and the autosaves NetLogo writes.

A process can open the NetLogo window only once, so every test runs its
scenario in a child process.  These tests open real windows and run only with
NETLOGOPY_GUI_TESTS=1:

    NETLOGOPY_GUI_TESTS=1 pytest tests/test_window.py
"""

import hashlib
import os
import shutil
import subprocess
import sys
import textwrap

import pytest
from conftest import ROOT

pytestmark = [pytest.mark.netlogo,
              pytest.mark.skipif(os.environ.get("NETLOGOPY_GUI_TESTS") != "1",
                                 reason="opens the NetLogo window: set NETLOGOPY_GUI_TESTS=1")]

# What every child starts with: the model given on the command line, in the window.
OPEN = """
    import os, sys, threading, time
    import jpype
    from netlogopy import NetLogo, NetLogoError, _java
    model = sys.argv[1]
    dialogs = []

    def watch():                                   # any dialog NetLogo shows is a failure
        while _java._gui["app"] is None:           # AWT must be started by NetLogo, not by this thread
            time.sleep(0.05)
        window_class = jpype.JClass("java.awt.Window")
        dialog_class = jpype.JClass("java.awt.Dialog")
        while True:
            for window in window_class.getWindows():
                if isinstance(window, dialog_class) and window.isVisible():
                    title = str(window.getTitle() or "")
                    if title and title not in dialogs:         # NetLogo 6's loading panel has no title
                        dialogs.append(title)
                        print("DIALOG", title, flush=True)
            time.sleep(0.1)

    threading.Thread(target=watch, daemon=True).start()
    nl = NetLogo(model, gui=True)
    folder, known = _java._gui["autosaves"]
    print("FOLDER", folder or "", flush=True)
"""


def run_child(code, model, *arguments, timeout=180):
    """Run a scenario in its own Python process and return what it printed, by keyword."""
    env = dict(os.environ, PYTHONPATH=ROOT)
    env.pop("NETLOGOPY_HEADLESS", None)
    script = textwrap.dedent(OPEN) + textwrap.dedent(code)
    result = subprocess.run([sys.executable, "-c", script, str(model), *arguments],
                            capture_output=True, text=True, timeout=timeout, env=env)
    lines = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        lines.setdefault(key, []).append(value)
    return result, lines


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.md5(handle.read()).hexdigest()


@pytest.fixture
def model(tmp_path):
    """A copy of the bundled model: a killed session must not be tried on a tracked file."""
    from netlogopy import find_netlogo_home
    from netlogopy._java import netlogo_version
    from netlogopy.core import bundled_model
    source = bundled_model(netlogo_version(find_netlogo_home()))
    target = tmp_path / ("my_model" + os.path.splitext(source)[1])
    shutil.copy(source, target)
    shutil.copy(os.path.join(os.path.dirname(source), "base.nls"), tmp_path / "base.nls")
    return target


CLOSE_BY_HAND = """
    nl.setup()
    nl.start("while [ true ] [ tick ]")            # even with a step that never ends
    time.sleep(0.5)
    frame = nl._app.frame()
    if sys.argv[2:] == ["quit"]:                   # File > Quit
        bar, quit_text = frame.getJMenuBar(), _java._i18n("menu.file.quit", "Quit")
        items = [bar.getMenu(m).getItem(i) for m in range(bar.getMenuCount())
                 for i in range(bar.getMenu(m).getItemCount())]
        item = [item for item in items if item is not None and str(item.getText()) == quit_text][0]
        _java.run_on_edt(item.doClick)
    else:                                          # the close button of the window
        event_class = jpype.JClass("java.awt.event.WindowEvent")
        queue = jpype.JClass("java.awt.Toolkit").getDefaultToolkit().getSystemEventQueue()
        queue.postEvent(event_class(frame, event_class.WINDOW_CLOSING))
    limit = time.time() + 30
    while not nl.closed and time.time() < limit:
        time.sleep(0.1)
    print("CLOSED", nl.closed, flush=True)
    try:
        nl.report("count patches")
        print("ANSWER none", flush=True)
    except NetLogoError as error:
        print("ANSWER", str(error).splitlines()[0], flush=True)
    print("ALIVE yes", flush=True)
"""


@pytest.mark.parametrize("how", ["button", "quit"])
def test_closing_the_window_closes_the_session_and_not_python(model, how):
    result, lines = run_child(CLOSE_BY_HAND, model, how)
    assert lines.get("CLOSED") == ["True"], result.stdout + result.stderr
    assert lines["ANSWER"] == ["this NetLogo session is closed: the NetLogo window was closed"]
    assert lines["ALIVE"] == ["yes"] and result.returncode == 0
    assert "DIALOG" not in lines


KILLED = """
    nl.setup()
    nl.add_slider("added-by-python", 0, 10, 3, 1)
    nl.globals["speed"] = 7
    print("GLOBALS", " ".join(nl.global_names()), flush=True)
    time.sleep(8)                                  # NetLogo 7 autosaves 5 s after a change
    os._exit(0)                                    # killed: nothing is closed
"""

REOPENED = """
    print("GLOBALS", " ".join(nl.global_names()), flush=True)
    print("TITLE", str(nl._app.frame().getTitle()), flush=True)
    nl.close()
    print("DONE yes", flush=True)
"""


def test_a_killed_session_leaves_no_autosave_and_the_model_is_never_written(model, tmp_path):
    before = digest(model)
    result, lines = run_child(KILLED, model)
    assert "added-by-python" in lines["GLOBALS"][0], result.stdout + result.stderr
    folder = lines["FOLDER"][0]
    assert sorted(os.listdir(tmp_path)) == sorted(["base.nls", model.name])     # NetLogo 6 autosaves there
    assert not (folder and os.path.isdir(folder) and os.listdir(folder))        # NetLogo 7 autosaves there
    assert digest(model) == before

    # An autosave newer than the model, as an older netlogopy or NetLogo itself may
    # have left: NetLogo 7 would ask "Recover Autosave" and then save over the model.
    planted = None
    if folder:
        os.makedirs(folder, exist_ok=True)
        planted = os.path.join(folder, "autosave_2099-01-01.00_00_00" + model.suffix)
        with open(model, encoding="utf-8") as source, open(planted, "w", encoding="utf-8") as target:
            target.write(source.read().replace("speed", "sped"))
    try:
        result, lines = run_child(REOPENED, model)
        assert lines.get("DONE") == ["yes"], result.stdout + result.stderr
        assert "DIALOG" not in lines                       # nothing was asked
        assert "speed" in lines["GLOBALS"][0].split() and "added-by-python" not in lines["GLOBALS"][0]
        assert digest(model) == before                     # the model file was not written
        assert planted is None or os.path.isfile(planted)  # and the autosave is still the user's
        assert not folder or not os.path.isdir(os.path.join(os.path.dirname(folder), "autosaves.netlogopy"))
    finally:
        if folder:
            shutil.rmtree(os.path.dirname(folder), ignore_errors=True)
