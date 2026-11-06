"""Shared test helpers: a fake NetLogo that records what netlogopy sends to it.

These tests do not need NetLogo or Java.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # test the working copy, not an installed netlogopy

import netlogopy.netlogopy as nlp  # noqa: E402


class FakeNetLogo:
    """Stands in for the Java side of a NetLogo instance.

    `responses` maps a reporter prefix to the text NetLogo would return
    (or to a function of the reporter). Unknown reporters return "0.0",
    which is what base.nls actions report when they succeed.
    """

    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.commands = []
        self.reports = []
        self.globals = {}
        self.next_who = 0
        self.ticks = 0
        self.model = None
        self.closed = False

    # bridge interface -----------------------------------------------------------
    def open_model(self, path):
        self.model = path

    def command(self, command):
        self.commands.append(command)
        match = re.match(r"set (\S+) (.+)$", command)
        if match:
            self.globals[match.group(1)] = match.group(2)
        if command == "tick":
            self.ticks += 1

    def report(self, reporter):
        self.reports.append(reporter)
        for prefix, result in self.responses.items():
            if reporter.startswith(prefix):
                return result(reporter) if callable(result) else result
        if reporter in self.globals:
            return self.globals[reporter]
        if reporter.startswith("create-pyturtle-xyid"):
            who = self.next_who
            self.next_who += 1
            return "{}.0".format(who)
        if reporter.startswith("create-pyturtles-xyid"):
            coords = nlp._parse_nl_value(reporter[len("create-pyturtles-xyid "):])[0]
            ids = list(range(self.next_who, self.next_who + len(coords)))
            self.next_who += len(coords)
            return "[{}]".format(", ".join("{}.0".format(who) for who in ids))
        if reporter == "[ (list who xcor ycor) ] of pyturtles":
            mine = [t for t in nlp.list_pyturtle
                    if getattr(t.n, "_target", t.n) is self]  # t.n may be a wrapper
            rows = ["[{}.0, 20.0, 20.0]".format(t.id) for t in mine]
            return "[{}]".format(", ".join(rows))
        if reporter.startswith("create-street-ft"):
            ends = reporter[len("create-street-ft ["):].split()[:2]
            return "{}_{}".format(*ends)
        if reporter.startswith("getxyturtle"):
            return "[20.0, 20.0]"
        if reporter.startswith("can_move_turtle"):
            return "true"
        if reporter.startswith(("in_radius_turtle", "turtles_here_turtle")):
            return "[]"
        if reporter == "ticks":
            return "{}.0".format(self.ticks)
        if reporter == "count pyturtles":
            return "{}.0".format(len(nlp.list_pyturtle))
        if reporter in ("world-width", "world-height"):
            return "61.0"
        return "0.0"

    def close_model(self):
        self.closed = True

    # helpers -------------------------------------------------------------------
    @property
    def last_report(self):
        return self.reports[-1]


@pytest.fixture(autouse=True)
def clean_registries():
    nlp.list_pyturtle.clear()
    nlp.list_street.clear()
    yield
    nlp.list_pyturtle.clear()
    nlp.list_street.clear()


@pytest.fixture
def n():
    return FakeNetLogo()
