"""Leader hold state and explicit diagnostic-loss event adapter."""

import numpy as np


class BehaviorEventAdapter:
    def __init__(self, mission, state, events, console):
        self.m = mission
        self.state = state
        self.events = events
        self.console = console
        self.last_status = None

    def step(self, original, ent, b, op, comms, scn, k, rng, world=None):
        if self.m["diagnostic_loss_s"] is not None and k == self.m["diagnostic_loss_s"]:
            h = int(b.ll_head[0])
            if h >= 0 and ent.alive[h]:
                ent.alive[h] = False
                ent.hp[h] = 0
                self.events.append(dict(t=k, event="FORCED_DIAGNOSTIC_HEAD_LOSS", vehicle=h))
        original(ent, b, op, comms, scn, k, rng, world=world)
        self.console.after_behavior(k, ent, b)
        lh = np.zeros(ent.n, bool)
        if b.ll_halted is not None:
            for u, held in enumerate(b.ll_halted):
                if held:
                    lh |= (ent.march_unit == u) & ent.alive & (ent.side == 0)
        self.state["leader_hold"] = lh
        status = (tuple(b.ll_head), bool(b.in_contact), int(b.ll_handoffs))
        if status != self.last_status:
            self.events.append(
                dict(
                    t=k,
                    event="BEHAVIOR_STATE",
                    heads=b.ll_head.tolist(),
                    contact=bool(b.in_contact),
                    handoffs=int(b.ll_handoffs),
                )
            )
            self.last_status = status
