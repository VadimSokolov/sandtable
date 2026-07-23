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
            air0: int = 0) -> dict:
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

    return {
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
