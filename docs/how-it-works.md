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
repeated `command()` or `report()` takes a few hundredths of a millisecond
([measurements](why.md#speed-of-a-call)). Results are
converted from Java to Python values (numbers, strings, lists, agents).

## Details handled for you

- **Java version**: NetLogo 6.2 and older bundle Java 8, which JPype does not
  support; netlogopy then uses `JAVA_HOME`, the conda environment or another
  NetLogo's runtime.
- **NetLogo 7**: one model per headless workspace (a new workspace for each
  `open_model`), the `.nlogox` format and the widget-resize dialog answered.
- **The model file**: NetLogo does not autosave the model of a session, and its
  "Recover Autosave" question never comes up: the model file is not written
  unless you save it in the window.
- **Closing the window**: NetLogo would end the process (and Python with it);
  the session is closed instead and the script goes on.
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

## History

Versions 0.x of netlogopy were a layer of agent classes on top of [NL4Py](https://github.com/chathika/NL4Py)
(Gunaratne and Garibay, *NL4Py: Agent-based modeling in Python with parallelizable NetLogo workspaces*, SoftwareX 16, 2021, [doi:10.1016/j.softx.2021.100801](https://doi.org/10.1016/j.softx.2021.100801)), which started NetLogo behind a Java server, reached through Py4J,
and sent it commands. We thank its authors for the work the first versions
relied on. Version 1.0 is a new implementation on NetLogo's own Java API, in
the Python process, and no longer depends on NL4Py; scripts written for 0.x
keep working ([The 0.x API](guide/legacy.md)).
