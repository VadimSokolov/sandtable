#!/usr/bin/env python3
"""Emit paper two's Results macros from a benchmark sweep.

Every gate here is the project's full tier and comes from score_bench.py rather than being
reimplemented, so the prose and the registered verdicts cannot drift apart. Nothing in this file
chooses a threshold; score_bench.py owns them and it was committed before the sweep produced a row.

    python3 tools/make_results_numbers.py $ROOT/search/bench-r300.jsonl \
        --prev experiments/results/bench-wide.jsonl \
        --old  experiments/results/bench-all.jsonl

The shipping sweep is `search/bench-r300.jsonl` under the cluster root, 540,000 rows from hopper job
st-search-9471782. There is a similarly named `experiments/results/bench-r300.jsonl` holding a
17,610-row fragment, and running this generator against it silently produces a complete-looking set
of macros from a thirtieth of the data. Check the row count the run prints before shipping anything.

--prev is the earlier, lower-replicate sweep of the same suite, and --old the sweep that ran on the
superseded budget ladder. The paper reports a verdict that changed when the replicate count rose and
a headline that changed when the ladder was corrected. A reader cannot check either against a number
typed into the prose from memory, so both are regenerated here, on the same method pair and through
the same gate as the sweep that supersedes them.
"""
from __future__ import annotations

import collections
import pathlib
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from score_bench import load, paired, gate, spread_of, mid_rungs      # noqa: E402
from sandtable.search.problems import PROBLEMS               # noqa: E402

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


def short_of_separation(rows) -> tuple[int, int]:
    """How many of a sweep's problems have their TOP rung below the budget that separates the top
    two designs.

    A method can only concentrate on evidence that ranks the arms. Where the ladder stops below
    that budget, no allocator can do better than uniform, so uniform wins as a property of the
    ladder rather than of the methods. This project shipped that mistake once and the count is
    reported rather than described, for both the ladder that made it and the one that replaced it.
    """
    from sandtable.search.oracle import difficulty
    from sandtable.search.problems import PROBLEMS
    top: dict = {}
    for r in rows:
        top[r["problem"]] = max(top.get(r["problem"], 0.0), r["budget"])
    short = have = 0
    for k, b in top.items():
        pr = PROBLEMS.get(k)
        sep = difficulty(pr).get("budget_to_separate") if pr else None
        if sep:
            have += 1
            short += b < sep
    return short, have


def balanced(rows):
    """Keep only cells that EVERY method reached, and return them with the cell set.

    Every method must be averaged over the same cells. A method added to a sweep later carries
    fewer, and a resume can leave a partial tail, so intersecting replicate NUMBERS is not enough:
    the unit is the (problem, budget, replicate) cell. Comparing a mean over sixty replicates
    against a mean over thirty is a comparison whose denominators differ, which is the defect this
    project's first paper is about.
    """
    seen = {}
    for r in rows:
        seen.setdefault((r["problem"], r["budget"], r["replicate"]), set()).add(r["method"])
    nm = len({r["method"] for r in rows})
    full = {c for c, ms in seen.items() if len(ms) == nm}
    kept = [r for r in rows if (r["problem"], r["budget"], r["replicate"]) in full]
    print(f"  cells reached by all {nm} methods: {len(full):,} of {len(seen):,}; "
          f"kept {len(kept):,} of {len(rows):,} rows")
    return kept, full


def main() -> None:
    argv = sys.argv[1:]
    prev_path = None
    old_path = None
    for flag in ("--prev", "--old"):
        if flag in argv:
            i = argv.index(flag)
            if flag == "--prev":
                prev_path = argv[i + 1]
            else:
                old_path = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
    if not argv:
        raise SystemExit(__doc__)
    rows = load(argv[0])
    if not rows:
        raise SystemExit("no rows")
    # Every method must be averaged over the SAME cells. A method added to a sweep later carries
    # fewer, and a resume can leave a partial tail, so intersecting replicate NUMBERS is not
    # enough: the unit is the (problem, budget, replicate) cell, and only a cell that every method
    # actually reached can be averaged. Comparing a mean over sixty against a mean over thirty is a
    # comparison whose denominators differ, which is the defect this project's first paper is about.
    rows, full = balanced(rows)
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
    try:
        from sandtable.search.oracle import reaches_separation
        from sandtable.search.problems import get as _g
        out.append(("RsReachSep", str(sum(1 for k in probs if reaches_separation(_g(k))))))
    except Exception:
        pass

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
    lose = {b: [] for b in BASELINES}
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
            elif g["verdict"] == "gate up":        # separates in the WORSE direction
                lose[b].append(m)
    # Both directions are published. A method that is decisively worse than the baseline has
    # separated from it just as surely as one that is decisively better, and a headline counting
    # only the favourable direction reports "nothing separates" about a set in which three methods
    # do. That is the same reading error this file corrects for CR-73 C below.
    for b in BASELINES:
        out += [(f"RsBeat{b.title()}", str(len(beat[b]))),
                (f"RsBeat{b.title()}Names",
                 ", ".join(x.replace("_", r"\_") for x in sorted(beat[b])) or "none"),
                (f"RsWorse{b.title()}", str(len(lose[b]))),
                (f"RsWorse{b.title()}Names",
                 ", ".join(x.replace("_", r"\_") for x in sorted(lose[b])) or "none")]

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
        # Which clause of the tier the top-rung verdict turns on. The gate has THREE clauses and
        # this used to check two, so it printed "clears both clauses" beside a verdict of
        # equivalent whenever the minimum practical effect was the one that bound. That is the
        # sentence a reader would have trusted most.
        from score_bench import MPE, T_MIN, SIGN_MIN
        big = abs(gt["eff"]) >= MPE * sp
        missed = [name for name, ok in (("the t statistic", abs(gt["t"]) >= T_MIN),
                                        ("sign consistency", gt["sign"] >= SIGN_MIN),
                                        ("the minimum practical effect", big)) if not ok]
        out += [("RsCrossTopBinds",
                 "clears every clause of the tier" if not missed
                 else "misses on " + " and ".join(missed)),
                ("RsCrossTopMpe", f"{MPE * sp:.4f}")]
        # The same contrast on an earlier, lower-replicate sweep of this suite. The paper says
        # a verdict changed when the replicate count rose; this is the number that changed, taken
        # through the same gate on the same pair rather than typed in from a previous run's log.
        if prev_path:
            prev, _ = balanced(load(prev_path))
            pm = {r["method"] for r in prev}
            if hi_w in pm and lo_w in pm:
                pg = gate(paired(prev, hi_w, lo_w, "regret_frac", budgets=tier(prev)["Top"]),
                          spread_of(prev, "regret_frac"))
                out += [("RsPrevReplicates", str(len({r["replicate"] for r in prev}))),
                        ("RsPrevCrossTopEff", f"{pg['eff']:+.4f}"),
                        ("RsPrevCrossTopT", f"{pg['t']:+.2f}"),
                        ("RsPrevCrossTopVerdict", pg["verdict"])]
            else:
                print(f"  !! {prev_path} lacks {hi_w} or {lo_w}; no Prev macros emitted")
        # How far each ladder reached. The paper's first answer was an artefact of a ladder that
        # stopped below the learnable regime, and that is a count, not an adjective.
        sh, hv = short_of_separation(rows)
        out += [("RsLadderShort", str(sh)), ("RsLadderHave", str(hv))]
        if old_path:
            osh, ohv = short_of_separation(load(old_path))
            out += [("RsOldLadderShort", str(osh)), ("RsOldLadderHave", str(ohv))]
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

    # Coverage at the bottom rung. Every row carries the number of DISTINCT designs the method
    # actually evaluated, and at the bottom rung that column explains the whole low-budget result:
    # an allocator that never evaluates a design cannot return it, whatever it does with the
    # evidence it has. This is measured rather than inferred, and it replaces an earlier prose
    # explanation about unequal sampling variance that this column does not support.
    if grade:
        gset = set(grade)
        lo = rungs["Low"]
        cover = {}
        for m in meths:
            d = [r["distinct"] for r in rows if r["method"] == m and r["problem"] in gset
                 and r["budget"] in lo.get(r["problem"], ())]
            if d:
                cover[m] = st.mean(d)
        sizes = [PROBLEMS[k].n_designs for k in grade if k in PROBLEMS]
        if cover and sizes:
            n_mean = st.mean(sizes)
            uni, adp = min(cover, key=cover.get), max(cover, key=cover.get)
            out += [("RsLowDesigns", f"{n_mean:.1f}"),
                    ("RsLowTouchMost", f"{cover[adp]:.1f}"),
                    ("RsLowTouchMostName", adp.replace("_", r"\_")),
                    ("RsLowTouchLeast", f"{cover[uni]:.1f}"),
                    ("RsLowTouchLeastName", uni.replace("_", r"\_")),
                    ("RsLowTouchAdapt", f"{cover.get(hi_w, float('nan')):.1f}"),
                    ("RsLowTouchUni", f"{cover.get(lo_w, float('nan')):.1f}"),
                    ("RsLowCoverAdapt", f"{100 * cover.get(hi_w, 0) / n_mean:.0f}"),
                    ("RsLowCoverUni", f"{100 * cover.get(lo_w, 0) / n_mean:.0f}")]
            # CR-72's control by name, because the paragraph about it must not quote a coverage
            # figure computed for a different method that happens to match.
            if "ucb_raw" in cover:
                out += [("RsLowTouchRaw", f"{cover['ucb_raw']:.1f}"),
                        ("RsLowCoverRaw", f"{100 * cover['ucb_raw'] / n_mean:.0f}")]

    # CR-72's three registered predictions, scored exactly as they were written rather than at
    # whichever rung is convenient. M1 claimed equivalence to grid at EVERY budget on BOTH regret
    # and found-rate, so it is scored per rung and per metric and falsified by any single gate.
    # Scoring it at the top rung alone would have called it held, because that is the one rung
    # where the two are equivalent.
    #
    # The registration said "every problem whose answer key resolves". The set used here is the
    # sweep's gradeable set, which is that plus the one problem carrying an optimum from a separate
    # registered study, because a found-rate needs a known argmax and that problem has one. The
    # difference is a single problem and it is named rather than absorbed.
    if grade:
        gset = set(grade)
        sub = [r for r in rows if r["problem"] in gset]
        if {"ucb_raw", "grid"} <= set(meths):
            spr = {"regret_frac": spread_of(sub, "regret_frac"),
                   "found": spread_of(sub, "found")}
            gated = []
            for tag in ("Low", "Mid", "Top"):
                for fld in ("regret_frac", "found"):
                    g = gate(paired(sub, "ucb_raw", "grid", fld, budgets=rungs[tag]), spr[fld])
                    if g["verdict"] != "equivalent":
                        gated.append((tag, fld, g))
            out += [("RsMOneGates", str(len(gated))),
                    ("RsMOneOf", str(6)),
                    ("RsMOneVerdict", "refuted" if gated else "holds")]
            if gated:
                w = max(gated, key=lambda x: abs(x[2]["eff"]))
                # Direction is field-dependent and reading it off the sign alone is how a
                # sign gets reported backwards: lower normalized regret is better, higher argmax
                # recovery is better, and the two fields disagree about what a negative effect
                # means.
                better = (w[2]["eff"] < 0) if w[1] == "regret_frac" else (w[2]["eff"] > 0)
                out += [("RsMOneWorstRung", w[0].lower()),
                        ("RsMOneWorstField",
                         "normalized regret" if w[1] == "regret_frac" else "argmax recovery"),
                        ("RsMOneWorstEff", f"{w[2]['eff']:+.4f}"),
                        # Magnitude too, because prose that already names the direction reads
                        # "worse by -0.3990" if it is handed the signed value.
                        ("RsMOneWorstMag", f"{abs(w[2]['eff']):.4f}"),
                        ("RsMOneWorstT", f"{w[2]['t']:+.2f}"),
                        ("RsMOneWorstDir", "better than" if better else "worse than")]
        if {"ucb", "ucb_raw"} <= set(meths):
            g = gate(paired(sub, "ucb", "ucb_raw", "regret_frac", budgets=rungs["Mid"]),
                     spread_of(sub, "regret_frac"))
            out += [("RsMTwoEff", f"{g['eff']:+.4f}"), ("RsMTwoT", f"{g['t']:+.2f}"),
                    ("RsMTwoSign", f"{100 * g['sign']:.0f}"),
                    ("RsMTwoVerdict", "holds" if g["verdict"] == "gate down" else "refuted")]

    # CR-73 B and C, both of which the paper states in counts rather than in adjectives.
    #
    # B asked whether grading on argmax recovery and grading on normalized regret rank the methods
    # differently, so that the choice of grading rule changes the answer. C asked whether the
    # problems whose key cannot resolve its own top two still carry information about method
    # quality, which is what justifies keeping more than half the suite. C is therefore scored on
    # exactly those problems and not on the gradeable ones.
    if grade:
        gset, order = set(grade), {}
        for m in meths:
            reg = [r["regret_frac"] for r in rows if r["method"] == m and r["problem"] in gset]
            fnd = [1.0 if r["found"] else 0.0 for r in rows
                   if r["method"] == m and r["problem"] in gset]
            if reg and fnd:
                order[m] = (st.mean(reg), st.mean(fnd))
        if len(order) > 2:
            by_reg = sorted(order, key=lambda m: order[m][0])
            by_fnd = sorted(order, key=lambda m: -order[m][1])
            n = len(by_reg)
            d2 = sum((by_reg.index(m) - by_fnd.index(m)) ** 2 for m in order)
            rho = 1.0 - 6.0 * d2 / (n * (n * n - 1))
            same = sum(1 for pb in grade
                       if min((m for m in meths),
                              key=lambda m: st.mean([r["regret_frac"] for r in rows
                                                     if r["method"] == m and r["problem"] == pb]
                                                    or [9e9]))
                       == max((m for m in meths),
                              key=lambda m: st.mean([1.0 if r["found"] else 0.0 for r in rows
                                                     if r["method"] == m and r["problem"] == pb]
                                                    or [-1.0])))
            out += [("RsRankSpearman", f"{rho:.3f}"),
                    ("RsRankSame", str(same)), ("RsRankProblems", str(len(grade)))]

    unres = sorted({r["problem"] for r in rows} - set(grade))
    if unres and "random" in meths:
        # C's falsifier was registered as a TWO-clause rule, |t| above T_MIN with SIGN_MIN sign
        # consistency, and it is scored as registered. The full tier adds a minimum practical
        # effect, and the count under that third clause is emitted beside it rather than instead
        # of it, because swapping a rule for a stricter one after seeing the answer is the move
        # this project exists to catch.
        # The registration put no rung restriction on this contrast, so it is scored over the
        # whole ladder, and separation is counted in BOTH directions. A problem set that can tell
        # a bad method from random carries information about method quality just as surely as one
        # that can tell a good method from random, and counting only the favourable direction
        # would answer a question nobody registered.
        from score_bench import MPE, T_MIN, SIGN_MIN
        sub = [r for r in rows if r["problem"] in unres]
        ssp = spread_of(sub, "regret_frac")
        better, worse, strict = [], [], 0
        for m in meths:
            if m == "random":
                continue
            g = gate(paired(sub, m, "random", "regret_frac"), ssp)
            if abs(g["t"]) >= T_MIN and g["sign"] >= SIGN_MIN:
                (better if g["eff"] < 0 else worse).append(m)
                strict += abs(g["eff"]) >= MPE * ssp
        out += [("RsSepUnresReg", str(len(better))),
                ("RsSepUnresRegNames", ", ".join(x.replace("_", r"\_") for x in better) or "none"),
                ("RsSepUnresWorse", str(len(worse))),
                ("RsSepUnresWorseNames", ", ".join(x.replace("_", r"\_") for x in worse) or "none"),
                ("RsSepUnresEither", str(len(better) + len(worse))),
                ("RsSepUnresTied", str(len(meths) - 1 - len(better) - len(worse))),
                ("RsSepUnres", str(strict)),
                ("RsSepUnresOf", str(len(meths) - 1)), ("RsSepUnresN", str(len(unres)))]

    # Pool reuse: how often a method asked for more missions of a design than the pool holds. A
    # sweep that wrapped a lot is resampling its own draws and the precision it reports is optimistic.
    ru = [r.get("reused", 0) for r in rows]
    out += [("RsReuse", f"{sum(ru):,}".replace(",", "{,}")),
            ("RsReuseRows", f"{100 * sum(1 for x in ru if x) / len(ru):.1f}")]

    # The full ranking, as a table rather than as ten macros a reader has to assemble. Emitted
    # from the same rows as every number above, sorted by the rung the paper's headline turns on,
    # so the ordering in the table and the ordering in the prose cannot disagree.
    lines = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
             r"& \multicolumn{3}{c}{normalized regret} & \multicolumn{3}{c}{argmax recovery (\%)} \\",
             r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
             r"method & low & mid & top & low & mid & top \\", r"\midrule"]
    stat = {}
    for m in meths:
        row = {}
        for tag in ("Low", "Mid", "Top"):
            reg = [r["regret_frac"] for r in rows if r["method"] == m
                   and r["budget"] in rungs[tag].get(r["problem"], ())]
            fnd = [1.0 if r["found"] else 0.0 for r in rows if r["method"] == m
                   and r["problem"] in set(grade)
                   and r["budget"] in rungs[tag].get(r["problem"], ())]
            row[tag] = (st.mean(reg) if reg else None, st.mean(fnd) if fnd else None)
        stat[m] = row
    for m in sorted(meths, key=lambda x: stat[x]["Top"][0] if stat[x]["Top"][0] is not None else 9e9):
        name = m.replace("_", r"\_")
        if m in BASELINES:
            name = rf"\textit{{{name}}}"
        cells = [f"{stat[m][tag][0]:.3f}" if stat[m][tag][0] is not None else "--"
                 for tag in ("Low", "Mid", "Top")]
        cells += [f"{100 * stat[m][tag][1]:.0f}" if stat[m][tag][1] is not None else "--"
                  for tag in ("Low", "Mid", "Top")]
        lines.append(f"{name} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]

    # How far apart the best and worst method are at each rung. This is the quantity that says
    # whether the choice of method matters, and it is the one a table of ten rows makes visible
    # and a pairwise contrast does not.
    # Range and interquartile range together. The range alone is set by whichever method is
    # worst, and on this suite that is a surrogate whose acquisition rule fails outright, so the
    # range says almost nothing about how much the choice among the other methods matters. The
    # IQR is a standard summary and is fixed here before looking at which methods land where.
    for tag in ("Low", "Mid", "Top"):
        v = sorted(stat[m][tag][0] for m in meths if stat[m][tag][0] is not None)
        if v:
            q = st.quantiles(v, n=4, method="inclusive") if len(v) > 3 else [v[0], v[0], v[-1]]
            out += [(f"RsRange{tag}", f"{v[-1] - v[0]:.3f}"),
                    (f"RsIqr{tag}", f"{q[2] - q[0]:.3f}")]
    lo_r = [stat[m]["Low"][0] for m in meths if stat[m]["Low"][0] is not None]
    hi_r = [stat[m]["Top"][0] for m in meths if stat[m]["Top"][0] is not None]
    if lo_r and hi_r and (max(hi_r) - min(hi_r)) > 0:
        out.append(("RsRangeShrink",
                    f"{(max(lo_r) - min(lo_r)) / (max(hi_r) - min(hi_r)):.1f}"))
    tab = pathlib.Path(__file__).resolve().parents[1] / "paper-search" / "gen" / "tab_methods.tex"
    tab.write_text("% generated by tools/make_results_numbers.py; do not edit\n"
                   + "\n".join(lines) + "\n")
    print(f"wrote {tab} with {len(meths)} method rows")

    body = "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in out) + "\n"
    for dest in OUT:
        p = pathlib.Path(__file__).resolve().parents[1] / dest
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("% generated by tools/make_results_numbers.py; do not edit\n" + body)
        print(f"wrote {p} with {len(out)} macros")


if __name__ == "__main__":
    main()
