"""Frozen evaluation harness for the FP6111 autoresearch run (workflow 7, mode I).

FROZEN. Nothing in the loop may edit this file: it defines the measurement, and an
edited measurement voids every number taken before and after the edit.

Design. A contract "seed" here is a BLOCK, not a single mission. Block b with R
replications runs mission seeds b*R .. b*R+R-1 and reports the mean metric over the
block (sandtable.sim.evaluate already uses exactly that indexing, so blocks are
disjoint by construction). Blocks give continuous, paired, low-variance values from a
simulator whose per-mission `success` is binary, which is what the paired gate needs.

Arms and sweeps. An arm is a named parameter override; a sweep varies one parameter
across values. The cross product is evaluated on a shared block set, so every
comparison is paired on identical mission seeds.

Output is one greppable row per (arm, sweep value):

    AR_ROW arm=<name> <sweep>=<value> mean=<m> vals=<v0,v1,...>

Usage:
    python3 tools/ar_eval.py --scenario scenarios/sc_span_control.json \
        --metric success --blocks 0-15 --reps 16 \
        --arm 'direct={"control_mode":"direct"}' \
        --arm 'super={"control_mode":"supervisory"}' \
        --sweep 'comms_level=0,1,2,3,4,5'
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import numpy as np  # noqa: E402

from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import evaluate  # noqa: E402


def parse_blocks(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def parse_arm(spec: str) -> tuple[str, dict]:
    """'name={json}' -> (name, params). A bare name means no overrides."""
    if "=" not in spec:
        return spec, {}
    name, payload = spec.split("=", 1)
    payload = payload.strip()
    return name.strip(), (json.loads(payload) if payload else {})


def parse_sweep(spec: str) -> tuple[str, list]:
    """'param=v1,v2,v3' -> (param, [values]). Values are JSON-decoded when possible."""
    key, payload = spec.split("=", 1)
    vals = []
    for tok in payload.split(","):
        tok = tok.strip()
        try:
            vals.append(json.loads(tok))
        except json.JSONDecodeError:
            vals.append(tok)
    return key.strip(), vals


def _one(task):
    """Evaluate a single (scenario, reps, block, params) -> metric. Module level, for pickling."""
    scn_path, reps, block, params, metric = task
    scn = load_scenario(scn_path)
    return float(evaluate(scn, n_reps=reps, seed=block, params=params)[metric])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--metric", default="success")
    ap.add_argument("--blocks", default="0-15", help="block indices, '0-15' or '0,1,2'")
    ap.add_argument("--reps", type=int, default=16, help="missions per block")
    ap.add_argument("--arm", action="append", default=[], help="name={json params}")
    ap.add_argument("--sweep", default=None, help="param=v1,v2,...")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2),
                    help="parallel workers; results are independent seeded blocks so "
                         "completion order cannot affect any value")
    args = ap.parse_args()

    blocks = parse_blocks(args.blocks)
    arms = [parse_arm(a) for a in (args.arm or ["base="])]
    sweep_key, sweep_vals = parse_sweep(args.sweep) if args.sweep else (None, [None])

    jobs = []          # (arm_name, sv, block, params)
    for arm_name, arm_params in arms:
        for sv in sweep_vals:
            params = dict(arm_params)
            if sweep_key is not None:
                params[sweep_key] = sv
            for b in blocks:
                jobs.append((arm_name, sv, b, params))

    task = [(args.scenario, args.reps, b, params, args.metric) for (_, _, b, params) in jobs]
    if args.jobs > 1 and len(task) > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            got = list(ex.map(_one, task, chunksize=1))
    else:
        got = [_one(t) for t in task]

    acc: dict = {}
    for (arm_name, sv, b, _), val in zip(jobs, got):
        acc.setdefault((arm_name, sv), []).append((b, val))
    for arm_name, _ in arms:
        for sv in sweep_vals:
            pairs = sorted(acc[(arm_name, sv)])          # restore block order
            vals = [v for _, v in pairs]
            tag = f" {sweep_key}={sv}" if sweep_key is not None else ""
            print(f"AR_ROW arm={arm_name}{tag} mean={np.mean(vals):.6f} "
                  f"vals={','.join(f'{v:.6f}' for v in vals)}", flush=True)

    print(f"AR_META scenario={args.scenario} metric={args.metric} "
          f"blocks={len(blocks)} reps={args.reps}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
