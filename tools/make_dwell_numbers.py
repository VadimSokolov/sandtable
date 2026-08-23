"""The four-term decomposition of console crowding, each term against an admissible reference.

The word "residual" meant three different things in this project's history and every disagreement
about it, ours and the reviewer's, was really a disagreement about which. With the dwell sweep re-run
so that each arm's delivered rate is logged, the terms separate cleanly:

  1. what a gated channel contributes, computed in closed form from its dwell and the delivered rate
  2. what a fleet with the reliance loop OPEN adds on top, which no channel property predicts
  3. what a fixed retry hold adds beyond that, which is the term the fade length governs
  4. what a randomized hold of the same mean adds, which is nothing

Term 1 comes from tools/bench_gate.py, evaluated at each arm's own dwell and own logged rate, which
is what makes the level readings admissible under the NULL_ARGS rule in tools/ar_gate.py. Term 3 is
a paired difference between two arms at a common configuration, so it needs no null at all.

Source: hopper/batteries/dwellow.sh, job 9447711.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from ar_read import find, load  # noqa: E402
from bench_gate import truth  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-dwellow-9447711.out"
DUTY = 0.8          # rung 3 delivers 80 percent of the time
WINDOW = 7


def null_for(L: float, rate: float) -> float:
    """The gated channel's own excess at this dwell and this delivered rate, in closed form."""
    l_off, l_on = L, L * DUTY / (1.0 - DUTY)
    pi_on = l_on / (l_on + l_off)
    return truth(l_on, l_off, min(1.0, rate / pi_on), WINDOW)[1]


def main() -> None:
    p = find(LOG)
    E, R = load(p, "D1", "arrival_excess"), load(p, "D1", "arrival_rate")
    dwells = sorted({k for a, k in E}, key=float)
    rows = []
    for L in dwells:
        cell = {}
        for arm in ("fix18", "jit18"):
            exc = sum(E[(arm, L)]) / len(E[(arm, L)])
            rate = sum(R[(arm, L)]) / len(R[(arm, L)])
            cell[arm] = (exc, null_for(float(L), rate), exc - null_for(float(L), rate))
        e, t, w, N = paired({"vals": E[("fix18", L)]}, {"vals": E[("jit18", L)]})
        rows.append((float(L), cell, e, t, w, N))

    jr = [r[1]["jit18"][2] for r in rows]
    fr = [r[1]["fix18"][2] for r in rows]
    gaps = [r[2] for r in rows]
    m = {
        "dwN": str(len(rows)), "dwLo": f"{rows[0][0]:.0f}", "dwHi": f"{rows[-1][0]:.0f}",
        "dwFold": f"{rows[-1][0] / rows[0][0]:.0f}",
        # Term 1: the channel's own contribution, which is not a fleet property.
        "dwNullLo": f"{min(r[1]['jit18'][1] for r in rows):.3f}",
        "dwNullHi": f"{max(r[1]['jit18'][1] for r in rows):.3f}",
        # Term 2: flat, so the claim is its range rather than its endpoints.
        "dwJitLo": f"{min(jr):.4f}", "dwJitHi": f"{max(jr):.4f}",
        "dwJitMean": f"{sum(jr) / len(jr):.3f}",
        "dwJitSpread": f"{max(jr) - min(jr):.4f}",
        # Term 3: the one the fade governs.
        "dwFixLo": f"{fr[0]:.3f}", "dwFixHi": f"{fr[-1]:.3f}",
        "dwGapLo": f"{gaps[0]:.3f}", "dwGapHi": f"{gaps[-1]:.3f}",
        "dwGapRising": str(sum(1 for a, b in zip(gaps, gaps[1:]) if b > a)),
        "dwGapSteps": str(len(gaps) - 1),
        "dwGapMinT": f"{min(abs(r[3]) for r in rows):.0f}",
        "dwBlocks": str(min(r[4] for r in rows)), "dwBlocksN": str(rows[0][5]),
    }
    gen = ROOT / "report" / "gen" / "dwell_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nFour-term crowding decomposition (source: tools/make_dwell_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    print(f"  channel term {m['dwNullLo']} to {m['dwNullHi']} over a {m['dwFold']}-fold dwell range")
    print(f"  jittered fleet sits {m['dwJitMean']} above it, spread only {m['dwJitSpread']}")
    print(f"  fixed hold adds {m['dwGapLo']} to {m['dwGapHi']} on top, "
          f"{m['dwGapRising']} of {m['dwGapSteps']} steps rising, |t| at least {m['dwGapMinT']}")


if __name__ == "__main__":
    main()
