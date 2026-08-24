"""`round_robin`: the only service order in the set that reads nothing about the request.

Every other discipline needs something. `edf` and `patient_first` need a deadline field somebody has
to define and populate. `easy_first` and `hard_first` need the console to see what it has been
handed. `fcfs` needs arrival order, which is where the harm comes from. This one needs a counter the
console keeps about its own past behaviour, which no message format has to carry, and that is why it
is worth a discipline of its own rather than a footnote to the random arm.

These tests pin the selection rule, the tie-break, and the property the conjecture rests on, and
they pin the byte-identity of every arm that does not ask for it.
"""
import numpy as np
import pytest

from sandtable.c2 import DISCIPLINES, _pick
from sandtable.scenario import load_scenario
from sandtable.sim import evaluate, run_mission
from conftest import same_run


class _Op:
    """The two fields `_pick_next` reads for this discipline, and nothing else."""

    def __init__(self, disc, served, pending):
        self.queue_discipline = disc
        self.n_ans_v = np.asarray(served)
        self.pending = pending


def _pending(vehicle_ids):
    """`pending` records are (vehicle, arrive, service, deadline); only the first is read here."""
    return {r: (v, 0, 1.0, 20) for r, v in enumerate(vehicle_ids)}


def test_it_is_a_registered_discipline():
    assert "round_robin" in DISCIPLINES


def test_it_serves_whoever_has_been_served_least():
    op = _Op("round_robin", served=[9, 0, 4], pending=_pending([0, 1, 2]))
    assert _pick(op, [0, 1, 2], np.random.default_rng(0), {}) == 1


def test_a_tie_falls_back_to_arrival_order_so_the_null_case_is_fcfs():
    """Ties must not become an arbitrary permutation, or a uniform fleet would look like a
    treatment when nothing was applied."""
    op = _Op("round_robin", served=[3, 3, 3], pending=_pending([0, 1, 2]))
    assert _pick(op, [0, 1, 2], np.random.default_rng(0), {}) == 0
    assert _pick(op, [2, 1], np.random.default_rng(0), {}) == 1


def test_it_ignores_the_deadline_and_the_service_length_it_is_handed():
    """The claim is that it reads nothing about the REQUEST. Give it a pending record whose
    deadline and length both point the other way and it must still pick on the counter."""
    op = _Op("round_robin", served=[0, 7], pending={0: (0, 0, 99.0, 2), 1: (1, 0, 0.1, 99)})
    assert _pick(op, [0, 1], np.random.default_rng(0), {}) == 0
    op.n_ans_v = np.asarray([7, 0])
    assert _pick(op, [0, 1], np.random.default_rng(0), {}) == 1


def _scn(**over):
    scn = load_scenario("scenarios/sc_span_control.json")
    scn.params.update(dict(control_mode="direct", queue_model="buffer", comms_level=0,
                           queue_policy="admit", service_cv=0.5, admit_acuity=1.0,
                           patience_spread=12, patience_shape="twopoint", n_blue=16))
    scn.params.update(over)
    return scn


def test_it_removes_the_exclusion_that_arrival_order_creates():
    """The property the conjecture rests on, at the operating point it is claimed for."""
    fcfs = evaluate(_scn(), n_reps=12, seed=3)
    rr = evaluate(_scn(queue_discipline="round_robin"), n_reps=12, seed=3)
    assert fcfs["starved_frac"] > 0.05
    assert rr["starved_frac"] < fcfs["starved_frac"] / 4.0
    assert rr["answer_step_ratio"] < fcfs["answer_step_ratio"] / 2.0


def test_it_does_not_buy_the_fairness_out_of_the_aggregate():
    """A distributional fix that costs throughput is a trade and would have to be reported as one."""
    fcfs = evaluate(_scn(), n_reps=12, seed=3)
    rr = evaluate(_scn(queue_discipline="round_robin"), n_reps=12, seed=3)
    assert rr["answer_rate_v"] >= fcfs["answer_rate_v"]
    assert rr["served_per_step"] >= fcfs["served_per_step"]


def test_adding_the_discipline_changed_no_arm_that_does_not_ask_for_it():
    """Byte-identity for the default and for one arm of every other discipline, so the new branch
    cannot have perturbed a published number or the RNG stream behind one."""
    for disc in ("fcfs", "random", "edf", "patient_first", "easy_first", "hard_first"):
        over = {} if disc == "fcfs" else {"queue_discipline": disc}
        a = run_mission(_scn(**over), seed=11)
        b = run_mission(_scn(**over), seed=11)
        assert same_run(a, b)


def test_an_unknown_discipline_is_still_refused():
    with pytest.raises(ValueError, match="queue_discipline"):
        run_mission(_scn(queue_discipline="least_recently_used"), seed=0)
