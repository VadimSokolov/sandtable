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

from sandtable import personality as _personality
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


def step(ent: Entities, world: World, scn: Scenario, spawn_x: float, pers=None, bhv=None) -> None:
    """Set each entity's movement target in place.

    `pers`, if given, replaces the scripted blue-ground lane with the opt-in
    personality-movement propensity sum (byte-identical when None). `bhv`, if given, is the
    behaviour layer: it may hold an agent in place or place it on a follower station, and it is
    applied last so it overrides the lane (byte-identical when None)."""
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

    # Opt-in personality movement: replace the scripted lane for blue GROUND with the weighted
    # propensity sum (goal, enemy repulsion, cover, separation). None on the baseline path.
    if pers is not None:
        res = _personality.aim(ent, world, scn, pers)
        if res is not None:
            p_idx, p_tx, p_ty = res
            tx_new[p_idx] = p_tx
            ty_new[p_idx] = p_ty

    # Behaviour layer (opt-in). A held agent targets its own position, which `motion.step` turns
    # into exactly zero speed via its `v = min(v, dist/dt)` clamp; a follower targets its column
    # station behind the leader it can currently see. None leaves every target untouched.
    if bhv is not None:
        tx_new, ty_new = _behavior_targets(ent, scn, bhv, tx_new, ty_new)

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
    _ = spread  # consumed by the behaviour layer's follower stations; unused on the scripted path


def _behavior_targets(ent: Entities, scn: Scenario, bhv, tx_new, ty_new):
    """Apply behaviour-layer target overrides: follower stations first, then holds."""
    from sandtable import behavior as _behavior

    gap = float(scn.params.get("formation_spread", 30.0))
    # A column closes up at its destination: past the convergence line the follower drops the
    # station and runs the lane in, exactly as the scripted planner already converges. Without this
    # a follower stationed `rank*gap` behind the leader can never reach the objective at all, and
    # the mission is unscoreable rather than merely hard.
    gx = scn.objective.goal[0]
    x_conv = gx - float(scn.params.get("converge_dist", 900.0))
    foll = np.nonzero((bhv.state == _behavior.LEADER_FOLLOW) & ent.alive & (ent.x < x_conv))[0]
    for i in foll:
        # Station `rank * gap` metres behind the lead vehicle along its heading, taken from this
        # follower's own picture of it (live or dead-reckoned per `follow_mode`). Rank comes from
        # the spawn bookkeeping: `leader[i] = i - k` makes every follower reference the group's
        # lead vehicle, so `i - leader[i]` is its place in the column. That star topology is the
        # fielded leader-follower arrangement, and it is what makes the column comms-dependent:
        # every follower needs the same lead vehicle's pose.
        # A chain follower stations one gap behind the vehicle it can see, a star follower
        # `rank` gaps behind the one vehicle whose pose is broadcast. The two describe the same
        # column when nothing is lost, and come apart the moment a track goes stale: a star's
        # error is the LEADER's staleness multiplied by nothing, a chain's is its predecessor's
        # staleness plus its own, which is where string instability enters.
        ref = _behavior._predecessor(ent, bhv, int(i))
        rank = 1 if bhv.topology == "chain" else max(int(i - ent.leader[i]), 1)
        v = np.hypot(bhv.trk_vx[i], bhv.trk_vy[i])
        ux, uy = (bhv.trk_vx[i] / v, bhv.trk_vy[i] / v) if v > 1e-6 else (1.0, 0.0)
        tx_new[i] = bhv.trk_x[i] - rank * gap * ux
        ty_new[i] = bhv.trk_y[i] - rank * gap * uy
        # Station-keeping error against the TRUE pose of the reference, not the tracked one: how
        # far this vehicle is from where the formation wants it, which is the mission-level
        # quantity a path error is a proxy for. Zero when the column is closed up and driving.
        rv = np.hypot(ent.speed[ref] * np.cos(ent.heading[ref]),
                      ent.speed[ref] * np.sin(ent.heading[ref]))
        if rv > 1e-6:
            rux = ent.speed[ref] * np.cos(ent.heading[ref]) / rv
            ruy = ent.speed[ref] * np.sin(ent.heading[ref]) / rv
        else:
            rux, ruy = 1.0, 0.0
        ex = ent.x[i] - (ent.x[ref] - rank * gap * rux)
        ey = ent.y[i] - (ent.y[ref] - rank * gap * ruy)
        bhv.st_err_sum[i] += float(np.hypot(ex, ey))
        # The same error resolved onto the reference's heading and its normal. A vehicle that is
        # merely late is displaced ALONG the column and is still on the route; one that is off to
        # the side has left it. The scalar station error adds the two in quadrature and cannot tell
        # a programme which of them its autonomy stack is producing.
        bhv.st_along_sum[i] += abs(ex * rux + ey * ruy)
        bhv.st_cross_sum[i] += abs(-ex * ruy + ey * rux)
        bhv.st_steps[i] += 1

    held = np.nonzero(bhv.holding)[0]
    tx_new[held] = ent.x[held]
    ty_new[held] = ent.y[held]
    return tx_new, ty_new
