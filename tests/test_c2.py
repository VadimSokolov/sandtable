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


# ---- heterogeneous patience and the two deadline disciplines (CR-46) --------

def test_patience_spread_zero_is_the_published_constant_fleet(skirmish_scenario, rng):
    """The published model gives every requester the same deadline. Spread zero must reproduce it
    as a constant vector, because every claim about ordering rests on that being exact rather
    than nearly so."""
    from sandtable.c2 import _patience_vector

    v = _patience_vector(8, np.arange(6), 20, 0)
    assert v.tolist() == [20] * 8


@pytest.mark.parametrize("m", [2, 5, 6, 8, 10])
@pytest.mark.parametrize("spread", [3, 6, 9, 12])
def test_patience_spread_holds_the_fleet_mean_exactly(m, spread):
    """A dispersion sweep is a second-moment manipulation only if the first moment does not move.
    The collapse span of Equation nstar is linear in patience, so a spread that shifted the mean
    would move the operating point and the contrast would mix two things. The offsets are
    symmetric by construction; this pins that they stay symmetric after rounding."""
    from sandtable.c2 import _patience_vector

    v = _patience_vector(m, np.arange(m), 20, spread)[:m]
    assert abs(float(v.mean()) - 20.0) < 1e-9
    assert v.min() == 20 - spread and v.max() == 20 + spread
    assert list(v) == sorted(v)          # assignment is by position, so the vector is ordered


def test_patience_spread_is_rejected_when_the_floor_truncates_the_low_tail():
    """The `retry_spread` lesson, applied before it can cost anything: a width bound is not a mean
    guard. A spread at or above the mean clips at one step and the arm silently stops holding the
    mean it claims."""
    scn = _span_scenario(control_mode="direct", patience=20, patience_spread=25)
    rng = make_rng(0, scn.id)
    ent = build_entities(scn, rng)
    with pytest.raises(ValueError, match="realized fleet mean"):
        build_c2(scn, ent)


def test_deadline_disciplines_are_identity_orders_on_a_constant_fleet():
    """`edf` and `patient_first` sort on a key that is constant until the fleet is mixed, and the
    sort is stable, so at spread zero both must return the arrival order untouched. This is what
    makes the dispersion sweep identify the ordering effect on its own: the same arm is the
    control at its own zero."""
    from sandtable.c2 import service_order

    class Op:
        queue_discipline = "edf"
        patience_v = np.full(9, 20)

    op, blue = Op(), np.array([3, 1, 7, 4])
    assert service_order(op, blue, {}, None).tolist() == blue.tolist()
    op.queue_discipline = "patient_first"
    assert service_order(op, blue, {}, None).tolist() == blue.tolist()


def test_deadline_disciplines_are_exact_reverses_under_dispersion():
    """The two rules are the prescriptions of two literatures that disagree, so on a fleet with no
    tied deadlines they must be exact opposites. A test that only checked `edf` would pass on an
    implementation where `patient_first` silently fell through to arrival order."""
    from sandtable.c2 import service_order

    class Op:
        queue_discipline = "edf"
        patience_v = np.array([30, 10, 25, 5, 15])

    op, blue = Op(), np.array([0, 1, 2, 3, 4])
    early = service_order(op, blue, {}, None).tolist()
    assert early == [3, 1, 4, 2, 0]            # ascending patience: 5, 10, 15, 25, 30
    op.queue_discipline = "patient_first"
    assert service_order(op, blue, {}, None).tolist() == early[::-1]


def test_a_requester_is_held_to_its_own_deadline_not_the_fleet_mean(skirmish_scenario):
    """The whole mechanism is that `wait <= patience` reads the REQUESTER's patience. A fleet with
    dispersion whose short-deadline members are never refused would mean the vector was built and
    then ignored."""
    from sandtable.sim import run_mission

    flat = run_mission(_span_scenario(control_mode="direct", n_blue=8, patience=20,
                                      queue_policy="admit"), seed=11)
    mixed = run_mission(_span_scenario(control_mode="direct", n_blue=8, patience=20,
                                       patience_spread=12, queue_policy="admit"), seed=11)
    assert flat["patience_sd"] == 0.0 and flat["patience_mean"] == 20.0
    assert mixed["patience_sd"] > 0.0 and abs(mixed["patience_mean"] - 20.0) < 1e-9
    assert mixed["patience_min"] == 8.0
    assert mixed["abandon_queue_frac"] != flat["abandon_queue_frac"]


def test_patience_layout_is_permuted_but_the_multiset_and_mean_are_not():
    """The values are fixed and only their assignment is drawn, because a fleet laid out in index
    order would make `edf` identical to `fcfs` by construction: the operator walks its arrivals in
    index order. This pins that the draw moves WHO gets what and nothing else."""
    from sandtable.c2 import _patience_vector
    from sandtable.seeding import make_rng

    blue = np.arange(8)
    fixed = _patience_vector(8, blue, 20, 12)
    drawn = [_patience_vector(8, blue, 20, 12, make_rng(s, 1)) for s in range(6)]
    assert all(sorted(d.tolist()) == sorted(fixed.tolist()) for d in drawn)
    assert all(abs(float(d.mean()) - 20.0) < 1e-9 for d in drawn)
    assert any(d.tolist() != fixed.tolist() for d in drawn)      # the layout really is permuted


def test_patience_layout_draws_from_a_child_stream_and_leaves_the_parent_alone():
    """A dispersed fleet and a uniform one must see the same mission, otherwise the sweep's own
    baseline contrast is unpaired. `rng.spawn` takes a child of the seed sequence rather than
    drawing, so the parent stream is where it was."""
    from sandtable.c2 import _patience_vector
    from sandtable.seeding import make_rng

    a, b = make_rng(4, 2), make_rng(4, 2)
    _patience_vector(6, np.arange(6), 20, 9, a)
    assert np.allclose(a.random(5), b.random(5))


# ---- the buffered queue model (CR-47) --------------------------------------

def test_reserve_is_the_default_and_is_untouched_by_the_buffer_code(skirmish_scenario):
    """Every published number was produced under `reserve`. The buffer is a second service model,
    not a revision of the first, so the default path must be bit-identical with the new code in."""
    from sandtable.sim import run_mission

    a = run_mission(_span_scenario(control_mode="direct", n_blue=8, queue_policy="admit"), seed=3)
    b = run_mission(_span_scenario(control_mode="direct", n_blue=8, queue_policy="admit",
                                   queue_model="reserve"), seed=3)
    assert a == b


def test_build_c2_rejects_an_unknown_queue_model(skirmish_scenario, rng):
    scn = skirmish_scenario.with_params({"control_mode": "direct", "queue_model": "carousel"})
    with pytest.raises(ValueError, match="queue_model"):
        build_c2(scn, build_entities(scn, rng), rng)


def test_the_buffer_starts_work_at_the_fractional_free_time():
    """One service is 1/mu steps and 1/mu is not an integer. Dispatching only on integer steps
    would round every service up and cost capacity that has nothing to do with queueing: at
    mu = 0.15 the console would deliver 1/7 = 0.1429 rather than 0.15, a four percent cut. The
    served rate under a policy that never over-commits is the check."""
    from sandtable.sim import run_mission

    m = run_mission(_span_scenario(control_mode="direct", n_blue=16, comms_level=0,
                                   queue_policy="admit", queue_model="buffer"), seed=5)
    assert m["served_per_step"] > 0.1429


def test_a_stale_request_is_worked_and_counted_but_never_answers_its_requester():
    """The waste `blind` is named for, in its sharpest form: a requester whose patience ran out
    asks again while its first request is still in the backlog, the console works the first one,
    and the answer lands on a request nobody is holding. `reserve` cannot represent this at all."""
    from sandtable.sim import run_mission

    blind = run_mission(_span_scenario(control_mode="direct", n_blue=12, comms_level=0,
                                       queue_policy="blind", queue_model="buffer"), seed=5)
    admit = run_mission(_span_scenario(control_mode="direct", n_blue=12, comms_level=0,
                                       queue_policy="admit", queue_model="buffer"), seed=5)
    assert blind["stale_frac"] > 0.3          # most of a blind console's work, at this span
    assert admit["stale_frac"] == 0.0         # a refused request leaves the queue before it can go stale
    assert blind["backlog_mean"] > admit["backlog_mean"]


def test_newest_first_beats_oldest_first_on_an_overloaded_blind_console():
    """The CR-47 mechanism, at one seed and one span, so a regression that inverted the discipline
    would be caught here rather than in a battery. The tier result is what the paper reports."""
    from sandtable.sim import run_mission

    def go(disc):
        return run_mission(_span_scenario(control_mode="direct", n_blue=12, comms_level=0,
                                          queue_policy="blind", queue_model="buffer",
                                          queue_discipline=disc), seed=5)["served_per_step"]

    assert go("patient_first") > 10 * go("fcfs")


def test_queue_capacity_defaults_to_unbounded_and_zero_is_a_real_setting():
    """Zero must mean "hold no backlog", not "no bound", because the sizing rule prescribes zero
    once the link is slow enough. The unbounded sentinel is therefore negative."""
    from sandtable.sim import run_mission

    scn = _span_scenario(control_mode="direct", n_blue=12, comms_level=0,
                         queue_model="buffer", queue_policy="blind")
    default = run_mission(scn, seed=5)
    explicit = run_mission(scn.with_params({**scn.params, "queue_capacity": -1}), seed=5)
    assert default == explicit
    zero = run_mission(scn.with_params({**scn.params, "queue_capacity": 0}), seed=5)
    assert zero["served_per_step"] > 0.0        # a free console still serves what arrives to it
    assert zero["backlog_mean"] < 1.0


def test_the_bound_counts_what_has_arrived_not_what_is_in_flight():
    """A request still travelling occupies nothing the console owns. Counting it would make a
    capacity of zero mean "serve nothing" on any link with latency, which is a different and much
    stronger policy than the one being tested."""
    from sandtable.sim import run_mission

    m = run_mission(_span_scenario(control_mode="direct", n_blue=12, comms_level=3,
                                   queue_model="buffer", queue_policy="blind",
                                   queue_capacity=0), seed=5)
    assert m["served_per_step"] > 0.0


def test_the_derived_bound_sits_on_a_plateau_that_beats_everything_outside_it():
    """k* = floor((P - 2L) mu) - 1 is 2 at the published operating point, and a bound of 1 measures
    the same to within noise at any sample size a unit test can afford (0.1279 vs 0.1275, se 0.004,
    12 seeds). So the fixture asserts what is resolvable here: the {1, 2} plateau beats 0, beats 3,
    and beats unbounded by a factor of three. Separating 1 from 2 is the battery's job, not this
    file's. A regression in the trim, the sentinel, or the in-flight rule moves the plateau."""
    from sandtable.sim import run_mission

    def go(cap):
        return np.mean([run_mission(_span_scenario(control_mode="direct", n_blue=8, comms_level=0,
                                                   queue_model="buffer", queue_policy="blind",
                                                   queue_capacity=cap), seed=s)["served_per_step"]
                        for s in range(12)])

    plateau = min(go(1), go(2))
    assert plateau > go(0) * 1.2
    assert plateau > go(3) * 1.2
    assert plateau > go(-1) * 2.0


def test_a_length_cap_measured_in_time_is_the_arrival_rate_in_disguise():
    """The mechanism behind the sizing rule's load dependence, checked in the auxiliary queue model
    rather than asserted. A request entering a full buffer of k advances one place per removal, and
    at equilibrium removals (services plus drop-oldest evictions) happen at the ARRIVAL rate, so the
    age of the request the console picks up is about (k-1)/Lambda. Holding k fixed and tripling the
    arrival rate should therefore cut that age to about a third."""
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    from queue_kstar import simulate

    def age(n, k):
        r = [simulate(n, 20, 0, 0.15, k, 22.0, 40000, 1000 + s, "fifo") for s in range(4)]
        return (sum(x["age"] for x in r) / 4, sum(x["arr_rate"] for x in r) / 4)

    for k in (4, 6):
        a8, lam8 = age(8, k)
        a24, lam24 = age(24, k)
        assert lam24 > 2.5 * lam8                       # the load really did move
        assert 0.85 < a8 / ((k - 1) / lam8) < 1.15      # the form holds at both ends
        assert 0.85 < a24 / ((k - 1) / lam24) < 1.35
        assert a24 < 0.5 * a8                           # same cap, less than half the delay
