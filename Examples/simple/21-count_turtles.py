"""
Example 21 : count_pyturtles / get_all_pyturtles / clear_all_turtles
Count, list and remove all turtles.
"""
import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"
    n = run_netlogo(netlogo_home)
    resize_world(n, 0, 60, 0, 60)

    # Create 5 turtles
    turtles = []
    for i in range(5):
        t = pyturtle(n, x=i * 10, y=20, shape="car", size_shape=3, color=15 + i * 10, name=f"car{i:02d}")
        turtles.append(t)

    time.sleep(1)
    total = count_pyturtles(n)
    print(f"Total pyturtles in NetLogo: {total}")

    all_t = get_all_pyturtles()
    print(f"Python list has {len(all_t)} turtles, IDs: {[t.id for t in all_t]}")

    time.sleep(2)
    print("Clearing all turtles...")
    clear_all_turtles(n)

    time.sleep(1)
    print(f"After clear: {count_pyturtles(n)} turtles in NetLogo")
    print(f"After clear: {len(get_all_pyturtles())} turtles in Python list")

    n.close_model()
