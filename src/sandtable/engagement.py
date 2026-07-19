"""Engagement: probability-of-kill attrition modulated by cover.

Each living shooter engages its nearest detected enemy within weapon range. A kill is a Bernoulli
draw with probability `pk_base * (1 - cover at the target)`; cover reduces incoming lethality. Both
sides resolve against the same pre-step state and damage is applied simultaneously (no ordering
bias). This is the cheap, mission-level Pk abstraction (COMBAT XXI data-table style; Gaertner 2013).

Planned enhancement: aspect-sector Pk (target split into 8 sectors, exposed sector sets the kill
probability) and a Lanchester aggregate mode for off-stage forces. The interface (`step` mutates
`ent.hp`/`ent.alive` in place) stays fixed.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist

from sandtable.entities import BLUE, GROUND, RED, Entities
from sandtable.world import World


def _side_damage(ent: Entities, world: World, dist: np.ndarray, shooter_side: int,
                 rng: np.random.Generator, damage: np.ndarray) -> None:
    shooters = ent.alive & (ent.side == shooter_side)
    if not shooters.any():
        return
    opposing = ent.side[:, None] != ent.side[None, :]
    engageable = (
        shooters[:, None]
        & ent.alive[None, :]
        & opposing
        & (dist <= ent.weapon_range[:, None])
        & ent.seen[None, :]                 # may only fire on detected enemies
        & (ent.domain[None, :] == GROUND)   # air recon (UAS) is not engaged (no SHORAD modeled)
    )
    dmasked = np.where(engageable, dist, np.inf)
    has_target = np.isfinite(dmasked).any(axis=1)
    shooter_idx = np.nonzero(shooters & has_target)[0]
    if shooter_idx.size == 0:
        return
    target_idx = np.argmin(dmasked[shooter_idx], axis=1)
    pk = ent.pk_base[shooter_idx] * (1.0 - world.cover_at(ent.x[target_idx], ent.y[target_idx]))
    # Control-quality coupling (Increment 2): a well-controlled shooter engages more
    # effectively; a poorly-controlled target exposes itself and is easier to hit.
    # Neutral at control_quality 1.0, so ground-core scenarios are byte-identical.
    q = getattr(ent, "control_quality", None)
    if q is not None:
        pk = pk * q[shooter_idx] * (2.0 - q[target_idx])
    pk = np.clip(pk, 0.0, 1.0)
    killed = rng.random(shooter_idx.size) < pk
    np.add.at(damage, target_idx[killed], 1.0)


def step(ent: Entities, world: World, dt: float, rng: np.random.Generator) -> None:
    """Resolve one round of mutual engagement in place."""
    n = ent.n
    if n == 0:
        return
    pos = np.column_stack([ent.x, ent.y])
    dist = cdist(pos, pos)

    damage = np.zeros(n)
    _side_damage(ent, world, dist, BLUE, rng, damage)
    _side_damage(ent, world, dist, RED, rng, damage)

    ent.hp = ent.hp - damage
    ent.alive = ent.alive & (ent.hp > 0.0)
