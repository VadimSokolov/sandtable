"""The simulation loop: `run_mission` (one deterministic run) and `evaluate` (MC ensemble).

`run_mission(scenario, seed) -> metrics` is a pure function with no global state: the top-level
contract the optimizer and the polarisopt slave call. The fixed-timestep loop advances planning ->
motion -> sensing -> engagement, records the objective-arrival time, and stops on mission success or
blue elimination. `evaluate` averages the KPIs over independent seeded replications and returns the
scalars an optimizer minimizes/maximizes.
"""
from __future__ import annotations

import numpy as np

from sandtable import (
    behavior,
    belief,
    c2,
    counter_uas,
    engagement,
    formation_metrics,
    mechanics,
    metrics,
    motion,
    personality,
    planning,
    sensing,
)
from sandtable.comms_ew import build_comms
from sandtable.entities import AIR, BLUE, GROUND, RED
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
    op = c2.build_c2(scn, ent, rng)
    # Optional belief/track layer (Increment 4, prototype). None unless the scenario opts in via
    # params["belief"]["model"] == "tracks"; when None the baseline engagement path runs unchanged.
    tracks = belief.build_tracks(scn, ent)
    # Optional kill-web mechanics (Increment 5): suppression and munitions. None unless the scenario
    # sets params["mech"]; when None the engagement draws the identical RNG stream (byte-identical).
    mech = mechanics.build_mech(scn)
    if mech is not None:
        mechanics.arm(ent, mech)
    # Optional personality-movement mode (opt-in). None unless params["movement"]=="personality";
    # when None, planning uses the scripted lane and results are byte-identical.
    pers = personality.build_personality(scn)
    # Optional counter-UAS / SHORAD (Increment 6): red air defense attrites the blue recon swarm.
    # None unless params set cuas_rate>0; when None the loop skips it and draws no extra RNG
    # (byte-identical to any prior run without it).
    cuas = counter_uas.build_counter_uas(scn, ent)
    # Optional blue behavior layer (CR-1): modality selects a behaviour repertoire rather than
    # only a quality gain. None unless params set blue_behavior; when None planning takes exactly
    # its previous code path and the run is byte-identical.
    bhv = behavior.build_behavior(scn, ent)

    init_counts = {BLUE: int((ent.side == BLUE).sum()), RED: int((ent.side == RED).sum())}
    blue_mask0 = ent.side == BLUE
    spawn_x = float(ent.x[blue_mask0].min()) if blue_mask0.any() else 0.0

    tempo = float(scn.params.get("tempo", 1.0))
    dt = scn.dt
    # `duration` is a scenario field, but the mission-length audit has to vary it without
    # editing scenario files, so a param of the same name overrides it when present.
    n_steps = max(int(float(scn.params.get("duration", scn.duration)) / dt), 1)
    # The assault force is the GROUND blue; UAS recon assets (air) do not advance to the objective,
    # so the success threshold and time-to-objective are judged over ground blue only. For the
    # ground-core scenarios (no air) this equals init_counts[BLUE], so they are unchanged.
    ground_blue0 = int(((ent.side == BLUE) & (ent.domain == GROUND)).sum())
    assault0 = ground_blue0 if ground_blue0 > 0 else init_counts[BLUE]
    air_blue0 = int(((ent.side == BLUE) & (ent.domain == AIR)).sum())   # recon swarm size (for cost KPI)
    need = scn.objective.survive_fraction * assault0

    t = 0.0
    t_reached = None
    cov_sum = 0.0
    cov_steps = 0
    # Mutual support is a range question, and the range that matters is the one an engagement
    # happens at rather than any formation constant. Blue's own weapon range is the honest choice:
    # two vehicles inside it can shoot at the same thing.
    _bw = ent.weapon_range[ent.side_mask(BLUE) & (ent.domain == GROUND)]
    supp_range = float(_bw.max()) if _bw.size else 1000.0
    # The graph readings of the same formation, opt-in through a peer-link range. They are off by
    # default because they are a measurement rather than a mechanism and they cost real time: an
    # exact vertex connectivity is a run of max flows, so it is sampled on a cadence rather than
    # every step. Off, the block never runs and the four keys read zero.
    graph_range = float(scn.params.get("graph_range", 0.0))
    graph_every = max(1, int(scn.params.get("graph_every", 20)))
    g_fied = g_kappa = g_faults = g_disc = 0.0
    g_steps = 0
    # Formation dispersion, which is the same positions as station-keeping error read through a
    # different functional. Station error is measured against each vehicle's COMMANDED station, so
    # it is structurally blind to whether the commanded geometry is survivable; this one has no
    # commanded geometry in it at all. RMS distance of the living blue assault force from its own
    # centroid, averaged over the steps where two or more of them are alive.
    disp_sum = 0.0
    disp_steps = 0
    # And the same three mediators the reviewer asked for, because RMS dispersion has a known way of
    # being wrong: it grows with extent even when every vehicle still has a neighbour inside weapon
    # range. `along` and `cross` decompose the RMS exactly onto the force's own mean heading, so
    # disp^2 = along^2 + cross^2 and the pair is a partition rather than two more numbers.
    # `support` is the mission-referenced one: the share of the force that is not alone.
    along_sum = 0.0
    cross_sum = 0.0
    supp_sum = 0.0
    # Vehicle-steps at risk. A loss FRACTION divides by the force that started, so an arm that keeps
    # vehicles alive longer gives the enemy more time to shoot at them and can read worse for a
    # reason that has nothing to do with the arm. Accumulating the exposure lets loss be reported as
    # an intensity, losses per vehicle-step at risk, which is immune to that by construction. The
    # fraction stays the headline; the intensity audits it and never travels on its own.
    blue_exposure = 0.0
    for k in range(n_steps):
        comms.set_step(k)                       # no-op unless the scenario declares a jam window
        if op is not None:
            c2.step(ent, op, comms, scn, k, rng, world)
        if bhv is not None:
            behavior.step(ent, bhv, op, comms, scn, k, rng)
        planning.step(ent, world, scn, spawn_x, pers=pers, bhv=bhv)
        motion.step(ent, world, dt, tempo)
        sensing.step(ent, world, rng, comms)
        if mech is not None:
            mechanics.decay(ent, mech)          # relax suppression one step before this tick's fire
        if tracks is None:
            engagement.step(ent, world, dt, rng, mech=mech)
        else:
            belief.update(ent, tracks, comms, rng)
            belief.engage(ent, world, tracks, rng, mech=mech)
        if cuas is not None:
            counter_uas.step(ent, cuas, rng)     # red air defense engages the blue UAS overwatch
        t = (k + 1) * dt

        # Detection coverage: fraction of the living red force currently on the blue shared picture
        # (the UC-5 sensor-swarm KPI). Averaged over the steps where red remain.
        red_alive = ent.side_mask(RED)
        n_red = int(red_alive.sum())
        if n_red > 0:
            cov_sum += int((ent.seen & red_alive).sum()) / n_red
            cov_steps += 1

        blue_exposure += float(ent.side_mask(BLUE).sum())

        assault = ent.side_mask(BLUE) & (ent.domain == GROUND)
        if int(assault.sum()) > 1:
            ax, ay = ent.x[assault], ent.y[assault]
            dx, dy = ax - ax.mean(), ay - ay.mean()
            disp_sum += float(np.sqrt((dx ** 2 + dy ** 2).mean()))
            hx = float(np.cos(ent.heading[assault]).mean())
            hy = float(np.sin(ent.heading[assault]).mean())
            hn = float(np.hypot(hx, hy))
            ux, uy = (hx / hn, hy / hn) if hn > 1e-6 else (1.0, 0.0)
            along_sum += float(np.sqrt(((dx * ux + dy * uy) ** 2).mean()))
            cross_sum += float(np.sqrt(((-dx * uy + dy * ux) ** 2).mean()))
            rr = np.hypot(ax[:, None] - ax[None, :], ay[:, None] - ay[None, :])
            np.fill_diagonal(rr, np.inf)
            supp_sum += float((rr.min(axis=1) <= supp_range).mean())
            disp_steps += 1
            if graph_range > 0.0 and k % graph_every == 0:
                s = formation_metrics.score(ax, ay, graph_range)
                g_fied += s["fiedler"]
                g_kappa += s["kappa"]
                g_faults += s["faults"]
                g_disc += s["disconnected"]
                g_steps += 1

        if t_reached is None and metrics.blue_at_goal(ent, scn).sum() >= need:
            t_reached = t
            break
        if not ent.side_mask(BLUE).any():
            break

    result = metrics.compute(scn, init_counts, ent, t_reached, t, assault0=assault0, air0=air_blue0,
                             bhv=bhv, op=op)
    result["detection_coverage"] = cov_sum / max(cov_steps, 1)
    result["fleet_spread_mean"] = disp_sum / max(disp_steps, 1)
    result["fleet_along_mean"] = along_sum / max(disp_steps, 1)
    result["fleet_cross_mean"] = cross_sum / max(disp_steps, 1)
    result["support_frac"] = supp_sum / max(disp_steps, 1)
    # Averaged over the SAMPLED steps, not over the mission, so a formation that dies early is not
    # credited with the connectivity of the steps it did not live to see.
    # Exposure and the intensity it makes readable. `blue_exposure` is in vehicle-steps, so
    # it is a scale that depends on the horizon and is reported for the decomposition rather
    # than for comparison: d(frac) = d(intensity) * exposure + intensity * d(exposure), and
    # the second term is a real console channel (a console that keeps vehicles moving changes
    # how long they are exposed) rather than a confound to be removed.
    result["blue_exposure"] = blue_exposure
    result["loss_intensity"] = (result["blue_losses"] / blue_exposure
                                if blue_exposure > 0.0 else float("nan"))
    result["fleet_fiedler_mean"] = g_fied / g_steps if g_steps else 0.0
    result["fleet_kappa_mean"] = g_kappa / g_steps if g_steps else 0.0
    result["fleet_faults_mean"] = g_faults / g_steps if g_steps else 0.0
    result["fleet_disconnected_frac"] = g_disc / g_steps if g_steps else 0.0
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
