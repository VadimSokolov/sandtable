"""Entities SoA container: allocation shape, defaults, and side masking."""
from __future__ import annotations

from dataclasses import fields

import numpy as np

from sandtable.entities import BLUE, RED, Entities


def test_allocate_all_fields_are_length_n_arrays():
    n = 7
    e = Entities.allocate(n)
    assert e.n == n
    for f in fields(Entities):
        arr = getattr(e, f.name)
        assert isinstance(arr, np.ndarray), f"{f.name} is not an array"
        assert arr.shape == (n,), f"{f.name} has shape {arr.shape}, expected {(n,)}"


def test_allocate_defaults():
    e = Entities.allocate(5)
    assert e.alive.dtype == bool and bool(e.alive.all())      # alive defaults True
    assert not e.seen.any()                                   # nothing seen yet
    assert np.array_equal(e.hp, np.ones(5))                   # full hp
    assert np.isinf(e.fuel).all()                             # infinite endurance by default
    assert np.array_equal(e.leader, np.full(5, -1))           # no leader
    assert np.array_equal(e.x, np.zeros(5))                   # zeroed kinematics


def test_side_mask_filters_by_side_and_alive():
    e = Entities.allocate(6)
    e.side[:] = [BLUE, BLUE, RED, RED, BLUE, RED]
    e.alive[1] = False   # a dead blue must drop out of the blue mask
    e.alive[3] = False   # a dead red must drop out of the red mask

    assert e.side_mask(BLUE).tolist() == [True, False, False, False, True, False]
    # index 2 is a living red; index 3 is a dead red; index 5 is a living red
    assert e.side_mask(RED).tolist() == [False, False, True, False, False, True]


def test_side_mask_all_alive():
    e = Entities.allocate(4)
    e.side[:] = [BLUE, RED, BLUE, RED]
    assert int(e.side_mask(BLUE).sum()) == 2
    assert int(e.side_mask(RED).sum()) == 2
