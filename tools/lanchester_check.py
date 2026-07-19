"""Analytic cross-check: does SandTable's attrition kernel obey Lanchester's square law?

SandTable resolves fire as *aimed* fire: every living shooter engages its nearest detected
enemy with a per-step Bernoulli kill (engagement.py). When fire is distributed across the
opposing force, the expected kill rate on a side is proportional to the *number of opposing
shooters*, which is exactly the hypothesis of Lanchester's square law:

    dB/dt = -a R,   dR/dt = -b B,   with the invariant  b B^2 - a R^2 = const.

For equal effectiveness (a = b) the stronger side annihilates the weaker and its survivors are
B_inf = sqrt(B0^2 - R0^2). We isolate the engagement kernel (no movement, no terrain cover, both
sides mutually detected, intermixed so fire distributes) and compare the Monte-Carlo mean
survivors to that closed form. The sim tracks the square law to within about 5-9%, biased slightly
low (it predicts marginally more attrition than the idealized law) for two known and conservative
reasons: (i) simultaneous discrete-time resolution -- both sides fire on the pre-step force, so a
unit about to die still returns fire, an effect that vanishes as the per-step kill probability
shrinks; and (ii) finite overkill under nearest-target assignment -- the stronger side occasionally
concentrates fire on an already-doomed target. This is the defensibility check called for by
Gaertner (2013): a low-fidelity ABM should reproduce a recognized combat model.

    PYTHONPATH=src python tools/lanchester_check.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sandtable.entities import BLUE, GROUND, RED, Entities
from sandtable import engagement
from sandtable.world import World

OUT = Path("report/data/lanchester.csv")
PK = 0.01           # per-step kill probability (small -> continuous-time limit is accurate)
BOX = 150.0         # m; intermix both forces in a small box so nearest-enemy fire distributes
WEAPON = 5000.0     # m; everyone in range of everyone (kernel test, not a geometry test)
SENSOR = 5000.0
MAX_STEPS = 20000
REPS = 600
DUELS = [(10, 6), (12, 8), (16, 10), (20, 12), (20, 16), (30, 20)]


def _flat_world() -> World:
    z = np.zeros((4, 4))
    return World(size=(BOX * 2, BOX * 2), cell=BOX, speed=np.ones((4, 4)), cover=z, conceal=z)


def _make(b0: int, r0: int, rng: np.random.Generator) -> Entities:
    n = b0 + r0
    e = Entities.allocate(n)
    e.x[:] = rng.uniform(0.0, BOX, n)
    e.y[:] = rng.uniform(0.0, BOX, n)
    e.side[:b0] = BLUE; e.side[b0:] = RED
    e.domain[:] = GROUND
    e.hp[:] = 1.0
    e.alive[:] = True
    e.seen[:] = True                       # both sides mutually detected (kernel-only test)
    e.pk_base[:] = PK
    e.weapon_range[:] = WEAPON
    e.sensor_range[:] = SENSOR
    return e


def _run_once(b0: int, r0: int, world: World, rng: np.random.Generator) -> int:
    e = _make(b0, r0, rng)
    for _ in range(MAX_STEPS):
        e.seen[:] = True                   # keep mutual detection each step
        engagement.step(e, world, 1.0, rng)
        b = int((e.alive & (e.side == BLUE)).sum())
        r = int((e.alive & (e.side == RED)).sum())
        if b == 0 or r == 0:
            break
    return int((e.alive & (e.side == BLUE)).sum())


def main() -> None:
    world = _flat_world()
    rows = []
    for b0, r0 in DUELS:
        rng = np.random.default_rng(20260719 + b0 * 100 + r0)
        surv = np.mean([_run_once(b0, r0, world, rng) for _ in range(REPS)])
        lanch = float(np.sqrt(max(b0 ** 2 - r0 ** 2, 0.0)))
        rel = (surv - lanch) / max(lanch, 1e-9)
        rows.append(dict(B0=b0, R0=r0, sim_surv=round(surv, 3),
                         lanch_surv=round(lanch, 3), rel_err=round(rel, 4)))
        print(f"B0={b0:>2} R0={r0:>2} | sim={surv:5.2f}  square-law={lanch:5.2f}  "
              f"rel.err={rel*100:+5.1f}%")
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"\nmax |rel err| = {df.rel_err.abs().max()*100:.1f}%   ->  {OUT}")


if __name__ == "__main__":
    main()
