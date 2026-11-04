"""Compose explicit study adapters around one real, process-isolated mission."""

import contextlib
from unittest.mock import patch
from sandtable import behavior, c2, engagement, metrics, motion, planning, sim
from sandtable.comms_ew import Comms
from sandtable.scenario import Scenario
from .adapters.movement import RouteMotionAdapter
from .adapters.consoles import ConsoleTransferAdapter
from .adapters.world import BuilderWorldAdapter
from .adapters.behavior_events import BehaviorEventAdapter
from .adapters.engagement import EngagementAdapter
from .recording import MissionRecorder
from .serialization import clean


class Cancelled(Exception):
    pass


class SimulationRunner:
    """One mission per process. Temporary core hooks are always restored."""

    def run(self, compiled, seed, progress=None, cancel=None, capture=True, capture_stride_s=None):
        cfg = compiled["scenario"]
        m = compiled["config"]["mission"]
        state = {}
        events = []
        geometry = RouteMotionAdapter(m, state)
        console = ConsoleTransferAdapter(m, state, events)
        terrain = BuilderWorldAdapter(compiled, state)
        behavior_events = BehaviorEventAdapter(m, state, events, console)
        combat = EngagementAdapter(m, cfg, state, events)
        stride = (
            max(1, int(m["duration"] // 450)) if capture_stride_s is None else int(capture_stride_s)
        )
        if stride < 1:
            raise ValueError("Capture stride must be positive.")
        recorder = MissionRecorder(state, m, console, geometry, stride, capture)
        original = {
            k: getattr(mod, name)
            for k, mod, name in [
                ("entities", sim, "build_entities"),
                ("world", sim, "build_world"),
                ("behavior_build", behavior, "build_behavior"),
                ("behavior", behavior, "step"),
                ("c2", c2, "step"),
                ("planning", planning, "step"),
                ("motion", motion, "step"),
                ("risk", metrics, "accumulate_crew_at_risk"),
                ("comms", Comms, "set_step"),
                ("engagement", engagement, "step"),
            ]
        }

        def entities(scn, rng):
            e = terrain.place_entities(original["entities"], scn, rng)
            recorder.register_entities(e)
            return e

        def behavior_build(scn, ent):
            b = original["behavior_build"](scn, ent)
            state["bhv"] = b
            return b

        def comms(link, k):
            if cancel and cancel():
                raise Cancelled("Cancelled by user")
            state["k"] = k
            recorder.capture_frame(k)
            if progress and k % 10 == 0:
                progress(k / m["duration"], k)
            return original["comms"](link, k)

        def risk(ent, acc):
            original["risk"](ent, acc)
            state["risk"] = float(acc.sum())

        hooks = [
            (sim, "build_world", lambda *a, **kw: terrain.build(original["world"], *a, **kw)),
            (sim, "build_entities", entities),
            (behavior, "build_behavior", behavior_build),
            (Comms, "set_step", comms),
            (
                behavior,
                "step",
                lambda *a, **kw: behavior_events.step(original["behavior"], *a, **kw),
            ),
            (c2, "step", lambda *a, **kw: console.step(original["c2"], *a, **kw)),
            (planning, "step", lambda *a, **kw: geometry.plan(original["planning"], *a, **kw)),
            (motion, "step", lambda *a, **kw: geometry.move(original["motion"], *a, **kw)),
            (metrics, "accumulate_crew_at_risk", risk),
            (engagement, "step", lambda *a, **kw: combat.step(original["engagement"], *a, **kw)),
        ]
        with contextlib.ExitStack() as stack:
            for mod, name, fn in hooks:
                stack.enter_context(patch.object(mod, name, fn))
            outcome = sim.run_mission(Scenario.from_dict(cfg), seed=seed)
            recorder.capture_frame(outcome["mission_time"], True)
        outcome.update(combat.metrics())
        outcome.update(
            v3_blocked_move_steps=geometry.blocked,
            v3_herringbone_episodes=geometry.episodes,
            v3_rejected_parking_stations=geometry.rejected,
        )
        if outcome["cargo_success"] == 1:
            reason = "Required cargo delivery fraction reached."
        elif outcome["cargo_in_transit"] <= 1e-6:
            reason = "No undelivered cargo remains on living vehicles; delivery target unmet."
        else:
            reason = "Mission horizon reached before the delivery requirement."
        return clean(
            dict(
                seed=seed,
                config_hash=compiled["config_hash"],
                summary=compiled["summary"],
                configuration=compiled["config"],
                engine_scenario=cfg,
                entities=state["entities"],
                frames=recorder.frames,
                events=sorted(events, key=lambda x: x["t"]),
                outcome=outcome,
                end_reason=reason,
                frame_stride_s=stride,
                notes=[
                    "Frames are end-of-step snapshots including delivery accounting; no position interpolation.",
                    "Crew exposure counts living crews in range without a LOS/detection gate.",
                    "Accepted console services do not prove reply delivery.",
                ],
            )
        )


def run(*args, **kwargs):
    return SimulationRunner().run(*args, **kwargs)
