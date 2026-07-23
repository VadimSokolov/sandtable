"""Mission scoring: KPI dict contract, success rule, and blue_at_goal geometry."""
from __future__ import annotations

from sandtable.entities import AIR, BLUE, GROUND, RED, Entities
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
    "blue_air_losses",
    "blue_ground_losses",
    "blue_cost_lost",
    "cost_exchange",
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


def test_cost_exchange_defaults_to_loss_exchange():
    """With no per-platform cost params (all costs 1), the cost-weighted exchange reduces EXACTLY to
    the count-based loss_exchange, so every prior scenario's numbers are unchanged."""
    scn = _scn()
    e = _entities()                       # all-ground blue, air0 defaults to 0
    d = metrics.compute(scn, {BLUE: 4, RED: 2}, e, t_reached=120.0, t_elapsed=120.0)
    assert d["blue_air_losses"] == 0.0
    assert d["blue_ground_losses"] == d["blue_losses"]
    assert d["cost_exchange"] == d["loss_exchange"]


def _mixed_entities():
    # idx0 ground blue alive, idx1 ground blue dead, idx2 air blue dead, idx3 red alive, idx4 red dead
    e = Entities.allocate(5)
    e.side[:] = [BLUE, BLUE, BLUE, RED, RED]
    e.domain[:] = [GROUND, GROUND, AIR, GROUND, GROUND]
    e.x[:] = 0.0                          # all far from the goal (positions irrelevant to the cost KPI)
    e.alive[1] = False
    e.alive[2] = False
    e.alive[4] = False
    return e


def test_cost_exchange_weights_domains():
    """A shot-down recon drone is cheap, a lost assault vehicle is not: cost_exchange weights blue
    losses by domain via the stipulated unit-cost params."""
    scn = _scn().with_params({"cost_uas": 1.0, "cost_ugv": 20.0, "cost_red": 15.0})
    e = _mixed_entities()
    d = metrics.compute(scn, {BLUE: 3, RED: 2}, e, t_reached=None, t_elapsed=300.0, air0=1)
    assert d["blue_air_losses"] == 1.0             # the one UAS was shot down
    assert d["blue_ground_losses"] == 1.0          # one ground vehicle lost
    assert d["blue_cost_lost"] == 1.0 * 1.0 + 1.0 * 20.0        # 21 cost units
    # red value destroyed (1 x 15) over blue cost expended (21)
    assert d["cost_exchange"] == 15.0 / 21.0
