"""
Example 42 : Segregation (Schelling), analysed by Python
========================================================
Two groups share a city.  A person moves to a free place when fewer than
`threshold` of their neighbours belong to their own group.  NetLogo runs the
moves; after each step Python reads the whole city in one call and measures
it: the segregation (mean share of same-group neighbours) and, by a flood
fill, the largest block of one group.  At the end of each run Python shows
the largest block of each group on the NetLogo view (darker colours).

Schelling's result appears: even people who accept being a minority (30 %)
end up in a strongly segregated city.

The NetLogo model is written by Python (the bundled model with its Code tab
replaced).
"""
import os, sys, tempfile, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import BUNDLED_MODEL, NetLogo

THRESHOLDS = [0.3, 0.5]
MAX_STEPS = 60

MODEL_CODE = """
breed [ pyturtles pyturtle ]
directed-link-breed [ streets street ]
globals [ threshold ]
turtles-own [ group happy? ]

to setup
  clear-all
  resize-world 0 39 0 39
  set-default-shape turtles "square"
  ask patches [ set pcolor white
    if random 100 < 85 [ sprout 1 [
      set group one-of [ 1 2 ]
      set color ifelse-value group = 1 [ orange ] [ sky ] ] ] ]
  update-happiness
  reset-ticks
end

to go
  ask turtles with [ not happy? ] [ move-to one-of patches with [ not any? turtles-here ] ]
  update-happiness
  tick
end

to update-happiness
  ask turtles [
    let around turtles-on neighbors
    set happy? count around with [ group = [group] of myself ] >= threshold * count around ]
end

to-report city    ; one row per pycor (top first): 0 empty, 1 or 2 the group
  report map [ y -> map [ x -> [ ifelse-value any? turtles-here [ [group] of one-of turtles-here ] [ 0 ] ]
    of patch x y ] range world-width ] reverse range world-height
end
"""


def write_model():
    with open(BUNDLED_MODEL, encoding="utf-8") as source:
        widgets = source.read().split("@#$#@#$#@", 1)[1]
    path = os.path.join(tempfile.mkdtemp(), "segregation.nlogo")
    with open(path, "w", encoding="utf-8") as model:
        model.write(MODEL_CODE + "@#$#@#$#@" + widgets)
    return path


def neighbours(row, col, height, width):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            r, c = row + dr, col + dc
            if (dr or dc) and 0 <= r < height and 0 <= c < width:
                yield r, c


def segregation(city):
    """Mean share of same-group neighbours, over the people who have neighbours."""
    height, width = len(city), len(city[0])
    shares = []
    for r in range(height):
        for c in range(width):
            if city[r][c]:
                groups = [city[i][j] for i, j in neighbours(r, c, height, width) if city[i][j]]
                if groups:
                    shares.append(groups.count(city[r][c]) / len(groups))
    return sum(shares) / len(shares)


def largest_blocks(city):
    """{group: cells of its largest connected block} (flood fill, 4 neighbours)."""
    height, width = len(city), len(city[0])
    seen, best = set(), {1: [], 2: []}
    for r in range(height):
        for c in range(width):
            group = city[r][c]
            if not group or (r, c) in seen:
                continue
            block, stack = [], [(r, c)]
            seen.add((r, c))
            while stack:
                i, j = stack.pop()
                block.append((i, j))
                for k, l in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= k < height and 0 <= l < width and (k, l) not in seen and city[k][l] == group:
                        seen.add((k, l))
                        stack.append((k, l))
            if len(block) > len(best[group]):
                best[group] = block
    return best


def run(nl, threshold, delay):
    nl.random_seed(7)
    nl.setup()                                      # clear-all also resets the globals
    nl.globals["threshold"] = threshold
    nl.command("update-happiness")
    start = segregation(nl.report("city"))
    nl.set_current_plot("My Plot")
    nl.create_temporary_plot_pen(f"{threshold:.0%}")
    nl.plot(100 * start)
    for step in range(MAX_STEPS):
        if nl.count("turtles", "not happy?") == 0:
            break
        nl.go()
        nl.plot(100 * segregation(nl.report("city")))
        time.sleep(delay)
    city = nl.report("city")
    blocks = largest_blocks(city)
    top = nl.max_pycor
    for group in (1, 2):                            # Python's analysis, shown in NetLogo
        cells = " ".join(f"patch {col} {top - row}" for row, col in blocks[group])
        nl.command(f"ask turtles-on (patch-set {cells}) [ set color color - 3 ]")
    time.sleep(1)
    return {"threshold": threshold, "steps": nl.ticks, "before": start,
            "after": segregation(city), "block": max(len(b) for b in blocks.values()),
            "people": nl.count("turtles")}


if __name__ == "__main__":
    with NetLogo(write_model(), gui=True) as nl:    # gui=False: same run without the window
        results = [run(nl, threshold, delay=0.05) for threshold in THRESHOLDS]
        time.sleep(2)

    print("threshold  steps  same-group neighbours  largest block")
    for r in results:
        print(f"{r['threshold']:9.0%} {r['steps']:6.0f}   {r['before']:6.0%} -> {r['after']:4.0%}"
              f"          {r['block']:4d} of {r['people']:.0f}")
