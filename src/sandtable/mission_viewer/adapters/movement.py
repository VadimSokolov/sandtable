"""Opt-in study adapter, isolated from default engine behavior."""

import numpy as np


class RouteMotionAdapter:
    """Experimental route controller, not vehicle dynamics or runtime pathfinding."""

    def __init__(self, mission, state):
        self.m = mission
        self.state = state
        self.contact = False
        self.anchors = None
        self.park_heading = None
        self.parked = None
        self.rejected = 0
        self.blocked = 0
        self.episodes = 0

    def plan(self, original, ent, world, scn, *args, **kw):
        original(ent, world, scn, *args, **kw)
        bhv = kw.get("bhv")
        self.state.update(ent=ent, world=world, bhv=bhv)
        ids = np.flatnonzero((ent.side == 0) & ent.alive)
        self.parked = np.zeros(ent.n, bool)
        active = self.m["response"] == "herringbone" and bool(bhv.in_contact)
        if active and (not self.contact):
            self.episodes += 1
            self.anchors = np.column_stack([ent.x.copy(), ent.y.copy()])
            self.park_heading = ent.heading.copy()
            s, _ = world.route.project(ent.x[ids], ent.y[ids])
            rx, ry, rh = world.route.point_at(s + self.m["herringbone_offset"])
            sign = np.where(np.arange(len(ids)) % 2, -1, 1)
            off = self.m["herringbone_offset"]
            ax = rx - sign * off * np.sin(rh)
            ay = ry + sign * off * np.cos(rh)
            clear = world.in_bounds(ax, ay) & world.los(ent.x[ids], ent.y[ids], ax, ay)
            iy, ix = world._idx(ax, ay)
            if world.buildings is not None:
                clear &= ~world.buildings[iy, ix]
            self.anchors[ids[clear]] = np.column_stack([ax[clear], ay[clear]])
            self.rejected += int((~clear).sum())
            self.park_heading[ids] = rh + sign * np.pi / 4
        self.contact = active
        if active:
            ids = ids[~self.state.get("leader_hold", np.zeros(ent.n, bool))[ids]]
            ent.tgt_x[ids] = self.anchors[ids, 0]
            ent.tgt_y[ids] = self.anchors[ids, 1]
        else:
            gx, gy = scn.objective.goal
            ids = ids[
                ~bhv.holding[ids]
                & (np.hypot(ent.x[ids] - gx, ent.y[ids] - gy) > scn.objective.goal_radius)
            ]
            if ids.size:
                s, cross = world.route.project(ent.x[ids], ent.y[ids])
                ts, _ = world.route.project(ent.tgt_x[ids], ent.tgt_y[ids])
                returning = cross > 0.08
                rx, ry, _ = world.route.point_at(s[returning])
                ent.tgt_x[ids[returning]] = rx
                ent.tgt_y[ids[returning]] = ry
                for j, i in enumerate(ids):
                    if returning[j]:
                        continue
                    vertices = world.route.cum_dist[world.route.cum_dist > s[j] + 0.05]
                    if len(vertices) and ts[j] > vertices[0]:
                        ent.tgt_x[i], ent.tgt_y[i], _ = world.route.point_at(vertices[0])
                    elif ts[j] <= s[j] + 0.05:
                        ent.tgt_x[i] = ent.x[i]
                        ent.tgt_y[i] = ent.y[i]

    def move(self, original, ent, world, dt, tempo=1):
        ids = np.flatnonzero((ent.side == 0) & ent.alive)
        px = ent.x.copy()
        py = ent.y.copy()
        ph = ent.heading.copy()
        caps = ent.speed_cap.copy()
        d = np.hypot(ent.tgt_x[ids] - ent.x[ids], ent.tgt_y[ids] - ent.y[ids])
        err = (
            np.arctan2(ent.tgt_y[ids] - ent.y[ids], ent.tgt_x[ids] - ent.x[ids]) - ph[ids] + np.pi
        ) % (2 * np.pi) - np.pi
        after = err - np.clip(err, -ent.turn_rate[ids] * dt, ent.turn_rate[ids] * dt)
        cap = np.where(np.abs(after) > 0.001, 0, np.minimum(ent.max_speed[ids], d / (2 * dt)))
        cap = np.where(d < 0.05, 0, cap)
        ent.speed_cap[ids] = np.minimum(caps[ids], cap)
        try:
            original(ent, world, dt, tempo)
        finally:
            ent.speed_cap[:] = caps
        clear = world.in_bounds(ent.x[ids], ent.y[ids]) & world.los(
            px[ids], py[ids], ent.x[ids], ent.y[ids]
        )
        iy, ix = world._idx(ent.x[ids], ent.y[ids])
        if world.buildings is not None:
            clear &= ~world.buildings[iy, ix]
        bad = ids[~clear]
        ent.x[bad] = px[bad]
        ent.y[bad] = py[bad]
        ent.speed[bad] = 0
        self.blocked += len(bad)
        constraint = np.zeros(ent.n, bool)
        constraint[bad] = True
        self.state["constraint"] = constraint
        reasons = ["destroyed" if not alive else "static_red" for alive in ent.alive]
        b = self.state["bhv"]
        gx, gy = self.state["world"].route.waypoints[-1]
        for j, i in enumerate(ids):
            if constraint[i]:
                reason = "building_or_boundary_constraint"
            elif self.state.get("leader_hold", np.zeros(ent.n, bool))[i]:
                reason = "leader_loss_halt"
            elif ent.speed[i] > 0.001:
                reason = "herringbone_maneuver" if self.contact else "moving"
            elif (
                self.contact
                and self.anchors is not None
                and (np.hypot(ent.x[i] - self.anchors[i, 0], ent.y[i] - self.anchors[i, 1]) < 0.05)
            ):
                reason = "herringbone_parked"
            elif b.holding[i]:
                reason = (
                    "contact_halt"
                    if b.in_contact and self.m["response"] != "continue"
                    else "tracking_or_behavior_hold"
                )
            elif np.hypot(ent.x[i] - gx, ent.y[i] - gy) <= self.state.get("goal_radius", 0):
                reason = "at_goal"
            elif abs(after[j]) > 0.001:
                reason = "aligning_to_route"
            else:
                reason = "waiting_at_station"
            reasons[i] = reason
        self.state["motion_reason"] = reasons
        if self.contact:
            at = ids[
                np.hypot(ent.x[ids] - self.anchors[ids, 0], ent.y[ids] - self.anchors[ids, 1])
                < 0.05
            ]
            delta = (self.park_heading[at] - ph[at] + np.pi) % (2 * np.pi) - np.pi
            ent.heading[at] = ph[at] + np.clip(
                delta, -ent.turn_rate[at] * dt, ent.turn_rate[at] * dt
            )
            self.parked[at] = True
