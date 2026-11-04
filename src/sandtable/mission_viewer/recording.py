"""End-of-step recording and entity metadata; no simulation policy decisions."""

import numpy as np


class MissionRecorder:
    def __init__(self, state, m, console, geometry, stride, capture=True):
        self.state = state
        self.m = m
        self.console = console
        self.geometry = geometry
        self.stride = stride
        self.capture = capture
        self.frames = []

    def capture_frame(self, t, force=False):
        if not self.capture or "bhv" not in self.state:
            return
        e = self.state["ent"]
        b = self.state["bhv"]
        con = self.console.snapshot(e)
        blue = e.side == 0
        alive = e.alive
        D = float(e.cargo_delivered[blue].sum())
        X = float((e.cargo[blue & ~alive] - e.cargo_delivered[blue & ~alive]).sum())
        I = float((e.cargo[blue & alive] - e.cargo_delivered[blue & alive]).sum())
        loaded = float(e.cargo[blue].sum())
        assert abs(loaded - D - X - I) < 1e-06, "Cargo invariant failed in recorded frame"
        signature = (
            tuple(alive),
            tuple(b.ll_head),
            bool(b.in_contact),
            tuple(e.leader),
            tuple(con["available"]) if con else (),
        )
        if not force and int(t) % self.stride and (signature == self.state.get("snapshot_status")):
            return
        self.state["snapshot_status"] = signature
        s, cross = self.state["world"].route.project(e.x[blue], e.y[blue])
        leaderhold = self.state.get("leader_hold", np.zeros(e.n, bool))
        contacthold = np.zeros(e.n, bool)
        if b.in_contact and self.m["response"] != "continue":
            contacthold = blue & alive
        constraint = self.state.get("constraint", np.zeros(e.n, bool))
        parked = self.geometry.parked if self.geometry.parked is not None else np.zeros(e.n, bool)
        frame = dict(
            t=float(t),
            motion_reason=self.state.get("motion_reason", ["initial_state"] * e.n),
            tracked_reference_speed=np.hypot(b.trk_vx, b.trk_vy).round(5).tolist(),
            x=e.x.round(4).tolist(),
            y=e.y.round(4).tolist(),
            heading=e.heading.round(5).tolist(),
            speed=e.speed.round(5).tolist(),
            alive=alive.astype(int).tolist(),
            seen=e.seen.astype(int).tolist(),
            quality=e.control_quality.round(6).tolist(),
            leader=e.leader.tolist(),
            unit=e.march_unit.tolist(),
            heads=b.ll_head.tolist(),
            contact=bool(b.in_contact),
            holding=b.holding.astype(int).tolist(),
            leader_hold=leaderhold.astype(int).tolist(),
            contact_hold=contacthold.astype(int).tolist(),
            constraint=constraint.astype(int).tolist(),
            parked=parked.astype(int).tolist(),
            exposure=float(self.state.get("risk", 0)),
            cargo=dict(loaded=loaded, delivered=D, lost=X, in_transit=I),
            crew_alive=int((e.crew[blue] * alive[blue]).sum()),
            crew_lost=int((e.crew[blue] * ~alive[blue]).sum()),
            vehicle_losses=int((blue & ~alive).sum()),
            handoffs=int(b.ll_handoffs),
            leaderless_steps=int(b.leaderless_steps),
            route_s=s.round(4).tolist(),
            cross_track=cross.round(4).tolist(),
            consoles=con,
        )
        if self.frames and self.frames[-1]["t"] == t:
            self.frames[-1] = frame
        else:
            self.frames.append(frame)

    def register_entities(self, e):
        ids = np.flatnonzero(e.side == 0)
        self.state["entities"] = [
            dict(
                id=i,
                label="V" + str(i + 1) if e.side[i] == 0 else "Red " + str(i - len(ids) + 1),
                side=int(e.side[i]),
                role=int(e.convoy_role[i]),
                unit=int(e.march_unit[i]),
                serial=int(e.serial[i]),
                crew=int(e.crew[i]),
                cargo_kg=float(e.cargo[i] * 1000),
                weapon_range=float(e.weapon_range[i]),
                sensor_range=float(e.sensor_range[i]),
                length=float(e.length[i]),
            )
            for i in range(e.n)
        ]
