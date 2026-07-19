"""Detection: cookie-cutter range gate modulated by concealment."""
from __future__ import annotations

import numpy as np

from sandtable.entities import BLUE, RED, Entities
from sandtable import sensing


def _observer_target(sep=500.0, obs_range=1000.0):
    """A blue observer at origin and a red target `sep` metres away; red is blind (range 0)."""
    e = Entities.allocate(2)
    e.side[:] = [BLUE, RED]
    e.x[:] = [0.0, sep]
    e.y[:] = [0.0, 0.0]
    e.sensor_range[:] = [obs_range, 0.0]
    return e


def test_in_range_zero_conceal_is_detected(make_world):
    w = make_world(conceal=0.0)   # pd = 1 - conceal = 1 -> always detected
    e = _observer_target(sep=500.0, obs_range=1000.0)
    sensing.step(e, w, np.random.default_rng(0))
    assert bool(e.seen[1])         # the red target is on blue's SA picture
    assert not bool(e.seen[0])     # the blind red never detects the blue observer


def test_out_of_range_enemy_never_seen(make_world):
    w = make_world(conceal=0.0)
    e = _observer_target(sep=2000.0, obs_range=1000.0)   # target beyond sensor range
    for seed in range(50):
        sensing.step(e, w, np.random.default_rng(seed))
        assert not bool(e.seen[1])


def test_zero_conceal_always_detected_over_many_draws(make_world):
    w = make_world(conceal=0.0)
    e = _observer_target(sep=500.0, obs_range=1000.0)
    rng = np.random.default_rng(42)
    for _ in range(500):
        sensing.step(e, w, rng)
        assert bool(e.seen[1])   # pd == 1 makes detection deterministic across draws


def test_concealment_reduces_detection_probability(make_world):
    e = _observer_target(sep=500.0, obs_range=1000.0)
    n = 1500

    def seen_fraction(conceal):
        w = make_world(conceal=conceal)
        rng = np.random.default_rng(42)
        hits = 0
        for _ in range(n):
            sensing.step(e, w, rng)
            hits += int(e.seen[1])
        return hits / n

    frac_clear = seen_fraction(0.0)     # pd = 1.0
    frac_hidden = seen_fraction(0.8)    # pd = 0.2

    assert frac_clear == 1.0
    assert frac_hidden < frac_clear
    # statistical band around the expected 0.2 (3-sigma over 1500 draws is ~0.03)
    assert 0.12 < frac_hidden < 0.30
