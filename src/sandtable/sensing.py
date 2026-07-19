"""Detection and shared situational awareness: cookie-cutter range gate + a relayed SA picture.

For each entity, if any living opposing observer is within its sensor range (and LOS is clear), the
entity is detected with probability (1 - concealment at its location). Detections are per-step
("who is currently on the opposing side's shared picture"); engagement reads `ent.seen` to decide
who may be fired upon.

Shared-SA relay (Increment 3): a contact seen ONLY by an air (UAS) observer must be relayed to the
shared picture over the comms/EW link, so a jammed relay drops that contact; a contact also held
organically by a ground observer is unaffected. This is the recon-cueing effect the UC-5 sensor-swarm
scenario turns on: a UAS overwatch extends detection beyond the ground force's organic reach until
jamming denies the relay. With no air observers (the ground-core scenarios) the relay path is a
no-op and detection is byte-identical to the cookie-cutter baseline.

The cookie-cutter + concealment model is the standard mission-level abstraction (MANA, Gaertner
2013). An exponential glimpse-Pd and elevation-based LOS are the planned enhancements; the interface
(`step` updates `ent.seen` in place) stays fixed.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist

from sandtable.entities import AIR, GROUND, Entities
from sandtable.world import World


def step(ent: Entities, world: World, rng: np.random.Generator, comms=None) -> None:
    """Update `ent.seen` in place for this timestep.

    `comms` (a `sandtable.comms_ew.Comms`, optional) gates the air-relay path. It only has an effect when
    the scenario actually fields air observers; otherwise the result and the RNG stream are identical
    to the ground-core baseline.
    """
    n = ent.n
    if n == 0:
        return
    pos = np.column_stack([ent.x, ent.y])
    dist = cdist(pos, pos)                      # (N, N)

    alive = ent.alive
    opposing = ent.side[:, None] != ent.side[None, :]
    within = dist <= ent.sensor_range[:, None]  # observer o (row) can range target t (col)
    los_ok = world.los(ent.x[:, None], ent.y[:, None], ent.x[None, :], ent.y[None, :])
    observable = alive[:, None] & alive[None, :] & opposing & within & los_ok

    detected_by_any = observable.any(axis=0)    # per target column
    pd = 1.0 - world.conceal_at(ent.x, ent.y)   # concealment lowers detection probability
    base_hit = detected_by_any & (rng.random(n) < pd)

    # Air-relay gate: a contact held only by a UAS is lost from the shared picture if the (jammed)
    # relay drops it. No air observers => no extra draw => identical to the ground core.
    if comms is not None and bool((ent.domain == AIR).any()):
        air_only = (observable & (ent.domain[:, None] == AIR)).any(axis=0) & ~(
            observable & (ent.domain[:, None] == GROUND)
        ).any(axis=0)
        relay_lost = air_only & (rng.random(n) < comms.p_drop)
        ent.seen = base_hit & ~relay_lost
    else:
        ent.seen = base_hit
