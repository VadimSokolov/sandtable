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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                              # noqa: E402

from sandtable.search import PROBLEMS, get                      # noqa: E402
from sandtable.search import oracle, runner                     # noqa: E402

BUDGETS = (64, 128, 256, 512, 1024)
METHODS = ("grid", "random", "halving", "ucb", "thompson", "gp_ei")


def cmd_truth(a) -> None:
    keys = a.problems or list(PROBLEMS)
    for k in keys:
        p = get(k)
        t0 = time.time()
        t = oracle.truth(p, refresh=a.refresh, verbose=True)
        d, v = oracle.best_design(p, t)
        ok = oracle.agrees_with_key(p, t)
        print(f"{k:16s} best={json.dumps(d, sort_keys=True):40s} {v:.6f}  "
              f"key={'AGREES' if ok else 'DISAGREES with ' + json.dumps(p.optimum)}  "
              f"({time.time() - t0:.0f}s)")


def cmd_run(a) -> None:
    keys = a.problems or list(PROBLEMS)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w") as fh:
        for k in keys:
            p = get(k)
            t = oracle.truth(p)
            agrees = oracle.agrees_with_key(p, t)
            print(f"### {k}  designs={p.n_designs}  key={'agrees' if agrees else 'DISAGREES'}",
                  flush=True)
            for b in a.budgets:
                for m in a.methods:
                    t0 = time.time()
                    for r in range(a.replicates):
                        res = runner.run_one(k, m, b, r, t)
                        fh.write(json.dumps({**res.__dict__, "key_agrees": agrees}) + "\n")
                        n += 1
                    fh.flush()
                    print(f"  budget={b:5d} {m:9s} {time.time() - t0:6.1f}s", flush=True)
    print(f"\n{n} rows -> {out}")


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
    t.add_argument("--refresh", action="store_true"); t.set_defaults(fn=cmd_truth)
    r = sub.add_parser("run"); r.add_argument("--problems", nargs="*")
    r.add_argument("--out", default="experiments/results/search_bench.jsonl")
    r.add_argument("--budgets", nargs="*", type=int, default=list(BUDGETS))
    r.add_argument("--methods", nargs="*", default=list(METHODS))
    r.add_argument("--replicates", type=int, default=24); r.set_defaults(fn=cmd_run)
    p = sub.add_parser("report"); p.add_argument("results"); p.set_defaults(fn=cmd_report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
