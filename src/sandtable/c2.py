"""Two-tier command and control: one operator supervising N autonomous agents.

The mission's control quality, not its physics, is what span-of-control and comms
degradation act on. Each blue agent periodically hits a *decision event* (a
contact or a route fork). How well that decision is resolved sets the agent's
per-step `control_quality` in [0, 1], which the motion and engagement kernels read
as a neutral-at-1.0 multiplier (well-controlled agents keep tempo, shoot well, and
expose themselves less; poorly-controlled agents stall and blunder).

Two control modalities (scenario param `control_mode`):

- ``supervisory`` (human-on-the-loop): the agent decides locally and immediately
  at quality ``q_auto`` (~0.7). No queue, no wait; comms degradation is almost
  irrelevant. Quality is steady but mediocre.
- ``direct`` (human-in-the-loop): the agent requests the operator and waits. The
  operator is a *single shared server* (``service_rate`` decisions/step) across all
  N agents, and the request pays a comms round trip (``2*latency``) and may be
  dropped. A serviced decision is high quality (``q_operator``, ~0.95); while
  waiting the agent sits at the low ``q_stall`` (~0.30); if the wait exceeds
  ``patience`` (or the message is dropped) the agent falls back to autonomous
  ``q_auto``. So direct control is excellent when comms are clean and N is small,
  and collapses as latency/drop and queue contention grow: the crossover the
  span-of-control study is built to expose.

The single shared server is the span-of-control coupling: more agents means a
longer queue, so the crossover to supervisory arrives at a milder jamming level.

Deterministic given (rng, state); no globals. Only living blue agents are managed;
red and air agents keep the neutral control_quality 1.0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from sandtable.comms_ew import Comms
from sandtable.entities import BLUE, Entities
from sandtable.scenario import Scenario


@dataclass
class Operator:
    mode: str                     # "direct" | "supervisory"
    service_rate: float           # operator decisions serviced per step (direct only)
    q_operator: float             # attention-diluted quality of an operator-serviced decision
    q_auto: float                 # control quality of a supervisory-autonomous decision
    q_fallback: float             # control quality of a DIRECT-mode agent forced autonomous
    q_stall: float                # control quality while awaiting a pending request
    patience: int                 # steps an agent waits before giving up -> fallback
    decision_interval: int        # mean steps between an agent's decision events
    operator_free_at: float = 0.0  # step at which the single server clears its queue
    resolved_quality: np.ndarray = field(default=None)  # per-agent between-decision quality


def build_c2(scn: Scenario, ent: Entities) -> Operator | None:
    """Build the operator model, or None if the scenario declares no C2 layer."""
    mode = scn.params.get("control_mode")
    if mode is None:
        return None
    if mode not in ("direct", "supervisory"):
        raise ValueError(f"control_mode must be 'direct' or 'supervisory', got {mode!r}")
    q_operator = float(scn.params.get("q_operator", 0.95))
    q_auto = float(scn.params.get("q_auto", 0.70))
    # Attention dilution (span-of-control on decision QUALITY, separate from queue latency):
    # one operator fully attends up to `span_capacity` agents; beyond that the per-decision
    # quality decays toward q_auto as attention spreads thin over the team.
    span_capacity = float(scn.params.get("span_capacity", 4.0))
    n_span = max(int((ent.side == BLUE).sum()), 1)
    attention = min(1.0, span_capacity / n_span)
    q_operator_eff = q_auto + (q_operator - q_auto) * attention
    op = Operator(
        mode=mode,
        service_rate=float(scn.params.get("service_rate", 0.5)),
        q_operator=q_operator_eff,
        q_auto=q_auto,
        q_fallback=float(scn.params.get("q_fallback", 0.50)),
        q_stall=float(scn.params.get("q_stall", 0.30)),
        patience=int(scn.params.get("patience", 20)),
        decision_interval=int(scn.params.get("decision_interval", 30)),
        resolved_quality=np.full(ent.n, q_auto),
    )
    return op


def _reset_cooldown(op: Operator, rng: np.random.Generator) -> int:
    """A jittered inter-decision interval so agents desynchronize (queue contention)."""
    lo = max(1, op.decision_interval // 2)
    hi = max(lo + 1, op.decision_interval * 3 // 2)
    return int(rng.integers(lo, hi + 1))


def step(ent: Entities, op: Operator, comms: Comms, scn: Scenario, k: int,
         rng: np.random.Generator) -> None:
    """Advance the C2 queue/latency model one tick and write ent.control_quality in place."""
    blue = np.nonzero((ent.side == BLUE) & ent.alive)[0]

    for i in blue:
        # 1) A pending request has come back: adopt its resolved quality, re-arm the cooldown.
        if ent.await_until[i] >= 0 and k >= ent.await_until[i]:
            ent.control_quality[i] = op.resolved_quality[i]
            ent.await_until[i] = -1
            ent.decision_cooldown[i] = _reset_cooldown(op, rng)
            continue

        # 2) Still awaiting a reply: sit at the low stall quality (hesitating without guidance).
        if ent.await_until[i] >= 0:
            ent.control_quality[i] = op.q_stall
            continue

        # 3) Not awaiting: count down to the next decision event.
        if ent.decision_cooldown[i] > 0:
            ent.decision_cooldown[i] -= 1
            continue

        # 4) A decision event fires now.
        if op.mode == "supervisory":
            ent.control_quality[i] = op.q_auto
            op.resolved_quality[i] = op.q_auto
            ent.decision_cooldown[i] = _reset_cooldown(op, rng)
            continue

        # direct control: request the operator over the (possibly jammed) link.
        up_ok = comms.delivered(rng)
        down_ok = comms.delivered(rng)
        if up_ok and down_ok:
            recv = k + comms.latency                          # request reaches operator
            start = max(op.operator_free_at, recv)            # single shared server
            done = start + 1.0 / op.service_rate              # operator finishes this decision
            op.operator_free_at = done
            reply = done + comms.latency                      # reply travels back
            wait = reply - k
            if wait <= op.patience:
                ent.await_until[i] = int(math.ceil(reply))
                op.resolved_quality[i] = op.q_operator
            else:
                ent.await_until[i] = k + op.patience          # gives up waiting -> poor autonomy
                op.resolved_quality[i] = op.q_fallback
        else:
            ent.await_until[i] = k + op.patience              # message dropped -> poor autonomy
            op.resolved_quality[i] = op.q_fallback

        ent.control_quality[i] = op.q_stall                   # now awaiting
