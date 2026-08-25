#!/usr/bin/env python3
"""Emit paper two's Results macros from a benchmark sweep.

Every gate here is the project's full tier and comes from score_bench.py rather than being
reimplemented, so the prose and the registered verdicts cannot drift apart. Nothing in this file
chooses a threshold; score_bench.py owns them and it was committed before the sweep produced a row.

    python3 tools/make_results_numbers.py experiments/results/bench-pool.jsonl
"""
from __future__ import annotations

import collections
import pathlib
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from score_bench import load, paired, gate, spread_of, mid_rungs      # noqa: E402

OUT = ["paper-search/gen/results_numbers.tex"]
# Written out as words because a LaTeX macro name cannot contain a digit.
WORD = {"grid": "Grid", "random": "Random", "halving": "Halving", "ucb": "Ucb",
        "ucb_raw": "UcbRaw", "ucb_pooled": "UcbPooled", "thompson": "Thompson",
        "gp_ei": "GpEi", "gp_raw": "GpRaw", "gp_noisy": "GpNoisy"}
BASELINES = ("grid", "random")


def tier(rows):
    """Low, middle and top rung of each problem's ladder, as three separate budget selections."""
    by = collections.defaultdict(set)
    for r in rows:
        by[r["problem"]].add(r["budget"])
    lo = {k: (min(v),) for k, v in by.items()}
    hi = {k: (max(v),) for k, v in by.items()}
    return {"Low": lo, "Mid": mid_rungs(rows), "Top": hi}


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    rows = load(sys.argv[1])
    if not rows:
        raise SystemExit("no rows")
    meths = sorted({r["method"] for r in rows})
    probs = sorted({r["problem"] for r in rows})
    reps = len({r["replicate"] for r in rows})
    grade = sorted({r["problem"] for r in rows if r.get("gradeable")})

    out = [("RsRows", f"{len(rows):,}".replace(",", "{,}")),
           ("RsReplicates", str(reps)),
           ("RsMethods", str(len(meths))),
           ("RsProblems", str(len(probs))),
           ("RsGradeable", str(len(grade)))]

    # Mean normalized regret per method at each rung. Zero is the best design, one is the worst,
    # so these are comparable across problems and across metrics, which raw regret is not.
    rungs = tier(rows)
    for tag, sel in rungs.items():
        mean = {}
        for m in meths:
            v = [r["regret_frac"] for r in rows
                 if r["method"] == m and r["budget"] in sel.get(r["problem"], ())]
            if v:
                mean[m] = st.mean(v)
        for m, x in mean.items():
            out.append((f"Rs{tag}{WORD.get(m, m.title())}", f"{x:.3f}"))
        if mean:
            best = min(mean, key=mean.get)
            out += [(f"Rs{tag}Winner", best.replace("_", r"\_")),
                    (f"Rs{tag}WinnerRegret", f"{mean[best]:.3f}")]

    # Every method against both baselines at the top rung, gated. The count of methods that
    # actually separate is the headline the section turns on.
    sp = spread_of(rows, "regret_frac")
    beat = {b: [] for b in BASELINES}
    for b in BASELINES:
        for m in meths:
            if m == b:
                continue
            g = gate(paired(rows, m, b, "regret_frac", budgets=rungs["Top"]), sp)
            key = f"Rs{WORD.get(m, m.title())}Vs{b.title()}"
            out += [(key + "Eff", f"{g['eff']:+.4f}"), (key + "T", f"{g['t']:+.2f}"),
                    (key + "Verdict", g["verdict"])]
            if g["verdict"] == "gate down":       # lower regret is better
                beat[b].append(m)
    for b in BASELINES:
        out += [(f"RsBeat{b.title()}", str(len(beat[b]))),
                (f"RsBeat{b.title()}Names",
                 ", ".join(x.replace("_", r"\_") for x in sorted(beat[b])) or "none")]

    # Argmax recovery, on the problems whose key can actually rank its design set.
    if grade:
        for tag, sel in rungs.items():
            fr = {}
            for m in meths:
                v = [1.0 if r["found"] else 0.0 for r in rows
                     if r["method"] == m and r["problem"] in grade
                     and r["budget"] in sel.get(r["problem"], ())]
                if v:
                    fr[m] = st.mean(v)
            for m, x in fr.items():
                out.append((f"RsFound{tag}{WORD.get(m, m.title())}", f"{100 * x:.0f}"))
            if fr:
                out.append((f"RsFound{tag}Winner", max(fr, key=fr.get).replace("_", r"\_")))

    # The crossing itself, gated rather than eyeballed. The claim is that the sign of the
    # difference between the best low-budget method and the best top-budget method REVERSES between
    # the two rungs, so both contrasts are gated and both are reported.
    lo_w = min((m for m in meths), key=lambda m: st.mean(
        [r["regret_frac"] for r in rows if r["method"] == m
         and r["budget"] in rungs["Low"].get(r["problem"], ())] or [9e9]))
    hi_w = min((m for m in meths), key=lambda m: st.mean(
        [r["regret_frac"] for r in rows if r["method"] == m
         and r["budget"] in rungs["Top"].get(r["problem"], ())] or [9e9]))
    out += [("RsCrossLow", lo_w.replace("_", r"\_")), ("RsCrossTop", hi_w.replace("_", r"\_"))]
    if lo_w != hi_w:
        for tag in ("Low", "Top"):
            g = gate(paired(rows, hi_w, lo_w, "regret_frac", budgets=rungs[tag]), sp)
            out += [(f"RsCross{tag}Eff", f"{g['eff']:+.4f}"), (f"RsCross{tag}T", f"{g['t']:+.2f}"),
                    (f"RsCross{tag}Sign", f"{100 * g['sign']:.0f}"),
                    (f"RsCross{tag}Verdict", g["verdict"]),
                    (f"RsCross{tag}N", f"{g['n']:,}".replace(",", "{,}"))]
        out.append(("RsCrossReal",
                    "yes" if all(x[0] != f"RsCross{tg}Verdict" or x[1] != "equivalent"
                                 for tg in ("Low", "Top") for x in out) else "no"))

    # Pool reuse: how often a method asked for more missions of a design than the pool holds. A
    # sweep that wrapped a lot is resampling its own draws and the precision it reports is optimistic.
    ru = [r.get("reused", 0) for r in rows]
    out += [("RsReuse", f"{sum(ru):,}".replace(",", "{,}")),
            ("RsReuseRows", f"{100 * sum(1 for x in ru if x) / len(ru):.1f}")]

    body = "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in out) + "\n"
    for dest in OUT:
        p = pathlib.Path(__file__).resolve().parents[1] / dest
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("% generated by tools/make_results_numbers.py; do not edit\n" + body)
        print(f"wrote {p} with {len(out)} macros")


if __name__ == "__main__":
    main()
