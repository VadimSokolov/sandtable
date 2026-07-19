"""make_rng: reproducible, identity-seeded Generators."""
from __future__ import annotations

import numpy as np

from sandtable.seeding import make_rng


def test_returns_numpy_generator():
    assert isinstance(make_rng(0), np.random.Generator)


def test_same_seed_sub_identical_draws():
    a = make_rng(123, 4).random(16)
    b = make_rng(123, 4).random(16)
    assert np.array_equal(a, b)


def test_default_sub_is_zero():
    assert np.array_equal(make_rng(7).random(8), make_rng(7, 0).random(8))


def test_different_seed_differs():
    a = make_rng(1).random(16)
    b = make_rng(2).random(16)
    assert not np.array_equal(a, b)


def test_different_sub_differs():
    a = make_rng(5, 0).random(16)
    b = make_rng(5, 1).random(16)
    assert not np.array_equal(a, b)
