#!/usr/bin/env python3
"""Separate console ASSIGNMENT effects from HOST SURVIVABILITY (Issue #19 verification pass).

The first console experiment (tools/make_console_arms.py, kept unchanged with its limitation) compared dedicated consoles that die
with their control vehicles against a single operator that cannot be destroyed, so its goodput gap measured survivability, not
assignment. Here every arm has EQUAL HOST AVAILABILITY: the control vehicles cannot be destroyed in any arm.

DIAGNOSTIC ABSTRACTION, NOT A CAPABILITY. The tool wraps `engagement.step` and resets the control vehicles' hit points before
each tick. That makes the hosts indestructible; it is not an implemented remote-operator or off-the-loop capability, and no
such capability should be read into it. Red still shoots and kills other vehicles.

Arms (3 march units, scenarios/uc3_convoy.json, combat on, autonomous units, direct control, comms C0, 30 seeds matched):
  legacy_single       published model: one operator, attention = min(1, 4 / all 15 Blue vehicles) = 0.267
  legacy_single_att1  the same with span_capacity 15, so attention = 1 (isolates the attention equation)
  shared_crew         n_operators = 3 (a pool), attention as in legacy_single
  shared_crew_att1    n_operators = 3, span_capacity 15, attention = 1
  per_unit            one dedicated console per march unit, attention 1.0 (4 agents per console, capacity 4)

Primary comparisons (equal attention = 1 and equal host availability): per_unit vs legacy_single_att1, per_unit vs shared_crew_att1.
Secondary: the attention-equation effect (legacy_single_att1 vs legacy_single; shared_crew_att1 vs shared_crew) and the console-count
effect (shared_crew_att1 vs legacy_single_att1). Even the primary comparison still changes WHO files requests (the crewed control
vehicles stop asking under per_unit) as well as the topology; that confound is stated, not removed.
Metrics: operator_goodput, delivered_frac, blue_losses, success, crew_steps_at_risk, c2u_serviced_frac (per_unit only).
Paired differences, 95% t intervals, Holm within (group, metric). No ranking, no calibration.

REGISTRATION: `python tools/make_assignment_diagnostic.py freeze` before running. Output: report/viz/assignment_diagnostic.json  (generated; do not commit)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_manifest as lm  # noqa: E402

from sandtable import engagement  # noqa: E402
from sandtable.c2_units import resolve_unit_consoles  # noqa: E402
from sandtable.convoy import ROLE_CONTROL  # noqa: E402
from sandtable.entities import BLUE  # noqa: E402
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402

NAME = "assignment"
SCENARIO = "scenarios/uc3_convoy.json"
SEEDS = list(range(30))
OUT = "report/viz/assignment_diagnostic.json"
MANIFEST = f"doc/manifests/{NAME}.manifest.json"
ANALYSIS_FILES = ["tools/make_assignment_diagnostic.py", "tools/local_manifest.py"]
BASE = {"control_mode": "direct", "autonomy_arm": "autonomous_march_unit", "leader_loss_policy": "continue",
        "comms_level": 0, "cargo_per_vehicle": 5.0,
        "convoy": {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1, "pace": 10.0, "time_gap": 4.0}}
ARMS = {
    "legacy_single": {},
    "legacy_single_att1": {"span_capacity": 15.0},
    "shared_crew": {"n_operators": 3},
    "shared_crew_att1": {"n_operators": 3, "span_capacity": 15.0},
    "per_unit": {"console_per_march_unit": {"attention_basis": "assigned", "exceptions": False}},
}
METRICS = ("operator_goodput", "delivered_frac", "blue_losses", "success", "crew_steps_at_risk", "c2u_serviced_frac")
GROUPS = {
    "primary": [("per_unit", "legacy_single_att1"), ("per_unit", "shared_crew_att1")],
    "attention_equation": [("legacy_single_att1", "legacy_single"), ("shared_crew_att1", "shared_crew")],
    "console_count": [("shared_crew_att1", "legacy_single_att1")],
}


def registration() -> dict:
    arms = {lab: {"params": {**BASE, **extra}, "resolved": {"console_per_march_unit": resolve_unit_consoles({**BASE, **extra})}}
            for lab, extra in ARMS.items()}
    comps = [{"group": g, "metric": m, "arm": a, "reference": r, "pairing": "seed"}
             for g, pairs in GROUPS.items() for a, r in pairs for m in METRICS]
    analysis = {"estimate": "mean of paired differences", "interval": "95% t interval",
                "p_values": "two-sided paired t, Holm-adjusted within (group, metric)",
                "host_availability": "control vehicles indestructible in EVERY arm: diagnostic abstraction implemented by "
                                     "resetting their hit points before each engagement step; not a remote-operator capability",
                "confounds": "per_unit also changes who files requests (control vehicles stop asking); stated, not removed",
                "missing_metrics": "c2u_* keys exist only for per_unit; comparisons on them between arms lacking them are unavailable",
                "calibration": "none", "ranking": "none"}
    return {"schema": 1, "name": NAME, "scenarios": {"convoy": lm.scenario_input(SCENARIO)}, "arms": arms, "fixed": BASE,
            "seeds": list(SEEDS), "comparisons": comps, "analysis": analysis}


def _run_one(scn, params: dict, seed: int) -> dict:
    orig = engagement.step

    def shield(ent, *a, **kw):
        ent.hp[(ent.side == BLUE) & (ent.convoy_role == ROLE_CONTROL) & ent.alive] = 1.0e9
        return orig(ent, *a, **kw)

    engagement.step = shield
    try:
        return dict(run_mission(scn, seed=seed, params=params))
    finally:
        engagement.step = orig


def _col(runs, k):
    return np.array([float(r[k]) if k in r and r[k] is not None else np.nan for r in runs])


def _paired(d: np.ndarray) -> dict:
    d = d[np.isfinite(d)]
    if d.size < 3:
        return {"available": False}
    n, se, m = d.size, float(d.std(ddof=1) / np.sqrt(d.size)), float(d.mean())
    t = float(stats.t.ppf(0.975, n - 1))
    return {"available": True, "n_pairs": int(n), "mean": m, "se": se, "ci95": [m - t * se, m + t * se],
            "p": 1.0 if se == 0 else float(2 * stats.t.sf(abs(m / se), n - 1))}


def _holm(items: list) -> None:
    items = [i for i in items if i["available"]]
    order = sorted(range(len(items)), key=lambda i: items[i]["p"])
    m, run = len(items), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * items[i]["p"]))
        items[i]["p_holm"] = run


def run(accept_source_drift: bool = False) -> dict:
    reg = registration()
    man, now, check = lm.check_before_run(MANIFEST, reg, ANALYSIS_FILES, accept_source_drift)
    scn = load_scenario(SCENARIO)
    runs = {lab: [_run_one(scn, a["params"], s) for s in SEEDS] for lab, a in reg["arms"].items()}
    rows, groups = [], {}
    for c in reg["comparisons"]:
        row = {**c, **_paired(_col(runs[c["arm"]], c["metric"]) - _col(runs[c["reference"]], c["metric"]))}
        rows.append(row)
        groups.setdefault((c["group"], c["metric"]), []).append(row)
    for items in groups.values():
        _holm(items)
    means = {lab: {m: (None if not np.isfinite(_col(r, m)).any() else float(np.nanmean(_col(r, m)))) for m in METRICS}
             for lab, r in runs.items()}
    checks = {"per_unit_consoles_lost_max": float(np.nanmax(_col(runs["per_unit"], "c2u_consoles_lost"))),
              "per_unit_abandon_console_max": float(np.nanmax(_col(runs["per_unit"], "c2u_abandon_console")))}
    return {"registration_hash": man["registration_hash"], "manifest_status": man["status"],
            "source_hashes_at_freeze": man["provenance"]["source_hashes"], "source_hashes_at_run": now, "source_check": check,
            "host_availability_check": checks, "arm_means": means, "comparisons": rows}


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "freeze":
        return lm.freeze(MANIFEST, registration(), ANALYSIS_FILES, "frozen_before_run", "Frozen before the first run of this tool.")
    out = run("--accept-source-drift" in sys.argv)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(out, indent=2))
    print(f'manifest {out["manifest_status"]} {out["registration_hash"][:12]}; source check {out["source_check"]}; hosts {out["host_availability_check"]}')
    for lab, m in out["arm_means"].items():
        print(f"  {lab:20s}", {k: (None if v is None else round(v, 3)) for k, v in m.items()})
    for c in out["comparisons"]:
        if c["available"] and c["metric"] in ("operator_goodput", "delivered_frac", "blue_losses"):
            print(f'  {c["group"]:18s} {c["arm"]:18s} vs {c["reference"]:18s} {c["metric"]:16s} {c["mean"]:+.3f} '
                  f'[{c["ci95"][0]:+.3f},{c["ci95"][1]:+.3f}] holm {c["p_holm"]:.3f}')


if __name__ == "__main__":
    main()
