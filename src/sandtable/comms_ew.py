"""Communications / EW degradation ladder (C0-C5).

Maps a scenario `comms_level` (0 = uncontested ... 5 = denied) to link quality:
one-way latency (in steps) and a per-message drop probability. Under DIRECT
control every operator<->agent decision pays this cost twice (request out, reply
back); under SUPERVISORY control only the rare exception channel does, which is
why supervisory degrades gracefully as jamming rises. The ladder point is
overridable through `scn.params` so the improve-loop can retune it without code
changes.

Two channel models share that ladder (`scn.params["channel"]`):

- ``"bernoulli"`` (default): losses are independent per message, the memoryless
  model. This is the historical behaviour and is byte-identical to it.
- ``"gilbert_elliot"``: a two-state Markov chain (GOOD/BAD) whose losses arrive in
  *runs*, which is how real jamming behaves. The chain is calibrated so its
  stationary drop rate equals the ladder's ``p_drop`` at every rung, so the two
  channels differ **only** in burst structure and never in mean. Any result that
  moves between them is attributable to burstiness alone.

  The chain draws exactly one uniform per message, the same as the Bernoulli path,
  so the two channels stay aligned on a shared seed and their comparison is paired.

The Gilbert-Elliot chain carries state across draws, so a `Comms` instance is no
longer data-only. The state lives on the per-run instance built by `build_comms`,
never at module level, so `run_mission` remains a pure function of (scenario, seed).
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
    p_drop: float         # per-message drop probability (the ladder value, and the
                          # stationary drop rate of the Gilbert-Elliot chain)
    label: str
    channel: str = "bernoulli"   # "bernoulli" | "gilbert_elliot"
    p_gb: float = 0.0            # GOOD -> BAD transition probability
    p_bg: float = 0.0            # BAD  -> GOOD transition probability
    _bad: bool = False           # per-run chain state; never module level
    # Transient jam window (CR-17). The ladder is a STANDING condition: a scenario picks a rung
    # and lives on it for the whole mission. A jammer that sweeps through and lifts is a different
    # question, and it is the one that separates a system which recovers from one which does not.
    # `jam_start < 0` disables the window and `set_step` becomes a no-op, so every previously
    # recorded number is reproduced exactly.
    jam_start: int = -1
    jam_end: int = -1
    jam_latency: int = 0
    jam_p_drop: float = 0.0
    base_latency: int = 0
    base_p_drop: float = 0.0
    # Channel clock (CR-18). The Gilbert-Elliot chain advances one transition per MESSAGE, so a
    # request and its reply are adjacent in chain time even though the operator's whole service
    # delay separates them in mission time. That makes the handshake maximally correlated for a
    # coding reason rather than a physical one. `step` prices the reply on the chain's actual decay
    # over the elapsed lag instead. `message` is the default and leaves every recorded number
    # unchanged.
    clock: str = "message"
    _k: int = 0            # current mission step, set by `set_step`
    _last_k: int = 0       # step at which the chain was last resolved

    def reply_survives(self, rng: np.random.Generator, lag: float) -> bool:
        """Draw the reply's survival, given the request survived and `lag` steps have passed.

        One uniform, as `delivered` uses, so the stream stays aligned either way.

        For a two-state chain with second eigenvalue `lam = 1 - p_gb - p_bg`, the probability that
        a message sent `L` steps after a delivered one also survives is

            P = 1 - p * (1 - lam^L),

        which is `1 - p_gb` at `L = 1` (the adjacent case the message clock always assumes) and
        decays to the marginal `1 - p` as `L` grows, recovering an independent handshake. The
        round-trip delivery rate therefore runs from `(1-p)(1-p_gb)` down to `(1-p)^2` as the
        service delay outruns the channel's coherence.
        """
        if self.channel != "gilbert_elliot" or self.clock != "step":
            return self.delivered(rng)
        lam = max(0.0, 1.0 - self.p_gb - self.p_bg)
        keep = 1.0 - self.p_drop * (1.0 - lam ** max(1.0, float(lag)))
        return bool(rng.random() < keep)

    def set_step(self, k: int) -> None:
        """Put the link on its jammed or its standing parameters for step `k`."""
        self._k = k
        if self.jam_start < 0:
            return
        on = self.jam_start <= k < self.jam_end
        self.latency = self.jam_latency if on else self.base_latency
        self.p_drop = self.jam_p_drop if on else self.base_p_drop

    def round_trip(self) -> int:
        """Steps for a request to reach the operator and the reply to return."""
        return 2 * self.latency

    def delivered(self, rng: np.random.Generator) -> bool:
        """Message-survival draw (True = message not dropped). One uniform per call.

        Bernoulli: survival iff the draw clears the ladder drop rate.

        Gilbert-Elliot: the same single uniform advances the two-state chain, and the
        message is lost exactly when the chain sits in BAD afterwards. Because the
        chain's stationary BAD probability is set to ``p_drop`` (see `build_comms`),
        the long-run drop rate matches the Bernoulli channel rung for rung while the
        losses arrive in runs of mean length ``1 / p_bg``.
        """
        u = rng.random()
        if self.channel != "gilbert_elliot":
            return bool(u >= self.p_drop)
        if self.clock == "step":
            # Time-indexed chain (CR-18). Advance by the number of STEPS since the chain was last
            # resolved, not by one transition per message. Two requests four steps apart are then
            # four transitions apart however many other vehicles asked in between, and a chain that
            # is only consulted rarely has decayed toward stationarity by the time it is, which is
            # what a real fade does and what the message clock cannot represent.
            lam = max(0.0, 1.0 - self.p_gb - self.p_bg)
            # Gap of zero is not floored to one (CR-20). Two vehicles that transmit on the SAME
            # step are in one radio environment and must see one channel state: with `gap = 0` the
            # decay is 1, so `p_bad` is 1 if the chain is BAD and 0 if it is GOOD, and the second
            # caller inherits the first caller's outcome deterministically. Flooring the gap at one
            # instead forced a transition between them and decorrelated vehicles that share a fade,
            # which is the cross-vehicle half of burst structure and the half a queue feels most:
            # a synchronized outage idles the operator and then floods the console.
            decay = lam ** max(0, self._k - self._last_k)
            self._last_k = self._k
            p_bad = self.p_drop + (1.0 - self.p_drop) * decay if self._bad \
                else self.p_drop * (1.0 - decay)
            self._bad = u < p_bad
            return not self._bad
        self._bad = (u >= self.p_bg) if self._bad else (u < self.p_gb)
        return not self._bad


def build_comms(scn: Scenario) -> Comms:
    """Build the Comms state for a scenario from `comms_level` (ladder + overrides)."""
    level = int(np.clip(scn.params.get("comms_level", 0), 0, 5))
    lat, drop, label = _LADDER[level]
    # Improve-loop overrides (retune the operating point without touching the ladder).
    lat = int(scn.params.get("comms_latency", lat))
    drop = float(scn.params.get("comms_p_drop", drop))

    channel = str(scn.params.get("channel", "bernoulli"))
    p_gb = p_bg = 0.0
    if channel == "gilbert_elliot":
        # Calibrate the chain so its stationary BAD probability equals the ladder drop
        # rate: with mean bad-state dwell L we need p_bg = 1/L and, from
        # pi_bad = p_gb / (p_gb + p_bg) = drop,  p_gb = drop * p_bg / (1 - drop).
        # Same mean, different burst structure, which is the whole point of the contrast.
        burst = max(1.0, float(scn.params.get("ge_burst_len", 4.0)))
        p_bg = 1.0 / burst
        p_gb = 0.0 if drop >= 1.0 else drop * p_bg / (1.0 - drop)
    # Transient jam: `jam_window` = [start, end) in steps, `jam_level` the ladder rung to sit on
    # while it is open. The window is a Bernoulli-channel feature; a Gilbert-Elliot chain is
    # calibrated to a single stationary drop rate, so swapping that rate mid-run would leave the
    # chain's transition probabilities describing a channel it is no longer on.
    win = scn.params.get("jam_window")
    j_start = j_end = -1
    j_lat, j_drop = lat, drop
    if win is not None:
        if channel != "bernoulli":
            raise ValueError("jam_window requires the bernoulli channel; "
                             f"got channel={channel!r}")
        j_start, j_end = int(win[0]), int(win[1])
        if j_end <= j_start:
            raise ValueError(f"jam_window must be [start, end) with end > start, got {win!r}")
        j_level = int(np.clip(scn.params.get("jam_level", 5), 0, 5))
        j_lat, j_drop, _ = _LADDER[j_level]
        j_lat = int(scn.params.get("jam_latency", j_lat))
        j_drop = float(scn.params.get("jam_p_drop", j_drop))
    clock = str(scn.params.get("channel_clock", "message"))
    if clock not in ("message", "step"):
        raise ValueError(f"channel_clock must be 'message' or 'step', got {clock!r}")
    return Comms(level=level, latency=lat, p_drop=drop, label=label, clock=clock,
                 channel=channel, p_gb=p_gb, p_bg=p_bg,
                 jam_start=j_start, jam_end=j_end,
                 jam_latency=j_lat, jam_p_drop=j_drop,
                 base_latency=lat, base_p_drop=drop)
