"""Exceptions raised by netlogopy."""

from typing import Optional

__all__ = [
    "NetLogoError",
    "NetLogoNotFoundError",
    "NetLogoCompileError",
    "NetLogoRuntimeError",
]


class NetLogoError(Exception):
    """Base class of every error raised by netlogopy.

    ``source`` holds the NetLogo code that failed (when there is one) and
    ``context`` what NetLogo says about where a runtime error happened: the
    agent, the primitive and the calling procedures (when it says so).
    """

    def __init__(self, message: str, source: Optional[str] = None, context: Optional[str] = None):
        self.message = message
        self.source = source
        self.context = context
        if context:
            message += "".join(f"\n  {line}" for line in context.splitlines())
        if source:
            shown = source if len(source) <= 300 else source[:297] + "..."
            message = f"{message}\n  NetLogo code: {shown}"
        super().__init__(message)


class NetLogoNotFoundError(NetLogoError):
    """NetLogo, or a Java runtime able to run it, could not be found."""


class NetLogoCompileError(NetLogoError):
    """NetLogo could not compile the code (syntax error, unknown name, ...)."""


class NetLogoRuntimeError(NetLogoError):
    """The code compiled but failed while running (e.g. ``ask nobody``)."""
