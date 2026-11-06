#!/usr/bin/env python3
"""Compare Red target-priority policies (Issue #18) on matched scenarios and seeds.

Arms in every experiment (the label is written into every row; `legacy` is the nearest-eligible rule run
through the report-only path, so it records the same statistics without changing any choice):
  legacy              order []
  ends_seen           head and trail of the column as Red sees it (position)      observable
  ends_column         head and trail of the whole living column (position)        GROUND TRUTH
  ends_identity       organizational head and trail (identity), seen basis         observable, assumes index order
  security_first      Blue security vehicles first                                 GROUND TRUTH (convoy_role)
  control_first       Blue control vehicle first                                   GROUND TRUTH (convoy_role)
  ends_then_security  ends (seen), then security                                   GROUND TRUTH for the second class

Experiments (a scenario each; all other inputs identical across arms and seeds 0..SEEDS-1):
  head_on_static  scenarios/uc3_convoy.json: Red teams on the route axis, no ambush discipline. Nothing is
                  ahead of the head, so "ends" should pick what "nearest" picks: this is the NEGATIVE
                  CONTROL. Equivalence of Blue-loss fraction is tested with ar_gate.tost (margin 0.06,
                  t_min 1.70, >= 30 paired blocks).
  abeam_ambush    scenarios/uc3_convoy_ambush.json: Red 300 m off the route, fire held until a seen
                  non-security vehicle reaches the trigger, ordered withdrawal. The POSITIVE CONTROL
                  (priority changes which vehicles are destroyed) and the setting for the main comparison.

Fixed across arms: `leader_loss_policy="continue"` (so leaderless time exists), crew metrics on, 5 units of
cargo per vehicle.
Nothing else is varied. Paired differences are arm minus legacy within an experiment and never across
experiments. P-values are Holm-adjusted within each (experiment, metric) family.

The manned-versus-autonomous march unit comparison (Issue #14) and the registered prediction of Issue #18
(item 6) are NOT run here. A first attempt compared the two arms in these scenarios and found delivery and
losses identical seed by seed, because both arms keep the same roles and behavior and differ only in crew
counts, which the combat does not read; the exposure difference was crew arithmetic, not an effect.

Caveats carried into the output:
- Priority only reorders ELIGIBLE targets; wrecks do not block the road, so a policy that "traps the
  column" is not modelled. Loss of leadership, a behavioral halt and physical blockage are separate things
  and only the first two exist here.
- Several classes read ground truth Red may not have (see the labels above).
- Red's geometry, trigger, withdrawal timing and every Red parameter are placeholders; no sourced value.
- One road, one convoy layout, SEEDS seeds. Not a ranking, and not evidence about any real engagement.

Output: report/viz/red_priority_arms.json (generated; do not commit)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ar_gate  # noqa: E402

from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402

SEEDS = 40
N_BLUE = 15
MARGIN = ar_gate.FULL_MPE            # 0.06, in units of Blue-loss fraction
FIXED = {"leader_loss_policy": "continue", "crew_metrics": True, "cargo_per_vehicle": 5.0}
ARMS = {
    "legacy": {"order": []},
    "ends_seen": {"order": ["ends"]},
    "ends_column": {"order": ["ends"], "ends_basis": "column"},
    "ends_identity": {"order": ["ends"], "end_definition": "identity"},
    "security_first": {"order": ["security"]},
    "control_first": {"order": ["control"]},
    "ends_then_security": {"order": ["ends", "security"]},
}
EXPERIMENTS = {
    "head_on_static": "scenarios/uc3_convoy.json",
    "abeam_ambush": "scenarios/uc3_convoy_ambush.json",
}
METRICS = ("blue_losses", "delivered_frac", "cargo_in_transit", "crew_steps_at_risk", "tp_head_destroyed",
           "tp_trail_destroyed", "tp_vehicles_targeted", "tp_activation_frac", "leaderless_steps")
PAIRED = ("blue_losses", "delivered_frac", "cargo_in_transit", "crew_steps_at_risk", "tp_head_destroyed",
          "tp_trail_destroyed", "leaderless_steps")
LABELS = {"ends_column": "ground truth (whole column)", "security_first": "ground truth (convoy_role)",
          "control_first": "ground truth (convoy_role)", "ends_then_security": "ground truth (security class)",
          "ends_identity": "observable; assumes index order is column order",
          "ends_seen": "observable", "legacy": "none"}


def _runs(scn, extra: dict, arm: dict) -> list[dict]:
    p = {**FIXED, **extra, "target_priority": arm}
    return [run_mission(scn, seed=s, params=p) for s in range(SEEDS)]


def _col(runs, k):
    return np.array([float(r[k]) for r in runs])


def _holm(pvals: dict) -> dict:
    order = sorted(pvals, key=lambda a: pvals[a])
    m, out, run_max = len(order), {}, 0.0
    for i, a in enumerate(order):
        run_max = max(run_max, min(1.0, (m - i) * pvals[a]))
        out[a] = run_max
    return out


def _summary(runs) -> dict:
    row = {}
    for k in METRICS:
        v = _col(runs, k)
        row[k] = float(v.mean())
        row[k + "_se"] = float(v.std(ddof=1) / np.sqrt(len(v)))
    row["policy_active_runs"] = int(sum(r["tp_priority_shots"] > 0 for r in runs))
    row["head_lost_runs"] = int(sum(r["tp_head_destroyed"] > 0 for r in runs))
    return row


def _paired(arm_runs, ref_runs) -> dict:
    out = {}
    for k in PAIRED:
        d = _col(arm_runs, k) - _col(ref_runs, k)
        se = float(d.std(ddof=1) / np.sqrt(d.size))
        tcrit = float(stats.t.ppf(0.975, d.size - 1))
        m = float(d.mean())
        p = 1.0 if se == 0 else float(2 * stats.t.sf(abs(m / se), d.size - 1))
        out[k] = {"mean": m, "se": se, "ci95": [m - tcrit * se, m + tcrit * se], "p": p}
    return out


def run_experiment(name: str, path: str) -> dict:
    scn = load_scenario(path)
    runs = {label: _runs(scn, {}, arm) for label, arm in ARMS.items()}
    rows = []
    ref = runs["legacy"]
    pairs = {a: _paired(runs[a], ref) for a in ARMS if a != "legacy"}
    for k in PAIRED:                                           # Holm within (experiment, metric)
        adj = _holm({a: pairs[a][k]["p"] for a in pairs})
        for a in pairs:
            pairs[a][k]["p_holm"] = adj[a]
    for label in ARMS:
        row = {"experiment": name, "arm": label, "knowledge": LABELS[label], "n_seeds": SEEDS,
               **_summary(runs[label])}
        if label != "legacy":
            row["paired_vs_legacy"] = pairs[label]
        rows.append(row)
    out = {"scenario": path, "rows": rows}
    if name == "head_on_static":                               # the negative control
        d = (_col(runs["ends_seen"], "blue_losses") - _col(ref, "blue_losses")) / N_BLUE
        se = float(d.std(ddof=1) / np.sqrt(d.size))
        eff = float(d.mean())
        t = eff / se if se > 0 else 0.0
        equivalent, stat = ar_gate.tost(eff, t, int(d.size), MARGIN)
        base = float(_col(ref, "blue_losses").mean() / N_BLUE)
        spread = float(d.std(ddof=1))
        tcrit = float(stats.t.ppf(1 - stats.t.sf(ar_gate.FULL_T, d.size - 1), d.size - 1))
        variants = {}
        for label, marg in (("absolute_0.06_of_loss_fraction", MARGIN),
                            ("ar_gate.margin_0.06_x_legacy_level", ar_gate.margin("blue_loss_fraction", base)),
                            ("0.06_x_sd_of_paired_contrast", ar_gate.FULL_MPE * spread)):
            ok, st = ar_gate.tost(eff, t, int(d.size), marg)
            variants[label] = {"margin": float(marg), "equivalent": bool(ok), "tost_stat": float(st)}
        out["negative_control"] = {
            "arm": "ends_seen", "metric": "blue_loss_fraction (blue_losses / 15)", "pairs": int(d.size),
            "mean_diff": eff, "se": se, "t_min": ar_gate.FULL_T,
            "alpha_each_one_sided_test": float(stats.t.sf(ar_gate.FULL_T, d.size - 1)),
            "ci_equivalent_two_sided_level": float(1 - 2 * stats.t.sf(ar_gate.FULL_T, d.size - 1)),
            "ci_at_that_level": [eff - ar_gate.FULL_T * se, eff + ar_gate.FULL_T * se],
            "primary_margin": MARGIN, "equivalent": bool(equivalent), "tost_stat": float(stat),
            "margin_note": "The primary margin (absolute 0.06 of the loss fraction) was fixed in the tool before "
                           "any result was inspected. The issue says '0.06 of the contrast spread', which is not "
                           "defined; the two other readings below were added AFTER the results were seen and are "
                           "an exploratory sensitivity check.",
            "margin_variants_exploratory": variants,
            "scope": "this metric, this arm, this head-on setting only"}
    return out


NAME = "red_priority"
MANIFEST = "doc/manifests/red_priority.manifest.json"


def registration() -> dict:
    """The definitions of this sweep as a manifest (src/sandtable/manifest.py). This sweep was run, and its
    results examined, BEFORE this function existed, so its manifest is `post_hoc`: it fixes the definitions
    for reproducibility and is not a preregistration."""
    from sandtable import manifest
    from sandtable.target_priority import resolve_target_priority
    arms = {lab: {"params": {**FIXED, "target_priority": arm},
                  "resolved": {"target_priority": resolve_target_priority({"target_priority": arm})}}
            for lab, arm in ARMS.items()}
    comparisons = [{"experiment": e, "arm": lab, "reference": "legacy", "metric": m, "pairing": "seed",
                    "adjustment": "Holm within (experiment, metric)"}
                   for e in EXPERIMENTS for lab in ARMS if lab != "legacy" for m in PAIRED]
    comparisons.append({"experiment": "head_on_static", "arm": "ends_seen", "reference": "legacy",
                        "metric": "blue_loss_fraction", "test": "ar_gate.tost", "primary_margin": MARGIN,
                        "t_min": ar_gate.FULL_T, "primary_margin_fixed": "before results were inspected",
                        "exploratory_margins": ["ar_gate.margin 0.06 x legacy level", "0.06 x sd of paired contrast"],
                        "exploratory_margins_added": "after results were inspected"})
    analysis = {"interval": "95% t interval", "p_values": "two-sided paired t, Holm-adjusted", "n_blue": N_BLUE,
                "ranking": "none"}
    return manifest.build_registration(NAME, EXPERIMENTS, arms, FIXED, list(range(SEEDS)), comparisons, analysis)


def main() -> None:
    out = {"seeds": SEEDS, "fixed": FIXED, "margin": MARGIN,
           "caveat": "Verification and exploration, not a ranking. Paired differences are against legacy within "
                     "an experiment; P-values are Holm-adjusted within (experiment, metric). Priority only "
                     "reorders eligible targets, wrecks do not block the road, several classes read ground "
                     "truth, and every Red parameter is a placeholder.",
           "experiments": {n: run_experiment(n, p) for n, p in EXPERIMENTS.items()}}
    path = Path("report/viz/red_priority_arms.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    for n, e in out["experiments"].items():
        print(n)
        for r in e["rows"]:
            d = r.get("paired_vs_legacy", {}).get("blue_losses")
            dtxt = "ref" if d is None else f'{d["mean"]:+.2f} [{d["ci95"][0]:+.2f},{d["ci95"][1]:+.2f}] holm p={d["p_holm"]:.2f}'
            print(f'  {r["arm"]:19s} losses {r["blue_losses"]:5.2f} delivered {r["delivered_frac"]:.2f} '
                  f'headX {r["tp_head_destroyed"]:4.2f} active {r["policy_active_runs"]:2d}/{r["n_seeds"]}  d(losses) {dtxt}')
        if "negative_control" in e:
            print("  negative control:", e["negative_control"])


if __name__ == "__main__":
    main()
