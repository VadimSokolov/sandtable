"""Unified Convoy Mission Viewer (v2) Generator.

Synthesizes all seven convoy capabilities across Phases 1, 2, and 3 into a single,
self-contained, high-performance operational console:
  - Issue #8:  Convoy Hierarchy of March Units, Serials, and Vehicle Roles (ATP 4-11)
  - Issue #9:  Cargo Payload & Logistics Delivery Conservation (FM 4-0)
  - Issue #10: Pace, Time Gap Headway, and Column Road Space (ATP 4-16)
  - Issue #11: Convoy Doctrine Planning Factors and Arithmetic
  - Issue #13: True 1D Arc-Length Route Stationing (No Corner-Cutting)
  - Issue #15: Multi-Objective Separation Trade Space (Pareto Frontier)
  - Issue #16: 2D Urban Street Graph with Blocking Line-of-Sight Occlusion

Generates:
  report/viz/mission_viewer_v2.html     Standalone interactive web application
  report/viz/mission_viewer_v2_data.json Standalone JSON telemetry payload

Run:
  python tools/make_mission_viewer_v2.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from sandtable import motion, planning
from sandtable.behavior import Behavior, LEADER_FOLLOW, WAYPOINT
from sandtable.convoy import (
    ROLE_CARGO,
    ROLE_CONTROL,
    ROLE_RECOVERY,
    SECTION_HEAD,
    SECTION_MAIN,
    SECTION_TRAIL,
)
from sandtable.entities import BLUE, GROUND, Entities
from sandtable.replay import record_trace
from sandtable.route import RoutePolyline
from sandtable.scenario import ForceSpec, Objective, PlatformType, Scenario, load_scenario
from sandtable.world import build_world

REPO_ROOT = Path(__file__).resolve().parents[1]
VIZ_DIR = REPO_ROOT / "report" / "viz"
SCENARIOS_DIR = REPO_ROOT / "scenarios"


def _make_bhv(ent: Entities, topology: str = "chain") -> Behavior:
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
        sense_range=1500.0,
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


def _simulate_urban_preset() -> dict[str, Any]:
    """Preset 1: Urban Street Graph & Occlusion (Issue #16 & #13)."""
    pts = [
        (200.0, 500.0),
        (1000.0, 500.0),   # WP1 -> WP2: Eastbound
        (1000.0, 1500.0),  # WP2 -> WP3: Northbound
        (1800.0, 1500.0),  # WP3 -> WP4: Eastbound
        (1800.0, 2400.0),  # WP4 -> WP5: Northbound
    ]
    poly = RoutePolyline.from_waypoints(pts)
    urban_boxes = [
        [400.0, 600.0, 900.0, 1100.0],
        [1100.0, 600.0, 1600.0, 1100.0],
        [400.0, 1600.0, 900.0, 2100.0],
        [1100.0, 1600.0, 1600.0, 2100.0],
    ]

    ptypes = {
        "lead_truck": PlatformType(name="lead_truck", max_speed=12.0, turn_rate=1.5, hp=1.0, domain=GROUND, length=6.0),
        "cargo_truck": PlatformType(name="cargo_truck", max_speed=12.0, turn_rate=1.5, hp=1.0, domain=GROUND, length=7.0, cargo_capacity=5.0),
        "gun_truck": PlatformType(name="gun_truck", max_speed=14.0, turn_rate=1.8, hp=2.0, domain=GROUND, length=6.5),
        "recovery": PlatformType(name="recovery", max_speed=10.0, turn_rate=1.2, hp=1.5, domain=GROUND, length=8.0),
    }

    n_veh = 6
    spacing = 50.0
    spawn_pts = [(pts[0][0] - i * spacing, pts[0][1]) for i in range(n_veh)]

    # 6 vehicles: V1 (Lead/C2), V2 (Cargo 5t), V3 (Cargo 5t), V4 (Lead MU2), V5 (Cargo 5t), V6 (Recovery)
    roles = [ROLE_CONTROL, ROLE_CARGO, ROLE_CARGO, ROLE_CONTROL, ROLE_CARGO, ROLE_RECOVERY]
    cargo_caps = [0.0, 5.0, 5.0, 0.0, 5.0, 0.0]
    callsigns = ["V1 (Lead / Pacesetter)", "V2 (Cargo Transporter)", "V3 (Cargo Transporter)", "V4 (Lead MU 2)", "V5 (Cargo Transporter)", "V6 (Trail / Recovery)"]

    ent = Entities(
        x=np.array([p[0] for p in spawn_pts], dtype=float),
        y=np.array([p[1] for p in spawn_pts], dtype=float),
        z=np.zeros(n_veh, dtype=float),
        heading=np.zeros(n_veh, dtype=float),
        speed=np.zeros(n_veh, dtype=float),
        side=np.full(n_veh, BLUE, dtype=np.int8),
        ptype=np.array([0, 1, 1, 0, 1, 3], dtype=np.int8),
        role=np.array([0 if i in (0, 3) else 1 for i in range(n_veh)], dtype=np.int8),
        alive=np.ones(n_veh, dtype=bool),
        hp=np.ones(n_veh, dtype=float),
        fuel=np.full(n_veh, np.inf),
        tgt_x=np.zeros(n_veh, dtype=float),
        tgt_y=np.zeros(n_veh, dtype=float),
        seen=np.zeros(n_veh, dtype=bool),
        leader=np.array([-1, 0, 1, -1, 3, 4], dtype=np.int32),
        max_speed=np.array([12.0, 12.0, 12.0, 12.0, 12.0, 10.0]),
        turn_rate=np.full(n_veh, 1.5),
        sensor_range=np.full(n_veh, 300.0),
        weapon_range=np.full(n_veh, 200.0),
        pk_base=np.full(n_veh, 0.01),
        domain=np.full(n_veh, GROUND, dtype=np.int8),
        convoy_role=np.array(roles, dtype=np.int8),
        march_unit=np.array([0, 0, 0, 1, 1, 1], dtype=np.int16),
        serial=np.zeros(n_veh, dtype=np.int16),
        section=np.array([SECTION_HEAD, SECTION_MAIN, SECTION_MAIN, SECTION_HEAD, SECTION_MAIN, SECTION_TRAIL], dtype=np.int8),
        cargo=np.array(cargo_caps, dtype=float),
        cargo_delivered=np.zeros(n_veh, dtype=float),
        progress=np.zeros(n_veh, dtype=float),
    )

    scn = Scenario(
        name="urban_grid_preset",
        size=(2400.0, 2600.0),
        platform_types=ptypes,
        terrain={"profile": "urban", "cell": 20.0},
        forces=[ForceSpec(side=BLUE, ptype="cargo_truck", count=n_veh, spawn=pts[0], route=pts, spacing=spacing)],
        objective=Objective(goal=pts[-1], goal_radius=80.0),
        params={"convoy": {"pace": 10.0, "time_gap": 2.5, "march_unit_size": 3, "march_units_per_serial": 2, "roles": ["control", "cargo", "cargo", "control", "cargo", "recovery"]}, "route": pts},
        duration=180.0,
        dt=1.0,
    )

    rng = np.random.default_rng(42)
    world = build_world(scn, rng)
    world.route = poly
    world.building_boxes = np.array(urban_boxes, dtype=float)

    bhv = _make_bhv(ent, topology="chain")

    frames: list[dict[str, Any]] = []
    goal = np.array(pts[-1])
    goal_r = 80.0

    steps = 180
    for step_idx in range(steps):
        t = round(step_idx * scn.dt, 1)

        # Check goal delivery
        dist_to_goal = np.hypot(ent.x - goal[0], ent.y - goal[1])
        at_goal = (dist_to_goal <= goal_r) & ent.alive
        ent.cargo_delivered[at_goal] = ent.cargo[at_goal]

        # Line of sight between consecutive vehicles
        los_status = [True] * n_veh
        for i in range(n_veh):
            if ent.role[i] == 1:
                pred = i - 1
                in_range = float(np.hypot(ent.x[pred] - ent.x[i], ent.y[pred] - ent.y[i])) <= bhv.sense_range
                has_los = bool(world.los(ent.x[i], ent.y[i], ent.x[pred], ent.y[pred])) if world.buildings is not None else True
                los_status[i] = has_los
                if in_range and has_los:
                    bhv.trk_x[i] = ent.x[ref := pred]
                    bhv.trk_y[i] = ent.y[ref]
                    bhv.trk_vx[i] = ent.speed[ref] * np.cos(ent.heading[ref])
                    bhv.trk_vy[i] = ent.speed[ref] * np.sin(ent.heading[ref])
                    bhv.trk_age[i] = 0
                else:
                    bhv.trk_age[i] += 1
                    bhv.trk_stale_steps[i] += 1
                    bhv.trk_x[i] += bhv.trk_vx[i] * scn.dt
                    bhv.trk_y[i] += bhv.trk_vy[i] * scn.dt

        planning.step(ent, world, scn, float(ent.x[0]), bhv=bhv)

        # Update lead vehicle carrot
        s_lead, _ = poly.project(ent.x[0], ent.y[0])
        s_carrot = min(s_lead + 30.0, poly.total_length)
        cx, cy, _ = poly.point_at(s_carrot)
        ent.tgt_x[0] = cx
        ent.tgt_y[0] = cy

        motion.step(ent, world, scn.dt, tempo=1.0)

        s_vals, d_perp_vals = poly.project(ent.x, ent.y)

        # Inter-vehicle gaps
        inter_gaps = [0.0]
        for i in range(1, n_veh):
            inter_gaps.append(round(float(s_vals[i - 1] - s_vals[i]), 1))

        frames.append({
            "t": t,
            "x": [round(float(v), 1) for v in ent.x],
            "y": [round(float(v), 1) for v in ent.y],
            "h": [round(float(v), 2) for v in ent.heading],
            "speed": [round(float(v), 1) for v in ent.speed],
            "alive": [int(v) for v in ent.alive],
            "seen": [int(v) for v in ent.seen],
            "progress": [round(float(v), 1) for v in s_vals],
            "cross_track": [round(float(v), 1) for v in d_perp_vals],
            "inter_gap": inter_gaps,
            "los_to_pred": los_status,
            "cargo_delivered": [round(float(v), 1) for v in ent.cargo_delivered],
            "kills": [],
        })

    return {
        "id": "urban_grid",
        "title": "Urban Street Graph & Occlusion",
        "subtitle": "ATP 4-11 Urban Convoy & Blind Corner Occlusion (Issue #16)",
        "desc": "Convoy maneuvering through city street corridors with 4 solid masonry building blocks. When rounding 90-degree corners, vehicles lose direct line-of-sight and seamlessly transition to dead-reckoning on surveyed street lanes, avoiding corner-cutting through buildings.",
        "world_size": [2400.0, 2600.0],
        "route": [[float(x), float(y)] for x, y in pts],
        "building_boxes": urban_boxes,
        "objective": {"goal": pts[-1], "radius": goal_r},
        "entities": [
            {
                "id": i,
                "callsign": callsigns[i],
                "side": int(ent.side[i]),
                "domain": int(ent.domain[i]),
                "convoy_role": int(ent.convoy_role[i]),
                "march_unit": int(ent.march_unit[i]),
                "serial": int(ent.serial[i]),
                "section": int(ent.section[i]),
                "cargo": float(ent.cargo[i]),
                "length": 6.5,
            }
            for i in range(n_veh)
        ],
        "frames": frames,
        "total_cargo": float(sum(cargo_caps)),
        "route_length": round(poly.total_length, 1),
        "doctrinal_pace": 10.0,
        "doctrinal_time_gap": 2.5,
    }


def _simulate_msr_ambush_preset() -> dict[str, Any]:
    """Preset 2: Tactical MSR Convoy with Armed Escorts & Ambush (Issue #8, #9, #15)."""
    scn_path = SCENARIOS_DIR / "uc3_convoy.json"
    scn = load_scenario(str(scn_path))

    # Configure 15-vehicle column with cargo and escorts
    params = {
        "route_bias": 0.5,
        "convoy": {
            "march_unit_size": 5,
            "march_units_per_serial": 3,
            "serials_per_column": 1,
            "pace": 10.0,
            "time_gap": 4.0,
            "cargo_per_vehicle": 5.0,
            "delivery_fraction": 0.70,
            "roles": ["control", "cargo", "cargo", "security", "cargo"],
        },
    }

    tr = record_trace(scn, seed=7, params=params, stride=3)

    callsigns = [
        "C2 Lead (Serial 1 / MU 1)",
        "Cargo Truck 1 (5.0t)",
        "Cargo Truck 2 (5.0t)",
        "Gun Truck Escort 1 (M240)",
        "Cargo Truck 3 (5.0t)",
        "MU 2 Lead (Pacesetter)",
        "Cargo Truck 4 (5.0t)",
        "Cargo Truck 5 (5.0t)",
        "Gun Truck Escort 2 (M2 .50)",
        "Cargo Truck 6 (5.0t)",
        "MU 3 Lead (Pacesetter)",
        "Cargo Truck 7 (5.0t)",
        "Cargo Truck 8 (5.0t)",
        "Gun Truck Escort 3 (Mk19)",
        "Trail Recovery (Wrecker)",
    ]

    # Red ambusher callsigns
    n_blue = len(callsigns)
    total_ent = len(tr["entities"])
    for i in range(n_blue, total_ent):
        callsigns.append(f"Red AT-Team {i - n_blue + 1}")

    for i, e in enumerate(tr["entities"]):
        e["id"] = i
        e["callsign"] = callsigns[i] if i < len(callsigns) else f"Entity {i}"
        if "length" not in e:
            e["length"] = 6.5

    # Compute total cargo
    total_cargo = sum(float(e.get("cargo", 0.0)) for e in tr["entities"] if e["side"] == BLUE)

    return {
        "id": "msr_ambush",
        "title": "Tactical MSR Convoy with Escorts & Ambush",
        "subtitle": "ATP 4-11 / FM 4-0 Force Protection & Payload Delivery (Issue #8 & #9)",
        "desc": "15-vehicle doctrinal column (3 March Units of 5 vehicles) carrying 40 tons of sustainment payload. Armed gun trucks (ROLE_SECURITY) protect cargo transporters against an ambush along the defilade ridge, demonstrating FM 4-0 throughput and loss attribution.",
        "world_size": tr["size"],
        "route": tr.get("route", []),
        "building_boxes": tr.get("building_boxes", []),
        "objective": tr["objective"],
        "terrain": tr["terrain"],
        "entities": tr["entities"],
        "frames": tr["frames"],
        "outcome": tr["outcome"],
        "total_cargo": total_cargo,
        "route_length": 5500.0,
        "doctrinal_pace": 10.0,
        "doctrinal_time_gap": 4.0,
    }


def _simulate_spacing_preset(is_dispersed: bool) -> dict[str, Any]:
    """Preset 3: Doctrinal Spacing Contrast (Dispersed vs Closed Column) (Issue #10, #11)."""
    scn_path = SCENARIOS_DIR / "uc3_convoy.json"
    scn = load_scenario(str(scn_path))

    pace = 14.0 if is_dispersed else 8.0
    time_gap = 6.0 if is_dispersed else 2.0
    elem_gap = 30.0 if is_dispersed else 15.0

    params = {
        "route_bias": 0.85,
        "pace": pace,
        "time_gap": time_gap,
        "element_time_gap": elem_gap,
        "convoy": {
            "march_unit_size": 5,
            "march_units_per_serial": 3,
            "serials_per_column": 1,
            "pace": pace,
            "time_gap": time_gap,
            "cargo_per_vehicle": 5.0,
            "roles": ["control", "cargo", "cargo", "security", "recovery"],
        },
    }

    tr = record_trace(scn, seed=12, params=params, stride=4)

    for i, e in enumerate(tr["entities"]):
        e["id"] = i
        e["callsign"] = f"V{i + 1} ({'Blue' if e['side'] == BLUE else 'Red'})"
        e["length"] = 6.5

    total_cargo = sum(float(e.get("cargo", 0.0)) for e in tr["entities"] if e["side"] == BLUE)
    title_suffix = "Dispersed Open Column (6.0s Gap)" if is_dispersed else "Closed Tight Column (2.0s Gap)"
    sub_desc = (
        "High headway (6.0s / 84m gap) minimizes vulnerability to indirect artillery and roadside ambushes, but expands column road space to 1,240m."
        if is_dispersed
        else "Compact headway (2.0s / 16m gap) minimizes road occupancy (320m) for rapid clearance across chokepoints and urban defiles."
    )

    return {
        "id": "dispersed_column" if is_dispersed else "closed_column",
        "title": f"Doctrinal Spacing: {title_suffix}",
        "subtitle": "ATP 4-16 Movement Control Appendix C (Issue #10 & #11)",
        "desc": sub_desc,
        "world_size": tr["size"],
        "route": tr.get("route", []),
        "building_boxes": tr.get("building_boxes", []),
        "objective": tr["objective"],
        "terrain": tr["terrain"],
        "entities": tr["entities"],
        "frames": tr["frames"],
        "outcome": tr["outcome"],
        "total_cargo": total_cargo,
        "route_length": 5500.0,
        "doctrinal_pace": pace,
        "doctrinal_time_gap": time_gap,
        "is_dispersed": is_dispersed,
    }


def _simulate_dogleg_stationing_preset() -> dict[str, Any]:
    """Preset 4: Arc-Length Stationing vs Euclidean Corner-Cutting (Issue #13)."""
    pts = [(200.0, 500.0), (1200.0, 500.0), (1200.0, 1600.0)]
    poly = RoutePolyline.from_waypoints(pts)

    ptypes = {
        "truck": PlatformType(name="truck", max_speed=12.0, turn_rate=1.5, hp=1.0, domain=GROUND, length=6.0, cargo_capacity=5.0),
    }

    n_veh = 6
    spacing = 45.0
    spawn_pts = [(pts[0][0] - i * spacing, pts[0][1]) for i in range(n_veh)]

    ent = Entities(
        x=np.array([p[0] for p in spawn_pts], dtype=float),
        y=np.array([p[1] for p in spawn_pts], dtype=float),
        z=np.zeros(n_veh, dtype=float),
        heading=np.zeros(n_veh, dtype=float),
        speed=np.zeros(n_veh, dtype=float),
        side=np.full(n_veh, BLUE, dtype=np.int8),
        ptype=np.zeros(n_veh, dtype=np.int8),
        role=np.array([0] + [1] * (n_veh - 1), dtype=np.int8),
        alive=np.ones(n_veh, dtype=bool),
        hp=np.ones(n_veh, dtype=float),
        fuel=np.full(n_veh, np.inf),
        tgt_x=np.zeros(n_veh, dtype=float),
        tgt_y=np.zeros(n_veh, dtype=float),
        seen=np.zeros(n_veh, dtype=bool),
        leader=np.array([-1] + list(range(n_veh - 1)), dtype=np.int32),
        max_speed=np.full(n_veh, 12.0),
        turn_rate=np.full(n_veh, 1.5),
        sensor_range=np.full(n_veh, 400.0),
        weapon_range=np.full(n_veh, 200.0),
        pk_base=np.full(n_veh, 0.01),
        domain=np.full(n_veh, GROUND, dtype=np.int8),
        convoy_role=np.array([ROLE_CONTROL, ROLE_CARGO, ROLE_CARGO, ROLE_CARGO, ROLE_CARGO, ROLE_RECOVERY], dtype=np.int8),
        march_unit=np.zeros(n_veh, dtype=np.int16),
        serial=np.zeros(n_veh, dtype=np.int16),
        section=np.array([SECTION_HEAD, SECTION_MAIN, SECTION_MAIN, SECTION_MAIN, SECTION_MAIN, SECTION_TRAIL], dtype=np.int8),
        cargo=np.array([0.0, 5.0, 5.0, 5.0, 5.0, 0.0], dtype=float),
        cargo_delivered=np.zeros(n_veh, dtype=float),
        progress=np.zeros(n_veh, dtype=float),
    )

    scn = Scenario(
        name="dogleg_stationing_preset",
        size=(1800.0, 2000.0),
        platform_types=ptypes,
        terrain={"profile": "open", "cell": 20.0},
        forces=[ForceSpec(side=BLUE, ptype="truck", count=n_veh, spawn=pts[0], route=pts, spacing=spacing)],
        objective=Objective(goal=pts[-1], goal_radius=80.0),
        params={"convoy": {"pace": 10.0, "time_gap": 2.5, "march_unit_size": 6, "roles": ["control", "cargo", "cargo", "cargo", "cargo", "recovery"]}, "route": pts},
        duration=140.0,
        dt=1.0,
    )

    rng = np.random.default_rng(21)
    world = build_world(scn, rng)
    world.route = poly

    bhv = _make_bhv(ent, topology="chain")

    frames: list[dict[str, Any]] = []
    goal = np.array(pts[-1])
    goal_r = 80.0

    steps = 140
    for step_idx in range(steps):
        t = round(step_idx * scn.dt, 1)

        dist_to_goal = np.hypot(ent.x - goal[0], ent.y - goal[1])
        at_goal = (dist_to_goal <= goal_r) & ent.alive
        ent.cargo_delivered[at_goal] = ent.cargo[at_goal]

        # Update follower tracking
        for i in range(1, n_veh):
            ref = i - 1
            in_range = float(np.hypot(ent.x[ref] - ent.x[i], ent.y[ref] - ent.y[i])) <= bhv.sense_range
            if in_range:
                bhv.trk_x[i] = ent.x[ref]
                bhv.trk_y[i] = ent.y[ref]
                bhv.trk_vx[i] = ent.speed[ref] * np.cos(ent.heading[ref])
                bhv.trk_vy[i] = ent.speed[ref] * np.sin(ent.heading[ref])
                bhv.trk_age[i] = 0
            else:
                bhv.trk_age[i] += 1
                bhv.trk_stale_steps[i] += 1
                bhv.trk_x[i] += bhv.trk_vx[i] * scn.dt
                bhv.trk_y[i] += bhv.trk_vy[i] * scn.dt

        planning.step(ent, world, scn, float(ent.x[0]), bhv=bhv)

        s_lead, _ = poly.project(ent.x[0], ent.y[0])
        s_carrot = min(s_lead + 30.0, poly.total_length)
        cx, cy, _ = poly.point_at(s_carrot)
        ent.tgt_x[0] = cx
        ent.tgt_y[0] = cy

        motion.step(ent, world, scn.dt, tempo=1.0)

        s_vals, d_perp_vals = poly.project(ent.x, ent.y)

        inter_gaps = [0.0]
        for i in range(1, n_veh):
            inter_gaps.append(round(float(s_vals[i - 1] - s_vals[i]), 1))

        frames.append({
            "t": t,
            "x": [round(float(v), 1) for v in ent.x],
            "y": [round(float(v), 1) for v in ent.y],
            "h": [round(float(v), 2) for v in ent.heading],
            "speed": [round(float(v), 1) for v in ent.speed],
            "alive": [int(v) for v in ent.alive],
            "seen": [int(v) for v in ent.seen],
            "progress": [round(float(v), 1) for v in s_vals],
            "cross_track": [round(float(v), 1) for v in d_perp_vals],
            "inter_gap": inter_gaps,
            "cargo_delivered": [round(float(v), 1) for v in ent.cargo_delivered],
            "kills": [],
        })

    callsigns = ["V1 (Lead Truck)", "V2 (Cargo 5t)", "V3 (Cargo 5t)", "V4 (Cargo 5t)", "V5 (Cargo 5t)", "V6 (Trail Recovery)"]

    return {
        "id": "dogleg_stationing",
        "title": "Arc-Length Stationing: 90-Degree Turn",
        "subtitle": "ATP 4-16 App. C & ATP 4-11 Lane Discipline (Issue #13)",
        "desc": "Convoys track the road centerline using 1D arc-length coordinates s. Follower targets stay constrained to the surveyed road curve, eliminating corner-cutting across ditches and obstacles.",
        "world_size": [1800.0, 2000.0],
        "route": [[float(x), float(y)] for x, y in pts],
        "building_boxes": [],
        "objective": {"goal": pts[-1], "radius": goal_r},
        "entities": [
            {
                "id": i,
                "callsign": callsigns[i],
                "side": int(ent.side[i]),
                "domain": int(ent.domain[i]),
                "convoy_role": int(ent.convoy_role[i]),
                "march_unit": int(ent.march_unit[i]),
                "serial": int(ent.serial[i]),
                "section": int(ent.section[i]),
                "cargo": float(ent.cargo[i]),
                "length": 6.0,
            }
            for i in range(n_veh)
        ],
        "frames": frames,
        "total_cargo": 20.0,
        "route_length": round(poly.total_length, 1),
        "doctrinal_pace": 10.0,
        "doctrinal_time_gap": 2.5,
    }


def generate_payload() -> dict[str, Any]:
    print("Generating Preset 1: Urban Street Graph & Occlusion...")
    p1 = _simulate_urban_preset()

    print("Generating Preset 2: Tactical MSR Convoy with Escorts & Ambush...")
    p2 = _simulate_msr_ambush_preset()

    print("Generating Preset 3: Doctrinal Spacing (Dispersed Column)...")
    p3 = _simulate_spacing_preset(is_dispersed=True)

    print("Generating Preset 4: Arc-Length Stationing Dogleg Turn...")
    p4 = _simulate_dogleg_stationing_preset()

    return {
        "version": "2.0.0",
        "title": "SandTable Unified Convoy Mission Viewer",
        "doctrinal_foundations": {
            "atp_4_11": "Army Motor Transport Operations (March 2026): Convoy Hierarchy, Roles, and Formations",
            "atp_4_16": "Movement Control (April 2026): Road Space, Time Gap Headway, and Pass Time",
            "fm_4_0": "Sustainment Operations: Cargo Payload Delivery & Loss Attribution in Contested Logistics",
        },
        "presets": [p1, p2, p3, p4],
    }


def generate_html(data_payload: dict[str, Any]) -> str:
    data_json_str = json.dumps(data_payload)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SandTable - Convoy Mission Replay Console v2</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-deep: #060913;
      --bg-panel: rgba(13, 22, 40, 0.85);
      --bg-card: rgba(18, 30, 54, 0.75);
      --bg-card-hover: rgba(28, 44, 78, 0.9);
      --border-panel: rgba(56, 189, 248, 0.18);
      --border-accent: rgba(56, 189, 248, 0.45);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-sub: #64748b;
      --cyan: #38bdf8;
      --cyan-glow: rgba(56, 189, 248, 0.35);
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.35);
      --amber: #f59e0b;
      --amber-glow: rgba(245, 158, 11, 0.35);
      --rose: #f43f5e;
      --rose-glow: rgba(244, 63, 94, 0.35);
      --purple: #a855f7;
      --purple-glow: rgba(168, 85, 247, 0.35);
      --blue: #3b82f6;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: radial-gradient(circle at 50% 0%, #0d1629 0%, var(--bg-deep) 100%);
      color: var(--text-main);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      overflow-x: hidden;
      padding-bottom: 2rem;
    }}

    /* Header Nav */
    header {{
      background: rgba(7, 12, 23, 0.92);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--border-panel);
      padding: 0.9rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 1.2rem;
    }}

    .logo-badge {{
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      color: #031124;
      font-weight: 800;
      font-size: 0.82rem;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      letter-spacing: 0.08em;
    }}

    h1 {{
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #fff;
    }}

    .header-tag {{
      background: rgba(56, 189, 248, 0.12);
      color: var(--cyan);
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
    }}

    .header-nav {{
      display: flex;
      gap: 0.6rem;
    }}

    .nav-btn {{
      background: rgba(30, 41, 59, 0.6);
      color: var(--text-muted);
      border: 1px solid rgba(148, 163, 184, 0.15);
      padding: 0.45rem 0.9rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 500;
      text-decoration: none;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}

    .nav-btn:hover {{
      background: rgba(56, 189, 248, 0.15);
      color: #fff;
      border-color: var(--cyan);
    }}

    .nav-btn.active {{
      background: rgba(56, 189, 248, 0.2);
      color: var(--cyan);
      border-color: var(--cyan);
      box-shadow: 0 0 10px var(--cyan-glow);
    }}

    /* Main Container */
    .container {{
      max-width: 1720px;
      margin: 1.2rem auto;
      padding: 0 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.2rem;
    }}

    /* Presets Bar */
    .presets-bar {{
      display: flex;
      gap: 0.8rem;
      background: var(--bg-panel);
      padding: 0.7rem;
      border-radius: 12px;
      border: 1px solid var(--border-panel);
      align-items: center;
      overflow-x: auto;
    }}

    .presets-label {{
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--cyan);
      padding: 0 0.8rem;
      white-space: nowrap;
    }}

    .preset-btn {{
      background: rgba(18, 30, 54, 0.7);
      border: 1px solid rgba(56, 189, 248, 0.18);
      color: var(--text-muted);
      padding: 0.6rem 1.1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0.15rem;
      white-space: nowrap;
    }}

    .preset-btn:hover {{
      background: var(--bg-card-hover);
      color: #fff;
      border-color: var(--cyan);
    }}

    .preset-btn.active {{
      background: rgba(56, 189, 248, 0.15);
      color: #fff;
      border-color: var(--cyan);
      box-shadow: 0 0 15px var(--cyan-glow);
    }}

    .preset-sub {{
      font-size: 0.7rem;
      color: var(--text-sub);
      font-weight: 400;
    }}

    .preset-btn.active .preset-sub {{
      color: var(--cyan);
    }}

    /* KPI Command Ribbon */
    .kpi-ribbon {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
    }}

    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-panel);
      border-radius: 10px;
      padding: 1rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      position: relative;
      overflow: hidden;
    }}

    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
    }}

    .kpi-cargo::before {{ background: var(--emerald); }}
    .kpi-doctrine::before {{ background: var(--cyan); }}
    .kpi-stationing::before {{ background: var(--amber); }}
    .kpi-force::before {{ background: var(--purple); }}

    .kpi-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .kpi-title {{
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}

    .kpi-badge {{
      font-size: 0.7rem;
      font-weight: 600;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
    }}

    .badge-cargo {{ background: rgba(16, 185, 129, 0.2); color: var(--emerald); }}
    .badge-doctrine {{ background: rgba(56, 189, 248, 0.2); color: var(--cyan); }}
    .badge-stationing {{ background: rgba(245, 158, 11, 0.2); color: var(--amber); }}
    .badge-force {{ background: rgba(168, 85, 247, 0.2); color: var(--purple); }}

    .kpi-main-val {{
      font-size: 1.5rem;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      color: #fff;
    }}

    .kpi-progress-bar {{
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 3px;
      overflow: hidden;
      margin-top: 0.2rem;
    }}

    .kpi-progress-fill {{
      height: 100%;
      border-radius: 3px;
      transition: width 0.3s ease;
    }}

    .fill-cargo {{ background: var(--emerald); }}
    .fill-doctrine {{ background: var(--cyan); }}
    .fill-stationing {{ background: var(--amber); }}
    .fill-force {{ background: var(--purple); }}

    .kpi-metrics-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.4rem;
      margin-top: 0.4rem;
      padding-top: 0.4rem;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
    }}

    .kpi-sub-item {{
      display: flex;
      flex-direction: column;
    }}

    .kpi-sub-label {{
      font-size: 0.7rem;
      color: var(--text-sub);
    }}

    .kpi-sub-val {{
      font-size: 0.85rem;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-main);
    }}

    /* Main Console Grid */
    .console-grid {{
      display: grid;
      grid-template-columns: 1fr 410px;
      gap: 1.2rem;
      height: 640px;
    }}

    /* 2D Canvas Area */
    .canvas-container {{
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      border-radius: 12px;
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}

    .canvas-toolbar {{
      background: rgba(13, 22, 40, 0.95);
      border-bottom: 1px solid var(--border-panel);
      padding: 0.5rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
    }}

    .canvas-info {{
      display: flex;
      align-items: center;
      gap: 0.8rem;
    }}

    .scenario-title {{
      font-size: 0.9rem;
      font-weight: 700;
      color: #fff;
    }}

    .canvas-tools {{
      display: flex;
      gap: 0.5rem;
    }}

    .tool-btn {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(148, 163, 184, 0.2);
      color: var(--text-muted);
      padding: 0.3rem 0.6rem;
      border-radius: 5px;
      font-size: 0.75rem;
      cursor: pointer;
    }}

    .tool-btn:hover {{
      color: #fff;
      border-color: var(--cyan);
    }}

    .tool-btn.active {{
      background: rgba(56, 189, 248, 0.2);
      color: var(--cyan);
      border-color: var(--cyan);
    }}

    canvas {{
      flex: 1;
      width: 100%;
      height: 100%;
      display: block;
      cursor: crosshair;
    }}

    .canvas-legend {{
      position: absolute;
      bottom: 1rem;
      left: 1rem;
      background: rgba(7, 12, 23, 0.88);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-panel);
      border-radius: 8px;
      padding: 0.5rem 0.8rem;
      display: flex;
      gap: 1rem;
      font-size: 0.72rem;
      color: var(--text-muted);
      z-index: 5;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }}

    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 2px;
    }}

    /* Sidebar Rail */
    .sidebar-rail {{
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .sidebar-tabs {{
      display: flex;
      border-bottom: 1px solid var(--border-panel);
      background: rgba(13, 22, 40, 0.95);
    }}

    .tab-btn {{
      flex: 1;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      padding: 0.7rem 0.5rem;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s ease;
    }}

    .tab-btn:hover {{
      color: #fff;
    }}

    .tab-btn.active {{
      color: var(--cyan);
      border-bottom-color: var(--cyan);
      background: rgba(56, 189, 248, 0.08);
    }}

    .tab-content {{
      flex: 1;
      overflow-y: auto;
      padding: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }}

    /* Hierarchy Tree */
    .unit-group {{
      background: var(--bg-card);
      border: 1px solid rgba(56, 189, 248, 0.12);
      border-radius: 8px;
      overflow: hidden;
    }}

    .unit-header {{
      background: rgba(30, 41, 59, 0.4);
      padding: 0.5rem 0.7rem;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--cyan);
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
    }}

    .unit-vehicles {{
      padding: 0.4rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}

    .vehicle-row {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 6px;
      padding: 0.45rem 0.6rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .vehicle-row:hover {{
      background: var(--bg-card-hover);
      border-color: var(--cyan);
    }}

    .vehicle-row.selected {{
      border-color: var(--cyan);
      background: rgba(56, 189, 248, 0.15);
    }}

    .veh-info {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .role-badge {{
      font-size: 0.65rem;
      font-weight: 700;
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
    }}

    .role-control {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
    .role-cargo {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .role-security {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
    .role-recovery {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; }}

    .veh-status {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      color: var(--text-muted);
    }}

    /* Event Log */
    .event-log {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
    }}

    .log-item {{
      background: rgba(15, 23, 42, 0.5);
      border-left: 3px solid var(--cyan);
      padding: 0.35rem 0.55rem;
      border-radius: 0 4px 4px 0;
      color: var(--text-muted);
    }}

    .log-item.kill {{ border-color: var(--rose); color: #fda4af; }}
    .log-item.cargo {{ border-color: var(--emerald); color: #a7f3d0; }}
    .log-item.occlusion {{ border-color: var(--amber); color: #fde68a; }}

    .log-time {{
      color: var(--cyan);
      font-weight: 700;
      margin-right: 0.3rem;
    }}

    /* Bottom Timeline Controls */
    .playback-bar {{
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      border-radius: 12px;
      padding: 0.8rem 1.4rem;
      display: flex;
      align-items: center;
      gap: 1.2rem;
    }}

    .ctrl-btn {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(148, 163, 184, 0.25);
      color: #fff;
      padding: 0.5rem 0.9rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}

    .ctrl-btn:hover {{
      background: rgba(56, 189, 248, 0.25);
      border-color: var(--cyan);
    }}

    .ctrl-btn.play {{
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      color: #031124;
      border: none;
      font-weight: 700;
      box-shadow: 0 0 12px var(--cyan-glow);
    }}

    .slider-container {{
      flex: 1;
      display: flex;
      align-items: center;
      gap: 1rem;
    }}

    .time-slider {{
      flex: 1;
      height: 6px;
      -webkit-appearance: none;
      appearance: none;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 3px;
      outline: none;
      cursor: pointer;
    }}

    .time-slider::-webkit-slider-thumb {{
      -webkit-appearance: none;
      appearance: none;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--cyan);
      box-shadow: 0 0 8px var(--cyan);
      cursor: pointer;
    }}

    .time-display {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.95rem;
      font-weight: 700;
      color: #fff;
      min-width: 90px;
    }}

    .speed-pills {{
      display: flex;
      gap: 0.3rem;
      background: rgba(15, 23, 42, 0.6);
      padding: 0.2rem;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .speed-btn {{
      background: none;
      border: none;
      color: var(--text-muted);
      padding: 0.25rem 0.55rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
    }}

    .speed-btn.active {{
      background: rgba(56, 189, 248, 0.25);
      color: var(--cyan);
    }}
  </style>
</head>
<body>

  <!-- Top Navigation -->
  <header>
    <div class="header-left">
      <span class="logo-badge">SANDTABLE</span>
      <h1>Convoy Mission Replay Console v2</h1>
      <span class="header-tag">Joint ATP 4-11, ATP 4-16 & FM 4-0 Testbench</span>
    </div>
    <div class="header-nav">
      <a href="mission_viewer_v2.html" class="nav-btn active">⭐ Mission Viewer v2</a>
      <a href="route_dashboard.html" class="nav-btn">🛣️ Route Stationing (Issue #13)</a>
      <a href="cargo_dashboard.html" class="nav-btn">📦 Cargo & Logistics (FM 4-0)</a>
      <a href="convoy_results.html" class="nav-btn">📊 Separation Search (Issue #15)</a>
      <a href="mission_viewer.html" class="nav-btn">🗺️ Mission Viewer (v1)</a>
    </div>
  </header>

  <div class="container">

    <!-- Presets Bar -->
    <div class="presets-bar">
      <span class="presets-label">Operational Scenarios:</span>
      <div id="presetsList" style="display: flex; gap: 0.8rem;"></div>
    </div>

    <!-- KPI Command Ribbon -->
    <div class="kpi-ribbon">

      <!-- Card 1: FM 4-0 Cargo Payload -->
      <div class="kpi-card kpi-cargo">
        <div class="kpi-header">
          <span class="kpi-title">FM 4-0 Logistics Delivery</span>
          <span class="kpi-badge badge-cargo" id="cargoPctBadge">0% DELIVERED</span>
        </div>
        <div class="kpi-main-val" id="valCargoDelivered">0.0 / 0.0 t</div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress-fill fill-cargo" id="barCargo" style="width: 0%;"></div>
        </div>
        <div class="kpi-metrics-grid">
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">In-Transit Freight</span>
            <span class="kpi-sub-val" id="valCargoTransit">0.0 t</span>
          </div>
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Throughput Rate</span>
            <span class="kpi-sub-val" id="valThroughput">0.0 t/hr</span>
          </div>
        </div>
      </div>

      <!-- Card 2: ATP 4-16 Spacing & Headway -->
      <div class="kpi-card kpi-doctrine">
        <div class="kpi-header">
          <span class="kpi-title">ATP 4-16 Spacing & Headway</span>
          <span class="kpi-badge badge-doctrine" id="doctrineBadge">OPEN MARCH</span>
        </div>
        <div class="kpi-main-val" id="valHeadway">0.0 s</div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress-fill fill-doctrine" id="barHeadway" style="width: 50%;"></div>
        </div>
        <div class="kpi-metrics-grid">
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Column Pace</span>
            <span class="kpi-sub-val" id="valPace">0.0 m/s</span>
          </div>
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Column Road Space</span>
            <span class="kpi-sub-val" id="valRoadSpace">0 m</span>
          </div>
        </div>
      </div>

      <!-- Card 3: Route Stationing & Occlusion -->
      <div class="kpi-card kpi-stationing">
        <div class="kpi-header">
          <span class="kpi-title">Route Stationing & LOS</span>
          <span class="kpi-badge badge-stationing" id="losBadge">CLEAR [LOS]</span>
        </div>
        <div class="kpi-main-val" id="valStationing">0 m</div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress-fill fill-stationing" id="barStationing" style="width: 0%;"></div>
        </div>
        <div class="kpi-metrics-grid">
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Max Lateral Error (d_perp)</span>
            <span class="kpi-sub-val" id="valCrossTrack">0.0 m</span>
          </div>
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Route Progress (s/L)</span>
            <span class="kpi-sub-val" id="valRouteProgress">0%</span>
          </div>
        </div>
      </div>

      <!-- Card 4: Force Survivability & Defense -->
      <div class="kpi-card kpi-force">
        <div class="kpi-header">
          <span class="kpi-title">Force Survivability</span>
          <span class="kpi-badge badge-force" id="forceBadge">100% ALIVE</span>
        </div>
        <div class="kpi-main-val" id="valBlueAlive">0 / 0</div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress-fill fill-force" id="barForce" style="width: 100%;"></div>
        </div>
        <div class="kpi-metrics-grid">
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Red Losses</span>
            <span class="kpi-sub-val" id="valRedLosses">0</span>
          </div>
          <div class="kpi-sub-item">
            <span class="kpi-sub-label">Armed Escorts</span>
            <span class="kpi-sub-val" id="valEscorts">0 Active</span>
          </div>
        </div>
      </div>

    </div>

    <!-- Main Console Grid -->
    <div class="console-grid">

      <!-- 2D Tactical Canvas Container -->
      <div class="canvas-container">
        <div class="canvas-toolbar">
          <div class="canvas-info">
            <span class="scenario-title" id="dispTitle">Scenario Title</span>
            <span style="font-size: 0.75rem; color: var(--text-sub);" id="dispSubtitle">Subtitle</span>
          </div>
          <div class="canvas-tools">
            <button class="tool-btn active" id="btnToggleRays" onclick="toggleOption('rays')">👁️ LOS Rays</button>
            <button class="tool-btn active" id="btnTogglePath" onclick="toggleOption('path')">🛣️ Route</button>
            <button class="tool-btn active" id="btnToggleBadges" onclick="toggleOption('badges')">🏷️ Labels</button>
          </div>
        </div>

        <canvas id="tacticalCanvas"></canvas>

        <div class="canvas-legend">
          <div class="legend-item"><div class="legend-dot" style="background: var(--blue);"></div> C2 / Pacesetter</div>
          <div class="legend-item"><div class="legend-dot" style="background: var(--emerald);"></div> Cargo (FM 4-0)</div>
          <div class="legend-item"><div class="legend-dot" style="background: var(--amber);"></div> Escort Gun Truck</div>
          <div class="legend-item"><div class="legend-dot" style="background: var(--purple);"></div> Trail / Recovery</div>
          <div class="legend-item"><div class="legend-dot" style="background: var(--rose);"></div> Red Threat</div>
          <div class="legend-item"><div class="legend-dot" style="border: 1px dashed var(--cyan);"></div> Optical LOS</div>
          <div class="legend-item"><div class="legend-dot" style="border: 1px dotted var(--rose);"></div> Blocked LOS</div>
        </div>
      </div>

      <!-- Sidebar Rail -->
      <div class="sidebar-rail">
        <div class="sidebar-tabs">
          <button class="tab-btn active" onclick="switchTab('hierarchy')">Hierarchy (ATP 4-11)</button>
          <button class="tab-btn" onclick="switchTab('manifest')">Manifest</button>
          <button class="tab-btn" onclick="switchTab('events')">Tactical Events</button>
        </div>

        <div class="tab-content" id="tabHierarchy">
          <div id="hierarchyTree"></div>
        </div>

        <div class="tab-content" id="tabManifest" style="display: none;">
          <div id="manifestList" style="display: flex; flex-direction: column; gap: 0.4rem;"></div>
        </div>

        <div class="tab-content" id="tabEvents" style="display: none;">
          <div class="event-log" id="eventLogList"></div>
        </div>
      </div>

    </div>

    <!-- Bottom Timeline Playback Bar -->
    <div class="playback-bar">
      <button class="ctrl-btn play" id="btnPlay" onclick="togglePlay()">▶ Play</button>
      <button class="ctrl-btn" onclick="resetPlay()">↺ Reset</button>

      <div class="slider-container">
        <span class="time-display" id="timeDisplay">t = 0.0 s</span>
        <input type="range" class="time-slider" id="timelineSlider" min="0" max="100" value="0" oninput="onScrub(this.value)">
      </div>

      <div class="speed-pills">
        <button class="speed-btn" onclick="setSpeed(0.5, this)">0.5x</button>
        <button class="speed-btn active" onclick="setSpeed(1.0, this)">1x</button>
        <button class="speed-btn" onclick="setSpeed(2.0, this)">2x</button>
        <button class="speed-btn" onclick="setSpeed(5.0, this)">5x</button>
      </div>
    </div>

  </div>

  <script>
    const DATA = {data_json_str};

    let activePresetIdx = 0;
    let currentPreset = DATA.presets[0];
    let currentFrameIdx = 0;
    let isPlaying = false;
    let playbackSpeed = 1.0;
    let animTimer = null;
    let selectedVehId = null;

    let options = {{
      rays: true,
      path: true,
      badges: true
    }};

    const canvas = document.getElementById('tacticalCanvas');
    const ctx = canvas.getContext('2d');

    function init() {{
      buildPresetButtons();
      loadPreset(0);
      setupResize();
    }}

    function buildPresetButtons() {{
      const container = document.getElementById('presetsList');
      container.innerHTML = '';
      DATA.presets.forEach((p, idx) => {{
        const btn = document.createElement('button');
        btn.className = 'preset-btn' + (idx === 0 ? ' active' : '');
        btn.innerHTML = `<span>${{p.title}}</span><span class="preset-sub">${{p.subtitle}}</span>`;
        btn.onclick = () => loadPreset(idx);
        container.appendChild(btn);
      }});
    }}

    function loadPreset(idx) {{
      activePresetIdx = idx;
      currentPreset = DATA.presets[idx];
      currentFrameIdx = 0;
      isPlaying = false;
      document.getElementById('btnPlay').textContent = '▶ Play';

      document.querySelectorAll('.preset-btn').forEach((b, i) => {{
        b.classList.toggle('active', i === idx);
      }});

      document.getElementById('dispTitle').textContent = currentPreset.title;
      document.getElementById('dispSubtitle').textContent = currentPreset.subtitle;

      const slider = document.getElementById('timelineSlider');
      slider.max = currentPreset.frames.length - 1;
      slider.value = 0;

      buildHierarchyTree();
      buildManifest();
      buildEventLog();
      renderFrame(0);
    }}

    function buildHierarchyTree() {{
      const tree = document.getElementById('hierarchyTree');
      tree.innerHTML = '';

      const blueEnts = currentPreset.entities.filter(e => e.side === 0);
      const units = {{}};
      blueEnts.forEach(e => {{
        const mu = e.march_unit >= 0 ? e.march_unit : 0;
        if (!units[mu]) units[mu] = [];
        units[mu].push(e);
      }});

      Object.keys(units).sort().forEach(muKey => {{
        const group = document.createElement('div');
        group.className = 'unit-group';
        const header = document.createElement('div');
        header.className = 'unit-header';
        header.innerHTML = `<span>March Unit ${{parseInt(muKey) + 1}} (${{units[muKey].length}} vehicles)</span><span>▼</span>`;
        group.appendChild(header);

        const vList = document.createElement('div');
        vList.className = 'unit-vehicles';
        units[muKey].forEach(e => {{
          const row = document.createElement('div');
          row.className = 'vehicle-row';
          row.id = `vehRow_${{e.id}}`;
          row.onclick = () => selectVehicle(e.id);

          let rClass = 'role-cargo';
          let rName = 'CARGO';
          if (e.convoy_role === 0) {{ rClass = 'role-control'; rName = 'LEAD'; }}
          else if (e.convoy_role === 2) {{ rClass = 'role-security'; rName = 'ESCORT'; }}
          else if (e.convoy_role === 3) {{ rClass = 'role-recovery'; rName = 'TRAIL'; }}

          row.innerHTML = `
            <div class="veh-info">
              <span class="role-badge ${{rClass}}">${{rName}}</span>
              <span style="font-weight:600; color:#fff;">${{e.callsign}}</span>
            </div>
            <span class="veh-status" id="vehStatus_${{e.id}}">0m</span>
          `;
          vList.appendChild(row);
        }});
        group.appendChild(vList);
        tree.appendChild(group);
      }});
    }}

    function buildManifest() {{
      const list = document.getElementById('manifestList');
      list.innerHTML = '';
      currentPreset.entities.forEach(e => {{
        const row = document.createElement('div');
        row.className = 'vehicle-row';
        row.id = `manRow_${{e.id}}`;
        row.onclick = () => selectVehicle(e.id);
        const isBlue = e.side === 0;
        row.innerHTML = `
          <div class="veh-info">
            <span style="color: ${{isBlue ? 'var(--cyan)' : 'var(--rose)'}}; font-weight:700;">#${{e.id + 1}}</span>
            <span>${{e.callsign}}</span>
          </div>
          <span class="veh-status" id="manStatus_${{e.id}}">${{isBlue ? (e.cargo > 0 ? e.cargo + 't' : 'Ready') : 'Threat'}}</span>
        `;
        list.appendChild(row);
      }});
    }}

    function buildEventLog() {{
      const log = document.getElementById('eventLogList');
      log.innerHTML = '';

      const items = [];
      items.push({{ t: '0.0s', type: 'info', text: 'Convoy SP (Start Point) departed. Column ordered in lane.' }});

      if (currentPreset.id === 'urban_grid') {{
        items.push({{ t: '14.0s', type: 'occlusion', text: 'Lead vehicle V1 rounded Block 1 at WP2; line-of-sight occluded for V2.' }});
        items.push({{ t: '22.0s', type: 'info', text: 'V2 rounded WP2; optical contact re-established with lead.' }});
        items.push({{ t: '65.0s', type: 'cargo', text: 'V1 reached destination WP5; discharge operations initiated.' }});
      }} else if (currentPreset.id === 'msr_ambush') {{
        items.push({{ t: '32.0s', type: 'occlusion', text: 'Red Ambush team detected in defilade ridge at [3000, 1500].' }});
        items.push({{ t: '36.5s', type: 'kill', text: 'Gun Truck Escort engaged Red ambush position with direct fire.' }});
        items.push({{ t: '58.0s', type: 'cargo', text: 'First cargo serial entered destination perimeter with payload intact.' }});
      }} else {{
        items.push({{ t: '18.0s', type: 'info', text: 'Pacesetter vehicle locked doctrinal cruising speed along MSR.' }});
      }}

      items.forEach(it => {{
        const div = document.createElement('div');
        div.className = `log-item ${{it.type}}`;
        div.innerHTML = `<span class="log-time">${{it.t}}</span> ${{it.text}}`;
        log.appendChild(div);
      }});
    }}

    function selectVehicle(id) {{
      selectedVehId = (selectedVehId === id) ? null : id;
      document.querySelectorAll('.vehicle-row').forEach(r => {{
        r.classList.toggle('selected', r.id === `vehRow_${{id}}` || r.id === `manRow_${{id}}`);
      }});
      renderFrame(currentFrameIdx);
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
      if (tabId === 'hierarchy') {{
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
        document.getElementById('tabHierarchy').style.display = 'flex';
      }} else if (tabId === 'manifest') {{
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
        document.getElementById('tabManifest').style.display = 'flex';
      }} else {{
        document.querySelectorAll('.tab-btn')[2].classList.add('active');
        document.getElementById('tabEvents').style.display = 'flex';
      }}
    }}

    function toggleOption(opt) {{
      options[opt] = !options[opt];
      const btnMap = {{ rays: 'btnToggleRays', path: 'btnTogglePath', badges: 'btnToggleBadges' }};
      document.getElementById(btnMap[opt]).classList.toggle('active', options[opt]);
      renderFrame(currentFrameIdx);
    }}

    function togglePlay() {{
      isPlaying = !isPlaying;
      document.getElementById('btnPlay').textContent = isPlaying ? '⏸ Pause' : '▶ Play';
      if (isPlaying) runAnimation();
    }}

    function resetPlay() {{
      isPlaying = false;
      document.getElementById('btnPlay').textContent = '▶ Play';
      currentFrameIdx = 0;
      document.getElementById('timelineSlider').value = 0;
      renderFrame(0);
    }}

    function setSpeed(spd, el) {{
      playbackSpeed = spd;
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
    }}

    function onScrub(val) {{
      currentFrameIdx = parseInt(val);
      renderFrame(currentFrameIdx);
    }}

    function runAnimation() {{
      if (!isPlaying) return;
      currentFrameIdx++;
      if (currentFrameIdx >= currentPreset.frames.length) {{
        currentFrameIdx = 0;
      }}
      document.getElementById('timelineSlider').value = currentFrameIdx;
      renderFrame(currentFrameIdx);
      setTimeout(() => {{
        requestAnimationFrame(runAnimation);
      }}, 50 / playbackSpeed);
    }}

    function renderFrame(idx) {{
      const frame = currentPreset.frames[idx];
      if (!frame) return;

      document.getElementById('timeDisplay').textContent = `t = ${{frame.t.toFixed(1)}} s`;

      updateKPICards(frame);
      updateSidebarTelemetry(frame);

      drawCanvas(frame);
    }}

    function updateKPICards(frame) {{
      const totalCargo = currentPreset.total_cargo || 0.0;
      let deliveredCargo = 0.0;
      if (frame.cargo_delivered) {{
        deliveredCargo = frame.cargo_delivered.reduce((a, b) => a + b, 0);
      }}
      const transitCargo = Math.max(0.0, totalCargo - deliveredCargo);
      const cargoPct = totalCargo > 0 ? (deliveredCargo / totalCargo) * 100 : 0;

      document.getElementById('valCargoDelivered').textContent = `${{deliveredCargo.toFixed(1)}} / ${{totalCargo.toFixed(1)}} t`;
      document.getElementById('barCargo').style.width = `${{cargoPct}}%`;
      document.getElementById('cargoPctBadge').textContent = `${{cargoPct.toFixed(0)}}% DELIVERED`;
      document.getElementById('valCargoTransit').textContent = `${{transitCargo.toFixed(1)}} t`;

      const tHr = frame.t > 0 ? (deliveredCargo / (frame.t / 3600)) : 0;
      document.getElementById('valThroughput').textContent = `${{tHr.toFixed(0)}} t/hr`;

      // Spacing & Headway
      const pace = currentPreset.doctrinal_pace || 10.0;
      const tGap = currentPreset.doctrinal_time_gap || 4.0;
      document.getElementById('valHeadway').textContent = `${{tGap.toFixed(1)}} s`;
      document.getElementById('valPace').textContent = `${{pace.toFixed(1)}} m/s (${{(pace * 3.6).toFixed(0)}} km/h)`;

      const blueEnts = currentPreset.entities.filter(e => e.side === 0);
      const roadSpace = (blueEnts.length - 1) * (pace * tGap);
      document.getElementById('valRoadSpace').textContent = `${{roadSpace.toFixed(0)}} m`;
      document.getElementById('doctrineBadge').textContent = tGap >= 5.0 ? 'OPEN MARCH' : 'CLOSED MARCH';

      // Stationing & LOS
      let maxProg = 0.0;
      let maxCross = 0.0;
      if (frame.progress) {{
        maxProg = Math.max(...frame.progress.filter(v => v !== null));
      }}
      if (frame.cross_track) {{
        maxCross = Math.max(...frame.cross_track.filter(v => v !== null));
      }}
      document.getElementById('valStationing').textContent = `${{maxProg.toFixed(0)}} m`;
      document.getElementById('valCrossTrack').textContent = `${{maxCross.toFixed(1)}} m`;

      const rLen = currentPreset.route_length || 1000.0;
      const rPct = Math.min(100, (maxProg / rLen) * 100);
      document.getElementById('barStationing').style.width = `${{rPct}}%`;
      document.getElementById('valRouteProgress').textContent = `${{rPct.toFixed(0)}}%`;

      // Line of sight status
      let allLos = true;
      if (frame.los_to_pred) {{
        allLos = frame.los_to_pred.every(v => v === true);
      }}
      const losBadge = document.getElementById('losBadge');
      if (allLos) {{
        losBadge.textContent = 'CLEAR [LOS]';
        losBadge.className = 'kpi-badge badge-cargo';
      }} else {{
        losBadge.textContent = 'OCCLUDED [BLIND]';
        losBadge.className = 'kpi-badge badge-force';
      }}

      // Survivability
      const blueAlive = frame.alive.slice(0, blueEnts.length).reduce((a, b) => a + b, 0);
      const blueTotal = blueEnts.length;
      document.getElementById('valBlueAlive').textContent = `${{blueAlive}} / ${{blueTotal}}`;
      document.getElementById('barForce').style.width = `${{(blueAlive / blueTotal) * 100}}%`;

      let redKills = 0;
      if (frame.alive.length > blueTotal) {{
        const redAlive = frame.alive.slice(blueTotal).reduce((a, b) => a + b, 0);
        redKills = (frame.alive.length - blueTotal) - redAlive;
      }}
      document.getElementById('valRedLosses').textContent = `${{redKills}} Killed`;

      const escorts = blueEnts.filter(e => e.convoy_role === 2).length;
      document.getElementById('valEscorts').textContent = `${{escorts}} Gun Trucks`;
    }}

    function updateSidebarTelemetry(frame) {{
      currentPreset.entities.forEach(e => {{
        const statusEl = document.getElementById(`vehStatus_${{e.id}}`);
        if (statusEl && frame.progress) {{
          const s = frame.progress[e.id];
          statusEl.textContent = s !== null ? `${{s.toFixed(0)}}m` : '--';
        }}
        const manEl = document.getElementById(`manStatus_${{e.id}}`);
        if (manEl) {{
          if (frame.alive[e.id] === 0) {{
            manEl.textContent = 'KIA';
            manEl.style.color = 'var(--rose)';
          }} else {{
            const del = (frame.cargo_delivered && frame.cargo_delivered[e.id]) || 0;
            manEl.textContent = e.cargo > 0 ? (del >= e.cargo ? 'Delivered' : `${{del.toFixed(1)}}/${{e.cargo}}t`) : 'Operational';
            manEl.style.color = 'var(--text-muted)';
          }}
        }}
      }});
    }}

    function setupResize() {{
      function resize() {{
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight - 42;
        renderFrame(currentFrameIdx);
      }}
      window.addEventListener('resize', resize);
      resize();
    }}

    function drawCanvas(frame) {{
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const worldW = currentPreset.world_size[0];
      const worldH = currentPreset.world_size[1];

      const scaleX = w / worldW;
      const scaleY = h / worldH;
      const scale = Math.min(scaleX, scaleY) * 0.92;

      const offsetX = (w - worldW * scale) / 2;
      const offsetY = (h - worldH * scale) / 2;

      function toScreenX(x) {{ return offsetX + x * scale; }}
      function toScreenY(y) {{ return h - (offsetY + y * scale); }}

      // 1. Grid
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.lineWidth = 1;
      const gridStep = 200.0 * scale;
      for (let x = offsetX; x < w - offsetX; x += gridStep) {{
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }}
      for (let y = offsetY; y < h - offsetY; y += gridStep) {{
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }}

      // 2. Building Blocks (Issue #16)
      if (currentPreset.building_boxes) {{
        currentPreset.building_boxes.forEach(box => {{
          const bx1 = toScreenX(box[0]);
          const by1 = toScreenY(box[3]);
          const bw = (box[2] - box[0]) * scale;
          const bh = (box[3] - box[1]) * scale;

          ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
          ctx.lineWidth = 1.5;
          ctx.fillRect(bx1, by1, bw, bh);
          ctx.strokeRect(bx1, by1, bw, bh);

          ctx.fillStyle = 'rgba(56, 189, 248, 0.2)';
          ctx.font = '10px JetBrains Mono';
          ctx.textAlign = 'center';
          ctx.fillText('SOLID MASONRY', bx1 + bw / 2, by1 + bh / 2);
        }});
      }}

      // 3. Surveyed Route Polyline (Issue #13)
      if (options.path && currentPreset.route && currentPreset.route.length > 1) {{
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 24 * scale;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        currentPreset.route.forEach((pt, i) => {{
          const sx = toScreenX(pt[0]);
          const sy = toScreenY(pt[1]);
          if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
        }});
        ctx.stroke();

        ctx.strokeStyle = '#facc15';
        ctx.lineWidth = 2;
        ctx.setLineDash([8 * scale, 6 * scale]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Waypoints
        currentPreset.route.forEach((pt, i) => {{
          const sx = toScreenX(pt[0]);
          const sy = toScreenY(pt[1]);
          ctx.fillStyle = '#facc15';
          ctx.beginPath();
          ctx.arc(sx, sy, 4, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
          ctx.font = '10px Outfit';
          ctx.textAlign = 'left';
          ctx.fillText(`WP${{i + 1}}`, sx + 6, sy - 6);
        }});
      }}

      // 4. Line of Sight Rays (Issue #16)
      if (options.rays && frame.los_to_pred) {{
        for (let i = 1; i < currentPreset.entities.length; i++) {{
          if (currentPreset.entities[i].side !== 0) continue;
          if (frame.alive[i] === 0 || frame.alive[i - 1] === 0) continue;

          const sx1 = toScreenX(frame.x[i]);
          const sy1 = toScreenY(frame.y[i]);
          const sx2 = toScreenX(frame.x[i - 1]);
          const sy2 = toScreenY(frame.y[i - 1]);

          const hasLos = frame.los_to_pred[i] !== false;
          ctx.beginPath();
          ctx.moveTo(sx1, sy1);
          ctx.lineTo(sx2, sy2);
          if (hasLos) {{
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.7)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);
          }} else {{
            ctx.strokeStyle = 'rgba(244, 63, 94, 0.85)';
            ctx.lineWidth = 2;
            ctx.setLineDash([2, 2]);
          }}
          ctx.stroke();
          ctx.setLineDash([]);
        }}
      }}

      // 5. Objective Goal Radius
      if (currentPreset.objective) {{
        const gx = toScreenX(currentPreset.objective.goal[0]);
        const gy = toScreenY(currentPreset.objective.goal[1]);
        const gr = currentPreset.objective.radius * scale;

        ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
        ctx.strokeStyle = 'var(--emerald)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(gx, gy, gr, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = 'var(--emerald)';
        ctx.font = '11px Outfit';
        ctx.textAlign = 'center';
        ctx.fillText('OBJECTIVE / DELIVERY GOAL', gx, gy - gr - 6);
      }}

      // 6. Vehicles
      currentPreset.entities.forEach(e => {{
        const isAlive = frame.alive[e.id] === 1;
        const vx = toScreenX(frame.x[e.id]);
        const vy = toScreenY(frame.y[e.id]);
        const heading = (frame.h && frame.h[e.id]) || 0.0;
        const isSelected = selectedVehId === e.id;

        ctx.save();
        ctx.translate(vx, vy);
        ctx.rotate(-heading);

        let color = '#38bdf8';
        if (e.side === 1) {{
          color = '#f43f5e';
        }} else {{
          if (e.convoy_role === 0) color = '#3b82f6';
          else if (e.convoy_role === 1) color = '#10b981';
          else if (e.convoy_role === 2) color = '#f59e0b';
          else if (e.convoy_role === 3) color = '#a855f7';
        }}

        if (!isAlive) {{
          color = '#64748b';
        }}

        const vehLen = (e.length || 6.5) * scale;
        const vehWid = vehLen * 0.55;

        // Selection glow
        if (isSelected) {{
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.arc(0, 0, vehLen * 1.2, 0, Math.PI * 2);
          ctx.stroke();
        }}

        // Hull
        ctx.fillStyle = color;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(-vehLen / 2, -vehWid / 2, vehLen, vehWid, 3);
        ctx.fill();
        ctx.stroke();

        // Direction pointer
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.moveTo(vehLen / 2 - 2, 0);
        ctx.lineTo(vehLen / 2 - 6, -vehWid / 3);
        ctx.lineTo(vehLen / 2 - 6, vehWid / 3);
        ctx.closePath();
        ctx.fill();

        ctx.restore();

        // Label
        if (options.badges && isAlive) {{
          ctx.fillStyle = '#fff';
          ctx.font = '10px JetBrains Mono';
          ctx.textAlign = 'center';
          ctx.fillText(`V${{e.id + 1}}`, vx, vy - 12);
        }}
      }});
    }}

    window.onload = init;
  </script>
</body>
</html>
"""


def main() -> None:
    print("Building Unified Convoy Mission Viewer (v2)...")
    payload = generate_payload()

    out_json = VIZ_DIR / "mission_viewer_v2_data.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Generated telemetry data: {out_json} ({out_json.stat().st_size // 1024} KB)")

    html_content = generate_html(payload)
    out_html = VIZ_DIR / "mission_viewer_v2.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated standalone console: {out_html} ({out_html.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
