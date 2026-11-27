"""Conversions between Python values and NetLogo values.

* :func:`to_netlogo` turns a Python value into NetLogo source code
  (``"car"`` -> ``"\\"car\\""``, ``[1, True]`` -> ``"[1 true]"``, a Turtle -> ``"(turtle 3)"``).
* :func:`from_java` turns what NetLogo reports into Python values:

  ==========================  ====================================
  NetLogo                     Python
  ==========================  ====================================
  number                      ``float``
  string                      ``str``
  boolean                     ``bool``
  list                        ``list`` (recursively converted)
  turtle / patch / link       :class:`Turtle` / :class:`Patch` / :class:`Link`
  agentset                    ``list`` of agents
  nobody (or a dead agent)    ``None``
  anything else               ``str`` (NetLogo's printed form)
  ==========================  ====================================
"""

import math
import numbers
from types import SimpleNamespace
from typing import Any, Optional

__all__ = ["Code", "to_netlogo", "from_java"]


class Code(str):
    """Raw NetLogo code, inserted as-is instead of being quoted as a string.

    >>> nl.create_turtles(50, xcor=Code("random-xcor"), ycor=Code("random-ycor"))
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return f"Code({str(self)!r})"


def _c(code: str) -> str:
    """``code`` ready to be followed by a closing bracket.

    A NetLogo comment (``;``) runs to the end of the line, so code that holds
    one gets a new line: the comment must not swallow the bracket.
    """
    return code + "\n" if ";" in code else code


def _quote(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return '"' + (text.replace("\\", "\\\\").replace('"', '\\"')
                  .replace("\n", "\\n").replace("\t", "\\t")) + '"'


def _is_literal(value: Any) -> bool:
    """True for values allowed inside a NetLogo list literal ``[...]``."""
    if isinstance(value, Code):
        return False
    if isinstance(value, (bool, str, numbers.Real)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_literal(item) for item in value)
    return False


def to_netlogo(value: Any) -> str:
    """Return the NetLogo source code that evaluates to ``value``.

    Supports None (``nobody``), booleans, numbers, strings, nested
    lists/tuples/sets/ranges, numpy values and arrays, agents
    (:class:`Turtle`, :class:`Patch`, :class:`Link`) and :class:`Code`.
    """
    if type(value).__module__ == "numpy" and hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, Code):
        return str(value)
    if value is None:
        return "nobody"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, numbers.Integral):
        if abs(int(value)) > 2 ** 53:      # NetLogo numbers are doubles: no exact integer beyond that
            try:
                return repr(float(value))
            except OverflowError:
                raise ValueError(f"{value!r} is too large for a NetLogo number") from None
        return str(int(value))
    if isinstance(value, numbers.Real):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            raise ValueError(f"NetLogo numbers must be finite, got {value!r}")
        return repr(number)
    if isinstance(value, str):
        return _quote(value)
    to_nl = getattr(value, "to_netlogo", None)
    if callable(to_nl):
        return to_nl()
    if isinstance(value, dict):
        raise TypeError("NetLogo has no dictionary type: pass a list of [key value] "
                        "pairs instead (or use the table extension).")
    if isinstance(value, (list, tuple, set, frozenset, range)) or _is_iterable(value):
        items = list(value)
        if not items:
            return "[]"
        if all(_is_literal(item) for item in items):
            return "[" + " ".join(to_netlogo(item) for item in items) + "]"
        codes = [to_netlogo(item) for item in items]
        if len(codes) <= _PIECE:
            return "(list " + " ".join(codes) + ")"
        # NetLogo compiles a list expression into one Java method, which has a
        # maximum size: a long list is built in pieces, each by its own reporter,
        # and `sentence` joins the pieces (the items themselves are not flattened).
        pieces = ["(runresult [ -> (list " + " ".join(codes[start:start + _PIECE]) + ") ])"
                  for start in range(0, len(codes), _PIECE)]
        return "(sentence " + " ".join(pieces) + ")"
    raise TypeError(f"Cannot convert {type(value).__name__} to a NetLogo value")


_PIECE = 200        # expressions per piece of a long list (agents, NetLogo code: not plain values)


def _is_iterable(value: Any) -> bool:
    if isinstance(value, (str, bytes, bytearray)):
        return False
    try:
        iter(value)
    except TypeError:
        return False
    return True


# ─── Java -> Python ────────────────────────────────────────────────────────────

_types: Optional[SimpleNamespace] = None


def _java_types() -> SimpleNamespace:
    global _types
    if _types is None:
        import jpype
        jclass = jpype.JClass
        _types = SimpleNamespace(
            Double=jclass("java.lang.Double"),
            Boolean=jclass("java.lang.Boolean"),
            String=jclass("java.lang.String"),
            Number=jclass("java.lang.Number"),
            LogoList=jclass("org.nlogo.core.LogoList"),
            Turtle=jclass("org.nlogo.api.Turtle"),
            Patch=jclass("org.nlogo.api.Patch"),
            Link=jclass("org.nlogo.api.Link"),
            AgentSet=jclass("org.nlogo.api.AgentSet"),
            Nobody=jclass("org.nlogo.core.Nobody$"),
            Dump=jclass("org.nlogo.api.Dump"),
        )
    return _types


def from_java(obj: Any, nl: Any = None) -> Any:
    """Convert an object reported by NetLogo into a Python value.

    ``nl`` is the :class:`~netlogopy.NetLogo` session the agents belong to.
    """
    if obj is None:
        return None
    types = _java_types()
    if isinstance(obj, types.Double):
        return float(obj)
    if isinstance(obj, types.String):
        return str(obj)
    if isinstance(obj, types.Boolean):
        return bool(obj.booleanValue())
    if isinstance(obj, types.LogoList):
        return [from_java(obj.get(i), nl) for i in range(obj.size())]
    if isinstance(obj, (types.Turtle, types.Patch, types.Link)):
        return _agent(obj, nl, types)
    if isinstance(obj, types.AgentSet):
        return [_agent(agent, nl, types) for agent in obj.agents()]
    if isinstance(obj, types.Nobody):
        return None
    if isinstance(obj, types.Number):
        return float(obj.doubleValue())
    return str(types.Dump.logoObject(obj))


def _agent(obj: Any, nl: Any, types: SimpleNamespace) -> Any:
    from .agents import Link, Patch, Turtle
    if isinstance(obj, types.Patch):
        return Patch(nl, int(obj.pxcor()), int(obj.pycor()))
    if int(obj.id()) < 0:                  # a turtle or link that died
        return None
    if isinstance(obj, types.Turtle):
        return Turtle(nl, int(obj.id()))
    breed = str(obj.getBreed().printName()).lower()
    singular = nl._link_singular(breed, obj.getBreed()) if nl is not None else None
    return Link(nl, int(obj.end1().id()), int(obj.end2().id()), breed=breed,
                directed=bool(obj.isDirectedLink()), singular=singular)

