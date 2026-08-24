"""CR-13: vehicles are not phase-locked, and pretending they are inflates the queue.

`entities.py` starts every agent's `decision_cooldown` at zero, so on step 0 all n blue agents
fire a decision event simultaneously and the single operator opens the mission with a burst of n
requests it cannot possibly clear. Everything after that is a recovery from a transient nobody
designed. `params["stagger_decisions"]` draws a uniform starting phase instead.

Off by default, so every number recorded before this landed is reproduced exactly.
"""
from __future__ import annotations

import numpy as np
import pytest

from sandtable import sim
from sandtable.scenario import Scenario, load_scenario
from conftest import same_run

BASE = "scenarios/sc_span_control.json"


def _run(seed=0, **params):
    scn = load_scenario(BASE)
    p = dict(scn.params)
    p.update(params)
    return sim.run_mission(Scenario(**{**scn.__dict__, "params": p}), seed=seed)


def _mean(metric, seeds=range(8), **params):
    return float(np.mean([_run(seed=s, **params)[metric] for s in seeds]))


def test_off_by_default_and_byte_identical():
    for s in range(4):
        a = _run(seed=s, control_mode="direct", n_blue=8)
        b = _run(seed=s, control_mode="direct", n_blue=8, stagger_decisions=False)
        assert same_run(a, b)


def test_starting_phases_are_drawn_inside_one_decision_interval():
    from sandtable import c2
    from sandtable.scenario import build_entities
    from sandtable.seeding import make_rng
    scn = load_scenario(BASE)
    p = dict(scn.params)
    p.update({"control_mode": "direct", "n_blue": 8, "stagger_decisions": True})
    scn = Scenario(**{**scn.__dict__, "params": p})
    rng = make_rng(0, scn.id)
    ent = build_entities(scn, rng)
    op = c2.build_c2(scn, ent, rng)
    phases = op.decision_cooldown_seed
    assert phases is not None
    assert phases.min() >= 0
    assert phases.max() < op.decision_interval
    assert len(set(phases.tolist())) > 1, "a stagger that phase-locks everything is not a stagger"


def test_the_synchronized_start_suppresses_goodput_at_saturated_span():
    """Eight requests on step 0 is more than the operator can ever clear, so the mission opens
    already collapsed. Spreading the first requests out is worth more than any link improvement."""
    sync = _mean("operator_goodput", control_mode="direct", n_blue=8)
    stag = _mean("operator_goodput", control_mode="direct", n_blue=8, stagger_decisions=True)
    assert stag > sync + 0.10, f"expected a large recovery: sync={sync:.3f} stag={stag:.3f}"


def test_it_barely_matters_below_saturation():
    """With two vehicles the operator absorbs the opening burst, so the phase cannot matter much."""
    sync = _mean("operator_goodput", control_mode="direct", n_blue=2)
    stag = _mean("operator_goodput", control_mode="direct", n_blue=2, stagger_decisions=True)
    assert abs(stag - sync) < 0.10, f"sync={sync:.3f} stag={stag:.3f}"


def test_supervisory_is_untouched():
    """No requests, no queue, so a starting phase changes only which step a local decision fires."""
    a = _mean("success", control_mode="supervisory", n_blue=8)
    b = _mean("success", control_mode="supervisory", n_blue=8, stagger_decisions=True)
    assert a == pytest.approx(b, abs=0.15)
