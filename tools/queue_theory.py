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

**Stable.** In the collapsed regime every request abandons, so each vehicle cycles
`patience + decision_interval` steps between requests. Requests arrive at the operator at
`n * d / (patience + decision_interval)` where `d = (1 - p_drop)^2` is the two-way delivery
probability, and each costs `S` of server time *whether or not anyone is still waiting for the
answer*. That last clause is the published `queue_policy="blind"` operator, and it makes the
collapsed regime self-sustaining once

    n * d * S / (patience + decision_interval)  >=  1,

that is, once the span exceeds

    n_collapse = (patience + decision_interval) * service_rate / d.

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


def serviceable(latency: float, service_rate: float, patience: float) -> bool:
    """Can a reply return inside `patience` even with an idle operator?"""
    return 2.0 * latency + 1.0 / service_rate <= patience


def collapse_span(p_drop: float, service_rate: float, patience: float,
                  decision_interval: float) -> float:
    """Span above which the abandonment cycle sustains its own overload."""
    d = two_way_delivery(p_drop)
    if d <= 0.0:
        return float("inf")
    return (patience + decision_interval) * service_rate / d


def solve(n: int, latency: float, p_drop: float, service_rate: float = 0.15,
          patience: float = 20.0, decision_interval: float = 30.0,
          refund: bool = False, iters: int = 400) -> dict:
    """Fixed point for goodput and mean reply time at one operating point.

    The cycle length depends on the wait, the wait depends on the arrival rate, and the arrival
    rate depends on the cycle length, so the three are iterated to convergence.

    Approximation, stated because it matters: the ABM's service is deterministic and its arrivals
    are a superposition of `n` jittered renewal processes, but the queueing delay here uses the
    M/M/1 tail ``P(Wq > t) = rho * exp(-(1 - rho) t / S)``. That overstates delay variance, so the
    predicted goodput is conservative near the threshold and exact away from it. The collapse
    threshold itself, which is the object of interest, involves only mean rates and is not
    approximate. `queue_only_sim` is the exact check.
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
        p_s = 0.5 * p_s + 0.5 * p_s_new
        cycle = 0.5 * cycle + 0.5 * cycle_new       # damped, so the map cannot ring
    return {"regime": "stable", "goodput": d * p_s, "rho": rho, "reply": reply,
            "cycle": cycle, "n_collapse": n_star}


def queue_only_sim(n: int, latency: float, p_drop: float, service_rate: float = 0.15,
                   patience: float = 20.0, decision_interval: float = 30.0,
                   policy: str = "blind", steps: int = 20000, seed: int = 0) -> dict:
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
    free_at = 0.0
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
            done = max(free_at, k + latency) + S
            reply = done + latency
            if reply - k <= patience:
                free_at = done
                await_until[i] = int(math.ceil(reply))
                served += 1
            else:
                if policy == "blind":
                    free_at = done
                await_until[i] = k + (2 * latency if policy == "admit" else patience)
                abandoned += 1
    total = max(served + dropped + abandoned, 1)
    return {"goodput": served / total, "abandon_queue_frac": abandoned / total,
            "abandon_link_frac": dropped / total, "requests": total}


_LADDER = [(0, 0.00), (1, 0.05), (2, 0.10), (4, 0.20), (8, 0.35), (16, 0.55)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", help="read service_rate/patience/decision_interval from this "
                                       "scenario JSON, so the theory is quoted at the operating "
                                       "point the simulator actually ran")
    ap.add_argument("--service-rate", type=float, default=0.15)
    ap.add_argument("--patience", type=float, default=20.0)
    ap.add_argument("--decision-interval", type=float, default=30.0)
    ap.add_argument("--spans", type=int, nargs="+", default=[2, 4, 6, 8, 10, 12])
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
          f"decision_interval={a.decision_interval}  policy="
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
        ns = collapse_span(drop, a.service_rate, a.patience, a.decision_interval)
        blocked = "" if serviceable(lat, a.service_rate, a.patience) else "   (latency-blocked)"
        print(f"  C{lvl}   {lat:>3}  {drop:.2f}  {d:.3f}  {ns:6.2f}{blocked}")
    print()
    print("goodput (share of requests answered by the operator), closed form vs queue-only sim:")
    print("  span " + "".join(f"       C{i}" for i in range(6)))
    for n in a.spans:
        row = []
        for lvl, (lat, drop) in enumerate(_LADDER):
            r = solve(n, lat, drop, a.service_rate, a.patience, a.decision_interval, a.refund)
            q = queue_only_sim(n, lat, drop, a.service_rate, a.patience, a.decision_interval,
                               "refund" if a.refund else "blind")
            row.append(f"  {r['goodput']:.2f}/{q['goodput']:.2f}")
        print(f"  n={n:<3}" + "".join(row))


if __name__ == "__main__":
    main()
