"""Input value validation shared by map and mission configuration boundaries."""

import math


class Invalid(ValueError):
    """A user-editable scenario violates its declared schema or model contract."""


def number(value, name, lo, hi, integer=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not lo <= value <= hi
        or (integer and value != int(value))
    ):
        raise Invalid(f"{name} must be {'an integer ' if integer else ''}between {lo} and {hi}.")
    return int(value) if integer else float(value)


def option(value, name, choices):
    if value not in choices:
        raise Invalid(f"{name} must be one of {', '.join(map(str, choices))}.")
    return value


def point(value, name, width, height):
    if not isinstance(value, list) or len(value) != 2:
        raise Invalid(name + " must contain x and y in metres.")
    return [
        number(value[0], name + " x", 1, width - 1),
        number(value[1], name + " y", 1, height - 1),
    ]
