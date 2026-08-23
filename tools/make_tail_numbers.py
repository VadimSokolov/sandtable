"""CR-41 line two, and what a tail statistic says that a mean cannot.

Two questions land on the same battery. The first closes the four-term decomposition: a jittered
fleet was measured at the no-retry baseline at ONE dwell, and line two of the decomposition claims
it sits there at every dwell. The control that settles it is the no-retry arm run at all ten, so the
contrast is paired and every nuisance parameter cancels.

The second is what adversarial review asked for and is the more interesting half. `arrival_excess`
is a mean, and a mean cannot tell many small collisions from few large ones. `arrival_ge2` and
`arrival_ge3` are the fraction of busy service windows that saw two or more, and three or more,
distinct vehicles. Reading the three together decomposes the fade's effect into how OFTEN the
console is collided with and how DEEP the collision is, and they turn out to answer differently.

Source: hopper/batteries/dwellnr.sh, job 9448457.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_FRAC, FULL_MPE, FULL_T  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-dwellnr-9448457.out"


def series(d: dict, hi: str, lo: str, dwells: list[str]) -> list[tuple]:
    out = []
    for n in dwells:
        e, t, w, N = paired({"vals": d[(hi, n)]}, {"vals": d[(lo, n)]})
        base = sum(d[(lo, n)]) / len(d[(lo, n)])
        ok = abs(t) > FULL_T and w >= FULL_FRAC * N and abs(e) > FULL_MPE * abs(base)
        out.append((n, e, t, w, N, 100 * e / base, ok))
    return out


def main() -> None:
    p = find(LOG)
    m: dict[str, str] = {}
    ex = load(p, "N1", "arrival_excess")
    dwells = sorted({k for a, k in ex if a == "noretry"}, key=float)
    m["tlDwells"] = str(len(dwells))
    m["tlDwellLo"] = dwells[0]
    m["tlDwellHi"] = dwells[-1]
    m["tlFold"] = str(int(float(dwells[-1]) / float(dwells[0])))
    m["tlBlocks"] = str(len(ex[("noretry", dwells[0])]))

    # Line two: the jittered fleet against the no-retry control, at every dwell.
    jit = series(ex, "jit18", "noretry", dwells)
    m["tlJitGated"] = str(sum(1 for r in jit if r[6]))
    m["tlJitMaxPct"] = f"{max(abs(r[5]) for r in jit):.1f}"
    m["tlJitMaxAbs"] = f"{max(abs(r[1]) for r in jit):.4f}"

    # The three statistics on the fixed arm, which is where the fade's effect lives.
    for metric, tag in (("arrival_excess", "Exc"), ("arrival_ge2", "GeTwo"),
                        ("arrival_ge3", "GeThree")):
        s = series(load(p, "N1", metric), "fix18", "noretry", dwells)
        m[f"tl{tag}Gated"] = str(sum(1 for r in s if r[6]))
        m[f"tl{tag}Lo"] = f"{s[0][1]:+.4f}"
        m[f"tl{tag}Hi"] = f"{s[-1][1]:+.4f}"
        m[f"tl{tag}LoPct"] = f"{s[0][5]:.0f}"
        m[f"tl{tag}HiPct"] = f"{s[-1][5]:.0f}"
        m[f"tl{tag}MinT"] = f"{min(abs(r[2]) for r in s):.0f}"
        # The growth factor across the whole dwell range is the statistic the comparison is about:
        # a flat one says the fade changes how OFTEN, a rising one says how DEEP.
        m[f"tl{tag}Growth"] = f"{s[-1][1] / s[0][1]:.1f}"

    gen = ROOT / "report" / "gen" / "tail_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nThe tail of the arrival cohort (source: tools/make_tail_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    print(f"  line two: jitter against no-retry gates {m['tlJitGated']} of {m['tlDwells']} dwells, "
          f"largest {m['tlJitMaxPct']}%")
    for tag, nm in (("GeTwo", "two or more"), ("GeThree", "three or more"), ("Exc", "mean excess")):
        print(f"  {nm:14s}: {m[f'tl{tag}Lo']} to {m[f'tl{tag}Hi']} "
              f"({m[f'tl{tag}LoPct']}% to {m[f'tl{tag}HiPct']}%), growth {m[f'tl{tag}Growth']}x, "
              f"gated {m[f'tl{tag}Gated']}/{m['tlDwells']}")


if __name__ == "__main__":
    main()
