"""polarisopt plugins: MissionScoreMetric scoring and MissionSimulator construction guards."""
from __future__ import annotations

import pytest

pytest.importorskip("polarisopt")

from polarisopt.metrics.base import MetricError            # noqa: E402
from polarisopt.simulator.base import SimulatorError       # noqa: E402

from sandtable.opt_metrics import MissionScoreMetric             # noqa: E402
from sandtable.plugin import MissionSimulator                    # noqa: E402

BASE_OUTPUT = {"success_rate": 0.5, "time_to_objective": 600.0, "blue_loss_frac": 0.2}


def test_compute_returns_shape_one_scalar():
    j = MissionScoreMetric().compute(BASE_OUTPUT)
    assert j.shape == (1,)


def test_score_increases_with_blue_loss_frac():
    m = MissionScoreMetric()
    base = float(m.compute(BASE_OUTPUT)[0])
    worse = float(m.compute({**BASE_OUTPUT, "blue_loss_frac": 0.6})[0])
    assert worse > base


def test_score_increases_with_time_to_objective():
    m = MissionScoreMetric()
    base = float(m.compute(BASE_OUTPUT)[0])
    slower = float(m.compute({**BASE_OUTPUT, "time_to_objective": 1200.0})[0])
    assert slower > base


def test_negative_weight_raises():
    for bad in ({"w_fail": -1.0}, {"w_time": -0.1}, {"w_loss": -0.5}):
        with pytest.raises(MetricError):
            MissionScoreMetric(**bad)


def test_nonpositive_time_scale_raises():
    with pytest.raises(MetricError):
        MissionScoreMetric(time_scale=0.0)
    with pytest.raises(MetricError):
        MissionScoreMetric(time_scale=-1800.0)


def test_simulator_bad_scenario_path_raises():
    with pytest.raises(SimulatorError):
        MissionSimulator(scenario="/no/such/scenario/path.json")


def test_simulator_nonpositive_repeats_raises(uc3_path):
    with pytest.raises(SimulatorError):
        MissionSimulator(scenario=uc3_path, n_repeats=0)
