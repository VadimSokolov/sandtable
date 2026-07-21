"""Kill-web mechanics: suppression and munitions (opt-in, prototype).

Two first-class effects from the ground-combat lineage (COMBAT XXI, OneSAF) that the baseline
attrition kernel lacks, both raised in review as state every entity should carry:

  Suppression: a decaying [0, 1] state raised by incoming fire. A suppressed unit brings less
  effective fire (aim and target acquisition both degrade), so its per-shot kill probability is
  scaled down. This is what makes a base-of-fire element valuable: suppressing the defenders lets a
  maneuver element cross a danger zone at lower cost, an effect a fixed Pk table cannot express.

  Munitions: rounds carried per shooter, decremented on fire; a shooter that runs dry cannot engage.
  This puts a sustainment ceiling on sustained rate of fire.

Opt-in and isolated. `build_mech` returns None unless the scenario sets `params["mech"]` with
`suppression` or `munitions` true. When None, the baseline engagement path runs unchanged and draws
the identical RNG stream, so every existing scenario, test, and number stays byte-identical. Both
effects are applied inside the engagement resolution through the helpers here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.entities import Entities


@dataclass
class Mech:
    suppression: bool
    munitions: bool
    supp_gain: float    # suppression added to a target per incoming engagement opportunity
    supp_decay: float   # multiplicative decay of suppression per step
    supp_fire: float    # fraction of Pk removed at full suppression, in [0, 1]
    ammo_load: float    # rounds each shooter starts with when munitions are on


def build_mech(scn) -> Mech | None:
    """Build the kill-web mechanics config, or None unless the scenario opts in."""
    cfg = scn.params.get("mech") or {}
    if not (cfg.get("suppression") or cfg.get("munitions")):
        return None
    return Mech(
        suppression=bool(cfg.get("suppression", False)),
        munitions=bool(cfg.get("munitions", False)),
        supp_gain=float(cfg.get("supp_gain", 0.25)),
        supp_decay=float(cfg.get("supp_decay", 0.85)),
        supp_fire=float(cfg.get("supp_fire", 0.8)),
        ammo_load=float(cfg.get("ammo_load", 30.0)),
    )


def arm(ent: Entities, mech: Mech) -> None:
    """Set the initial ammo load on weapon-carrying entities (called once at build)."""
    if mech.munitions:
        ent.ammo[ent.pk_base > 0.0] = mech.ammo_load


def decay(ent: Entities, mech: Mech) -> None:
    """Relax suppression one step (called once per tick)."""
    if mech.suppression:
        ent.suppression *= mech.supp_decay


def fire_factor(mech: Mech, supp: np.ndarray | None, idx) -> np.ndarray | float:
    """Pk multiplier from a pre-step suppression snapshot (1.0 when suppression is off).

    `supp` is a snapshot of `ent.suppression` taken before this step's engagement, so both sides
    read the same pre-step values (no shooter-order bias); `idx` selects the shooters. Returns a
    scalar 1.0 when suppression is off, which broadcasts harmlessly against any Pk array or scalar.
    """
    if not mech.suppression:
        return 1.0
    return 1.0 - mech.supp_fire * supp[idx]


def has_ammo(ent: Entities, mech: Mech) -> np.ndarray:
    """Boolean mask over all entities that still have ammunition (all True when munitions off)."""
    if not mech.munitions:
        return np.ones(ent.n, bool)
    return ent.ammo > 0.0


def expend(ent: Entities, mech: Mech, shooter_idx: np.ndarray) -> None:
    """Decrement ammo by one round for each shooter that fired."""
    if mech.munitions and shooter_idx.size:
        np.add.at(ent.ammo, shooter_idx, -1.0)


def suppress(ent: Entities, mech: Mech, target_idx: np.ndarray) -> None:
    """Raise suppression on entities that were fired upon this step (capped at 1)."""
    if mech.suppression and target_idx.size:
        np.add.at(ent.suppression, target_idx, mech.supp_gain)
        np.clip(ent.suppression, 0.0, 1.0, out=ent.suppression)
