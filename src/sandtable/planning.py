"""Target assignment and formation keeping (mission-scale planning).

Minimal, vectorized policy sufficient for the target scenarios:
  - Blue GROUND vehicles steer toward the objective along a lateral lane chosen by the `route_bias`
    design parameter (0 = fast exposed corridor, 1 = slow covered route), converging onto the
    objective as they close the distance (pure-pursuit carrot).
  - Blue AIR (UAS) loiter at dispersed overwatch stations providing sensor coverage of the contested
    band (more UAS => more coverage); they do not advance to the ground objective.
  - Red defenders are static (hold position).

This is the seam where the full planner (Dijkstra least-time path over the mobility raster, richer
formations, UAS search patterns) will slot in; the interface (`step` mutates `ent.tgt_x/tgt_y` in
place) stays fixed.
"""
from __future__ import annotations

import numpy as np

from sandtable.entities import AIR, BLUE, Entities
from sandtable.scenario import Scenario
from sandtable.world import World


def overwatch_stations(n: int, cx: float, cy: float, r: float,
                       size: tuple[float, float], aspect: float = 1.0) -> np.ndarray:
    """`n` UAS loiter stations tiling the contested band, center-first (priority ordered).

    Stations sit on a lattice (spacing ~1.5*sensor_range so footprints tile with mild overlap)
    centered on the threat centroid (cx, cy), taken in increasing *anisotropic* distance from the
    centroid. `aspect` penalizes lateral (y) offsets: with aspect>1 the swarm first spreads ALONG
    the assault/threat axis (x) before adding lateral rings, matching a threat laydown that runs in
    depth along x (e.g. a defense in depth). aspect=1 recovers the isotropic square lattice.

    Because the first k stations are identical for any n >= k, adding a UAS never removes coverage:
    detection coverage is monotone non-decreasing in n, with diminishing returns as the line fills
    and outer stations fall on sparser parts of the laydown. Returns an (n, 2) array clipped to the
    field.
    """
    if n <= 0:
        return np.zeros((0, 2))
    step_m = 1.5 * max(r, 1.0)
    mx = 2 * n + 1                                        # enough columns to lay all n along x
    my = 2 * int(np.ceil(np.sqrt(n))) + 1                # odd -> the centroid itself is a station
    ox = (np.arange(mx) - (mx - 1) / 2) * step_m
    oy = (np.arange(my) - (my - 1) / 2) * step_m
    gx, gy = np.meshgrid(ox, oy)
    cand = np.column_stack([cx + gx.ravel(), cy + gy.ravel()])
    d = np.hypot(cand[:, 0] - cx, max(aspect, 1e-6) * (cand[:, 1] - cy))
    order = np.argsort(d, kind="stable")
    cand = cand[order][:n].astype(float)
    cand[:, 0] = np.clip(cand[:, 0], 0.05 * size[0], 0.95 * size[0])
    cand[:, 1] = np.clip(cand[:, 1], 0.05 * size[1], 0.95 * size[1])
    return cand


def step(ent: Entities, world: World, scn: Scenario, spawn_x: float) -> None:
    """Set each entity's movement target in place."""
    gx, gy = scn.objective.goal
    bias = float(np.clip(scn.params.get("route_bias", 0.0), 0.0, 1.0))
    spread = float(scn.params.get("formation_spread", 30.0))
    lane_y = (1.0 - bias) * world.corridor_y + bias * world.covered_y

    blue = ent.side == BLUE

    # Every blue GROUND vehicle navigates independently toward the objective along the chosen lane,
    # robust to any vehicle's loss (no dead-leader dependency). It HOLDS the lane through the threat
    # and converges onto the objective only over the last stretch, so a covered route stays in
    # defilade past the defenders instead of being dragged through the exposed zone.
    look = float(scn.params.get("lookahead", 400.0))
    x_conv = gx - float(scn.params.get("converge_dist", 900.0))
    c = np.clip((ent.x - x_conv) / max(gx - x_conv, 1.0), 0.0, 1.0)   # 0 on the lane, 1 at goal
    ty = lane_y + (gy - lane_y) * c                    # lane y (converges onto the goal near the end)
    tx = np.minimum(ent.x + look, gx)                  # carrot ahead: climb onto the lane fast, then follow

    tx_new = np.where(blue, tx, ent.tgt_x)
    ty_new = np.where(blue, ty, ent.tgt_y)

    # Air (UAS) blue loiter at dispersed overwatch stations instead of advancing to the objective:
    # more UAS spread across the contested band => more sensor coverage. Ground-core scenarios have
    # no air entities, so this branch never fires for them.
    air_idx = np.nonzero(blue & (ent.domain == AIR))[0]
    if air_idx.size > 0:
        h = world.size[1]
        cx = float(scn.params.get("overwatch_x", gx * 0.6))
        cy = float(scn.params.get("overwatch_y", h * 0.5))
        r = float(np.mean(ent.sensor_range[air_idx])) if air_idx.size else 500.0
        aspect = float(scn.params.get("overwatch_aspect", 1.0))
        st = overwatch_stations(air_idx.size, cx, cy, r, world.size, aspect=aspect)
        tx_new[air_idx] = st[:, 0]
        ty_new[air_idx] = st[:, 1]

    # Blue GROUND that have reached the objective hold there (so arrivals accumulate). Air stations
    # are far from the goal, so UAS are unaffected by this.
    dist_goal = np.hypot(ent.x - gx, ent.y - gy)
    at_goal = blue & (ent.domain != AIR) & (dist_goal <= scn.objective.goal_radius)
    tx_new = np.where(at_goal, ent.x, tx_new)
    ty_new = np.where(at_goal, ent.y, ty_new)

    # Red defenders hold position.
    red = ~blue
    tx_new = np.where(red, ent.x, tx_new)
    ty_new = np.where(red, ent.y, ty_new)

    ent.tgt_x, ent.tgt_y = tx_new, ty_new
    _ = spread  # reserved for the richer formation model
