"""
Example 47 : A NetLogo model as a Gymnasium environment
=======================================================
The Fire model becomes an environment for reinforcement learning: at each
step the agent sees the state of the fire and chooses to do nothing or to
send a firefighter that puts one fire out, which costs something.

NetLogoEnv follows the Gymnasium API, so a learning library (Stable-Baselines3,
CleanRL, RLlib...) can train on it without glue code:

    from stable_baselines3 import PPO
    PPO("MlpPolicy", env).learn(20_000)

Here two fixed policies are compared, to show the loop.
Needs `pip install gymnasium numpy`.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "complexe", "Fire", "Fire.nlogo")
WAIT, FIGHT = 0, 1


def episode(env, policy, seed):
    observation, _ = env.reset(seed=seed)
    total = 0.0
    while True:
        observation, reward, terminated, truncated, _ = env.step(policy(observation))
        total += reward
        if terminated or truncated:
            return total, int(observation[0])


if __name__ == "__main__":
    try:
        from netlogopy.rl import NetLogoEnv
    except ImportError as exc:
        print("example skipped:", exc)
        sys.exit(0)

    env = NetLogoEnv(
        MODEL,
        observation=["burned-trees", "count fires"],
        actions=["",                                              # 0: wait
                 "ask up-to-n-of 2 fires [ die ]"],               # 1: put two fires out
        reward="0 - count fires",                                 # fewer fires is better
        done="not any? turtles",
        max_steps=400,
        gui=os.environ.get("NETLOGOPY_HEADLESS") != "1",          # watch it in the NetLogo window
    )
    env.nl.globals["density"] = 62
    print("observation:", env.observation_space, " actions:", env.action_space)
    for name, policy in [("always wait", lambda observation: WAIT),
                         ("fight when more than 5 fires", lambda observation: FIGHT if observation[1] > 5 else WAIT)]:
        results = [episode(env, policy, seed) for seed in (1, 2, 3)]
        burned = sum(burned for _, burned in results) / len(results)
        reward = sum(total for total, _ in results) / len(results)
        print(f"{name:30s} mean reward {reward:9.0f}   burned trees {burned:7.0f}")
    env.close()
