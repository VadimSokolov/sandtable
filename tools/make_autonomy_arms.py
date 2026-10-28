#!/usr/bin/env python3
"""Run the Issue #14 manned vs autonomous march unit arms across the C0-C5 comms ladder.

Arms (the label is written into every row):
  manned                  every truck has a driver and assistant driver; holds station with human perception
  autonomous_link         one manned control vehicle, four unmanned trucks, leader pose over the link
  autonomous_behavior     the same, followers dead-reckon on their own sensors

Both arms use the same roles (control + four cargo, no escorts) so cargo count is equal. The manned
arm holds station on the vehicle ahead with human perception (`follow_mode="human"`), isolating crew
reduction and channel dependence without confounding formation discipline.

Output: report/viz/autonomy_arms.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SEEDS = 10
UNIT = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1, "pace": 10.0,
        "time_gap": 4.0, "cargo_per_vehicle": 5.0, "roles": ["control", "cargo", "cargo", "cargo", "cargo"]}
KEYS = ("success", "delivered_frac", "time_to_delivery", "cargo_lost", "blue_losses", "crew_steps_at_risk",
        "crew_steps_at_risk_control", "crew_steps_at_risk_cargo", "crew_lost", "autonomous_headless_steps")
ARMS = {
    "manned": {"autonomy_arm": "manned"},
    "autonomous_link": {"autonomy_arm": "autonomous_march_unit", "follow_mode": "link"},
    "autonomous_behavior": {"autonomy_arm": "autonomous_march_unit", "follow_mode": "behavior"},
}


def run(scenario_path: str = "scenarios/uc3_convoy.json") -> dict:
    scn = load_scenario(scenario_path)
    rows = []
    for label, arm in ARMS.items():
        for level in range(6):
            params = {"convoy": dict(UNIT), "comms_level": level, **arm}
            runs = [run_mission(scn, seed=s, params=params) for s in range(SEEDS)]
            row = {"arm": label, "comms_level": level, "n_seeds": SEEDS}
            for k in KEYS:
                vals = [r[k] for r in runs if k in r and r[k] == r[k]]
                row[k] = float(np.mean(vals)) if vals else None
            rows.append(row)
    return {"scenario": scenario_path, "caveat": "crew is model-defined; manned arm uses human perception; "
            "headless policy is a placeholder (Issue #17)", "rows": rows}


def main() -> None:
    out = run()
    path = Path("report/viz/autonomy_arms.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    for r in out["rows"]:
        print(r["arm"], r["comms_level"], {k: (round(r[k], 2) if r[k] is not None else None)
                                           for k in ("success", "delivered_frac", "crew_steps_at_risk")})


if __name__ == "__main__":
    main()
