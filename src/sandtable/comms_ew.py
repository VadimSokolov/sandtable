"""Communications / EW degradation ladder (C0-C5).

Maps a scenario `comms_level` (0 = uncontested ... 5 = denied) to link quality:
one-way latency (in steps) and a per-message drop probability. Under DIRECT
control every operator<->agent decision pays this cost twice (request out, reply
back); under SUPERVISORY control only the rare exception channel does, which is
why supervisory degrades gracefully as jamming rises. The ladder point is
overridable through `scn.params` so the improve-loop can retune it without code
changes. Pure and data-only: a run stays a pure function of (scenario, seed).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.scenario import Scenario

# Default ladder: level -> (one-way latency in steps, per-message drop prob, label).
_LADDER = {
    0: (0, 0.00, "uncontested"),
    1: (1, 0.05, "nominal"),
    2: (2, 0.10, "degraded"),
    3: (4, 0.20, "contested"),
    4: (8, 0.35, "heavily-jammed"),
    5: (16, 0.55, "denied"),
}


@dataclass
class Comms:
    level: int
    latency: int          # one-way link latency, in steps
    p_drop: float         # per-message drop probability
    label: str

    def round_trip(self) -> int:
        """Steps for a request to reach the operator and the reply to return."""
        return 2 * self.latency

    def delivered(self, rng: np.random.Generator) -> bool:
        """Bernoulli message-survival draw (True = message not dropped)."""
        return bool(rng.random() >= self.p_drop)


def build_comms(scn: Scenario) -> Comms:
    """Build the Comms state for a scenario from `comms_level` (ladder + overrides)."""
    level = int(np.clip(scn.params.get("comms_level", 0), 0, 5))
    lat, drop, label = _LADDER[level]
    # Improve-loop overrides (retune the operating point without touching the ladder).
    lat = int(scn.params.get("comms_latency", lat))
    drop = float(scn.params.get("comms_p_drop", drop))
    return Comms(level=level, latency=lat, p_drop=drop, label=label)
