"""CR-16: what order the operator works its arrivals in.

The proposal this replaced was "serve the request with the least remaining patience," which cannot
do anything in this model: every requester carries the same patience and a request's completion
time is fixed at arrival, so all competing requests have identical slack and reordering two
feasible ones only swaps which vehicle is served. That leaves one thing order can change, whether
the vehicle that gets helped is one for which the help is worth much, so the priority arms key on
terrain rather than on the request.

The arms carry their own controls. `random` is the null: reordering the loop also reassigns which
entity draws which random number, so a priority arm moves two things at once and only the gap
against `random` is priority. `easy_first` is the adversary for `hard_first`.
"""
from __future__ import annotations

import numpy as np
import pytest

from sandtable import sim
from sandtable.c2 import DISCIPLINES, Operator, service_order
from sandtable.scenario import Scenario, load_scenario

BASE = "scenarios/sc_span_control.json"


def _run(seed=0, **params):
    scn = load_scenario(BASE)
    p = dict(scn.params)
    p.update(params)
    return sim.run_mission(Scenario(**{**scn.__dict__, "params": p}), seed=seed)


def _mean(metric, seeds=range(8), **params):
    return float(np.mean([_run(seed=s, **params)[metric] for s in seeds]))


def test_off_by_default_and_byte_identical():
    """`fcfs` must leave `blue` exactly as np.nonzero produced it."""
    from conftest import same_run

    for s in range(4):
        assert same_run(_run(seed=s, control_mode="direct", n_blue=8),
                        _run(seed=s, control_mode="direct", n_blue=8, queue_discipline="fcfs"))


def _op(discipline):
    return Operator(mode="direct", service_rate=0.15, q_operator=0.9, q_auto=0.7, q_fallback=0.5,
                    q_stall=0.3, patience=20, decision_interval=22, queue_discipline=discipline)


def test_priority_sorts_by_difficulty_in_both_directions():
    blue = np.array([2, 5, 7, 9])
    diff = {2: 0.1, 5: 0.9, 7: 0.1, 9: 0.4}
    rng = np.random.default_rng(0)
    assert list(service_order(_op("hard_first"), blue, diff, rng)) == [5, 9, 2, 7]
    assert list(service_order(_op("easy_first"), blue, diff, rng)) == [2, 7, 9, 5]
    assert list(service_order(_op("fcfs"), blue, diff, rng)) == [2, 5, 7, 9]


def test_priority_degenerates_to_fcfs_on_uniform_ground():
    """The sort is stable, so with no difficulty spread the priority arms must reduce to arrival
    order rather than to an arbitrary permutation. This is what makes a flat result at
    terrain_demand=0 interpretable: it says ordering did nothing, not that the order was scrambled.
    Asserted on the helper because the procedural terrain always carries noise, so no scenario can
    supply genuinely uniform ground."""
    blue = np.array([2, 5, 7, 9])
    flat = {int(i): 0.5 for i in blue}
    rng = np.random.default_rng(0)
    for d in ("hard_first", "easy_first"):
        assert list(service_order(_op(d), blue, flat, rng)) == list(blue), d
    # And with no difficulty map at all (terrain-blind scenario), likewise.
    for d in ("hard_first", "easy_first"):
        assert list(service_order(_op(d), blue, {}, rng)) == list(blue), d


def test_random_order_perturbs_the_run_but_not_the_throughput_identity():
    """The null control must actually reorder (otherwise it controls for nothing) while leaving
    the number of requests the operator can serve statistically unchanged."""
    fcfs = _run(seed=0, control_mode="direct", n_blue=8)
    rand = _run(seed=0, control_mode="direct", n_blue=8, queue_discipline="random")
    assert fcfs != rand, "random discipline did not perturb the run at all"
    a = _mean("operator_goodput", control_mode="direct", n_blue=8)
    b = _mean("operator_goodput", control_mode="direct", n_blue=8, queue_discipline="random")
    assert abs(a - b) < 0.15, f"reordering alone moved goodput a lot: fcfs={a:.3f} random={b:.3f}"


@pytest.mark.parametrize("d", DISCIPLINES)
def test_every_discipline_runs_and_conserves_requests(d):
    m = _run(seed=1, control_mode="direct", n_blue=8, terrain_demand=2.0, queue_discipline=d)
    assert 0.0 <= m["operator_goodput"] <= 1.0
    assert 0.0 <= m["abandon_queue_frac"] <= 1.0


def test_bad_discipline_is_rejected():
    scn = load_scenario(BASE)
    p = dict(scn.params, control_mode="direct", queue_discipline="shortest_job")
    bad = Scenario(**{**scn.__dict__, "params": p})
    with pytest.raises(ValueError, match="queue_discipline"):
        sim.run_mission(bad, seed=0)


def test_ordering_alone_does_not_change_how_many_requests_are_served():
    """The model-level claim behind the whole redesign: order can change WHICH vehicle is helped
    but not HOW MANY are. Serviced-request counts are compared, not mission success, because
    success also absorbs where the helped vehicle happened to be."""
    kw = dict(control_mode="direct", n_blue=8, terrain_demand=2.0)
    served = {d: _mean("operator_goodput", seeds=range(16), queue_discipline=d, **kw)
              for d in DISCIPLINES}
    spread = max(served.values()) - min(served.values())
    assert spread < 0.10, f"ordering moved goodput by {spread:.3f}: {served}"
