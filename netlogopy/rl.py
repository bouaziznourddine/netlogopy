"""A NetLogo model as a Gymnasium environment, for reinforcement learning.

>>> from netlogopy.rl import NetLogoEnv
>>> env = NetLogoEnv("Fire.nlogo",
...                  observation=["burned-trees", "count fires"],
...                  actions=["", "ask one-of fires [ die ]"],     # 0: do nothing, 1: put one fire out
...                  reward="0 - count fires",
...                  done="not any? turtles", max_steps=500)
>>> observation, info = env.reset(seed=1)
>>> observation, reward, terminated, truncated, info = env.step(1)

The environment follows the Gymnasium API, so the libraries built on it
(Stable-Baselines3, CleanRL, RLlib...) can train on the model without glue
code.  Needs ``pip install gymnasium numpy``.
"""

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

try:
    import gymnasium
    import numpy
except ImportError as exc:                 # pragma: no cover - depends on the installation
    raise ImportError("netlogopy.rl needs Gymnasium and numpy: pip install gymnasium numpy") from exc

from .core import NetLogo, PathLike

__all__ = ["NetLogoEnv"]


class NetLogoEnv(gymnasium.Env):
    """A NetLogo model seen as an environment: observe, act, get a reward.

    Parameters
    ----------
    model : str or os.PathLike, optional
        The model file (default: the model bundled with netlogopy).
    observation : str or sequence of str
        NetLogo reporters giving numbers or lists of numbers; their values,
        put end to end, are the observation.  Read without changing the
        course of the model.
    actions : sequence of str, or callable
        The NetLogo commands of each action: action ``i`` runs
        ``actions[i]`` and then one step of the model.  Or a function
        ``actions(nl, action)`` that applies the action itself; then give
        ``action_space``.
    reward : str or callable
        A NetLogo reporter giving the reward of the step, or a function
        ``reward(nl)``.
    done : str, optional
        NetLogo condition that ends an episode.  An episode also ends when
        the ``go`` procedure of the model calls ``stop``.
    setup, go : str
        The commands that start an episode and that make one step.
    max_steps : int, optional
        Steps after which an episode is cut short (``truncated``).
    action_space : gymnasium.Space, optional
        Needed when ``actions`` is a function.
    low, high : float
        Bounds of the observation values (default: no bound).
    gui : bool, default False
        Run in the NetLogo window, to watch the agent.
    render_mode : {"rgb_array", None}
        ``"rgb_array"``: :meth:`render` returns the image of the view.
    **session
        Other arguments of :class:`~netlogopy.NetLogo` (``netlogo_home``...).

    Attributes
    ----------
    nl : NetLogo
        The session, for anything the environment does not cover.
    """

    metadata = {"render_modes": ["rgb_array"], "render_fps": 10}

    def __init__(self, model: Optional[PathLike] = None, *,
                 observation: Union[str, Sequence[str]],
                 actions: Union[Sequence[str], Callable[[NetLogo, Any], None]],
                 reward: Union[str, Callable[[NetLogo], float]],
                 done: Optional[str] = None, setup: str = "setup", go: str = "go",
                 max_steps: Optional[int] = None, action_space: Optional[Any] = None,
                 low: float = -numpy.inf, high: float = numpy.inf, gui: bool = False,
                 render_mode: Optional[str] = None, **session: Any) -> None:
        if render_mode not in (None, "rgb_array"):
            raise ValueError('render_mode must be "rgb_array" or None')
        self._observation = [observation] if isinstance(observation, str) else list(observation)
        if not self._observation:
            raise ValueError("observation is empty: give at least one reporter")
        self._act: Optional[Callable[[NetLogo, Any], None]] = None
        self._commands: List[str] = []
        if callable(actions):
            if action_space is None:
                raise ValueError("actions is a function: give its action_space")
            self._act = actions
        else:
            self._commands = list(actions)
            if not self._commands:
                raise ValueError("actions is empty: give at least one command")
            action_space = action_space or gymnasium.spaces.Discrete(len(self._commands))
        self.action_space = action_space
        self._reward, self._done = reward, done
        self._setup, self._go = setup, go
        self.max_steps = None if max_steps is None else int(max_steps)
        self.render_mode = render_mode
        self._steps = 0
        self.nl = NetLogo(model, gui=gui, **session)
        try:
            # Compile everything now: a typo must not wait for the first episode.
            for code in self._commands + [setup, go]:
                self.nl._compile(code, reporter=False)
            for code in self._observation + [code for code in (reward, done) if isinstance(code, str)]:
                self.nl._compile(code, reporter=True)
            self.nl.command(setup)
            size = self._observe().shape
        except BaseException:
            self.nl.close()
            raise
        self.observation_space = gymnasium.spaces.Box(low=low, high=high, shape=size, dtype=numpy.float32)

    def _observe(self) -> Any:
        flat: List[float] = []

        def add(value: Any) -> None:
            if isinstance(value, (list, tuple)):
                for item in value:
                    add(item)
            elif isinstance(value, bool):
                flat.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                flat.append(float(value))
            else:
                raise TypeError(f"an observation must be made of numbers, the model gave {value!r}")

        add(self.nl.observe(self._observation))
        return numpy.array(flat, dtype=numpy.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None,
              ) -> Tuple[Any, Dict[str, Any]]:
        """Start an episode: ``setup``; ``seed`` also seeds NetLogo's random generator."""
        super().reset(seed=seed)
        if seed is not None:
            self.nl.random_seed(int(seed))
        self.nl.command(self._setup)
        self._steps = 0
        return self._observe(), {}

    def step(self, action: Any) -> Tuple[Any, float, bool, bool, Dict[str, Any]]:
        """Apply ``action``, run one step of the model, and report what happened."""
        with self.nl.hold():
            if self._act is not None:
                self._act(self.nl, action)
            else:
                command = self._commands[int(action)]
                if command.strip():
                    self.nl.command(command)
            stopped = self.nl._step(self._go)
            self._steps += 1
            reward = self._reward(self.nl) if callable(self._reward) else self.nl.observe(self._reward)
            terminated = bool(stopped) or (bool(self._done) and bool(self.nl.observe(self._done)))
            truncated = (not terminated and self.max_steps is not None and self._steps >= self.max_steps)
            return self._observe(), float(reward), terminated, truncated, {"steps": self._steps}

    def render(self) -> Any:
        """The image of the view as an array, when ``render_mode="rgb_array"``."""
        if self.render_mode == "rgb_array":
            return self.nl.view_array()
        return None

    def close(self) -> None:
        """Close the NetLogo session."""
        self.nl.close()
