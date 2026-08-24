"""A console that recognises a superseded request before working it, not after.

`req_seq` is the console's own record of what each vehicle last asked. It is maintained on the
arrival path and no message field carries it, so a console that consults it before starting work is
using nothing it was not already holding. The published console does not consult it: it claims the
slot, works the request, and only then discovers that the requester gave up long ago. The knob is
what separates those two consoles, and it is an interface difference rather than an information one.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SCN = load_scenario("scenarios/sc_span_control.json")

# Twelve assets and above is where the blind buffer console spends most of its clock on ghosts; the
# pilot reads busy_stale 0.95 there and 0.20 at eight, so the collapsing arm is the one to test on.
COLLAPSED = dict(control_mode="direct", comms_level=0, queue_model="buffer",
                 queue_policy="blind", n_blue=16)


def _run(seed=0, **kw):
    return run_mission(SCN.with_params({**SCN.params, **COLLAPSED, **kw}), seed=seed)


def _mean(metric, seeds=range(8), **kw):
    return float(np.mean([_run(seed=s, **kw)[metric] for s in seeds]))


def test_after_is_the_default_and_naming_it_changes_nothing():
    for s in range(4):
        assert same_run(_run(seed=s), _run(seed=s, stale_check="after"))


def test_an_unknown_value_is_rejected():
    with pytest.raises(ValueError, match="stale_check"):
        _run(stale_check="sometimes")


def test_the_early_check_removes_the_wasted_effort_entirely():
    """Not "reduces": a record recognised from the books costs no service time at all, so the
    time-weighted waste is exactly zero rather than small."""
    assert _mean("busy_stale") > 0.5                      # the console being repaired
    assert _mean("busy_stale", stale_check="before") == 0.0


def test_the_two_buckets_are_disjoint():
    """`n_stale` means "worked, then found to have no requester" and is divided by in three effort
    metrics. A record dropped for free is not work and gets its own counter, or a console that
    wastes nothing would report the same effort as one that wastes everything."""
    assert _mean("stale_frac") > 0.0
    assert _mean("stale_dropped_frac") == 0.0
    assert _mean("stale_frac", stale_check="before") == 0.0
    assert _mean("stale_dropped_frac", stale_check="before") > 0.0


def test_the_per_job_service_time_is_untouched():
    """The knob changes which jobs are worked, never how long one takes. If this moves, the arm is
    buying its throughput from a cheaper server rather than from a better queue."""
    a = _mean("svc_worked_mean")
    b = _mean("svc_worked_mean", stale_check="before")
    assert a == pytest.approx(b, abs=1e-9)


def test_the_effort_moves_rather_than_disappears():
    """The result the knob exists to establish. Freed effort does not become throughput on a console
    that cannot refuse: it becomes work on live requests that still miss their deadline."""
    late_after = _mean("busy_late")
    late_before = _mean("busy_late", stale_check="before")
    assert late_before > late_after + 0.5
    served_after = _mean("served_per_step")
    served_before = _mean("served_per_step", stale_check="before")
    assert served_before - served_after < 0.009        # inside the project's rate floor


def test_the_knob_is_inert_where_nothing_goes_stale():
    """An admitting console never carries a superseded record to the head, so the branch is never
    taken and the run is bit-identical, RNG stream included."""
    for s in range(4):
        assert same_run(_run(seed=s, queue_policy="admit"),
                        _run(seed=s, queue_policy="admit", stale_check="before"))


def test_effort_still_accounts_for_the_whole_clock():
    for kw in ({}, {"stale_check": "before"}):
        m = _run(seed=1, **kw)
        parts = m["busy_serviced"] + m["busy_stale"] + m["busy_late"] + m["busy_lost"]
        assert parts == pytest.approx(m["busy_total"], abs=1e-9)


# --- the dead-clock sum, and the cadence that manufactures the ghosts ---------------------------

def test_dead_clock_is_the_sum_of_the_three_ways_to_produce_no_answer():
    for kw in ({}, {"stale_check": "before"}, {"queue_capacity": 2}):
        m = _run(seed=2, **kw)
        assert m["busy_dead"] == pytest.approx(m["busy_stale"] + m["busy_late"] + m["busy_lost"],
                                               abs=1e-9)
        assert m["busy_total"] == pytest.approx(m["busy_dead"] + m["busy_serviced"], abs=1e-9)


def test_the_repair_relabels_the_dead_clock_rather_than_removing_it():
    """The reason `busy_dead` exists. Adversarial review asked for the sum beside the bucket that
    falls, because a reader shown only `busy_stale` going to zero would read a relabelling as a
    recovery. At sixteen assets it is a relabelling."""
    assert _mean("busy_dead") > 0.9
    assert _mean("busy_dead", stale_check="before") > 0.9


def test_reask_cadence_is_inert_at_its_published_value():
    for s in range(4):
        assert same_run(_run(seed=s), _run(seed=s, reask_hold=1.0))


def test_reask_cadence_is_rejected_at_zero_and_below():
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError, match="reask_hold"):
            _run(reask_hold=bad)


def test_the_cadence_knob_moves_the_hold_it_is_supposed_to_move():
    """A control that does nothing is not a control, so the knob is checked where it acts rather
    than on an aggregate that could absorb it. The hold a give-up applies is read directly."""
    from sandtable import c2

    applied = []
    original = c2._give_up

    def spy(op, ent, i, arrive, hold, rng):
        original(op, ent, i, arrive, hold, rng)
        applied.append((int(hold), int(ent.await_until[i]) - int(arrive)))

    c2._give_up = spy
    try:
        _run(seed=3)
        base = [(a, b) for a, b in applied if a > 0]
        applied.clear()
        _run(seed=3, reask_hold=8.0)
        eight = [(a, b) for a, b in applied if a > 0]
    finally:
        c2._give_up = original

    assert base and eight, "no give-up with a positive hold was exercised"
    assert all(b == a for a, b in base)              # published value passes the hold through
    assert all(b == 8 * a for a, b in eight)         # and the knob scales exactly what it says


def test_a_zero_hold_stays_zero_at_every_multiplier():
    """An admitting console at zero latency passes a hold of zero, meaning a refused vehicle may
    ask again on the next step. A floor would make the knob move that console at every multiplier
    except its own default, which is a discontinuity at exactly the value the control nests."""
    for s in range(3):
        assert same_run(_run(seed=s, queue_policy="admit"),
                        _run(seed=s, queue_policy="admit", reask_hold=16.0))


def test_slower_re_asking_is_itself_a_repair_at_the_collapse_edge():
    """The finding the control turned up. At eight assets the ghosts ARE manufactured by the
    cadence, and asking half as often doubles what the console delivers. At sixteen it is inert,
    which is why the battery carries both spans."""
    edge = dict(n_blue=8)
    fast = _mean("served_per_step", seeds=range(12), **edge)
    slow = _mean("served_per_step", seeds=range(12), reask_hold=2.0, **edge)
    assert slow > 1.5 * fast
    assert _mean("busy_stale", seeds=range(12), **edge) > 0.15
    assert _mean("busy_stale", seeds=range(12), reask_hold=2.0, **edge) < 0.05


def test_the_ghost_clock_does_not_follow_the_cadence():
    """The registered prediction for the CR-65 control section, pinned here so a later change to the
    give-up path cannot quietly turn the result into a property of one re-ask rate."""
    lo = _mean("busy_stale", reask_hold=0.5)
    hi = _mean("busy_stale", reask_hold=8.0)
    assert abs(hi - lo) < 0.06 * lo
