# Sessions and NetLogo code

## Opening a model

```python
from netlogopy import NetLogo

nl = NetLogo()                                   # bundled model, headless
nl = NetLogo("my_model.nlogo", gui=True)         # your model, in the window
nl = NetLogo("my_model.nlogo", setup=True)       # run its setup right away
nl = NetLogo(netlogo_home="C:/Program Files/NetLogo 6.4.0", jvm_args=["-Xmx8g"])

nl.open_model("other.nlogo")                     # switch model
with NetLogo("model.nlogo") as nl:               # closed at the end of the block
    ...
```

- One NetLogo installation (one JVM) per Python process.
- One NetLogo window per process, and any number of headless sessions. Each
  session can be used from its own thread.
- Closing a session in the window closes the window without saving the model.
- Closing the window by hand, or *File > Quit*, closes the session: the next
  call raises `NetLogoError`, and the Python script goes on.
- A session never writes the model file, and NetLogo does not autosave the
  model of a session; *File > Save* in the window saves it when you ask.
- `NETLOGOPY_HEADLESS=1` turns every window off.
- NetLogo 7 asks to resize the widgets of models saved by NetLogo 6 when it
  opens them in its window; netlogopy answers "Resize and adjust positions".
- At its first window on a computer, NetLogo 7 asks whether it may send
  anonymous usage statistics ("Data Consent"). The answer is yours: the script
  waits for it, and says so. Where nobody can click (a server, continuous
  integration), the script `tools/netlogo_no_statistics.py` of the repository
  records "No" beforehand.

## Commands and reporters

```python
nl.command("crt 10 [ setxy random-xcor random-ycor ]")
nl.command("ask turtles [ fd 1 ]", "tick")        # several commands
nl.report("count turtles")                        # 10.0
nl.report(["count turtles", "ticks"])             # several reporters, one call
```

NetLogo code is compiled once and the compiled procedure is reused: a repeated
call takes a few hundredths of a millisecond ([measurements](../why.md#speed-of-a-call)).

## Values

| NetLogo value             | Python value                        |
|---------------------------|-------------------------------------|
| number                    | `float`                             |
| string                    | `str`                               |
| boolean                   | `bool`                              |
| list                      | `list` (converted recursively)      |
| turtle / patch / link     | `Turtle` / `Patch` / `Link`         |
| agentset                  | `list` of agents                    |
| `nobody`, a dead agent    | `None`                              |
| anything else             | `str` (NetLogo's printed form)      |

Python values passed to netlogopy are converted the other way by
`to_netlogo()`: `None` becomes `nobody`, strings are quoted, lists become
NetLogo lists, agents become `(turtle 3)`. To pass NetLogo code instead of a
value, wrap it in `Code`:

```python
from netlogopy import Code
nl.create_turtles(100, xcor=Code("random-xcor"), ycor=Code("random-ycor"))
```

## Errors

```python
from netlogopy import NetLogoCompileError, NetLogoRuntimeError

try:
    nl.command("ask turtle 999 [ fd 1 ]")
except NetLogoRuntimeError as error:
    print(error.message)     # ASK expected input to be an agent ... but got NOBODY
    print(error.source)      # ask turtle 999 [ fd 1 ]
    print(error.context)     # error while observer running ASK (the agent, the primitive,
                             # the calling procedures; None when NetLogo gives none)
```

`NetLogoCompileError` is raised for code that does not compile (syntax error,
unknown name), `NetLogoRuntimeError` for code that fails while running. Both
derive from `NetLogoError`, and work the same in the window and headless.

## NetLogo primitives as methods

Most NetLogo primitives that are useful from Python have a method: choosing
agents (`one_of`, `n_of`, `max_one_of`, `with_max`...), NetLogo's random
numbers (`random_normal`, `random_poisson`...), colors (`scale_color`,
`extract_rgb`...), NetLogo's file primitives (`file_open`, `file_read`...), the
timer, the mouse and the user dialogs. The full list is in the
[API reference](../api/index.md).

The primitives without a method of their own (maths, lists, strings, control
flow, HubNet) are the ones Python already has; they are available in any code
passed to `command()` and `report()`.
