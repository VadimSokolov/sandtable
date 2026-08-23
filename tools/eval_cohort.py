"""Evaluate CR-34 against its AMENDED predictions, with the instrument's own floor subtracted.

The amendment (doc/autoresearch-conjectures.md, CR-34 AMENDMENT) established two things that this
evaluation has to respect and a naive read would not.

  1. A perfectly scattered source does NOT read 1.0. A Bernoulli count is under-dispersed against
     Poisson, so the scatter reference is about 0.97 and depends on the delivered rate.
  2. An on-off gate reads HIGH even with no cohort in the source: 1.026 to 1.032 at the deployed
     geometry and the batteries' rates. The gate manufactures apparent clustering.

So P1 ("the memoryless jittered arm reaches the scatter reference") and P2 ("the GE jittered arm
stays above it") must both be judged against the bench floor at each arm's own MEASURED delivered
rate, not against 1.0. `tools/bench_excess.py` supplies the floor; this script interpolates it.

Within-channel contrasts (jit against fix at the same mean hold) are reported unadjusted, because
the floor is common to both arms and differences away.

Usage:  python3 tools/eval_cohort.py <logfile>
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import paired  # noqa: E402

TCRIT, MINWIN = 1.70, 0.6


def floor_for(rate: float, window: int, channel: str) -> float:
    """The instrument's reading for a source with NO cohort at the given delivered rate.

    Closed form for the memoryless case, where the bench showed the estimator exact to under 1%:
    a Bernoulli(lambda) source over a w-step window reads `(1-e^{-lw}) / (1-(1-lambda)^w)`. The
    on-off case has no closed form, so it carries the bench's measured multiplicative bias, which
    ran +5.5% at lambda 0.070 and +6.7% at 0.090; linear in lambda over that span and applied as
    such, with the range stated rather than hidden.
    """
    lw = rate * window
    base = (1.0 - math.exp(-lw)) / (1.0 - (1.0 - rate) ** window) if 0 < rate < 1 else 1.0
    if channel != "ge":
        return base
    bias = 0.055 + (rate - 0.070) * (0.067 - 0.055) / (0.090 - 0.070)
    return base * (1.0 + bias)


def invert_rate(mult: float, excess: float, window: int) -> float:
    """Recover the delivered rate from the two logged statistics, exactly.

    `excess = mult / P(lw)` with `P(lw) = lw / (1 - e^{-lw})`, so `P` is known from the pair and
    `lw` follows by inversion. `P` is smooth and strictly increasing on `lw > 0` with `P -> 1` as
    `lw -> 0`, so a bisection is both safe and exact to machine precision. This is why the battery
    did not need to carry `arrival_rate` as a third metric: it is already in the two it carries.
    """
    if excess <= 0 or mult <= 0:
        return float("nan")
    target = mult / excess
    if target <= 1.0:
        return 0.0
    lo, hi = 1e-9, 50.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        val = mid / (1.0 - math.exp(-mid))
        if val < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi) / window


def load(path: pathlib.Path, sec_prefix: str, metric: str) -> dict:
    out, cur = {}, False
    for line in path.read_text().splitlines():
        if line.startswith("### "):
            cur = line.startswith(f"### {sec_prefix}") and f"({metric})" in line
        elif cur and line.startswith("AR_ROW"):
            f = dict(p.split("=", 1) for p in line.split()[1:])
            key = next(v for k, v in f.items() if k not in ("arm", "mean", "vals"))
            out[(f["arm"], key)] = [float(v) for v in f["vals"].split(",")]
    return out


def gate(e: float, t: float, w: int, n: int, mpe: float) -> str:
    return "**" if abs(t) > TCRIT and abs(e) >= mpe and w / n >= MINWIN else "~"


def main() -> None:
    path = pathlib.Path(sys.argv[1])
    print("CR-34, judged against the AMENDED predictions. Floors from tools/bench_excess.py.\n")

    for sec, chan, label in (("K1", "bern", "memoryless (P1: reaches its floor)"),
                             ("K2", "ge", "GE-120 (P2: stays above its floor)")):
        ex = load(path, sec, "arrival_excess")
        mult = load(path, sec, "arrival_multiplicity")
        if not ex:
            print(f"{sec}: not in the log yet")
            continue
        print(f"--- {label} ---")
        print(f"{'arm':>7} {'n':>3} {'rate':>7} {'floor':>7} {'excess':>7} {'above floor':>12} "
              f"{'gate':>5}")
        for (arm, n) in sorted(ex, key=lambda k: (k[0], int(k[1]))):
            if not arm.startswith("jit"):
                continue
            v = sum(ex[(arm, n)]) / len(ex[(arm, n)])
            mv = sum(mult[(arm, n)]) / len(mult[(arm, n)]) if (arm, n) in mult else float("nan")
            r = invert_rate(mv, v, 7)
            fl = floor_for(r, 7, chan) if r == r else float("nan")
            resid = [x - fl for x in ex[(arm, n)]]
            e, t, w, N = paired({"vals": resid}, {"vals": [0.0] * len(resid)})
            print(f"{arm:>7} {n:>3} {r:7.4f} {fl:7.4f} {v:7.4f} {e:+12.4f} "
                  f"{gate(e, t, w, N, 0.02):>5}  t={t:.1f} {w}/{N}")
        print()

    print("--- within-channel contrasts (floor is common, reported unadjusted) ---")
    for sec, chan in (("K1", "memoryless"), ("K2", "GE-120")):
        d = load(path, sec, "arrival_excess")
        if not d:
            continue
        for rho in ("04", "18"):
            for n in sorted({k[1] for k in d}, key=int):
                if (f"jit{rho}", n) not in d:
                    continue
                e, t, w, N = paired({"vals": d[(f"jit{rho}", n)]},
                                    {"vals": d[(f"fix{rho}", n)]})
                print(f"  {chan:>11} rho={rho} n={n:>3}  {e:+.4f}  t={t:7.2f}  {w:>2}/{N}  "
                      f"{gate(e, t, w, N, 0.02)}")
    print("\nP3 check: does GE dissolve MORE clustering and gain LESS goodput?")
    for sec, chan in (("K1", "memoryless"), ("K2", "GE-120")):
        g = load(path, sec, "operator_goodput")
        if not g:
            continue
        for n in sorted({k[1] for k in g}, key=int):
            if ("jit18", n) not in g:
                continue
            e, t, w, N = paired({"vals": g[("jit18", n)]}, {"vals": g[("fix18", n)]})
            print(f"  {chan:>11} n={n:>3} goodput {e:+.4f}  t={t:7.2f}  {w:>2}/{N}")


if __name__ == "__main__":
    main()
