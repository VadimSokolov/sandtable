"""Mission scoring: KPI dict contract, success rule, and blue_at_goal geometry."""
from __future__ import annotations

from sandtable.entities import BLUE, RED, Entities
from sandtable.scenario import Objective, PlatformType, Scenario
from sandtable import metrics

EXPECTED_KEYS = {
    "success",
    "time_to_objective",
    "blue_losses",
    "red_losses",
    "blue_survivors",
    "arrived",
    "blue_loss_frac",
    "red_loss_frac",
    "loss_exchange",
    "mission_time",
}


def _scn(goal_radius=100.0, survive_fraction=0.5, duration=300.0):
    return Scenario(
        name="m",
        size=(2000.0, 1000.0),
        platform_types={"u": PlatformType("u")},
        forces=[],
        objective=Objective(goal=(1000.0, 500.0), goal_radius=goal_radius,
                            survive_fraction=survive_fraction),
        duration=duration,
    )


def _entities():
    # 0,1 blue on goal; 2 blue far; 3 red on goal; 4 red dead
    e = Entities.allocate(5)
    e.side[:] = [BLUE, BLUE, BLUE, RED, RED]
    e.x[:] = [1000.0, 1010.0, 50.0, 1000.0, 1000.0]
    e.y[:] = [500.0, 500.0, 500.0, 500.0, 500.0]
    e.alive[4] = False
    return e


def test_compute_returns_all_keys_as_floats():
    scn = _scn()
    e = _entities()
    d = metrics.compute(scn, {BLUE: 4, RED: 2}, e, t_reached=120.0, t_elapsed=120.0)
    assert set(d.keys()) == EXPECTED_KEYS
    for k, v in d.items():
        assert isinstance(v, float), f"{k} is {type(v).__name__}, expected float"


def test_blue_at_goal_matches_geometry():
    scn = _scn()
    e = _entities()
    mask = metrics.blue_at_goal(e, scn)
    # only living blue within the goal radius: indices 0 and 1 (2 is far, 3/4 are red)
    assert mask.tolist() == [True, True, False, False, False]


def test_success_when_enough_blue_at_goal():
    scn = _scn(survive_fraction=0.5)      # need >= 2 of 4 blue arrived
    e = _entities()                       # 2 blue on the goal
    d = metrics.compute(scn, {BLUE: 4, RED: 2}, e, t_reached=120.0, t_elapsed=120.0)
    assert d["success"] == 1.0
    assert d["arrived"] == 2.0


def test_failure_when_too_few_blue_at_goal():
    scn = _scn(survive_fraction=0.75)     # need >= 3 of 4; only 2 arrived
    e = _entities()
    d = metrics.compute(scn, {BLUE: 4, RED: 2}, e, t_reached=None, t_elapsed=300.0)
    assert d["success"] == 0.0
    # a run that never reached the goal is charged the full mission duration
    assert d["time_to_objective"] == scn.duration


def test_loss_bookkeeping():
    scn = _scn()
    e = _entities()
    d = metrics.compute(scn, {BLUE: 4, RED: 2}, e, t_reached=120.0, t_elapsed=120.0)
    assert d["blue_survivors"] == 3.0     # 3 blue alive of 4
    assert d["blue_losses"] == 1.0
    assert d["red_losses"] == 1.0         # 1 red dead of 2
    assert d["blue_loss_frac"] == 0.25
    assert d["red_loss_frac"] == 0.5
