"""CR-15: operator demand that follows the ground, not a clock.

Without this the offered load on the operator is stationary: every vehicle calls for help at the
same average rate wherever it is. Real demand is spatially correlated. A column entering a defile
needs help together, so a queue sized for the average rate meets a burst, and the closed-form
collapse threshold, which assumes stationary arrivals, is optimistic.

`params["terrain_demand"]` scales the inter-decision interval by local trafficability. Off by
default; exactly one integer is drawn either way, so the off path is byte-identical and the two
paths stay paired on a shared seed.
"""
from __future__ import annotations

import numpy as np
import pytest

from sandtable import sim
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
    from conftest import same_run

    for s in range(4):
        assert same_run(_run(seed=s, control_mode="direct", n_blue=6),
                        _run(seed=s, control_mode="direct", n_blue=6, terrain_demand=0.0))


def test_difficult_ground_raises_the_call_rate_and_sinks_goodput():
    """More requests against the same operator is the whole mechanism."""
    flat = _mean("operator_goodput", control_mode="direct", n_blue=6)
    hard = _mean("operator_goodput", control_mode="direct", n_blue=6, terrain_demand=2.0)
    assert hard < flat - 0.2, f"flat={flat:.3f} hard={hard:.3f}"


def test_demand_is_monotone_in_the_coupling_strength():
    g = [_mean("operator_goodput", control_mode="direct", n_blue=6, terrain_demand=t)
         for t in (0.0, 1.0, 2.0, 4.0)]
    assert g == sorted(g, reverse=True), f"not monotone in terrain_demand: {g}"


def test_it_pulls_the_collapse_below_the_published_span():
    """The closed form puts the threshold at 6.3 vehicles for stationary arrivals. Correlated
    arrivals collapse the queue at six, which is the span the centerpiece scenario ships."""
    flat = _mean("operator_goodput", control_mode="direct", n_blue=6)
    hard = _mean("operator_goodput", control_mode="direct", n_blue=6, terrain_demand=2.0)
    assert flat > 0.5, "six vehicles should be just below the stationary threshold"
    assert hard < 0.4, "and above it once demand follows the terrain"


def test_admission_control_still_recovers_it():
    """The remedy does not care why the queue is overloaded, only that it is."""
    hard = _mean("operator_goodput", control_mode="direct", n_blue=6, terrain_demand=2.0)
    fixed = _mean("operator_goodput", control_mode="direct", n_blue=6, terrain_demand=2.0,
                  queue_policy="admit")
    assert fixed > hard + 0.3, f"hard={hard:.3f} fixed={fixed:.3f}"


def test_supervisory_demand_is_also_terrain_driven_but_costs_nothing():
    """A supervisory agent decides locally, so a higher decision rate has no queue to congest."""
    a = _mean("success", control_mode="supervisory", n_blue=6)
    b = _mean("success", control_mode="supervisory", n_blue=6, terrain_demand=2.0)
    assert a == pytest.approx(b, abs=0.2)
