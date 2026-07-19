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

from sandtable import c2, engagement, metrics, motion, planning, sensing
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
    op = c2.build_c2(scn, ent)

    init_counts = {BLUE: int((ent.side == BLUE).sum()), RED: int((ent.side == RED).sum())}
    blue_mask0 = ent.side == BLUE
    spawn_x = float(ent.x[blue_mask0].min()) if blue_mask0.any() else 0.0
    tempo = float(scn.params.get("tempo", 1.0))
    dt = scn.dt
    n_steps = max(int(scn.duration / dt), 1)
    ground_blue0 = int(((ent.side == BLUE) & (ent.domain == GROUND)).sum())
    assault0 = ground_blue0 if ground_blue0 > 0 else init_counts[BLUE]
    need = scn.objective.survive_fraction * assault0

    frames: list[dict] = []

    def snapshot(t: float) -> None:
        frames.append({
            "t": round(float(t), 1),
            "x": [round(float(v), 1) for v in ent.x],
            "y": [round(float(v), 1) for v in ent.y],
            "alive": [int(v) for v in ent.alive],
            "seen": [int(v) for v in ent.seen],
            "cq": [round(float(v), 2) for v in ent.control_quality],
        })

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
        planning.step(ent, world, scn, spawn_x)
        motion.step(ent, world, dt, tempo)
        sensing.step(ent, world, rng, comms)
        engagement.step(ent, world, dt, rng)
        t = (k + 1) * dt

        red_alive = ent.side_mask(RED)
        n_red = int(red_alive.sum())
        if n_red > 0:
            cov_sum += int((ent.seen & red_alive).sum()) / n_red
            cov_steps += 1

        if (k + 1) % stride == 0:
            snapshot(t)
        if t_reached is None and metrics.blue_at_goal(ent, scn).sum() >= need:
            t_reached = t
            snapshot(t)
            break
        if not ent.side_mask(BLUE).any():
            snapshot(t)
            break

    result = metrics.compute(scn, init_counts, ent, t_reached, t, assault0=assault0)
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
        },
        "entities": [
            {
                "side": int(ent.side[i]),
                "domain": int(ent.domain[i]),
                "sensor_range": float(ent.sensor_range[i]),
                "weapon_range": float(ent.weapon_range[i]),
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
        },
    }
