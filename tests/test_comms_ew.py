"""Comms / EW degradation ladder (Increment 2).

Unit-tests build_comms (level -> ladder + overrides), round_trip geometry, and the
Bernoulli message-survival draw (deterministic given a seeded rng, and correctly
degenerate at p_drop 0 and 1). Pure and data-only, so every test is a few milliseconds.
"""
from __future__ import annotations

import numpy as np

from sandtable.comms_ew import Comms, _LADDER, build_comms


def test_build_comms_maps_level_to_ladder(skirmish_scenario):
    """Each level 0..5 reproduces its ladder point (latency, p_drop, label)."""
    for level in range(6):
        c = build_comms(skirmish_scenario.with_params({"comms_level": level}))
        lat, drop, label = _LADDER[level]
        assert c.level == level
        assert c.latency == lat
        assert c.p_drop == drop
        assert c.label == label


def test_ladder_is_monotone_in_level(skirmish_scenario):
    """Latency and drop probability are both non-decreasing as jamming worsens."""
    lats, drops = [], []
    for level in range(6):
        c = build_comms(skirmish_scenario.with_params({"comms_level": level}))
        lats.append(c.latency)
        drops.append(c.p_drop)
    assert lats == sorted(lats), f"latency not non-decreasing: {lats}"
    assert drops == sorted(drops), f"p_drop not non-decreasing: {drops}"
    # strictly worse at the extremes (a real ladder, not a flat line)
    assert lats[5] > lats[0]
    assert drops[5] > drops[0]


def test_round_trip_is_twice_latency():
    """A request out plus a reply back costs two one-way latencies."""
    for lat in (0, 1, 2, 4, 8, 16):
        c = Comms(level=0, latency=lat, p_drop=0.0, label="x")
        assert c.round_trip() == 2 * lat


def test_delivered_is_deterministic_given_seed():
    """The survival draw is a pure function of the rng stream (same seed, same draws)."""
    c = Comms(level=3, latency=4, p_drop=0.5, label="contested")
    r1 = np.random.default_rng(123)
    r2 = np.random.default_rng(123)
    seq1 = [c.delivered(r1) for _ in range(100)]
    seq2 = [c.delivered(r2) for _ in range(100)]
    assert seq1 == seq2


def test_delivered_never_drops_at_p_zero():
    """p_drop == 0: every message is delivered."""
    c = Comms(level=0, latency=0, p_drop=0.0, label="uncontested")
    rng = np.random.default_rng(0)
    assert all(c.delivered(rng) for _ in range(2000))


def test_delivered_always_drops_at_p_one(skirmish_scenario):
    """p_drop == 1 (via the comms_p_drop override): no message survives."""
    c = build_comms(skirmish_scenario.with_params({"comms_p_drop": 1.0}))
    assert c.p_drop == 1.0
    rng = np.random.default_rng(0)
    assert not any(c.delivered(rng) for _ in range(2000))


def test_delivered_half_rate_is_about_half():
    """p_drop == 0.5: the empirical drop rate over many draws is ~0.5 (wide tolerance)."""
    c = Comms(level=3, latency=4, p_drop=0.5, label="contested")
    rng = np.random.default_rng(7)
    n = 20000
    delivered = np.mean([c.delivered(rng) for _ in range(n)])
    drop_rate = 1.0 - delivered
    assert abs(drop_rate - 0.5) < 0.05, f"empirical drop rate {drop_rate:.3f} not near 0.5"


def test_params_overrides_take_effect(skirmish_scenario):
    """comms_latency and comms_p_drop retune the operating point without touching the ladder."""
    scn = skirmish_scenario.with_params(
        {"comms_level": 2, "comms_latency": 7, "comms_p_drop": 0.9}
    )
    c = build_comms(scn)
    assert c.level == 2               # label/level still come from the ladder
    assert c.label == _LADDER[2][2]
    assert c.latency == 7            # overridden
    assert c.p_drop == 0.9          # overridden
    assert c.round_trip() == 14


def test_comms_level_clips_to_range(skirmish_scenario):
    """comms_level below 0 or above 5 is clipped into the valid ladder range."""
    lo = build_comms(skirmish_scenario.with_params({"comms_level": -3}))
    hi = build_comms(skirmish_scenario.with_params({"comms_level": 99}))
    assert lo.level == 0
    assert hi.level == 5
    # and the clipped level pulls the matching ladder point
    assert (lo.latency, lo.p_drop) == (_LADDER[0][0], _LADDER[0][1])
    assert (hi.latency, hi.p_drop) == (_LADDER[5][0], _LADDER[5][1])


def _ge(burst: float = 4.0, drop: float = 0.20) -> Comms:
    """A step-clocked Gilbert-Elliot link at a chosen dwell and marginal rate."""
    p_bg = 1.0 / burst
    return Comms(level=3, latency=1, p_drop=drop, label="probe",
                 channel="gilbert_elliot", clock="step",
                 p_gb=drop * p_bg / (1.0 - drop), p_bg=p_bg)


def test_same_step_transmissions_share_one_channel_state():
    """CR-20. Two vehicles that transmit on the same step are in one radio environment, so the
    second must inherit the first's outcome rather than draw against a chain that has been
    advanced one transition on its behalf."""
    for burst in (4.0, 28.0, 120.0):
        for start_bad in (False, True):
            c = _ge(burst)
            c._bad = start_bad
            c._k = c._last_k = 40
            rng = np.random.default_rng(7)
            first = c.delivered(rng)
            # eight more callers on the very same step, each consuming its own uniform
            assert all(c.delivered(rng) == first for _ in range(8))


def test_a_gap_of_one_step_still_admits_a_transition():
    """The fix must not freeze the chain: one step of separation restores the transition, so the
    channel is shared only by callers that are genuinely simultaneous."""
    c = _ge(4.0)
    c._bad = True
    c._k = c._last_k = 0
    rng = np.random.default_rng(0)
    c.delivered(rng)                     # gap 0, stays BAD
    assert c._bad
    flips = 0
    for k in range(1, 400):
        c._bad = True
        c._last_k = k - 1
        c._k = k
        c.delivered(rng)
        flips += not c._bad
    # BAD -> GOOD at p_bg = 0.25 per step, so about a quarter of the single-step gaps recover
    assert 0.15 < flips / 399 < 0.35


def test_the_step_clock_leaves_a_memoryless_channel_untouched():
    """K2 measured this at every rung on the full model; assert it here so a regression is caught
    in milliseconds rather than in a two-hour battery."""
    for drop in (0.05, 0.20, 0.55):
        a = Comms(level=3, latency=1, p_drop=drop, label="p", clock="message")
        b = Comms(level=3, latency=1, p_drop=drop, label="p", clock="step")
        ra, rb = np.random.default_rng(3), np.random.default_rng(3)
        for k in range(500):
            a._k = b._k = k
            assert a.delivered(ra) == b.delivered(rb)
