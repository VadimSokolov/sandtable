#!/usr/bin/env python3
"""Queue-only cross-check for the console buffer sizing rule (CR-48, CR-49).

This is a SECOND, INDEPENDENT implementation of the console queue, written from the model
description rather than from `sandtable.c2`, so that agreement between the two is evidence and not
a shared bug. It carries none of SandTable's terrain, sensing, combat, or vehicle state: a
requester here is a token that issues, waits, and gives up.

The model. `n` requesters. A requester thinks for Exp(Z), issues a request, and gives up exactly
`P` steps after issuing whether or not an answer is coming, which is the deterministic deadline the
simulator uses. The request reaches the console `L` steps later, waits in a buffer holding at most
`cap` ARRIVED requests (a negative `cap` is unbounded), and is answered in a DETERMINISTIC 1/mu,
which is what `c2.py` does and is the fact that killed the first version of CR-49. The answer takes
another `L` to travel back. It is USEFUL only if it lands within the requester's deadline.

Two details are load-bearing and are inherited deliberately:

  * There is no background reaper. A request whose requester has already given up stays in the
    buffer and still consumes a full service when the console reaches it. That is where the wasted
    work comes from and it is the point of the whole exercise.
  * The bound drops the OLDEST arrived request, which is the purge a console can perform without
    the requester's deadline travelling in the message.
"""
import argparse
import heapq
import math

import numpy as np

ISSUE, ARRIVE, ABANDON, DONE = 0, 1, 2, 3


def simulate(n, P, L, mu, cap, Z, horizon, seed, discipline="fifo", drop="oldest"):
    rng = np.random.default_rng(seed)
    svc = 1.0 / mu
    ev, ctr = [], 0
    gen = np.zeros(n, dtype=np.int64)

    def push(t, kind, payload):
        nonlocal ctr
        heapq.heappush(ev, (t, ctr, kind, payload))
        ctr += 1

    def think(now, i):
        push(now + (rng.exponential(Z) if Z > 0 else 0.0), ISSUE, (i,))

    for i in range(n):
        think(0.0, i)

    buf = []                      # (issue_time, i, gen) in arrival order
    busy_until = -1.0
    useful = served = dropped = 0
    work_time = 0.0

    def maybe_start(now):
        nonlocal busy_until
        if busy_until > now or not buf:
            return
        rec = buf.pop(0) if discipline == "fifo" else buf.pop()
        issue, i, g = rec
        busy_until = now + svc
        push(busy_until, DONE, (i, issue, g))

    t = 0.0
    while ev:
        t, _c, kind, pl = heapq.heappop(ev)
        if t > horizon:
            break
        if kind == ISSUE:
            (i,) = pl
            gen[i] += 1
            push(t + L, ARRIVE, (i, t, gen[i]))
            push(t + P, ABANDON, (i, gen[i]))
        elif kind == ARRIVE:
            i, issue, g = pl
            buf.append((issue, i, g))
            # Order matters and is inherited from `c2.py`: the console picks work up FIRST, then the
            # bound is applied to what is left waiting. The other order makes a capacity of zero mean
            # "serve nothing", which is a different policy from "hold no backlog".
            maybe_start(t)
            if cap >= 0:
                while len(buf) > cap:
                    victim = buf.pop(0) if drop == "oldest" else buf.pop()
                    dropped += 1
        elif kind == ABANDON:
            i, g = pl
            if gen[i] == g:                  # still waiting on this one: give up and re-arm
                think(t, i)
        else:
            i, issue, g = pl
            served += 1
            work_time += svc
            if t + L <= issue + P and gen[i] == g:
                useful += 1
                gen[i] += 1                  # the answer landed: cancel the pending abandon
                think(t + L, i)
            maybe_start(t)

    return dict(useful=useful / horizon, served=served / horizon,
                dropped=dropped / horizon, util=work_time / horizon)


def kstar_rules(lam):
    return dict(floor=math.floor(lam) - 1,
                third=math.floor(lam + 1.0 / 3.0) - 1,
                half=math.floor(lam + 0.5) - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--mu", type=float, default=0.15)
    ap.add_argument("--lat", type=float, default=0.0)
    ap.add_argument("--think", type=float, default=22.0)   # the sim's decision_interval
    ap.add_argument("--horizon", type=float, default=40000.0)
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--caps", type=str, default="-1,0,1,2,3,4,5,6,7,8,10")
    ap.add_argument("--patience", type=str, default="")
    ap.add_argument("--lam", type=str, default="", help="sweep lambda directly; P is derived")
    ap.add_argument("--discipline", type=str, default="fifo")
    ap.add_argument("--drop", type=str, default="oldest")
    ap.add_argument("--mpe", type=float, default=0.009,
                    help="material effect on served/step; caps within this of the max are a tie")
    a = ap.parse_args()

    caps = [int(x) for x in a.caps.split(",")]
    if a.lam:
        lams = [float(x) for x in a.lam.split(",")]
        pats = [l / a.mu + 2 * a.lat for l in lams]
    else:
        pats = [float(x) for x in a.patience.split(",")]

    print(f"n={a.n} mu={a.mu} L={a.lat} think={a.think} horizon={a.horizon} reps={a.reps} "
          f"discipline={a.discipline} drop={a.drop}")
    print("     P  lambda | " + " ".join(f"c{c:<+3d}" for c in caps)
          + " | argmax   plateau   floor third half")
    for P in pats:
        lam = (P - 2 * a.lat) * a.mu
        vals = []
        for c in caps:
            r = [simulate(a.n, P, a.lat, a.mu, c, a.think, a.horizon, 1000 + s,
                          a.discipline, a.drop)["useful"] for s in range(a.reps)]
            vals.append(float(np.mean(r)))
        am = caps[int(np.argmax(vals))]
        # A point argmax over a flat ridge is noise dressed as a decision. The plateau is every
        # capacity whose delivered service is within one material effect of the best one, and a
        # rule is scored against membership in it, not against the ridge's highest pixel.
        best = max(vals)
        plate = [c for c, v in zip(caps, vals) if best - v <= a.mpe and c >= 0]
        k = kstar_rules(lam)
        mark = "".join("*" if k[r] in plate else "." for r in ("floor", "third", "half"))
        ps = f"[{min(plate)}-{max(plate)}]" if plate else "[]"
        print(f"{P:6.2f} {lam:6.3f} | " + " ".join(f"{v:.4f}" for v in vals)
              + f" | {am:^6d} {ps:>9s} {k['floor']:5d} {k['third']:5d} {k['half']:4d}  {mark}")


if __name__ == "__main__":
    main()
