"""Opt-in study adapter, isolated from default engine behavior."""

import numpy as np


class ConsoleTransferAdapter:
    def __init__(self, m, state, events):
        self.m = m
        self.state = state
        self.events = events
        self.episodes = {}
        self.op = None

    def step(self, original, ent, op, comms, scn, k, rng, world=None, bhv=None):
        self.op = op
        u = op.units
        for c, h in enumerate(u.host):
            e = self.episodes.get(c)
            if not ent.alive[h] and (e is None or e["host"] != int(h) or e["transferred"]):
                e = dict(host=int(h), lost=k, leader=None, transferred=False)
                self.episodes[c] = e
                self.events.append(
                    dict(t=k, event="CONSOLE_HOST_LOSS_OBSERVED", console=c, vehicle=int(h))
                )
            if (
                e
                and e["leader"] is not None
                and (not e["transferred"])
                and (self.m["console_transfer"] == "successor")
                and (k >= e["leader"] + self.m["console_delay_s"])
            ):
                head = int(bhv.ll_head[c])
                if head >= 0 and ent.alive[head] and (ent.crew[head] > 0):
                    u.host[c] = head
                    op.crew_free_at[c] = max(float(k), op.crew_free_at[c])
                    e.update(transferred=True, host=head)
                    self.events.append(
                        dict(t=k, event="EXPERIMENTAL_CONSOLE_TRANSFER", console=c, vehicle=head)
                    )
        original(ent, op, comms, scn, k, rng, world, bhv)

    def after_behavior(self, k, ent, bhv):
        for c, e in self.episodes.items():
            if e["leader"] is None:
                h = int(bhv.ll_head[c])
                if h >= 0 and ent.alive[h] and (ent.crew[h] > 0):
                    e["leader"] = k
                    self.events.append(
                        dict(t=k, event="CREWED_LEADER_RESTORED", console=c, vehicle=h)
                    )

    def snapshot(self, ent):
        if self.op is None:
            return None
        u = self.op.units
        return dict(
            hosts=u.host.tolist(),
            available=ent.alive[u.host].tolist(),
            assigned=u.n_assigned0.tolist(),
            living=u.n_living.tolist(),
            attention=u.attention.tolist(),
            quality=u.q_eff.tolist(),
            requests=u.requests.tolist(),
            serviced=u.serviced.tolist(),
            denied=u.abandon_console.tolist(),
            rule=self.m["console_transfer"],
        )
