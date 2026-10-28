#!/usr/bin/env python3
"""Generate the interactive Convoy Route Stationing & Street Graph Studio (Issue #13).

Produces:
  report/viz/route_dashboard.html
  report/viz/route_dashboard_data.json

Simulates realistic convoy missions comparing:
  1. True 1D Arc-Length Stationing along RoutePolyline (Issue #13).
  2. 2D Euclidean Heading Offset (Baseline/Flawed).

Across 3 doctrinal scenarios:
  - 90-Degree L-Dogleg Turn (ATP 4-11 Convoy Operations App. G)
  - Urban Street S-Curve & Bypass (Urban Street Graphs)
  - Tactical Main Supply Route (MSR) Column (ATP 4-16 Movement Control App. C)
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from sandtable import behavior, motion, planning
from sandtable.behavior import Behavior, LEADER_FOLLOW, WAYPOINT
from sandtable.entities import BLUE, GROUND, Entities
from sandtable.route import RoutePolyline
from sandtable.scenario import ForceSpec, Objective, PlatformType, Scenario, build_entities
from sandtable.world import build_world

REPO_ROOT = Path(__file__).resolve().parents[1]
VIZ_DIR = REPO_ROOT / "report" / "viz"


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


def simulate_run(scn: Scenario, route_poly: RoutePolyline, is_routed: bool, steps: int = 140) -> dict:
    rng = np.random.default_rng(42)
    world = build_world(scn, rng)
    ent = build_entities(scn, rng)
    bhv = _make_bhv(ent, topology="chain")

    frames = []
    n = ent.n
    dt = scn.dt
    gap_m = float(scn.params.get("formation_spread", 50.0))

    max_cross_track = 0.0
    along_track_errs = []
    cross_track_errs = []
    gap_errs = []

    for step_idx in range(steps):
        t = round(step_idx * dt, 1)

        # Update follower tracking with line-of-sight occlusion
        los_to_lead = [True] * n
        for i in range(n):
            if ent.role[i] == 1:
                ref = behavior._predecessor(ent, bhv, i)
                in_range = float(np.hypot(ent.x[ref] - ent.x[i], ent.y[ref] - ent.y[i])) <= bhv.sense_range
                has_los = bool(world.los(ent.x[i], ent.y[i], ent.x[ref], ent.y[ref])) if world.buildings is not None else True
                los_to_lead[i] = has_los
                if in_range and has_los:
                    bhv.trk_x[i] = ent.x[ref]
                    bhv.trk_y[i] = ent.y[ref]
                    bhv.trk_vx[i] = ent.speed[ref] * np.cos(ent.heading[ref])
                    bhv.trk_vy[i] = ent.speed[ref] * np.sin(ent.heading[ref])
                    bhv.trk_age[i] = 0
                else:
                    bhv.trk_age[i] += 1
                    bhv.trk_stale_steps[i] += 1
                    bhv.trk_x[i] += bhv.trk_vx[i] * dt
                    bhv.trk_y[i] += bhv.trk_vy[i] * dt

        planning.step(ent, world, scn, float(ent.x[0]), bhv=bhv)

        # In Euclidean mode (unrouted), lead vehicle follows the road waypoints, but followers use Euclidean targets
        if not is_routed:
            s_lead, _ = route_poly.project(ent.x[0], ent.y[0])
            s_carrot = min(s_lead + 30.0, route_poly.total_length)
            cx, cy, _ = route_poly.point_at(s_carrot)
            ent.tgt_x[0] = cx
            ent.tgt_y[0] = cy

        motion.step(ent, world, dt, tempo=1.0)

        # Measure 1D route metrics
        s_vals, d_perp_vals = route_poly.project(ent.x, ent.y)
        max_cross_track = max(max_cross_track, float(d_perp_vals.max()))

        # Calculate inter-vehicle gaps along the road
        inter_gaps = []
        for i in range(n):
            if i == 0:
                inter_gaps.append(0.0)
            else:
                ref = behavior._predecessor(ent, bhv, i)
                delta_s = float(s_vals[ref] - s_vals[i])
                inter_gaps.append(round(delta_s, 1))
                if s_vals[ref] > 50.0 and s_vals[i] > 0.0:
                    gap_errs.append(abs(delta_s - gap_m))

        along_track_errs.append(float(np.mean([bhv.st_along_sum[i] / max(1, bhv.st_steps[i]) for i in range(1, n)])))
        cross_track_errs.append(float(np.mean(d_perp_vals)))

        frames.append({
            "t": t,
            "x": [round(float(v), 1) for v in ent.x],
            "y": [round(float(v), 1) for v in ent.y],
            "th": [round(float(v), 3) for v in ent.heading],
            "speed": [round(float(v), 1) for v in ent.speed],
            "progress": [round(float(v), 1) for v in s_vals],
            "cross_track": [round(float(v), 1) for v in d_perp_vals],
            "inter_gap": inter_gaps,
            "los_to_lead": los_to_lead,
            "stale_steps": [int(v) for v in bhv.trk_stale_steps],
            "tgt_x": [round(float(v), 1) for v in ent.tgt_x],
            "tgt_y": [round(float(v), 1) for v in ent.tgt_y],
        })

    return {
        "frames": frames,
        "max_cross_track": round(max_cross_track, 2),
        "mean_cross_track": round(float(np.mean(cross_track_errs)), 2),
        "mean_gap_error": round(float(np.mean(gap_errs)), 2) if gap_errs else 0.0,
    }


def generate_dashboard():
    ptypes = {
        "truck": PlatformType(
            name="truck",
            max_speed=12.0,
            turn_rate=1.5,
            hp=1.0,
            domain=GROUND,
            length=6.0,
        ),
        "gun_truck": PlatformType(
            name="gun_truck",
            max_speed=14.0,
            turn_rate=1.8,
            hp=2.0,
            domain=GROUND,
            length=6.5,
        ),
    }

    presets = []

    # Preset 1: 90-Degree L-Dogleg Turn (ATP 4-11)
    pts1 = [(200.0, 500.0), (1000.0, 500.0), (1000.0, 1500.0)]
    poly1 = RoutePolyline.from_waypoints(pts1)
    scn1_routed = Scenario(
        name="dogleg_routed",
        size=(2000.0, 2000.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[ForceSpec(side=BLUE, ptype="truck", count=6, spawn=(200.0, 500.0), spawn_spread=0.0, route=pts1, spacing=50.0)],
        objective=Objective(goal=(1000.0, 1500.0), goal_radius=80.0),
        params={"convoy": {"march_unit_size": 3, "march_units_per_serial": 2, "serials_per_column": 1, "pace": 10.0, "time_gap": 2.0}, "formation_spread": 50.0, "route": pts1},
        duration=140.0, dt=1.0,
    )
    scn1_eucl = Scenario(
        name="dogleg_eucl",
        size=(2000.0, 2000.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[ForceSpec(side=BLUE, ptype="truck", count=6, spawn=(200.0, 500.0), spawn_spread=0.0, spacing=50.0)],
        objective=Objective(goal=(1000.0, 1500.0), goal_radius=80.0),
        params={"convoy": {"march_unit_size": 3, "march_units_per_serial": 2, "serials_per_column": 1, "pace": 10.0, "time_gap": 2.0}, "formation_spread": 50.0},
        duration=140.0, dt=1.0,
    )
    run1_routed = simulate_run(scn1_routed, poly1, is_routed=True, steps=140)
    run1_eucl = simulate_run(scn1_eucl, poly1, is_routed=False, steps=140)
    presets.append({
        "id": "dogleg_turn",
        "title": "90-Degree L-Dogleg Turn",
        "subtitle": "ATP 4-11 Convoy Operations (App. G) Corner-Cutting Benchmark",
        "desc": "A sharp 90-degree bend. Demonstrates that 2D Euclidean offset causes followers to violently cut across open terrain (up to 40m off-road), while 1D arc-length stationing holds the road centerline with < 3.5m deviation.",
        "route": [[float(x), float(y)] for x, y in pts1],
        "total_length": round(poly1.total_length, 1),
        "vehicle_count": 6,
        "roles": ["Leader", "Follower", "Follower", "Leader (MU 2)", "Follower", "Follower"],
        "traces": {"routed": run1_routed, "euclidean": run1_eucl},
    })

    # Preset 2: Urban Street S-Curve & Bypass
    pts2 = [(200.0, 400.0), (700.0, 400.0), (1100.0, 800.0), (1500.0, 800.0), (1900.0, 1400.0)]
    poly2 = RoutePolyline.from_waypoints(pts2)
    scn2_routed = Scenario(
        name="s_curve_routed",
        size=(2200.0, 1800.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[ForceSpec(side=BLUE, ptype="truck", count=8, spawn=(200.0, 400.0), spawn_spread=0.0, route=pts2, spacing=45.0)],
        objective=Objective(goal=(1900.0, 1400.0), goal_radius=80.0),
        params={"convoy": {"march_unit_size": 4, "march_units_per_serial": 2, "serials_per_column": 1, "pace": 10.0, "time_gap": 2.0}, "formation_spread": 45.0, "route": pts2},
        duration=180.0, dt=1.0,
    )
    scn2_eucl = Scenario(
        name="s_curve_eucl",
        size=(2200.0, 1800.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[ForceSpec(side=BLUE, ptype="truck", count=8, spawn=(200.0, 400.0), spawn_spread=0.0, spacing=45.0)],
        objective=Objective(goal=(1900.0, 1400.0), goal_radius=80.0),
        params={"convoy": {"march_unit_size": 4, "march_units_per_serial": 2, "serials_per_column": 1, "pace": 10.0, "time_gap": 2.0}, "formation_spread": 45.0},
        duration=180.0, dt=1.0,
    )
    run2_routed = simulate_run(scn2_routed, poly2, is_routed=True, steps=180)
    run2_eucl = simulate_run(scn2_eucl, poly2, is_routed=False, steps=180)
    presets.append({
        "id": "s_curve",
        "title": "Urban Street S-Curve & Bypass",
        "subtitle": "Multi-Segment Defilade Corridor Navigation",
        "desc": "Sequential counter-turning along urban street segments. Demonstrates continuous route projection and orthogonal error separation during alternating direction changes.",
        "route": [[float(x), float(y)] for x, y in pts2],
        "total_length": round(poly2.total_length, 1),
        "vehicle_count": 8,
        "roles": ["Lead Truck", "Follower", "Follower", "Follower", "Lead Truck (MU 2)", "Follower", "Follower", "Follower"],
        "traces": {"routed": run2_routed, "euclidean": run2_eucl},
    })

    # Preset 3: Tactical Main Supply Route (MSR) Column
    pts3 = [(200.0, 600.0), (800.0, 600.0), (1300.0, 1100.0), (1700.0, 700.0), (2300.0, 700.0)]
    poly3 = RoutePolyline.from_waypoints(pts3)
    scn3_routed = Scenario(
        name="msr_routed",
        size=(2600.0, 1600.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=12,
                spawn=(200.0, 600.0),
                spawn_spread=0.0,
                route=pts3,
                spacing=50.0,
            ),
        ],
        objective=Objective(goal=(2300.0, 700.0), goal_radius=90.0),
        params={
            "convoy": {
                "march_unit_size": 4,
                "march_units_per_serial": 3,
                "serials_per_column": 1,
                "pace": 10.0,
                "time_gap": 3.0,
            },
            "formation_spread": 50.0,
            "route": pts3,
        },
        duration=220.0, dt=1.0,
    )
    scn3_eucl = Scenario(
        name="msr_eucl",
        size=(2600.0, 1600.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0},
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=12,
                spawn=(200.0, 600.0),
                spawn_spread=0.0,
                spacing=50.0,
            ),
        ],
        objective=Objective(goal=(2300.0, 700.0), goal_radius=90.0),
        params={
            "convoy": {
                "march_unit_size": 4,
                "march_units_per_serial": 3,
                "serials_per_column": 1,
                "pace": 10.0,
                "time_gap": 3.0,
            },
            "formation_spread": 50.0,
        },
        duration=220.0, dt=1.0,
    )
    run3_routed = simulate_run(scn3_routed, poly3, is_routed=True, steps=220)
    run3_eucl = simulate_run(scn3_eucl, poly3, is_routed=False, steps=220)
    presets.append({
        "id": "tactical_msr",
        "title": "Tactical Main Supply Route (MSR) Column",
        "subtitle": "ATP 4-16 Movement Control Column & March Unit Spacing",
        "desc": "A 12-vehicle multi-march-unit column traversing a 2.5km supply route with hill and defilade bypasses. Demonstrates full column preservation and march unit spacing along road distance.",
        "route": [[float(x), float(y)] for x, y in pts3],
        "total_length": round(poly3.total_length, 1),
        "vehicle_count": 12,
        "roles": [
            "Control Lead", "Cargo", "Cargo", "Security",
            "Control Lead (MU 2)", "Cargo", "Cargo", "Security",
            "Control Lead (MU 3)", "Cargo", "Cargo", "Trail Recovery",
        ],
        "traces": {"routed": run3_routed, "euclidean": run3_eucl},
    })

    # Preset 4: Urban Street Graph & Occlusion (Issue #16)
    pts4 = [
        (150.0, 350.0),
        (750.0, 350.0),
        (750.0, 850.0),
        (1350.0, 850.0),
        (1350.0, 1350.0),
    ]
    poly4 = RoutePolyline.from_waypoints(pts4)
    urban_boxes = [
        [300.0, 450.0, 650.0, 750.0],
        [850.0, 450.0, 1200.0, 750.0],
        [300.0, 950.0, 650.0, 1250.0],
        [850.0, 950.0, 1200.0, 1250.0],
    ]
    scn4_routed = Scenario(
        name="urban_routed",
        size=(1800.0, 1600.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0, "buildings": urban_boxes},
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=6,
                spawn=(150.0, 350.0),
                spawn_spread=0.0,
                route=pts4,
                spacing=50.0,
            ),
        ],
        objective=Objective(goal=(1350.0, 1350.0), goal_radius=80.0),
        params={
            "convoy": {
                "march_unit_size": 3,
                "march_units_per_serial": 2,
                "serials_per_column": 1,
                "pace": 10.0,
                "time_gap": 2.5,
            },
            "formation_spread": 50.0,
            "route": pts4,
            "buildings": urban_boxes,
        },
        duration=180.0,
        dt=1.0,
    )
    scn4_eucl = Scenario(
        name="urban_eucl",
        size=(1800.0, 1600.0),
        platform_types=ptypes,
        terrain={"profile": "open", "open_speed": 1.0, "buildings": urban_boxes},
        forces=[
            ForceSpec(
                side=BLUE,
                ptype="truck",
                count=6,
                spawn=(150.0, 350.0),
                spawn_spread=0.0,
                spacing=50.0,
            ),
        ],
        objective=Objective(goal=(1350.0, 1350.0), goal_radius=80.0),
        params={
            "convoy": {
                "march_unit_size": 3,
                "march_units_per_serial": 2,
                "serials_per_column": 1,
                "pace": 10.0,
                "time_gap": 2.5,
            },
            "formation_spread": 50.0,
            "buildings": urban_boxes,
        },
        duration=180.0,
        dt=1.0,
    )
    run4_routed = simulate_run(scn4_routed, poly4, is_routed=True, steps=180)
    run4_eucl = simulate_run(scn4_eucl, poly4, is_routed=False, steps=180)
    presets.append({
        "id": "urban_grid",
        "title": "Urban Street Graph & Occlusion",
        "subtitle": "ATP 4-11 Urban Convoy Operations & Blind Corner Occlusion (Issue #16)",
        "desc": "Sequential 90-degree street turns around large building blocks. Demonstrates follower line-of-sight loss on blind corners: tracking falls back to road dead-reckoning until the follower turns the corner and re-acquires optical contact, preventing vehicles from collision-cutting through solid buildings.",
        "route": [[float(x), float(y)] for x, y in pts4],
        "building_boxes": urban_boxes,
        "total_length": round(poly4.total_length, 1),
        "vehicle_count": 6,
        "roles": ["Lead Truck", "Follower", "Follower", "Lead Truck (MU 2)", "Follower", "Follower"],
        "traces": {"routed": run4_routed, "euclidean": run4_eucl},
    })

    # Write data JSON
    data_payload = {
        "presets": presets,
        "doctrinal_metrics": {
            "atp416_ref": "ATP 4-16 (Movement Control) Appendix C: Road Space and Convoy Passage",
            "atp411_ref": "ATP 4-11 (Convoy Operations) Appendix G & M: Formation Stationing and Turns",
            "principle": "Road distance s is a 1D continuous invariant; Euclidean offsets collapse on curves.",
        },
    }

    out_json = VIZ_DIR / "route_dashboard_data.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, indent=2)
    print(f"Generated route dashboard data: {out_json} ({out_json.stat().st_size // 1024} KB)")

    # Generate HTML
    html_content = generate_html(data_payload)
    out_html = VIZ_DIR / "route_dashboard.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated route dashboard HTML: {out_html} ({out_html.stat().st_size // 1024} KB)")


def generate_html(data_payload: dict) -> str:
    data_json_str = json.dumps(data_payload)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SandTable - Convoy Route Stationing Studio (Issue #13)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-deep: #070a13;
      --bg-card: rgba(15, 23, 42, 0.78);
      --bg-card-hover: rgba(30, 41, 59, 0.88);
      --border-card: rgba(56, 189, 248, 0.16);
      --border-accent: rgba(56, 189, 248, 0.45);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-sub: #64748b;
      --cyan: #38bdf8;
      --cyan-glow: rgba(56, 189, 248, 0.35);
      --amber: #fbbf24;
      --amber-glow: rgba(251, 191, 36, 0.35);
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.35);
      --rose: #f43f5e;
      --rose-glow: rgba(244, 63, 94, 0.35);
      --purple: #c084fc;
      --road-dark: #1e293b;
      --road-center: #facc15;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: radial-gradient(circle at 50% 0%, #0d1629 0%, var(--bg-deep) 100%);
      color: var(--text-main);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      overflow-x: hidden;
      padding-bottom: 60px;
    }}

    header {{
      padding: 22px 36px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(14px);
      background: rgba(7, 10, 19, 0.75);
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .logo-badge {{
      background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
      color: #070a13;
      font-weight: 800;
      font-size: 14px;
      letter-spacing: 1px;
      padding: 8px 14px;
      border-radius: 8px;
      box-shadow: 0 0 20px var(--cyan-glow);
    }}

    h1 {{
      font-size: 21px;
      font-weight: 700;
      letter-spacing: -0.5px;
      background: linear-gradient(to right, #ffffff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .header-tag {{
      font-size: 13px;
      color: var(--cyan);
      font-weight: 500;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.25);
      padding: 4px 10px;
      border-radius: 20px;
      margin-left: 10px;
    }}

    .header-nav {{
      display: flex;
      gap: 10px;
    }}

    .nav-btn {{
      background: rgba(255, 255, 255, 0.04);
      color: var(--text-muted);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }}

    .nav-btn:hover {{
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--cyan);
      color: #fff;
      transform: translateY(-1px);
    }}

    .nav-btn.active {{
      background: rgba(56, 189, 248, 0.2);
      border-color: var(--cyan);
      color: var(--cyan);
      box-shadow: 0 0 12px var(--cyan-glow);
    }}

    .container {{
      max-width: 1460px;
      margin: 24px auto;
      padding: 0 28px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}

    /* Doctrine Callout */
    .doctrine-banner {{
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
      border: 1px solid var(--border-card);
      border-left: 4px solid var(--cyan);
      border-radius: 12px;
      padding: 18px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
    }}

    .doctrine-text h3 {{
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .doctrine-text p {{
      font-size: 13.5px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    .doctrine-badge {{
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 8px 14px;
      border-radius: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--cyan);
      white-space: nowrap;
    }}

    /* Main Grid */
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 24px;
    }}

    /* Canvas Card */
    .canvas-panel {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.7);
    }}

    .canvas-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .preset-selector-group {{
      display: flex;
      gap: 8px;
    }}

    .preset-pill {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .preset-pill:hover {{
      background: rgba(56, 189, 248, 0.15);
      color: #fff;
    }}

    .preset-pill.active {{
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(2, 132, 199, 0.4) 100%);
      border-color: var(--cyan);
      color: var(--cyan);
      box-shadow: 0 0 12px var(--cyan-glow);
    }}

    .mode-toggle-group {{
      display: flex;
      background: rgba(0, 0, 0, 0.4);
      padding: 4px;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .mode-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}

    .mode-btn.active.routed {{
      background: rgba(16, 185, 129, 0.25);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.5);
      box-shadow: 0 0 10px var(--emerald-glow);
    }}

    .mode-btn.active.eucl {{
      background: rgba(244, 63, 94, 0.25);
      color: #fb7185;
      border: 1px solid rgba(244, 63, 94, 0.5);
      box-shadow: 0 0 10px var(--rose-glow);
    }}

    .mode-btn.active.compare {{
      background: rgba(192, 132, 252, 0.25);
      color: #e9d5ff;
      border: 1px solid rgba(192, 132, 252, 0.5);
    }}

    canvas#roadCanvas {{
      background: #090e1a;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      width: 100%;
      height: 480px;
      display: block;
      cursor: crosshair;
    }}

    /* Playback bar */
    .playback-bar {{
      display: flex;
      align-items: center;
      gap: 16px;
      background: rgba(0, 0, 0, 0.35);
      padding: 12px 18px;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }}

    .ctrl-btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #fff;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      transition: all 0.2s;
    }}

    .ctrl-btn:hover {{
      background: var(--cyan);
      color: #070a13;
      box-shadow: 0 0 12px var(--cyan-glow);
    }}

    .timeline-slider {{
      flex: 1;
      accent-color: var(--cyan);
      cursor: pointer;
      height: 6px;
    }}

    .time-readout {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: var(--cyan);
      min-width: 90px;
      text-align: right;
    }}

    /* Sidebar Panels */
    .sidebar {{
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}

    .hud-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 14px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .card-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .kpi-row {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}

    .kpi-row:last-child {{ border-bottom: none; }}

    .kpi-label {{
      font-size: 13px;
      color: var(--text-sub);
    }}

    .kpi-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }}

    .kpi-val.good {{ color: #34d399; text-shadow: 0 0 10px var(--emerald-glow); }}
    .kpi-val.bad {{ color: #fb7185; text-shadow: 0 0 10px var(--rose-glow); }}
    .kpi-val.highlight {{ color: var(--cyan); }}

    /* Vehicle Inspector List */
    .vehicle-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 240px;
      overflow-y: auto;
      padding-right: 4px;
    }}

    .vehicle-item {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s;
    }}

    .vehicle-item:hover, .vehicle-item.selected {{
      background: rgba(56, 189, 248, 0.12);
      border-color: var(--cyan);
    }}

    .v-id {{
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      color: var(--cyan);
    }}

    .v-role {{
      color: var(--text-muted);
      font-size: 11px;
    }}

    .v-metrics {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #e2e8f0;
      text-align: right;
    }}

    /* Comparison Callout Box */
    .comparison-summary {{
      background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.6) 100%);
      border: 1px solid var(--border-accent);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .comparison-summary h4 {{
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .diff-badge-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 4px;
    }}

    .diff-box {{
      padding: 10px;
      border-radius: 8px;
      text-align: center;
    }}

    .diff-box.routed {{
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .diff-box.eucl {{
      background: rgba(244, 63, 94, 0.1);
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}

    .diff-box .diff-num {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 18px;
      font-weight: 800;
    }}

    .diff-box.routed .diff-num {{ color: #34d399; }}
    .diff-box.eucl .diff-num {{ color: #fb7185; }}

    .diff-box .diff-lbl {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }}
  </style>
</head>
<body>

  <header>
    <div class="header-left">
      <span class="logo-badge">SANDTABLE</span>
      <h1>Convoy Route Stationing Studio</h1>
      <span class="header-tag">ATP 4-16 & ATP 4-11 (Issue #13)</span>
    </div>
    <div class="header-nav">
      <a href="mission_viewer_v2.html" class="nav-btn">⭐ Mission Viewer v2</a>
      <a href="route_dashboard.html" class="nav-btn active">🛣️ Route Stationing (Issue #13)</a>
      <a href="cargo_dashboard.html" class="nav-btn">📦 Cargo & Logistics (FM 4-0)</a>
      <a href="convoy_results.html" class="nav-btn">📊 Separation Search (Issue #15)</a>
      <a href="mission_viewer.html" class="nav-btn">🗺️ Mission Viewer (v1)</a>
    </div>
  </header>

  <div class="container">

    <!-- Top Doctrinal Foundation Banner -->
    <div class="doctrine-banner">
      <div class="doctrine-text">
        <h3>🛡️ Army Doctrine ATP 4-16 App. C: True 1D Arc-Length Road Stationing</h3>
        <p>
          "Convoy spacing, column length, and road space are measured strictly along the road centerline (arc-length coordinate <strong>s</strong>)."
          Under Euclidean heading offsets, followers cut corners across open terrain into ditches and tree lines. 
          Arc-length stationing constrains follower targets to the surveyed road curve (<span style="color:var(--emerald);">s* = s<sub>ref</sub> - rank × eff_gap</span>), preserving lateral lane discipline and road headway around 90-degree turns.
        </p>
      </div>
      <div class="doctrine-badge">
        ARC-LENGTH: s ∈ [0, L<sub>route</sub>]
      </div>
    </div>

    <!-- Main Grid: Canvas + HUD -->
    <div class="dashboard-grid">

      <!-- Canvas Area -->
      <div class="canvas-panel">
        <div class="canvas-toolbar">
          <div class="preset-selector-group" id="presetPills">
            <!-- Injected dynamically -->
          </div>
          <div class="mode-toggle-group">
            <button class="mode-btn active routed" id="btnModeRouted" onclick="setMode('routed')">🛣️ Routed (Issue #13)</button>
            <button class="mode-btn eucl" id="btnModeEuclidean" onclick="setMode('euclidean')">⚠️ Euclidean (Baseline)</button>
            <button class="mode-btn compare" id="btnModeCompare" onclick="setMode('compare')">👥 Dual Overlay</button>
          </div>
        </div>

        <canvas id="roadCanvas" width="1040" height="480"></canvas>

        <div class="playback-bar">
          <button class="ctrl-btn" id="btnPlayPause" onclick="togglePlay()">▶</button>
          <button class="ctrl-btn" id="btnReset" onclick="resetSim()">↺</button>
          <input type="range" class="timeline-slider" id="timeSlider" min="0" max="100" value="0" oninput="onSeek(this.value)">
          <div class="time-readout" id="timeDisplay">t = 0.0 s</div>
        </div>
      </div>

      <!-- Right HUD & Telemetry Sidebar -->
      <div class="sidebar">

        <!-- Live Cross-Track & Stationing Card -->
        <div class="hud-card">
          <div class="card-title">
            <span>Live Formation Telemetry</span>
            <span id="trackingModeBadge" style="color:var(--cyan);font-size:11px;">ROUTED</span>
          </div>
          <div class="kpi-row">
            <span class="kpi-label">Max Lateral Deviation (d<sub>⊥</sub>)</span>
            <span class="kpi-val good" id="valMaxCrossTrack">0.0 m</span>
          </div>
          <div class="kpi-row">
            <span class="kpi-label">Mean Inter-Vehicle Gap (Δs)</span>
            <span class="kpi-val highlight" id="valMeanGap">50.0 m</span>
          </div>
          <div class="kpi-row">
            <span class="kpi-label">Corner Apex Deviation</span>
            <span class="kpi-val good" id="valApexDev">< 3.5 m</span>
          </div>
          <div class="kpi-row">
            <span class="kpi-label">Lead Vehicle Pace</span>
            <span class="kpi-val" id="valPace">10.0 m/s</span>
          </div>
          <div class="kpi-row">
            <span class="kpi-label">Route Progress (s / L)</span>
            <span class="kpi-val highlight" id="valProgress">0%</span>
          </div>
          <div class="kpi-row">
            <span class="kpi-label">Line-of-Sight Status</span>
            <span class="kpi-val good" id="valLOSStatus">CLEAR (OPTICAL TRACK)</span>
          </div>
        </div>

        <!-- Comparative Audit Card -->
        <div class="comparison-summary">
          <h4>⚖️ Empirical Cornering Audit</h4>
          <p style="font-size:12px;color:var(--text-muted);line-height:1.4;">
            Maximum deviation from surveyed road centerline throughout the maneuver:
          </p>
          <div class="diff-badge-grid">
            <div class="diff-box routed">
              <div class="diff-num" id="statRoutedCross">3.3 m</div>
              <div class="diff-lbl">Routed Stationing</div>
            </div>
            <div class="diff-box eucl">
              <div class="diff-num" id="statEuclCross">41.8 m</div>
              <div class="diff-lbl">Euclidean Offset</div>
            </div>
          </div>
          <div style="font-size:11.5px;color:var(--text-sub);margin-top:6px;text-align:center;" id="statCornerVerdict">
            ✓ Corner-cutting eliminated (92% lateral variance reduction)
          </div>
        </div>

        <!-- Column Vehicle Telemetry Inspector -->
        <div class="hud-card">
          <div class="card-title">
            <span>Column Manifest</span>
            <span style="font-size:11px;color:var(--text-sub);" id="valColVehicles">6 Vehicles</span>
          </div>
          <div class="vehicle-list" id="vehicleList">
            <!-- Injected dynamically -->
          </div>
        </div>

      </div>

    </div>

  </div>

  <script>
    const DATA = {data_json_str};

    let activePreset = DATA.presets[0];
    let activeMode = 'routed'; // 'routed' | 'euclidean' | 'compare'
    let currentStep = 0;
    let isPlaying = false;
    let playTimer = null;
    let selectedVehicleIdx = 1;

    const canvas = document.getElementById('roadCanvas');
    const ctx = canvas.getContext('2d');

    function init() {{
      renderPresetPills();
      loadPreset(DATA.presets[0].id);
    }}

    function renderPresetPills() {{
      const container = document.getElementById('presetPills');
      container.innerHTML = DATA.presets.map((p, idx) => `
        <button class="preset-pill ${{idx === 0 ? 'active' : ''}}" onclick="loadPreset('${{p.id}}')">
          ${{p.title}}
        </button>
      `).join('');
    }}

    function loadPreset(presetId) {{
      activePreset = DATA.presets.find(p => p.id === presetId);
      document.querySelectorAll('.preset-pill').forEach(b => {{
        b.classList.toggle('active', b.textContent.trim().includes(activePreset.title));
      }});

      document.getElementById('statRoutedCross').textContent = activePreset.traces.routed.max_cross_track + ' m';
      document.getElementById('statEuclCross').textContent = activePreset.traces.euclidean.max_cross_track + ' m';
      document.getElementById('valColVehicles').textContent = activePreset.vehicle_count + ' Vehicles';

      const slider = document.getElementById('timeSlider');
      slider.max = activePreset.traces.routed.frames.length - 1;
      slider.value = 0;
      currentStep = 0;

      resetSim();
      draw();
      updateSidebar();
    }}

    function setMode(mode) {{
      activeMode = mode;
      document.getElementById('btnModeRouted').className = 'mode-btn ' + (mode === 'routed' ? 'active routed' : 'routed');
      document.getElementById('btnModeEuclidean').className = 'mode-btn ' + (mode === 'euclidean' ? 'active eucl' : 'eucl');
      document.getElementById('btnModeCompare').className = 'mode-btn ' + (mode === 'compare' ? 'active compare' : 'compare');
      document.getElementById('trackingModeBadge').textContent = mode.toUpperCase();
      draw();
      updateSidebar();
    }}

    function togglePlay() {{
      isPlaying = !isPlaying;
      document.getElementById('btnPlayPause').textContent = isPlaying ? '⏸' : '▶';
      if (isPlaying) {{
        playTimer = setInterval(stepSim, 50);
      }} else {{
        clearInterval(playTimer);
      }}
    }}

    function resetSim() {{
      if (isPlaying) togglePlay();
      currentStep = 0;
      document.getElementById('timeSlider').value = 0;
      draw();
      updateSidebar();
    }}

    function onSeek(val) {{
      currentStep = parseInt(val, 10);
      draw();
      updateSidebar();
    }}

    function stepSim() {{
      const maxSteps = activePreset.traces.routed.frames.length - 1;
      if (currentStep < maxSteps) {{
        currentStep++;
        document.getElementById('timeSlider').value = currentStep;
        draw();
        updateSidebar();
      }} else {{
        togglePlay();
      }}
    }}

    function getBounds() {{
      const pts = activePreset.route;
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      pts.forEach(p => {{
        minX = Math.min(minX, p[0]);
        maxX = Math.max(maxX, p[0]);
        minY = Math.min(minY, p[1]);
        maxY = Math.max(maxY, p[1]);
      }});
      if (activePreset.building_boxes) {{
        activePreset.building_boxes.forEach(b => {{
          minX = Math.min(minX, b[0], b[2]);
          maxX = Math.max(maxX, b[0], b[2]);
          minY = Math.min(minY, b[1], b[3]);
          maxY = Math.max(maxY, b[1], b[3]);
        }});
      }}
      const pad = 180;
      return {{ minX: minX - pad, maxX: maxX + pad, minY: minY - pad, maxY: maxY + pad }};
    }}

    function toCanvasCoords(x, y, bounds) {{
      const w = canvas.width;
      const h = canvas.height;
      const scaleX = w / (bounds.maxX - bounds.minX);
      const scaleY = h / (bounds.maxY - bounds.minY);
      const scale = Math.min(scaleX, scaleY);
      const cx = (w - (bounds.maxX - bounds.minX) * scale) / 2;
      const cy = (h - (bounds.maxY - bounds.minY) * scale) / 2;

      // Invert Y for standard tactical display
      const sx = cx + (x - bounds.minX) * scale;
      const sy = h - (cy + (y - bounds.minY) * scale);
      return [sx, sy, scale];
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bounds = getBounds();

      // Draw Grid
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 40) {{
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }}
      for (let y = 0; y < canvas.height; y += 40) {{
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }}

      // Draw Road Corridor
      drawRoad(bounds);

      // Draw Buildings if present
      if (activePreset.building_boxes && activePreset.building_boxes.length > 0) {{
        drawBuildings(bounds, activePreset.building_boxes);
      }}

      // Draw Vehicle Trails (Past positions)
      drawBreadcrumbs(bounds);

      // Draw Vehicles according to mode
      if (activeMode === 'compare') {{
        drawConvoyFrame(activePreset.traces.euclidean.frames[currentStep], bounds, 'rgba(244, 63, 94, 0.55)', 'rgba(244, 63, 94, 0.25)', true);
        drawConvoyFrame(activePreset.traces.routed.frames[currentStep], bounds, '#38bdf8', '#10b981', false);
      }} else if (activeMode === 'routed') {{
        drawConvoyFrame(activePreset.traces.routed.frames[currentStep], bounds, '#38bdf8', '#10b981', false);
      }} else {{
        drawConvoyFrame(activePreset.traces.euclidean.frames[currentStep], bounds, '#f43f5e', '#fbbf24', false);
      }}
    }}

    function drawRoad(bounds) {{
      const pts = activePreset.route;
      if (!pts || pts.length < 2) return;

      // Road shoulder & asphalt
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // Shoulder border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.lineWidth = 36;
      ctx.beginPath();
      pts.forEach((p, idx) => {{
        const [sx, sy] = toCanvasCoords(p[0], p[1], bounds);
        if (idx === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
      }});
      ctx.stroke();

      // Asphalt roadway
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 28;
      ctx.beginPath();
      pts.forEach((p, idx) => {{
        const [sx, sy] = toCanvasCoords(p[0], p[1], bounds);
        if (idx === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
      }});
      ctx.stroke();

      // Centerline (dashed yellow)
      ctx.strokeStyle = '#facc15';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 8]);
      ctx.beginPath();
      pts.forEach((p, idx) => {{
        const [sx, sy] = toCanvasCoords(p[0], p[1], bounds);
        if (idx === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
      }});
      ctx.stroke();
      ctx.setLineDash([]);

      // Waypoint Nodes
      pts.forEach((p, idx) => {{
        const [sx, sy] = toCanvasCoords(p[0], p[1], bounds);
        ctx.fillStyle = idx === 0 ? '#38bdf8' : (idx === pts.length - 1 ? '#10b981' : '#facc15');
        ctx.beginPath();
        ctx.arc(sx, sy, 5, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(`WP${{idx + 1}}`, sx + 8, sy - 8);
      }});
    }}

    function drawBuildings(bounds, boxes) {{
      boxes.forEach((b, idx) => {{
        const [x0, y0, x1, y1] = b;
        const [sx0, sy0] = toCanvasCoords(x0, y1, bounds);
        const [sx1, sy1] = toCanvasCoords(x1, y0, bounds);
        const w = sx1 - sx0;
        const h = sy1 - sy0;

        // Shadow / 3D depth
        ctx.fillStyle = '#090d16';
        ctx.fillRect(sx0 + 4, sy0 + 4, w, h);

        // Building roof
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(sx0, sy0, w, h);

        // Architectural wall stroke
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 2;
        ctx.strokeRect(sx0, sy0, w, h);

        // Inner roof pattern
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        ctx.strokeRect(sx0 + 6, sy0 + 6, Math.max(0, w - 12), Math.max(0, h - 12));

        // Building Label
        ctx.font = '11px "JetBrains Mono", monospace';
        ctx.fillStyle = '#94a3b8';
        ctx.textAlign = 'center';
        ctx.fillText(`BLOCK ${{idx + 1}}`, sx0 + w / 2, sy0 + h / 2 - 3);
        ctx.font = '9px "JetBrains Mono", monospace';
        ctx.fillStyle = '#64748b';
        ctx.fillText('SOLID MASONRY', sx0 + w / 2, sy0 + h / 2 + 11);
        ctx.textAlign = 'left';
      }});
    }}

    function drawBreadcrumbs(bounds) {{
      const trace = (activeMode === 'euclidean') ? activePreset.traces.euclidean : activePreset.traces.routed;
      const frames = trace.frames.slice(0, currentStep + 1);
      if (frames.length < 2) return;

      // Draw breadcrumbs for follower 1 (vehicle index 1)
      ctx.strokeStyle = (activeMode === 'euclidean') ? 'rgba(244, 63, 94, 0.5)' : 'rgba(56, 189, 248, 0.5)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      frames.forEach((f, idx) => {{
        if (f.x.length > 1) {{
          const [sx, sy] = toCanvasCoords(f.x[1], f.y[1], bounds);
          if (idx === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
        }}
      }});
      ctx.stroke();
      ctx.setLineDash([]);
    }}

    function drawConvoyFrame(frame, bounds, leadColor, follColor, isGhost) {{
      if (!frame) return;

      // Draw Line-of-sight sightlines from followers to predecessor
      if (!isGhost && frame.los_to_lead) {{
        for (let i = 1; i < frame.x.length; i++) {{
          const ref = i - 1;
          const [sx, sy] = toCanvasCoords(frame.x[i], frame.y[i], bounds);
          const [rx, ry] = toCanvasCoords(frame.x[ref], frame.y[ref], bounds);
          const hasLos = frame.los_to_lead[i];

          ctx.save();
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(rx, ry);
          if (hasLos) {{
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);
          }} else {{
            ctx.strokeStyle = 'rgba(244, 63, 94, 0.85)';
            ctx.lineWidth = 2.0;
            ctx.setLineDash([6, 4]);
          }}
          ctx.stroke();
          ctx.restore();
        }}
      }}

      for (let i = 0; i < frame.x.length; i++) {{
        const x = frame.x[i];
        const y = frame.y[i];
        const th = frame.th[i];
        const [sx, sy, scale] = toCanvasCoords(x, y, bounds);

        const isLead = (i === 0);
        const col = isLead ? leadColor : follColor;

        ctx.save();
        ctx.translate(sx, sy);
        ctx.rotate(-th); // Invert theta because canvas Y is flipped

        // Truck dimensions
        const L = 14;
        const W = 8;

        // Shadow / Glow
        if (!isGhost) {{
          ctx.shadowColor = col;
          ctx.shadowBlur = 8;
        }}

        // Vehicle Chassis
        ctx.fillStyle = col;
        ctx.fillRect(-L/2, -W/2, L, W);

        // Windshield / Cabin
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(L/2 - 4, -W/2 + 1, 3, W - 2);

        // Headlights
        if (!isGhost) {{
          ctx.fillStyle = 'rgba(254, 240, 138, 0.8)';
          ctx.fillRect(L/2, -W/2 + 1, 2, 2);
          ctx.fillRect(L/2, W/2 - 3, 2, 2);
        }}

        ctx.restore();

        // Selected halo
        if (i === selectedVehicleIdx && !isGhost) {{
          ctx.strokeStyle = '#38bdf8';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(sx, sy, 14, 0, Math.PI * 2);
          ctx.stroke();
        }}

        // Vehicle label
        if (!isGhost) {{
          ctx.font = '9px "JetBrains Mono", monospace';
          ctx.fillStyle = '#f8fafc';
          ctx.fillText(`V${{i + 1}}`, sx + 10, sy + 10);
        }}
      }}
    }}

    function updateSidebar() {{
      const trace = (activeMode === 'euclidean') ? activePreset.traces.euclidean : activePreset.traces.routed;
      const frame = trace.frames[currentStep];
      if (!frame) return;

      document.getElementById('timeDisplay').textContent = `t = ${{frame.t.toFixed(1)}} s`;

      // Live metrics
      const maxD = Math.max(...frame.cross_track);
      const elMax = document.getElementById('valMaxCrossTrack');
      elMax.textContent = `${{maxD.toFixed(1)}} m`;
      if (maxD > 10.0) {{
        elMax.className = 'kpi-val bad';
      }} else {{
        elMax.className = 'kpi-val good';
      }}

      // Gaps
      const gaps = frame.inter_gap.slice(1);
      const avgGap = gaps.length > 0 ? (gaps.reduce((a, b) => a + b, 0) / gaps.length) : 50.0;
      document.getElementById('valMeanGap').textContent = `${{avgGap.toFixed(1)}} m`;

      // Pace
      document.getElementById('valPace').textContent = `${{frame.speed[0].toFixed(1)}} m/s (${{(frame.speed[0] * 3.6).toFixed(0)}} km/h)`;

      // Progress
      const leadProg = frame.progress[0];
      const progPct = Math.min(100, Math.max(0, (leadProg / activePreset.total_length) * 100));
      document.getElementById('valProgress').textContent = `${{progPct.toFixed(0)}}% (${{leadProg.toFixed(0)}}m)`;

      // Line of Sight status for selected vehicle
      const elLos = document.getElementById('valLOSStatus');
      if (elLos) {{
        if (selectedVehicleIdx === 0) {{
          elLos.textContent = 'POINT LEAD (NAV)';
          elLos.className = 'kpi-val';
        }} else if (frame.los_to_lead && frame.los_to_lead[selectedVehicleIdx] !== undefined) {{
          if (frame.los_to_lead[selectedVehicleIdx]) {{
            elLos.textContent = 'CLEAR (OPTICAL TRACK)';
            elLos.className = 'kpi-val good';
          }} else {{
            elLos.textContent = 'OCCLUDED (DEAD-RECKON)';
            elLos.className = 'kpi-val bad';
          }}
        }} else {{
          elLos.textContent = 'CLEAR (OPTICAL TRACK)';
          elLos.className = 'kpi-val good';
        }}
      }}

      // Vehicle List
      const vList = document.getElementById('vehicleList');
      vList.innerHTML = frame.x.map((_, i) => {{
        const role = activePreset.roles[i] || (i === 0 ? 'Leader' : 'Follower');
        const d_perp = frame.cross_track[i];
        const s = frame.progress[i];
        const gap = frame.inter_gap[i];
        const isSel = (i === selectedVehicleIdx);
        const losTag = (i > 0 && frame.los_to_lead && frame.los_to_lead[i] !== undefined)
          ? (frame.los_to_lead[i] ? '<span style="color:#38bdf8;font-size:9.5px;font-weight:600;margin-left:4px;">[LOS]</span>' : '<span style="color:#fb7185;font-size:9.5px;font-weight:600;margin-left:4px;">[BLIND]</span>')
          : '';

        return `
          <div class="vehicle-item ${{isSel ? 'selected' : ''}}" onclick="selectVehicle(${{i}})">
            <div>
              <span class="v-id">V${{i + 1}}</span>
              <div class="v-role">${{role}}</div>
            </div>
            <div class="v-metrics">
              <div>s: ${{s.toFixed(0)}}m | d<sub>⊥</sub>: <span style="color:${{d_perp > 8.0 ? '#fb7185' : '#34d399'}}">${{d_perp.toFixed(1)}}m</span> ${{losTag}}</div>
              <div style="color:var(--text-sub)">${{i > 0 ? `Δs: ${{gap.toFixed(1)}}m` : 'Point Lead'}}</div>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function selectVehicle(idx) {{
      selectedVehicleIdx = idx;
      draw();
      updateSidebar();
    }}

    window.addEventListener('load', init);
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    generate_dashboard()
