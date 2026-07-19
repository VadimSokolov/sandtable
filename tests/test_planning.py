"""Target assignment: blue leads to the objective along a route_bias lane; red holds."""
from __future__ import annotations

import numpy as np

from sandtable.entities import BLUE, RED, Entities
from sandtable.scenario import Objective, PlatformType, Scenario
from sandtable import planning
from sandtable.world import build_world


def _scn():
    return Scenario(
        name="p",
        size=(6000.0, 3000.0),
        platform_types={"u": PlatformType("u")},
        forces=[],
        objective=Objective(goal=(5750.0, 1500.0), goal_radius=150.0),
        terrain={"cell": 25.0},
    )


def _entities():
    # index 0: blue far from goal; 1: red defender; 2: blue already at the goal
    e = Entities.allocate(3)
    e.side[:] = [BLUE, RED, BLUE]
    e.x[:] = [250.0, 3000.0, 5750.0]
    e.y[:] = [1500.0, 1500.0, 1500.0]
    return e


def test_blue_target_leads_toward_objective(rng):
    scn = _scn()
    world = build_world(scn, rng)
    e = _entities()
    gx = scn.objective.goal[0]

    planning.step(e, world, scn, spawn_x=250.0)
    # A blue vehicle short of the goal is handed a carrot strictly ahead of it, bounded by the goal.
    assert e.x[0] < e.tgt_x[0] <= gx


def test_red_defenders_hold_position(rng):
    scn = _scn()
    world = build_world(scn, rng)
    e = _entities()
    planning.step(e, world, scn, spawn_x=250.0)
    assert e.tgt_x[1] == e.x[1] and e.tgt_y[1] == e.y[1]


def test_at_goal_blue_holds_position(rng):
    scn = _scn()
    world = build_world(scn, rng)
    e = _entities()
    planning.step(e, world, scn, spawn_x=250.0)
    # entity 2 sits on the goal, so it must be told to stay put (arrivals accumulate).
    assert e.tgt_x[2] == e.x[2] and e.tgt_y[2] == e.y[2]


def test_route_bias_shifts_target_lane(rng):
    scn = _scn()
    world = build_world(scn, rng)

    e0 = _entities()
    planning.step(e0, world, scn.with_params({"route_bias": 0.0}), spawn_x=250.0)
    ty_open = e0.tgt_y[0]

    e1 = _entities()
    planning.step(e1, world, scn.with_params({"route_bias": 1.0}), spawn_x=250.0)
    ty_cover = e1.tgt_y[0]

    # bias 0 aims at the open corridor lane, bias 1 at the covered lane: clearly different y.
    assert ty_open != ty_cover
    assert np.isclose(ty_open, world.corridor_y)
    assert np.isclose(ty_cover, world.covered_y)
    assert abs(ty_open - ty_cover) > world.cell
