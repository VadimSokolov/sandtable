"""Two-tier command and control (Increment 2).

Unit-tests the operator model: build_c2 gating and attention dilution (span-of-control
on decision quality), and the per-step control_quality state machine under both control
modalities. Steps are driven in isolation (no full mission) so every test is fast and
deterministic given the seeded rng.
"""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import numpy as np
import pytest

from sandtable.c2 import Operator, build_c2, step
from sandtable.comms_ew import build_comms
from sandtable.entities import BLUE, RED
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng

SPAN_PATH = str(Path(__file__).resolve().parents[1] / "scenarios" / "sc_span_control.json")

# Configured (undiluted) quality anchors, matching sc_span_control.json.
Q_OPERATOR = 0.95
Q_AUTO = 0.70
SPAN_CAPACITY = 4.0


def _span_scenario(**overrides):
    return load_scenario(SPAN_PATH).with_params(overrides)


def _build(scn, seed=0):
    """Build (entities, comms, operator) from a scenario with a fixed-seed rng."""
    rng = make_rng(seed, scn.id)
    ent = build_entities(scn, rng)
    comms = build_comms(scn)
    op = build_c2(scn, ent)
    return ent, comms, op, rng


# ---- build_c2 gating --------------------------------------------------------

def test_build_c2_none_without_control_mode(skirmish_scenario, rng):
    """No control_mode in params means no C2 layer (build_c2 returns None)."""
    ent = build_entities(skirmish_scenario, rng)
    assert build_c2(skirmish_scenario, ent) is None


def test_build_c2_rejects_invalid_mode(skirmish_scenario, rng):
    """An unknown control_mode is a configuration error, not a silent default."""
    scn = skirmish_scenario.with_params({"control_mode": "telepathy"})
    ent = build_entities(scn, rng)
    with pytest.raises(ValueError):
        build_c2(scn, ent)


def test_operator_has_expected_fields():
    """The Operator dataclass exposes the documented control parameters."""
    scn = _span_scenario()
    ent, _, op, _ = _build(scn)
    names = {f.name for f in fields(Operator)}
    assert names == {
        "mode", "service_rate", "q_operator", "q_auto", "q_fallback", "q_stall",
        "patience", "decision_interval", "operator_free_at", "resolved_quality",
        "ew_immune", "immune_latency",
    }
    assert op.mode == "direct"                       # sc_span_control default
    assert op.resolved_quality.shape == (ent.n,)


# ---- attention dilution (span-of-control on decision quality) ---------------

@pytest.mark.parametrize("n_blue", [2, 3, 4])
def test_attention_undiluted_within_span(n_blue):
    """With span_capacity=4, the operator fully attends up to 4 agents: q_operator undiluted."""
    scn = _span_scenario(n_blue=n_blue)
    _, _, op, _ = _build(scn)
    assert np.isclose(op.q_operator, Q_OPERATOR)


def test_attention_diluted_beyond_span():
    """Beyond span_capacity the effective q_operator decays toward q_auto per the formula."""
    n_blue = 8
    scn = _span_scenario(n_blue=n_blue)
    ent, _, op, _ = _build(scn)
    n_span = int((ent.side == BLUE).sum())
    assert n_span == n_blue
    expected = Q_AUTO + (Q_OPERATOR - Q_AUTO) * min(1.0, SPAN_CAPACITY / n_span)
    assert np.isclose(op.q_operator, expected)             # exact formula match
    assert Q_AUTO < op.q_operator < Q_OPERATOR             # strictly between the anchors


# ---- per-step control_quality state machine --------------------------------

def test_step_keeps_control_quality_in_unit_range_and_leaves_red_neutral():
    """After each step blue control_quality stays in [0,1]; red keeps the neutral 1.0."""
    scn = _span_scenario(control_mode="direct", comms_level=2, n_blue=4)
    ent, comms, op, rng = _build(scn, seed=1)
    blue = np.nonzero(ent.side == BLUE)[0]
    red = np.nonzero(ent.side == RED)[0]
    saw_below_one = False
    for k in range(80):
        step(ent, op, comms, scn, k, rng)
        cq_blue = ent.control_quality[blue]
        assert np.all(cq_blue >= 0.0) and np.all(cq_blue <= 1.0)
        if np.any(cq_blue < 1.0):
            saw_below_one = True
        assert np.allclose(ent.control_quality[red], 1.0)   # red never managed
    assert saw_below_one, "control_quality never moved off the neutral 1.0 (step did nothing)"


def test_supervisory_settles_at_q_auto():
    """Supervisory (human-on-the-loop): agents decide locally at q_auto, no stall/operator states."""
    scn = _span_scenario(control_mode="supervisory", comms_level=0, n_blue=4)
    ent, comms, op, rng = _build(scn, seed=7)
    blue = np.nonzero(ent.side == BLUE)[0]
    seen = set()
    for k in range(120):
        step(ent, op, comms, scn, k, rng)
        seen.update(np.round(ent.control_quality[blue], 6).tolist())
    # only q_auto is ever observed: no q_stall (0.30) and no q_operator (0.95)
    assert all(np.isclose(v, op.q_auto) for v in seen), f"unexpected qualities: {sorted(seen)}"
    assert np.allclose(ent.control_quality[blue], op.q_auto)


def test_direct_at_c0_reaches_q_operator():
    """Direct (human-in-the-loop) with clean comms: serviced decisions reach q_operator."""
    scn = _span_scenario(control_mode="direct", comms_level=0, n_blue=4,
                         span_capacity=4.0, service_rate=0.5)
    ent, comms, op, rng = _build(scn, seed=3)
    blue = np.nonzero(ent.side == BLUE)[0]
    reached = False
    for k in range(400):
        step(ent, op, comms, scn, k, rng)
        if np.any(np.isclose(ent.control_quality[blue], op.q_operator)):
            reached = True
            break
    assert reached, f"direct control at comms_level 0 never reached q_operator={op.q_operator}"


def _control_quality_history(seed, params, n_steps=40):
    scn = _span_scenario(**params)
    ent, comms, op, rng = _build(scn, seed=seed)
    hist = []
    for k in range(n_steps):
        step(ent, op, comms, scn, k, rng)
        hist.append(ent.control_quality.copy())
    return np.array(hist)


def test_step_sequence_is_deterministic():
    """Two step sequences with the same seed produce identical control_quality traces."""
    params = {"control_mode": "direct", "comms_level": 3, "n_blue": 5}
    a = _control_quality_history(42, params)
    b = _control_quality_history(42, params)
    assert np.array_equal(a, b)
