"""Opt-in personality-movement mode (ISAAC / EINSTein / MANA lineage), prototype.

The baseline steers blue ground vehicles down a scripted lateral lane set by the `route_bias` design
parameter. This module offers the alternative the combat-distillation models are built on: each
agent's heading is the normalized weighted sum of a few propensity vectors, toward the objective,
away from detected enemies, up the cover gradient, and away from crowding friends. Route choice is
then emergent from local propensities rather than a scripted lane, and sweeping the enemy-repulsion
weight traces a speed-survivability tradeoff with no planner in the loop. This is the ISAAC/EINSTein
weighted-penalty movement rule, with MANA's terrain awareness supplied by the cover term.

Opt-in and isolated. `build_personality` returns None unless the scenario sets
`params["movement"] == "personality"`. When None, planning.step uses the baseline lane logic and
every existing number is byte-identical (no random draws are involved on either path).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.entities import BLUE, GROUND, Entities
from sandtable.world import World


@dataclass
class Personality:
    w_goal: float      # attraction to the objective
    w_enemy: float     # repulsion from detected enemies
    w_cover: float     # attraction up the cover gradient
    w_sep: float       # separation from crowding friends
    radius: float      # interaction radius for the enemy/friend propensities (m)
    look: float        # distance ahead to place the aim point (m)


def build_personality(scn) -> Personality | None:
    """Build the personality-movement config, or None unless the scenario opts in."""
    if scn.params.get("movement") != "personality":
        return None
    p = scn.params.get("personality", {})
    return Personality(
        w_goal=float(p.get("w_goal", 1.0)),
        w_enemy=float(p.get("w_enemy", 0.0)),
        w_cover=float(p.get("w_cover", 0.0)),
        w_sep=float(p.get("w_sep", 0.0)),
        radius=float(p.get("radius", 1500.0)),
        look=float(p.get("look", 400.0)),
    )


def _unit(vx: np.ndarray, vy: np.ndarray):
    n = np.hypot(vx, vy)
    n = np.where(n > 1e-9, n, 1.0)
    return vx / n, vy / n


def aim(ent: Entities, world: World, scn, pers: Personality):
    """Aim points (tx, ty) for blue GROUND vehicles from the weighted propensity sum.

    Returns (idx, tx, ty) with `idx` the entity indices of the blue ground vehicles, or None if there
    are none. Enemy and friend propensities use an inverse-distance falloff out to `radius`; the
    enemy term only reacts to threats on the shared picture (`ent.seen`), so what the force does not
    know it cannot avoid.
    """
    gx, gy = scn.objective.goal
    idx = np.nonzero((ent.side == BLUE) & (ent.domain == GROUND) & ent.alive)[0]
    if idx.size == 0:
        return None
    px, py = ent.x[idx], ent.y[idx]

    dgx, dgy = _unit(gx - px, gy - py)                       # toward the objective
    vx = pers.w_goal * dgx
    vy = pers.w_goal * dgy

    if pers.w_enemy != 0.0:                                  # away from detected enemies
        foe = np.nonzero((ent.side != BLUE) & ent.alive & ent.seen)[0]
        if foe.size:
            rx = px[:, None] - ent.x[None, foe]
            ry = py[:, None] - ent.y[None, foe]
            d = np.hypot(rx, ry)
            w = np.clip(1.0 - d / pers.radius, 0.0, 1.0) / np.where(d > 1e-6, d, 1.0)
            vx = vx + pers.w_enemy * (rx * w).sum(axis=1)
            vy = vy + pers.w_enemy * (ry * w).sum(axis=1)

    if pers.w_sep != 0.0 and idx.size > 1:                   # separation from crowding friends
        rx = px[:, None] - px[None, :]
        ry = py[:, None] - py[None, :]
        d = np.hypot(rx, ry)
        np.fill_diagonal(d, np.inf)
        w = np.clip(1.0 - d / pers.radius, 0.0, 1.0) / np.where(d > 1e-6, d, 1.0)
        vx = vx + pers.w_sep * (rx * w).sum(axis=1)
        vy = vy + pers.w_sep * (ry * w).sum(axis=1)

    if pers.w_cover != 0.0:                                  # up the cover gradient (finite diff)
        h = world.cell
        gxc = world.cover_at(px + h, py) - world.cover_at(px - h, py)
        gyc = world.cover_at(px, py + h) - world.cover_at(px, py - h)
        on = np.hypot(gxc, gyc) > 1e-9
        gux, guy = _unit(gxc, gyc)
        vx = vx + pers.w_cover * np.where(on, gux, 0.0)
        vy = vy + pers.w_cover * np.where(on, guy, 0.0)

    ux, uy = _unit(vx, vy)
    tx = np.clip(px + ux * pers.look, 0.0, world.size[0])
    ty = np.clip(py + uy * pers.look, 0.0, world.size[1])
    return idx, tx, ty
