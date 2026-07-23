"""Counter-UAS / SHORAD attrition of the blue recon swarm (Increment 6).

Opt-in via params["cuas_rate"]. Off by default it must be a byte-identical no-op (the loop draws no
extra RNG). On, red air defense shoots down exposed blue UAS with a hazard that grows with the
committed swarm size, so the UC-5 sensor-swarm response gains an INTERIOR optimum in swarm size
(the acceptance test) instead of the monotone "bigger is always better" curve it shows unopposed.
"""
from __future__ import annotations

import numpy as np

from sandtable.counter_uas import build_counter_uas
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import evaluate, run_mission

SC = load_scenario("scenarios/uc5_sensor_swarm.json")

# Calibrated so the survivable-swarm optimum sits at an interior size (see experiments/empirical.md):
# a superlinear signature collapses a massed swarm before it can cue the ground force.
CUAS = {"cuas_rate": 0.00006, "cuas_signature": 2.0}


def _p(**kw):
    base = {"n_uas": 4}
    base.update(kw)
    return base


# ---- gating -----------------------------------------------------------------

def test_build_none_when_off():
    """No cuas_rate (or a non-positive one) means no SHORAD layer is built."""
    rng = make_rng(0, SC.id)
    ent = build_entities(SC, rng)
    assert build_counter_uas(SC, ent) is None
    assert build_counter_uas(SC.with_params({"cuas_rate": 0.0}), ent) is None


def test_build_captures_committed_size():
    """When on, the layer freezes the committed swarm size n0 (the hazard keys on it, not the live count)."""
    scn = SC.with_params(_p(n_uas=6, **CUAS))
    rng = make_rng(0, scn.id)
    ent = build_entities(scn, rng)
    cuas = build_counter_uas(scn, ent)
    assert cuas is not None
    assert cuas.n0 == 6


# ---- byte-identical off ------------------------------------------------------

def test_off_is_byte_identical():
    """Absent vs explicit cuas_rate=0 give identical metrics across seeds: the off-path is the original
    code and draws the same RNG stream (the SHORAD step is never called)."""
    for seed in range(8):
        a = run_mission(SC, seed=seed, params=_p())
        b = run_mission(SC, seed=seed, params=_p(cuas_rate=0.0))
        assert a == b


# ---- attrition ---------------------------------------------------------------

def test_cuas_shoots_down_uas_and_cuts_coverage():
    """With SHORAD on, a large swarm loses drones (air losses > 0) and its detection coverage falls
    below the unopposed baseline for the same swarm size."""
    off = evaluate(SC, n_reps=40, params=_p(n_uas=8))
    on = evaluate(SC, n_reps=40, params=_p(n_uas=8, **CUAS))
    assert on["blue_air_losses"] > off["blue_air_losses"]
    assert on["detection_coverage"] < off["detection_coverage"]


# ---- acceptance test: interior peak in swarm size ---------------------------

def test_unopposed_swarm_is_monotone_bigger_is_better():
    """Baseline (no SHORAD): the largest swarm is (weakly) the best -- the UC-5 unbounded-swarm
    behavior that motivates the mechanic."""
    small = evaluate(SC, n_reps=60, params=_p(n_uas=1))["success_rate"]
    large = evaluate(SC, n_reps=60, params=_p(n_uas=8))["success_rate"]
    assert large > small + 0.15


def test_cuas_makes_swarm_success_peak_interior():
    """ACCEPTANCE TEST. With SHORAD on, mission success vs swarm size is a hump: a mid-size swarm beats
    both a too-small one (thin coverage) and a too-large one (attrited before it can cue). This is the
    interior optimum the mechanic is built to produce."""
    small = evaluate(SC, n_reps=60, params=_p(n_uas=1, **CUAS))["success_rate"]
    mid = evaluate(SC, n_reps=60, params=_p(n_uas=3, **CUAS))["success_rate"]
    large = evaluate(SC, n_reps=60, params=_p(n_uas=8, **CUAS))["success_rate"]
    assert mid > small + 0.10, f"no rise to the interior optimum: mid={mid:.3f} small={small:.3f}"
    assert mid > large + 0.10, f"no fall past the interior optimum: mid={mid:.3f} large={large:.3f}"
