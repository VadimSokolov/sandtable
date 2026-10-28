#!/usr/bin/env python3
"""Run the Issue #12 contact-reaction arms on the UC-3 convoy and write a labeled comparison.

Arms (the label is written into every row, not only the filename):
  no_escort_no_reaction  zero-escort autonomous counterfactual: security_ratio 0, no reaction
  escort_no_reaction     gun trucks at the baseline roles, no reaction
  escort_continue        reaction declared, action `continue` (the control arm)
  escort_halt            reaction declared, action `halt`

Caveat carried into the output: Red does not exploit a halted column (no indirect fire or secondary
devices), so `escort_halt` is not evidence about halting until that cost is modelled. The ratio
range is inference (Issue #12, Oct 20 comment) and the gun-truck armament a placeholder.

Output: report/viz/contact_arms.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sandtable.scenario import Scenario
from sandtable.sim import run_mission

SEEDS = 20
TRIGGERS = ["receive_fire", "lead_lost", "detect_range"]
KEYS = ("success", "time_to_objective", "blue_losses", "red_losses", "escort_vehicle_steps",
        "convoy_contact_count", "convoy_contact_steps", "convoy_halt_steps")

# Placeholder armament (NOT sourced): a gun truck with five times the cargo truck's pk_base.
GUN_TRUCK = {"domain": 0, "max_speed": 12.0, "turn_rate": 0.6, "sensor_range": 1500.0,
             "weapon_range": 1200.0, "pk_base": 0.01, "hp": 1.0}

ARMS = {
    "no_escort_no_reaction": {"security_ratio": 0.0, "security_ptype": "gun_truck"},
    "escort_no_reaction": {"security_ptype": "gun_truck"},
    "escort_continue": {"security_ptype": "gun_truck",
                        "contact_reaction": {"action": "continue", "triggers": TRIGGERS}},
    "escort_halt": {"security_ptype": "gun_truck",
                    "contact_reaction": {"action": "halt", "triggers": TRIGGERS}},
}


def run(scenario_path: str = "scenarios/uc3_convoy.json") -> dict:
    d = json.loads(Path(scenario_path).read_text())
    d["platform_types"]["gun_truck"] = GUN_TRUCK
    scn = Scenario.from_dict(d)
    rows = []
    for label, params in ARMS.items():
        runs = [run_mission(scn, seed=s, params=params) for s in range(SEEDS)]
        row = {"arm": label, "n_seeds": SEEDS}
        for k in KEYS:
            vals = [r[k] for r in runs if k in r]
            row[k] = float(np.mean(vals)) if vals else None
        rows.append(row)
    return {"scenario": scenario_path, "caveat": "Red does not exploit a halt; ratios and gun-truck armament are placeholders.",
            "arms": rows}


def main() -> None:
    out = run()
    path = Path("report/viz/contact_arms.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    for r in out["arms"]:
        print(r["arm"], {k: r[k] for k in KEYS})


if __name__ == "__main__":
    main()
