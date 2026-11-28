# Experiments

::: netlogopy.run_experiment

::: netlogopy.parameter_grid

## BehaviorSpace experiments of a model

::: netlogopy.behaviorspace_experiments

::: netlogopy.run_behaviorspace

## Designs, sensitivity, calibration

::: netlogopy.latin_hypercube

::: netlogopy.random_sample

::: netlogopy.sensitivity

::: netlogopy.calibrate

## Reinforcement learning

`netlogopy.rl` needs Gymnasium and numpy (`pip install "netlogopy[rl]"`).

`NetLogoEnv(model=None, *, observation, actions, reward, done=None, setup="setup", go="go",
max_steps=None, action_space=None, low=-inf, high=inf, gui=False, render_mode=None, **session)`

| Member | |
|---|---|
| `reset(seed=None)` | starts an episode with `setup`; `seed` also seeds NetLogo; returns `(observation, info)` |
| `step(action)` | applies the action, runs one step; returns `(observation, reward, terminated, truncated, info)` |
| `render()` | the image of the view, with `render_mode="rgb_array"` |
| `close()` | closes the NetLogo session |
| `nl` | the session |
| `observation_space`, `action_space` | the Gymnasium spaces |

See [Reinforcement learning](../guide/simulation.md#reinforcement-learning).
