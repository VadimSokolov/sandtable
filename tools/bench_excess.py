"""Bench the collision-multiplicity instrument at its DEPLOYED window, against a closed form.

The Fano null was read through a window with almost no power, and the lesson generalized: a
deployed instrument setting is registration content and needs its own bench point before any
result read through it is believed. `arrival_excess` is deployed at `mult_window = 7`, one service
time at the scenario's 0.15 per step. This is that bench point, owed before CR-34 is read.

The same injected process as `bench_fano`: `N_t = K * B_t` with `B_t ~ Bernoulli(lambda / K)`, mean
`lambda` for every K. Over a window of w steps the number of arrivals is `K * Binomial(w, lambda/K)`,
so

    E[k | k >= 1] = lambda * w / (1 - (1 - lambda/K)^w)

and the Poisson control at the same rate is `lambda * w / (1 - exp(-lambda * w))`. The true excess
is therefore

    excess = (1 - exp(-lambda * w)) / (1 - (1 - lambda/K)^w)

which depends on K and lambda and nothing else. That is the ground truth the estimator is measured
against, at the window the batteries actually use and at the rates they actually run.

Usage:  python3 tools/bench_excess.py [--window 7] [--blocks 32] [--steps 1800]
"""
from __future__ import annotations

import argparse
import math

import numpy as np

from bench_fano import gate, inject


def excess(counts: np.ndarray, window: int) -> float:
    """The shipped statistic: E[k | k>=1] over the window, divided by Poisson at the same rate."""
    n = (len(counts) // window) * window
    b = counts[:n].reshape(-1, window).sum(axis=1).astype(float)
    busy = b > 0
    if not busy.any():
        return 0.0
    mult = b[busy].mean()
    lam_w = b.sum() / len(b)                      # arrivals per window = lambda * w
    pois = lam_w / (1.0 - math.exp(-lam_w)) if lam_w > 0 else 1.0
    return float(mult / pois)


def truth(lam: float, K: int, w: int) -> float:
    return (1.0 - math.exp(-lam * w)) / (1.0 - (1.0 - lam / K) ** w)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--blocks", type=int, default=32)
    ap.add_argument("--steps", type=int, default=1800)
    ap.add_argument("--l-on", type=float, default=120.0)
    ap.add_argument("--l-off", type=float, default=120.0)
    a = ap.parse_args()

    pi = a.l_on / (a.l_on + a.l_off)
    print(f"window={a.window} (one service time)  blocks={a.blocks}  steps={a.steps}  "
          f"on-off dwells {a.l_on:.0f}/{a.l_off:.0f}")
    print("Rates chosen to bracket what the batteries deliver (0.070 to 0.091 per step).\n")
    print(f"{'channel':>12} {'lambda':>7} {'K':>2} {'truth':>7} {'measured':>9} {'err %':>7} "
          f"{'t vs truth':>11}")

    for lam in (0.07, 0.09, 0.15):
        for K in (1, 2, 3):
            for name in ("memoryless", "on-off"):
                vals = []
                for b in range(a.blocks):
                    if name == "on-off":
                        mask = gate(np.random.default_rng([b, 7]), a.steps, a.l_on, a.l_off)
                        src = inject(np.random.default_rng([b, K, 11]), a.steps,
                                     min(lam / pi, 1.0), K)
                        vals.append(excess(src * mask, a.window))
                    else:
                        src = inject(np.random.default_rng([b, K, 11]), a.steps, lam, K)
                        vals.append(excess(src, a.window))
                v = np.array(vals)
                # On-off delivers at the same MARGINAL rate, so the truth is the same closed form.
                tr = truth(lam, K, a.window)
                d = v - tr
                t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if d.std(ddof=1) > 0 else np.inf
                print(f"{name:>12} {lam:>7.3f} {K:>2} {tr:>7.4f} {v.mean():>9.4f} "
                      f"{100 * (v.mean() - tr) / tr:>7.2f} {t:>11.2f}")
        print()


if __name__ == "__main__":
    main()
