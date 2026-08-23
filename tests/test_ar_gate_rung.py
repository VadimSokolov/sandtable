"""Guard for instrument defect 11: a rate carried from the rung it was derived on to another.

CR-58's bridge arithmetic used a drop rate of 0.55 in a prediction it then tested at C3, where the
ladder's value is 0.20. The prediction came out 3.4 times too large and its registered falsifier
fired. `deep_stale_fraction` takes the rung as an argument and reads the rate from the model, so the
mistake is now a wrong argument rather than an invisible constant. These tests pin that it reads the
model and not a copy of it.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from ar_gate import deep_stale_fraction  # noqa: E402
from sandtable.comms_ew import _LADDER  # noqa: E402


def test_reads_the_ladder_rather_than_a_copy_of_it():
    for level, (_, p_drop, _label) in _LADDER.items():
        assert deep_stale_fraction(level, 60.0, 0.0) == pytest.approx(p_drop)


def test_the_rungs_the_bridge_confused_are_not_interchangeable():
    # The whole point: C3 and C5 differ by a factor the bridge's error was made of.
    c3 = deep_stale_fraction(3, 60.0, 40.0)
    c5 = deep_stale_fraction(5, 60.0, 40.0)
    assert c5 / c3 == pytest.approx(_LADDER[5][1] / _LADDER[3][1])
    assert c5 / c3 > 2.5


def test_an_unknown_rung_is_an_error_and_not_a_default():
    with pytest.raises(KeyError):
        deep_stale_fraction(9, 60.0, 40.0)
