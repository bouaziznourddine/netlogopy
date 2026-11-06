"""Run the Wolf Sheep model without window and log each iteration."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from netlogopy.netlogopy import netlogo_session, run_command

netlogo_home = "C:/Program Files/NetLogo 6.2.2"   # or None to detect it
model_path = os.path.join(os.path.dirname(__file__), "Wolf Sheep Predation.nlogo")
output_file_path = os.path.join(os.path.dirname(__file__), "output_wolf_sheep.txt")

with netlogo_session(netlogo_home, model_path, headless=True) as n:
    for i in range(10):
        run_command(n, "go")
        with open(output_file_path, "a") as f:
            f.write(f"{model_path} iteration {i}\n")
        print(f"{model_path}  {i}")
