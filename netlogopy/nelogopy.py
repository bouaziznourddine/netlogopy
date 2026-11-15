"""Old spelling of :mod:`netlogopy.netlogopy`.

The first releases named this module ``nelogopy``, and the SW25 paper's
examples import it that way (``from netlogopy.nelogopy import *``).  It is
kept so that code copied from the paper keeps working.
"""

from . import netlogopy as _netlogopy

__all__ = list(_netlogopy.__all__)
globals().update({name: getattr(_netlogopy, name) for name in __all__})
