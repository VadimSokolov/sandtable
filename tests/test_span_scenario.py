"""Span-of-control scenario integration + sensitivity gate (Increment 2).

Ties the C2 and comms layers together through run_mission / evaluate on the real
sc_span_control.json centerpiece scenario: determinism, the n_blue sweep knob, the
ground-core no-op guard, and the decision-relevant result that comms jamming shifts
the optimum toward on-platform (supervisory) autonomy.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from sandtable import engagement, motion, planning, sensing
from sandtable.c2 import build_c2
from sandtable.comms_ew import build_comms
from sandtable.entities import BLUE, RED
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import evaluate, run_mission
from sandtable.world import build_world

SPAN_PATH = str(Path(__file__).resolve().parents[1] / "scenarios" / "sc_span_control.json")

# Sensitivity-gate settings: modest replications, fixed seed, a firm margin. Do NOT weaken.
N_REPS = 30
SEED = 0
SUCCESS_MARGIN = 0.15
FIXED_RED = 4        # sc_span_control.json places a fixed 4-team red force


def test_run_mission_is_deterministic():
    scn = load_scenario(SPAN_PATH)
    assert run_mission(scn, seed=5) == run_mission(scn, seed=5)
    # deterministic under param overrides (C2 + comms wired in) as well
    params = {"control_mode": "supervisory", "comms_level": 4, "n_blue": 5}
    assert run_mission(scn, seed=2, params=params) == run_mission(scn, seed=2, params=params)


def test_count_param_honors_n_blue():
    """ForceSpec.count_param lets params[n_blue] sweep the blue force; red stays fixed."""
    for n_blue in (4, 8):
        scn = load_scenario(SPAN_PATH).with_params({"n_blue": n_blue})
        ent = build_entities(scn, make_rng(0, scn.id))
        assert int((ent.side == BLUE).sum()) == n_blue
        assert int((ent.side == RED).sum()) == FIXED_RED
        assert ent.n == n_blue + FIXED_RED


def test_build_c2_is_none_without_control_mode(uc3_path, rng):
    """A ground-core scenario (no control_mode) gets no operator: build_c2 returns None."""
    scn = load_scenario(uc3_path)
    assert "control_mode" not in scn.params
    ent = build_entities(scn, rng)
    assert build_c2(scn, ent) is None
    # explicitly nulling control_mode on the span scenario also disables the C2 layer
    span = load_scenario(SPAN_PATH).with_params({"control_mode": None})
    assert build_c2(span, build_entities(span, rng)) is None


def test_ground_core_leaves_control_quality_neutral(uc3_path):
    """With no C2 layer the run never writes control_quality: it stays the neutral 1.0.

    This mirrors run_mission's loop (planning -> motion -> sensing -> engagement) but with
    op is None, so the motion/engagement control-quality couplings see a neutral multiplier
    and the ground core behaves as if Increment 2 were absent.
    """
    scn = load_scenario(uc3_path)
    rng = make_rng(0, scn.id)
    world = build_world(scn, rng)
    ent = build_entities(scn, rng)
    op = build_c2(scn, ent)
    assert op is None                                    # the guard: no operator to run
    blue0 = ent.side == BLUE
    spawn_x = float(ent.x[blue0].min()) if blue0.any() else 0.0
    for _ in range(40):
        planning.step(ent, world, scn, spawn_x)
        motion.step(ent, world, scn.dt, 1.0)
        sensing.step(ent, world, rng)
        engagement.step(ent, world, scn.dt, rng)
    assert np.allclose(ent.control_quality, 1.0)


def test_jamming_favors_supervisory_autonomy():
    """SENSITIVITY GATE: under heavy jamming (C5), supervisory beats direct control clearly.

    As comms degrade, the shared-operator round trip collapses direct control while
    on-platform supervisory autonomy degrades gracefully; the crossover is the single most
    decision-relevant result of the span-of-control study. This threshold is NOT to be weakened.
    """
    scn = load_scenario(SPAN_PATH)
    base = {"comms_level": 5, "n_blue": 6}
    sup = evaluate(scn, n_reps=N_REPS, seed=SEED, params={**base, "control_mode": "supervisory"})
    direct = evaluate(scn, n_reps=N_REPS, seed=SEED, params={**base, "control_mode": "direct"})
    s_sup = sup["success"]
    s_dir = direct["success"]
    assert s_sup - s_dir >= SUCCESS_MARGIN, (
        f"jamming did not favor supervisory autonomy: supervisory={s_sup:.3f} "
        f"direct={s_dir:.3f} margin={s_sup - s_dir:.3f} (need >= {SUCCESS_MARGIN}) "
        f"at comms_level=5, n_blue=6, n_reps={N_REPS}, seed={SEED}"
    )
