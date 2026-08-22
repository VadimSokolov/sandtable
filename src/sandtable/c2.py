"""Two-tier command and control: one operator supervising N autonomous agents.

The mission's control quality, not its physics, is what span-of-control and comms
degradation act on. Each blue agent periodically hits a *decision event* (a
contact or a route fork). How well that decision is resolved sets the agent's
per-step `control_quality` in [0, 1], which the motion and engagement kernels read
as a neutral-at-1.0 multiplier (well-controlled agents keep tempo, shoot well, and
expose themselves less; poorly-controlled agents stall and blunder).

Two control modalities (scenario param `control_mode`):

Decision events arrive at a jittered fixed rate by default. With ``terrain_demand`` set they
arrive faster on difficult ground, which makes the offered load *spatially correlated*: a column
entering a defile calls for help together rather than independently, and a queue sized for the
average rate meets a burst. That coupling is what connects terrain to the teaming loop rather than
only to the movement loop.

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
``queue_discipline`` is the separate question of what *order* it works its arrivals in; because
every requester carries the same patience, order can change which vehicle is helped but never how
many are, so the priority arms key on terrain rather than on the request itself.

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


# Service orders the operator can work its arrivals in (CR-16). `fcfs` is the published behavior
# and the default. `random` exists as the NULL CONTROL: reordering the loop also reassigns which
# entity draws which random number, so a priority arm moves two things at once; `random` moves only
# the RNG assignment. `easy_first` is the adversarial control for `hard_first`.
DISCIPLINES = ("fcfs", "random", "hard_first", "easy_first")


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
    terrain_demand: float = 0.0    # >0 makes difficult ground raise the call-for-help rate (CR-15)
    queue_discipline: str = "fcfs"  # "fcfs" | "random" | "hard_first" | "easy_first"; see `step`
    # Closed-loop reliance (CR-17). A vehicle that asked for help and did not get it does not
    # necessarily settle into autonomy for a full decision interval: an operator-reliant one asks
    # again sooner. `retry_prob` is the fraction of abandoned requests that come back on the short
    # `retry_backoff` instead of the standing `decision_interval`. This is the only mechanism in
    # the model whose demand depends on its own recent failures, and it is what turns the queue's
    # mean loss into a bistable one. Off by default: retry_prob = 0 draws nothing.
    retry_prob: float = 0.0
    retry_backoff: int = 0         # resolved to decision_interval in `build_c2` when unset
    retry_spread: int = -1         # <0 keeps the rescale; >=0 sets the backoff jitter in steps
    retry_pending: np.ndarray = None   # set at abandonment, read when the hold expires
    n_retry: int = 0
    # Late-window request accounting (CR-17). Whole-mission goodput averages over the transient,
    # which is exactly the thing a hysteresis question is about: it cannot tell "the jam hurt while
    # it was on" from "the jam left the team somewhere else". These count only the final quarter of
    # the mission, after any declared jam window has closed. Counters, no RNG, nothing reads them
    # back, so the OFF path is untouched.
    late_from: int = 1 << 30       # first step counted as late; set in `build_c2`
    n_request_late: int = 0
    n_serviced_late: int = 0
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
        terrain_demand=float(scn.params.get("terrain_demand", 0.0)),
        queue_discipline=str(scn.params.get("queue_discipline", "fcfs")),
        retry_prob=float(scn.params.get("retry_prob", 0.0)),
        retry_pending=np.zeros(ent.n, dtype=bool),
    )
    _dt = float(scn.params.get("dt", 1.0))
    op.late_from = int(0.75 * max(int(scn.duration / _dt), 1))
    _rb = int(scn.params.get("retry_backoff", -1))
    op.retry_backoff = op.decision_interval if _rb < 0 else _rb
    if not 0.0 <= op.retry_prob <= 1.0:
        raise ValueError(f"retry_prob must lie in [0, 1], got {op.retry_prob}")
    if op.retry_backoff < 1:
        raise ValueError(f"retry_backoff must be at least 1 step, got {op.retry_backoff}")
    op.retry_spread = int(scn.params.get("retry_spread", -1))
    if op.retry_spread > op.retry_backoff + op.decision_interval:
        raise ValueError(f"retry_spread {op.retry_spread} exceeds anything the standing interval "
                         f"could produce; the floor at one step would shift the mean")
    if op.queue_policy not in ("blind", "refund", "admit"):
        raise ValueError(f"queue_policy must be blind|refund|admit, got {op.queue_policy!r}")
    if op.queue_discipline not in DISCIPLINES:
        raise ValueError(f"queue_discipline must be one of {sorted(DISCIPLINES)}, "
                         f"got {op.queue_discipline!r}")
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


def _backoff(op: "Operator", cool: int) -> int:
    """Map the standing jittered interval onto the shorter backoff, without a second draw.

    The default rescales, which is what CR-17 shipped. Rescaling shrinks the ABSOLUTE jitter by
    `rho/tau` along with the mean: a backoff of 4 against an interval of 22 leaves a spread of
    about 4 steps where the standing cycle had 22. So a retry does two things at once and the
    published result cannot tell them apart. It shortens the cycle, which is what opens the fold
    band, and it also strips out five sixths of the jitter that keeps vehicles a common outage
    dropped together from coming back together.

    `retry_spread` separates them. Set it and the backoff is `rho + s*u`, with `u` the same drawn
    integer mapped onto [-1, 1], so the MEAN is held at `rho` while the jitter width is set
    independently. `s = 0` returns every retrying vehicle after exactly `rho` steps, the strongest
    possible cohort; `s = tau/2` gives the retry the same absolute spread as the standing cycle.
    Exactly one integer is drawn either way, so the arms stay paired on a shared seed.

    With `terrain_demand` on, `_reset_cooldown` may compress `cool` below `lo`, which puts `u`
    under -1. The floor at one step absorbs it; no cell reported here runs both at once.
    """
    if op.retry_spread < 0:
        return max(1, int(round(cool * op.retry_backoff / op.decision_interval)))
    lo = max(1, op.decision_interval // 2)
    hi = max(lo + 1, op.decision_interval * 3 // 2)
    u = 2.0 * (cool - lo) / (hi - lo) - 1.0
    return max(1, int(round(op.retry_backoff + op.retry_spread * u)))


def _reset_cooldown(op: Operator, rng: np.random.Generator, difficulty: float = 0.0) -> int:
    """A jittered inter-decision interval so agents desynchronize (queue contention).

    With `terrain_demand` on, the interval shortens on difficult ground (CR-15): a vehicle
    picking its way through a defile calls for help more often than one on a road. Exactly one
    integer is drawn either way, so the OFF path is byte-identical and the two paths stay paired
    on a shared seed.
    """
    lo = max(1, op.decision_interval // 2)
    hi = max(lo + 1, op.decision_interval * 3 // 2)
    c = int(rng.integers(lo, hi + 1))
    if op.terrain_demand > 0.0 and difficulty > 0.0:
        c = max(1, int(round(c / (1.0 + op.terrain_demand * difficulty))))
    return c


def _arm_retry(op: Operator, rng: np.random.Generator, i: int) -> None:
    """Mark an abandoned requester to come back on the short backoff (CR-17).

    The coin is drawn at ABANDONMENT rather than at re-arm so that a request which is still
    outstanding carries no pending draw, and so that `retry_prob = 0` draws nothing at all and
    leaves the stream where it was.
    """
    if op.retry_prob <= 0.0:
        return
    if rng.random() < op.retry_prob:
        op.retry_pending[i] = True
        op.n_retry += 1


def service_order(op: Operator, blue: np.ndarray, difficulty: dict,
                  rng: np.random.Generator) -> np.ndarray:
    """The order the operator works this tick's arrivals in (CR-16).

    `fcfs` returns `blue` untouched, which is what keeps the default path byte-identical.

    Ordering cannot change how MANY requests the operator serves. Every requester carries the same
    patience and a request's completion time is fixed at arrival, so reordering two feasible
    requests only swaps which vehicle is served. What ordering can change is whether the vehicle
    that gets helped is one for which operator quality is worth much, which is why the priority
    arms key on the ground under the vehicle rather than on anything intrinsic to the request.

    The priority sorts are stable, so vehicles on identical ground keep their index order and the
    discipline degenerates to `fcfs` rather than to an arbitrary permutation. That is what makes a
    null result on uniform terrain interpretable instead of merely noisy.
    """
    if op.queue_discipline == "random":
        return rng.permutation(blue)
    if op.queue_discipline in ("hard_first", "easy_first") and difficulty:
        sign = -1.0 if op.queue_discipline == "hard_first" else 1.0
        keys = np.array([sign * difficulty.get(int(i), 0.0) for i in blue])
        return blue[np.argsort(keys, kind="stable")]
    return blue


def step(ent: Entities, op: Operator, comms: Comms, scn: Scenario, k: int,
         rng: np.random.Generator, world=None) -> None:
    """Advance the C2 queue/latency model one tick and write ent.control_quality in place.

    `world` is read only when the scenario opts into `terrain_demand` or into a terrain-keyed
    `queue_discipline`; without it the demand process is the stationary one this model has always
    had and the service order is arrival order.
    """
    blue = np.nonzero((ent.side == BLUE) & ent.alive)[0]

    # Terrain difficulty, when demand is terrain-driven or the service order keys on it. `speed`
    # is a trafficability multiplier in [0, 1], so 1 - speed is how hard the ground is under each
    # vehicle right now. Reading the terrain draws no random numbers, so widening the condition
    # cannot perturb the RNG stream of any arm that does not use the result.
    needs_difficulty = op.terrain_demand > 0.0 or op.queue_discipline in ("hard_first", "easy_first")
    if needs_difficulty and world is not None and blue.size:
        diff = np.clip(1.0 - world.speed_at(ent.x[blue], ent.y[blue]), 0.0, 1.0)
        difficulty = dict(zip(blue.tolist(), diff.tolist()))
    else:
        difficulty = {}

    blue = service_order(op, blue, difficulty, rng)

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
            cool = _reset_cooldown(op, rng, difficulty.get(i, 0.0))
            if op.retry_pending[i]:
                cool = _backoff(op, cool)
                op.retry_pending[i] = False
            ent.decision_cooldown[i] = cool
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
            ent.decision_cooldown[i] = _reset_cooldown(op, rng, difficulty.get(i, 0.0))
            continue

        # direct control: request the operator over the link. Both link types draw the same two
        # Bernoulli message-survival values, so the RNG stream stays aligned and the OFF path is
        # byte-identical. An EW-immune link (fiber / autonomous terminal guidance) ignores the drops
        # and rides a fixed low latency off the comms ladder; the single operator is still a shared
        # server, so span-of-control contention remains the residual limit.
        lat = op.immune_latency if op.ew_immune else comms.latency
        up_ok = comms.delivered(rng)
        # Read the queue before pricing the reply. The reply is not sent when the request is: it
        # leaves when the operator finishes, so the two messages are separated by `done - k` steps,
        # and on a channel with memory that gap is what decides whether their fates are correlated
        # (CR-18). Reading the queue consumes no randomness, so moving it above the second draw
        # leaves the stream exactly where it was.
        recv = k + lat                                        # request reaches operator
        if op.crew_free_at is None:
            console = -1
            start = max(op.operator_free_at, recv)            # single shared server
        else:
            console = int(np.argmin(op.crew_free_at))         # earliest-free console (CR-14)
            start = max(op.crew_free_at[console], recv)
        done = start + 1.0 / op.service_rate                  # operator finishes this decision
        reply = done + lat                                    # reply travels back
        down_ok = comms.reply_survives(rng, done - k)
        link_ok = op.ew_immune or (up_ok and down_ok)
        op.n_request += 1
        late = k >= op.late_from
        if late:
            op.n_request_late += 1
        if link_ok:
            wait = reply - k
            if wait <= op.patience:
                _claim(op, console, done)
                ent.await_until[i] = int(math.ceil(reply))
                op.resolved_quality[i] = op.q_operator
                op.waits.append(float(wait))          # attention-switching wait, serviced only
                op.n_serviced += 1
                if late:
                    op.n_serviced_late += 1
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
                # Under `admit` the refusal rides the link home, so the agent learns at
                # `2*lat`. On a slow enough link that is LATER than the agent's own patience
                # timer, at which point it has already given up unaided: capping at `patience`
                # keeps admission control from ever being worse than not being told. Without the
                # cap, C5 (one-way latency 16) would hold an agent 32 steps against a patience of
                # 20. No published number changes, because every gated cell runs at C0 or C2.
                hold = min(2 * lat, op.patience) if op.queue_policy == "admit" else op.patience
                ent.await_until[i] = k + hold                 # gives up waiting -> poor autonomy
                op.resolved_quality[i] = op.q_fallback
                op.n_abandon_queue += 1
                _arm_retry(op, rng, i)
        else:
            ent.await_until[i] = k + op.patience              # message dropped -> poor autonomy
            op.resolved_quality[i] = op.q_fallback
            op.n_abandon_link += 1
            _arm_retry(op, rng, i)

        ent.control_quality[i] = op.q_stall                   # now awaiting
