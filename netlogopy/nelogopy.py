"""Old spelling of :mod:`netlogopy.netlogopy`.

The first releases named this module ``nelogopy``, and scripts written for
them import it that way (``from netlogopy.nelogopy import *``).  It is kept
so that these scripts keep working.
"""

from . import netlogopy as _netlogopy

__all__ = list(_netlogopy.__all__)
globals().update({name: getattr(_netlogopy, name) for name in __all__})
