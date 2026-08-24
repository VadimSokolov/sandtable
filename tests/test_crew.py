"""CR-14: the operator generalized to a crew of consoles.

The span-of-control study asks how many vehicles one operator can hold. The question a command
post actually faces is how many operators a given formation needs, which is the same queue read
the other way round. `params["n_operators"]` sets the number of consoles, each serving at
`service_rate`. One console is the default and reproduces the published single server exactly.
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


def test_one_console_is_the_default_and_byte_identical():
    for s in range(4):
        assert same_run(_run(seed=s, control_mode="direct", n_blue=8),
                        _run(seed=s, control_mode="direct", n_blue=8, n_operators=1))


def test_zero_operators_is_rejected():
    with pytest.raises(ValueError, match="n_operators"):
        _run(control_mode="direct", n_operators=0)


def test_a_second_console_clears_the_collapsed_queue():
    """Theory puts the one-console threshold at 6.3 vehicles and the two-console one at 12.6,
    so eight vehicles straddle them and the second operator should be transformational."""
    solo = _mean("operator_goodput", control_mode="direct", n_blue=8, n_operators=1)
    pair = _mean("operator_goodput", control_mode="direct", n_blue=8, n_operators=2)
    assert solo < 0.35 and pair > 0.90, f"solo={solo:.3f} pair={pair:.3f}"


def test_extra_consoles_past_the_threshold_stop_helping():
    """Once nothing queues, more operators only lower utilization."""
    g3 = _mean("operator_goodput", control_mode="direct", n_blue=8, n_operators=3)
    g4 = _mean("operator_goodput", control_mode="direct", n_blue=8, n_operators=4)
    assert g3 == pytest.approx(g4, abs=0.02)
    u3 = _mean("operator_utilization", control_mode="direct", n_blue=8, n_operators=3)
    u4 = _mean("operator_utilization", control_mode="direct", n_blue=8, n_operators=4)
    assert u4 < u3, "adding a console must spread the same work thinner"


def test_admission_control_substitutes_for_part_of_a_second_operator():
    """The decision-relevant comparison: an interface feature against a person."""
    solo = _mean("operator_goodput", control_mode="direct", n_blue=8)
    solo_admit = _mean("operator_goodput", control_mode="direct", n_blue=8,
                       queue_policy="admit")
    pair = _mean("operator_goodput", control_mode="direct", n_blue=8, n_operators=2)
    assert solo < solo_admit < pair
    assert solo_admit - solo > 0.5 * (pair - solo), "should recover most of the crew's gain"
