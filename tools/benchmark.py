"""Time repeated netlogopy calls on the bundled model (headless).

    python tools/benchmark.py            # NetLogo found as netlogopy does it
    NETLOGO_HOME="C:/Program Files/NetLogo 6.2.2" python tools/benchmark.py

Prints the median time of a repeated call, after a warm-up (the first call of
a piece of code compiles it; the compiled procedure is then cached).
"""

import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netlogopy import NetLogo  # noqa: E402

CALLS = {
    'command("tick")': lambda nl: nl.command("tick"),
    'report("count turtles")': lambda nl: nl.report("count turtles"),
    'report("ticks")': lambda nl: nl.report("ticks"),
    "turtle.xcor": lambda nl: nl.turtle(0).xcor,
    'command("ask turtles [ fd 1 ]")  (100 turtles)': lambda nl: nl.command("ask turtles [ fd 1 ]"),
    'report([3 reporters])': lambda nl: nl.report(["count turtles", "ticks", "mean [xcor] of turtles"]),
}


def median_ms(function, repeat=2000):
    for _ in range(200):                       # warm-up: compile, JIT
        function()
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        function()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples) * 1000


def main():
    with NetLogo() as nl:
        nl.setup()
        nl.command("create-turtles 100")
        print(f"NetLogo {nl.netlogo_version}, Python {sys.version.split()[0]}")
        for name, call in CALLS.items():
            print(f"{median_ms(lambda call=call: call(nl)):7.3f} ms  {name}")


if __name__ == "__main__":
    main()
