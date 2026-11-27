"""Check an installed netlogopy: the package imports and its model files are there.

Run it with the Python of the environment where the wheel was installed, from
a folder that is not the repository (so that the installed package is the one
imported):

    python tools/check_wheel.py
"""

import os
import sys

import netlogopy
from netlogopy.core import BUNDLED_MODEL, BUNDLED_MODEL_NLOGOX

folder = os.path.dirname(os.path.abspath(netlogopy.__file__))
files = [BUNDLED_MODEL, BUNDLED_MODEL_NLOGOX, os.path.join(folder, "base.nls"), os.path.join(folder, "py.typed")]
missing = [path for path in files if not os.path.isfile(path)]
if missing:
    sys.exit("missing from the installed package: " + ", ".join(missing))
print(f"netlogopy {netlogopy.__version__} in {folder}: {len(files)} data files present")
