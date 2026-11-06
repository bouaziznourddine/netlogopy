"""
Example 29 : Patches as a grid
==============================
Read and write a patch variable for the whole world in one call, let NetLogo
diffuse it, and analyse the result in Python.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo

if __name__ == "__main__":
    with NetLogo(gui=True) as nl:
        nl.setup()
        height, width = nl.world_height, nl.world_width

        # A Python-made pattern: a bright square in the middle (row 0 = top row)
        grid = [[9.9 if 25 <= x <= 35 and 25 <= y <= 35 else 0 for x in range(width)]
                for y in range(height)]
        nl.set_patch_grid("pcolor", grid)

        for step in range(30):
            nl.diffuse("pcolor", 0.5)            # NetLogo's diffuse primitive
            nl.tick()
            time.sleep(0.05)

        grid = nl.patch_grid("pcolor")          # list of rows, top row first
        total = sum(map(sum, grid))
        lit = sum(value > 0.5 for row in grid for value in row)
        print(f"total brightness {total:.1f}, {lit} patches brighter than 0.5")
        print("centre patch:", nl.patch(30, 30).pcolor)

        # Patches are agents too
        corner = nl.patch(0, 0)
        corner.pcolor = 15
        corner.plabel = "corner"
        print("neighbours of the corner:", corner.neighbors())
        print("patches with pcolor > 1:", nl.count("patches", "pcolor > 1"))
        time.sleep(2)
