"""Scripts written for the first releases of netlogopy must keep running.

They use the 0.x API and the first import spelling (``netlogopy.nelogopy``);
only the placeholder paths are filled in.
"""

import os

import pytest
from conftest import EXAMPLES, WOLF_MODEL

pytestmark = pytest.mark.netlogo

AGENTS_SCRIPT = '''
import time
from netlogopy.nelogopy import *

n = run_netlogo(netlogo_home)

# Resize the NetLogo world
resize_world(n, 0, 60, 0, 60)

# Create a turtle agent
car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)

# Move the agent forward by 1 unit each step
for i in range(10):
    time.sleep(1)
    car01.fd(1)
    print(f"Agent moved to position {getxyturtle(n, car01)}")
after_moving = getxyturtle(n, car01)

# Create a second turtle agent
car02 = pyturtle(n, x=5, y=5, shape="car", size_shape=4, color=55, name="car02", labelcolor=55)

# Create a link (street) between agents
street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, thickness=0.5)

# Move agent car01 towards car02
for i in range(10):
    time.sleep(1)
    car01.face_to(car02)
    car01.fd(1)
    distance = car01.distanceto(car02)
    print(f"Distance to car02: {distance}")
after_approach = distance

# Set a background image
set_background(n, background_image)

# Get the agent's position
position = getxyturtle(n, car01)
print(f"Agent position: {position}")

# Set the agent's position
car01.setxy(10, 10)
after_setxy = getxyturtle(n, car01)

# Move car01 to the position of car02
car01.move_to(car02)

# Hide the agent car01
car01.hideturtle()

# Change the shape of car01 to 'default'
car01.set_shape('default')

# Calculate the distance between car01 and car02
distance = distancebetween(n, car01, car02)
print(f"Distance between car01 and car02: {distance}")
'''

EXISTING_MODEL_SCRIPT = '''
import time, os, sys
from netlogopy.nelogopy import *

n = run_netlogo(netlogo_home, path_model)

# Resize world
resize_world(n, 0, 70, 0, 55)

# Initialize the original NetLogo model
run_command(n, "setup")

# Add Python-controlled agents
car01 = pyturtle(n, x=20, y=20, shape="car", size_shape=4, color=15, name="car01", labelcolor=15)
car02 = pyturtle(n, x=5, y=5, shape="car", size_shape=4, color=55, name="car02", labelcolor=55)
street(n, fromm=car01, too=car02, label="street", labelcolor=35, color=35, shape="default", thickness=0.5)

for i in range(100):
    run_command(n, "go")  # Run the NetLogo model step
    time.sleep(0.1)
    print(f"*********** {i} ********")
    car01.fd(1)
    if i % 20 == 0:
        car01.setxy(10, 10)
'''


@pytest.fixture
def script(monkeypatch):
    monkeypatch.setenv("NETLOGOPY_HEADLESS", "1")
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    namespace = {"netlogo_home": None}
    yield namespace
    session = namespace.get("n")
    if session is not None:
        session.close_model()


def test_agents_script(script):
    script["background_image"] = os.path.join(EXAMPLES, "netlogopy.png")
    exec(AGENTS_SCRIPT, script)
    assert script["after_moving"] == [20, 30]              # ten steps north
    assert script["after_approach"] < 26 and script["after_setxy"] == [10, 10]
    car01, car02 = script["car01"], script["car02"]
    assert script["distance"] == 0 and car01.get_xy() == car02.get_xy() == [5, 5]
    assert car01.hidden and car01.get_shape() == "default"
    assert script["n"].count("streets") == 1


def test_existing_model_script(script):
    script["path_model"] = WOLF_MODEL
    exec(EXISTING_MODEL_SCRIPT, script)
    n = script["n"]
    assert n.ticks == 100 and (n.world_width, n.world_height) == (71, 56)
    assert n.count("pyturtles") == 2 and n.count("streets") == 1
    assert script["car01"].get_xy() == [10, 29]            # reset at i = 80, then 19 steps
