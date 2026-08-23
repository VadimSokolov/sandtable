"""Bench `arrival_excess` on a GATED source, at dwells above and below the measurement window.

Owed before CR-41 is read, on Fable's objection: the dwell is part of the instrument, not only part
of the model. The estimator normalizes multiplicity by the Poisson value at the stream's own measured
rate, and a gate makes the stream non-Poisson in a way that depends on how the dwell compares to the
window. Sub-window dwells are a regime `bench_excess` has never visited, because its injected source
has no gate at all.

The source here is the one the batteries run against: a two-state chain with geometric dwells, an
arrival probability `p` while ON and none while OFF. Its exact count distribution over a window of
`w` steps is available by transfer matrix rather than by simulation, which is what makes this a bench
and not a second experiment. Carry the joint law of (chain state, arrivals so far) forward `w` steps
from the stationary start:

    f_0(s, 0) = pi(s)
    f_{t+1}(s', k) = sum_s f_t(s, k) * A(s, s') * (1 - p_s)  +  f_t(s, k-1) * A(s, s') * p_s

with `p_ON = p`, `p_OFF = 0`. From the final marginal over `k`,

    E[k | k >= 1] = sum_k k f(k) / (1 - f(0))

and the true excess is that divided by the Poisson value `lw / (1 - exp(-lw))` at the same mean rate
`l = pi_ON * p`. That is the number the estimator has to reproduce.

Usage:  python3 tools/bench_gate.py [--window 7] [--blocks 32] [--steps 20000]
"""
from __future__ import annotations

import argparse

import numpy as np

# The deployed rate: the batteries sit near 0.10 to 0.15 delivered round trips per step, and the
# gate's duty cycle is set so the mean rate is the same at every dwell, which is what makes the
# comparison across dwells a comparison of structure rather than of load.
DUTY = 0.8                 # rung 3 drops 20 percent, so the link delivers 80 percent of the time
DWELLS = (1, 2, 3, 5, 7, 15, 30, 60, 120, 240)

# The size of the quantity CR-41 is trying to measure: the jittered arm's excess above one runs
# 0.062 to 0.094 across the F3 dwell sweep. An estimator bias has to be judged against that rather
# than against zero, because a bias small next to the effect does not change any reading.
RESIDUAL = 0.08


def truth(l_on: float, l_off: float, p: float, w: int) -> tuple[float, float]:
    """Exact (E[k | k>=1], excess over Poisson) for the gated source over a window of w steps."""
    a_on, a_off = 1.0 / l_on, 1.0 / l_off             # per-step switch probabilities
    A = np.array([[1.0 - a_off, a_off], [a_on, 1.0 - a_on]])   # states: 0 = OFF, 1 = ON
    pi = np.array([a_on, a_off]) / (a_on + a_off)
    pk = np.array([0.0, p])
    f = np.zeros((2, w + 1))
    f[:, 0] = pi
    for _ in range(w):
        g = np.zeros_like(f)
        for s in (0, 1):
            moved = np.outer(A[s], f[s])              # (s', k)
            g += moved * (1.0 - pk[s])
            g[:, 1:] += moved[:, :-1] * pk[s]
        f = g
    dist = f.sum(axis=0)
    p0 = dist[0]
    ek = float((np.arange(w + 1) * dist).sum() / (1.0 - p0))
    lam = float(pi[1] * p)
    lw = lam * w
    pois = lw / (1.0 - np.exp(-lw))
    return ek, ek / pois


def measure(rng: np.random.Generator, l_on: float, l_off: float, p: float,
            w: int, steps: int) -> float:
    """The SHIPPED estimator, run over a realization of the same source."""
    a_on, a_off = 1.0 / l_on, 1.0 / l_off
    on = rng.random() < l_on / (l_on + l_off)
    nwin = steps // w
    counts = np.zeros(nwin, dtype=np.int64)
    for t in range(nwin * w):
        if on and rng.random() < p:
            counts[t // w] += 1
        on = (rng.random() >= a_on) if on else (rng.random() < a_off)
    busy = counts > 0
    if not busy.any():
        return float("nan")
    mult = counts[busy].mean()
    lw = counts.sum() / (len(counts) * w) * w          # the estimator's own rate, times the window
    pois = lw / (1.0 - np.exp(-lw)) if lw > 0 else 1.0
    return float(mult / pois)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--blocks", type=int, default=32)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--rate", type=float, default=0.12)
    ap.add_argument("--duty", type=float, default=DUTY)
    a = ap.parse_args()
    duty = a.duty
    p = a.rate / duty                                  # ON-state probability giving the target mean
    print(f"Gated-source bench for arrival_excess at window {a.window}.")
    print(f"Mean rate {a.rate} per step held fixed at every dwell (delivery fraction {duty}), "
          f"so only the structure changes. The dwell is the OUTAGE length, as in the model.\n")
    print(f"{'dwell':>6} {'duty':>6} {'true mult':>10} {'true exc':>9} {'measured':>10} "
          f"{'bias':>9} {'se':>8}   reads")
    for L in DWELLS:
        # `ge_burst_len` in the model is the mean BAD run, the outage, and the chain is calibrated
        # so the stationary drop rate equals the rung's value at every dwell. So the good run is
        # `L * duty / (1 - duty)`, four times the outage at rung 3, and the duty is exactly the
        # rung's delivery fraction at every row. Getting this backwards would bench a channel the
        # batteries never run, which is the whole failure mode this file exists to prevent.
        l_off = float(L)
        l_on = float(L * duty / (1.0 - duty))
        pi_on = l_on / (l_on + l_off)
        pp = min(1.0, a.rate / pi_on)
        ek, exc = truth(l_on, l_off, pp, a.window)
        rng = np.random.default_rng(20260823 + L)
        vals = np.array([measure(rng, l_on, l_off, pp, a.window, a.steps) for _ in range(a.blocks)])
        m, sd = float(vals.mean()), float(vals.std(ddof=1))
        se = sd / np.sqrt(len(vals))
        bias = m - exc
        # `recovery`, the share of the true clustering recovered, is unusable when the truth sits
        # near 1: its denominator vanishes there and a bias of a thousandth reports as a factor.
        # What matters for CR-41 is the ABSOLUTE bias against the residual it is trying to measure.
        flag = ("OK" if abs(bias) < 0.2 * RESIDUAL else
                "MARGINAL" if abs(bias) < 0.5 * RESIDUAL else "UNREADABLE")
        print(f"{L:>6} {pi_on:6.3f} {ek:10.4f} {exc:9.4f} {m:10.4f} {bias:+9.4f} {se:8.4f}   {flag}")
    print(f"\nbias is measured minus true. CR-41 reads a residual of about {RESIDUAL:.2f}, so a")
    print("dwell whose bias is a fifth of that is readable, a half of it marginal, and more is not.")
    print("The TRUE column is the null CR-41 must be scored against at each dwell, and it is NOT")
    print("1.0: a gate faster than the window REGULARIZES the stream and pushes the true excess")
    print("below one, so a residual read against a fixed null of 1.0 at short dwells would be")
    print("measuring the gate's own smoothing rather than the retry cohort.")




if __name__ == "__main__":
    main()
