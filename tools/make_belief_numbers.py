"""Belief/track-layer demonstration numbers (UC-3): baseline vs the opt-in belief model.

Writes report/data/belief_demo.csv, mean blue and red losses over N seeded replications for four
conditions: the baseline (single seen-bit, fires against truth), the belief/track model in clear
communications, the belief model with decoys (spoofing), and the belief model under severe jamming
(stale tracks). The point is that with a first-class belief state, deception and electronic warfare
act on outcomes as first-order effects, not probability-of-kill modifiers. Consumed by
tools/make_numbers.py (the `belief` block), which turns the CSV into LaTeX macros.

    PYTHONPATH=src python tools/make_belief_numbers.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

UC3 = "scenarios/uc3_route_defilade.json"
NREP = 24


def _belief(**kw):
    cfg = {"model": "tracks"}
    cfg.update(kw)
    return {"belief": cfg}


CONDITIONS = [
    ("baseline", None),                                    # single seen-bit, fires vs truth
    ("clear", _belief()),                                  # belief tracks, clear comms
    ("decoy", _belief(decoys=6, decoy_rate=0.95)),         # belief tracks + spoofed/decoy tracks
    ("jam", {**_belief(), "comms_level": 5}),              # belief tracks, severe jamming (stale)
]


def main() -> None:
    out = Path("report/data/belief_demo.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, params in CONDITIONS:
        runs = [run_mission(load_scenario(UC3), seed=s, params=params) for s in range(NREP)]
        rows.append({
            "condition": name,
            "blue_losses": round(float(np.mean([r["blue_losses"] for r in runs])), 4),
            "red_losses": round(float(np.mean([r["red_losses"] for r in runs])), 4),
            "n_rep": NREP,
        })
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["condition", "blue_losses", "red_losses", "n_rep"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} (N={NREP})")
    for r in rows:
        print(f"  {r['condition']:9s} blue={r['blue_losses']:.2f}  red={r['red_losses']:.2f}")


if __name__ == "__main__":
    main()
