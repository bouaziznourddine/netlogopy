"""NetLogo colors: the named colors and small helpers.

NetLogo colors are numbers from 0 to 140: each named color ``c`` (red = 15...)
has shades from ``c - 5`` (black) to ``c + 4.9`` (white).  Any variable that
takes a color also accepts an RGB or RGBA list, see :func:`rgb` and :func:`rgba`.
"""

import math
from typing import List

__all__ = [
    "BLACK", "GRAY", "WHITE", "RED", "ORANGE", "BROWN", "YELLOW", "GREEN", "LIME",
    "TURQUOISE", "CYAN", "SKY", "BLUE", "VIOLET", "MAGENTA", "PINK",
    "BASE_COLORS", "rgb", "rgba", "shade",
]

BLACK = 0
GRAY = 5
WHITE = 9.9
RED = 15
ORANGE = 25
BROWN = 35
YELLOW = 45
GREEN = 55
LIME = 65
TURQUOISE = 75
CYAN = 85
SKY = 95
BLUE = 105
VIOLET = 115
MAGENTA = 125
PINK = 135

#: Same values as NetLogo's ``base-colors`` reporter.
BASE_COLORS = [GRAY, RED, ORANGE, BROWN, YELLOW, GREEN, LIME, TURQUOISE,
               CYAN, SKY, BLUE, VIOLET, MAGENTA, PINK]


def _channel(value: float, name: str) -> float:
    if not 0 <= value <= 255:
        raise ValueError(f"{name} must be between 0 and 255, got {value!r}")
    return value


def rgb(red: float, green: float, blue: float) -> List[float]:
    """An RGB color usable anywhere NetLogo expects a color."""
    return [_channel(red, "red"), _channel(green, "green"), _channel(blue, "blue")]


def rgba(red: float, green: float, blue: float, alpha: float) -> List[float]:
    """An RGB color with transparency (alpha 0 = invisible, 255 = opaque)."""
    return rgb(red, green, blue) + [_channel(alpha, "alpha")]


def shade(color: float, amount: float) -> float:
    """Darker (amount < 0) or lighter (amount > 0) shade of the same hue.

    >>> shade(RED, -3)
    12
    """
    band = math.floor(color / 10) * 10
    return min(max(color + amount, band), band + 9.9)
