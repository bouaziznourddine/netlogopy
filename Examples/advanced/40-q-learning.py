"""
Example 40 : Reinforcement learning with NetLogo as the environment
===================================================================
A robot learns by trial and error (Q-learning) to cross a maze.  NetLogo is
the environment: it holds the maze, moves the robot and says where it is;
Python holds the learning: the table of action values, the reward and the
exploration.  Every 20 episodes the robot shows, pen down, what it has
learned so far; while it has not learned enough it goes round in circles, and
the demonstration stops as soon as it comes back to a square it has visited.

The same loop works with any learning library (a neural network instead of
the table, Stable-Baselines3 with a gym wrapper...).
"""
import os, random, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

MAZE = [                     # # wall, S start, G goal (top row first)
    "###############",
    "#S  #     #   #",
    "# # # ### # # #",
    "# #   #   # # #",
    "# ##### ### # #",
    "#     #     # #",
    "##### # ##### #",
    "#   # #     # #",
    "# # # ##### # #",
    "# #   #   # # #",
    "# ##### # # # #",
    "#     # # #   #",
    "# ### # # ### #",
    "#   #   #    G#",
    "###############",
]
ACTIONS = [0, 90, 180, 270]                  # headings: north, east, south, west
EPISODES, MAX_STEPS, SHOW_EVERY = 160, 250, 20
ALPHA, GAMMA = 0.5, 0.95


def build(nl):
    size = len(MAZE)
    nl.resize_world(0, size - 1, 0, size - 1)
    if nl.gui:
        nl.set_patch_size(30)
    for row, line in enumerate(MAZE):
        for column, cell in enumerate(line):
            patch = nl.patch(column, size - 1 - row)
            patch.pcolor = {"#": colors.GRAY, "G": colors.LIME}.get(cell, colors.BLACK)
            if cell == "S":
                start = (column, size - 1 - row)
    robot = nl.create_turtles(1, shape="turtle", size=1, color=colors.ORANGE,
                              xcor=start[0], ycor=start[1], heading=0)[0]
    return robot, start


def step(nl, robot, action):
    """NetLogo moves the robot one patch, unless a wall is ahead; reward and new state."""
    nl.command(f"ask {robot.to_netlogo()} [ set heading {ACTIONS[action]} "
               f"if [pcolor] of patch-ahead 1 != {colors.GRAY} [ fd 1 ] ]")
    x, y, color = nl.report(f"[(list pxcor pycor pcolor)] of {robot.to_netlogo()}")
    state = (int(x), int(y))
    if color == colors.LIME:
        return state, 100.0, True
    return state, -1.0, False


def episode(nl, robot, start, q, epsilon, rng, show=False):
    robot.pen_up()
    robot.setxy(*start)
    if show:
        nl.clear_drawing()
        robot.pen_down()
    state, total, visited = start, 0.0, {start}
    for moves in range(1, MAX_STEPS + 1):
        values = q.setdefault(state, [0.0] * len(ACTIONS))
        action = rng.randrange(len(ACTIONS)) if rng.random() < epsilon else values.index(max(values))
        new_state, reward, done = step(nl, robot, action)
        best_next = max(q.setdefault(new_state, [0.0] * len(ACTIONS)))
        if not show:                                          # learn (not while showing)
            values[action] += ALPHA * (reward + GAMMA * best_next * (not done) - values[action])
        state, total = new_state, total + reward
        if show:
            time.sleep(0.02)
            if new_state in visited:                          # going round in circles
                break
            visited.add(new_state)
        if done:
            break
    return moves, done


if __name__ == "__main__":
    rng = random.Random(5)
    with NetLogo(gui=True) as nl:                  # the bundled model; gui=False also works
        nl.setup()
        robot, start = build(nl)
        q = {}
        for number in range(1, EPISODES + 1):
            epsilon = max(0.05, 1 - number / (0.7 * EPISODES))   # explore less and less
            moves, reached = episode(nl, robot, start, q, epsilon, rng)
            if number % SHOW_EVERY == 0:
                shown, ok = episode(nl, robot, start, q, 0.0, rng, show=True)
                print(f"episode {number:3d}: exploring took {moves:3d} moves; "
                      f"what it learned: {'goal in ' + str(shown) + ' moves' if ok else 'stuck after ' + str(shown) + ' moves'}")
                time.sleep(0.5)
        print(f"{len(q)} states learned; shortest route found: {shown} moves")
        time.sleep(2)
