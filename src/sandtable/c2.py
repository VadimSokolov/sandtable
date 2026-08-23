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
#
# `edf` and `patient_first` sort on the requester's own patience, which is a constant across the
# fleet until `patience_spread` is set and therefore a no-op until then: a stable sort on a
# constant key returns the identity permutation, so both arms are byte-identical to `fcfs` at
# spread zero. That is the point. The two rules are the prescriptions of two literatures that
# disagree about an overloaded server with abandonment, and the disagreement is only visible in a
# fleet whose members do not all wait the same length of time.
DISCIPLINES = ("fcfs", "random", "hard_first", "easy_first", "edf", "patient_first")


@dataclass
class Operator:
    mode: str                     # "direct" | "supervisory"
    service_rate: float           # operator decisions serviced per step (direct only)
    q_operator: float             # attention-diluted quality of an operator-serviced decision
    q_auto: float                 # control quality of a supervisory-autonomous decision
    q_fallback: float             # control quality of a DIRECT-mode agent forced autonomous
    q_stall: float                # control quality while awaiting a pending request
    patience: int                 # MEAN steps an agent waits before giving up -> fallback
    decision_interval: int        # mean steps between an agent's decision events
    # Per-vehicle patience, built by `_patience_vector`; a constant vector until
    # `patience_spread` is set, which is what keeps the published path byte-identical.
    patience_v: np.ndarray = field(default=None)
    operator_free_at: float = 0.0  # step at which the (first) server clears its queue
    crew_free_at: np.ndarray = None  # per-console free times when n_operators > 1 (CR-14)
    resolved_quality: np.ndarray = field(default=None)  # per-agent between-decision quality
    ew_immune: bool = False        # EW-immune command link (fiber / autonomous terminal guidance)
    immune_latency: int = 1        # fixed one-way latency of the immune link, off the comms ladder
    queue_policy: str = "blind"    # "blind" | "refund" | "admit"; see `step`
    terrain_demand: float = 0.0    # >0 makes difficult ground raise the call-for-help rate (CR-15)
    queue_discipline: str = "fcfs"  # see DISCIPLINES and `service_order`
    # `reserve` (default, and the published model) decides a request's fate at ARRIVAL: it reads
    # the console's free time, computes the reply, and either claims the slot or refuses on the
    # spot. That makes the console a reservation system rather than a queue, with two consequences
    # we did not see until CR-46 went looking for a discipline to test. There is nothing for a
    # discipline to order, since a request never waits in a place where it could be reordered; and
    # the admission test is made against a FORECAST of the console's own delay rather than against
    # the delay itself. `buffer` is the queue: an arrival joins a pending list, the console picks
    # from it when it frees, and the admission test is applied at the head with the delay known.
    queue_model: str = "reserve"   # "reserve" | "buffer"
    # A real console's backlog is bounded. `queue_capacity < 0` leaves it unbounded, which is the
    # default and the regime a newest-first discipline is most flattered by, since it never has to
    # account for the requests it starves. Zero is a meaningful setting and not a sentinel: it means
    # the console holds no backlog at all, serving a request only if it is free when the request
    # arrives, which is what the sizing rule prescribes on a slow enough link. A bound drops the
    # OLDEST pending request on overflow, the one purge a console can perform knowing nothing about
    # the requester: it needs its own receive clock, not the deadline field `refund` and `admit`
    # require.
    queue_capacity: int = -1
    n_dropped: int = 0             # buffer: requests pushed out of a full backlog
    pending: list = field(default_factory=list)   # buffer: [i, arrive, recv, deadline, seq]
    req_seq: np.ndarray = None     # buffer: per-vehicle request counter, for the staleness test
    n_stale: int = 0               # buffer: requests worked after their requester had moved on
    backlog_sum: float = 0.0       # buffer: pending length summed over steps
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
    retry_streak: np.ndarray = None    # consecutive unanswered requests, for the doubling rule
    retry_mode: str = "fixed"          # "fixed" | "double"
    # Cadence AIMD (CR-26). Under `admit` the operator emits an explicit refusal, which is a
    # congestion signal in the sense of Floyd and Fall. Nothing in the model consumed it: the
    # refused vehicle went autonomous sooner and then asked again on the same standing cadence, so
    # the signal changed one wait and never the offered load. `admit_response = "aimd"` makes the
    # vehicle consume it the way a TCP sender does, halving its own request rate on a refusal and
    # recovering additively on each answered request. Off by default; requires `queue_policy` to be
    # `admit`, because under the other two policies there is no signal to consume.
    # Waiting is priced FLAT by default: an asset at `q_stall` is no worse off on the twentieth
    # step of a wait than on the first. That is a modelling choice and it is load-bearing for the
    # backoff recommendation, because if waiting is cheap then not re-asking is free. `stall_decay`
    # prices the wait as escalating exposure instead: the stalled quality falls linearly toward a
    # floor over the requester's own patience window, so a vehicle stopped in contact is worse off
    # the longer it is left there. Zero by default, and zero reproduces the published model
    # exactly (CR-28).
    q_droop: float = 0.0           # serviced-decision quality lost at full utilization
    stall_decay: float = 0.0
    stall_floor: float = 0.0       # the quality a fully decayed waiter sits at
    admit_response: str = "none"       # "none" | "aimd"
    cadence_rate: np.ndarray = None    # per-vehicle request rate, 1.0 = the standing cadence
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
    # Summed count of LIVE supervised vehicles (CR-25/Q2). Operator goodput is a share of the
    # requests that arrived, and requests arrive from vehicles that are still alive, so a costly
    # mission relieves the console by destroying its own demand. Reporting the demand alongside the
    # goodput is the only way a staffing number read off a high-attrition trial can be discounted.
    supervised_sum: float = 0.0
    supervised_n0: int = 0         # the count on the first step, so the sum can be normalized
    # Arrival-burstiness instrument (CR-27). The damage a bursty link does to the console is not
    # in the marginal delivery rate, which is matched by construction, but in how the delivered
    # requests are spaced. The right statistic is the Fano factor of the DELIVERED UPLINK stream
    # counted in windows comparable to the channel's dwell; measured in windows shorter than the
    # dwell it reads near one and says nothing, which is how the first probe of it was wrong.
    # Accumulated in bins so no per-step array is kept. Off by default (window 0), and counting
    # consumes no randomness, so the OFF path is byte-identical.
    fano_window: int = 0
    # Collision multiplicity (CR-34). `fano_window` is the CHANNEL dwell; this window is the
    # SERVICE time, because the quantity the mechanism consumes is how many requests land
    # inside one service: k arrivals in a service window is k-1 forced waits. The Fano is a
    # variance and cannot say that; two streams with equal variance can differ in whether the
    # excess arrives as many small clusters or a few large ones.
    mult_window: int = 0
    _mult_bin: float = 0.0
    _mult_idx: int = 0
    _mult_sum: float = 0.0
    _mult_busy: int = 0                   # windows with at least one arrival
    _mult_peak: float = 0.0
    # Which vehicles arrived in the open window, as a bitmask. A window holding three requests
    # from three vehicles and one holding three from one vehicle have the same multiplicity and
    # opposite mechanisms: the first is the retry cohort this paper is about, the second is one
    # vehicle's own refusal echo bouncing inside a window shorter than its backoff. Counting
    # distinct senders separates them at no cost, because the mask is one integer.
    _mult_mask: int = 0
    _mult_dsum: float = 0.0
    # Busy windows holding at least 2, 3 and 4 DISTINCT senders. The console prices the tail and
    # not the mean: it serves one request and can hold `floor((P - 2*lat)/S)` more before the
    # requester's patience expires, so a window whose sender count stays inside that depth costs
    # nothing however crowded the average looks. The whole distribution is kept rather than a
    # single over-depth flag, because the depth depends on the rung and baking one rung's
    # arithmetic into the simulator would make the statistic un-reusable at another.
    _mult_ge2: int = 0
    _mult_ge3: int = 0
    _mult_ge4: int = 0
    _fano_bin: float = 0.0
    _fano_idx: int = 0
    _fano_n: int = 0
    _fano_sum: float = 0.0
    _fano_sumsq: float = 0.0
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
    op.retry_streak = np.zeros(ent.n, dtype=int)
    op.admit_response = str(scn.params.get("admit_response", "none"))
    op.fano_window = int(scn.params.get("fano_window", 0))
    # Default: one service time, rounded up, so the window is the thing it is meant to be
    # without the battery having to restate the service rate.
    mw = scn.params.get("mult_window")
    op.mult_window = int(mw) if mw is not None else 0
    op.q_droop = float(scn.params.get("q_droop", 0.0))
    if not 0.0 <= op.q_droop <= 1.0:
        raise ValueError(f"q_droop must lie in [0, 1], got {op.q_droop}")
    op.stall_decay = float(scn.params.get("stall_decay", 0.0))
    op.stall_floor = float(scn.params.get("stall_floor", 0.0))
    if not 0.0 <= op.stall_decay <= 1.0:
        raise ValueError(f"stall_decay must lie in [0, 1], got {op.stall_decay}")
    op.cadence_rate = np.ones(ent.n)
    op.req_seq = np.zeros(ent.n, dtype=int)
    # Heterogeneous patience (CR-46). A mixed fleet does not wait the same length of time: an air
    # vehicle orbiting a target has a long window before its request is stale, a ground vehicle
    # halted in contact has a short one. The guard is the `retry_spread` lesson applied in advance:
    # a spread that reaches the floor at one step no longer holds its mean, so the arm is rejected
    # on the realized mean rather than on the nominal width.
    _ps = int(scn.params.get("patience_spread", 0))
    if _ps < 0:
        raise ValueError(f"patience_spread must be at least 0, got {_ps}")
    op.patience_v = _patience_vector(ent.n, np.flatnonzero(ent.side == BLUE), op.patience,
                                    _ps, rng)
    if _ps > 0:
        _realized = float(op.patience_v[ent.side == BLUE].mean())
        if abs(_realized - op.patience) > 0.02 * max(op.patience, 1):
            raise ValueError(
                f"patience_spread {_ps} at patience {op.patience} delivers a realized fleet mean "
                f"of {_realized:.2f}, a {100 * (_realized - op.patience) / max(op.patience, 1):.0f}% "
                f"shift; the floor at one step has truncated the low tail. A dispersion arm must "
                f"hold its mean, so use patience_spread <= patience - 1")
    op.retry_mode = str(scn.params.get("retry_mode", "fixed"))
    if op.retry_mode not in ("fixed", "double"):
        raise ValueError(f"retry_mode must be 'fixed' or 'double', got {op.retry_mode!r}")
    if op.retry_spread >= 0:
        # The point of `retry_spread` is to vary the jitter WIDTH at a held mean, so an arm whose
        # realized mean has drifted is not the control it claims to be. Checking the width against
        # a bound is not enough: the hold is floored at one step, so rho = 4 with spread 12 sits
        # inside any width bound worth having and still delivers a mean of 5.8. The realized mean
        # is therefore computed over the full support and the arm is rejected on the mean itself.
        realized = backoff_mean(op)
        if abs(realized - op.retry_backoff) > 0.02 * max(op.retry_backoff, 1):
            raise ValueError(
                f"retry_spread {op.retry_spread} at retry_backoff {op.retry_backoff} delivers a "
                f"realized mean of {realized:.2f}, a {100 * (realized - op.retry_backoff) / max(op.retry_backoff, 1):.0f}% "
                f"shift; the floor at one step has truncated the low tail. A jitter arm must hold "
                f"its mean, so use retry_spread <= retry_backoff - 1 or state the arm's mean")
    if op.queue_policy not in ("blind", "refund", "admit"):
        raise ValueError(f"queue_policy must be blind|refund|admit, got {op.queue_policy!r}")
    if op.admit_response not in ("none", "aimd"):
        raise ValueError(f"admit_response must be none|aimd, got {op.admit_response!r}")
    if op.admit_response == "aimd" and op.queue_policy != "admit":
        raise ValueError("admit_response='aimd' needs queue_policy='admit'; the other policies "
                         "emit no refusal for the vehicle to respond to")
    op.queue_capacity = int(scn.params.get("queue_capacity", -1))
    op.queue_model = str(scn.params.get("queue_model", "reserve"))
    if op.queue_model not in ("reserve", "buffer"):
        raise ValueError(f"queue_model must be reserve|buffer, got {op.queue_model!r}")
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


def backoff_mean(op: "Operator") -> float:
    """The realized mean hold of a jitter arm, over the full support of the standing interval.

    A jitter arm exists to vary the width of the backoff at a fixed mean, and `_backoff` floors the
    hold at one step, so wide spreads truncate the low tail and silently raise the mean. Every arm
    that claims to be mean-matched is checked here by value rather than by an inequality on its
    width, and batteries print this number in their own registrations.
    """
    lo = max(1, op.decision_interval // 2)
    hi = max(lo, (3 * op.decision_interval) // 2)
    draws = range(lo, hi + 1)
    return sum(_backoff(op, c) for c in draws) / len(draws)


def _backoff(op: "Operator", cool: int, i_streak: int | None = None) -> int:
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
    if op.retry_mode == "double":
        # Adaptive backoff. Double the hold on each consecutive unanswered request and reset it on
        # service, capped at the standing interval so a retry never delays a vehicle longer than
        # not retrying would. This finds the floor without being told `n`, `d`, `mu` or `c`, pays
        # nothing while the team is healthy, and is the form real systems field; the point of it is
        # that it removes the number from the recommendation and leaves only the rule.
        k = max(1, int(op.retry_streak[i_streak])) if i_streak is not None else 1
        rho = min(float(op.decision_interval), op.retry_backoff * (2.0 ** (k - 1)))
        return max(1, int(round(cool * rho / op.decision_interval)))
    if op.retry_spread < 0:
        return max(1, int(round(cool * op.retry_backoff / op.decision_interval)))
    lo = max(1, op.decision_interval // 2)
    hi = max(lo + 1, op.decision_interval * 3 // 2)
    u = 2.0 * (cool - lo) / (hi - lo) - 1.0
    return max(1, int(round(op.retry_backoff + op.retry_spread * u)))


# Cadence AIMD constants (CR-26). A refusal halves the vehicle's request rate; each answered
# request adds back an eighth, so a vehicle needs eight good answers to undo one refusal. The floor
# caps the stretch at four times the standing cadence, which is the analogue of a minimum window.
_AIMD_BETA = 0.5
_AIMD_ALPHA = 0.125
_AIMD_FLOOR = 0.25


def _reset_cooldown(op: Operator, rng: np.random.Generator, difficulty: float = 0.0,
                    i: int | None = None) -> int:
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
    # Cadence AIMD (CR-26) stretches the interval by the reciprocal of the vehicle's own request
    # rate. Applied AFTER the draw, so the RNG stream is untouched and the OFF path is identical.
    if op.admit_response == "aimd" and i is not None:
        c = max(1, int(round(c / max(op.cadence_rate[i], _AIMD_FLOOR))))
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
        op.retry_streak[i] += 1
        op.n_retry += 1


def _patience_vector(n_ent: int, blue_idx: np.ndarray, mean: int, spread: int,
                     rng: np.random.Generator | None = None) -> np.ndarray:
    """Per-vehicle patience: a balanced spread about the mean, laid out on a side stream.

    The SET of values is fixed rather than drawn. A fleet whose patiences are sampled has a
    realized mean that wanders block to block, which puts a nuisance variance into a paired
    contrast whose entire subject is the second moment; and a real mixed fleet is not a sample,
    since a program knows it is flying vehicles that can sit and vehicles that cannot. The offsets
    run -spread..+spread in equal steps, so they sum to zero and the fleet mean is exactly `mean`
    in every replication. Because the collapse span of Equation nstar is LINEAR in patience, that
    makes the sweep a pure second-moment manipulation.

    What IS drawn is which vehicle gets which value. Laying the values out in index order would
    make the deadline order identical to the arrival order, since the operator walks its arrivals
    in index order, and `edf` would then be `fcfs` by construction rather than by measurement.
    The permutation comes from `rng.spawn`, a CHILD stream, so the parent's draws are untouched
    and a dispersed fleet and a uniform one see the same mission: every contrast in the sweep,
    including the one that reads the uniform arm against a dispersed one, stays paired.

    `spread = 0` returns a constant vector and spawns nothing, so every deadline discipline is a
    stable sort on a constant key and returns the identity permutation. The published path is
    reproduced exactly, not approximately.
    """
    v = np.full(n_ent, int(mean), dtype=int)
    m = int(blue_idx.size)
    if spread <= 0 or m < 2:
        return v
    offs = [spread * (2.0 * j / (m - 1) - 1.0) for j in range(m)]
    order = rng.spawn(1)[0].permutation(m) if rng is not None else np.arange(m)
    for slot, j in enumerate(order):
        v[int(blue_idx[slot])] = max(1, int(round(mean + offs[int(j)])))
    return v


def _pick(op: Operator, ready: list[int], rng: np.random.Generator,
          difficulty: dict) -> int:
    """Which pending request the freed console takes next.

    Under `reserve` a discipline can only permute requests that arrived on the same tick, because
    a request's slot is committed the instant it arrives. Here there is a real backlog, so the
    discipline is doing what its name says. The keys are the same ones `service_order` uses, read
    off the pending record rather than off the arrival order.
    """
    d = op.queue_discipline
    if d == "fcfs":
        return ready[0]                      # the list is append-ordered, so index 0 is the oldest
    if d == "random":
        return ready[int(rng.integers(len(ready)))]
    if d in ("edf", "patient_first"):
        sign = 1 if d == "edf" else -1
        return min(ready, key=lambda r: (sign * op.pending[r][3], r))
    if d in ("hard_first", "easy_first") and difficulty:
        sign = -1.0 if d == "hard_first" else 1.0
        return min(ready, key=lambda r: (sign * difficulty.get(int(op.pending[r][0]), 0.0), r))
    return ready[0]


def _trim(op: Operator, ent: Entities, k: int, rng: np.random.Generator) -> None:
    """Hold the backlog to `queue_capacity` by dropping the OLDEST pending request.

    The choice of victim is the whole content of the knob. Dropping the oldest is the purge a
    console can perform on its own clock, without the requester's deadline travelling in the
    message, and it is therefore a weaker information requirement than `refund` or `admit`. It is
    also the purge that most helps first-come-first-served and least helps newest-first, since
    newest-first was never going to reach those requests anyway, so a bound is the adversarial test
    of a newest-first recommendation rather than a friendly one.
    """
    if op.queue_capacity < 0:
        return
    # The bound is on the console's buffer, which holds what has ARRIVED. A request still in flight
    # is not occupying anything the console owns, and counting it would make a capacity of zero mean
    # "serve nothing" on any link with latency, which is a different and much stronger policy than
    # the sizing rule prescribes.
    while True:
        here = [r for r, rec in enumerate(op.pending) if rec[2] <= k]
        if len(here) <= op.queue_capacity:
            return
        i, arrive, _recv, _deadline, _seq = op.pending.pop(here[0])
        op.n_dropped += 1
        op.n_abandon_queue += 1
        _give_up(op, ent, int(i), arrive, int(op.patience_v[int(i)]), rng)


def _give_up(op: Operator, ent: Entities, i: int, arrive: float, hold: int,
             rng: np.random.Generator) -> None:
    """A request that will not be answered in time. The requester falls back to autonomy `hold`
    steps after it asked, which is one round trip under `admit` and its full patience otherwise."""
    ent.await_until[i] = int(arrive) + int(hold)
    op.resolved_quality[i] = op.q_fallback
    _arm_retry(op, rng, i)


def _drain_buffer(op: Operator, ent: Entities, comms: Comms, k: int,
                  rng: np.random.Generator, difficulty: dict) -> None:
    """Work the backlog for one step, under `queue_model = "buffer"`.

    This is the part of a console that `reserve` does not have. A freed operator looks at what is
    actually waiting, applies `queue_policy` to the HEAD rather than to the arrival, and only then
    chooses by `queue_discipline`. Three differences follow, and all three are why the arm exists:

    * The admission test uses the delay the request has actually suffered rather than a forecast of
      it. Under `reserve` the console reads `operator_free_at`, which is a perfect prediction of its
      own queueing delay; here it reads the clock.
    * A request can wait, so a discipline has something to order.
    * `blind` means what it says: the console works the head even when the answer will be discarded,
      and the slot is gone. That is also where a STALE request comes from, since a requester whose
      patience ran out re-arms and asks again while its first request is still in the buffer. The
      console cannot tell, spends the slot, and the answer lands on a request nobody is holding any
      more. `reserve` cannot represent that at all, and it is the sharpest form of the waste the
      whole paper is about.

    Consoles are worked in index order, which reproduces `reserve`'s `argmin` over free times when
    they are all free and is a documented tie-break when they are not.
    """
    lat = op.immune_latency if op.ew_immune else comms.latency
    svc = 1.0 / op.service_rate
    # There is deliberately no background reaper. A console that swept its whole backlog every
    # step and released every expired requester would be a STRONGER console than the one being
    # modelled: it would be refusing work it has not looked at yet. Admission control here happens
    # where a person's does, at the head, when the console picks the request up. The cost is that
    # an expired request occupies the queue until the console reaches it, and its requester waits
    # out its full patience, which is the honest consequence of the policy and not an artifact.
    n_con = 1 if op.crew_free_at is None else int(op.crew_free_at.size)
    for console in range(n_con):
        c = -1 if op.crew_free_at is None else console
        while op.pending:
            free_at = op.operator_free_at if c < 0 else op.crew_free_at[c]
            # The console frees at a fractional time, because one service is 1/mu steps and 1/mu
            # is not an integer. Dispatching only at integer steps would round every service up and
            # cost real capacity: at mu = 0.15 the console would deliver 1/7 rather than 0.15, a
            # four percent capacity cut that has nothing to do with queueing. The condition is
            # therefore "frees before this step ends", and the start is the fractional free time.
            if free_at >= k + 1:
                break
            ready = [r for r, rec in enumerate(op.pending) if rec[2] <= k]
            if not ready:
                break
            r = _pick(op, ready, rng, difficulty)
            i, arrive, recv, deadline, seq = op.pending.pop(r)
            i = int(i)
            # A request still in flight is not the console's to work, which is what makes latency
            # cost throughput here and not only delay.
            start = max(float(free_at), float(recv))
            reply = start + svc + lat
            if reply > deadline and op.queue_policy != "blind":
                # Head-of-line admission control against the delay this console actually has. No
                # service time is claimed, so the next request is considered on the same step.
                op.n_abandon_queue += 1
                if op.admit_response == "aimd":
                    op.cadence_rate[i] = max(_AIMD_FLOOR, op.cadence_rate[i] * _AIMD_BETA)
                hold = min(2 * lat, int(op.patience_v[i])) if op.queue_policy == "admit" \
                    else int(op.patience_v[i])
                _give_up(op, ent, i, arrive, hold, rng)
                continue
            _claim(op, c, start + svc)               # the slot is spent from here on, always
            stale = seq != op.req_seq[i]
            down_ok = comms.reply_survives(rng, svc)
            if stale:
                op.n_stale += 1                       # worked, and nobody is holding it
                continue
            if not down_ok:
                op.n_abandon_link += 1
                _give_up(op, ent, i, arrive, int(op.patience_v[i]), rng)
                continue
            if reply > deadline:                      # `blind` only: worked, and answered too late
                op.n_abandon_queue += 1
                _give_up(op, ent, i, arrive, int(op.patience_v[i]), rng)
                continue
            ent.await_until[i] = int(math.ceil(reply))
            q = op.q_operator
            if op.q_droop > 0.0:
                util = op.busy_steps / max(op.total_steps, 1)
                q = op.q_operator - op.q_droop * util * (op.q_operator - op.q_auto)
            op.resolved_quality[i] = q
            op.waits.append(float(reply - arrive))
            op.n_serviced += 1
            op.retry_streak[i] = 0
            if op.admit_response == "aimd":
                op.cadence_rate[i] = min(1.0, op.cadence_rate[i] + _AIMD_ALPHA)
            if arrive >= op.late_from:
                op.n_serviced_late += 1


def service_order(op: Operator, blue: np.ndarray, difficulty: dict,
                  rng: np.random.Generator) -> np.ndarray:
    """The order the operator works this tick's arrivals in (CR-16).

    `fcfs` returns `blue` untouched, which is what keeps the default path byte-identical.

    An earlier version of this docstring said ordering cannot change how many requests the operator
    serves, because every requester carries the same patience. That is wrong twice over and both
    errors are worth leaving on the record, because the wrong version is the intuitive one.

    It is wrong as queueing. Under a common deadline, first-come-first-served already IS
    earliest-deadline-first, which is the order that maximizes the number of deadlines met, so a
    worse order does not reshuffle the beneficiaries: it strands earlier arrivals past their
    deadlines and serves FEWER. Ordering changes how many, downward.

    And it names the wrong reason for the null it was explaining. Under `queue_model = "reserve"`
    a request is committed to a slot at ARRIVAL, so nothing ever waits in a place where it could
    be reordered and a discipline can only permute requests that arrive on the same step. That is
    a property of this simulator, not of consoles, and `queue_model = "buffer"` is the arm that
    removes it.

    `patience_spread` removes the assumption. Once requesters carry different deadlines, ordering
    changes the COUNT, because a short-deadline request placed late in the tick no longer fits and
    a long-deadline one placed late still does. `edf` serves the earliest deadline first, which is
    the shortest remaining patience; `patient_first` serves the longest, which is the cmu/theta
    prescription of Atar, Giat and Shimkin for a many-server queue with abandonment. The two rules
    are exact opposites and they come from literatures that assume different information: cmu/theta
    is derived where the server sees an abandonment HAZARD, deadline scheduling where it sees the
    DEADLINE. A console running admission control has already assumed the second, because
    `wait <= patience` is that test, so this model should sit in the deadline regime.

    The priority sorts are stable, so vehicles on identical ground keep their index order and the
    discipline degenerates to `fcfs` rather than to an arbitrary permutation. That is what makes a
    null result on uniform terrain interpretable instead of merely noisy.
    """
    if op.queue_discipline == "random":
        return rng.permutation(blue)
    if op.queue_discipline in ("edf", "patient_first"):
        sign = 1.0 if op.queue_discipline == "edf" else -1.0
        return blue[np.argsort(sign * op.patience_v[blue], kind="stable")]
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
    op.supervised_sum += float(blue.size)
    if op.mult_window > 0:                    # same bookkeeping, on the service-time window
        idx = k // op.mult_window
        while op._mult_idx < idx:
            if op._mult_bin > 0.0:
                op._mult_sum += op._mult_bin
                op._mult_busy += 1
                op._mult_peak = max(op._mult_peak, op._mult_bin)
                senders = int(op._mult_mask).bit_count()
                op._mult_dsum += float(senders)
                op._mult_ge2 += senders >= 2
                op._mult_ge3 += senders >= 3
                op._mult_ge4 += senders >= 4
            op._mult_bin = 0.0
            op._mult_mask = 0
            op._mult_idx += 1
    if op.fano_window > 0:                    # close the bin this step has left behind
        idx = k // op.fano_window
        while op._fano_idx < idx:
            op._fano_n += 1
            op._fano_sum += op._fano_bin
            op._fano_sumsq += op._fano_bin * op._fano_bin
            op._fano_bin = 0.0
            op._fano_idx += 1
    if op.supervised_n0 == 0:
        op.supervised_n0 = int(blue.size)

    for i in blue:
        # 1) A pending request has come back: adopt its resolved quality, re-arm the cooldown.
        if ent.await_until[i] >= 0 and k >= ent.await_until[i]:
            ent.control_quality[i] = op.resolved_quality[i]
            ent.await_until[i] = -1
            cool = _reset_cooldown(op, rng, difficulty.get(i, 0.0), i)
            if op.retry_pending[i]:
                cool = _backoff(op, cool, i)
                op.retry_pending[i] = False
            ent.decision_cooldown[i] = cool
            continue

        # 2) Still awaiting a reply: sit at the low stall quality (hesitating without guidance).
        # With `stall_decay` on, that quality decays toward `stall_floor` in proportion to how far
        # into its patience window the requester has waited, so a long wait is worse than a short
        # one. The elapsed fraction is computed from the deadline the requester is holding, which
        # is `await_until`, and is clamped because an `admit` refusal shortens that deadline.
        if ent.await_until[i] >= 0:
            q = op.q_stall
            if op.stall_decay > 0.0:
                left = max(0.0, float(ent.await_until[i] - k))
                frac = 1.0 - min(1.0, left / max(1.0, float(op.patience_v[i])))
                q = op.q_stall - op.stall_decay * frac * (op.q_stall - op.stall_floor)
            ent.control_quality[i] = q
            continue

        # 3) Not awaiting: count down to the next decision event.
        if ent.decision_cooldown[i] > 0:
            ent.decision_cooldown[i] -= 1
            continue

        # 4) A decision event fires now.
        if op.mode == "supervisory":
            ent.control_quality[i] = op.q_auto
            op.resolved_quality[i] = op.q_auto
            ent.decision_cooldown[i] = _reset_cooldown(op, rng, difficulty.get(i, 0.0), i)
            continue

        # direct control: request the operator over the link. Both link types draw the same two
        # Bernoulli message-survival values, so the RNG stream stays aligned and the OFF path is
        # byte-identical. An EW-immune link (fiber / autonomous terminal guidance) ignores the drops
        # and rides a fixed low latency off the comms ladder; the single operator is still a shared
        # server, so span-of-control contention remains the residual limit.
        lat = op.immune_latency if op.ew_immune else comms.latency
        up_ok = comms.delivered(rng)
        if op.fano_window > 0 and up_ok:
            op._fano_bin += 1.0                  # one arrival at the console on this step
        if op.mult_window > 0 and up_ok:
            op._mult_bin += 1.0
            op._mult_mask |= 1 << int(i)
        # Read the queue before pricing the reply. The reply is not sent when the request is: it
        # leaves when the operator finishes, so the two messages are separated by `done - k` steps,
        # and on a channel with memory that gap is what decides whether their fates are correlated
        # (CR-18). Reading the queue consumes no randomness, so moving it above the second draw
        # leaves the stream exactly where it was.
        recv = k + lat                                        # request reaches operator
        if op.queue_model == "buffer":
            # The request joins the backlog and its fate is decided at the head, by `_drain_buffer`.
            # Until then the requester waits on its own deadline, so a request that is never picked
            # up costs exactly what an unanswered one always cost.
            op.n_request += 1
            if k >= op.late_from:
                op.n_request_late += 1
            op.req_seq[i] += 1
            if up_ok or op.ew_immune:
                op.pending.append([int(i), float(k), float(recv),
                                   float(k + int(op.patience_v[i])), int(op.req_seq[i])])
                ent.await_until[i] = k + int(op.patience_v[i])
                op.resolved_quality[i] = op.q_fallback
            else:
                op.n_abandon_link += 1
                _give_up(op, ent, int(i), k, int(op.patience_v[i]), rng)
            ent.control_quality[i] = op.q_stall
            continue
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
            if wait <= op.patience_v[i]:
                _claim(op, console, done)
                ent.await_until[i] = int(math.ceil(reply))
                # The published operator is an ORACLE: its answers never degrade, however hard
                # it is working. That is a real limitation, and `q_droop` exists to test whether
                # the results depend on it rather than to claim a psychology. It takes the
                # serviced-decision quality down toward the autonomous baseline in proportion to
                # the console's running utilization, which is the DESCENDING limb of the
                # utilization-performance relation and not the full inverted U. Zero is exactly
                # the published value, so the sweep nests the shipped model at its own baseline.
                q = op.q_operator
                if op.q_droop > 0.0:
                    util = op.busy_steps / max(op.total_steps, 1)
                    q = op.q_operator - op.q_droop * util * (op.q_operator - op.q_auto)
                op.resolved_quality[i] = q
                op.waits.append(float(wait))          # attention-switching wait, serviced only
                op.n_serviced += 1
                op.retry_streak[i] = 0        # answered, so the doubling rule resets
                if op.admit_response == "aimd":   # additive increase on a good answer (CR-26)
                    op.cadence_rate[i] = min(1.0, op.cadence_rate[i] + _AIMD_ALPHA)
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
                pat = int(op.patience_v[i])
                hold = min(2 * lat, pat) if op.queue_policy == "admit" else pat
                if op.admit_response == "aimd":   # multiplicative decrease on a refusal (CR-26)
                    op.cadence_rate[i] = max(_AIMD_FLOOR, op.cadence_rate[i] * _AIMD_BETA)
                ent.await_until[i] = k + hold                 # gives up waiting -> poor autonomy
                op.resolved_quality[i] = op.q_fallback
                op.n_abandon_queue += 1
                _arm_retry(op, rng, i)
        else:
            ent.await_until[i] = k + int(op.patience_v[i])    # message dropped -> poor autonomy
            op.resolved_quality[i] = op.q_fallback
            op.n_abandon_link += 1
            _arm_retry(op, rng, i)

        ent.control_quality[i] = op.q_stall                   # now awaiting

    if op.queue_model == "buffer":
        op.backlog_sum += float(len(op.pending))
        # After the arrivals, so a request that reaches a free console on the step it was sent is
        # served on that step, which is what `reserve` does with `start = max(free_at, recv)`.
        _drain_buffer(op, ent, comms, k, rng, difficulty)
        # And the overflow drop comes last, so the order within a step is arrive, serve, discard.
        # Trimming before service would make a capacity of zero mean "serve nothing" rather than
        # "serve only what arrives to a free console", which is the setting the sizing rule
        # prescribes once the link is slow enough.
        _trim(op, ent, k, rng)
