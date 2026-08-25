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
    # Every method must be averaged over the SAME cells. A method added to a sweep later carries
    # fewer, and a resume can leave a partial tail, so intersecting replicate NUMBERS is not
    # enough: the unit is the (problem, budget, replicate) cell, and only a cell that every method
    # actually reached can be averaged. Comparing a mean over sixty against a mean over thirty is a
    # comparison whose denominators differ, which is the defect this project's first paper is about.
    seen = {}
    for r in rows:
        seen.setdefault((r["problem"], r["budget"], r["replicate"]), set()).add(r["method"])
    nm = len({r["method"] for r in rows})
    full = {c for c, ms in seen.items() if len(ms) == nm}
    dropped = len(rows)
    rows = [r for r in rows if (r["problem"], r["budget"], r["replicate"]) in full]
    print(f"  cells reached by all {nm} methods: {len(full):,} of {len(seen):,}; "
          f"kept {len(rows):,} of {dropped:,} rows")
    meths = sorted({r["method"] for r in rows})
    probs = sorted({r["problem"] for r in rows})
    reps = len({r["replicate"] for r in rows})
    grade = sorted({r["problem"] for r in rows if r.get("gradeable")})

    out = [("RsCells", f"{len(full):,}".replace(",", "{,}")),
           ("RsRows", f"{len(rows):,}".replace(",", "{,}")),
           ("RsReplicates", str(reps)),
           ("RsMethods", str(len(meths))),
           ("RsProblems", str(len(probs))),
           ("RsGradeable", str(len(grade))),
           ("RsRegretOnly", str(len(probs) - len(grade)))]

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
        # The rung means for the crossing pair, so the prose never hardcodes a method name.
        for tag in ("Low", "Mid", "Top"):
            for who, lab in ((lo_w, "Uni"), (hi_w, "Adapt")):
                v = [r["regret_frac"] for r in rows if r["method"] == who
                     and r["budget"] in rungs[tag].get(r["problem"], ())]
                if v:
                    out.append((f"RsCross{tag}{lab}", f"{v and st.mean(v):.3f}"))
                f = [1.0 if r["found"] else 0.0 for r in rows if r["method"] == who
                     and r["problem"] in grade and r["budget"] in rungs[tag].get(r["problem"], ())]
                if f:
                    out.append((f"RsCross{tag}{lab}Found", f"{100 * st.mean(f):.0f}"))
        # Which clause of the tier the top-rung verdict actually turned on. A contrast that clears
        # t and misses only sign consistency is a different statement from one that misses on both,
        # and collapsing them into "equivalent" hides which.
        gt = gate(paired(rows, hi_w, lo_w, "regret_frac", budgets=rungs["Top"]), sp)
        out.append(("RsCrossTopBinds",
                    "sign consistency alone" if abs(gt["t"]) >= 1.70 and gt["sign"] < 0.60
                    else "the t statistic" if abs(gt["t"]) < 1.70 and gt["sign"] >= 0.60
                    else "both t and sign consistency"))
        out.append(("RsCrossReal",
                    "yes" if all(x[0] != f"RsCross{tg}Verdict" or x[1] != "equivalent"
                                 for tg in ("Low", "Top") for x in out) else "no"))

    # The two discriminator arms, each a pair differing in exactly one estimator. They are here so
    # a reader can tell an implementation fault apart from a claim about adaptive search, and they
    # are emitted whatever they say.
    for a, b, tag in (("ucb_pooled", "ucb", "Var"), ("gp_noisy", "gp_ei", "Inc"),
                      ("ucb", "ucb_raw", "Scale"), ("gp_ei", "gp_raw", "Prior")):
        if a in meths and b in meths:
            g = gate(paired(rows, a, b, "regret_frac"), sp)
            out += [(f"RsDisc{tag}Eff", f"{g['eff']:+.4f}"), (f"RsDisc{tag}T", f"{g['t']:+.2f}"),
                    (f"RsDisc{tag}Sign", f"{100 * g['sign']:.0f}"),
                    (f"RsDisc{tag}Verdict", g["verdict"]),
                    (f"RsDisc{tag}N", f"{g['n']:,}".replace(",", "{,}"))]

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
