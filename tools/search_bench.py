"""Driver for the design-space search benchmark.

    python3 tools/search_bench.py truth                       # ground-truth tables, all problems
    python3 tools/search_bench.py run --out results.jsonl     # the head-to-head
    python3 tools/search_bench.py report results.jsonl        # the table

Split into two commands on purpose. The truth tables are expensive, are computed once, and must be
computed on seeds disjoint from the searches, so recomputing them inside a sweep would be both
wasteful and a correctness hazard.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                              # noqa: E402

from sandtable.search import PROBLEMS, get                      # noqa: E402
from sandtable.search import oracle, runner                     # noqa: E402

BUDGETS = (64, 128, 256, 512, 1024)
METHODS = ("grid", "random", "halving", "ucb", "thompson", "gp_ei")


def _truth_cell(spec):
    """All benchmark metrics for one design at one operating point, at the dearest metric's reps.

    Grouped this way because metric-paired problems ARE the same missions scored differently, so
    running them separately would both waste the dear metric's replication count once per axis and
    quietly break the pairing the comparison depends on. Top level so a pool can pickle it.
    """
    key, design, reps = spec
    p = get(key)
    draws = oracle._draws(p, design, reps)
    return oracle._run_key(p, design), draws


def cmd_truth(a) -> None:
    keys = a.problems or list(PROBLEMS)
    probs = [get(k) for k in keys]

    # Group by (scenario, operating point). Every problem in a group draws the same missions; the
    # group runs once, at the replication count of its dearest axis, and each problem then scores
    # the slice it needs off those missions.
    groups: dict[str, list] = {}
    for p in probs:
        if not p.is_discrete:
            continue
        for d in p.designs():
            groups.setdefault(oracle._run_key(p, d), []).append((p, d))
    specs = [(g[0][0].key, g[0][1], max(oracle.truth_reps(q) for q, _ in g))
             for g in groups.values()]
    specs.sort(key=lambda s: -s[2])
    total = sum(s[2] for s in specs)
    print(f"{len(specs)} (operating point, design) cells, {total:,} missions, "
          f"{a.workers} workers", flush=True)

    done = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for rk, draws in ex.map(_truth_cell, specs):
            oracle._DRAWS[rk] = draws
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{len(specs)} cells", flush=True)

    for k in keys:
        p = get(k)
        if not p.is_discrete:
            continue
        t = oracle.truth(p, refresh=True)
        d, v = oracle.best_design(p, t)
        meta = json.loads(oracle._path(p).read_text())["_meta"]
        # A table whose leading gap sits inside its own noise cannot grade a search method. Say so
        # here rather than let it become a silent zero in the results.
        flag = "RESOLVED" if meta["_resolved"] else "*** UNRESOLVED, cannot grade ***"
        agree = ""
        if p.optimum:
            agree = "  key=" + ("AGREES" if oracle.agrees_with_key(p, t)
                                else "DISAGREES with " + json.dumps(p.optimum))
        print(f"{k:16s} best={json.dumps(d, sort_keys=True):32s} {v:.6f}  "
              f"gap={meta['_gap']:.6f} se={meta['_se_top2']:.6f}  {flag}{agree}", flush=True)


def _job(spec):
    """One (problem, method, budget, replicate). Top level so a process pool can pickle it."""
    k, m, b, r = spec
    res = runner.run_one(k, m, b, r)
    return {**res.__dict__}


def cmd_run(a) -> None:
    keys = a.problems or list(PROBLEMS)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Truth tables first, in the parent, so every worker reads a cached file rather than 16 workers
    # racing to compute the same table. This also fails fast if a table is missing.
    agrees, ladders, diffs = {}, {}, {}
    kept = []
    for k in keys:
        p = get(k)
        t = oracle.truth(p)
        meta = json.loads(oracle._path(p).read_text()).get("_meta", {})
        # A problem whose answer key cannot resolve its own top two designs is not a hard problem,
        # it is a problem with no answer, and grading a search method on it grades noise. Drop it,
        # loudly. Silent truncation of a benchmark reads downstream as "we covered everything".
        if not meta.get("_resolved", True):
            print(f"### {k:22s} DROPPED: the truth table cannot resolve its own top two "
                  f"(gap={meta.get('_gap', 0):.6f} <= 2 x se={meta.get('_se_top2', 0):.6f}) "
                  f"at {meta.get('_reps')} reps on {p.metric}", flush=True)
            continue
        kept.append(k)
        agrees[k] = oracle.agrees_with_key(p, t)
        diffs[k] = oracle.difficulty(p)
        ladders[k] = a.budgets or oracle.budget_ladder(p)
        d = diffs[k]
        print(f"### {k:22s} designs={p.n_designs:3d} metric={p.metric:16s} "
              f"gap={d['gap']:.5f} sd={d['sd_per_mission']:.5f} "
              f"reps/design={d['reps_per_design']:8.1f} "
              f"key={'agrees' if agrees[k] else 'DISAGREES'} ladder={ladders[k]}", flush=True)

    if len(kept) < len(keys):
        print(f"### {len(kept)} of {len(keys)} problems have a gradeable answer key", flush=True)
    keys = kept

    # Replicates are set PER PROBLEM to a fixed mission allowance, not held constant. A ladder
    # derived from difficulty spans very different totals across problems (tens of missions on a
    # low-noise throughput axis, tens of thousands on a mission-success axis), and holding
    # replicates constant across them would spend the whole allocation on the noisy problems and
    # then report the quiet ones at n=24 anyway. The allowance is stated rather than tuned, and the
    # realized replicate count per problem is recorded on every row so the reader can see which
    # problems are estimated less precisely.
    reps = {}
    for k in keys:
        per_config = 6 * sum(ladders[k]) if ladders[k] else 1     # one pass over methods
        reps[k] = int(min(a.replicates, max(a.min_replicates,
                                            a.allowance // max(per_config, 1))))
        print(f"    {k:22s} ladder-total={sum(ladders[k]):8d} replicates={reps[k]:3d} "
              f"missions~{per_config * reps[k]:9d}", flush=True)
    total = sum(6 * sum(ladders[k]) * reps[k] for k in keys)
    print(f"    TOTAL ~{total:,} missions across {len(keys)} problems", flush=True)

    specs = [(k, m, b, r) for k in keys for b in ladders[k]
             for m in a.methods for r in range(reps[k])]
    # The most expensive jobs first, so the pool does not finish with one worker on a 1024-budget
    # run while fifteen sit idle.
    specs.sort(key=lambda s: -s[2])
    print(f"{len(specs)} runs on {a.workers} workers", flush=True)

    t0 = time.time()
    n = 0
    with out.open("w") as fh, ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(_job, s): s for s in specs}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                row = fut.result()
            except Exception as e:                       # a method that dies is recorded, not fatal
                print(f"  !! {s} raised {type(e).__name__}: {e}", flush=True)
                continue
            k = row["problem"]
            fh.write(json.dumps({**row, "key_agrees": agrees[k], "metric": get(k).metric,
                                 "n_designs": get(k).n_designs,
                                 "reps_per_design": diffs[k]["reps_per_design"],
                                 "gap": diffs[k]["gap"],
                                 "sd_per_mission": diffs[k]["sd_per_mission"]}) + "\n")
            n += 1
            if n % 100 == 0:
                el = time.time() - t0
                fh.flush()
                print(f"  {n}/{len(specs)}  {el:6.0f}s  eta {el / n * (len(specs) - n):6.0f}s",
                      flush=True)
    print(f"\n{n} rows -> {out}  ({time.time() - t0:.0f}s)")


def cmd_report(a) -> None:
    rows = [json.loads(l) for l in open(a.results)]
    probs = sorted({r["problem"] for r in rows})
    methods = sorted({r["method"] for r in rows}, key=lambda m: METHODS.index(m)
                     if m in METHODS else 99)
    budgets = sorted({r["budget"] for r in rows})
    for stat, label in (("found", "hit rate on the registered optimum"), ("regret", "mean regret")):
        print(f"\n=== {label} ===")
        for p in probs:
            print(f"\n{p}")
            print(f"  {'budget':>7} " + " ".join(f"{m:>10s}" for m in methods))
            for b in budgets:
                cells = []
                for m in methods:
                    v = [r[stat] for r in rows
                         if r["problem"] == p and r["method"] == m and r["budget"] == b]
                    cells.append(f"{np.mean(v):10.4f}" if v else f"{'--':>10s}")
                print(f"  {b:>7d} " + " ".join(cells))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("truth"); t.add_argument("--problems", nargs="*")
    t.add_argument("--refresh", action="store_true")
    t.add_argument("--workers", type=int, default=8); t.set_defaults(fn=cmd_truth)
    r = sub.add_parser("run"); r.add_argument("--problems", nargs="*")
    r.add_argument("--out", default="experiments/results/search_bench.jsonl")
    r.add_argument("--budgets", nargs="*", type=int, default=[],
                   help="override the per-problem ladder derived from difficulty")
    r.add_argument("--methods", nargs="*", default=list(METHODS))
    r.add_argument("--replicates", type=int, default=24,
                   help="upper bound on replicates per problem")
    r.add_argument("--min-replicates", type=int, default=8)
    r.add_argument("--allowance", type=int, default=300_000,
                   help="approximate mission budget per problem")
    r.add_argument("--workers", type=int, default=16); r.set_defaults(fn=cmd_run)
    p = sub.add_parser("report"); p.add_argument("results"); p.set_defaults(fn=cmd_report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
