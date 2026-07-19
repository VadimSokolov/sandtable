"""Collect a polarisopt study workspace into one tidy CSV (one row per design).

Reads every ``experiments/sim-*/`` folder under a study workspace, joins each design's
``inputs.json`` params with the scalar KPI means in ``outputs.json``, and writes a flat CSV.

Usage:
    python experiments/analysis/collect_results.py <workspace_dir> <out.csv>
    # e.g. .../sandtable-runs/centerpiece-direct  ->  experiments/results/centerpiece_direct.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Scalar KPI keys we keep from outputs.json (drop the per-run "repeats" list and non-scalars).
_KPI = [
    "success", "success_rate", "time_to_objective", "t_obj_success", "blue_losses",
    "red_losses", "blue_survivors", "arrived", "blue_loss_frac", "red_loss_frac",
    "loss_exchange", "mission_time", "detection_coverage", "n_repeats", "seed",
]


def collect(workspace: str) -> pd.DataFrame:
    root = Path(workspace) / "experiments"
    rows = []
    for sim in sorted(root.glob("sim-*")):
        ip, op = sim / "inputs.json", sim / "outputs.json"
        if not (ip.exists() and op.exists()):
            continue
        inp = json.loads(ip.read_text())
        out = json.loads(op.read_text())
        row = {"sim": sim.name}
        row.update(inp.get("params", {}))
        for k in _KPI:
            if k in out:
                row[k] = out[k]
        rows.append(row)
    if not rows:
        raise SystemExit(f"no completed sim-*/outputs.json found under {root}")
    df = pd.DataFrame(rows).sort_values("sim").reset_index(drop=True)
    return df


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    df = collect(sys.argv[1])
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {out}  ({len(df)} designs, {len(df.columns)} cols)")
    print(df.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
