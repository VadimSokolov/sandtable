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

The shared server is the span-of-control coupling: more agents means a longer queue, so the
crossover to supervisory arrives at a milder jamming level. ``n_operators`` turns the single
operator into a crew of that many consoles, each serving at ``service_rate``, so the same study
answers a staffing question rather than only a span question. One console is the default and
reproduces the published single server exactly.

The server also has *abandonment*: a requester that has waited longer than
``patience`` stops caring about the answer. Whether the operator finds that out,
and what it does about it, is the ``queue_policy`` knob documented in `step`.

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
    operator_free_at: float = 0.0  # step at which the (first) server clears its queue
    crew_free_at: np.ndarray = None  # per-console free times when n_operators > 1 (CR-14)
    resolved_quality: np.ndarray = field(default=None)  # per-agent between-decision quality
    ew_immune: bool = False        # EW-immune command link (fiber / autonomous terminal guidance)
    immune_latency: int = 1        # fixed one-way latency of the immune link, off the comms ladder
    queue_policy: str = "blind"    # "blind" | "refund" | "admit"; see `step`
    # Request accounting (CR-10). Counts only, no RNG, so the OFF path stays byte-identical.
    n_request: int = 0             # direct-mode decision events that reached the link
    n_serviced: int = 0            # ... that came back with an operator decision
    n_abandon_queue: int = 0       # ... that reached the operator but could not be served in time
    n_abandon_link: int = 0        # ... that the link dropped
    decision_cooldown_seed: np.ndarray = None   # staggered starting phases, when opted in
    # Operator-load accumulators (CR-7). Read out by `metrics.compute`; every one of them is a
    # by-product of state this model already carried, so nothing here changes any decision.
    busy_steps: float = 0.0        # busy-console-steps; with one console this is a step count
    total_steps: int = 0
    queue_depth_sum: float = 0.0   # summed count of agents with a request outstanding
    waits: list = field(default_factory=list)   # per-serviced-request wait, in steps


def build_c2(scn: Scenario, ent: Entities,
             rng: np.random.Generator | None = None) -> Operator | None:
    """Build the operator model, or None if the scenario declares no C2 layer.

    `rng` is used only when the scenario opts into `stagger_decisions`; without it the RNG
    stream is untouched and every previously recorded number is reproduced exactly.
    """
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
        ew_immune=bool(scn.params.get("ew_immune_link", False)),
        immune_latency=int(scn.params.get("immune_latency", 1)),
        queue_policy=str(scn.params.get("queue_policy", "blind")),
    )
    if op.queue_policy not in ("blind", "refund", "admit"):
        raise ValueError(f"queue_policy must be blind|refund|admit, got {op.queue_policy!r}")
    n_operators = int(scn.params.get("n_operators", 1))
    if n_operators < 1:
        raise ValueError(f"n_operators must be at least 1, got {n_operators}")
    if n_operators > 1:
        # A crew of `c` consoles, each serving at `service_rate`. One console reproduces the
        # published single server exactly, which is why the array is only allocated above one.
        op.crew_free_at = np.zeros(n_operators)
    if scn.params.get("stagger_decisions") and rng is not None:
        # `decision_cooldown` starts at zero for every entity, so without this every agent's
        # first decision event fires on step 0 and the operator opens the mission with a
        # synchronized burst of n requests. Real vehicles are not phase-locked. Drawing a
        # uniform starting phase removes the startup transient; leaving it off reproduces the
        # published stream byte for byte, which is why it is opt-in rather than a fix.
        blue = np.nonzero(ent.side == BLUE)[0]
        op.decision_cooldown_seed = rng.integers(0, max(op.decision_interval, 1), size=blue.size)
        ent.decision_cooldown[blue] = op.decision_cooldown_seed
    return op


def _claim(op: Operator, console: int, done: float) -> None:
    """Mark the chosen console busy until `done`. Console -1 is the single-server path."""
    if console < 0:
        op.operator_free_at = done
    else:
        op.crew_free_at[console] = done


def _reset_cooldown(op: Operator, rng: np.random.Generator) -> int:
    """A jittered inter-decision interval so agents desynchronize (queue contention)."""
    lo = max(1, op.decision_interval // 2)
    hi = max(lo + 1, op.decision_interval * 3 // 2)
    return int(rng.integers(lo, hi + 1))


def step(ent: Entities, op: Operator, comms: Comms, scn: Scenario, k: int,
         rng: np.random.Generator) -> None:
    """Advance the C2 queue/latency model one tick and write ent.control_quality in place."""
    blue = np.nonzero((ent.side == BLUE) & ent.alive)[0]

    # Operator-load sampling (CR-7), taken before this tick's decisions are resolved.
    op.total_steps += 1
    if op.crew_free_at is None:
        if op.operator_free_at > k:
            op.busy_steps += 1
    else:
        # Fraction of consoles still clearing work, so utilization stays comparable across crews.
        op.busy_steps += float((op.crew_free_at > k).mean())
    op.queue_depth_sum += float((ent.await_until[blue] >= 0).sum()) if blue.size else 0.0

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

        # direct control: request the operator over the link. Both link types draw the same two
        # Bernoulli message-survival values, so the RNG stream stays aligned and the OFF path is
        # byte-identical. An EW-immune link (fiber / autonomous terminal guidance) ignores the drops
        # and rides a fixed low latency off the comms ladder; the single operator is still a shared
        # server, so span-of-control contention remains the residual limit.
        up_ok = comms.delivered(rng)
        down_ok = comms.delivered(rng)
        link_ok = op.ew_immune or (up_ok and down_ok)
        lat = op.immune_latency if op.ew_immune else comms.latency
        op.n_request += 1
        if link_ok:
            recv = k + lat                                    # request reaches operator
            if op.crew_free_at is None:
                console = -1
                start = max(op.operator_free_at, recv)        # single shared server
            else:
                console = int(np.argmin(op.crew_free_at))     # earliest-free console (CR-14)
                start = max(op.crew_free_at[console], recv)
            done = start + 1.0 / op.service_rate              # operator finishes this decision
            reply = done + lat                                # reply travels back
            wait = reply - k
            if wait <= op.patience:
                _claim(op, console, done)
                ent.await_until[i] = int(math.ceil(reply))
                op.resolved_quality[i] = op.q_operator
                op.waits.append(float(wait))          # attention-switching wait, serviced only
                op.n_serviced += 1
            else:
                # The request cannot come back inside the requester's patience, so its answer
                # will be thrown away. What the operator does with the slot, and whether the
                # requester is told, is `queue_policy` (CR-10):
                #   blind  -- the operator works the request anyway and the agent waits it out.
                #             The slot is spent on an answer nobody will use, which is what makes
                #             the queue collapse under its own offered load at large span.
                #   refund -- the operator silently drops work it cannot finish in time. The slot
                #             is freed for the next requester; the agent still waits out patience.
                #   admit  -- the operator refuses on arrival and the refusal rides the link home,
                #             so the agent goes autonomous after one round trip instead of after
                #             `patience` steps. Explicit admission control.
                if op.queue_policy == "blind":
                    _claim(op, console, done)
                hold = 2 * lat if op.queue_policy == "admit" else op.patience
                ent.await_until[i] = k + hold                 # gives up waiting -> poor autonomy
                op.resolved_quality[i] = op.q_fallback
                op.n_abandon_queue += 1
        else:
            ent.await_until[i] = k + op.patience              # message dropped -> poor autonomy
            op.resolved_quality[i] = op.q_fallback
            op.n_abandon_link += 1

        ent.control_quality[i] = op.q_stall                   # now awaiting
