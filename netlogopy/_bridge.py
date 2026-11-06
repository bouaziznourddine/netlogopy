"""Talk to NetLogo through JPype: the JVM runs inside the Python process.

Written for netlogopy on top of NetLogo's public controlling API
(org.nlogo.headless.HeadlessWorkspace and org.nlogo.app.App).

Only one JVM can run in a Python process and it cannot be restarted, so the
first NetLogo folder used stays in use until Python exits.
"""
import glob
import os
import platform
import threading
import time
import warnings
from typing import Any, List, Optional

_state = {"home": None, "gui_started": False}
_lock = threading.Lock()


class BridgeError(RuntimeError):
    """NetLogo answered a command with an error."""


def _jpype() -> Any:
    try:
        import jpype
        import jpype.imports  # noqa: F401
    except ImportError as error:
        raise ImportError("netlogopy needs JPype to run NetLogo. Install it with:  "
                          "pip install JPype1") from error
    return jpype


def jar_dir(home: str) -> str:
    """Folder that holds netlogo-<version>.jar."""
    return os.path.join(home, "Java" if platform.system() == "Darwin" else "app")


def _bundled_jvm(home: str) -> Optional[str]:
    """The JVM library shipped with NetLogo (matches its jars), if any."""
    names = {"Windows": ["runtime/bin/server/jvm.dll", "runtime/bin/client/jvm.dll"],
             "Darwin": ["runtime/Contents/Home/lib/server/libjvm.dylib",
                        "runtime/Contents/Home/lib/libjli.dylib"]}
    default = ["runtime/lib/server/libjvm.so", "lib/runtime/lib/server/libjvm.so"]
    for relative in names.get(platform.system(), default):
        path = os.path.join(home, *relative.split("/"))
        if os.path.isfile(path):
            return path
    return None


def jvm_path(home: str) -> Optional[str]:
    """JVM used to run NetLogo: NETLOGOPY_JVM, then NetLogo's own, then JAVA_HOME/system."""
    if os.environ.get("NETLOGOPY_JVM"):
        return os.environ["NETLOGOPY_JVM"]
    bundled = _bundled_jvm(home)
    if bundled:
        return bundled
    try:
        return _jpype().getDefaultJVMPath()
    except Exception:
        return None


def start_jvm(home: str) -> Any:
    """Start the JVM with NetLogo's jars (once per Python process)."""
    jpype = _jpype()
    with _lock:
        if jpype.isJVMStarted():
            if _state["home"] and os.path.normcase(_state["home"]) != os.path.normcase(home):
                warnings.warn("NetLogo is already running from '{}' in this Python process; "
                              "'{}' is ignored. Restart Python to change NetLogo version."
                              .format(_state["home"], home), RuntimeWarning, stacklevel=3)
            return jpype
        jars = jar_dir(home)
        options = ["-Dnetlogo.extensions.dir=" + os.path.join(jars, "extensions"),
                   "-Dnetlogo.models.dir=" + os.path.join(jars, "models"),
                   "-Dnetlogo.docs.dir=" + os.path.join(jars, "docs")]
        options += os.environ.get("NETLOGOPY_JVM_OPTIONS", "").split()
        path = jvm_path(home)
        if path is None:
            raise FileNotFoundError(
                "No Java found to run NetLogo: NetLogo's own Java runtime is missing and "
                "JAVA_HOME is not set. Install a JDK or set NETLOGOPY_JVM to its jvm library.")
        classpath = sorted(glob.glob(os.path.join(glob.escape(jars), "*.jar")))
        jpype.startJVM(path, *options, classpath=classpath, convertStrings=False)
        _state["home"] = home
    return jpype


def _message(error: BaseException) -> str:
    get_message = getattr(error, "getMessage", None)
    if get_message is not None:
        try:
            text = get_message()
            if text is not None:
                return str(text)
        except Exception:
            pass
    return str(error)


def _open(target: Any, path: str) -> None:
    """open(path, autoInstallLibs) since NetLogo 6.1, open(path) in 6.0."""
    try:
        target.open(path, False)
    except TypeError:
        target.open(path)


class _Workspace:
    """Common part of the GUI app and headless workspaces."""

    def __init__(self, target: Any):
        self._java = target

    def command(self, command: str) -> None:
        jpype = _jpype()
        try:
            self._java.command(command)
        except jpype.JException as error:
            raise BridgeError(_message(error)) from None

    def report(self, reporter: str) -> str:
        """Text of the result (Java's toString), or NetLogo's error message."""
        jpype = _jpype()
        try:
            result = self._java.report(reporter)
        except jpype.JException as error:
            return _message(error)
        return str(result)

    def close_model(self) -> None:
        """Kept for compatibility with nl4py scripts; does nothing."""


class HeadlessWorkspace(_Workspace):
    """NetLogo without window."""

    def __init__(self) -> None:
        jpype = _jpype()
        super().__init__(jpype.JClass("org.nlogo.headless.HeadlessWorkspace").newInstance())

    def open_model(self, path: str) -> None:
        jpype = _jpype()
        try:
            _open(self._java, path)
        except jpype.JException as error:
            raise BridgeError(_message(error)) from None

    def export_view(self, filename: str) -> None:
        self._java.exportView(filename, "png")

    def dispose(self) -> None:
        self._java.dispose()


class GuiApp(_Workspace):
    """The NetLogo application window (one per Python process)."""

    def __init__(self, timeout: float = 120.0) -> None:
        jpype = _jpype()
        if platform.system() == "Darwin":
            raise RuntimeError("The NetLogo window cannot be driven from Python on macOS; "
                               "use run_netlogo(headless=True).")
        app_class = jpype.JClass("org.nlogo.app.App")
        with _lock:
            if not _state["gui_started"]:
                app_class.main(jpype.JArray(jpype.JString)([]))
                _state["gui_started"] = True
        deadline = time.time() + timeout
        app = None
        while app is None:
            try:
                app = app_class.app()
            except jpype.JException:
                app = None
            if app is None:
                if time.time() > deadline:
                    raise TimeoutError("The NetLogo window did not start in time.")
                time.sleep(0.2)
        super().__init__(app)

    def open_model(self, path: str) -> None:
        # Swing objects must be used from the event thread.
        jpype = _jpype()
        errors: List[BaseException] = []

        @jpype.JImplements("java.lang.Runnable")
        class Open:
            @jpype.JOverride
            def run(self) -> None:
                try:
                    _open(app, path)
                except BaseException as error:  # reported to the caller below
                    errors.append(error)

        app = self._java
        jpype.JClass("java.awt.EventQueue").invokeAndWait(Open())
        if errors:
            raise BridgeError(_message(errors[0]))
