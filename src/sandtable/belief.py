"""Optional per-side belief/track layer (prototype, opt-in).

Increment 4 (prototype): a first-class perception state. The baseline carries a single `ent.seen`
bit that gates fires against truth (a detected enemy is engaged at its exact position). Here each
side instead maintains a persistent TRACK per opposing entity: a believed position that is refreshed
on detection and goes stale (frozen, with decaying confidence) when detection lapses, plus optional
FALSE tracks (decoys / spoofing). Fires are allocated against the believed position and confidence,
not truth, so electronic warfare and deception become first-order effects (a jammed track drifts and
misses; a decoy draws a wasted shot) rather than probability-of-kill modifier tables. This mirrors
the perception-processor and false-target / track effects of engagement-level frameworks such as
AFSIM.

Opt-in and isolated. `build_tracks` returns None unless the scenario sets
`params["belief"]["model"] == "tracks"`. When it is None, `sim.run_mission` calls the baseline
`engagement.step` unchanged and draws the identical RNG stream, so every existing scenario, test, and
reported number stays byte-identical. Only scenarios that request the belief model pay for it or see
its effects.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial.distance import cdist

from sandtable.entities import BLUE, GROUND, RED, Entities
from sandtable.world import World


@dataclass
class Tracks:
    """Belief state. Real tracks are one slot per entity (the opposing side's belief about it);
    false tracks are a fixed pool of decoys, `fside` naming the side that believes each one."""

    live: np.ndarray   # bool: a maintained track exists on this entity
    bx: np.ndarray     # believed x (last measured, frozen while stale)
    by: np.ndarray     # believed y
    age: np.ndarray    # int: steps since the last fresh update
    conf: np.ndarray   # float in [0, 1]: confidence, decays while stale
    fside: np.ndarray  # int8: the side that believes each false track
    fx: np.ndarray     # false-track x
    fy: np.ndarray     # false-track y
    flive: np.ndarray  # bool: false track active
    ttl: np.ndarray    # int: remaining life of each false track
    meas_noise: float
    max_age: int
    conf_decay: float
    decoy_rate: float


def build_tracks(scn, ent: Entities) -> Tracks | None:
    """Allocate the belief state, or None unless the scenario opts into the track model."""
    cfg = scn.params.get("belief") or {}
    if cfg.get("model") != "tracks":
        return None
    n = ent.n
    m = int(cfg.get("decoys", 0)) * 2   # capacity: up to `decoys` per side
    return Tracks(
        live=np.zeros(n, bool), bx=ent.x.copy(), by=ent.y.copy(),
        age=np.zeros(n, np.int32), conf=np.zeros(n),
        fside=np.zeros(m, np.int8), fx=np.zeros(m), fy=np.zeros(m),
        flive=np.zeros(m, bool), ttl=np.zeros(m, np.int32),
        meas_noise=float(cfg.get("meas_noise", 30.0)),
        max_age=int(cfg.get("max_age", 5)),
        conf_decay=float(cfg.get("conf_decay", 0.75)),
        decoy_rate=float(cfg.get("decoy_rate", 0.25)),
    )


def update(ent: Entities, tracks: Tracks, comms, rng: np.random.Generator) -> None:
    """Refresh real tracks from this step's detections, age the rest, and manage decoys.

    A jammed link (`comms.p_drop`) can fail to refresh a track (belief corruption): the track then
    goes stale and its believed position drifts from the moving truth. Decoys age out and respawn
    near the enemy, more often when jammed.
    """
    n = ent.n
    p_drop = float(getattr(comms, "p_drop", 0.0) or 0.0)

    fresh = ent.seen & ent.alive
    if p_drop > 0.0:                                   # jamming can drop the track update
        fresh = fresh & (rng.random(n) >= p_drop)
    idx = np.nonzero(fresh)[0]
    if idx.size:
        noise = rng.normal(0.0, tracks.meas_noise, size=(idx.size, 2))
        tracks.bx[idx] = ent.x[idx] + noise[:, 0]
        tracks.by[idx] = ent.y[idx] + noise[:, 1]
        tracks.age[idx] = 0
        tracks.conf[idx] = 1.0
        tracks.live[idx] = True
    stale = tracks.live & ~fresh                       # previously live, not refreshed
    tracks.age[stale] += 1
    tracks.conf[stale] *= tracks.conf_decay
    dropped = (tracks.age > tracks.max_age) | ~ent.alive
    tracks.live[dropped] = False
    tracks.conf[dropped] = 0.0

    m = tracks.flive.size
    if m == 0:
        return
    tracks.ttl[tracks.flive] -= 1
    tracks.flive &= tracks.ttl > 0
    half = m // 2
    for s, foe in ((BLUE, RED), (RED, BLUE)):
        foe_alive = np.nonzero(ent.alive & (ent.side == foe))[0]
        if foe_alive.size == 0:
            continue
        spawn_p = tracks.decoy_rate * (0.3 + p_drop)   # more decoys under jamming
        for sl in range(0 if s == BLUE else half, (half if s == BLUE else m)):
            if not tracks.flive[sl] and rng.random() < spawn_p:
                j = foe_alive[rng.integers(foe_alive.size)]
                off = rng.normal(0.0, 120.0, size=2)
                tracks.fside[sl] = s
                tracks.fx[sl] = ent.x[j] + off[0]
                tracks.fy[sl] = ent.y[j] + off[1]
                tracks.flive[sl] = True
                tracks.ttl[sl] = tracks.max_age + 2


def engage(ent: Entities, world: World, tracks: Tracks, rng: np.random.Generator,
           mech=None) -> None:
    """Belief-aware engagement: each shooter fires on its nearest live track (by believed position),
    real or decoy. A real track resolves a Bernoulli kill on the true target with Pk scaled by track
    confidence (stale tracks miss more often); a decoy consumes the shot with no effect. Both sides
    resolve against the pre-step state and damage is applied simultaneously.

    `mech`, if given, layers the opt-in kill-web mechanics on top of the belief resolution: a shooter
    out of ammunition cannot fire, a firing shooter spends a round, its Pk is scaled down by its own
    pre-step suppression, and each engaged real target is suppressed. When None, the belief path and
    its RNG draws are byte-identical to the belief-only prototype.
    """
    n = ent.n
    if n == 0:
        return
    shooter_pos = np.column_stack([ent.x, ent.y])
    real_pos = np.column_stack([tracks.bx, tracks.by])
    q = getattr(ent, "control_quality", None)
    m = tracks.flive.size
    false_pos = np.column_stack([tracks.fx, tracks.fy]) if m else np.zeros((0, 2))
    # Snapshot suppression before either side fires so both read pre-step values (no order bias).
    supp0 = ent.suppression.copy() if (mech is not None and mech.suppression) else None
    damage = np.zeros(n)

    for s in (BLUE, RED):
        shooters = ent.alive & (ent.side == s)
        if not shooters.any():
            continue
        si = np.nonzero(shooters)[0]
        rng_gate = ent.weapon_range[si][:, None]
        d_real = cdist(shooter_pos[si], real_pos)                     # (S, N)
        eng_real = ((ent.side[None, :] != s) & ent.alive[None, :] & tracks.live[None, :]
                    & (ent.domain[None, :] == GROUND) & (d_real <= rng_gate))
        d_real = np.where(eng_real, d_real, np.inf)
        if m:
            fsel = tracks.flive & (tracks.fside == s)
            d_false = cdist(shooter_pos[si], false_pos)               # (S, M)
            d_false = np.where(fsel[None, :] & (d_false <= rng_gate), d_false, np.inf)
        else:
            d_false = np.full((si.size, 0), np.inf)
        d_all = np.hstack([d_real, d_false])
        has = np.isfinite(d_all).any(axis=1)
        pick = np.argmin(d_all, axis=1)
        for r in np.nonzero(has)[0]:
            shooter = int(si[r])
            if mech is not None and mech.munitions and ent.ammo[shooter] <= 0.0:
                continue                                              # out of rounds: no shot fired
            p = int(pick[r])
            if p < n:                                                 # real target
                cover = world.cover_at(real_pos[p:p + 1, 0], real_pos[p:p + 1, 1])[0]
                pk = ent.pk_base[shooter] * (1.0 - cover) * tracks.conf[p]
                if q is not None:
                    pk = pk * q[shooter] * (2.0 - q[p])
                if mech is not None and mech.suppression:            # suppressed shooter aims worse
                    pk = pk * (1.0 - mech.supp_fire * supp0[shooter])
                if rng.random() < min(max(pk, 0.0), 1.0):
                    damage[p] += 1.0
                if mech is not None and mech.suppression:            # being fired on suppresses target
                    ent.suppression[p] = min(ent.suppression[p] + mech.supp_gain, 1.0)
            # else: decoy -> shot wasted, no damage
            if mech is not None and mech.munitions:
                ent.ammo[shooter] -= 1.0                             # a round was fired (real or decoy)
    ent.hp = ent.hp - damage
    ent.alive = ent.alive & (ent.hp > 0.0)
