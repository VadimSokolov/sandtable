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


def _cells(keys):
    """Every (operating point, design) cell and the replication count it must reach.

    Grouped by run key rather than by problem: metric-paired problems ARE the same missions scored
    differently, so a group runs once at the replication count of its dearest axis and each problem
    then reads the slice it needs.
    """
    groups: dict[str, list] = {}
    for p in (get(k) for k in keys):
        if not p.is_discrete:
            continue
        for d in p.designs():
            groups.setdefault(oracle._run_key(p, d), []).append((p, d))
    specs = [(g[0][0].key, g[0][1], max(oracle.truth_reps(q) for q, _ in g))
             for g in groups.values()]
    specs.sort(key=lambda s: (-s[2], s[0], json.dumps(s[1], sort_keys=True)))
    return specs


def cmd_pools(a) -> None:
    """Compute and store the per-mission pools for one shard of the cells.

    Split out from `truth` so the expensive half can be sized for BACKFILL. The whole answer key is
    half a million missions, which as one job waited more than a day behind the account's other
    work; as sixteen shards of twenty minutes each it slots into gaps the scheduler is already
    leaving. The shards write disjoint files and no shard reads another's, so they are independent
    and a lost one is re-runnable on its own. `truth` afterwards runs no missions at all: it reads
    the pools off disk and reduces them.
    """
    specs = _cells(a.problems or list(PROBLEMS))
    mine = [s for i, s in enumerate(specs) if i % a.of == a.shard]
    total = sum(s[2] for s in mine)
    print(f"shard {a.shard}/{a.of}: {len(mine)} of {len(specs)} cells, {total:,} missions",
          flush=True)
    done = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for _rk, _draws in ex.map(_truth_cell, mine):
            done += 1
            print(f"  {done}/{len(mine)} cells", flush=True)
    print("### POOLS DONE", flush=True)


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


_BACKEND = "sim"


def _job(spec):
    """One (problem, method, budget, replicate). Top level so a process pool can pickle it."""
    k, m, b, r = spec
    res = runner.run_one(k, m, b, r, backend=_BACKEND)
    return {**res.__dict__}


def _init_worker(backend: str) -> None:
    global _BACKEND
    _BACKEND = backend


def cmd_run(a) -> None:
    global _BACKEND
    _BACKEND = a.backend
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
        # A problem whose answer key cannot resolve its own top two designs has no argmax to
        # recover, so its `found` column would be a coin flip dressed as a score. It is KEPT and
        # graded on regret, which asks how far the returned design sits from the best one rather
        # than which of two statistically tied designs is best, and is roughly eighty times cheaper
        # to answer here. The flag rides on every row so the report can grade either way, and the
        # count is printed, because silent truncation of a benchmark reads downstream as "we
        # covered everything".
        if not meta.get("_resolved", True):
            print(f"### {k:22s} REGRET-ONLY: the truth table cannot resolve its own top two "
                  f"(gap={meta.get('_gap', 0):.6f} <= 2 x se={meta.get('_se_top2', 0):.6f}) "
                  f"at {meta.get('_reps')} reps on {p.metric}", flush=True)
        kept.append(k)
        agrees[k] = oracle.agrees_with_key(p, t)
        diffs[k] = oracle.difficulty(p)
        ladders[k] = a.budgets or oracle.budget_ladder(p)
        d = diffs[k]
        print(f"### {k:22s} designs={p.n_designs:3d} metric={p.metric:16s} "
              f"gap={d['gap']:.5f} sd={d['sd_per_mission']:.5f} "
              f"reps/design={d['reps_per_design']:8.1f} "
              f"key={'agrees' if agrees[k] else 'DISAGREES'} ladder={ladders[k]}", flush=True)

    n_arg = sum(1 for k in kept
                if json.loads(oracle._path(get(k)).read_text())
                .get("_meta", {}).get("_resolved", True) or get(k).optimum)
    print(f"### {n_arg} of {len(kept)} problems can be graded on argmax recovery; "
          f"all {len(kept)} are graded on regret", flush=True)
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
        # len(a.methods), not a literal. This read 6 while METHODS held eight, which
        # under-counted the allowance by a third and is the same defect this project's
        # first paper catalogues: a constant derived when the list had six, carried into
        # a run where it no longer does.
        n_meth = max(len(a.methods), 1)
        per_config = n_meth * sum(ladders[k]) if ladders[k] else 1
        # The allowance rations SIMULATOR time. On the pool backend a mission is an index into an
        # array of missions already run, so there is nothing to ration and the replicate count is
        # set by the precision the comparison needs instead of by what is left in the budget.
        reps[k] = (a.replicates if a.backend == "pool" else
                   int(min(a.replicates, max(a.min_replicates,
                                             a.allowance // max(per_config, 1)))))
        print(f"    {k:22s} ladder-total={sum(ladders[k]):8d} replicates={reps[k]:3d} "
              f"missions~{per_config * reps[k]:9d}", flush=True)
    total = sum(len(a.methods) * sum(ladders[k]) * reps[k] for k in keys)
    print(f"    TOTAL ~{total:,} missions across {len(keys)} problems", flush=True)

    specs = [(k, m, b, r) for k in keys for b in ladders[k]
             for m in a.methods for r in range(reps[k])]
    # The most expensive jobs first, so the pool does not finish with one worker on a 1024-budget
    # run while fifteen sit idle.
    specs.sort(key=lambda s: -s[2])

    # RESUME. The cluster partition this runs on is preemptible by design, and the first attempt at
    # this sweep was preempted five times in three hours. Opening the results file for writing threw
    # away every completed run on each restart, so the job could not finish no matter how long it
    # was given: it was not slow, it was Sisyphean. Completed runs are now read back and skipped,
    # and results are appended. Each spec is deterministic in (problem, method, budget, replicate),
    # so a row already on disk is exactly the row that would be recomputed.
    done = set()
    if out.exists():
        for ln in out.read_text().splitlines():
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue          # a line truncated mid-write by the preemption that killed it
            done.add((r["problem"], r["method"], r["budget"], r["replicate"]))
    todo = [s for s in specs if s not in done]
    if done:
        print(f"resuming: {len(done)} runs already on disk, {len(todo)} to go", flush=True)
    specs = todo
    print(f"{len(specs)} runs on {a.workers} workers", flush=True)

    t0 = time.time()
    n = 0
    # The backend rides in through the pool initializer, not through a module global set in
    # the parent: workers are spawned, so they re-import this module fresh and would each
    # come up with the default. It stays out of the spec tuple so the resume key is
    # unchanged and a half-finished sweep can still be picked up.
    with out.open("a") as fh, ProcessPoolExecutor(
            max_workers=a.workers, initializer=_init_worker,
            initargs=(a.backend,)) as ex:
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
            fh.flush()          # so a preemption loses at most the row in flight
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
    pl = sub.add_parser("pools", help="store per-mission draws for one shard of the cells")
    pl.add_argument("--problems", nargs="*")
    pl.add_argument("--shard", type=int, default=0)
    pl.add_argument("--of", type=int, default=1)
    pl.add_argument("--workers", type=int, default=16)
    pl.set_defaults(fn=cmd_pools)
    t = sub.add_parser("truth"); t.add_argument("--problems", nargs="*")
    t.add_argument("--refresh", action="store_true")
    t.add_argument("--workers", type=int, default=8); t.set_defaults(fn=cmd_truth)
    r = sub.add_parser("run"); r.add_argument("--problems", nargs="*")
    r.add_argument("--out", default="experiments/results/search_bench.jsonl")
    r.add_argument("--budgets", nargs="*", type=int, default=[],
                   help="override the per-problem ladder derived from difficulty")
    r.add_argument("--methods", nargs="*", default=list(METHODS))
    r.add_argument("--replicates", type=int, default=300,
                   help="upper bound on replicates per problem")
    r.add_argument("--min-replicates", type=int, default=8)
    r.add_argument("--allowance", type=int, default=300_000,
                   help="approximate mission budget per problem")
    r.add_argument("--workers", type=int, default=16)
    r.add_argument("--backend", choices=("sim", "pool"), default="pool",
                   help="pool resamples the stored per-mission draws; sim runs fresh "
                        "missions. pool makes pairing across methods exact and costs "
                        "nothing once truth has run.")
    r.set_defaults(fn=cmd_run)
    p = sub.add_parser("report"); p.add_argument("results"); p.set_defaults(fn=cmd_report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
