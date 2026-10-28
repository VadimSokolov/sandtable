"""Replay recorder: run a mission and capture a compact per-step trace for visualization.

`record_trace` runs the SAME fixed-timestep loop as `sandtable.sim.run_mission` (identical step order and
RNG, so the trace faithfully reflects the simulated behavior) but snapshots entity positions and
detection state every `stride` steps, plus the static terrain rasters and force metadata. The result
is a small JSON-serializable dict that the web viewer (`tools/make_viz.py` -> a self-contained HTML
page) animates. This is the telemetry/replay-store seam from the TDD; it does not touch the hot-path
`run_mission` used inside the optimizer.
"""
from __future__ import annotations

import numpy as np

from sandtable import behavior, c2, engagement, metrics, motion, personality, planning, sensing
from sandtable.comms_ew import build_comms
from sandtable.entities import BLUE, GROUND, RED
from sandtable.scenario import Scenario, build_entities
from sandtable.seeding import make_rng
from sandtable.world import build_world


def _downsample(field: np.ndarray, nx: int = 80, ny: int = 40) -> list:
    """Coarsen a terrain raster to at most (ny, nx) for a light background image."""
    sy = max(1, field.shape[0] // ny)
    sx = max(1, field.shape[1] // nx)
    coarse = field[::sy, ::sx]
    return [[round(float(v), 3) for v in row] for row in coarse]


def record_trace(scenario: Scenario, seed: int = 0, params: dict | None = None,
                 stride: int = 10) -> dict:
    """Run one mission and return a compact trace dict for the web viewer."""
    scn = scenario.with_params(params) if params else scenario
    rng = make_rng(seed, scn.id)

    world = build_world(scn, rng)
    ent = build_entities(scn, rng)
    comms = build_comms(scn)
    op = c2.build_c2(scn, ent, rng)   # same signature as sim.run_mission, so a
                                  # staggered or mixed-patience fleet replays as it ran
    pers = personality.build_personality(scn)
    bhv = behavior.build_behavior(scn, ent)

    init_counts = {BLUE: int((ent.side == BLUE).sum()), RED: int((ent.side == RED).sum())}
    blue_mask0 = ent.side == BLUE
    spawn_x = float(ent.x[blue_mask0].min()) if blue_mask0.any() else 0.0
    tempo = float(scn.params.get("tempo", 1.0))
    dt = scn.dt
    n_steps = max(int(scn.duration / dt), 1)
    ground_blue0 = int(((ent.side == BLUE) & (ent.domain == GROUND)).sum())
    assault0 = ground_blue0 if ground_blue0 > 0 else init_counts[BLUE]
    need = scn.objective.survive_fraction * assault0

    cargo_total = float(ent.cargo[ent.side_mask(BLUE)].sum()) if ent.cargo is not None else 0.0
    cargo_active = cargo_total > 0.0
    from sandtable.convoy import resolve_crew_table, resolve_delivery_fraction
    req_del_frac = resolve_delivery_fraction(scn)
    req_cargo = float(req_del_frac) * cargo_total if cargo_active else 0.0

    crew_table = resolve_crew_table(scn.params.get("convoy"))
    crew_on = crew_table is not None
    if crew_on:
        crew_risk = np.zeros(4, dtype=np.int64)
        crew_init = np.bincount(ent.convoy_role[ent.side_mask(BLUE)].clip(0), weights=ent.crew[ent.side_mask(BLUE)], minlength=4).astype(np.int64)

    frames: list[dict] = []
    kill_buf: list = []          # (shooter, target) kill pairs since the last snapshot

    def snapshot(t: float) -> None:
        frame_dict = {
            "t": round(float(t), 1),
            "x": [round(float(v), 1) for v in ent.x],
            "y": [round(float(v), 1) for v in ent.y],
            "h": [round(float(v), 2) for v in ent.heading],
            "alive": [int(v) for v in ent.alive],
            "seen": [int(v) for v in ent.seen],
            "cq": [round(float(v), 2) for v in ent.control_quality],
            "kills": [[s, tg] for s, tg in kill_buf],
            "cargo_delivered": [round(float(v), 2) for v in ent.cargo_delivered] if cargo_active else [],
            "crew_alive": [int(v) for v in ent.crew * ent.alive] if crew_on else [],
        }
        if getattr(world, "route", None) is not None and hasattr(ent, "progress"):
            frame_dict["progress"] = [round(float(v), 1) if not np.isnan(v) else None for v in ent.progress]
        frames.append(frame_dict)
        kill_buf.clear()

    snapshot(0.0)
    t = 0.0
    t_reached = None
    cov_sum = 0.0
    cov_steps = 0
    # Mirror sandtable.sim.run_mission step-for-step (identical module order and RNG consumption), so the
    # recorded trajectory is exactly the run the optimizer scored. The only additions are the
    # per-stride snapshots, which draw no randomness.
    for k in range(n_steps):
        if op is not None:
            c2.step(ent, op, comms, scn, k, rng)
        if bhv is not None:
            behavior.step(ent, bhv, op, comms, scn, k, rng, world=world)
        planning.step(ent, world, scn, spawn_x, pers=pers, bhv=bhv)
        motion.step(ent, world, dt, tempo)
        sensing.step(ent, world, rng, comms)
        engagement.step(ent, world, dt, rng, events=kill_buf)
        t = (k + 1) * dt

        red_alive = ent.side_mask(RED)
        n_red = int(red_alive.sum())
        if n_red > 0:
            cov_sum += int((ent.seen & red_alive).sum()) / n_red
            cov_steps += 1

        if (k + 1) % stride == 0:
            snapshot(t)
        if crew_on:
            metrics.accumulate_crew_at_risk(ent, crew_risk)
        if cargo_active:
            at_goal = metrics.blue_at_goal(ent, scn)
            if at_goal.any():
                ent.cargo_delivered[at_goal] = ent.cargo[at_goal]
            c_del = float(ent.cargo_delivered[ent.side == BLUE].sum())
            delivered_target_met = (c_del >= req_cargo) if req_cargo > 0.0 else (at_goal.any() and c_del >= req_cargo)
            if t_reached is None and delivered_target_met:
                t_reached = t
                snapshot(t)
                break
            blue_alive = ent.side_mask(BLUE)
            c_in_transit = float((ent.cargo[blue_alive] - ent.cargo_delivered[blue_alive]).sum())
            if c_in_transit <= 1e-6:
                snapshot(t)
                break
        else:
            if t_reached is None and metrics.blue_at_goal(ent, scn).sum() >= need:
                t_reached = t
                snapshot(t)
                break
        if not ent.side_mask(BLUE).any():
            snapshot(t)
            break

    result = metrics.compute(scn, init_counts, ent, t_reached, t, assault0=assault0)
    if crew_on:
        result.update(metrics.crew_metrics(ent, crew_risk, crew_init, bhv))
    if bhv is not None and getattr(bhv, "contact_action", None):
        result.update(metrics.contact_metrics(bhv, dt))
    result["detection_coverage"] = cov_sum / max(cov_steps, 1)
    gx, gy = scn.objective.goal
    return {
        "name": scn.name,
        "size": [float(scn.size[0]), float(scn.size[1])],
        "dt": dt,
        "stride": stride,
        "params": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in scn.params.items()},
        "objective": {"goal": [float(gx), float(gy)], "radius": float(scn.objective.goal_radius)},
        "terrain": {
            "cover": _downsample(world.cover),
            "conceal": _downsample(world.conceal),
            "buildings": _downsample(world.buildings.astype(float)) if world.buildings is not None else [],
        },
        "building_boxes": world.building_boxes.tolist() if getattr(world, "building_boxes", None) is not None else [],
        "street_graph": world.street_graph.to_dict() if getattr(world, "street_graph", None) is not None else None,
        "route": world.route.waypoints.tolist() if getattr(world, "route", None) is not None else [],
        "entities": [
            {
                "side": int(ent.side[i]),
                "domain": int(ent.domain[i]),
                "crew": int(ent.crew[i]) if hasattr(ent, "crew") and ent.crew is not None else 0,
                "sensor_range": float(ent.sensor_range[i]),
                "weapon_range": float(ent.weapon_range[i]),
                "convoy_role": int(ent.convoy_role[i]) if hasattr(ent, "convoy_role") and ent.convoy_role is not None else -1,
                "march_unit": int(ent.march_unit[i]) if hasattr(ent, "march_unit") and ent.march_unit is not None else -1,
                "serial": int(ent.serial[i]) if hasattr(ent, "serial") and ent.serial is not None else -1,
                "section": int(ent.section[i]) if hasattr(ent, "section") and ent.section is not None else -1,
                "cargo": float(ent.cargo[i]) if hasattr(ent, "cargo") and ent.cargo is not None else 0.0,
            }
            for i in range(ent.n)
        ],
        "frames": frames,
        "outcome": {
            "success": result["success"],
            "blue_losses": result["blue_losses"],
            "red_losses": result["red_losses"],
            "detection_coverage": round(result["detection_coverage"], 4),
            "mission_time": result["mission_time"],
            **{
                k: (round(v, 2) if isinstance(v, float) else v)
                for k, v in result.items()
                if k.startswith("convoy_") or k.startswith("cargo_") or k.startswith("crew_") or k.startswith("autonomous_") or k in ("delivered_frac", "time_to_delivery")
            },
        },
    }
