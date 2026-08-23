"""Does `arrival_fano` resolve a cohort component on a bursty channel? A bench with a known answer.

The paper wants to say that a retry cohort's variance is visible on a memoryless uplink and not on
a bursty one, because the channel's own burst variance sits on top of it. That is an instrument
claim, not a physics claim, and it should be measured on a stream whose Fano is known in closed
form before it is asserted about a stream whose Fano is not.

Construction. Arrivals per step are `N_t = K * B_t` with `B_t ~ Bernoulli(lambda / K)`, so the mean
is `lambda` for every K and the Fano is exactly `K - lambda`: a cohort of K raises the Fano by
`K - 1` and moves nothing else. That is the injected signal. It is then run through two channels
that deliver the same marginal rate:

  memoryless   every step admits, so the delivered stream is the injected one;
  on-off       a two-state Markov gate with mean dwells `L_on` / `L_off`, admitting at the inflated
               rate `lambda / pi` while on so the delivered marginal rate is again `lambda`.

The estimator is the shipped one: bin by `fano_window`, then population var over mean across bins
(`sandtable.metrics`, `arrival_fano`). Nothing here imports the simulator; the point is to test the
statistic in isolation, where the truth is arithmetic.

Usage:  python3 tools/bench_fano.py [--blocks 32] [--steps 1800]
"""
from __future__ import annotations

import argparse

import numpy as np


def fano(counts: np.ndarray, window: int) -> float:
    """The shipped estimator: bin, then population variance over mean across bins."""
    n = (len(counts) // window) * window
    b = counts[:n].reshape(-1, window).sum(axis=1).astype(float)
    m = b.mean()
    return float(b.var() / m) if m > 0 else 0.0


def inject(rng: np.random.Generator, steps: int, lam: float, K: int) -> np.ndarray:
    """Mean `lam` for every K; Fano exactly `K - lam`."""
    return K * (rng.random(steps) < lam / K).astype(np.int64)


def gate(rng: np.random.Generator, steps: int, l_on: float, l_off: float) -> np.ndarray:
    """A two-state on-off gate with geometric dwells; returns the boolean admit mask."""
    p_off, p_on = 1.0 / l_on, 1.0 / l_off      # leave-on, leave-off per step
    on = np.empty(steps, dtype=bool)
    s = True
    u = rng.random(steps)
    for t in range(steps):
        on[t] = s
        s = (u[t] >= p_off) if s else (u[t] < p_on)
    return on


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blocks", type=int, default=32)
    ap.add_argument("--steps", type=int, default=1800)
    ap.add_argument("--lam", type=float, default=0.15)
    ap.add_argument("--l-on", type=float, default=120.0)
    ap.add_argument("--l-off", type=float, default=120.0)
    a = ap.parse_args()

    pi = a.l_on / (a.l_on + a.l_off)
    print(f"lambda={a.lam}  blocks={a.blocks}  steps={a.steps}  on-off dwells "
          f"{a.l_on:.0f}/{a.l_off:.0f} (duty {pi:.2f})")
    print("Injected cohort K=2 raises the Fano of the SOURCE by exactly 1.000.\n")
    print(f"{'channel':>12} {'w':>3} {'F(K=1)':>9} {'F(K=2)':>9} {'recovered':>10} {'t':>8} "
          f"{'agree':>7} {'gate':>5}")

    for window in (1, 2, 4, 10, 120):
        for name in ("memoryless", "on-off"):
            f1, f2 = [], []
            for b in range(a.blocks):
                # Paired on the block seed: the same gate realization and the same uniform draws
                # serve both K arms, so the contrast is the cohort and nothing else.
                if name == "on-off":
                    mask = gate(np.random.default_rng([b, 7]), a.steps, a.l_on, a.l_off)
                    lam_on = min(a.lam / pi, 1.0)
                    for K, out in ((1, f1), (2, f2)):
                        src = inject(np.random.default_rng([b, K, 11]), a.steps, lam_on, K)
                        out.append(fano(src * mask, window))
                else:
                    for K, out in ((1, f1), (2, f2)):
                        src = inject(np.random.default_rng([b, K, 11]), a.steps, a.lam, K)
                        out.append(fano(src, window))
            d = np.array(f2) - np.array(f1)
            t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if d.std(ddof=1) > 0 else np.inf
            w = int(np.sum(d * d.mean() > 0))
            ok = abs(t) > 1.70 and abs(d.mean()) >= 0.03 and w / len(d) >= 0.6
            print(f"{name:>12} {window:>3} {np.mean(f1):9.4f} {np.mean(f2):9.4f} "
                  f"{d.mean():10.4f} {t:8.2f} {w:>4}/{len(d)} {'**' if ok else '~':>5}")
        print()


if __name__ == "__main__":
    main()
