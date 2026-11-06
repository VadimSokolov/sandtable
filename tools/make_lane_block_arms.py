#!/usr/bin/env python3
"""Lane blocking by wrecks (Issue #18, Change item 2): how long the column waits, by targeting rule.

Scenario: scenarios/uc3_convoy_ambush.json (Red abeam, ambush discipline). Arms: three Red targeting rules
(legacy, ends_seen, control_first) crossed with lane blocking off or on at three recovery times. Seeds 0..29.
Everything else is fixed. The recovery times (60, 300 and 900 s) and the 20 m stand-off are PLACEHOLDERS with
no public source; the lane model is the minimal one in `src/sandtable/lane_block.py` (no bypass, no
rerouting).

The experiment is defined by `registration()`. Its manifest must be frozen with
`python tools/manifest_cli.py freeze lane_block --status frozen_before_run` BEFORE this tool runs; `run`
refuses to start if the frozen hash does not match the definitions below, and writes the hash into the
output. Changing anything in `registration()` after freezing changes the hash.

Comparisons (all paired by seed, Holm-adjusted within a family):
  block_effect     for each targeting rule: (blocking at recovery time r) minus (blocking off), per metric
  targeting_effect for each recovery time (including off): (targeting rule) minus legacy, per metric
Metrics: success, delivered_frac, blue_losses, lane_blocked_vehicle_steps.

Not a ranking. Priority only reorders eligible targets, the wreck is the only new constraint, every Red value
is a placeholder, and one road/layout/terrain is used.

Output: report/viz/lane_block_arms.json (generated; do not commit)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sandtable import manifest  # noqa: E402
from sandtable.ambush import resolve_ambush  # noqa: E402
from sandtable.lane_block import resolve_lane_blocking  # noqa: E402
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402
from sandtable.target_priority import resolve_target_priority  # noqa: E402

NAME = "lane_block"
SCENARIO = "scenarios/uc3_convoy_ambush.json"
SEEDS = list(range(30))
FIXED = {"leader_loss_policy": "continue", "crew_metrics": True, "cargo_per_vehicle": 5.0}
TARGETING = {"legacy": {"order": []}, "ends_seen": {"order": ["ends"]}, "control_first": {"order": ["control"]}}
RECOVERY = {"off": None, "r60": 60.0, "r300": 300.0, "r900": 900.0}
STANDOFF_M = 20.0
METRICS = ("success", "delivered_frac", "blue_losses", "lane_blocked_vehicle_steps")
OUT = "report/viz/lane_block_arms.json"
MANIFEST = f"doc/manifests/{NAME}.manifest.json"


def arm_params(t_label: str, r_label: str) -> dict:
    p = {**FIXED, "target_priority": TARGETING[t_label]}
    if RECOVERY[r_label] is not None:
        p["lane_blocking"] = {"recovery_time_s": RECOVERY[r_label], "standoff_m": STANDOFF_M}
    return p


def arm_label(t: str, r: str) -> str:
    return f"{t}|{r}"


def registration() -> dict:
    arms = {}
    for t in TARGETING:
        for r in RECOVERY:
            p = arm_params(t, r)
            arms[arm_label(t, r)] = {"params": p, "resolved": {
                "target_priority": resolve_target_priority(p), "lane_blocking": resolve_lane_blocking(p),
                "ambush": resolve_ambush(load_scenario(SCENARIO).params)}}
    comparisons = (
        [{"family": "block_effect", "metric": m, "targeting": t, "arm": arm_label(t, r), "reference": arm_label(t, "off"),
          "pairing": "seed"} for t in TARGETING for r in RECOVERY if r != "off" for m in METRICS]
        + [{"family": "targeting_effect", "metric": m, "recovery": r, "arm": arm_label(t, r),
            "reference": arm_label("legacy", r), "pairing": "seed"}
           for r in RECOVERY for t in TARGETING if t != "legacy" for m in METRICS])
    analysis = {"estimate": "mean of paired differences", "interval": "95% t interval, n-1 degrees of freedom",
                "p_values": "two-sided paired t, Holm-adjusted within (family, metric, targeting-or-recovery group)",
                "equivalence_claims": "none registered", "ranking": "none"}
    return manifest.build_registration(NAME, {"ambush": SCENARIO}, arms, FIXED, SEEDS, comparisons, analysis)


def _col(runs, k):
    # arms with lane blocking off emit no lane_ metrics: zero blocked vehicle-steps by definition
    return np.array([float(r.get(k, 0.0)) if k.startswith('lane_') else float(r[k]) for r in runs])


def _diff(runs_a, runs_b, k):
    d = _col(runs_a, k) - _col(runs_b, k)
    n = d.size
    se = float(d.std(ddof=1) / np.sqrt(n))
    t = float(stats.t.ppf(0.975, n - 1))
    m = float(d.mean())
    p = 1.0 if se == 0 else float(2 * stats.t.sf(abs(m / se), n - 1))
    return {"mean": m, "se": se, "ci95": [m - t * se, m + t * se], "p": p}


def _holm(items: list) -> None:
    order = sorted(range(len(items)), key=lambda i: items[i]["p"])
    m, run = len(items), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * items[i]["p"]))
        items[i]["p_holm"] = run


def run() -> dict:
    reg = registration()
    path = Path(MANIFEST)
    if not path.exists():
        raise SystemExit(f"no manifest at {MANIFEST}: freeze it first (tools/manifest_cli.py freeze {NAME})")
    man = json.loads(path.read_text())
    ok, why = manifest.verify_manifest(man, reg)
    if not ok:
        raise SystemExit(f"manifest does not match the definitions, not running: {why}")
    scn = load_scenario(SCENARIO)
    runs = {lab: [run_mission(scn, seed=s, params=a["params"]) for s in SEEDS] for lab, a in reg["arms"].items()}
    results = []
    groups: dict = {}
    for c in reg["comparisons"]:
        d = _diff(runs[c["arm"]], runs[c["reference"]], c["metric"])
        row = {**c, **d}
        results.append(row)
        key = (c["family"], c["metric"], c.get("targeting") or c.get("recovery"))
        groups.setdefault(key, []).append(row)
    for items in groups.values():
        _holm(items)
    summary = {lab: {k: float(_col(r, k).mean()) for k in METRICS} for lab, r in runs.items()}
    return {"manifest_status": man["status"], "registration_hash": man["registration_hash"],
            "manifest_commit": man["provenance"]["source_revision"]["commit"],
            "run_commit": manifest.source_revision()["commit"], "arm_means": summary, "comparisons": results}


def main() -> None:
    out = run()
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(out, indent=2))
    print(f'manifest {out["manifest_status"]} {out["registration_hash"][:12]}')
    for lab, m in out["arm_means"].items():
        print(f"  {lab:22s}", {k: round(v, 2) for k, v in m.items()})
    sig = [c for c in out["comparisons"] if c["p_holm"] < 0.05]
    print(f"{len(sig)} of {len(out['comparisons'])} comparisons with Holm p < 0.05")
    for c in sig:
        print("  ", c["family"], c["arm"], "vs", c["reference"], c["metric"], f'{c["mean"]:+.3f}', f'holm {c["p_holm"]:.3f}')


if __name__ == "__main__":
    main()
