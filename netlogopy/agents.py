"""Python handles on NetLogo agents: :class:`Turtle`, :class:`Patch` and :class:`Link`.

A handle only stores the agent's identity (who number, patch coordinates or
link end points).  Every attribute read or write goes to NetLogo, so handles
never hold stale values; using the handle of a dead agent raises
:class:`~netlogopy.NetLogoRuntimeError`.

A handle therefore means "the agent with this number".  NetLogo gives the who
numbers again after ``clear-all`` or ``clear-turtles`` (a ``setup`` usually
does it): a handle kept from before then designates the new turtle that got
its number.

Variables are read and written with ``agent.get(name)`` / ``agent.set(name, value)``,
``agent[name]`` / ``agent[name] = value``, or the properties of the built-in
variables (``turtle.color = 15``).  Python-friendly aliases are accepted for the
built-in names that are not valid Python identifiers: ``label_color``,
``plabel_color``, ``pen_mode``, ``pen_size``, ``tie_mode`` and ``hidden`` (``hidden?``);
a model variable spelled like an alias is that variable, not the alias.
"""

import copy
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Union

from .convert import Code, _c, to_netlogo

if TYPE_CHECKING:                          # pragma: no cover
    from .core import NetLogo

__all__ = ["Agent", "Turtle", "Patch", "Link", "variable_name", "assignments"]

_ALIASES = {
    "label_color": "label-color",
    "plabel_color": "plabel-color",
    "pen_mode": "pen-mode",
    "pen_size": "pen-size",
    "tie_mode": "tie-mode",
    "hidden": "hidden?",
}


def variable_name(name: str) -> str:
    """NetLogo name of a variable (``label_color`` -> ``label-color``)."""
    return _ALIASES.get(name, name)


def assignments(variables: Dict[str, Any], name: Callable[[str], str] = variable_name) -> str:
    """NetLogo ``set`` commands for a dict of variables (``name`` gives their NetLogo names)."""
    return " ".join(f"set {name(key)} {to_netlogo(value)}" for key, value in variables.items())


_MISSING: Any = object()                   # "no value given", where None is a value (nobody)


def _variable(name: str, doc: str, readonly: bool = False) -> property:
    def getter(self: "Agent") -> Any:
        return self.get(name)

    def setter(self: "Agent", value: Any) -> None:
        self.set(name, value)

    return property(getter, None if readonly else setter, doc=doc)


def _num(value: Any) -> str:
    return to_netlogo(value)


class Agent:
    """Base class of the agent handles."""

    __slots__ = ("nl",)
    kind = "agent"

    def __init__(self, nl: "NetLogo"):
        self.nl = nl

    # -- identity ------------------------------------------------------------------
    @property
    def ref(self) -> str:
        """NetLogo expression designating this agent (e.g. ``turtle 3``)."""
        raise NotImplementedError

    def to_netlogo(self) -> str:
        """NetLogo code designating this agent: :attr:`ref` between parentheses."""
        return f"({self.ref})"

    def _key(self) -> tuple:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Agent) and other.nl is self.nl
                and other._key() == self._key())

    def __hash__(self) -> int:
        return hash((id(self.nl),) + self._key())

    def __deepcopy__(self, memo: Dict[int, Any]) -> "Agent":
        # A handle is an identity: the copy designates the same agent of the same
        # session (which cannot be copied); only Python attributes are copied.
        clone = copy.copy(self)
        for name, value in getattr(clone, "__dict__", {}).items():
            clone.__dict__[name] = copy.deepcopy(value, memo)
        return clone

    # -- variables -----------------------------------------------------------------
    def get(self, variable: str) -> Any:
        """Value of one of the agent's variables (built-in or ``-own``).

        ``breed`` gives the name of the breed, in plural form.
        """
        if variable == "breed" and self.kind != "patch":
            return self.of("(word breed)")
        value = self.nl._fast_get(self, variable)
        if value is not self.nl._NO_VALUE:
            return value
        return self.nl.report(f"[{self.nl._variable_name(variable)}] of {self.to_netlogo()}")

    def set(self, variable: Any = _MISSING, value: Any = _MISSING, /, **variables: Any) -> "Agent":
        """Set variables: ``agent.set("energy", 5)`` or ``agent.set(color=15, size=2)``.

        Every keyword is the name of a variable, ``value`` and ``variable``
        included.  ``breed`` takes the plural name of a breed.
        """
        if (variable is _MISSING and isinstance(variables.get("variable"), str) and "value" in variables
                and not self.nl._declares("variable")):
            # set(variable="color", value=15): the keyword form of the two arguments
            variable, value = variables.pop("variable"), variables.pop("value")
        values: Dict[str, Any] = {}
        if variable is not _MISSING:
            if value is _MISSING:
                raise TypeError("set() needs a value: agent.set(name, value) or agent.set(name=value)")
            values[variable] = value
        values.update(variables)
        breed = values.get("breed")
        if isinstance(breed, str) and not isinstance(breed, Code) and self.kind == "turtle":
            del values["breed"]
            self.nl.command(f"ask {self.to_netlogo()} [ set breed {breed} ]")
        if values and not self.nl._fast_set(self, values):
            self.nl.command(f"ask {self.to_netlogo()} [ {assignments(values, self.nl._variable_name)} ]")
        return self

    def __getitem__(self, variable: str) -> Any:
        return self.get(variable)

    def __setitem__(self, variable: str, value: Any) -> None:
        self.set(variable, value)

    def get_many(self, variables: Sequence[str]) -> Dict[str, Any]:
        """Several variables at once, in one NetLogo call."""
        names = [variables] if isinstance(variables, str) else list(variables)
        values = self.nl.report(
            f"[(list {' '.join(self.nl._variable_name(v) for v in names)})] of {self.to_netlogo()}")
        return dict(zip(names, values))

    # -- code in the agent's context -----------------------------------------------
    def ask(self, *commands: str) -> "Agent":
        """Run NetLogo commands as this agent (``ask agent [ ... ]``)."""
        self.nl.command(f"ask {self.to_netlogo()} [\n" + "\n".join(commands) + "\n]")
        return self

    def of(self, reporter: str) -> Any:
        """Evaluate a NetLogo reporter as this agent (``[reporter] of agent``)."""
        return self.nl.report(f"[{_c(reporter)}] of {self.to_netlogo()}")

    @property
    def alive(self) -> bool:
        """False once the agent has died (patches are always alive)."""
        return bool(self.nl.report(f"{self.to_netlogo()} != nobody"))

    def watch(self) -> "Agent":
        """Highlight this agent in the view (observer ``watch``)."""
        self.nl.command(f"watch {self.to_netlogo()}")
        return self


# ─── Turtle ────────────────────────────────────────────────────────────────────

class Turtle(Agent):
    """A NetLogo turtle (of any breed), designated by its ``who`` number."""

    __slots__ = ("who",)
    kind = "turtle"

    def __init__(self, nl: "NetLogo", who: int):
        super().__init__(nl)
        self.who = int(who)

    @property
    def ref(self) -> str:
        """NetLogo expression designating this turtle (``turtle 3``)."""
        return f"turtle {self.who}"

    def _key(self) -> tuple:
        return ("turtle", self.who)

    def __repr__(self) -> str:
        return f"Turtle({self.who})"

    # built-in variables
    xcor = _variable("xcor", "x coordinate.")
    ycor = _variable("ycor", "y coordinate.")
    heading = _variable("heading", "Heading in degrees (0 = north, 90 = east).")
    color = _variable("color", "Color (NetLogo color number or RGB(A) list).")
    size = _variable("size", "Size of the shape.")
    shape = _variable("shape", "Shape name (e.g. 'car').")
    label = _variable("label", "Text shown next to the turtle.")
    label_color = _variable("label-color", "Color of the label.")
    hidden = _variable("hidden?", "True when the turtle is hidden.")
    pen_mode = _variable("pen-mode", "'up', 'down' or 'erase'.")
    pen_size = _variable("pen-size", "Width of the pen line.")
    dx = _variable("dx", "x increment of one step forward.", readonly=True)
    dy = _variable("dy", "y increment of one step forward.", readonly=True)

    @property
    def breed(self) -> str:
        """Breed name in plural form (``'turtles'`` for unbreeded turtles); assign it to change the breed."""
        return self.of("(word breed)")

    @breed.setter
    def breed(self, breed: str) -> None:
        self.set_breed(breed)

    def set_breed(self, breed: str) -> "Turtle":
        """Change the breed (plural form, e.g. ``'wolves'``)."""
        return self.ask(f"set breed {breed}")

    @property
    def xy(self) -> List[float]:
        """``[xcor, ycor]`` in one call."""
        return self.of("(list xcor ycor)")

    # movement
    def forward(self, distance: float = 1) -> "Turtle":
        """Move forward (``fd``)."""
        return self.ask(f"fd {_num(distance)}")

    def back(self, distance: float = 1) -> "Turtle":
        """Move backward (``bk``)."""
        return self.ask(f"bk {_num(distance)}")

    def right(self, angle: float) -> "Turtle":
        """Turn right by ``angle`` degrees (``rt``)."""
        return self.ask(f"rt {_num(angle)}")

    def left(self, angle: float) -> "Turtle":
        """Turn left by ``angle`` degrees (``lt``)."""
        return self.ask(f"lt {_num(angle)}")

    fd, bk, rt, lt = forward, back, right, left

    def jump(self, distance: float) -> "Turtle":
        """Move ``distance`` in one jump (no pen trace in between)."""
        return self.ask(f"jump {_num(distance)}")

    def setxy(self, x: float, y: float) -> "Turtle":
        """Move to the point (x, y) (``setxy``)."""
        return self.ask(f"setxy {_num(x)} {_num(y)}")

    def move_to(self, agent: Agent) -> "Turtle":
        """Move to the position of a turtle or patch (``move-to``)."""
        return self.ask(f"move-to {self.nl._ref(agent)}")

    def face(self, agent: Agent) -> "Turtle":
        """Turn towards a turtle or a patch (``face``)."""
        return self.ask(f"face {self.nl._ref(agent)}")

    def facexy(self, x: float, y: float) -> "Turtle":
        """Turn towards the point (x, y) (``facexy``)."""
        return self.ask(f"facexy {_num(x)} {_num(y)}")

    def home(self) -> "Turtle":
        """Go to (0, 0); the heading does not change."""
        return self.ask("home")

    def can_move(self, distance: float = 1) -> bool:
        """``can-move?``: False when the move would leave a non-wrapping world."""
        return bool(self.of(f"can-move? {_num(distance)}"))

    def die(self) -> None:
        """Kill this turtle (``die``)."""
        self.ask("die")

    # appearance and pen
    def hide_turtle(self) -> "Turtle":
        """Make the turtle invisible (``hide-turtle``)."""
        return self.ask("hide-turtle")

    def show_turtle(self) -> "Turtle":
        """Make the turtle visible again (``show-turtle``)."""
        return self.ask("show-turtle")

    ht, st = hide_turtle, show_turtle

    def pen_down(self) -> "Turtle":
        """Put the pen down: the turtle draws a line when it moves (``pen-down``)."""
        return self.ask("pen-down")

    def pen_up(self) -> "Turtle":
        """Lift the pen: the turtle stops drawing (``pen-up``)."""
        return self.ask("pen-up")

    def pen_erase(self) -> "Turtle":
        """Make the turtle erase the lines it moves over (``pen-erase``)."""
        return self.ask("pen-erase")

    pd, pu, pe = pen_down, pen_up, pen_erase

    def stamp(self) -> "Turtle":
        """Leave an image of the turtle in the drawing."""
        return self.ask("stamp")

    def stamp_erase(self) -> "Turtle":
        """Erase the drawing under the turtle's shape (``stamp-erase``)."""
        return self.ask("stamp-erase")

    # geometry
    def distance(self, agent: Agent) -> float:
        """Distance to a turtle or a patch (``distance``)."""
        return self.of(f"distance {self.nl._ref(agent)}")

    def distancexy(self, x: float, y: float) -> float:
        """Distance to the point (x, y) (``distancexy``)."""
        return self.of(f"distancexy {_num(x)} {_num(y)}")

    def towards(self, agent: Agent) -> float:
        """Heading pointing to ``agent``."""
        return self.of(f"towards {self.nl._ref(agent)}")

    def towardsxy(self, x: float, y: float) -> float:
        """Heading pointing to the point (x, y) (``towardsxy``)."""
        return self.of(f"towardsxy {_num(x)} {_num(y)}")

    # patches
    def patch_here(self) -> "Patch":
        """The patch under the turtle (``patch-here``)."""
        return self.of("patch-here")

    def patch_ahead(self, distance: float) -> Optional["Patch"]:
        """The patch ``distance`` ahead of the turtle; None outside the world (``patch-ahead``)."""
        return self.of(f"patch-ahead {_num(distance)}")

    def patch_at(self, dx: float, dy: float) -> Optional["Patch"]:
        """The patch at (dx, dy) from the turtle; None outside the world (``patch-at``)."""
        return self.of(f"patch-at {_num(dx)} {_num(dy)}")

    def patch_right_and_ahead(self, angle: float, distance: float) -> Optional["Patch"]:
        """The patch ``distance`` away, ``angle`` degrees to the right of the heading; None outside the world."""
        return self.of(f"patch-right-and-ahead {_num(angle)} {_num(distance)}")

    def patch_left_and_ahead(self, angle: float, distance: float) -> Optional["Patch"]:
        """The patch ``distance`` away, ``angle`` degrees to the left of the heading; None outside the world."""
        return self.of(f"patch-left-and-ahead {_num(angle)} {_num(distance)}")

    def neighbors(self) -> List["Patch"]:
        """The 8 patches around the turtle's patch."""
        return self.of("sort neighbors")

    def neighbors4(self) -> List["Patch"]:
        """The 4 patches (north, east, south, west) around the turtle's patch."""
        return self.of("sort neighbors4")

    # other agents
    def turtles_here(self, breed: str = "turtles") -> List["Turtle"]:
        """Turtles on the same patch, this one included (``turtles-here``)."""
        return self.of(f"sort {breed}-here")

    def in_radius(self, radius: float, agents: Union[str, Agent, Sequence[Agent]] = "turtles",
                  other: bool = False) -> List[Agent]:
        """Agents of ``agents`` within ``radius`` (this turtle included unless ``other``).

        ``agents`` is NetLogo code (``"turtles"``, ``"patches"``, a breed...),
        an agent or a list of agents.
        """
        return self.of(f"sort {'other ' if other else ''}{self.nl._set(agents)} in-radius {_num(radius)}")

    def in_cone(self, radius: float, angle: float, agents: Union[str, Agent, Sequence[Agent]] = "turtles",
                other: bool = False) -> List[Agent]:
        """Agents in the vision cone of ``angle`` degrees and depth ``radius``."""
        return self.of(f"sort {'other ' if other else ''}{self.nl._set(agents)} "
                       f"in-cone {_num(radius)} {_num(angle)}")

    def hatch(self, count: int = 1, breed: Optional[str] = None,
              variables: Optional[Dict[str, Any]] = None, **kwargs: Any) -> List["Turtle"]:
        """Create ``count`` copies of this turtle; returns the new turtles."""
        count = int(count)
        if count <= 0:
            return []
        values = assignments({**(variables or {}), **kwargs}, self.nl._variable_name)
        if breed == "turtles":             # no hatch-turtles primitive
            primitive, values = "hatch", f"set breed turtles {values}"
        else:
            primitive = f"hatch-{breed}" if breed else "hatch"
        return self.nl._create(f"ask {self.to_netlogo()} [ {primitive} {count} [ {values} ] ]")

    # links
    def create_link_with(self, other: "Turtle", breed: Optional[str] = None, **variables: Any) -> "Link":
        """Undirected link to ``other``."""
        return self.nl.create_link(self, other, directed=False, breed=breed, **variables)

    def create_link_to(self, other: "Turtle", breed: Optional[str] = None, **variables: Any) -> "Link":
        """Directed link from this turtle to ``other``."""
        return self.nl.create_link(self, other, directed=True, breed=breed, **variables)

    def create_link_from(self, other: "Turtle", breed: Optional[str] = None, **variables: Any) -> "Link":
        """Directed link from ``other`` to this turtle."""
        return self.nl.create_link(other, self, directed=True, breed=breed, **variables)

    def _link_query(self, unbreeded: str, breeded: str, breed: Optional[str]) -> Any:
        if breed is None or breed == "links":
            return self.of(unbreeded)
        singular = self.nl._link_singular(breed)
        return self.of(breeded.format(singular=singular, plural=breed))

    def link_neighbors(self, breed: Optional[str] = None) -> List["Turtle"]:
        """Turtles linked to this one."""
        return self._link_query("sort link-neighbors", "sort {singular}-neighbors", breed)

    def in_link_neighbors(self, breed: Optional[str] = None) -> List["Turtle"]:
        """Turtles with a link pointing to this one."""
        return self._link_query("sort in-link-neighbors", "sort in-{singular}-neighbors", breed)

    def out_link_neighbors(self, breed: Optional[str] = None) -> List["Turtle"]:
        """Turtles this one points to."""
        return self._link_query("sort out-link-neighbors", "sort out-{singular}-neighbors", breed)

    def my_links(self, breed: Optional[str] = None) -> List["Link"]:
        """Links connected to this turtle, optionally of one link breed (``my-links``)."""
        return self._link_query("sort my-links", "sort my-{plural}", breed)

    def my_in_links(self, breed: Optional[str] = None) -> List["Link"]:
        """Links arriving at this turtle, optionally of one link breed (``my-in-links``)."""
        return self._link_query("sort my-in-links", "sort my-in-{plural}", breed)

    def my_out_links(self, breed: Optional[str] = None) -> List["Link"]:
        """Links leaving this turtle, optionally of one link breed (``my-out-links``)."""
        return self._link_query("sort my-out-links", "sort my-out-{plural}", breed)

    def link_with(self, other: "Turtle", breed: Optional[str] = None) -> Optional["Link"]:
        """The link between this turtle and ``other`` (None if there is none)."""
        target = self.nl._ref(other)
        return self._link_query(f"link-with {target}", f"{{singular}}-with {target}", breed)

    def create_links_with(self, others: Sequence["Turtle"], breed: Optional[str] = None,
                          **variables: Any) -> List["Link"]:
        """Undirected links to several turtles."""
        return [self.create_link_with(other, breed, **variables) for other in others]

    def create_links_to(self, others: Sequence["Turtle"], breed: Optional[str] = None,
                        **variables: Any) -> List["Link"]:
        """Directed links from this turtle to several turtles."""
        return [self.create_link_to(other, breed, **variables) for other in others]

    def create_links_from(self, others: Sequence["Turtle"], breed: Optional[str] = None,
                          **variables: Any) -> List["Link"]:
        """Directed links from several turtles to this turtle."""
        return [self.create_link_from(other, breed, **variables) for other in others]

    def is_link_neighbor(self, other: "Turtle", breed: Optional[str] = None) -> bool:
        """True if a link joins this turtle and ``other`` (``link-neighbor?``)."""
        target = self.nl._ref(other)
        return bool(self._link_query(f"link-neighbor? {target}", f"{{singular}}-neighbor? {target}", breed))

    def is_in_link_neighbor(self, other: "Turtle", breed: Optional[str] = None) -> bool:
        """True if a link comes from ``other`` to this turtle (``in-link-neighbor?``)."""
        target = self.nl._ref(other)
        return bool(self._link_query(f"in-link-neighbor? {target}", f"in-{{singular}}-neighbor? {target}", breed))

    def is_out_link_neighbor(self, other: "Turtle", breed: Optional[str] = None) -> bool:
        """True if a link goes from this turtle to ``other`` (``out-link-neighbor?``)."""
        target = self.nl._ref(other)
        return bool(self._link_query(f"out-link-neighbor? {target}", f"out-{{singular}}-neighbor? {target}", breed))

    def in_link_from(self, other: "Turtle", breed: Optional[str] = None) -> Optional["Link"]:
        """The link coming from ``other`` to this turtle (None if there is none)."""
        target = self.nl._ref(other)
        return self._link_query(f"in-link-from {target}", f"in-{{singular}}-from {target}", breed)

    def out_link_to(self, other: "Turtle", breed: Optional[str] = None) -> Optional["Link"]:
        """The link going from this turtle to ``other`` (None if there is none)."""
        target = self.nl._ref(other)
        return self._link_query(f"out-link-to {target}", f"out-{{singular}}-to {target}", breed)

    # gradients
    def uphill(self, patch_variable: str) -> "Turtle":
        """Move to the neighbouring patch (8 neighbours) with the highest value."""
        self.nl.command(f"ask {self.to_netlogo()} [ uphill {self.nl._variable_name(patch_variable)} ]")
        return self

    def uphill4(self, patch_variable: str) -> "Turtle":
        """Move to the neighbouring patch (4 neighbours) with the highest value."""
        self.nl.command(f"ask {self.to_netlogo()} [ uphill4 {self.nl._variable_name(patch_variable)} ]")
        return self

    def downhill(self, patch_variable: str) -> "Turtle":
        """Move to the neighbouring patch (8 neighbours) with the lowest value."""
        self.nl.command(f"ask {self.to_netlogo()} [ downhill {self.nl._variable_name(patch_variable)} ]")
        return self

    def downhill4(self, patch_variable: str) -> "Turtle":
        """Move to the neighbouring patch (4 neighbours) with the lowest value."""
        self.nl.command(f"ask {self.to_netlogo()} [ downhill4 {self.nl._variable_name(patch_variable)} ]")
        return self

    def turtles_at(self, dx: float, dy: float, breed: str = "turtles") -> List["Turtle"]:
        """Turtles on the patch at (dx, dy) from this turtle."""
        return self.of(f"sort {breed}-at {_num(dx)} {_num(dy)}")

    def patch_at_heading_and_distance(self, heading: float, distance: float) -> Optional["Patch"]:
        """The patch ``distance`` away in direction ``heading``; None outside the world."""
        return self.of(f"patch-at-heading-and-distance {_num(heading)} {_num(distance)}")

    # observer perspective
    def follow(self) -> "Turtle":
        """Make the observer follow this turtle."""
        self.nl.command(f"follow {self.to_netlogo()}")
        return self

    def ride(self) -> "Turtle":
        """Make the observer ride this turtle."""
        self.nl.command(f"ride {self.to_netlogo()}")
        return self


# ─── Patch ─────────────────────────────────────────────────────────────────────

class Patch(Agent):
    """A NetLogo patch, designated by its integer coordinates."""

    __slots__ = ("pxcor", "pycor")
    kind = "patch"

    def __init__(self, nl: "NetLogo", pxcor: int, pycor: int):
        super().__init__(nl)
        self.pxcor = int(pxcor)
        self.pycor = int(pycor)

    @property
    def ref(self) -> str:
        """NetLogo expression designating this patch (``patch 2 -1``)."""
        return f"patch {self.pxcor} {self.pycor}"

    def _key(self) -> tuple:
        return ("patch", self.pxcor, self.pycor)

    def __repr__(self) -> str:
        return f"Patch({self.pxcor}, {self.pycor})"

    pcolor = _variable("pcolor", "Color of the patch.")
    plabel = _variable("plabel", "Text shown on the patch.")
    plabel_color = _variable("plabel-color", "Color of the patch label.")

    def neighbors(self) -> List["Patch"]:
        """The 8 patches around this patch."""
        return self.of("sort neighbors")

    def neighbors4(self) -> List["Patch"]:
        """The 4 patches (north, east, south, west) around this patch."""
        return self.of("sort neighbors4")

    def turtles_here(self, breed: str = "turtles") -> List[Turtle]:
        """Turtles standing on this patch, optionally of one breed (``turtles-here``)."""
        return self.of(f"sort {breed}-here")

    def patch_at(self, dx: int, dy: int) -> Optional["Patch"]:
        """The patch at (dx, dy) from this patch; None outside the world (``patch-at``)."""
        return self.of(f"patch-at {_num(dx)} {_num(dy)}")

    def distance(self, agent: Agent) -> float:
        """Distance from the center of this patch to a turtle or a patch (``distance``)."""
        return self.of(f"distance {self.nl._ref(agent)}")

    def distancexy(self, x: float, y: float) -> float:
        """Distance from the center of this patch to the point (x, y) (``distancexy``)."""
        return self.of(f"distancexy {_num(x)} {_num(y)}")

    def in_radius(self, radius: float, agents: Union[str, Agent, Sequence[Agent]] = "patches",
                  other: bool = False) -> List[Agent]:
        """Agents of ``agents`` within ``radius`` (this patch included unless ``other``)."""
        return self.of(f"sort {'other ' if other else ''}{self.nl._set(agents)} in-radius {_num(radius)}")

    def turtles_at(self, dx: int, dy: int, breed: str = "turtles") -> List[Turtle]:
        """Turtles on the patch at (dx, dy) from this patch."""
        return self.of(f"sort {breed}-at {_num(dx)} {_num(dy)}")

    def patch_at_heading_and_distance(self, heading: float, distance: float) -> Optional["Patch"]:
        """The patch ``distance`` away in direction ``heading``; None outside the world."""
        return self.of(f"patch-at-heading-and-distance {_num(heading)} {_num(distance)}")

    def sprout(self, count: int = 1, breed: Optional[str] = None,
               variables: Optional[Dict[str, Any]] = None, **kwargs: Any) -> List[Turtle]:
        """Create ``count`` turtles on this patch; returns them."""
        count = int(count)
        if count <= 0:
            return []
        primitive = f"sprout-{breed}" if breed and breed != "turtles" else "sprout"
        values = assignments({**(variables or {}), **kwargs}, self.nl._variable_name)
        return self.nl._create(f"ask {self.to_netlogo()} [ {primitive} {count} [ {values} ] ]")


# ─── Link ──────────────────────────────────────────────────────────────────────

class Link(Agent):
    """A NetLogo link, designated by its two end turtles and its breed."""

    __slots__ = ("end1_who", "end2_who", "breed", "directed", "_singular")
    kind = "link"

    def __init__(self, nl: "NetLogo", end1: int, end2: int, breed: str = "links",
                 directed: bool = False, singular: Optional[str] = None):
        super().__init__(nl)
        self.end1_who = int(end1)
        self.end2_who = int(end2)
        self.breed = breed
        self.directed = bool(directed)
        self._singular = singular or ("link" if breed == "links" else None)

    @property
    def ref(self) -> str:
        """NetLogo expression designating this link (``link 0 1``, or ``street 0 1`` for a breed)."""
        if self._singular is None:
            self._singular = self.nl._link_singular(self.breed)
        return f"{self._singular} {self.end1_who} {self.end2_who}"

    def _key(self) -> tuple:
        ends = (self.end1_who, self.end2_who)
        # An undirected link is the same link whichever end is named first.
        return ("link", self.breed) + (ends if self.directed else tuple(sorted(ends)))

    def __repr__(self) -> str:
        arrow = "->" if self.directed else "--"
        breed = "" if self.breed == "links" else f", breed={self.breed!r}"
        return f"Link({self.end1_who} {arrow} {self.end2_who}{breed})"

    @property
    def end1(self) -> Turtle:
        """The first end of the link (the source of a directed link)."""
        return Turtle(self.nl, self.end1_who)

    @property
    def end2(self) -> Turtle:
        """The second end of the link (the destination of a directed link)."""
        return Turtle(self.nl, self.end2_who)

    def both_ends(self) -> List[Turtle]:
        """The two end turtles: ``[end1, end2]``."""
        return [self.end1, self.end2]

    def other_end(self, turtle: Union[Turtle, int]) -> Turtle:
        """The end that is not ``turtle`` (ValueError when ``turtle`` is not an end of the link)."""
        who = turtle.who if isinstance(turtle, Turtle) else int(turtle)
        if who == self.end1_who:
            return self.end2
        if who == self.end2_who:
            return self.end1
        raise ValueError(f"turtle {who} is not an end of {self!r}")

    color = _variable("color", "Color of the link.")
    label = _variable("label", "Text shown on the link.")
    label_color = _variable("label-color", "Color of the label.")
    thickness = _variable("thickness", "Line thickness.")
    shape = _variable("shape", "Link shape name.")
    hidden = _variable("hidden?", "True when the link is hidden.")
    tie_mode = _variable("tie-mode", "'none', 'fixed' or 'free'.")

    @property
    def length(self) -> float:
        """Distance between the two ends (``link-length``)."""
        return self.of("link-length")

    @property
    def heading(self) -> float:
        """Heading from end1 to end2 (``link-heading``)."""
        return self.of("link-heading")

    def die(self) -> None:
        """Remove this link (``die``)."""
        self.ask("die")

    def hide_link(self) -> "Link":
        """Make the link invisible (``hide-link``)."""
        return self.ask("hide-link")

    def show_link(self) -> "Link":
        """Make the link visible again (``show-link``)."""
        return self.ask("show-link")

    def tie(self) -> "Link":
        """Make end2 follow end1's movements and turns."""
        return self.ask("tie")

    def untie(self) -> "Link":
        """Free end2 from end1's movements (``untie``)."""
        return self.ask("untie")
