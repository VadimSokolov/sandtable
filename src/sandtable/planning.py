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
        ox = float(scn.params.get("overwatch_x", gx * 0.6))
        h = world.size[1]
        ys = np.linspace(h * 0.15, h * 0.85, air_idx.size) if air_idx.size > 1 else np.array([h * 0.5])
        tx_new[air_idx] = ox
        ty_new[air_idx] = ys

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
