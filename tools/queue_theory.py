"""Closed-form operator-queue model, and the collapse threshold it predicts.

SandTable's `c2.py` is an agent-based model, but the operator inside it is a single-server
queue with deterministic service, a fixed round-trip delay, and *abandonment*: a vehicle that
has waited longer than `patience` stops waiting and drives on autonomously. That is an
M/D/1+D queue, and it has enough structure to solve, so the agent-based numbers have something
to be checked against. Validating an ABM against a tractable analytic model is the discipline
Gaertner's UAV-swarm thesis argues for, and it is what turns "the simulator did something
surprising" into "the simulator did what a queue does".

Two regimes, separated by one threshold.

**Serviceable at all.** A reply must come back inside the requester's patience even with an
empty queue, so `2*latency + S <= patience` where `S = 1/service_rate`. Above that latency no
request can ever be answered and the drop rate stops mattering, which is why the C0-C5 ladder
has fewer distinguishable rungs than it has levels.

**Stable.** In the collapsed regime every request abandons, so each vehicle runs a fixed cycle:
`patience` steps waiting the request out, `decision_interval` steps of cooldown, and one step on
which the next decision fires (the counter is decremented on each of `decision_interval` steps and
the event fires on the step AFTER it reaches zero). Requests therefore arrive at the operator at
`n * d / (patience + decision_interval + 1)` where `d = (1 - p_drop)^2` is the two-way delivery
probability, and each costs `S` of server time *whether or not anyone is still waiting for the
answer*. That last clause is the published `queue_policy="blind"` operator, and it makes the
collapsed regime self-sustaining once

    n * d * S / (patience + decision_interval + 1)  >=  1,

that is, once the span exceeds

    n_collapse = (patience + decision_interval + 1) * service_rate / d.

The trailing step is not cosmetic: dropping it understates the threshold by about 2.4 percent
(6.30 against the correct 6.45 at the published operating point). The measured cycle deep in
collapse is 42.84 steps against this formula's 43.00.

Below the threshold the queue drains and the fixed point below solves for the achieved goodput.
The threshold is the interesting object: it says the span at which direct control collapses is
set by the operator's service rate and the vehicles' request rate, *not* by the link, and that
jamming RAISES it, because a dropped request is a request the operator never has to work.

Usage:  python3 tools/queue_theory.py [--service-rate 0.15] [--patience 20] ...
"""
from __future__ import annotations

import argparse
import math


def two_way_delivery(p_drop: float) -> float:
    """A request needs the uplink and the downlink, so delivery is (1 - p_drop) squared."""
    return (1.0 - p_drop) ** 2


def two_way_delivery_bursty(p_drop: float, burst_len: float) -> float:
    """Round-trip delivery on a Gilbert-Elliot channel whose stationary drop rate is `p_drop`.

    A request-reply handshake needs TWO messages to survive, and `two_way_delivery` squares the
    marginal rate because a memoryless channel makes their fates independent. A bursty channel does
    not. `c2.step` draws the two consecutively, so conditioning on the first surviving leaves the
    chain in GOOD, and the second is lost only on a fresh GOOD-to-BAD transition:

        d = (1 - p) * (1 - p_gb),      p_gb = p * p_bg / (1 - p),   p_bg = 1 / burst_len.

    Correlation therefore HELPS the handshake: at a matched mean drop rate the bursty channel
    completes more round trips than the memoryless one, measured 0.876 against 0.811 at the
    degraded rung and 0.312 against 0.203 at the denied one, and the closed form matches each to
    three decimals. That is the opposite of the usual reading of burstiness, and for this model it
    is bad news rather than good: the operator is the bottleneck, so a round trip that completes is
    work that arrives. Substituting into `collapse_span` moves the cliff LEFT by 3.6% at the
    nominal rung and 35.1% at the denied one.

    The consequence for the ladder is that `p_drop` is not a sufficient statistic for a link. Two
    channels with the same mean loss put different loads on the same operator.

    THIS FORMULA DESCRIBES A MESSAGE-CLOCKED CHANNEL, AND THAT TURNED OUT TO BE THE WRONG ONE.
    `burst_len` is coherence measured in MESSAGES, and the chain advances one transition per
    message, so a request and its reply are adjacent in chain time even though the operator's whole
    service delay separates them in mission time. Pricing the reply at the moment it is actually
    sent (`channel_clock="step"`, CR-18) collapses the effect: realized round-trip delivery at eight
    vehicles goes 0.9352 to 0.8945 at the nominal rung and 0.7598 to 0.6478 at the contested one,
    landing on the Bernoulli values of 0.9057 and 0.6348. The service delay outruns the channel's
    coherence, so the handshake is independent after all and burstiness at a matched mean drop rate
    does nothing to this queue. The ladder's `p_drop` IS a sufficient statistic for the operator,
    which is the opposite of what the message-clocked model says.

    The formula is kept because it is the correct description of the adjacent limit, which is the
    right physics for a jammer whose sweep is slow against the round trip, and because the size of
    the gap between the two clocks is the measure of the artifact. Bracketing it: `burst_len = 1/(1-p)` is the memoryless point, where
    the two draws are independent and `d` returns exactly to `(1-p)^2`, and as coherence grows `d`
    saturates at `(1-p)`, because a chain left in GOOD by the first message loses the second only
    on a fresh transition. So for any coherence at or above the memoryless point the effect is
    bounded,

        (1-p)^2  <=  d  <=  (1-p),

    (shorter dwells than that are the anti-correlated corner, where the bad state refuses to repeat
    and `d` falls BELOW the memoryless value; the ladder's default of 4 is above the memoryless
    point at every rung, since `1/(1-p)` runs from 1.05 to 2.22 across C1 to C5),

    and the collapse threshold can fall by at most a factor of `(1-p)`, which is 20% at the
    contested rung, however bursty the link. A link that decorrelates inside one round trip gets
    the Bernoulli answer and no effect at all. The ladder default of 4 sits between: 14.7% of a
    possible 20% at that rung.
    """
    if burst_len <= 0.0:
        raise ValueError(f"burst_len must be positive, got {burst_len}")
    if p_drop >= 1.0:
        return 0.0
    p_bg = 1.0 / max(1.0, burst_len)
    p_gb = p_drop * p_bg / (1.0 - p_drop)
    return (1.0 - p_drop) * (1.0 - p_gb)


def serviceable(latency: float, service_rate: float, patience: float) -> bool:
    """Can a reply return inside `patience` even with an idle operator?"""
    return 2.0 * latency + 1.0 / service_rate <= patience


def collapse_span(p_drop: float, service_rate: float, patience: float,
                  decision_interval: float, n_operators: int = 1,
                  burst_len: float | None = None) -> float:
    """Span above which the abandonment cycle sustains its own overload.

    In the collapsed state every request abandons, so an agent's cycle is `patience` steps waiting
    it out, then `decision_interval` steps of cooldown, then ONE step on which the next decision
    fires. That trailing step is not cosmetic: the cooldown counter is decremented on each of
    `decision_interval` steps and the event fires on the step after it reaches zero, so the cycle
    is `patience + decision_interval + 1`, measured at 42.84 against a predicted 43.00 deep in
    collapse. Dropping it understates the threshold by about 2.4 percent.

    Linear in crew size: `c` consoles each serving at `service_rate` carry `c` times the load,
    so the staffing question and the span question are the same question.

    Passing `burst_len` prices a Gilbert-Elliot channel at the same mean drop rate instead of a
    memoryless one, which raises `d` and so lowers the threshold.
    """
    d = two_way_delivery_bursty(p_drop, burst_len) if burst_len else two_way_delivery(p_drop)
    if d <= 0.0:
        return float("inf")
    return n_operators * (patience + decision_interval + 1.0) * service_rate / d


def fold_band(p_drop: float, service_rate: float, patience: float,
              decision_interval: float, retry_prob: float = 0.0,
              retry_backoff: float | None = None,
              n_operators: int = 1,
              abandon_healthy: float | None = None) -> tuple[float, float]:
    """The span interval over which BOTH the healthy and the collapsed state are self-sustaining.

    `collapse_span` above assumes a vehicle's request cycle does not depend on whether its last
    request was answered. Closed-loop reliance (CR-17) breaks that: a fraction `pi` of abandoned
    requests come back after `rho` steps instead of `tau`, so the cycle is SHORTER in the state
    where requests are being abandoned. Demand then depends on the state the system is already in,
    and the threshold splits in two.

    Deep in collapse every request abandons, so the mean cycle is `P + 1 + pi*rho + (1-pi)*tau`
    and the collapsed state sustains itself above

        n_c = c*mu*(P + 1 + tau - pi*(tau - rho)) / d.

    In the healthy state a smaller fraction `a_h` abandons, so only that fraction retries early
    and the mean cycle is `P + 1 + tau - a_h*pi*(tau - rho)`. The healthy state survives up to

        n_h = c*mu*(P + 1 + tau - a_h*pi*(tau - rho)) / d,

    and the gap is

        n_h - n_c = c * mu * pi * (tau - rho) * (1 - a_h) / d.

    `a_h` defaults to the link-dropped fraction `1 - d`, which is its FLOOR: a request can also
    abandon because the queue was busy, and at C0 that is the only way it can. Taking the floor
    therefore gives the widest band the parameters allow, an upper bound on `n_h` rather than a
    prediction of it; passing the measured no-retry abandonment fraction sharpens it. At the
    published operating point the bound puts `n_h` at the no-retry threshold 6.45, while feeding
    in the measured healthy abandonment at six vehicles (0.222) moves it to 5.85, which is what
    the simulator does: six vehicles collapse from both initial conditions and five do not.

    Two consequences follow, and both are operational rather than decorative. The band is empty
    exactly when retry does not shorten the cycle (`pi = 0` or `rho = tau`), so it is not a
    property of this particular retry rule but of any reliance loop that closes faster after a
    failure. And at the floor it spans a whole vehicle only when `pi*(tau - rho) >= 1/(c*mu)`,
    one service time per console, which is a backoff floor: hold a failed requester off for at
    least `tau - 1/(c*mu*pi)` steps and the band closes.

    Under `queue_policy = "admit"` the requester is told on arrival instead of abandoning, so the
    retry branch is never taken and the band does not exist. Admission control is retry-proof.
    """
    d = two_way_delivery(p_drop)
    if d <= 0.0:
        return float("inf"), float("inf")
    rho = decision_interval if retry_backoff is None else retry_backoff
    shortening = retry_prob * (decision_interval - rho)
    a_h = (1.0 - d) if abandon_healthy is None else float(abandon_healthy)
    base = patience + decision_interval + 1.0
    n_c = n_operators * service_rate * (base - shortening) / d
    n_h = n_operators * service_rate * (base - a_h * shortening) / d
    return n_c, n_h


def backoff_floor(service_rate: float, decision_interval: float, retry_prob: float,
                  n_operators: int = 1) -> float:
    """Shortest retry backoff that leaves the fold band narrower than one vehicle.

    Solves `n_h - n_c = c*mu*pi*(tau - rho) < 1` for `rho`. Below this floor an eager retry buys
    a vehicle a faster second attempt at the cost of a span at which the team has two stable
    states and only one of them is the one anybody wants.
    """
    if retry_prob <= 0.0:
        return 0.0
    return decision_interval - 1.0 / (n_operators * service_rate * retry_prob)


def solve(n: int, latency: float, p_drop: float, service_rate: float = 0.15,
          patience: float = 20.0, decision_interval: float = 30.0,
          refund: bool = False, iters: int = 400, burst_len: float | None = None) -> dict:
    """Fixed point for goodput and mean reply time at one operating point.

    The cycle length depends on the wait, the wait depends on the arrival rate, and the arrival
    rate depends on the cycle length, so the three are iterated to convergence.

    Approximation, stated because it matters: the ABM's service is deterministic and its arrivals
    are a superposition of `n` jittered renewal processes, but the queueing delay here uses the
    M/M/1 tail ``P(Wq > t) = rho * exp(-(1 - rho) t / S)``. That overstates delay variance, so the
    predicted goodput is conservative near the threshold and exact away from it. The collapse
    threshold itself, which is the object of interest, involves only mean rates and is not
    approximate. `queue_only_sim` is the exact check.

    `burst_len` closes a second loop, and it turns the other way from the first. On a coherent
    channel the round-trip delivery is `d = (1-p)[1 - p(1 - lam^lag)]`, which depends on the reply
    lag, which depends on the load. So `d` is not a constant of the operating point: as a team
    slides toward collapse its waits lengthen, `lam^lag` falls, `d` slides back toward `(1-p)^2`,
    and `n_c = c mu Lambda / d` RISES away from the team. That is negative feedback, and it is the
    opposite sign to the reliance loop of CR-17, where collapse shortens the cycle, which lowers
    `n_c` and deepens collapse. Two loops through one threshold, one opening a fold band and one
    damping it. Measured on the live model at rung 3, a 120-step dwell and a 4-step backoff: the
    mean reply lag runs 13, 51, 95 and 247 steps at four, five, six and eight vehicles, so the
    realized `d` runs 0.780, 0.740, 0.715, 0.679 and `n_c` runs 4.81, 5.07, 5.24, 5.52 instead of
    sitting at the 4.81 a static reading gives.

    Leave it `None` for a memoryless channel, where `d` has no lag dependence and the loop does
    not exist.
    """
    S = 1.0 / service_rate
    d = two_way_delivery(p_drop)
    slack = patience - 2.0 * latency - S            # queueing budget before the requester gives up
    n_star = collapse_span(p_drop, service_rate, patience, decision_interval)
    if slack < 0.0:
        # No request can be answered in time. Every one abandons; the operator is irrelevant.
        return {"regime": "latency-blocked", "goodput": 0.0, "rho": float("nan"),
                "reply": float("inf"), "cycle": patience + decision_interval,
                "n_collapse": n_star}

    cycle = patience + decision_interval            # start from the pessimistic cycle
    p_s = 0.0
    rho = 0.0
    for _ in range(iters):
        lam = n * d / cycle                         # requests reaching the operator per step
        # `blind` pays for abandoned work too, so the server carries the full arrival rate.
        # `refund` and `admit` only pay for work whose answer will be used.
        rho = lam * S * (1.0 if not refund else max(p_s, 1e-9))
        if rho >= 1.0:
            return {"regime": "collapsed", "goodput": 0.0, "rho": rho,
                    "reply": float("inf"), "cycle": patience + decision_interval,
                    "n_collapse": n_star}
        p_s_new = 1.0 - rho * math.exp(-(1.0 - rho) * slack / S)
        e_wq = rho * S / (1.0 - rho)
        reply = 2.0 * latency + e_wq + S
        served_wait = min(reply, patience)
        cycle_new = d * (p_s_new * served_wait + (1.0 - p_s_new) * patience) \
            + (1.0 - d) * patience + decision_interval
        if burst_len is not None:
            # The coherent-channel loop, damped like the other two so the map cannot ring.
            lam = max(0.0, 1.0 - 1.0 / (burst_len * (1.0 - p_drop)))
            d_new = (1.0 - p_drop) * (1.0 - p_drop * (1.0 - lam ** max(1.0, reply)))
            d = 0.5 * d + 0.5 * d_new
        p_s = 0.5 * p_s + 0.5 * p_s_new
        cycle = 0.5 * cycle + 0.5 * cycle_new       # damped, so the map cannot ring
    return {"regime": "stable", "goodput": d * p_s, "rho": rho, "reply": reply,
            "cycle": cycle, "n_collapse": n_star}


def queue_only_sim(n: int, latency: float, p_drop: float, service_rate: float = 0.15,
                   patience: float = 20.0, decision_interval: float = 30.0,
                   policy: str = "blind", steps: int = 20000, seed: int = 0,
                   n_operators: int = 1) -> dict:
    """The operator queue on its own, with no terrain, no sensing, and no combat.

    Same request-and-abandon rules as `c2.step`, same jittered cooldown, nothing else. If the
    goodput SandTable reports matches this, the behaviour is the queue's and not an interaction
    with the rest of the mission, which is what makes the closed form above the right explanation.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    S = 1.0 / service_rate
    lo, hi = max(1, int(decision_interval) // 2), max(2, int(decision_interval) * 3 // 2)
    await_until = np.full(n, -1)
    cooldown = rng.integers(lo, hi + 1, size=n)
    free_at = np.zeros(max(n_operators, 1))
    served = dropped = abandoned = 0
    for k in range(steps):
        for i in range(n):
            if await_until[i] >= 0:
                if k >= await_until[i]:
                    await_until[i] = -1
                    cooldown[i] = rng.integers(lo, hi + 1)
                continue
            if cooldown[i] > 0:
                cooldown[i] -= 1
                continue
            link_ok = rng.random() >= p_drop and rng.random() >= p_drop
            if not link_ok:
                await_until[i] = k + patience
                dropped += 1
                continue
            console = int(np.argmin(free_at))
            done = max(free_at[console], k + latency) + S
            reply = done + latency
            if reply - k <= patience:
                free_at[console] = done
                await_until[i] = int(math.ceil(reply))
                served += 1
            else:
                if policy == "blind":
                    free_at[console] = done
                await_until[i] = k + (2 * latency if policy == "admit" else patience)
                abandoned += 1
    total = max(served + dropped + abandoned, 1)
    return {"goodput": served / total, "abandon_queue_frac": abandoned / total,
            "abandon_link_frac": dropped / total, "requests": total}


def bench_sim(rate: float, cluster_len: float = 0.0, latency: float = 0.0,
              service_rate: float = 0.15, patience: float = 20.0, policy: str = "blind",
              steps: int = 200000, seed: int = 0, window: int = 120) -> dict:
    """The console driven by an EXOGENOUS arrival process, with the feedback loop cut.

    `queue_only_sim` still lets the console shape its own demand: a vehicle that is refused waits
    out its patience and so arrives later, which means arrival clustering is co-produced by console
    state and cannot be manipulated independently of it. Every observational contrast in this
    project inherits that. This bench replaces the vehicles with a stationary arrival process whose
    RATE and BURSTINESS are set separately and neither of which can hear the console, so the two
    can be crossed.

    The process is a Markov-modulated Poisson process with symmetric ON and OFF states of mean
    dwell `cluster_len` and an ON rate of `2*rate`, so the mean arrival rate is `rate` at every
    `cluster_len` by construction. `cluster_len = 0` degenerates to a homogeneous Poisson stream at
    the same rate, which is the smooth control. Nothing else differs between the two.

    Returns the goodput, the realized arrival rate (a check that the rate match held), and the
    Fano factor of the arrival stream at `window`, which is the intermediate variable the
    observational probe could only measure endogenously.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    S = 1.0 / service_rate
    on_rate = 2.0 * rate
    p_switch = 0.0 if cluster_len <= 0 else 1.0 / cluster_len
    on = True
    free_at = 0.0
    served = abandoned = 0
    counts = np.zeros(steps)
    for k in range(steps):
        if p_switch > 0.0:
            lam = on_rate if on else 0.0
            if rng.random() < p_switch:
                on = not on
        else:
            lam = rate
        n_arr = rng.poisson(lam)
        counts[k] = n_arr
        for _ in range(n_arr):
            done = max(free_at, k + latency) + S
            if done + latency - k <= patience:
                free_at = done
                served += 1
            else:
                if policy == "blind":
                    free_at = done          # the slot is spent on an answer nobody waits for
                abandoned += 1
    total = max(served + abandoned, 1)
    w = max(1, int(window))
    binned = counts[:len(counts) // w * w].reshape(-1, w).sum(1)
    fano = float(binned.var() / binned.mean()) if binned.mean() > 0 else float("nan")
    return {"goodput": served / total, "arrivals": total, "rate": total / steps,
            "fano": fano, "abandon_frac": abandoned / total}


_LADDER = [(0, 0.00), (1, 0.05), (2, 0.10), (4, 0.20), (8, 0.35), (16, 0.55)]


def failure_cycle(patience: float, decision_interval: float,
                  backoff: float | None = None) -> float:
    """Steps between one unanswered request and the same vehicle's next one.

    A vehicle whose request is dropped or abandoned waits out `patience`, then serves a cooldown,
    then fires on the following step, so the cycle is `P + tau + 1` and, under a CR-17 retry that
    returns after `rho` instead, `P + rho + 1`. This is the SAME quantity that sets the collapse
    span: `n* = c mu (P + tau + 1) / d` is `c mu C / d`, and the fold band is the gap between the
    cycle in the collapsed state and the cycle in the healthy one. It is written once here because
    it turns out to govern the channel as well as the queue (see `coherence_ratio`).
    """
    return patience + (decision_interval if backoff is None else backoff) + 1.0


def coherence_ratio(p_drop: float, burst_len: float, lag: float) -> float:
    """Channel coherence time measured in units of the interval at which the chain is re-consulted.

    A Gilbert-Elliot chain with mean bad-state dwell `L` and stationary drop rate `p` has
    `p_bg = 1/L` and, from `pi_bad = p_gb/(p_gb + p_bg) = p`, `p_gb = p/(L(1-p))`. Its second
    eigenvalue is therefore

        lam = 1 - p_gb - p_bg = 1 - 1/(L(1-p)),

    and the chain decorrelates on a timescale `tau_corr = -1/ln(lam)`, which is `L(1-p)` to first
    order. What decides whether that memory can reach a mission metric is not `tau_corr` but its
    ratio to `lag`, the interval after which the chain is consulted again:

        theta = tau_corr / lag.

    Below one the chain has mixed by the time it is next read, and the channel is memoryless at
    the granularity that reader samples it, whatever its burst statistics.

    **`lag` is not one number, and picking the wrong one is the easy mistake.** Two readers
    consult this chain at two very different intervals, so a burst channel has two knees:

    * A vehicle re-consults it after a full failure cycle, `failure_cycle(P, tau)` = 43 steps at
      the published operating point, because a dropped request costs it `P` steps of waiting and
      `tau` of cooldown before it can ask again. This governs how long one vehicle stays degraded.
    * The console re-consults it at the aggregate inter-request gap, measured at 12.2 steps for
      five vehicles, 7.6 for eight and 4.3 for twelve. This governs whether the vehicles' failures
      arrive together, which is what idles an operator and then floods the console.

    The second knee sits at a much shorter dwell than the first, so as a link's outages lengthen
    the cross-vehicle effect appears well before the within-vehicle one.
    """
    if burst_len <= 0 or p_drop >= 1.0:
        return 0.0
    lam = 1.0 - 1.0 / (burst_len * (1.0 - p_drop))
    if lam <= 0.0:
        return 0.0
    return (-1.0 / math.log(lam)) / lag


def coherence_excess(p_drop: float, burst_len: float, lag: float) -> float:
    """Excess probability that the chain is still BAD when next read, over the marginal rate.

    For a two-state chain the probability of being bad `lag` steps after being bad is
    `p + (1-p) lam^lag`, so the EXCESS over the marginal rate `p` is `(1-p) lam^lag`. With
    `lam^lag ~ exp(-1/theta)` this is

        e(theta) = (1 - p) exp(-1/theta),

    an exponential in the INVERSE coherence ratio: flat while `theta` is small, then steep. That
    shape is why `theta = 1` is a knee rather than an arbitrary cut.

    The mean throughput is untouched by any of this. The marginal drop rate is held fixed by
    construction, so the round-trip delivery `d` and the collapse span `n* = c mu C / d` do not
    move. What `e` governs is the DISPERSION of per-vehicle wait, and abandonment is a threshold on
    that wait rather than a rate, which is the only reason dispersion can reach a mission metric at
    all. Burst structure enters through the tail.
    """
    th = coherence_ratio(p_drop, burst_len, lag)
    if th <= 0.0:
        return 0.0
    return (1.0 - p_drop) * math.exp(-1.0 / th)


def crossover_burst_len(p_drop: float, lag: float) -> float:
    """Mean bad-state dwell at which the coherence ratio is exactly one.

    Solving `-1/ln(lam) = lag` for `lam` gives `lam = exp(-1/lag)`, and substituting
    `lam = 1 - 1/(L(1-p))` gives

        L* = 1 / [ (1-p) (1 - exp(-1/lag)) ].

    The first-order reading `L* ~ lag/(1-p)` is a few percent low and worsens as `lag` shrinks, so
    the exact form is what the registered crossovers are stated at. At `p = 0.20` the two knees of
    the published operating point are `L* = 54.4` for a vehicle's own failure cycle of 43 steps and
    `L* = 10.1` for the console's 7.6-step aggregate gap at eight vehicles.

    Note what shortening the backoff does. A CR-17 retry with `rho = 4` cuts the failure cycle from
    43 to 25 and the within-vehicle knee from 54.4 to 31.9, so a team that closes its reliance loop
    faster is MORE exposed to the link's burst structure, not less. The mechanism that opens a fold
    band and the mechanism that makes channel memory visible are the same shortened cycle.
    """
    return 1.0 / ((1.0 - p_drop) * (1.0 - math.exp(-1.0 / lag)))



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", help="read service_rate/patience/decision_interval from this "
                                       "scenario JSON, so the theory is quoted at the operating "
                                       "point the simulator actually ran")
    ap.add_argument("--service-rate", type=float, default=0.15)
    ap.add_argument("--patience", type=float, default=20.0)
    ap.add_argument("--decision-interval", type=float, default=30.0)
    ap.add_argument("--spans", type=int, nargs="+", default=[2, 4, 6, 8, 10, 12])
    ap.add_argument("--crew", type=int, default=1, help="number of operator consoles")
    ap.add_argument("--refund", action="store_true")
    a = ap.parse_args()
    if a.scenario:
        import json
        prm = json.load(open(a.scenario)).get("params", {})
        a.service_rate = float(prm.get("service_rate", a.service_rate))
        a.patience = float(prm.get("patience", a.patience))
        a.decision_interval = float(prm.get("decision_interval", a.decision_interval))
        print(f"operating point read from {a.scenario}")

    print(f"service_rate={a.service_rate}  patience={a.patience}  "
          f"decision_interval={a.decision_interval}  crew={a.crew}  policy="
          f"{'refund/admit' if a.refund else 'blind'}")
    print(f"latency cut-off: a request is serviceable only while "
          f"2*lat + {1/a.service_rate:.2f} <= {a.patience:.0f}, i.e. lat <= "
          f"{(a.patience - 1/a.service_rate)/2:.2f} steps")
    print()
    print("collapse span n* by rung (span above which the blind operator overloads):")
    hdr = "  rung  lat  drop   d      n*"
    print(hdr)
    for lvl, (lat, drop) in enumerate(_LADDER):
        d = two_way_delivery(drop)
        ns = collapse_span(drop, a.service_rate, a.patience, a.decision_interval, a.crew)
        blocked = "" if serviceable(lat, a.service_rate, a.patience) else "   (latency-blocked)"
        print(f"  C{lvl}   {lat:>3}  {drop:.2f}  {d:.3f}  {ns:6.2f}{blocked}")
    print()
    print("goodput (share of requests answered by the operator), closed form vs queue-only sim:")
    print("  span " + "".join(f"       C{i}" for i in range(6)))
    for n in a.spans:
        row = []
        for lvl, (lat, drop) in enumerate(_LADDER):
            r = solve(n / max(a.crew, 1), lat, drop, a.service_rate, a.patience,
                      a.decision_interval, a.refund)
            q = queue_only_sim(n, lat, drop, a.service_rate, a.patience, a.decision_interval,
                               "refund" if a.refund else "blind", n_operators=a.crew)
            row.append(f"  {r['goodput']:.2f}/{q['goodput']:.2f}")
        print(f"  n={n:<3}" + "".join(row))


if __name__ == "__main__":
    main()
