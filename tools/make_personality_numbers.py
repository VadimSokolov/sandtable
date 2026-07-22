"""Personality-movement demonstration (UC-3): emergent maneuver vs the scripted route planner.

Writes report/data/personality_sweep.csv, mean KPIs over N seeded replications for two movement
models on UC-3: the scripted lateral lane (route_bias, the baseline planner) at its fast and covered
extremes, and the opt-in personality-movement mode (ISAAC/EINSTein/MANA weighted propensities) as the
enemy-repulsion weight w_enemy is swept from off. With no enemy propensity the force drives straight
through the defense and reproduces the fast corridor; turning it on makes the agents bow around the
detected threat, a route choice that emerges from local rules and, at w_enemy = 1, matches or beats
the hand-scripted covered route on losses, success, and time. Consumed by tools/make_numbers.py (the
`personality` block).

    PYTHONPATH=src python tools/make_personality_numbers.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

UC3 = "scenarios/uc3_route_defilade.json"
NREP = 48
DATA = Path("report/data")


def _means(params: dict) -> dict:
    runs = [run_mission(load_scenario(UC3), seed=s, params=params) for s in range(NREP)]
    # Time-to-objective is reported conditioned on success (matching the UC-3 frontier convention),
    # so it is the actual transit time of the runs that arrived, not a value censored at the mission
    # duration by the runs that failed. blue_losses/success are means over all replications.
    won = [r["time_to_objective"] for r in runs if r["success"] >= 0.5]
    return {"blue_losses": float(np.mean([r["blue_losses"] for r in runs])),
            "success": float(np.mean([r["success"] for r in runs])),
            "time": float(np.mean(won)) if won else float("nan")}


def _pers(w_enemy: float) -> dict:
    return {"movement": "personality", "personality": {"w_goal": 1.0, "w_enemy": w_enemy}}


CONDITIONS = [
    ("scripted", 0.0, {"route_bias": 0.0}),     # scripted fast corridor
    ("scripted", 1.0, {"route_bias": 1.0}),     # scripted covered route (best scripted)
    ("personality", 0.0, _pers(0.0)),           # pure goal-seek (recovers the fast corridor)
    ("personality", 0.5, _pers(0.5)),
    ("personality", 1.0, _pers(1.0)),
    ("personality", 2.0, _pers(2.0)),
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode, knob, params in CONDITIONS:
        m = _means(params)
        rows.append({"mode": mode, "knob": knob,
                     "blue_losses": round(m["blue_losses"], 4),
                     "success": round(m["success"], 4),
                     "time": round(m["time"], 1), "n_rep": NREP})
        print(f"  {mode:12s} knob={knob:.1f}  blue={m['blue_losses']:.2f}  "
              f"succ={m['success']:.2f}  t={m['time']:.0f}")
    out = DATA / "personality_sweep.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mode", "knob", "blue_losses", "success", "time", "n_rep"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} (N={NREP})")


if __name__ == "__main__":
    main()
