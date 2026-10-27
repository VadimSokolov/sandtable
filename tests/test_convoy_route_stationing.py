"""Tests for convoy route stationing and arc-length tracking (Phase 3, Issue #13).

Doctrinal references:
- ATP 4-16 (Movement Control, App. C): Convoy spacing, column length, and road space
  are measured strictly along the road centerline (arc-length stationing coordinate s).
- ATP 4-11 (Convoy Operations, App. G & M): Formation spacing around turns and doglegs.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import behavior, motion, planning, sim
from sandtable.behavior import Behavior, LEADER_FOLLOW, WAYPOINT
from sandtable.entities import BLUE, GROUND, Entities
from sandtable.route import RoutePolyline
from sandtable.scenario import ForceSpec, Objective, PlatformType, Scenario, build_entities, load_scenario
from sandtable.world import build_world


def _make_bhv(ent: Entities, topology: str = "chain") -> Behavior:
    """Helper to build a properly initialized Behavior object for testing."""
    n = ent.n
    trk_x = ent.x.copy()
    trk_y = ent.y.copy()
    for i in range(n):
        if ent.role[i] == 1:
            ref = max(0, i - 1) if topology == "chain" else max(0, int(ent.leader[i]))
            trk_x[i] = ent.x[ref]
            trk_y[i] = ent.y[ref]

    return Behavior(
        mode=LEADER_FOLLOW,
        follow_mode="behavior",
        teleop_stop=True,
        track_timeout=40,
        state=np.where(ent.role == 0, WAYPOINT, LEADER_FOLLOW),
        holding=np.zeros(n, bool),
        was_holding=np.zeros(n, bool),
        interventions=np.zeros(n, np.int32),
        hold_steps=np.zeros(n, np.int32),
        alive_steps=np.zeros(n, np.int32),
        trk_x=trk_x,
        trk_y=trk_y,
        trk_vx=np.zeros(n),
        trk_vy=np.zeros(n),
        trk_age=np.zeros(n, np.int32),
        topology=topology,
        sense_range=1000.0,
        outage=0,
        trk_err_sum=np.zeros(n),
        trk_steps=np.zeros(n, np.int32),
        trk_stale_steps=np.zeros(n, np.int32),
        trk_lost_steps=np.zeros(n, np.int32),
        st_err_sum=np.zeros(n),
        st_along_sum=np.zeros(n),
        st_cross_sum=np.zeros(n),
        st_steps=np.zeros(n, np.int32),
        prev_heading=ent.heading.copy(),
        turn_sum=np.zeros(n),
        turn_steps=np.zeros(n, np.int32),
    )


# ---- 1. Byte-Identity when Route is OFF ---------------------------------------

def test_route_off_is_byte_identical():
    """Absence of a route leaves simulation runs and entities 100% byte-identical."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    for seed in range(3):
        run_a = sim.run_mission(scn, seed=seed)
        run_b = sim.run_mission(scn.with_params({"route": None}), seed=seed)
        assert same_run(run_a, run_b)

    rng = np.random.default_rng(0)
    world = build_world(scn, rng)
    assert world.route is None
    ent = build_entities(scn, rng)
    assert np.isnan(ent.progress).all()


# ---- 2. RoutePolyline Geometry & Mathematical Invariants --------------------

def test_route_polyline_geometry_and_projection():
    """Verify cumulative distance, point_at, and orthogonal projection on an L-dogleg."""
    # L-dogleg: (0, 0) -> (1000, 0) -> (1000, 1000)
    pts = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0)]
    r = RoutePolyline.from_waypoints(pts)

    assert r.total_length == pytest.approx(2000.0)
    assert np.allclose(r.cum_dist, [0.0, 1000.0, 2000.0])

    # Midpoint of first segment
    x, y, th = r.point_at(500.0)
    assert (x, y) == pytest.approx((500.0, 0.0))
    assert th == pytest.approx(0.0)

    # Midpoint of second segment (heading North = pi/2)
    x, y, th = r.point_at(1500.0)
    assert (x, y) == pytest.approx((1000.0, 500.0))
    assert th == pytest.approx(np.pi / 2)

    # Invertibility: project(point_at(s)) == s for any s in [0, L]
    for s_test in [0.0, 250.0, 999.0, 1000.0, 1001.0, 1750.0, 2000.0]:
        px, py, _ = r.point_at(s_test)
        s_proj, d_perp = r.project(px, py)
        assert s_proj == pytest.approx(s_test, abs=1e-6)
        assert d_perp == pytest.approx(0.0, abs=1e-6)

    # Off-route point orthogonal projection
    # Point at (500, 25): 25m lateral offset from first segment
    s_proj, d_perp = r.project(500.0, 25.0)
    assert s_proj == pytest.approx(500.0)
    assert d_perp == pytest.approx(25.0)

    # Point at (1050, 600): 50m lateral offset from second segment
    s_proj, d_perp = r.project(1050.0, 600.0)
    assert s_proj == pytest.approx(1600.0)
    assert d_perp == pytest.approx(50.0)


# ---- 3. Straight Route Matches Euclidean Stationing -------------------------

def test_straight_route_matches_euclidean_stationing():
    """On a straight East-West route, arc-length stationing produces positions matching
    the Euclidean heading offset within numerical precision."""
    ptypes = {
        "truck": PlatformType(
            name="truck",
            max_speed=15.0,
            turn_rate=1.0,
            hp=1.0,
            domain=GROUND,
        ),
    }
    spawn = (200.0, 500.0)
    goal = (2200.0, 500.0)
    straight_route = [spawn, goal]

    # Baseline scenario (Euclidean heading offset, no route)
    scn_base = Scenario(
        name="straight_baseline",
        size=(3000.0, 1000.0),
        platform_types=ptypes,
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=6,
                spawn=spawn,
                spawn_spread=0.0,
                spacing=50.0,
            ),
        ],
        objective=Objective(goal=goal, goal_radius=100.0),
        params={
            "convoy": {
                "march_unit_size": 3,
                "march_units_per_serial": 2,
                "serials_per_column": 1,
                "pace": 10.0,
                "time_gap": 3.0,
            },
            "formation_spread": 50.0,
            "lookahead": 50.0,
        },
        duration=30.0,
        dt=1.0,
    )

    # Route scenario (same geometry with explicit RoutePolyline)
    scn_route = scn_base.with_params({"route": straight_route})

    world_base = build_world(scn_base, np.random.default_rng(42))
    world_route = build_world(scn_route, np.random.default_rng(42))

    ent_base = build_entities(scn_base, np.random.default_rng(42))
    ent_route = build_entities(scn_route, np.random.default_rng(42))

    bhv_base = _make_bhv(ent_base, topology="chain")
    bhv_route = _make_bhv(ent_route, topology="chain")

    # Step planning
    planning.step(ent_base, world_base, scn_base, spawn[0], bhv=bhv_base)
    planning.step(ent_route, world_route, scn_route, spawn[0], bhv=bhv_route)

    # Targets should match within numerical precision on a straight line
    assert np.allclose(ent_base.tgt_x, ent_route.tgt_x, atol=1e-4)
    assert np.allclose(ent_base.tgt_y, ent_route.tgt_y, atol=1e-4)


# ---- 4. Dogleg 90-Degree Turn: Corner-Cutting Prevention & Gap Holding --------

def test_dogleg_holds_intervehicle_gap_around_corner():
    """Verify that on a 90-degree bend (dogleg):
    1. Follower does NOT cut the corner across open terrain (cross-track distance bounded).
    2. Arc-length gap along the road is preserved when leader and follower straddle the corner.
    """
    ptypes = {
        "truck": PlatformType(
            name="truck",
            max_speed=12.0,
            turn_rate=1.5,
            hp=1.0,
            domain=GROUND,
        ),
    }

    # Dogleg route: (200, 500) -> East to (1000, 500) -> North to (1000, 1500)
    turn_pt = (1000.0, 500.0)
    goal = (1000.0, 1500.0)
    dogleg_route = [(200.0, 500.0), turn_pt, goal]
    route_poly = RoutePolyline.from_waypoints(dogleg_route)

    gap_m = 50.0
    scn = Scenario(
        name="dogleg_convoy",
        size=(2000.0, 2000.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=6,
                spawn=(200.0, 500.0),
                spawn_spread=0.0,
                route=dogleg_route,
                spacing=gap_m,
            ),
        ],
        objective=Objective(goal=goal, goal_radius=80.0),
        params={
            "convoy": {
                "march_unit_size": 3,
                "march_units_per_serial": 2,
                "serials_per_column": 1,
                "pace": 10.0,
                "time_gap": 2.0,
            },
            "formation_spread": gap_m,
            "route": dogleg_route,
        },
        duration=180.0,
        dt=1.0,
    )

    rng = np.random.default_rng(123)
    world = build_world(scn, rng)
    ent = build_entities(scn, rng)
    bhv = _make_bhv(ent, topology="chain")

    max_cross_track = 0.0
    straddle_observed = False
    straddle_gap_error = 0.0

    # Advance simulation through the turn
    dt = 1.0
    for step_idx in range(150):
        # Update tracked poses: followers track their predecessor
        for i in range(ent.n):
            if ent.role[i] == 1:
                ref = behavior._predecessor(ent, bhv, i)
                bhv.trk_x[i] = ent.x[ref]
                bhv.trk_y[i] = ent.y[ref]
                bhv.trk_vx[i] = ent.speed[ref] * np.cos(ent.heading[ref])
                bhv.trk_vy[i] = ent.speed[ref] * np.sin(ent.heading[ref])

        planning.step(ent, world, scn, 200.0, bhv=bhv)
        motion.step(ent, world, dt, tempo=1.0)

        # Measure orthogonal distance to route polyline for all vehicles
        s_vals, d_perp_vals = route_poly.project(ent.x, ent.y)
        max_cross_track = max(max_cross_track, float(d_perp_vals.max()))

        # Check when leader (0) has rounded the corner (past 800m) while follower (1) is still before corner
        s_lead = s_vals[0]
        s_fol = s_vals[1]
        turn_s = 800.0  # distance from spawn (200, 500) to corner (1000, 500) is 800m

        if s_lead > turn_s + 20.0 and s_fol < turn_s - 10.0:
            straddle_observed = True
            delta_s = s_lead - s_fol
            straddle_gap_error = abs(delta_s - gap_m)

    # 1. Verification of corner-cutting prevention:
    # Vehicles must stay tightly bounded to the roadway throughout the turn.
    # (Under Euclidean offset, followers cut the corner by 40-50m across open ground).
    assert max_cross_track < 10.0, f"Vehicle deviated {max_cross_track}m from route polyline (corner-cutting detected)"

    # 2. Verification of arc-length gap holding around the corner:
    assert straddle_observed, "Leader and follower should straddle the 90-degree corner during the run"
    assert straddle_gap_error < 25.0, f"Arc-length gap error around corner was {straddle_gap_error}m (expected < 25m)"


# ---- 5. Along-Track vs Cross-Track Error Separation --------------------------

def test_along_and_cross_track_station_error_separation():
    """Verify that longitudinal lag accumulates into along-track error, while lateral
    displacement accumulates into cross-track error."""
    pts = [(0.0, 500.0), (1000.0, 500.0), (1000.0, 1500.0)]
    ptypes = {"truck": PlatformType(name="truck", max_speed=15.0, hp=1.0, domain=GROUND)}
    scn = Scenario(
        name="error_separation",
        size=(2000.0, 2000.0),
        platform_types=ptypes,
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=6,
                spawn=(0.0, 500.0),
                spawn_spread=0.0,
                route=pts,
                spacing=50.0,
            ),
        ],
        objective=Objective(goal=(1000.0, 1500.0)),
        params={
            "convoy": {"march_unit_size": 3, "march_units_per_serial": 2, "serials_per_column": 1},
            "formation_spread": 50.0,
            "route": pts,
        },
        duration=10.0,
        dt=1.0,
    )

    world = build_world(scn, np.random.default_rng(0))
    ent = build_entities(scn, np.random.default_rng(0))
    bhv = _make_bhv(ent, topology="chain")

    # Leader at (200, 500) (progress = 200m). Commanded follower station = 200 - 50 = 150m at (150, 500).
    ent.x[0], ent.y[0] = 200.0, 500.0
    bhv.trk_x[1], bhv.trk_y[1] = 200.0, 500.0

    # Follower placed at (100, 500): exactly on the road, but 50m late (longitudinal error = 50m, cross = 0m)
    ent.x[1], ent.y[1] = 100.0, 500.0

    planning.step(ent, world, scn, 0.0, bhv=bhv)
    assert bhv.st_along_sum[1] == pytest.approx(50.0, abs=1.0)
    assert bhv.st_cross_sum[1] == pytest.approx(0.0, abs=1.0)

    # Follower placed at (150, 530): at the correct arc length (150m), but 30m laterally off-road
    bhv.st_along_sum[1] = 0.0
    bhv.st_cross_sum[1] = 0.0
    ent.x[1], ent.y[1] = 150.0, 530.0

    planning.step(ent, world, scn, 0.0, bhv=bhv)
    assert bhv.st_along_sum[1] == pytest.approx(0.0, abs=1.0)
    assert bhv.st_cross_sum[1] == pytest.approx(30.0, abs=1.0)
