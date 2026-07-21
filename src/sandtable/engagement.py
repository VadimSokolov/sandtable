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

from sandtable import mechanics
from sandtable.entities import BLUE, GROUND, RED, Entities
from sandtable.world import World


def _side_damage(ent: Entities, world: World, dist: np.ndarray, shooter_side: int,
                 rng: np.random.Generator, damage: np.ndarray, events: list | None = None,
                 mech: "mechanics.Mech | None" = None, supp0: np.ndarray | None = None) -> None:
    shooters = ent.alive & (ent.side == shooter_side)
    if mech is not None:
        shooters = shooters & mechanics.has_ammo(ent, mech)   # a shooter with no rounds cannot fire
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
    # Kill-web coupling (Increment 5): a suppressed shooter fires less effectively. Read from the
    # pre-step snapshot so both sides use the same suppression; neutral when the mechanic is off.
    if mech is not None:
        pk = pk * mechanics.fire_factor(mech, supp0, shooter_idx)
    pk = np.clip(pk, 0.0, 1.0)
    killed = rng.random(shooter_idx.size) < pk
    np.add.at(damage, target_idx[killed], 1.0)
    if mech is not None:
        mechanics.suppress(ent, mech, target_idx)   # incoming fire suppresses the targets engaged
        mechanics.expend(ent, mech, shooter_idx)     # each shot spends a round
    # Optional replay hook: record (shooter, target) kill pairs. `events is None` on the hot path
    # (sim.run_mission), so the optimizer draws the identical RNG stream and pays no overhead.
    if events is not None:
        for s, t in zip(shooter_idx[killed], target_idx[killed]):
            events.append((int(s), int(t)))


def step(ent: Entities, world: World, dt: float, rng: np.random.Generator,
         events: list | None = None, mech: "mechanics.Mech | None" = None) -> None:
    """Resolve one round of mutual engagement in place. `events`, if given, collects kill pairs.
    `mech`, if given, applies the opt-in kill-web mechanics (suppression, munitions); when None the
    resolution and its RNG draws are byte-identical to the baseline.
    """
    n = ent.n
    if n == 0:
        return
    pos = np.column_stack([ent.x, ent.y])
    dist = cdist(pos, pos)

    # Snapshot suppression before either side fires so both read pre-step values (no order bias).
    supp0 = ent.suppression.copy() if (mech is not None and mech.suppression) else None
    damage = np.zeros(n)
    _side_damage(ent, world, dist, BLUE, rng, damage, events, mech, supp0)
    _side_damage(ent, world, dist, RED, rng, damage, events, mech, supp0)

    ent.hp = ent.hp - damage
    ent.alive = ent.alive & (ent.hp > 0.0)
