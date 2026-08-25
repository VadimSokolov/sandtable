"""Score the search benchmark against the predictions registered before it ran.

Written and committed BEFORE the benchmark produced a row, which is the only thing that makes the
verdicts below worth anything. Every threshold here comes from the registration log and none of them
were chosen after looking at results:

  CR-72 M1  `ucb_raw` is equivalent to `grid` on regret and found-rate at every budget on every
            problem whose key resolves. Falsified by gating away from `grid` on either.
  CR-72 M2  `ucb` gates UP against `ucb_raw` on regret at the middle rung of each ladder.
            Falsified by equivalent or worse.
  CR-72 M3  the advantage of `ucb` over `ucb_raw` is larger on axes with a worse gap-to-spread
            ratio, ordered served_per_step, blue_loss_frac, success. Falsified by no ordering or
            the reverse.
  CR-73 B   argmax recovery and regret rank methods differently. Retracted as academic if the two
            rankings agree at Spearman above 0.9 OR the same method wins at least ten of the twelve
            problems whose key resolves.
  CR-73 C   the eighteen problems with no resolvable argmax still carry information under regret.
            The drop stands if no method separates from `random` there at the full tier. The
            registration names the PROBLEM as the pairing unit, so sign consistency is counted
            across problems rather than across replicates; both are printed and the registered
            one decides.

The gate is the project's full tier throughout: |t| above 1.70, a minimum practical effect of 0.06
in units of the contrast's own spread, and sixty percent sign consistency across the pairing unit.
Methods are paired on the replicate, which is exactly what the pool-backed meter guarantees, so the
contrast is a paired difference and the variance that matters is the variance of that difference.

    python3 tools/score_bench.py results.jsonl
"""
from __future__ import annotations

import collections
import json
import math
import pathlib
import statistics as st
import sys

T_MIN, MPE, SIGN_MIN = 1.70, 0.06, 0.60
AXIS_ORDER = ["served_per_step", "blue_loss_frac", "success"]     # registered in CR-72 M3


def load(path):
    rows = []
    for ln in pathlib.Path(path).read_text().splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue                      # a line truncated by a kill mid-write
    return rows


def paired(rows, a, b, field, problems=None, budgets=None):
    """Per-replicate differences a minus b, pooled over the selected problems and budgets."""
    idx = collections.defaultdict(dict)
    for r in rows:
        if problems is not None and r["problem"] not in problems:
            continue
        if budgets is not None and r["budget"] not in budgets.get(r["problem"], ()):
            continue
        idx[(r["problem"], r["budget"], r["replicate"])][r["method"]] = r[field]
    diffs = [v[a] - v[b] for v in idx.values() if a in v and b in v]
    return diffs


def gate(diffs, spread):
    """The project's full tier, applied to a paired difference."""
    n = len(diffs)
    if n < 8:
        return {"n": n, "verdict": "insufficient", "eff": float("nan"), "t": float("nan"),
                "sign": float("nan")}
    eff = st.mean(diffs)
    sd = st.pstdev(diffs) if n > 1 else 0.0
    t = eff / (sd / math.sqrt(n)) if sd > 0 else (math.inf if eff else 0.0)
    nz = [d for d in diffs if d != 0]
    sign = (sum(1 for d in nz if (d > 0) == (eff > 0)) / len(nz)) if nz else 0.0
    big = abs(eff) >= MPE * spread if spread > 0 else abs(eff) > 0
    ok = abs(t) >= T_MIN and sign >= SIGN_MIN and big
    return {"n": n, "eff": eff, "t": t, "sign": sign,
            "verdict": ("gate up" if eff > 0 else "gate down") if ok else "equivalent"}


def spread_of(rows, field, problems=None):
    vals = [r[field] for r in rows if problems is None or r["problem"] in problems]
    return st.pstdev(vals) if len(vals) > 1 else 1.0


def mid_rungs(rows):
    """The middle rung of each problem's ladder, as CR-72 M2 specifies."""
    by = collections.defaultdict(set)
    for r in rows:
        by[r["problem"]].add(r["budget"])
    return {k: (sorted(v)[len(v) // 2],) for k, v in by.items()}


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    rows = load(sys.argv[1])
    if not rows:
        raise SystemExit("no rows")
    methods = sorted({r["method"] for r in rows})
    gradeable = sorted({r["problem"] for r in rows if r.get("gradeable")})
    ungradeable = sorted({r["problem"] for r in rows if not r.get("gradeable")})
    metric_of = {}
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
    from sandtable.search.problems import get
    for p in {r["problem"] for r in rows}:
        metric_of[p] = get(p).metric

    print(f"{len(rows):,} rows, {len(methods)} methods, "
          f"{len(gradeable)} argmax-gradeable problems, {len(ungradeable)} regret-only")
    print(f"gate: |t| >= {T_MIN}, MPE {MPE} of contrast spread, sign >= {SIGN_MIN:.0%}\n")

    sr = spread_of(rows, "regret_frac")
    sf = spread_of(rows, "found")

    # ---------------------------------------------------------------- CR-72 M1
    print("=" * 78)
    print("CR-72 M1: ucb_raw is equivalent to grid. FALSIFIED if it gates on either score.")
    m1_fired = []
    for field, spread in (("regret_frac", sr), ("found", sf)):
        g = gate(paired(rows, "ucb_raw", "grid", field, problems=gradeable), spread)
        print(f"  {field:12s} eff={g['eff']:+.4f} t={g['t']:+7.2f} "
              f"sign={g['sign']:.0%} n={g['n']:5d}  {g['verdict']}")
        if g["verdict"] != "equivalent":
            m1_fired.append(field)
    print(f"  VERDICT M1: {'REFUTED on ' + ', '.join(m1_fired) if m1_fired else 'HOLDS'}\n")

    # ---------------------------------------------------------------- CR-72 M2
    print("=" * 78)
    print("CR-72 M2: ucb gates UP against ucb_raw on regret at the middle rung.")
    print("          (regret is a LOSS, so gating up means the difference is NEGATIVE.)")
    mids = mid_rungs(rows)
    g = gate(paired(rows, "ucb", "ucb_raw", "regret_frac", problems=gradeable, budgets=mids), sr)
    print(f"  regret_frac eff={g['eff']:+.4f} t={g['t']:+7.2f} "
          f"sign={g['sign']:.0%} n={g['n']:5d}  {g['verdict']}")
    m2 = "HOLDS" if (g["verdict"] == "gate down") else "REFUTED"
    print(f"  VERDICT M2: {m2}\n")

    # ---------------------------------------------------------------- CR-72 M3
    print("=" * 78)
    print("CR-72 M3: the ucb-over-ucb_raw advantage is ordered "
          + " > ".join(AXIS_ORDER) + ".")
    adv = {}
    for axis in AXIS_ORDER:
        probs = [p for p in gradeable if metric_of[p] == axis]
        if not probs:
            print(f"  {axis:16s} no gradeable problem on this axis")
            continue
        gg = gate(paired(rows, "ucb", "ucb_raw", "regret_frac", problems=probs), sr)
        adv[axis] = -gg["eff"]                     # advantage = regret REDUCED
        print(f"  {axis:16s} advantage={adv[axis]:+.4f} t={gg['t']:+7.2f} "
              f"n={gg['n']:5d}  {gg['verdict']}")
    if len(adv) == len(AXIS_ORDER):
        got = [adv[a] for a in AXIS_ORDER]
        m3 = ("HOLDS" if got == sorted(got, reverse=True)
              else "REFUTED, reverse order" if got == sorted(got) else "REFUTED, no ordering")
    else:
        m3 = "cannot score, an axis has no gradeable problem"
    print(f"  VERDICT M3: {m3}\n")

    # ---------------------------------------------------------------- CR-73 B
    print("=" * 78)
    print("CR-73 B: argmax and regret rank methods differently.")
    print("         RETRACTED if Spearman > 0.9 or the same method wins >= 10 of 12 problems.")

    def rank(field, probs, lower_better):
        sc = {m: st.mean([r[field] for r in rows
                          if r["method"] == m and r["problem"] in probs]) for m in methods}
        order = sorted(sc, key=lambda m: sc[m], reverse=not lower_better)
        return {m: i for i, m in enumerate(order)}, sc

    rk_f, sc_f = rank("found", gradeable, lower_better=False)
    rk_r, sc_r = rank("regret_frac", gradeable, lower_better=True)
    d2 = sum((rk_f[m] - rk_r[m]) ** 2 for m in methods)
    n = len(methods)
    rho = 1 - 6 * d2 / (n * (n * n - 1)) if n > 2 else float("nan")
    print(f"  {'method':12s} {'found':>8s} {'rank':>5s} {'regret':>8s} {'rank':>5s}")
    for m in sorted(methods, key=lambda m: rk_r[m]):
        print(f"  {m:12s} {sc_f[m]:8.3f} {rk_f[m]:5d} {sc_r[m]:8.4f} {rk_r[m]:5d}")
    same = 0
    for p in gradeable:
        wf = max(methods, key=lambda m: st.mean(
            [r["found"] for r in rows if r["method"] == m and r["problem"] == p] or [0]))
        wr = min(methods, key=lambda m: st.mean(
            [r["regret_frac"] for r in rows if r["method"] == m and r["problem"] == p] or [1]))
        same += (wf == wr)
    print(f"  Spearman rho = {rho:.3f}; the same method wins both scores on "
          f"{same} of {len(gradeable)} problems")
    b = "RETRACTED" if (rho > 0.9 or (gradeable and same >= 10)) else "HOLDS"
    print(f"  VERDICT B: {b}\n")

    # ---------------------------------------------------------------- CR-73 C
    print("=" * 78)
    print("CR-73 C: the regret-only problems still carry information.")
    print("         The drop STANDS if no method separates from random there.")
    # The registration says "paired by problem", so the unit of sign consistency is the PROBLEM and
    # not the replicate. Both are reported: the per-problem test is the one registered and decides
    # the verdict, the per-replicate one sits beside it because pooling replicates is what the gate
    # does everywhere else here and a reader will look for it.
    sep = []
    print(f"  {'method':12s} {'per problem (REGISTERED)':>44s} {'per replicate':>30s}")
    for m in methods:
        if m == "random":
            continue
        per_prob = [st.mean(d) for d in
                    (paired(rows, m, "random", "regret_frac", problems={q}) for q in ungradeable)
                    if d]
        gp = gate(per_prob, st.pstdev(per_prob) if len(per_prob) > 1 else 1.0)
        gr = gate(paired(rows, m, "random", "regret_frac", problems=ungradeable), sr)
        mark = " <--" if gp["verdict"] != "equivalent" else ""
        print(f"  {m:12s} eff={gp['eff']:+.4f} t={gp['t']:+6.2f} "
              f"sign={gp['sign']:.0%} n={gp['n']:3d} {gp['verdict']:11s}"
              f" | eff={gr['eff']:+.4f} t={gr['t']:+7.2f} {gr['verdict']:11s}{mark}")
        if gp["verdict"] != "equivalent":
            sep.append(m)
    c = f"HOLDS, {len(sep)} of {len(methods) - 1} methods separate" if sep else "DROP STANDS"
    print(f"  VERDICT C: {c}\n")

    # ---------------------------------------------------------------- discriminators
    print("=" * 78)
    print("Discriminators. These were added to tell a broken estimator apart from a claim about")
    print("adaptive search, and they are reported whatever they say.")
    for a, b_, why in (("ucb_pooled", "ucb", "pooled vs per-arm variance"),
                       ("gp_noisy", "gp_ei", "posterior vs observed incumbent")):
        if a in methods and b_ in methods:
            gg = gate(paired(rows, a, b_, "regret_frac"), sr)
            print(f"  {a:12s} vs {b_:10s} eff={gg['eff']:+.4f} t={gg['t']:+7.2f} "
                  f"n={gg['n']:5d}  {gg['verdict']}   ({why})")

    reuse = sum(r.get("reused", 0) for r in rows)
    print(f"\npool reuse across every run: {reuse}"
          + ("  (a nonzero count means some rung outran its pool)" if reuse else "  (none)"))


if __name__ == "__main__":
    main()
