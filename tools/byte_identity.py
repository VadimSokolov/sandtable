"""Byte-identity check for the opt-in extensions.

Every increment in this project is required to default OFF and reproduce the prior model exactly.
This dumps the full metric dictionary of four scenarios over eight seeds each. Comparing two dumps
answers the question that matters: did any metric the previous model already reported change value?
New output-only keys are allowed and are reported separately, because adding a diagnostic is not the
same as perturbing a result.

    PYTHONPATH=src python3 tools/byte_identity.py dump out.json
    python3 tools/byte_identity.py compare before.json after.json
"""
from __future__ import annotations

import json
import pathlib
import sys

TOL = 1e-12
SCENARIOS = ["uc3_route_defilade", "uc5_sensor_swarm", "uc7_spoofed_advance", "sc_span_control"]
SEEDS = range(8)


def dump(out: str) -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from sandtable.scenario import load_scenario
    from sandtable.sim import run_mission

    rec = {}
    for name in SCENARIOS:
        scn = load_scenario(root / "scenarios" / f"{name}.json")
        for seed in SEEDS:
            rec[f"{name}:{seed}"] = {k: float(v) for k, v in run_mission(scn, seed).items()}
    pathlib.Path(out).write_text(json.dumps(rec, sort_keys=True, indent=0))
    print(f"wrote {out}: {len(rec)} runs, {len(next(iter(rec.values())))} metrics each")


def compare(before: str, after: str) -> None:
    a = json.loads(pathlib.Path(before).read_text())
    b = json.loads(pathlib.Path(after).read_text())
    assert a.keys() == b.keys(), "run sets differ"
    shared = set.intersection(*(set(a[k]) for k in a)) & set.intersection(*(set(b[k]) for k in b))
    added = set.union(*(set(b[k]) for k in b)) - set.union(*(set(a[k]) for k in a))
    bad = [(run, k, a[run][k], b[run][k]) for run in a for k in sorted(shared)
           if abs(a[run][k] - b[run][k]) > TOL]
    for run, k, x, y in bad[:10]:
        print(f"  DIFF {run} {k}: {x} -> {y}")
    print(f"new output-only metrics: {len(added)} ({', '.join(sorted(added)) or 'none'})")
    if bad:
        sys.exit(f"FAIL byte identity: {len(bad)} pre-existing metric values moved")
    print(f"OK byte identity: {len(shared)} pre-existing metrics identical across {len(a)} runs")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "dump":
        dump(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
