#!/usr/bin/env python3
"""Run the Issue #17 leader-loss policies on matched scenarios and seeds and write a labeled table.

Every arm sees the same scenario, the same convoy and the same seeds 0..SEEDS-1. The policies draw no
random numbers, but a different behavior changes the trajectory, so engagement draws diverge after the
first loss: the arms are paired by seed, not identical afterwards.

Two experiments, labeled in every row:
  forced_head_kill  the head of march unit 0 is destroyed at step KILL_STEP in every run, whatever Red
                    does. This isolates what each policy does after a loss. It is a verification
                    design, not a realistic engagement.
  engagement        nothing is forced; a loss happens only when Red kills a head. `head_loss_runs` says how
                    many of the seeds had one (recorded for every arm, legacy included). Rows with few
                    loss runs say little about the policy.

Arms: `legacy`; `continue`; `promote` and `absorb` at several handoff delays (0 is an idealized baseline:
the new head acts on the tick after the loss); `halt` with no release (a bound: it can only end when the
mission does), with `clear_steps`, with `max_hold_steps`, and with both (either one ends the halt).

Caveats carried into the output:
- `clear_steps` is judged on ground-truth Red positions and ranges, not on what Blue has detected.
- `absorb` is an experimental logical reassignment (nearest living unit in the serial); it is not
  something ATV-S documentation describes.
- The handoff delays are swept values with no public source.
- These are simulation policies, not documented ATV-S capabilities. Differences are against `legacy` only,
  so two non-legacy arms are not compared with each other, and an interval containing zero does not show
  an arm is equivalent to `legacy`. The `absorb` advantage is unexplained: it may be an artifact of the
  reassignment device.
- Means with standard errors, plus the paired difference to `legacy` (same seed in both arms) with a 95%
  t interval, computed separately inside each experiment. Many comparisons are made, so a few intervals
  exclude zero by chance; the count is reported. Do not rank policies from this, and do not read the
  forced_head_kill rows as a ranking either.
- `absorb` under `succession="manned_only"` only attaches to a receiving head with crew; crew is zero
  unless declared, and this sweep declares none, so the absorb arms here use `succession="any"`.

Output: report/viz/leader_loss_arms.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sandtable import behavior
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SEEDS = 20
KILL_STEP = 15
UNIT = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1, "pace": 10.0,
        "time_gap": 4.0, "cargo_per_vehicle": 5.0, "blue_behavior": "leader_follow"}
KEYS = ("success", "delivered_frac", "time_to_delivery", "time_to_objective", "cargo_lost",
        "cargo_in_transit", "blue_losses", "leaderless_steps", "ll_halt_steps", "ll_handoffs",
        "first_leader_loss_step")

ARMS = {
    "legacy": {"leader_loss_policy": "legacy"},
    "continue": {"leader_loss_policy": "continue"},
    "promote_h0_idealized": {"leader_loss_policy": "promote", "handoff_steps": 0},
    "promote_h5": {"leader_loss_policy": "promote", "handoff_steps": 5},
    "promote_h20": {"leader_loss_policy": "promote", "handoff_steps": 20},
    "absorb_h0_idealized": {"leader_loss_policy": "absorb", "handoff_steps": 0},
    "absorb_h5": {"leader_loss_policy": "absorb", "handoff_steps": 5},
    "absorb_h20": {"leader_loss_policy": "absorb", "handoff_steps": 20},
    "halt_no_release": {"leader_loss_policy": "halt"},
    "halt_clear10": {"leader_loss_policy": "halt", "halt_release": {"clear_steps": 10}},
    "halt_max30": {"leader_loss_policy": "halt", "halt_release": {"max_hold_steps": 30}},
    "halt_clear10_max30": {"leader_loss_policy": "halt",
                           "halt_release": {"clear_steps": 10, "max_hold_steps": 30}},
}


PAIRED_KEYS = ("success", "delivered_frac", "cargo_in_transit", "cargo_lost", "blue_losses")
REFERENCE = "legacy"


def _run_one(scn, params: dict, seed: int, force: bool) -> dict:
    """One mission. Records whether any march unit head was destroyed (`head_lost`) for EVERY arm,
    including legacy, and with `force` destroys the head of march unit 0 at KILL_STEP."""
    orig, seen = behavior.step, {}

    def patched(ent, bhv, op, comms, scn_, k, rng, world=None):
        if "heads" not in seen:
            seen["heads"] = np.nonzero((ent.side == 0) & (ent.march_unit >= 0) & (ent.leader == -1))[0]
        if force and k == KILL_STEP:
            ent.alive[int(np.nonzero(ent.march_unit == 0)[0][0])] = False
        out = orig(ent, bhv, op, comms, scn_, k, rng, world=world)
        seen["lost"] = seen.get("lost", False) or bool((~ent.alive[seen["heads"]]).any())
        return out

    behavior.step = patched
    try:
        r = dict(run_mission(scn, seed=seed, params=params))
    finally:
        behavior.step = orig
    r["head_lost"] = float(seen.get("lost", False))
    return r


def _t95(n: int) -> float:
    from scipy import stats
    return float(stats.t.ppf(0.975, n - 1))


def _row(experiment: str, label: str, runs: list[dict], ref: list[dict]) -> dict:
    """Per-arm means with standard errors, how often a head was actually lost, and the paired
    difference to the reference arm (same seed in both)."""
    n = len(runs)
    row = {"experiment": experiment, "arm": label, "n_seeds": n,
           "head_loss_runs": int(sum(r["head_lost"] for r in runs))}
    for k in KEYS:
        vals = [float(r[k]) for r in runs if k in r and r[k] == r[k] and r[k] is not None]
        row[k] = float(np.mean(vals)) if vals else None
        row[k + "_se"] = float(np.std(vals, ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else None
    if label != REFERENCE:
        diffs = {}
        for k in PAIRED_KEYS:
            d = np.array([float(a[k]) - float(b[k]) for a, b in zip(runs, ref)
                          if k in a and k in b and a[k] == a[k] and b[k] == b[k]])
            if d.size > 1:
                se = float(d.std(ddof=1) / np.sqrt(d.size))
                m = float(d.mean())
                diffs[k] = {"mean": m, "se": se, "ci95": [m - _t95(d.size) * se, m + _t95(d.size) * se],
                            "n_pairs": int(d.size), "sig_at_95": bool(abs(m) > _t95(d.size) * se)}
        row["paired_vs_" + REFERENCE] = diffs
    return row


def run(scenario_path: str = "scenarios/uc3_convoy.json") -> dict:
    scn = load_scenario(scenario_path)
    rows = []
    for experiment, force in (("forced_head_kill", True), ("engagement", False)):
        runs = {label: [_run_one(scn, {**UNIT, **arm}, s, force) for s in range(SEEDS)]
                for label, arm in ARMS.items()}
        rows += [_row(experiment, label, runs[label], runs[REFERENCE]) for label in ARMS]
    n_tests = sum(len(r.get("paired_vs_" + REFERENCE, {})) for r in rows)
    n_sig = sum(v["sig_at_95"] for r in rows for v in r.get("paired_vs_" + REFERENCE, {}).values())
    return {"scenario": scenario_path, "seeds": SEEDS, "kill_step": KILL_STEP, "reference": REFERENCE,
            "paired_comparisons": n_tests, "paired_significant_at_95": n_sig,
            "caveat": "Configurable simulation policies, not documented ATV-S capabilities. Verification and "
                      "exploration, not a ranking. Every paired difference is against legacy, so it is not "
                      "a comparison between two other arms. An interval containing zero does not show "
                      "equivalence. The absorb advantage is unexplained and exploratory. "
                      "Differences are paired by seed within "
                      "each experiment and never across experiments. After the first loss the arms' "
                      "engagement draws diverge, so pairing only removes the pre-loss noise. With this "
                      "many comparisons some 95% intervals exclude zero by chance. clear_steps uses "
                      "ground-truth Red; absorb is an experimental logical reassignment; handoff delays "
                      "are unsourced and 0 is an idealized baseline.",
            "rows": rows}


def main() -> None:
    out = run()
    path = Path("report/viz/leader_loss_arms.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    print(f'{out["paired_significant_at_95"]} of {out["paired_comparisons"]} paired differences exclude 0 at 95%')
    for r in out["rows"]:
        d = r.get("paired_vs_" + REFERENCE, {}).get("delivered_frac")
        dtxt = "ref" if d is None else f'{d["mean"]:+.3f} [{d["ci95"][0]:+.3f},{d["ci95"][1]:+.3f}]'
        print(f'{r["experiment"]:17s} {r["arm"]:22s} head_loss_runs {r["head_loss_runs"]:2d}/{r["n_seeds"]} '
              f'delivered_frac {r["delivered_frac"]:.2f}  paired d(delivered_frac) vs {REFERENCE}: {dtxt}')


if __name__ == "__main__":
    main()
