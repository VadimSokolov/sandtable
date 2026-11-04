"""Experimental control-first selection and combat event recording."""

import numpy as np
from sandtable.scenario import Scenario
from .vendor import target_priority, engagement


class EngagementAdapter:
    def __init__(self, mission, scenario, state, events):
        self.m = mission
        self.cfg = scenario
        self.state = state
        self.events = events
        self.tp = target_priority if mission["target_priority"] == "control_first" else None
        self.branch = engagement

    def metrics(self):
        return self.tp.metrics(self.state["priority"]) if self.tp is not None else {}

    def step(self, original, ent, w, dt, rng, **kw):
        before = ent.alive.copy()
        k = self.state["k"]
        if self.tp is None:
            original(ent, w, dt, rng, **kw)
        else:
            if self.state.get("priority") is None:
                self.state["priority"] = self.tp.build_target_priority(
                    Scenario.from_dict(self.cfg).with_params(
                        {"target_priority": {"order": ["control"]}}
                    ),
                    ent,
                )
            pr = self.state["priority"]
            self.tp.begin_step(ent, pr, k)
            self.branch.step(ent, w, dt, rng, prio=pr, **kw)
            self.tp.end_step(ent, pr)
        for i in np.flatnonzero(before & ~ent.alive):
            self.events.append(
                dict(
                    t=k + 1,
                    event="COMBAT_DESTRUCTION",
                    vehicle=int(i),
                    side=int(ent.side[i]),
                    role=int(ent.convoy_role[i]),
                )
            )
