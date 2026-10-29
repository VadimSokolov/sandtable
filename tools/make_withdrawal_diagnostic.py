#!/usr/bin/env python3
"""Diagnostic: why did lane blocking not lower delivery? (Issue #18, follow-up to tools/make_lane_block_arms.py)

OBSERVATION being investigated (from the registered lane-block experiment): with lane blocking on, delivered
fraction was often HIGHER than with it off. One untested possibility: the ambush template's scripted
withdrawal ends Red fire a fixed time after launch, so a column held by a wreck waits out Red's fire window.

DESIGN: the same abeam-ambush scenario, with the ambush withdrawal (a) as scripted, and (b) disabled (the `withdraw`
key removed; every other input unchanged), crossed with lane blocking off, at 60 s and at 300 s, and with two Red
targeting rules (legacy and control-first). Seeds 0..29, matched across every arm. Report-only target priority is on
in every arm so Red's first and last shot are recorded; it selects exactly as the legacy rule does.

WITHDRAWAL TIMING: the scripted withdrawal is timed from AMBUSH ACTIVATION (the launch tick), not from mission start:
`ambush.step` measures `after_s` from `launch_step`. A loss-fraction trigger is not used here.

Recorded per run, for inspection: the tick a wreck first appeared (`lane_first_block_step`), the last release tick
(`lane_last_release_step`), the launch and withdrawal ticks, Red's first and last shot, the ticks at which the
column's head and its last living vehicle passed the Red force's along-route position (`head_pass_step`,
`tail_pass_step`), and cargo delivery (`delivered_frac`, `time_to_delivery`).

Comparisons (paired by seed, Holm-adjusted within (family, metric, targeting)):
  block_effect       blocking at r minus blocking off, within each withdrawal condition
  withdrawal_interaction  (block effect with withdrawal disabled) minus (block effect with scripted withdrawal)
This is a diagnostic, not a search for a preferred result: no parameter is changed to make blockage reduce delivery.

REGISTRATION: `registration()` is frozen with `tools/manifest_cli.py freeze withdrawal --status frozen_before_run`
BEFORE the run. `run` refuses to start if the configuration hash differs, or if the simulation or analysis source
differs from the hashes recorded at freezing (unless `--accept-source-drift`, which is recorded in the output).

Output: report/viz/withdrawal_diagnostic.json (generated; do not commit)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sandtable import engagement, manifest  # noqa: E402
from sandtable.ambush import resolve_ambush  # noqa: E402
from sandtable.entities import BLUE, GROUND, RED  # noqa: E402
from sandtable.lane_block import resolve_lane_blocking  # noqa: E402
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402
from sandtable.target_priority import resolve_target_priority  # noqa: E402

NAME = "withdrawal"
SCENARIO = "scenarios/uc3_convoy_ambush.json"
SEEDS = list(range(30))
FIXED = {"leader_loss_policy": "continue", "crew_metrics": True, "cargo_per_vehicle": 5.0}
TARGETING = {"legacy": [], "control_first": ["control"]}
WITHDRAWAL = ("scripted", "disabled")
RECOVERY = {"off": None, "r60": 60.0, "r300": 300.0}
STANDOFF_M = 20.0
OUTCOMES = ("success", "delivered_frac", "blue_losses")
TIMING = ("lane_first_block_step", "lane_last_release_step", "ambush_launch_step", "ambush_withdraw_step",
          "tp_first_shot_step", "tp_last_shot_step", "head_pass_step", "tail_pass_step", "time_to_delivery",
          "lane_blocked_vehicle_steps")
OUT = "report/viz/withdrawal_diagnostic.json"
MANIFEST = f"doc/manifests/{NAME}.manifest.json"
ANALYSIS_FILES = ["tools/make_withdrawal_diagnostic.py"]


def _ambush(w: str) -> dict:
    cfg = dict(load_scenario(SCENARIO).params["ambush"])
    if w == "disabled":
        cfg.pop("withdraw")
    return cfg


def arm_label(t: str, w: str, r: str) -> str:
    return f"{t}|{w}|{r}"


def arm_params(t: str, w: str, r: str) -> dict:
    p = {**FIXED, "target_priority": {"order": TARGETING[t]}, "ambush": _ambush(w)}
    if RECOVERY[r] is not None:
        p["lane_blocking"] = {"recovery_time_s": RECOVERY[r], "standoff_m": STANDOFF_M}
    return p


def registration() -> dict:
    arms = {}
    for t in TARGETING:
        for w in WITHDRAWAL:
            for r in RECOVERY:
                p = arm_params(t, w, r)
                arms[arm_label(t, w, r)] = {"params": p, "resolved": {
                    "target_priority": resolve_target_priority(p), "lane_blocking": resolve_lane_blocking(p),
                    "ambush": resolve_ambush(p)}}
    comps = []
    for t in TARGETING:
        for r in ("r60", "r300"):
            for m in OUTCOMES:
                for w in WITHDRAWAL:
                    comps.append({"family": "block_effect", "metric": m, "targeting": t, "withdrawal": w,
                                  "arm": arm_label(t, w, r), "reference": arm_label(t, w, "off"), "pairing": "seed"})
                comps.append({"family": "withdrawal_interaction", "metric": m, "targeting": t, "recovery": r,
                              "definition": "(disabled|r - disabled|off) - (scripted|r - scripted|off)", "pairing": "seed"})
    analysis = {"estimate": "mean of paired differences", "interval": "95% t interval",
                "p_values": "two-sided paired t, Holm-adjusted within (family, metric, targeting)",
                "withdrawal_timing": "scripted withdrawal is timed from ambush activation (launch tick), not mission start",
                "disabled_withdrawal": "the ambush 'withdraw' key removed; all other inputs unchanged",
                "passage_definition": "tick when the foremost / rearmost living Blue ground vehicle first has x >= mean x of the "
                                      "initial Red force; -1 if never",
                "timing_recorded": list(TIMING), "diagnostic_only": True, "ranking": "none", "equivalence_claims": "none"}
    return manifest.build_registration(NAME, {"ambush": SCENARIO}, arms, FIXED, SEEDS, comps, analysis)


def _run_one(scn, params: dict, seed: int) -> dict:
    """run_mission with the passage ticks recorded by wrapping the engagement step (one call per tick)."""
    orig, st = engagement.step, {"k": 0, "head": -1, "tail": -1, "xr": None}

    def spy(ent, *a, **kw):
        if st["xr"] is None:
            st["xr"] = float(ent.x[(ent.side == RED)].mean())
        bg = (ent.side == BLUE) & (ent.domain == GROUND) & ent.alive
        if bg.any():
            if st["head"] < 0 and ent.x[bg].max() >= st["xr"]:
                st["head"] = st["k"]
            if st["tail"] < 0 and ent.x[bg].min() >= st["xr"]:
                st["tail"] = st["k"]
        st["k"] += 1
        return orig(ent, *a, **kw)

    engagement.step = spy
    try:
        r = dict(run_mission(scn, seed=seed, params=params))
    finally:
        engagement.step = orig
    r["head_pass_step"], r["tail_pass_step"] = float(st["head"]), float(st["tail"])
    return r


def _col(runs, k, default=None):
    out = []
    for r in runs:
        v = r.get(k, default)
        out.append(np.nan if v is None else float(v))
    return np.array(out)


def _paired(d: np.ndarray) -> dict:
    n = d.size
    se = float(d.std(ddof=1) / np.sqrt(n))
    t = float(stats.t.ppf(0.975, n - 1))
    m = float(d.mean())
    return {"mean": m, "se": se, "ci95": [m - t * se, m + t * se],
            "p": 1.0 if se == 0 else float(2 * stats.t.sf(abs(m / se), n - 1))}


def _holm(items: list) -> None:
    order = sorted(range(len(items)), key=lambda i: items[i]["p"])
    m, run = len(items), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * items[i]["p"]))
        items[i]["p_holm"] = run


def run(accept_source_drift: bool = False) -> dict:
    reg = registration()
    path = Path(MANIFEST)
    if not path.exists():
        raise SystemExit(f"no manifest at {MANIFEST}: freeze it first (tools/manifest_cli.py freeze {NAME})")
    man = json.loads(path.read_text())
    ok, why = manifest.verify_manifest(man, reg)
    if not ok:
        raise SystemExit(f"configuration does not match the frozen manifest, not running: {why}")
    sok, swhy, now = manifest.verify_source(man, ANALYSIS_FILES)
    if sok is not True and not accept_source_drift:
        raise SystemExit(f"source check failed, not running ({swhy}); rerun with --accept-source-drift to record it")
    scn = load_scenario(SCENARIO)
    runs = {lab: [_run_one(scn, a["params"], s) for s in SEEDS] for lab, a in reg["arms"].items()}
    rows, groups = [], {}
    for c in reg["comparisons"]:
        if c["family"] == "block_effect":
            d = _col(runs[c["arm"]], c["metric"]) - _col(runs[c["reference"]], c["metric"])
        else:
            t, r, m = c["targeting"], c["recovery"], c["metric"]
            eff = {w: _col(runs[arm_label(t, w, r)], m) - _col(runs[arm_label(t, w, "off")], m) for w in WITHDRAWAL}
            d = eff["disabled"] - eff["scripted"]
        row = {**c, **_paired(d)}
        rows.append(row)
        groups.setdefault((c["family"], c["metric"], c["targeting"]), []).append(row)
    for items in groups.values():
        _holm(items)
    arm_means = {lab: {k: (float(np.nanmean(_col(r, k))) if np.isfinite(_col(r, k)).any() else None)
                       for k in OUTCOMES + TIMING} for lab, r in runs.items()}
    per_run = {lab: [{k: (None if not np.isfinite(v) else v) for k, v in
                      zip(("seed",) + OUTCOMES + TIMING, [s] + [float(x.get(k, np.nan)) for k in OUTCOMES + TIMING])}
                     for s, x in zip(SEEDS, r)] for lab, r in runs.items()}
    return {"registration_hash": man["registration_hash"], "manifest_status": man["status"],
            "source_hashes_at_freeze": man["provenance"].get("source_hashes"), "source_hashes_at_run": now,
            "source_check": {"ok": sok, "message": swhy, "drift_accepted": bool(accept_source_drift and sok is not True)},
            "arm_means": arm_means, "per_run": per_run, "comparisons": rows}


def main() -> None:
    out = run("--accept-source-drift" in sys.argv)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(out, indent=2))
    print(f'manifest {out["manifest_status"]} {out["registration_hash"][:12]}; source check {out["source_check"]}')
    cols = ("delivered_frac", "success", "ambush_withdraw_step", "tp_last_shot_step", "head_pass_step", "tail_pass_step",
            "lane_first_block_step", "lane_last_release_step")
    for lab, m in out["arm_means"].items():
        print(f"  {lab:28s}", {k: (None if m[k] is None else round(m[k], 2)) for k in cols})
    for c in out["comparisons"]:
        if c["metric"] == "delivered_frac":
            tag = c.get("withdrawal") or "interaction"
            print(f'  {c["family"]:22s} {c["targeting"]:13s} {c.get("recovery") or c["arm"]:26s} {tag:10s} '
                  f'{c["mean"]:+.3f} [{c["ci95"][0]:+.3f},{c["ci95"][1]:+.3f}] holm {c["p_holm"]:.3f}')


if __name__ == "__main__":
    main()
