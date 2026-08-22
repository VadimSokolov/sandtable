"""Paired contrasts, including differences of differences, over an `ar_eval.py` run log.

`ar_table.py` gates each arm against one reference arm, which covers a two-arm question. Some
questions are not two-arm. CR-17 asks whether an INITIAL CONDITION is load-bearing, and staggering
the vehicles' first decision events also perturbs the RNG stream and has a direct effect of its
own, so the quantity that isolates the mechanism is

    [stag - burst | retry on] - [stag - burst | retry off],

a difference of differences. Every arm in a run shares the block set by construction, so the
interaction is paired block by block and gets the same three-part contract test as any other
contrast: |t| over 1.70, |mean| at or above the MPE, and a consistent sign in at least 60% of
blocks.

Reads a log file, never acts on its contents: it recognizes only the AR_ROW lines `ar_eval.py`
wrote and ignores everything else.

Usage:
  python3 tools/ar_contrast.py RUN.log --section H1 --diff stag_retry burst_retry
  python3 tools/ar_contrast.py RUN.log --section H1 \
      --did stag_retry burst_retry stag_off burst_off
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ar_table import parse  # noqa: E402

MPE = 0.03          # minimum practical effect, from the frozen contract
T_CRIT = 1.70       # one-sided alpha 0.05 at the block counts this harness runs
MIN_WIN = 0.60      # sign consistency


def stats(d: list[float]) -> dict:
    n = len(d)
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n) if var > 0 else 0.0
    t = mean / se if se > 0 else (math.inf if mean else 0.0)
    wins = sum(1 for x in d if x > 0) / n
    gated = abs(t) > T_CRIT and abs(mean) >= MPE and max(wins, 1 - wins) >= MIN_WIN
    return {"n": n, "mean": mean, "t": t, "win": wins, "gated": gated}


def series(sec: dict, arm: str) -> dict[str, list[float]]:
    """Sweep value -> block means, for one arm."""
    return {r["val"]: r["vals"] for r in sec["rows"] if r["arm"] == arm}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--section", default=None, help="substring of the section banner")
    ap.add_argument("--diff", nargs=2, metavar=("A", "B"), help="paired A - B")
    ap.add_argument("--did", nargs=4, metavar=("A", "B", "C", "D"),
                    help="paired (A - B) - (C - D)")
    args = ap.parse_args()

    # A log is only final once the runner says so. `hopper/collect.sh` rsyncs while a job may still
    # be writing, and a partial copy reads as a complete one: a section that has not finished simply
    # has fewer rows, with nothing to distinguish it from a section that was smaller by design. This
    # cost one wrong read already, so the check lives here, where logs are actually consumed.
    text = open(args.log, errors="replace").read()
    if "### ALL BATTERIES COMPLETE" not in text:
        print(f"WARNING: {args.log} has no completion marker; the run is unfinished or the local "
              f"copy is stale. Re-run hopper/collect.sh before trusting these rows.")

    for sec in parse(args.log, args.section):
        print(f"## {sec['title']}")
        if args.diff:
            a, b = args.diff
            sa, sb = series(sec, a), series(sec, b)
            label = f"{a} - {b}"
            cells = [(v, [x - y for x, y in zip(sa[v], sb[v])])
                     for v in sa if v in sb]
        elif args.did:
            a, b, c, d = args.did
            sa, sb, sc, sd = (series(sec, x) for x in (a, b, c, d))
            label = f"({a} - {b}) - ({c} - {d})"
            cells = [(v, [(w - x) - (y - z)
                          for w, x, y, z in zip(sa[v], sb[v], sc[v], sd[v])])
                     for v in sa if v in sb and v in sc and v in sd]
        else:
            ap.error("pass --diff or --did")
        if not cells:
            print("   (no matching arms in this section)")
            continue
        key = sec["rows"][0]["key"] or "cell"
        print(f"   {label}")
        for val, d in cells:
            s = stats(d)
            mark = "GATED" if s["gated"] else "     "
            print(f"   {key}={val:<8} {s['mean']:+.4f}  t={s['t']:7.2f}  "
                  f"sign={s['win'] * 100:3.0f}%  n={s['n']:>3}  {mark}")


if __name__ == "__main__":
    main()
