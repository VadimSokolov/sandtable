"""Counter-UAS / short-range air defense (SHORAD): attrition of the blue reconnaissance swarm.

Opt-in via ``params["cuas_rate"]`` (> 0). Off by default the layer is not built and the loop draws no
extra RNG, so every scenario without it stays byte-identical. On, red air defense engages the blue UAS
overwatch: each living airborne recon asset within reach of a living red defender is shot down per step
with a probability that RISES with the size of the committed swarm, because a larger, more detectable
formation cues and saturates the defense harder (a signature effect).

Why this gives an *interior* optimum in swarm size. A UAS is exposed for roughly the whole mission,
so with a constant per-step hazard ``p`` its survival over an ``E``-step engagement is ``(1-p)**E``.
Tie the hazard to the committed swarm size ``n0`` (``p = rate * n0**signature``, held constant by
keying on the *initial* count, not the dwindling live one, so it does not self-limit), and the
expected number of UAS still flying is ``n0 * (1-p)**E ~ n0 * exp(-rate*E * n0**signature)`` -- a curve
that peaks at an interior ``n0`` and falls away after. ``signature`` sets how sharp the fall is: at 1
the hazard is proportional to swarm size and the hump is broad; above 1 a massed formation is
disproportionately detectable (the calibrated signature exponent, not a modeled radar or magazine),
so the tail drops steeply. Coverage, and thus mission success, follows the surviving count: too few
UAS give thin coverage, too many are attrited faster than they can cue the ground force. That turns
the UC-5 sensor-swarm response from monotone-in-size (bigger is always better) into a hump.

Modeling honesty. This is a deliberately coarse stand-in, not a modeled weapon system. The "red
defender" is any living red unit (on UC-5 those are the anti-tank teams, not a dedicated SHORAD
element); a UAS is "exposed" simply by coming within ``reach`` of one; and the per-drone hazard is
set by the committed swarm size ``n0`` alone -- it is independent of the number and type of red
defenders present, and the superlinear ``signature`` is calibrated to produce the interior optimum,
not derived from search-radar or magazine physics. It answers "does a survivability cost bend the
UC-5 swarm curve", not "how would a specific air-defense system perform".

Deterministic given (rng, state); no globals. Mutates ``ent.alive`` in place.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.entities import AIR, BLUE, RED, Entities
from sandtable.scenario import Scenario


@dataclass
class CounterUAS:
    rate: float          # per-step kill probability against an exposed lone UAS (hazard scale)
    signature: float     # exponent: hazard ~ rate*n0**signature (>1 = massing is disproportionately lethal)
    reach: float         # a blue UAS is exposed if within this many metres of a living red defender
    n0: int              # committed (initial) blue UAS count -- fixes the hazard so it does not self-limit


def build_counter_uas(scn: Scenario, ent: Entities) -> CounterUAS | None:
    """Build SHORAD state, or None when the scenario does not opt in (then the sim is byte-identical)."""
    rate = float(scn.params.get("cuas_rate", 0.0))
    if rate <= 0.0:
        return None
    n0 = int((ent.side_mask(BLUE) & (ent.domain == AIR)).sum())   # committed swarm size, held constant
    return CounterUAS(
        rate=rate,
        signature=float(scn.params.get("cuas_signature", 2.0)),
        reach=float(scn.params.get("cuas_reach", 2500.0)),
        n0=n0,
    )


def step(ent: Entities, cuas: CounterUAS, rng: np.random.Generator) -> None:
    """Red air defense engages exposed blue UAS this tick; kills mutate ``ent.alive`` in place."""
    uas = np.nonzero(ent.alive & (ent.side == BLUE) & (ent.domain == AIR))[0]
    if uas.size == 0:
        return
    red = np.nonzero(ent.alive & (ent.side == RED))[0]
    if red.size == 0:
        return
    draws = rng.random(uas.size)                        # one draw per living UAS (count fixed by state)
    # Hazard keyed on the COMMITTED size n0 (not the live count), so it is constant over the engagement
    # and does not self-limit as the swarm thins -- a bigger commitment is a hotter, superlinear threat.
    p_kill = min(1.0, cuas.rate * cuas.n0 ** cuas.signature)
    rx, ry = ent.x[red], ent.y[red]
    for j, i in enumerate(uas):
        if draws[j] < p_kill and float(np.hypot(ent.x[i] - rx, ent.y[i] - ry).min()) <= cuas.reach:
            ent.alive[i] = False
