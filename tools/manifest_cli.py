#!/usr/bin/env python3
"""Freeze or verify the reproducibility manifest of a registered experiment (Issue #18).

    python tools/manifest_cli.py freeze lane_block --status frozen_before_run
    python tools/manifest_cli.py freeze red_priority --status post_hoc
    python tools/manifest_cli.py verify lane_block

An experiment module (tools/make_<name>_arms.py) exposes NAME, MANIFEST and registration(). `freeze` writes the
manifest and refuses to overwrite an existing one. `post_hoc` is for experiments whose results were already
seen: it fixes the definitions for reproducibility and is NOT a preregistration. See src/sandtable/manifest.py.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandtable import manifest  # noqa: E402

MODULES = {"lane_block": "make_lane_block_arms", "red_priority": "make_red_priority_arms",
           "withdrawal": "make_withdrawal_diagnostic"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["freeze", "verify"])
    ap.add_argument("experiment", choices=sorted(MODULES))
    ap.add_argument("--status", choices=manifest.STATUSES, default="frozen_before_run")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    mod = importlib.import_module(MODULES[a.experiment])
    path = Path(mod.MANIFEST)
    reg = mod.registration()
    if a.cmd == "freeze":
        if path.exists():
            raise SystemExit(f"{path} exists; a frozen manifest is never overwritten (delete it deliberately to redo)")
        man = manifest.make_manifest(reg, a.status, a.note, analysis_files=getattr(mod, "ANALYSIS_FILES", None))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
        print(f"{a.status} {man['registration_hash']}  -> {path}")
    else:
        man = json.loads(path.read_text())
        ok, why = manifest.verify_manifest(man, reg)
        print("configuration:", "OK" if ok else f"MISMATCH: {why}")
        files = getattr(mod, "ANALYSIS_FILES", None)
        if files is not None:
            sok, swhy, _ = manifest.verify_source(man, files)
            print("source:", {True: "OK", False: f"DIFFERS: {swhy}", None: swhy}[sok])
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
