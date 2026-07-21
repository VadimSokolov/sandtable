"""The simulation loop: `run_mission` (one deterministic run) and `evaluate` (MC ensemble).

`run_mission(scenario, seed) -> metrics` is a pure function with no global state: the top-level
contract the optimizer and the polarisopt slave call. The fixed-timestep loop advances planning ->
motion -> sensing -> engagement, records the objective-arrival time, and stops on mission success or
blue elimination. `evaluate` averages the KPIs over independent seeded replications and returns the
scalars an optimizer minimizes/maximizes.
"""
from __future__ import annotations

import numpy as np

from sandtable import belief, c2, engagement, mechanics, metrics, motion, planning, sensing
from sandtable.comms_ew import build_comms
from sandtable.entities import BLUE, GROUND, RED
from sandtable.scenario import Scenario, build_entities
from sandtable.seeding import make_rng
from sandtable.world import build_world


def run_mission(scenario: Scenario, seed: int = 0, params: dict | None = None) -> dict:
    """Run one mission to completion; return scalar KPIs. Deterministic given (seed, scenario)."""
    scn = scenario.with_params(params) if params else scenario
    rng = make_rng(seed, scn.id)

    world = build_world(scn, rng)
    ent = build_entities(scn, rng)

    # Optional C2 layer (Increment 2): a single operator supervising the blue agents
    # over a comms link. None for ground-core scenarios, which then run unchanged.
    comms = build_comms(scn)
    op = c2.build_c2(scn, ent)
    # Optional belief/track layer (Increment 4, prototype). None unless the scenario opts in via
    # params["belief"]["model"] == "tracks"; when None the baseline engagement path runs unchanged.
    tracks = belief.build_tracks(scn, ent)
    # Optional kill-web mechanics (Increment 5): suppression and munitions. None unless the scenario
    # sets params["mech"]; when None the engagement draws the identical RNG stream (byte-identical).
    mech = mechanics.build_mech(scn)
    if mech is not None:
        mechanics.arm(ent, mech)

    init_counts = {BLUE: int((ent.side == BLUE).sum()), RED: int((ent.side == RED).sum())}
    blue_mask0 = ent.side == BLUE
    spawn_x = float(ent.x[blue_mask0].min()) if blue_mask0.any() else 0.0

    tempo = float(scn.params.get("tempo", 1.0))
    dt = scn.dt
    n_steps = max(int(scn.duration / dt), 1)
    # The assault force is the GROUND blue; UAS recon assets (air) do not advance to the objective,
    # so the success threshold and time-to-objective are judged over ground blue only. For the
    # ground-core scenarios (no air) this equals init_counts[BLUE], so they are unchanged.
    ground_blue0 = int(((ent.side == BLUE) & (ent.domain == GROUND)).sum())
    assault0 = ground_blue0 if ground_blue0 > 0 else init_counts[BLUE]
    need = scn.objective.survive_fraction * assault0

    t = 0.0
    t_reached = None
    cov_sum = 0.0
    cov_steps = 0
    for k in range(n_steps):
        if op is not None:
            c2.step(ent, op, comms, scn, k, rng)
        planning.step(ent, world, scn, spawn_x)
        motion.step(ent, world, dt, tempo)
        sensing.step(ent, world, rng, comms)
        if mech is not None:
            mechanics.decay(ent, mech)          # relax suppression one step before this tick's fire
        if tracks is None:
            engagement.step(ent, world, dt, rng, mech=mech)
        else:
            belief.update(ent, tracks, comms, rng)
            belief.engage(ent, world, tracks, rng, mech=mech)
        t = (k + 1) * dt

        # Detection coverage: fraction of the living red force currently on the blue shared picture
        # (the UC-5 sensor-swarm KPI). Averaged over the steps where red remain.
        red_alive = ent.side_mask(RED)
        n_red = int(red_alive.sum())
        if n_red > 0:
            cov_sum += int((ent.seen & red_alive).sum()) / n_red
            cov_steps += 1

        if t_reached is None and metrics.blue_at_goal(ent, scn).sum() >= need:
            t_reached = t
            break
        if not ent.side_mask(BLUE).any():
            break

    result = metrics.compute(scn, init_counts, ent, t_reached, t, assault0=assault0)
    result["detection_coverage"] = cov_sum / max(cov_steps, 1)
    return result


def evaluate(scenario: Scenario, n_reps: int = 10, seed: int = 0,
             params: dict | None = None) -> dict:
    """Average KPIs over `n_reps` seeded replications; add a success_rate summary."""
    runs = [run_mission(scenario, seed=seed * n_reps + i, params=params) for i in range(n_reps)]
    keys = runs[0].keys()
    agg = {k: float(np.mean([r[k] for r in runs])) for k in keys}
    agg["success_rate"] = agg["success"]
    agg["n_reps"] = int(n_reps)
    return agg
