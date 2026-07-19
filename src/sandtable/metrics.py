"""Mission scoring: measures of effectiveness / performance reduced to scalar KPIs.

Everything the optimizer sees comes out of here. `compute` returns a flat dict of scalars per run;
`sandtable.sim.evaluate` averages them across Monte-Carlo replications. The five TDD metric families map
onto these fields (TTP effectiveness -> success / time_to_objective / attrition; more families are
added as the C2, comms/EW, and air layers land).
"""
from __future__ import annotations

import numpy as np

from sandtable.entities import BLUE, RED, Entities
from sandtable.scenario import Scenario


def blue_at_goal(ent: Entities, scn: Scenario) -> np.ndarray:
    """Mask of living blue entities within the objective radius."""
    gx, gy = scn.objective.goal
    d = np.hypot(ent.x - gx, ent.y - gy)
    return ent.side_mask(BLUE) & (d <= scn.objective.goal_radius)


def compute(scn: Scenario, init_counts: dict, ent: Entities,
            t_reached: float | None, t_elapsed: float, assault0: int | None = None) -> dict:
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

    return {
        "success": success,                                   # MOE: mission accomplished
        "time_to_objective": tto,                             # MOE: tempo (s)
        "blue_losses": float(blue_losses),                    # MOE: attrition
        "red_losses": float(red_losses),
        "blue_survivors": float(blue_alive),
        "arrived": float(arrived),
        "blue_loss_frac": blue_losses / blue0,
        "red_loss_frac": red_losses / red0,
        "loss_exchange": red_losses / max(blue_losses, 1),    # MOP: exchange ratio
        "mission_time": float(t_elapsed),
    }
