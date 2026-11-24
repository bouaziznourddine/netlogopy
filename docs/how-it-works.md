# How it works

netlogopy starts a Java virtual machine inside the Python process with
[JPype](https://jpype.readthedocs.io), with NetLogo's jars on the classpath,
and calls NetLogo's own API:

- `org.nlogo.headless.HeadlessWorkspace` for headless sessions,
- `org.nlogo.app.App` for the NetLogo window.

```text
Python script ──> netlogopy ──JPype──> NetLogo (Java, same process)
                     │                   ├─ compiler
                     │                   ├─ world (turtles, patches, links)
                     └─ Turtle, Patch,   └─ window: view, widgets, plots
                        Link objects
```

There is no server, no socket and no port: a call is a Java method call. NetLogo
code is compiled once and the compiled procedure is kept in a cache, so a
repeated `command()` or `report()` takes about 0.1 to 0.3 ms. Results are
converted from Java to Python values (numbers, strings, lists, agents).

## Details handled for you

- **Java version**: NetLogo 6.2 and older bundle Java 8, which JPype does not
  support; netlogopy then uses `JAVA_HOME`, the conda environment or another
  NetLogo's runtime.
- **NetLogo 7**: one model per headless workspace (a new workspace for each
  `open_model`), the `.nlogox` format, the widget-resize dialog answered, and
  NetLogo's autosave discarded when the window closes.
- **Errors in the window**: commands run in the window are wrapped so that a
  runtime error comes back to Python as `NetLogoRuntimeError` instead of a
  NetLogo dialog.
- **Threads**: each session can be used from its own Python thread; window
  operations run on Java's event thread.
- **Exit**: sessions are closed at Python exit, and the JVM shuts down
  cleanly.

## Limits

- One NetLogo installation (one JVM) per Python process; one NetLogo window
  per process.
- No NetLogo window on macOS (AWT must own the main thread there); headless
  sessions work.
- NetLogo 3D is not supported.

## Why not nl4py

netlogopy 0.x used [nl4py](https://github.com/chathika/NL4Py), which runs
NetLogo in a separate Java server and talks to it through a socket. netlogopy
1.0 calls NetLogo directly: it is faster, has no server to start, and keeps
netlogopy under the MIT license (nl4py is GPL-3).
