"""Numbers for the second paper that do not depend on the search results.

The replication counts, the problem inventory and the measured scale mismatch in the textbook
bandit bonus are all properties of the benchmark rather than outcomes of running it, so they are
generated here and are available before any search lands. Results-dependent macros live in a
separate generator that reads the benchmark output.

The truth-table replication count is per metric and deliberately so, which is why the paper cannot
quote one number for it: a flat count buys a precise answer key on the cheap axis and a noisy one
on the dear axis, and the noisy one would then grade methods on exactly the axis this paper claims
is expensive.
"""
from __future__ import annotations

import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from sandtable.search.oracle import METRIC_REPS, TRUTH_SEED           # noqa: E402
from sandtable.search.problems import PROBLEMS                        # noqa: E402
from sandtable.search.methods import METHODS                          # noqa: E402

OUT = HERE.parent / "paper-search" / "gen" / "bench_numbers.tex"

# Measured on the qcap design set: the gap between the two best designs, and the per-mission
# spread, at the operating point each axis is read at. See tools/make_pinned_numbers.py's sibling
# measurement in experiments/results/.
SCALE = {"served_per_step": (0.00641, 0.0193),
         "success": (0.03333, 0.4325),
         "blue_loss_frac": (0.01917, 0.2468)}
NAME = {"served_per_step": "Srv", "success": "Succ", "blue_loss_frac": "Loss"}


TRUTH = HERE.parent / "experiments" / "results" / "search_truth"



def bounded_ratio(num: float, den: float, den_se: float) -> float:
    """A ratio whose denominator is a measurement, or a valid bound when it is not.

    Every ratio this file publishes goes through here. A denominator consistent with zero makes the
    ratio unbounded in variance and nearly entailed by whatever rule declared it unresolved, which
    is how a gap of 0.000094 plus or minus 0.003791 once became a published 52,317,293. Where the
    denominator clears two standard errors it is used directly; where it does not, it is replaced
    by that ceiling, which turns the quotient into a floor computed from two measured quantities.
    """
    if den_se < 0:
        raise ValueError("standard error cannot be negative")
    floor = 2.0 * den_se
    if den > floor:
        return num / den
    if floor <= 0:
        raise ValueError("denominator is zero with no error to bound it")
    return num / floor


def _key_cost() -> list[tuple[str, str]]:
    """What each problem's answer key can and cannot resolve.

    This used to extrapolate how many missions per design a table would need to separate its top
    two, as `reps * (2 se / gap) ** 2`. That number is not a measurement and it has been removed.
    The denominator is the observed gap, and a table is called UNRESOLVED precisely when that gap
    sits inside two standard errors of zero, so the extrapolation is ill-conditioned exactly on the
    problems it was quoted for. Worse, it is nearly entailed: put `gap = 0` and it returns the
    replication count already spent, put `gap = 2 se` and it returns a quarter of it, so for any
    unresolved table the answer lies in a fixed band whatever the data say. It reported fifty-two
    million missions for a gap of nine parts in a hundred thousand measured to plus or minus
    thirty-eight hundredths of a percent.

    That is the third genus of the first paper, met in a derived quantity rather than in a verdict:
    a number computed from a below-floor reading inherits the floor and cannot carry more than the
    reading did. So the question is replaced with one whose parts are both well measured: what is
    the smallest top-two gap this table could have detected, against how far the design axis moves
    the metric at all. Detectable gap is two standard errors of the difference; spread is best
    design to worst. Neither divides by a quantity consistent with zero."""
    import json
    import statistics

    rows, skipped = [], []
    for f in sorted(TRUTH.glob("*.json")):
        if f.stem.endswith(".difficulty"):
            continue
        if f.stem not in PROBLEMS:
            # A truth table for a cell that is not in the benchmark registry. The predict grid
            # writes its tables into this same directory, and globbing the directory rather than
            # iterating the registry would let a published inventory grow by thirty to thirty-two
            # because a file was dropped next to the others. Two of those cells sit at a metric
            # ceiling with a top-two gap and a standard error of exactly zero, so they would also
            # have taken a ratio to a denominator with no bound. Which problems are in the
            # benchmark is a registry decision, not a filesystem one.
            skipped.append(f.stem)
            continue
        d = json.loads(f.read_text())
        m = d.get("_meta", {})
        if not m.get("_crn"):
            continue                              # a table predating common random numbers
        gap, se, reps = m["_gap"], m["_se_top2"], m["_reps"]
        vals = [v for k, v in d.items() if not k.startswith("_")]
        spread = abs(max(vals) - min(vals))
        rows.append({"key": f.stem, "metric": m["_metric"], "res": bool(m["_resolved"]),
                     "spread": spread, "gap": gap, "se": se, "reps": reps,
                     "best": max(vals), "worst": min(vals),
                     "det": 2 * se, "frac": (2 * se / spread) if spread > 0 else float("inf"),
                     "noisy": gap < se,
                     "ratio": spread / gap if gap > 0 else float("inf")})
    if not rows:
        return []
    if skipped:
        print(f"  skipped {len(skipped)} truth tables not in the benchmark registry: "
              + ", ".join(sorted(skipped)))

    # The benchmark grades argmax on more problems than the tables resolve, because a problem
    # whose optimum was established by a separate registered study has a known argmax whatever its
    # own table can see. Publishing only one of the two counts is how a reader ends up comparing
    # eighteen against seventeen and finding neither wrong.
    from sandtable.search.problems import PROBLEMS as _P
    study = sum(1 for r in rows if not r["res"] and getattr(_P.get(r["key"]), "optimum", None))
    sizes = [_P[r["key"]].n_designs for r in rows if r["key"] in _P]
    out = [("BnKeyProblems", str(len(rows))),
           ("BnKeyResolved", str(sum(r["res"] for r in rows))),
           ("BnKeyUnresolved", str(sum(1 for r in rows if not r["res"]))),
           ("BnArgmaxFromStudy", str(study)),
           ("BnDesignsMax", str(max(sizes))), ("BnDesignsMin", str(min(sizes)))]
    for metric, tag in NAME.items():
        sub = [r for r in rows if r["metric"] == metric]
        if sub:
            out += [(f"BnKeyRes{tag}", str(sum(r['res'] for r in sub))),
                    (f"BnKeyN{tag}", str(len(sub)))]

    # The smallest gap each key could have detected, as a percentage of the room the design axis
    # has. Both halves are measured directly; nothing here divides by a quantity consistent with
    # zero. `BnKeyNoisy` counts the tables whose observed top-two gap is smaller than one standard
    # error of itself, which is the count the removed extrapolation was quietly built on.
    out.append(("BnKeyNoisy", str(sum(r["noisy"] for r in rows))))
    out.append(("BnKeyDetMed", f"{100 * statistics.median(r['frac'] for r in rows):.1f}"))
    for metric, tag in NAME.items():
        sub = [r for r in rows if r["metric"] == metric]
        if sub:
            w = max(sub, key=lambda r: r["frac"])
            out += [(f"BnKeyDet{tag}", f"{100 * statistics.median(r['frac'] for r in sub):.1f}"),
                    (f"BnKeyDetWorst{tag}", f"{100 * w['frac']:.0f}"),
                    (f"BnKeyDetWorst{tag}Key", w["key"].replace("_", r"\_"))]
    out.append(("BnKeyUnrankable", str(sum(r["frac"] > 1.0 for r in rows))))

    # Whether the unresolved success tables are unresolved because replication is expensive or
    # because the metric is pinned at its bound. The second would be a theorem rather than a cost,
    # and reporting it as a cost would be wrong. The test is reachability, the same question the
    # first paper's second genus of defect turns on: does the design axis still move this metric
    # further than the answer key can resolve? Where it does, the tie between the top two designs
    # is a measurement about the designs and not an artefact of the ceiling. Both halves are
    # measured, the span from best design to worst and two standard errors of the top-two
    # difference, and neither is a modelled quantity.
    succ = [r for r in rows if r["metric"] == "success"]
    if succ:
        moves = [r for r in succ if r["spread"] > r["det"]]
        wide = max(succ, key=lambda r: r["spread"])
        tight = min(succ, key=lambda r: r["spread"])
        out += [("BnBoundNSucc", str(len(succ))),
                ("BnBoundMoves", str(len(moves))),
                ("BnBoundWideKey", wide["key"].replace("_", r"\_")),
                ("BnBoundWideSpan", f"{wide['spread']:.3f}"),
                ("BnBoundWideBest", f"{wide['best']:.4f}"),
                ("BnBoundWideHead", f"{1.0 - wide['best']:.4f}"),
                ("BnBoundCeilKey", tight["key"].replace("_", r"\_")),
                ("BnBoundCeilSpan", f"{tight['spread']:.4f}"),
                ("BnBoundCeilBest", f"{tight['best']:.4f}"),
                ("BnBoundCeilDet", f"{tight['det']:.4f}")]
        if moves:
            out.append(("BnBoundMovesMin",
                        f"{min(r['spread'] / r['det'] for r in moves):.1f}"))

    # The quantity the paper's grading rule turns on: how much further the design axis moves the
    # metric than the two best designs differ from each other. Reported as a LOWER bound, because
    # the gap in the denominator is only a measurement where the table resolved it. Where it did
    # not, the gap is known only to be at most two standard errors, and dividing by that ceiling
    # gives a valid floor on the ratio from two quantities that are both measured. Where the table
    # did resolve, the gap exceeds two standard errors and the same expression returns it exactly.
    # A ratio whose denominator is consistent with zero is not reported at all.
    bnd = [bounded_ratio(r["spread"], r["gap"], r["se"]) for r in rows if r["spread"] > 0]
    out += [("BnSpreadOverGapMed", f"{statistics.median(bnd):.1f}"),
            ("BnSpreadOverGapMax", f"{max(bnd):.0f}"),
            ("BnCheaper", f"{statistics.median(bnd) ** 2:.0f}"),
            ("BnSpreadBounded", str(sum(1 for r in rows if not r["res"]))) ]
    return out


def main() -> None:
    out: list[tuple[str, str]] = []

    for m, r in METRIC_REPS.items():
        if m in NAME:
            out.append((f"BnReps{NAME[m]}", str(r)))
    out += [("BnRepsMin", str(min(METRIC_REPS.values()))),
            ("BnRepsMax", str(max(METRIC_REPS.values()))),
            ("BnRepsRatio", f"{max(METRIC_REPS.values()) / min(METRIC_REPS.values()):.0f}"),
            ("BnTruthSeed", f"{TRUTH_SEED:,}".replace(",", "{,}")),
            ("BnProblems", str(len(PROBLEMS))),
            ("BnMethods", str(len(METHODS)))]

    # The bandit-bonus mismatch. The bonus is UCB1's at eight pulls after a full first pass over
    # seven designs, which is where the allocator makes its first real decision.
    pulls, spent = 8, 64
    bonus = math.sqrt(2.0 * math.log(spent) / pulls)
    out.append(("BnBonus", f"{bonus:.3f}"))
    worst = 0.0
    for m, (gap, sd) in SCALE.items():
        out += [(f"BnGap{NAME[m]}", f"{gap:.5f}"),
                (f"BnSd{NAME[m]}", f"{sd:.4f}"),
                (f"BnBonusOverGap{NAME[m]}", f"{bonus / gap:.0f}")]
        worst = max(worst, bonus / gap)
    out.append(("BnBonusOverGapWorst", f"{worst:.0f}"))

    # WHAT THE ANSWER KEY COST, read off the truth tables rather than asserted. This is measured
    # before any method runs, which is what makes it a property of the benchmark: how much
    # simulation it takes to know the right answer, per (metric, operating point) pair.
    out += _key_cost()

    # The pilot allocation that shows the degeneracy, from the CR-72 registration.
    out += [("BnRawRatio", "1.33"), ("BnScaledRatio", "21.50"),
            ("BnRawHopeless", "48"), ("BnBestValue", "0.1476"), ("BnHopelessValue", "0.0029")]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("% generated by tools/make_bench_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {OUT} with {len(out)} macros")


if __name__ == "__main__":
    main()
