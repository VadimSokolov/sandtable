#!/usr/bin/env python3
"""Emit paper two's CR-79 follow-up macros from the repaired-methods sweep.

Written before that sweep produced a row. These macros carry a `Wm` prefix and live in their own
file, because they come from a DIFFERENT sweep than the rest of the paper: `bench-warm.jsonl` runs
fourteen methods and `bench-r300.jsonl` runs ten, so their balanced-cell intersections differ and a
number from one must never be read as a number from the other. The main comparison keeps its own
provenance and this follow-up keeps its own.

    python3 tools/make_warm_numbers.py $ROOT/search/bench-warm.jsonl
"""
from __future__ import annotations

import collections
import pathlib
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from score_bench import load, paired, gate, spread_of           # noqa: E402
from sandtable.search.problems import PROBLEMS                  # noqa: E402

OUT = "paper-search/gen/warm_numbers.tex"
SUFFIX = "_warm"
BASE = "grid"
WORD = {"ucb_pooled_warm": "UcbPooledWarm", "ucb_raw_warm": "UcbRawWarm",
        "thompson_warm": "ThompsonWarm", "gp_ei_warm": "GpEiWarm"}


def main() -> None:
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
    print(f"  cells reached by all {nm} methods: {len(full):,}; kept {len(rows):,} rows")

    meths = sorted({r["method"] for r in rows})
    warm = [m for m in meths if m.endswith(SUFFIX)]
    if not warm:
        raise SystemExit(f"no methods ending in {SUFFIX}")
    grade = sorted({r["problem"] for r in rows if r.get("gradeable")})
    gset = set(grade)
    sub = [r for r in rows if r["problem"] in gset]
    by = collections.defaultdict(set)
    for r in rows:
        by[r["problem"]].add(r["budget"])
    lo = {k: (min(v),) for k, v in by.items()}
    hi = {k: (max(v),) for k, v in by.items()}
    sr = spread_of(rows, "regret_frac")
    sf = spread_of(sub, "found")

    def mean(m, field, sel, src):
        v = [(1.0 if r[field] else 0.0) if field == "found" else r[field] for r in src
             if r["method"] == m and r["budget"] in sel.get(r["problem"], ())]
        return st.mean(v) if v else float("nan")

    def touch(m, sel):
        v = [r["distinct"] for r in sub
             if r["method"] == m and r["budget"] in sel.get(r["problem"], ())]
        return st.mean(v) if v else float("nan")

    sizes = [PROBLEMS[k].n_designs for k in grade if k in PROBLEMS]
    out = [("WmRows", f"{len(rows):,}".replace(",", "{,}")),
           ("WmMethods", str(len(meths))),
           ("WmWarm", str(len(warm))),
           ("WmReplicates", str(len({r["replicate"] for r in rows}))),
           ("WmDesigns", f"{st.mean(sizes):.1f}" if sizes else "0")]

    base_lo = mean(BASE, "found", lo, sub)
    out += [("WmBaseLowFound", f"{100 * base_lo:.0f}"),
            ("WmBaseLowTouch", f"{touch(BASE, lo):.1f}")]

    worst_def, best_def = -9e9, 9e9
    for m in warm:
        twin = m[: -len(SUFFIX)]
        tag = WORD.get(m, m.title().replace("_", ""))
        d_new = base_lo - mean(m, "found", lo, sub)
        d_old = base_lo - mean(twin, "found", lo, sub)
        worst_def, best_def = max(worst_def, d_new), min(best_def, d_new)
        out += [(f"Wm{tag}LowDeficit", f"{d_new:+.4f}"),
                (f"Wm{tag}LowDeficitWas", f"{d_old:+.4f}"),
                (f"Wm{tag}LowTouch", f"{touch(m, lo):.1f}"),
                (f"Wm{tag}LowTouchWas", f"{touch(twin, lo):.1f}")]
        # Cost at the top rung against the method's own unrepaired twin.
        g = gate(paired(rows, m, twin, "regret_frac", budgets=hi), sr)
        out += [(f"Wm{tag}TopEff", f"{g['eff']:+.4f}"), (f"Wm{tag}TopT", f"{g['t']:+.2f}"),
                (f"Wm{tag}TopVerdict", g["verdict"])]
        # Parity with uniform allocation at the bottom rung, on argmax recovery.
        gp = gate(paired(sub, BASE, m, "found", budgets=lo), sf)
        out += [(f"Wm{tag}LowVsUni", gp["verdict"]),
                (f"Wm{tag}LowVsUniEff", f"{gp['eff']:+.4f}"),
                (f"Wm{tag}LowVsUniT", f"{gp['t']:+.2f}")]

    out += [("WmWorstDeficit", f"{worst_def:+.4f}"), ("WmBestDeficit", f"{best_def:+.4f}")]

    # The claim deliberately NOT predicted: that a repaired method beats uniform allocation.
    beat = []
    for m in warm:
        for tag, sel in (("low", lo), ("top", hi)):
            if gate(paired(rows, m, BASE, "regret_frac", budgets=sel), sr)["verdict"] == "gate down":
                beat.append(f"{m} at the {tag} rung")
    out += [("WmBeatUni", str(len(beat))),
            ("WmBeatUniNames", ", ".join(x.replace("_", r"\_") for x in beat) or "none")]

    body = "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in out) + "\n"
    p = pathlib.Path(__file__).resolve().parents[1] / OUT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("% generated by tools/make_warm_numbers.py; do not edit\n" + body)
    print(f"wrote {p} with {len(out)} macros")


if __name__ == "__main__":
    main()
