"""
Example 45 : Agents that write "NETLOGOPY"
==========================================
Nine turtles, one per letter, write the word NETLOGOPY with their pens.
Python holds the drawing: each letter is a list of strokes (points on a
4 x 6 grid); at every tick Python moves each turtle a little further along
its strokes, pen down on a stroke and pen up between two strokes.  NetLogo
draws the lines and shows the turtles.
"""
import math, os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

LETTERS = {                  # strokes on a 4 x 6 grid, (0, 0) bottom left
    "N": [[(0, 0), (0, 6), (4, 0), (4, 6)]],
    "E": [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    "T": [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    "L": [[(0, 6), (0, 0), (4, 0)]],
    "O": [[(0, 0), (0, 6), (4, 6), (4, 0), (0, 0)]],
    "G": [[(4, 6), (0, 6), (0, 0), (4, 0), (4, 3), (2, 3)]],
    "P": [[(0, 0), (0, 6), (4, 6), (4, 3), (0, 3)]],
    "Y": [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
}
WORD, SCALE, SPACING, MARGIN, SPEED = "NETLOGOPY", 2.5, 14, 5, 0.6
PALETTE = [colors.RED, colors.ORANGE, colors.YELLOW, colors.LIME, colors.TURQUOISE,
           colors.SKY, colors.BLUE, colors.VIOLET, colors.MAGENTA]


def plan(letter, left):
    """The letter as a list of (x, y, pen_down) targets, in world coordinates."""
    targets = []
    for stroke in LETTERS[letter]:
        points = [(left + x * SCALE, MARGIN + y * SCALE) for x, y in stroke]
        targets.append(points[0] + (False,))              # pen up to the stroke
        targets.extend(point + (True,) for point in points[1:])
    return targets


def step(turtle, position, targets):
    """Move the turtle SPEED patches towards its next target; its new position."""
    x, y = position
    while targets:
        tx, ty, pen = targets[0]
        distance = math.hypot(tx - x, ty - y)
        if distance > 1e-9:
            break
        targets.pop(0)
    if not targets:
        return position
    if pen:
        turtle.pen_down()
    else:
        turtle.pen_up()
    turtle.facexy(tx, ty)
    if distance <= SPEED:
        targets.pop(0)
        x, y = tx, ty
    else:
        x, y = x + (tx - x) * SPEED / distance, y + (ty - y) * SPEED / distance
    turtle.setxy(x, y)
    return x, y


if __name__ == "__main__":
    with NetLogo(gui=True) as nl:          # the bundled model; gui=False also works
        nl.setup()
        width = MARGIN * 2 + SPACING * (len(WORD) - 1) + 4 * SCALE
        nl.resize_world(0, round(width), 0, round(MARGIN * 2 + 6 * SCALE))
        if nl.gui:
            nl.set_patch_size(6)
        nl.ask("patches", "set pcolor black")
        writers, positions, plans = [], [], []
        for index, letter in enumerate(WORD):
            left = MARGIN + index * SPACING
            targets = plan(letter, left)
            x, y = targets[0][0], targets[0][1]
            turtle = nl.create_turtles(1, shape="turtle", size=3, color=PALETTE[index],
                                       xcor=x, ycor=y)[0]
            turtle.pen_size = 6
            writers.append(turtle)
            positions.append((x, y))
            plans.append(targets)
        while any(plans):
            for index, turtle in enumerate(writers):
                positions[index] = step(turtle, positions[index], plans[index])
            nl.tick()
            time.sleep(0.03)
        for turtle in writers:
            turtle.hide_turtle()
        print(f"{WORD} written in {nl.ticks:.0f} ticks by {len(writers)} turtles")
        time.sleep(2)
