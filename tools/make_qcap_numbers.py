"""CR-48 and CR-49: what bounding the console's backlog is worth, and how wrong you can size it.

Reads the fine lambda scans produced by `tools/queue_kstar.py`, the second and independent
implementation of the console queue, and writes the macros the manuscript inputs.

The scan asks, for each lambda = (P - 2L) mu, how much useful service a console delivers at each
backlog bound. The naive reading is "find the argmax and check the closed form predicts it". That
reading is wrong here and the script deliberately does not offer it: the response is a plateau
whose width grows with lambda, so the highest pixel on a flat ridge is noise. Every statement below
is instead about PLATEAU MEMBERSHIP, where the plateau is every bound delivering within one
material effect, `ar_gate.rate_floor()`, of the best one.

Regenerate the inputs with, for n in 8, 12, 24:

    LAM=$(python3 -c "print(','.join(f'{1.3+0.1*i:.2f}' for i in range(67)))")
    PYTHONPATH=src python3 tools/queue_kstar.py --lam "$LAM" --n $n --reps 12 \
        --horizon 40000 --caps=-1,0,1,2,3,4,5,6,7,8 > report/data/queue/kscan-n$n.txt
"""
from __future__ import annotations

import math
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import rate_floor  # noqa: E402

# `FULL_MPE` is a FRACTION of capacity, not a rate. Using it directly as a threshold on
# served_per_step is a factor of 6.7 too generous and swallows the whole capacity ladder into one
# plateau; the first version of this script did exactly that. `rate_floor()` is the rate.
MPE = rate_floor()

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAPS = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8]
RULES = {"floor": lambda x: math.floor(x) - 1,
         "third": lambda x: math.floor(x + 1.0 / 3.0) - 1,
         "half": lambda x: math.floor(x + 0.5) - 1}


def read(n: int) -> list[tuple[float, dict[int, float]]]:
    rows = []
    for ln in (ROOT / "report" / "data" / "queue" / f"kscan-n{n}.txt").read_text().splitlines():
        m = re.match(r"\s*([\d.]+)\s+([\d.]+) \| (.*) \|", ln)
        if m:
            rows.append((float(m.group(2)),
                         dict(zip(CAPS, [float(x) for x in m.group(3).split()]))))
    if not rows:
        raise SystemExit("no scan rows parsed; regenerate with the command in this file's docstring")
    return rows


def plateau(v: dict[int, float]) -> list[int]:
    best = max(v.values())
    return [c for c, x in v.items() if c >= 0 and best - x <= MPE]


def main() -> None:
    out, loads = [], (8, 12, 24)
    scans = {n: read(n) for n in loads}

    # 1. What bounding is worth at all, against the unbounded buffer the console has today.
    ratios = [max(v[c] for c in CAPS if c >= 0) / max(v[-1], 1e-9) for _, v in scans[12]]
    out.append(("QcapUnboundedGainMin", f"{min(ratios):.0f}"))
    out.append(("QcapUnboundedGainMed", f"{sorted(ratios)[len(ratios) // 2]:.0f}"))

    # 2. Which direction of mis-sizing hurts. The first version of this script averaged over all
    #    loads and reported a single asymmetry; that number is a mixture of two opposite regimes and
    #    meant nothing. A length cap does not have a fixed meaning in time: at high arrival rates a
    #    buffer of k is a short delay because it is refilled constantly, and at low rates the same k
    #    is a long one. So the direction of the risk REVERSES with load, and the honest statistic is
    #    per load.
    for n in loads:
        lo, hi, over = [], [], 0
        for _lam, v in scans[n]:
            k = max((c for c in CAPS if c >= 0), key=lambda c: v[c])
            best = v[k]
            if k - 1 >= 0 and k + 1 in v and best > 0:
                a, b = 100.0 * (best - v[k - 1]) / best, 100.0 * (best - v[k + 1]) / best
                lo.append(a)
                hi.append(b)
                over += b > a
        out.append((f"QcapUnderCost{n}", f"{sum(lo) / len(lo):.1f}"))
        out.append((f"QcapOverCost{n}", f"{sum(hi) / len(hi):.1f}"))
        out.append((f"QcapOverWorseFrac{n}", f"{100.0 * over / len(lo):.0f}"))

    # 3. Plateau geometry: the lower edge barely moves, the upper edge tracks lambda.
    edges = [(lam, min(plateau(v)), max(plateau(v))) for lam, v in scans[12]]
    wide = [(hi_ - lo_ + 1) for _l, lo_, hi_ in edges]
    out.append(("QcapPlateauLoMin", f"{min(e[1] for e in edges)}"))
    out.append(("QcapPlateauLoMax", f"{max(e[1] for e in edges)}"))
    out.append(("QcapPlateauWideMax", f"{max(wide)}"))
    for n in loads:
        sharp = sum(1 for _l, v in scans[n] if len(plateau(v)) <= 2)
        out.append((f"QcapSharp{n}", f"{sharp}"))
    out.append(("QcapLamMax", f"{max(e[0] for e in edges):.1f}"))

    # 4. How the three candidate rules score, and where the published one fails.
    for name, f in RULES.items():
        miss = [(n, lam) for n in loads for lam, v in scans[n] if f(lam) not in plateau(v)]
        tag = name.capitalize()
        out.append((f"Qcap{tag}Miss", f"{len(miss)}"))
        if miss:
            out.append((f"Qcap{tag}MissLo", f"{min(m[1] for m in miss):.1f}"))
            out.append((f"Qcap{tag}MissHi", f"{max(m[1] for m in miss):.1f}"))
    out.append(("QcapPoints", f"{sum(len(scans[n]) for n in loads)}"))

    # 5. Whether a single fixed bound would do, which is what a program office will actually ship.
    for fixed in (1, 2, 3):
        ok = [lam for n in loads for lam, v in scans[n] if fixed in plateau(v)]
        allm = [lam for n in loads for lam, v in scans[n]]
        out.append((f"QcapFixed{fixed}Frac", f"{100.0 * len(ok) / len(allm):.0f}"))
        bad = [lam for n in loads for lam, v in scans[n] if fixed not in plateau(v)]
        if bad:
            out.append((f"QcapFixed{fixed}BadHi", f"{max(bad):.1f}"))

    dst = ROOT / "report" / "qcap_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:24s} {v}")


if __name__ == "__main__":
    main()
