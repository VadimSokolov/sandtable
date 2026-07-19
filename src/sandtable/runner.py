"""Slave entry point: evaluate one mission-design sample from an inputs file.

Usage::

    python -m sandtable.runner inputs.json outputs.json

``inputs.json`` schema::

    {
      "scenario":  "/abs/path/to/scenarios/uc3_route_defilade.json",
      "params":    {"route_bias": 0.5, "formation_spread": 40, "tempo": 1.0},
      "seed":      42,          # optional, default 0
      "n_repeats": 20           # optional, default 1
    }

The mission is run ``n_repeats`` times with seeds ``seed, seed+1, ...`` and the
per-KPI means are written to ``outputs.json`` (top level), with the individual
runs preserved under ``"repeats"``. ``success_rate`` is the mean mission-success
indicator; ``t_obj_success`` is the mean time-to-objective over successful runs
only, whereas the unconditional ``time_to_objective`` penalizes a failed run with
the full mission duration (so it stays finite and is what an optimizer minimizes).

This mirrors the POLARIS master/slave contract: the polarisopt ``Simulator``
plugin writes ``inputs.json`` and shells out to this module; we read it, run the
pure ``sandtable.sim.run_mission`` the requested number of times, and write the scalar
KPIs the study's metric consumes. No global state, no wall-clock, deterministic
given (scenario, seed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

# The scalar KPIs run_mission emits, averaged across replications.
OUTPUT_KEYS = (
    "success", "time_to_objective", "blue_losses", "red_losses", "blue_survivors",
    "arrived", "blue_loss_frac", "red_loss_frac", "loss_exchange", "mission_time",
    "detection_coverage",
)


def evaluate(scenario_path: str, params: dict | None = None, seed: int = 0,
             n_repeats: int = 1) -> dict:
    """Run the mission ``n_repeats`` times and average the KPIs.

    Seeds are ``seed, seed+1, ..., seed+n_repeats-1``; the polarisopt plugin hands
    out disjoint seed blocks per sample (``base_seed + n_repeats*sample.id``) so
    replications never collide across a study.
    """
    if n_repeats < 1:
        raise ValueError(f"n_repeats must be >= 1, got {n_repeats}")
    scn = load_scenario(scenario_path)
    repeats = [run_mission(scn, seed=seed + i, params=params) for i in range(n_repeats)]

    means = {k: float(np.mean([r[k] for r in repeats])) for k in OUTPUT_KEYS}
    # Success rate and time conditioned on success (report-facing, un-penalized).
    succ = np.array([r["success"] for r in repeats])
    means["success_rate"] = float(succ.mean())
    won = [r["time_to_objective"] for r in repeats if r["success"] >= 1.0]
    means["t_obj_success"] = float(np.mean(won)) if won else float(scn.duration)
    return {**means, "seed": seed, "n_repeats": n_repeats, "repeats": repeats}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    input_path, output_path = Path(argv[0]), Path(argv[1])
    spec = json.loads(input_path.read_text())
    if "scenario" not in spec:
        print("inputs.json must specify a 'scenario' path", file=sys.stderr)
        return 2
    result = evaluate(
        scenario_path=spec["scenario"],
        params=spec.get("params", {}),
        seed=int(spec.get("seed", 0)),
        n_repeats=int(spec.get("n_repeats", 1)),
    )
    output_path.write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
