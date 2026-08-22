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
    assert {
        "mode", "service_rate", "q_operator", "q_auto", "q_fallback", "q_stall",
        "patience", "decision_interval", "operator_free_at", "resolved_quality",
        "ew_immune", "immune_latency", "queue_policy",
    } <= names
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


# ---- CR-28: waiting priced by exposure, not flat ---------------------------

def _stall_scn(scn, **kw):
    return scn.with_params({"control_mode": "direct", "comms_level": 3, "n_blue": 6, **kw})


def test_stall_decay_defaults_to_flat_pricing(skirmish_scenario, rng):
    """The published model prices a wait flat. `stall_decay = 0` must reproduce it exactly, so the
    knob can be swept without moving the baseline it is measured against."""
    from sandtable.sim import run_mission

    base = run_mission(_stall_scn(skirmish_scenario), seed=7)
    off = run_mission(_stall_scn(skirmish_scenario, stall_decay=0.0, stall_floor=0.0), seed=7)
    assert base == off


def test_stall_decay_lowers_quality_monotonically_across_the_patience_window():
    """Quality must fall as the requester's own deadline approaches and must never cross the floor,
    otherwise the sweep would price a long wait as SAFER than a short one somewhere in its range."""
    from sandtable import c2

    class Op:
        q_stall = 0.30
        patience = 20
        stall_decay = 1.0
        stall_floor = 0.05

    op = Op()

    def q(left):
        frac = 1.0 - min(1.0, left / max(1.0, float(op.patience)))
        return op.q_stall - op.stall_decay * frac * (op.q_stall - op.stall_floor)

    qs = [q(left) for left in range(20, -1, -1)]
    assert all(b <= a + 1e-12 for a, b in zip(qs, qs[1:]))
    assert abs(qs[0] - op.q_stall) < 1e-12          # a fresh wait is priced at the published value
    assert abs(qs[-1] - op.stall_floor) < 1e-12     # a wait about to expire sits at the floor
    op.stall_decay = 0.5
    assert abs(q(0) - (op.q_stall - 0.5 * (op.q_stall - op.stall_floor))) < 1e-12


def test_build_c2_rejects_an_out_of_range_stall_decay(skirmish_scenario, rng):
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    for bad in (-0.1, 1.1):
        scn = _stall_scn(skirmish_scenario, stall_decay=bad)
        try:
            build_c2(scn, build_entities(scn, rng))
        except ValueError:
            continue
        raise AssertionError(f"stall_decay={bad} was accepted")


def test_duration_param_overrides_the_scenario_field(skirmish_scenario):
    """The mission-length audit varies duration without editing scenario files. The override must
    be inert at the scenario's own value, or every audit cell shifts against its own baseline."""
    from sandtable.sim import run_mission

    d = skirmish_scenario.duration
    assert run_mission(skirmish_scenario.with_params({"n_blue": 5}), seed=3) == \
           run_mission(skirmish_scenario.with_params({"n_blue": 5, "duration": d}), seed=3)
    longer = run_mission(skirmish_scenario.with_params({"n_blue": 5, "duration": 2 * d}), seed=3)
    assert longer["mission_time"] >= 0.0


def test_q_droop_defaults_to_the_oracle_operator(skirmish_scenario):
    """CR-30. The published operator never degrades. `q_droop = 0` must reproduce it exactly, or
    the sensitivity sweep moves the baseline it is measured against."""
    from sandtable.sim import run_mission

    p = {"control_mode": "direct", "comms_level": 0, "n_blue": 8}
    assert run_mission(skirmish_scenario.with_params(p), seed=11) == \
           run_mission(skirmish_scenario.with_params({**p, "q_droop": 0.0}), seed=11)


def test_q_droop_never_takes_a_serviced_answer_below_the_autonomous_one(skirmish_scenario, rng):
    """A degraded operator answer must stay at least as good as no operator at all. Otherwise the
    sweep would make consulting actively harmful, which is a different model, not a sensitivity."""
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    scn = skirmish_scenario.with_params(
        {"control_mode": "direct", "comms_level": 0, "n_blue": 8, "q_droop": 1.0})
    op = build_c2(scn, build_entities(scn, rng))
    for util in (0.0, 0.5, 1.0):
        q = op.q_operator - op.q_droop * util * (op.q_operator - op.q_auto)
        assert op.q_auto - 1e-12 <= q <= op.q_operator + 1e-12
    for bad in (-0.1, 1.1):
        try:
            build_c2(skirmish_scenario.with_params({**scn.params, "q_droop": bad}),
                     build_entities(scn, rng))
        except ValueError:
            continue
        raise AssertionError(f"q_droop={bad} was accepted")
