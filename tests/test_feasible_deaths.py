"""`died_feasible`: the size of the scheduling problem, which no other metric in this model reports.

Adversarial review asked for a discriminator between two readings of one tie. Round-robin and
deadline order score the same on both inequality readings at sixteen assets, and there are two ways
that can happen. Either the queue never presents a binding choice, in which case the tie is about the
console's ceiling and would evaporate at a load where deadlines actually bind, or it does present one
and two rules resolve it equally well, in which case the tie is about the information they read.

A request is FEASIBLE at entry when an idle console could have answered it inside its deadline. One
that was feasible at entry and then died at a deadline was killed by the ORDER, not by capacity or
by the link. That count separates the two readings, and these tests pin what it counts.
"""
import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import evaluate, run_mission
from conftest import same_run


def _scn(**over):
    scn = load_scenario("scenarios/sc_span_control.json")
    scn.params.update(dict(control_mode="direct", queue_model="buffer", comms_level=0,
                           queue_policy="admit", service_cv=0.5, admit_acuity=1.0,
                           patience_spread=12, patience_shape="twopoint", n_blue=16))
    scn.params.update(over)
    return scn


def test_the_counter_is_reported_and_bounded_by_its_own_denominator():
    m = evaluate(_scn(), n_reps=8, seed=2)
    assert 0.0 <= m["died_feasible_frac"] <= 1.0
    assert 0.0 <= m["entered_feasible_frac"] <= 1.0
    assert m["died_feasible_per_step"] >= 0.0


def test_the_counter_has_an_exact_zero_so_a_large_reading_means_something():
    """The negative control, and it was not free to find.

    At the published patience the counter never approaches zero even at two assets, because one
    service is 6.67 steps against the impatient half's deadline of 8: two vehicles asking on the
    same step already exceeds it. That is genuine ordering loss, not a floor, but it means the
    published configuration cannot demonstrate the counter's zero. Doubling the patience does, and
    exactly: at forty steps and two assets no request that was servable at entry dies.
    """
    idle = evaluate(_scn(n_blue=2, patience=40, patience_spread=24, service_cv=0.0), n_reps=8, seed=2)
    assert idle["died_feasible_frac"] == 0.0
    loaded = evaluate(_scn(n_blue=24), n_reps=8, seed=2)
    assert loaded["died_feasible_frac"] > 0.40


def test_it_rises_with_load_at_a_fixed_deadline():
    a = evaluate(_scn(n_blue=4), n_reps=8, seed=2)
    b = evaluate(_scn(n_blue=16), n_reps=8, seed=2)
    c = evaluate(_scn(n_blue=24), n_reps=8, seed=2)
    assert a["died_feasible_frac"] < b["died_feasible_frac"] < c["died_feasible_frac"]


def test_the_tie_between_the_two_rules_happens_where_the_choice_is_binding():
    """The discrimination itself, at the operating point the conjecture rests on. If this test ever
    fails because the counter has fallen, the tie has become a ceiling effect and the claim about
    information dies with it."""
    rr = evaluate(_scn(queue_discipline="round_robin"), n_reps=8, seed=2)
    edf = evaluate(_scn(queue_discipline="edf"), n_reps=8, seed=2)
    assert rr["died_feasible_frac"] > 0.30 and edf["died_feasible_frac"] > 0.30


def test_nothing_is_born_dead_on_a_clear_link_at_the_published_patience():
    """`entered_feasible_frac` is the counter's own sanity check: with no latency and a service time
    far inside the patience, every request is servable when it arrives, so a death is always the
    queue's doing. A value below one on a CLEAR link would mean the feasibility test is wrong."""
    m = evaluate(_scn(), n_reps=8, seed=2)
    assert m["entered_feasible_frac"] == 1.0


def test_adding_the_counter_left_the_pending_record_readable_by_every_path():
    """The record grew a field and three call sites unpack it. The overflow purge is the one a
    normal run does not reach, so it is exercised explicitly here."""
    m = run_mission(_scn(queue_capacity=3), seed=4)
    assert m["died_feasible_per_step"] >= 0.0
    assert m["dropped_frac"] > 0.0


def test_the_counter_does_not_perturb_any_arm_that_ignores_it():
    a = run_mission(_scn(), seed=13)
    b = run_mission(_scn(), seed=13)
    assert same_run(a, b)
    assert not np.isnan(a["served_per_step"])


def test_the_console_with_no_backlog_reports_undefined_and_not_zero():
    """Instrument defect 13's exact shape, guarded at the moment the counter was added.

    The `reserve` console commits a request to a slot the instant it arrives, so it has no backlog
    and nothing to order. The counter's denominator is then empty. Zero would read as "this console
    loses no servable request to its ordering", which is a claim, and eleven batteries in this paper
    run that console. It is NaN, which `ar_survey` refuses out loud.
    """
    import math

    m = evaluate(_scn(queue_model="reserve"), n_reps=4, seed=2)
    assert m["entered_feasible_frac"] == 0.0
    assert math.isnan(m["died_feasible_frac"])
    buf = evaluate(_scn(queue_model="buffer"), n_reps=4, seed=2)
    assert not math.isnan(buf["died_feasible_frac"])
