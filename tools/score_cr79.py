#!/usr/bin/env python3
"""Score CR-79 against its three registered falsifiers.

Written before any repaired method exists, so the thresholds below cannot have been chosen to fit
what the sweep turned out to say. They are copied from the registration in
doc/autoresearch-conjectures.md and nothing here recomputes them.

  A: the bottom-rung argmax deficit against uniform allocation shrinks by at least half.
     FAILS if the repaired deficit exceeds DEFICIT_MAX.
  B: the repair costs nothing at the top rung.
     FAILS if a repaired method gates UP against its own unrepaired twin on top-rung regret.
  C: at the bottom rung the repaired methods become EQUIVALENT to grid on argmax recovery.
     FAILS if grid still gates up against every repaired method.

    python3 tools/score_cr79.py $ROOT/search/bench-warm.jsonl
"""
from __future__ import annotations

import collections
import pathlib
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from score_bench import load, paired, gate, spread_of           # noqa: E402

DEFICIT_MAX = 0.20          # registered
BASE = "grid"
SUFFIX = "_warm"            # repaired variants ship as <name>_warm


def rungs(rows):
    by = collections.defaultdict(set)
    for r in rows:
        by[r["problem"]].add(r["budget"])
    return ({k: (min(v),) for k, v in by.items()},
            {k: (max(v),) for k, v in by.items()})


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    rows = load(sys.argv[1])
    if not rows:
        raise SystemExit("no rows")
    seen = {}
    for r in rows:
        seen.setdefault((r["problem"], r["budget"], r["replicate"]), set()).add(r["method"])
    nm = len({r["method"] for r in rows})
    full = {c for c, ms in seen.items() if len(ms) == nm}
    rows = [r for r in rows if (r["problem"], r["budget"], r["replicate"]) in full]
    grade = {r["problem"] for r in rows if r.get("gradeable")}
    lo, hi = rungs(rows)
    meths = sorted({r["method"] for r in rows})
    warm = [m for m in meths if m.endswith(SUFFIX)]
    if not warm:
        raise SystemExit(f"no methods ending in {SUFFIX}; nothing to score")

    sub = [r for r in rows if r["problem"] in grade]
    sf, sr = spread_of(sub, "found"), spread_of(rows, "regret_frac")

    def found(m, sel):
        v = [1.0 if r["found"] else 0.0 for r in sub
             if r["method"] == m and r["budget"] in sel.get(r["problem"], ())]
        return st.mean(v) if v else float("nan")

    def touched(m, sel):
        v = [r["distinct"] for r in sub
             if r["method"] == m and r["budget"] in sel.get(r["problem"], ())]
        return st.mean(v) if v else float("nan")

    base_lo = found(BASE, lo)
    print(f"CR-79 scored against three registered falsifiers, {len(rows):,} balanced rows")
    print(f"  bottom-rung argmax recovery for {BASE}: {base_lo:.4f}, "
          f"designs touched {touched(BASE, lo):.2f}\n")

    print("A. deficit against uniform allocation at the bottom rung "
          f"(fails above {DEFICIT_MAX})")
    worst = 0.0
    for m in warm:
        twin = m[: -len(SUFFIX)]
        d_new = base_lo - found(m, lo)
        d_old = base_lo - found(twin, lo) if twin in meths else float("nan")
        worst = max(worst, d_new)
        print(f"  {m:16s} deficit {d_new:+.4f}  was {d_old:+.4f}  "
              f"touched {touched(m, lo):.2f} was {touched(twin, lo):.2f}")
    a_ok = worst <= DEFICIT_MAX
    print(f"  A {'HOLDS' if a_ok else 'FAILS'}: worst repaired deficit {worst:+.4f}\n")

    print("B. top-rung cost of the repair against each method's own twin (fails on a gate up)")
    b_ok = True
    for m in warm:
        twin = m[: -len(SUFFIX)]
        if twin not in meths:
            continue
        g = gate(paired(rows, m, twin, "regret_frac", budgets=hi), sr)
        b_ok &= g["verdict"] != "gate up"
        print(f"  {m:16s} vs {twin:12s} {g['eff']:+.4f} t={g['t']:+7.2f} "
              f"sign={100 * g['sign']:.0f}% {g['verdict']}")
    print(f"  B {'HOLDS' if b_ok else 'FAILS'}\n")

    print("C. bottom-rung argmax parity with uniform allocation "
          "(fails if grid gates up against every repaired method)")
    c_any = False
    for m in warm:
        g = gate(paired(sub, BASE, m, "found", budgets=lo), sf)
        c_any |= g["verdict"] != "gate up"
        print(f"  {BASE} vs {m:16s} {g['eff']:+.4f} t={g['t']:+7.2f} "
              f"sign={100 * g['sign']:.0f}% {g['verdict']}")
    print(f"  C {'HOLDS' if c_any else 'FAILS'}\n")

    print("NOT predicted: that any repaired method beats uniform allocation. Reported anyway.")
    for m in warm:
        for tag, sel in (("low", lo), ("top", hi)):
            g = gate(paired(rows, m, BASE, "regret_frac", budgets=sel), sr)
            if g["verdict"] == "gate down":
                print(f"  !! {m} beats {BASE} at the {tag} rung: {g['eff']:+.4f} t={g['t']:+.2f}")
    return 0 if (a_ok and b_ok and c_any) else 1


if __name__ == "__main__":
    raise SystemExit(main())
