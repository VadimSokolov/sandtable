"""Mission scoring: measures of effectiveness / performance reduced to scalar KPIs.

Everything the optimizer sees comes out of here. `compute` returns a flat dict of scalars per run;
`sandtable.sim.evaluate` averages them across Monte-Carlo replications. The five TDD metric families map
onto these fields (TTP effectiveness -> success / time_to_objective / attrition; more families are
added as the C2, comms/EW, and air layers land).
"""
from __future__ import annotations

import numpy as np

from sandtable.entities import AIR, BLUE, RED, Entities
from sandtable.scenario import Scenario


def blue_at_goal(ent: Entities, scn: Scenario) -> np.ndarray:
    """Mask of living blue entities within the objective radius."""
    gx, gy = scn.objective.goal
    d = np.hypot(ent.x - gx, ent.y - gy)
    return ent.side_mask(BLUE) & (d <= scn.objective.goal_radius)


def compute(scn: Scenario, init_counts: dict, ent: Entities,
            t_reached: float | None, t_elapsed: float, assault0: int | None = None,
            air0: int = 0, bhv=None, op=None) -> dict:
    blue0 = max(init_counts[BLUE], 1)
    red0 = max(init_counts[RED], 1)
    blue_alive = int(ent.side_mask(BLUE).sum())
    red_alive = int(ent.side_mask(RED).sum())
    arrived = int(blue_at_goal(ent, scn).sum())
    blue_losses = init_counts[BLUE] - blue_alive
    red_losses = init_counts[RED] - red_alive
    # Success is judged over the assault force (ground blue when air recon is present); defaults to
    # the whole blue force so the ground-core scenarios are unchanged.
    assault = assault0 if assault0 is not None else init_counts[BLUE]
    success = 1.0 if arrived >= scn.objective.survive_fraction * max(assault, 1) else 0.0
    tto = float(t_reached) if t_reached is not None else float(scn.duration)

    # Cost-weighted exchange (Increment 6 KPI). Split blue losses by domain so an asymmetric cost of
    # loss can be attached: a shot-down recon drone is cheap, a lost assault vehicle is not. The unit
    # costs are stipulated scenario params defaulting to 1, so with defaults `cost_exchange` reduces
    # EXACTLY to `loss_exchange` and every prior scenario's number is unchanged.
    blue_air_alive = int((ent.side_mask(BLUE) & (ent.domain == AIR)).sum())
    blue_air_losses = max(0, air0 - blue_air_alive)
    blue_ground_losses = blue_losses - blue_air_losses
    cost_uas = float(scn.params.get("cost_uas", 1.0))         # per shot-down recon drone (air blue)
    cost_ugv = float(scn.params.get("cost_ugv", 1.0))         # per lost assault vehicle (ground blue)
    cost_red = float(scn.params.get("cost_red", 1.0))         # value of a destroyed red element
    blue_cost_lost = blue_air_losses * cost_uas + blue_ground_losses * cost_ugv
    red_cost_lost = red_losses * cost_red

    out_extra = _teaming_metrics(scn, ent, bhv, op, t_elapsed)

    return {
        **out_extra,
        "success": success,                                   # MOE: mission accomplished
        "time_to_objective": tto,                             # MOE: tempo (s)
        "blue_losses": float(blue_losses),                    # MOE: attrition
        "red_losses": float(red_losses),
        "blue_survivors": float(blue_alive),
        "arrived": float(arrived),
        "blue_loss_frac": blue_losses / blue0,
        "red_loss_frac": red_losses / red0,
        "loss_exchange": red_losses / max(blue_losses, 1),    # MOP: exchange ratio (count-based)
        "blue_air_losses": float(blue_air_losses),            # recon drones shot down
        "blue_ground_losses": float(blue_ground_losses),      # assault vehicles lost
        "blue_cost_lost": float(blue_cost_lost),              # cost-weighted blue attrition
        "cost_exchange": red_cost_lost / max(blue_cost_lost, 1.0),  # MOP: cost-weighted exchange
        "mission_time": float(t_elapsed),
    }


def _teaming_metrics(scn: Scenario, ent: Entities, bhv, op, t_elapsed: float) -> dict:
    """Adaptability and operator-load families (CR-4, CR-7).

    Every key is exactly 0.0 when its layer is absent, so ground-core scenarios and every number
    recorded before these landed are unchanged.

    Two qualifiers are mandatory wherever these are reported.

    `intervention_rate` counts comms and operator-queue contention **only**. Terrain enters
    SandTable as a speed raster and a cover tradeoff, never as autonomy difficulty that forces a
    takeover, so this is not comparable to a field-measured soldier takeover rate.

    `intervention_rate` is a rate of *events*, and jamming lengthens each event, so it can fall
    while the burden rises. Always read it next to `hold_fraction`, the share of live vehicle-steps
    spent stopped waiting on the operator. `fan_out` is the Olsen and Goodrich estimate
    ``1 + neglect_steps / interaction_steps``: the number of vehicles this interaction pattern
    could sustain. It is a capacity prediction from the observed duty cycle, so comparing it with
    the span at which measured performance actually peaks is a check on the model, not a metric to
    optimize.

    `operator_goodput` is the share of direct-control decision requests that came back with an
    operator decision inside the requester's patience. Its complement splits into
    `abandon_queue_frac` (reached the operator, could not be served in time) and
    `abandon_link_frac` (the link dropped it). All three are 0.0 under supervisory control, where
    no request is ever made.

    `operator_utilization` is a workload *surrogate* in the sense of Donmez, Nehme and Cummings.
    Computational workload models explain roughly 61 to 77 percent of variance (Sarno and Wickens),
    so it is a ranking instrument and an overload flag, not a NASA-TLX-comparable score. Do not
    label it "workload".
    """
    from sandtable.entities import GROUND

    out = {"interventions": 0.0, "intervention_rate": 0.0,
           "operator_utilization": 0.0, "mean_wait": 0.0,
           "wait_p95": 0.0, "queue_depth_mean": 0.0,
           "operator_goodput": 0.0, "abandon_queue_frac": 0.0, "abandon_link_frac": 0.0,
           "hold_fraction": 0.0, "interaction_steps": 0.0, "neglect_steps": 0.0, "fan_out": 0.0}

    if bhv is not None:
        n_ground = max(int(((ent.side == BLUE) & (ent.domain == GROUND)).sum()), 1)
        hours = max(t_elapsed, 1e-9) / 3600.0
        out["interventions"] = float(bhv.interventions.sum())
        out["intervention_rate"] = out["interventions"] / (n_ground * hours)
        held = float(bhv.hold_steps.sum())
        live = float(bhv.alive_steps.sum())
        if live > 0.0:
            out["hold_fraction"] = held / live
        if out["interventions"] > 0.0 and held > 0.0:
            # Olsen and Goodrich's fan-out: how many vehicles one operator could hold if each
            # needed `interaction_steps` of attention and then ran free for `neglect_steps`.
            out["interaction_steps"] = held / out["interventions"]
            out["neglect_steps"] = (live - held) / out["interventions"]
            out["fan_out"] = 1.0 + out["neglect_steps"] / out["interaction_steps"]

    if op is not None and op.total_steps > 0:
        out["operator_utilization"] = op.busy_steps / op.total_steps
        out["queue_depth_mean"] = op.queue_depth_sum / op.total_steps
        if op.waits:
            w = np.asarray(op.waits, float)
            out["mean_wait"] = float(w.mean())
            out["wait_p95"] = float(np.percentile(w, 95))
        if op.n_request > 0:
            out["operator_goodput"] = op.n_serviced / op.n_request
            out["abandon_queue_frac"] = op.n_abandon_queue / op.n_request
            out["abandon_link_frac"] = op.n_abandon_link / op.n_request
    return out
