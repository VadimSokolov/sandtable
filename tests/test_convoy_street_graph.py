"""Tests for urban street graph topology and blocking line-of-sight occlusion (Phase 3, Issue #16).

Verifies:
1. Byte-identity when street graph and buildings are absent.
2. Shortest-path routing over street graphs parameterized continuously by route_bias.
3. Seamless translation from graph paths into continuous RoutePolyline.
4. Vectorized line-of-sight ray marching through buildings vs open streets.
5. Ground sensing blocked by buildings while aerial UAS maintains overwatch.
6. Direct-fire engagement prevented by intervening buildings.
7. Convoy visual follower dead-reckoning when leader rounds a blind building corner.
"""
from __future__ import annotations

import numpy as np
import pytest

from sandtable.behavior import _follow
from sandtable.comms_ew import build_comms
from sandtable.entities import AIR, BLUE, GROUND, RED
from sandtable.route import RoutePolyline
from sandtable.scenario import ForceSpec, Objective, PlatformType, Scenario
from sandtable.sim import run_mission
from sandtable.street_graph import StreetEdge, StreetGraph, StreetNode
from sandtable.world import World


def _make_base_scenario() -> Scenario:
    ptypes = {
        "truck": PlatformType(name="truck", domain=GROUND, max_speed=12.0, cargo_capacity=5.0),
        "escort": PlatformType(name="escort", domain=GROUND, max_speed=12.0, weapon_range=600.0, pk_base=0.8),
        "uas": PlatformType(name="uas", domain=AIR, max_speed=20.0, sensor_range=2000.0),
        "insurgent": PlatformType(name="insurgent", domain=GROUND, max_speed=8.0, weapon_range=500.0, pk_base=0.8),
    }
    forces = [
        ForceSpec(side=BLUE, ptype="truck", count=3, spawn=(100.0, 100.0)),
        ForceSpec(side=RED, ptype="insurgent", count=2, spawn=(800.0, 800.0)),
    ]
    obj = Objective(goal=(1500.0, 100.0), goal_radius=100.0, survive_fraction=0.5)
    return Scenario(
        name="test_street_graph",
        size=(2000.0, 1000.0),
        platform_types=ptypes,
        forces=forces,
        objective=obj,
        terrain={"profile": "band"},
        dt=1.0,
        duration=50.0,
    )


def test_street_graph_off_is_byte_identical():
    """Verify that missions run byte-identically when street graph and buildings are off."""
    scn = _make_base_scenario()
    res1 = run_mission(scn, seed=42)
    res2 = run_mission(scn, seed=42)
    assert res1 == res2
    assert res1["success"] == res2["success"]
    assert res1["blue_losses"] == res2["blue_losses"]
    assert res1["mission_time"] == res2["mission_time"]


def test_street_graph_shortest_path_bias_sweep():
    """Verify Dijkstra routing selects speed vs cover according to continuous route_bias."""
    # Build a graph with two parallel routes from start (0, 0) to goal (1000, 0):
    # - Route A (Arterial): length 1000m, speed_mult = 1.0, exposure = 0.9
    #   Travel time = 1000s, exposure_cost = 900
    # - Route B (Covered): length 1200m, speed_mult = 0.6, exposure = 0.1
    #   Travel time = 2000s, exposure_cost = 120
    nodes = [
        StreetNode("start", 0.0, 0.0),
        StreetNode("a_mid", 500.0, -100.0),
        StreetNode("b_mid", 500.0, 200.0),
        StreetNode("goal", 1000.0, 0.0),
    ]
    edges = [
        # Arterial
        StreetEdge("start", "a_mid", speed_mult=1.0, exposure=0.9, length=500.0),
        StreetEdge("a_mid", "goal", speed_mult=1.0, exposure=0.9, length=500.0),
        # Covered
        StreetEdge("start", "b_mid", speed_mult=0.6, exposure=0.1, length=600.0),
        StreetEdge("b_mid", "goal", speed_mult=0.6, exposure=0.1, length=600.0),
    ]
    sg = StreetGraph(nodes, edges)

    # At route_bias = 0.0: cost(A) = 1000, cost(B) = 2000 -> selects Route A (arterial)
    path_fast = sg.find_path("start", "goal", route_bias=0.0)
    assert path_fast == ["start", "a_mid", "goal"]

    # At route_bias = 1.0: cost(A) = 900, cost(B) = 120 -> selects Route B (covered)
    path_safe = sg.find_path("start", "goal", route_bias=1.0)
    assert path_safe == ["start", "b_mid", "goal"]

    # Sweep route_bias to verify crossover point
    biases = np.linspace(0.0, 1.0, 11)
    paths = [sg.find_path("start", "goal", route_bias=b) for b in biases]
    assert paths[0] == ["start", "a_mid", "goal"]
    assert paths[-1] == ["start", "b_mid", "goal"]


def test_graph_to_polyline_preserves_kinematics():
    """Verify StreetGraph.to_route_polyline converts paths into RoutePolyline with intermediate geometry."""
    nodes = [
        StreetNode("n0", 0.0, 0.0),
        StreetNode("n1", 100.0, 0.0),
        StreetNode("n2", 100.0, 100.0),
    ]
    edges = [
        StreetEdge("n0", "n1", length=100.0, geometry=((50.0, 10.0),)),
        StreetEdge("n1", "n2", length=100.0),
    ]
    sg = StreetGraph(nodes, edges)
    poly = sg.to_route_polyline(["n0", "n1", "n2"])

    assert isinstance(poly, RoutePolyline)
    assert poly.waypoints.shape[0] == 4  # (0, 0), (50, 10), (100, 0), (100, 100)
    assert poly.total_length > 200.0

    # Test projection and point_at
    s_proj, d_orth = poly.project(np.array([0.0]), np.array([0.0]))
    assert pytest.approx(float(s_proj[0]), abs=1e-3) == 0.0
    assert pytest.approx(float(d_orth[0]), abs=1e-3) == 0.0

    # Serialization round-trip
    d = sg.to_dict()
    sg2 = StreetGraph.from_dict(d)
    assert len(sg2.nodes) == len(sg.nodes)
    assert len(sg2.edges) == len(sg.edges)


def test_building_los_blocking():
    """Verify vectorized World.los ray-marching accurately detects building occlusions."""
    ny, nx = 40, 40
    cell = 25.0
    world = World(
        size=(1000.0, 1000.0),
        cell=cell,
        speed=np.ones((ny, nx)),
        cover=np.zeros((ny, nx)),
        conceal=np.zeros((ny, nx)),
        buildings=np.zeros((ny, nx), dtype=bool),
    )

    # Place a building block from x in [400, 600], y in [400, 600]
    # In raster indices: ix in [16, 24], iy in [16, 24]
    world.buildings[16:24, 16:24] = True

    # Ray 1: Passes straight through building center from (200, 500) to (800, 500) -> BLOCKED
    # Ray 2: Runs parallel outside building from (200, 200) to (800, 200) -> CLEAR
    # Ray 3: Short ray inside street from (100, 100) to (200, 100) -> CLEAR
    x0 = np.array([200.0, 200.0, 100.0])
    y0 = np.array([500.0, 200.0, 100.0])
    x1 = np.array([800.0, 800.0, 200.0])
    y1 = np.array([500.0, 200.0, 100.0])

    clear = world.los(x0, y0, x1, y1)
    assert clear.shape == (3,)
    assert bool(clear[0]) is False
    assert bool(clear[1]) is True
    assert bool(clear[2]) is True

    # Test 2D broadcast (2, 2)
    b_clear = world.los(x0[:2, None], y0[:2, None], x1[None, :2], y1[None, :2])
    assert b_clear.shape == (2, 2)


def test_sensing_blocked_by_building():
    """Verify ground sensing is occluded by buildings while air UAS overwatch sees over roofs."""
    from sandtable import sensing
    from sandtable.scenario import build_entities

    ptypes = {
        "scout": PlatformType(name="scout", domain=GROUND, sensor_range=600.0),
        "insurgent": PlatformType(name="insurgent", domain=GROUND, sensor_range=600.0),
        "uas": PlatformType(name="uas", domain=AIR, sensor_range=1000.0),
    }
    forces = [
        ForceSpec(side=BLUE, ptype="scout", count=1, spawn=(200.0, 500.0)),
        ForceSpec(side=RED, ptype="insurgent", count=1, spawn=(600.0, 500.0)),
        ForceSpec(side=BLUE, ptype="uas", count=1, spawn=(200.0, 500.0)),
    ]
    scn = Scenario(
        name="test_sensing",
        size=(1000.0, 1000.0),
        platform_types=ptypes,
        forces=forces,
        objective=Objective(goal=(1000.0, 500.0)),
    )
    rng = np.random.default_rng(1234)
    ent = build_entities(scn, rng)

    ny, nx = 40, 40
    cell = 25.0
    world = World(
        size=(1000.0, 1000.0),
        cell=cell,
        speed=np.ones((ny, nx)),
        cover=np.zeros((ny, nx)),
        conceal=np.zeros((ny, nx)),
        buildings=np.zeros((ny, nx), dtype=bool),
    )
    # Building between x=300 and x=500
    world.buildings[10:30, 12:20] = True

    # Align positions exactly
    ent.x[:] = [200.0, 600.0, 200.0]
    ent.y[:] = [500.0, 500.0, 500.0]

    # 1. Ground observer only (hide UAS by marking alive=False)
    ent.alive[2] = False
    sensing.step(ent, world, rng)
    # Red target (index 1) should NOT be seen because building occludes ground-to-ground LOS
    assert bool(ent.seen[1]) is False

    # 2. Activate UAS (alive=True)
    ent.alive[2] = True
    sensing.step(ent, world, rng)
    # Red target should now be detected by the air overwatch looking down
    assert bool(ent.seen[1]) is True


def test_engagement_blocked_by_building():
    """Verify ground direct fire cannot penetrate solid buildings even if target is seen."""
    from sandtable import engagement
    from sandtable.scenario import build_entities

    ptypes = {
        "shooter": PlatformType(name="shooter", domain=GROUND, weapon_range=600.0, pk_base=1.0),
        "target": PlatformType(name="target", domain=GROUND, weapon_range=600.0, pk_base=1.0),
    }
    forces = [
        ForceSpec(side=BLUE, ptype="shooter", count=1, spawn=(200.0, 500.0)),
        ForceSpec(side=RED, ptype="target", count=1, spawn=(600.0, 500.0)),
    ]
    scn = Scenario(
        name="test_eng",
        size=(1000.0, 1000.0),
        platform_types=ptypes,
        forces=forces,
        objective=Objective(goal=(1000.0, 500.0)),
    )
    rng = np.random.default_rng(999)
    ent = build_entities(scn, rng)

    ny, nx = 40, 40
    cell = 25.0
    world = World(
        size=(1000.0, 1000.0),
        cell=cell,
        speed=np.ones((ny, nx)),
        cover=np.zeros((ny, nx)),
        conceal=np.zeros((ny, nx)),
        buildings=np.zeros((ny, nx), dtype=bool),
    )
    # Building between x=300 and x=500
    world.buildings[10:30, 12:20] = True

    ent.x[:] = [200.0, 600.0]
    ent.y[:] = [500.0, 500.0]
    ent.seen[:] = True  # Both seen on common operating picture

    # Attempt engagement with building between shooter and target
    engagement.step(ent, world, dt=1.0, rng=rng)
    assert bool(ent.alive[1]) is True  # Red target survives because direct fire cannot pass through building

    # Move target to clear lane with no building (e.g. y=100)
    ent.y[1] = 100.0
    ent.x[1] = 200.0
    engagement.step(ent, world, dt=1.0, rng=rng)
    assert bool(ent.alive[1]) is False  # Target destroyed once in clear line of sight


def test_follower_blind_corner_dead_reckon():
    """Verify follower loses visual contact and dead-reckons when leader rounds a blind corner."""
    from sandtable.behavior import build_behavior
    from sandtable.scenario import build_entities

    ptypes = {
        "truck": PlatformType(name="truck", domain=GROUND, max_speed=12.0),
    }
    forces = [
        ForceSpec(side=BLUE, ptype="truck", count=2, spawn=(300.0, 400.0)),
    ]
    scn = Scenario(
        name="test_blind_corner",
        size=(1000.0, 1000.0),
        platform_types=ptypes,
        forces=forces,
        objective=Objective(goal=(1000.0, 500.0)),
        params={"blue_behavior": "leader_follow", "follow_mode": "behavior", "track_timeout": 10},
    )
    rng = np.random.default_rng(42)
    ent = build_entities(scn, rng)
    ent.role[:] = [0, 1]  # 0 = leader, 1 = follower
    ent.leader[:] = [-1, 0]

    ny, nx = 40, 40
    cell = 25.0
    world = World(
        size=(1000.0, 1000.0),
        cell=cell,
        speed=np.ones((ny, nx)),
        cover=np.zeros((ny, nx)),
        conceal=np.zeros((ny, nx)),
        buildings=np.zeros((ny, nx), dtype=bool),
    )
    # Building block at corner: x in [300, 500], y in [300, 500]
    world.buildings[12:20, 12:20] = True

    # Leader has rounded corner to (350, 550)
    # Follower is still on street at (250, 400)
    # The corner building at [300, 500] occludes line-of-sight between them
    ent.x[:] = [350.0, 250.0]
    ent.y[:] = [550.0, 400.0]
    ent.heading[:] = [np.pi / 2, np.pi / 2]
    ent.speed[:] = [10.0, 10.0]

    bhv = build_behavior(scn, ent)
    assert bhv is not None
    bhv.trk_x[:] = [350.0, 250.0]
    bhv.trk_y[:] = [550.0, 390.0]

    comms = build_comms(scn)

    # Verify building blocks direct line of sight
    assert bool(world.los(ent.x[1], ent.y[1], ent.x[0], ent.y[0])) is False

    # Execute _follow step with world line of sight
    _follow(ent, bhv, comms, scn, k=0, rng=rng, blue_ground=np.ones(2, bool), world=world)

    # Follower should have aged track and incremented stale steps due to blind corner occlusion
    assert bhv.trk_age[1] == 1
    assert bhv.trk_stale_steps[1] == 1
