#!/usr/bin/env python3
"""Exercise the per-console attention term directly (Issue #19 verification pass).

DESIGN. The same vehicles, crew, route, communications level (C2) and request workload in every arm; only
`span_capacity` varies, so attention = min(1, span_capacity / 4 assigned agents) takes the values 1, 1, 0.5, 0.25.
Combat is disabled (scenarios/uc3_convoy_no_threat.json: the Red teams cannot fire) so no console host is lost, and the run
is a fixed 300 s horizon (shorter than the time to the goal) so the request process does not depend on how fast the
convoy moves. Seeds 0..29, matched across arms.

WHAT IS CHECKED. (1) The equation: per run, `c2u_attention_mean` equals min(1, span/4) and `c2u_quality_mean` equals
q_auto + (q_operator - q_auto) x attention, to rounding. (2) Attention, effective quality, queue wait, interaction
time, communications delay and served share are reported separately, with paired differences against span 4.
Because attention enters only the quality of a served decision, wait, service time, delay and served share are
EXPECTED to be unchanged; that is a check of the mechanism, not a result about missions. No monotonic delivery
benefit is required or claimed.

NOT A CALIBRATION. This synthetic experiment says nothing about real human workload or about a real attention limit.

REGISTRATION: `python tools/make_attention_diagnostic.py freeze` before running; the run refuses on a configuration or
source mismatch (unless `--accept-source-drift`). Output: report/viz/attention_diagnostic.json (generated; do not commit)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_manifest as lm  # noqa: E402

from sandtable.c2_units import resolve_unit_consoles  # noqa: E402
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402

NAME = "attention"
SCENARIO = "scenarios/uc3_convoy_no_threat.json"
SEEDS = list(range(30))
SPANS = (8.0, 4.0, 2.0, 1.0)
REFERENCE = 4.0
AGENTS_PER_CONSOLE = 4
Q_AUTO, Q_OPERATOR = 0.70, 0.95
OUT = "report/viz/attention_diagnostic.json"
MANIFEST = f"doc/manifests/{NAME}.manifest.json"
ANALYSIS_FILES = ["tools/make_attention_diagnostic.py", "tools/local_manifest.py"]
BASE = {"control_mode": "direct", "autonomy_arm": "autonomous_march_unit", "leader_loss_policy": "continue",
        "console_per_march_unit": {"attention_basis": "assigned", "exceptions": False}, "comms_level": 2,
        "cargo_per_vehicle": 5.0, "duration": 300.0,
        "convoy": {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1, "pace": 10.0, "time_gap": 4.0}}
REPORTED = ("c2u_attention_mean", "c2u_quality_mean", "c2u_wt", "c2u_it", "c2u_comms_up", "c2u_comms_down",
            "c2u_serviced_frac", "c2u_requests", "c2u_abandon_link", "c2u_consoles_lost", "blue_losses", "delivered_frac")
PRIMARY = ("c2u_attention_mean", "c2u_quality_mean", "c2u_wt", "c2u_serviced_frac")


def arm_label(span: float) -> str:
    return f"span={span:g}"


def registration() -> dict:
    arms = {arm_label(s): {"params": {**BASE, "span_capacity": s},
                           "resolved": {"console_per_march_unit": resolve_unit_consoles({**BASE, "span_capacity": s})},
                           "expected_attention": min(1.0, s / AGENTS_PER_CONSOLE)} for s in SPANS}
    comps = [{"metric": m, "arm": arm_label(s), "reference": arm_label(REFERENCE), "pairing": "seed"}
             for s in SPANS if s != REFERENCE for m in REPORTED]
    analysis = {"estimate": "mean of paired differences vs span 4", "interval": "95% t interval",
                "p_values": "two-sided paired t; not adjusted, reported only as a check that unaffected quantities stay unchanged",
                "equation_check": "attention == min(1, span/4) and quality == q_auto + (q_operator - q_auto) x attention, per run",
                "primary_metrics": list(PRIMARY), "delivery": "reported, no monotonic benefit required",
                "calibration": "none: synthetic; no claim about human workload", "ranking": "none",
                "design_notes": "no threat so no host is lost; fixed 300 s horizon so the request process is movement independent"}
    return {"schema": 1, "name": NAME, "scenarios": {"diag": lm.scenario_input(SCENARIO)}, "arms": arms, "fixed": BASE,
            "seeds": list(SEEDS), "comparisons": comps, "analysis": analysis}


def _col(runs, k):
    return np.array([float(r.get(k, np.nan)) for r in runs])


def _paired(d: np.ndarray) -> dict:
    n = d.size
    se = float(d.std(ddof=1) / np.sqrt(n))
    m = float(d.mean())
    t = float(stats.t.ppf(0.975, n - 1))
    return {"mean": m, "se": se, "ci95": [m - t * se, m + t * se], "all_zero": bool(np.all(d == 0.0))}


def run(accept_source_drift: bool = False) -> dict:
    reg = registration()
    man, now, check = lm.check_before_run(MANIFEST, reg, ANALYSIS_FILES, accept_source_drift)
    scn = load_scenario(SCENARIO)
    runs = {lab: [run_mission(scn, seed=s, params=a["params"]) for s in SEEDS] for lab, a in reg["arms"].items()}
    equation = {}
    for s in SPANS:
        lab = arm_label(s)
        att, qual = _col(runs[lab], "c2u_attention_mean"), _col(runs[lab], "c2u_quality_mean")
        e_att = min(1.0, s / AGENTS_PER_CONSOLE)
        e_q = Q_AUTO + (Q_OPERATOR - Q_AUTO) * e_att
        equation[lab] = {"expected_attention": e_att, "expected_quality": e_q,
                         "max_abs_attention_dev": float(np.nanmax(np.abs(att - e_att))),
                         "max_abs_quality_dev": float(np.nanmax(np.abs(qual - e_q))),
                         "hosts_lost_max": float(np.nanmax(_col(runs[lab], "c2u_consoles_lost"))),
                         "blue_losses_max": float(np.nanmax(_col(runs[lab], "blue_losses")))}
    rows = []
    for c in reg["comparisons"]:
        rows.append({**c, **_paired(_col(runs[c["arm"]], c["metric"]) - _col(runs[c["reference"]], c["metric"]))})
    means = {lab: {m: float(np.nanmean(_col(r, m))) for m in REPORTED} for lab, r in runs.items()}
    return {"registration_hash": man["registration_hash"], "manifest_status": man["status"],
            "source_hashes_at_freeze": man["provenance"]["source_hashes"], "source_hashes_at_run": now,
            "source_check": check, "equation_check": equation, "arm_means": means, "comparisons": rows}


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "freeze":
        return lm.freeze(MANIFEST, registration(), ANALYSIS_FILES, "frozen_before_run", "Frozen before the first run of this tool.")
    out = run("--accept-source-drift" in sys.argv)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(out, indent=2))
    print(f'manifest {out["manifest_status"]} {out["registration_hash"][:12]}; source check {out["source_check"]}')
    for lab, e in out["equation_check"].items():
        print(f"  {lab:8s} expected att {e['expected_attention']:.3f} q {e['expected_quality']:.4f}  max dev att {e['max_abs_attention_dev']:.2e} "
              f"q {e['max_abs_quality_dev']:.2e}  hosts lost max {e['hosts_lost_max']:.0f}  Blue losses max {e['blue_losses_max']:.0f}")
    for lab, m in out["arm_means"].items():
        print(f"  {lab:8s}", {k: round(v, 3) for k, v in m.items() if k in PRIMARY})
    for c in out["comparisons"]:
        if c["metric"] in PRIMARY or c["metric"] == "delivered_frac":
            print(f'  {c["arm"]:8s} vs {c["reference"]} {c["metric"]:20s} {c["mean"]:+.4f} [{c["ci95"][0]:+.4f},{c["ci95"][1]:+.4f}]'
                  f'{"  (identical in every pair)" if c["all_zero"] else ""}')


if __name__ == "__main__":
    main()
