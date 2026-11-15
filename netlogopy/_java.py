"""Find NetLogo and a Java runtime, and run NetLogo in-process through JPype.

netlogopy talks directly to NetLogo's own Java API
(``org.nlogo.headless.HeadlessWorkspace`` and ``org.nlogo.app.App``) through
JPype: there is no separate Java server and no socket.  A Python process can
host a single JVM, so every session of a process uses the same NetLogo
installation.
"""

import atexit
import glob
import os
import platform
import re
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .errors import NetLogoError, NetLogoNotFoundError

__all__ = [
    "find_netlogo_home",
    "find_jar_dir",
    "find_jvm",
    "netlogo_version",
    "ensure_jvm",
    "jvm_info",
]

_JAR_RE = re.compile(r"^netlogo-(\d+(?:\.\d+)*)[\w.-]*\.jar$", re.IGNORECASE)
#: JPype >= 1.5 refuses to start Java 8 (bundled with NetLogo <= 6.2).
_MIN_JAVA = 9

_lock = threading.RLock()
_jvm: Dict[str, Any] = {}
_open_handles: List["WorkspaceHandle"] = []
_gui: Dict[str, Any] = {"app": None, "closed": False}


# ─── NetLogo installation ──────────────────────────────────────────────────────

def _version_tuple(text: Optional[str]) -> Tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text or "")[:3]) or (0,)


def _netlogo_jar(directory: str) -> Optional[str]:
    try:
        names = os.listdir(directory)
    except OSError:
        return None
    for name in sorted(names):
        if _JAR_RE.match(name):
            return os.path.join(directory, name)
    return None


def find_jar_dir(netlogo_home: str) -> Optional[str]:
    """Return the folder holding ``netlogo-<version>.jar`` and its libraries."""
    home = os.path.abspath(netlogo_home)
    if not os.path.isdir(home):
        return None
    # Windows / Linux / macOS layouts of NetLogo 6.x and 7.x
    for sub in ("app", os.path.join("lib", "app"), "Java", "lib", ""):
        folder = os.path.join(home, sub) if sub else home
        if _netlogo_jar(folder):
            return folder
    # Unusual layouts (e.g. macOS application bundles): shallow search.
    for root, dirs, files in os.walk(home):
        if root[len(home):].count(os.sep) >= 4:
            dirs[:] = []
        if any(_JAR_RE.match(name) for name in files):
            return root
    return None


def netlogo_version(netlogo_home: str) -> Optional[str]:
    """Return the NetLogo version of an installation (e.g. ``"6.2.2"``)."""
    jar_dir = find_jar_dir(netlogo_home)
    jar = _netlogo_jar(jar_dir) if jar_dir else None
    match = _JAR_RE.match(os.path.basename(jar)) if jar else None
    return match.group(1) if match else None


def _candidate_homes() -> List[str]:
    system = platform.system()
    if system == "Windows":
        bases = {os.environ.get(key) for key in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")}
        bases.update({"C:/Program Files", "C:/Program Files (x86)"})
        if os.environ.get("LOCALAPPDATA"):
            bases.add(os.path.join(os.environ["LOCALAPPDATA"], "Programs"))
        patterns = [os.path.join(base, "NetLogo*") for base in bases if base]
    elif system == "Darwin":
        patterns = ["/Applications/NetLogo*", os.path.expanduser("~/Applications/NetLogo*")]
    else:
        patterns = [os.path.expanduser("~/NetLogo*"), os.path.expanduser("~/netlogo*"),
                    "/opt/NetLogo*", "/opt/netlogo*", "/usr/local/NetLogo*",
                    "/usr/local/netlogo*", "/usr/share/netlogo*", "/usr/lib/netlogo*"]
    homes, seen = [], set()
    for pattern in patterns:
        for path in glob.glob(pattern):
            key = os.path.normcase(os.path.abspath(path))
            if key not in seen and os.path.isdir(path):
                seen.add(key)
                homes.append(os.path.abspath(path))
    return homes


def find_netlogo_home(netlogo_home: Optional[str] = None) -> str:
    """Locate the NetLogo installation folder.

    Order: the ``netlogo_home`` argument, the ``NETLOGO_HOME`` environment
    variable, then the newest NetLogo found in the usual install locations.
    """
    for given, origin in ((netlogo_home, "netlogo_home"),
                          (os.environ.get("NETLOGO_HOME"), "NETLOGO_HOME")):
        if given:
            given = os.fspath(given)
            if find_jar_dir(given):
                return os.path.abspath(given)
            raise NetLogoNotFoundError(
                f"{origin}={given!r} is not a NetLogo installation "
                "(no netlogo-<version>.jar found in it).")
    found = [(_version_tuple(netlogo_version(home)), home)
             for home in _candidate_homes() if find_jar_dir(home)]
    if not found:
        raise NetLogoNotFoundError(
            "NetLogo was not found. Install it from "
            "https://ccl.northwestern.edu/netlogo/download.shtml, or pass "
            "netlogo_home='...' (or set the NETLOGO_HOME environment variable).")
    return max(found)[1]


# ─── Java runtime ──────────────────────────────────────────────────────────────

_JVM_LIBS = {
    "Windows": ("bin/server/jvm.dll", "bin/client/jvm.dll",
                "jre/bin/server/jvm.dll", "jre/bin/client/jvm.dll"),
    "Darwin": ("lib/server/libjvm.dylib", "Contents/Home/lib/server/libjvm.dylib",
               "jre/lib/server/libjvm.dylib"),
    "Linux": ("lib/server/libjvm.so", "lib/amd64/server/libjvm.so",
              "lib/aarch64/server/libjvm.so", "jre/lib/amd64/server/libjvm.so",
              "lib/client/libjvm.so"),
}


def _jvm_library(java_home: str) -> Optional[str]:
    if os.path.isfile(java_home):          # direct path to jvm.dll / libjvm.so
        return os.path.abspath(java_home)
    for relative in _JVM_LIBS.get(platform.system(), _JVM_LIBS["Linux"]):
        path = os.path.join(java_home, *relative.split("/"))
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


def _java_version(java_home: str) -> Optional[int]:
    """Major Java version of a runtime folder (None when unknown)."""
    if not os.path.isdir(java_home):
        return None
    try:
        with open(os.path.join(java_home, "release"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("JAVA_VERSION="):
                    parts = _version_tuple(line.split("=", 1)[1])
                    return parts[1] if parts[0] == 1 and len(parts) > 1 else parts[0]
    except OSError:
        pass
    for rt_jar in (("lib", "rt.jar"), ("jre", "lib", "rt.jar")):
        if os.path.isfile(os.path.join(java_home, *rt_jar)):
            return 8                       # rt.jar disappeared with Java 9
    return None


def _bundled_runtimes(netlogo_home: str) -> List[str]:
    home = os.path.abspath(netlogo_home)
    candidates = [os.path.join(home, "runtime"), os.path.join(home, "lib", "runtime"),
                  os.path.join(home, "runtime", "Contents", "Home")]
    candidates += glob.glob(os.path.join(home, "*.app", "Contents", "runtime", "Contents", "Home"))
    candidates += glob.glob(os.path.join(home, "*.app", "Contents", "runtime"))
    return [path for path in candidates if os.path.isdir(path)]


def find_jvm(netlogo_home: str, java_home: Optional[str] = None) -> str:
    """Return the path of a JVM library (jvm.dll, libjvm.so...) able to run NetLogo.

    Order: ``java_home``, the runtime bundled with NetLogo, ``JAVA_HOME``, the
    active conda environment, the runtimes of other NetLogo installations,
    then JPype's default JVM.  Java 8 runtimes are skipped (JPype needs 9+).
    """
    minimum = 17 if _version_tuple(netlogo_version(netlogo_home)) >= (7,) else _MIN_JAVA
    rejected: List[str] = []

    def usable(folder: Optional[str], origin: str) -> Optional[str]:
        if not folder:
            return None
        lib = _jvm_library(folder)
        if lib is None:
            rejected.append(f"{origin}: no JVM library in {folder}")
            return None
        version = _java_version(folder)
        if version is not None and version < minimum:
            rejected.append(f"{origin}: Java {version} in {folder} is too old (Java {minimum}+ needed)")
            return None
        return lib

    if java_home:
        lib = usable(os.fspath(java_home), "java_home")
        if lib:
            return lib
        raise NetLogoNotFoundError("Unusable java_home. " + rejected[-1])

    candidates = [(rt, "runtime bundled with NetLogo") for rt in _bundled_runtimes(netlogo_home)]
    candidates.append((os.environ.get("JAVA_HOME"), "JAVA_HOME"))
    for prefix in dict.fromkeys((os.environ.get("CONDA_PREFIX"), sys.prefix, sys.base_prefix)):
        if prefix:
            candidates.append((os.path.join(prefix, "Library") if platform.system() == "Windows"
                               else prefix, "conda environment"))
    others = sorted(((_version_tuple(netlogo_version(h)), h) for h in _candidate_homes()
                     if os.path.normcase(os.path.abspath(h)) != os.path.normcase(os.path.abspath(netlogo_home))),
                    reverse=True)
    for _, home in others:
        candidates += [(rt, f"runtime of {os.path.basename(home)}") for rt in _bundled_runtimes(home)]
    for folder, origin in candidates:
        lib = usable(folder, origin)
        if lib:
            return lib
    try:
        import jpype
        return jpype.getDefaultJVMPath()
    except Exception as exc:               # JVMNotFoundException and friends
        rejected.append(f"JPype default JVM: {exc}")
    raise NetLogoNotFoundError(
        "No Java runtime able to run NetLogo was found:\n  - " + "\n  - ".join(rejected) +
        "\nNetLogo 6.2 and older bundle Java 8, which JPype cannot start. Install Java 11+ "
        "(for example `conda install -c conda-forge openjdk=17`), install NetLogo 6.3+, "
        "or pass java_home='...' / set JAVA_HOME.")


# ─── JVM start-up and shutdown ─────────────────────────────────────────────────

def _same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def prefer_headless_jvm(gui: bool) -> bool:
    """Start AWT in headless mode when no window can ever be shown."""
    if gui:
        return False
    if platform.system() == "Darwin":
        return True
    if platform.system() == "Linux":
        return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return False


def _natives_folder(base: str) -> Optional[str]:
    system, machine = platform.system(), platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "amd64"
    name = {"Windows": f"windows-{arch}", "Linux": f"linux-{arch}", "Darwin": "macosx-universal"}.get(system)
    folder = os.path.join(base, "natives", name) if name else None
    return folder if folder and os.path.isdir(folder) else None


def _jvm_options(home: str, jar_dir: str, version: Tuple[int, ...], headless: bool) -> List[str]:
    options = [
        "-XX:+IgnoreUnrecognizedVMOptions",
        "-XX:MaxRAMPercentage=50",
        "-Dfile.encoding=UTF-8",
        "--add-exports=java.base/java.lang=ALL-UNNAMED",
        "--add-exports=java.desktop/sun.awt=ALL-UNNAMED",
        "--add-exports=java.desktop/sun.java2d=ALL-UNNAMED",
    ]
    for prop, folder in (("netlogo.extensions.dir", "extensions"),
                         ("netlogo.models.dir", "models"),
                         ("netlogo.docs.dir", "docs")):
        for base in (jar_dir, os.path.dirname(jar_dir), home):
            path = os.path.join(base, folder)
            if os.path.isdir(path):
                options.append(f"-D{prop}={path}")
                break
    for base in (jar_dir, os.path.dirname(jar_dir), home):
        natives = _natives_folder(base)
        if natives:
            options.append(f"-Djava.library.path={natives}")
            break
    if version >= (7,):
        options.append("-Dorg.nlogo.release=true")
    if headless:
        options.append("-Djava.awt.headless=true")
    return options


def ensure_jvm(netlogo_home: Optional[str] = None, java_home: Optional[str] = None,
               jvm_args: Sequence[str] = (), headless: bool = False) -> str:
    """Start the JVM with NetLogo on its classpath (once per process).

    Returns the NetLogo installation folder used by this process.
    """
    import jpype
    with _lock:
        if jpype.isJVMStarted():
            running = _jvm.get("home")
            if running is None:            # started by someone else
                try:
                    jpype.JClass("org.nlogo.headless.HeadlessWorkspace")
                except Exception as exc:
                    raise NetLogoError(
                        "A JVM is already running in this Python process without NetLogo "
                        "on its classpath; netlogopy cannot add NetLogo to it.") from exc
                running = find_netlogo_home(netlogo_home) if netlogo_home else "<external JVM>"
                _jvm.update(home=running, version=None, jvm=None, headless=None)
                atexit.register(_shutdown)
                return running
            if netlogo_home and not _same_path(find_netlogo_home(netlogo_home), running):
                raise NetLogoError(
                    f"This Python process already runs NetLogo from {running!r}. Only one "
                    "NetLogo installation can be used per process: restart Python to switch.")
            return running

        home = find_netlogo_home(netlogo_home)
        jar_dir = find_jar_dir(home)
        version = _version_tuple(netlogo_version(home))
        jvm_path = find_jvm(home, java_home)
        jars = sorted(glob.glob(os.path.join(jar_dir, "*.jar")),
                      key=lambda path: (not _JAR_RE.match(os.path.basename(path)), path))
        options = _jvm_options(home, jar_dir, version, headless) + list(jvm_args)
        try:
            jpype.startJVM(jvm_path, *options, classpath=jars, convertStrings=False)
        except Exception as exc:
            raise NetLogoError(f"Could not start the Java VM {jvm_path}: {exc}") from exc
        _jvm.update(home=home, version=".".join(map(str, version)), jvm=jvm_path, headless=headless)
        # Registered after JPype's own exit hook, so it runs first (atexit is LIFO):
        # NetLogo's threads must be stopped before JPype shuts the JVM down.
        atexit.register(_shutdown)
        return home


def ensure_context_class_loader() -> None:
    """Give the calling thread NetLogo's class loader.

    Threads attached to the JVM by JPype have none, and NetLogo 7 needs it
    to open models (e.g. from run_experiment's worker threads).
    """
    import jpype
    thread = jpype.JClass("java.lang.Thread").currentThread()
    if thread.getContextClassLoader() is None:
        loader = jpype.JClass("org.nlogo.headless.HeadlessWorkspace").class_.getClassLoader()
        thread.setContextClassLoader(loader)


def jvm_info() -> Dict[str, Any]:
    """Details of the running JVM: NetLogo ``home`` and ``version``, ``jvm`` library."""
    return dict(_jvm)


class WorkspaceHandle:
    """Owns one NetLogo workspace (headless, or the GUI application) and disposes it once."""

    def __init__(self, workspace: Any, app: Any = None):
        self.workspace = workspace
        self.app = app
        self.owner: Any = None                 # weak reference to the NetLogo session
        self.closed = False
        self._close_lock = threading.Lock()
        with _lock:
            _open_handles.append(self)

    def close(self) -> None:
        with self._close_lock:
            if self.closed:
                return
            self.closed = True
        try:
            session = self.owner() if self.owner is not None else None
            if session is not None:
                session._stop_quietly()            # end its background run first
        except Exception:
            pass
        try:
            if self.app is not None:
                _close_gui(self.app)
            else:
                self.workspace.dispose()
        except Exception:                  # best effort: never mask the real error
            pass
        finally:
            with _lock:
                if self in _open_handles:
                    _open_handles.remove(self)


def _shutdown() -> None:
    for handle in list(_open_handles):
        handle.close()
    if _gui["app"] is None:
        return
    deadline = time.monotonic() + 3        # AWT needs a moment to stop its threads
    while _lingering_threads() and time.monotonic() < deadline:
        time.sleep(0.1)
    if _lingering_threads() or _version_tuple(_jvm.get("version")) >= (7,):
        # Stopping the JVM would wait forever: for threads still alive, or for
        # the shutdown hooks of NetLogo 7's window.  Let it end with the process.
        try:
            import jpype.config
            jpype.config.destroy_jvm = False
            jpype.config.onexit = False
        except Exception:
            pass


def _lingering_threads() -> List[str]:
    """Names of the non-daemon Java threads still alive, besides the current one."""
    import jpype
    names: List[str] = []
    try:
        thread_class = jpype.JClass("java.lang.Thread")
        current = thread_class.currentThread()
        group = current.getThreadGroup()
        while group.getParent() is not None:
            group = group.getParent()
        threads = jpype.JArray(thread_class)(group.activeCount() + 16)
        for index in range(group.enumerate(threads, True)):
            thread = threads[index]
            if not thread.isDaemon() and not thread.equals(current) \
                    and str(thread.getName()) != "DestroyJavaVM":
                names.append(str(thread.getName()))
    except Exception:
        pass
    return names


# ─── GUI ───────────────────────────────────────────────────────────────────────

def run_on_edt(function: Callable[[], Any]) -> Any:
    """Run ``function`` on the AWT event thread, wait, and return its result."""
    import jpype
    result: List[Any] = []
    errors: List[BaseException] = []

    def run() -> None:
        try:
            result.append(function())
        except BaseException as exc:       # re-raised in the calling thread
            errors.append(exc)

    event_queue = jpype.JClass("java.awt.EventQueue")
    task = jpype.JProxy("java.lang.Runnable", dict={"run": run})
    if event_queue.isDispatchThread():
        run()
    else:
        event_queue.invokeAndWait(task)
    if errors:
        raise errors[0]
    return result[0] if result else None


def call_open(target: Any, path: str) -> None:
    """``open(path)`` on a workspace or App, whatever its NetLogo signature."""
    try:
        target.open(path)
    except TypeError:                      # NetLogo 6.2+: open(path, autoInstallLibs)
        target.open(path, False)


#: Question NetLogo 7 asks when its window opens a model saved by NetLogo 6,
#: and the answer netlogopy clicks (NetLogo's recommended choice).  Other
#: questions are left to the user.
_OPEN_DIALOG_ANSWERS = {"Convert Widgets to New Sizes": "Resize and adjust positions"}


def _find_button(component: Any, text: str, button_class: Any) -> Any:
    if isinstance(component, button_class) and str(component.getText()) == text:
        return component
    for child in (component.getComponents() if hasattr(component, "getComponents") else ()):
        found = _find_button(child, text, button_class)
        if found is not None:
            return found
    return None


def _answer_open_dialogs(stop: threading.Event) -> None:
    import jpype
    window_class = jpype.JClass("java.awt.Window")
    button_class = jpype.JClass("javax.swing.AbstractButton")
    while not stop.wait(0.1):
        for window in window_class.getWindows():
            try:
                title = str(window.getTitle()) if hasattr(window, "getTitle") else ""
                answer = _OPEN_DIALOG_ANSWERS.get(title)
                if answer is None or not window.isVisible():
                    continue
                button = _find_button(window, answer, button_class)
                if button is not None:
                    run_on_edt(button.doClick)
            except Exception:              # the dialog closed meanwhile
                pass


def open_in_gui(app: Any, path: str) -> None:
    """Open a model in the NetLogo window, answering NetLogo's conversion questions."""
    stop = threading.Event()
    watcher = threading.Thread(target=_answer_open_dialogs, args=(stop,),
                               name="netlogopy-dialogs", daemon=True)
    watcher.start()
    try:
        run_on_edt(lambda: call_open(app, path))
    finally:
        stop.set()
        watcher.join(2)


def launch_gui() -> Any:
    """Open the NetLogo window (once per process) and return the ``App``."""
    import jpype
    with _lock:
        if _gui["app"] is not None:
            if _gui["closed"]:
                raise NetLogoError(
                    "The NetLogo window was closed; NetLogo cannot open another window in "
                    "the same Python process. Restart Python, or use gui=False.")
            raise NetLogoError(
                "A NetLogo window is already open in this Python process (NetLogo allows one "
                "per process). Close it first, or use headless sessions (gui=False).")
        if platform.system() == "Darwin":
            raise NetLogoError("The NetLogo window (gui=True) is not supported on macOS: "
                               "AWT must own the main thread there. Use gui=False.")
        if _jvm.get("headless"):
            raise NetLogoError("The JVM was started in headless mode (no display), so the "
                               "NetLogo window cannot be shown. Use gui=False.")
        app_class = jpype.JClass("org.nlogo.app.App")
        app_class.main(jpype.JArray(jpype.JString)([]))
        app = app_class.app()
        _gui["app"] = app
        return app


def _close_gui(app: Any) -> None:
    """Close the NetLogo window without saving, and stop NetLogo's GUI threads."""
    import jpype
    _gui["closed"] = True

    autosaves: List[str] = []

    def private_field(owner: Any, name: str) -> Any:
        field = owner.getClass().getDeclaredField(name)
        field.setAccessible(True)
        return field.get(owner)

    def forget_changes() -> None:
        # NetLogo autosaves a modified model (Python changing a slider is enough):
        # NetLogo 6 next to the model file, NetLogo 7 in ~/.nlogo, and NetLogo 7
        # offers to recover it next time.  Stop the autosave timer, remember this
        # session's autosave file, and mark the model as saved.
        monitor = app.dirtyMonitor()
        try:
            private_field(monitor, "dirtyTimer").cancel()          # NetLogo 7
        except Exception:
            pass
        for name in ("lastAutoSaveFile", "priorTempFile"):        # NetLogo 7 / 6
            try:
                option = private_field(monitor, name)
                if option is not None and option.isDefined():
                    autosaves.append(str(option.get()))
            except Exception:
                pass
        path = app.workspace().getModelPath()
        if path is not None:
            event_class = jpype.JClass("org.nlogo.window.Events$ModelSavedEvent")
            try:
                event = event_class(path, False)                   # NetLogo 7
            except TypeError:
                event = event_class(path)                          # NetLogo 6
            monitor.handle(event)

    def dispose_windows() -> None:
        for window in jpype.JClass("java.awt.Window").getWindows():
            window.dispose()

    for step in (lambda: run_on_edt(forget_changes) if hasattr(app, "dirtyMonitor") else None,
                 lambda: run_on_edt(app.frame().dispose),
                 lambda: app.workspace().dispose(),
                 lambda: run_on_edt(dispose_windows),
                 lambda: jpype.JClass("javafx.application.Platform").exit()):
        try:
            step()
        except Exception:                  # e.g. NetLogo 6 has no dirtyMonitor nor JavaFX
            pass
    for path in autosaves:
        try:
            os.remove(path)
        except OSError:
            pass
