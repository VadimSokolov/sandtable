"""Reproducibility manifest and registration hash for an experiment (Issue #18, Change item 5).

A manifest says what an experiment IS before it is run: the resolved configuration of every arm, the
scenario inputs, the seed list, the comparison definitions and the analysis settings. The registration
hash is the SHA-256 of a canonical serialization of exactly that content, so any later change to any of it
changes the hash.

What is hashed ("registration"): schema version, experiment name, scenario inputs (the parsed scenario
file, so whitespace does not matter), resolved arm configuration, fixed parameters, seed list, comparison
definitions, analysis settings.

What is NOT hashed: outputs and results, timestamps, the source revision, the status and notes. The source
revision (git commit, dirty flag) is recorded next to the hash in "provenance" and is a separate fact: the
same registration can be run on different commits, and two commits can differ without changing it.

Canonical serialization: JSON with sorted keys, no whitespace, ASCII only, NaN and infinity rejected, numpy
scalars and arrays converted to Python numbers and lists, tuples to lists. Floats use Python's shortest
round-trip representation, so equal numbers serialize equally.

SOURCE HASHES (provenance, never part of the registration hash). The registration hash fixes WHAT is run; the
source hashes say WHICH CODE ran it. Two digests are recorded, each over the SHA-256 of the file bytes on disk
(so uncommitted content counts, and a dirty working tree is visible in the file list):
  simulation  every `src/sandtable/**/*.py`
  analysis    the files an experiment tool lists in its `ANALYSIS_FILES` (the tool itself)
Scope, stated explicitly: NOT covered are tests, docs, scenario files (they are in the registration), generated
outputs, and third-party code (numpy, scipy, Python itself: only their versions are recorded). A manifest frozen
before this existed has no source hashes; it is reported as "not recorded" and nothing is inferred about its code.

Status words, and what they permit:
  frozen_before_run  the manifest was written and its hash recorded BEFORE the experiment was run. Only this
                     status may be called a registration. The run tool refuses to start if the hash no longer
                     matches the definitions.
  post_hoc           the manifest was written AFTER results were examined. It documents and fixes the
                     definitions for reproducibility. It is not a preregistration and must not be described as one.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np

SCHEMA = 1
STATUSES = ("frozen_before_run", "post_hoc")


def _plain(o):
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, np.ndarray):
        return _plain(o.tolist())
    if isinstance(o, np.generic):
        return o.item()
    return o


def canonical(obj) -> str:
    """Canonical JSON text of `obj` (see the module docstring)."""
    return json.dumps(_plain(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def registration_hash(registration: dict) -> str:
    return hashlib.sha256(canonical(registration).encode("ascii")).hexdigest()


def scenario_input(path: str | Path) -> dict:
    """The scenario file as parsed JSON, plus its path. Parsed, so formatting changes do not change the hash."""
    return {"path": str(path), "content": json.loads(Path(path).read_text())}


def build_registration(name: str, scenarios: dict, arms: dict, fixed: dict, seeds: list, comparisons: list,
                       analysis: dict) -> dict:
    """The hashed content. `scenarios` maps a label to a scenario file path; `arms` maps a label to the
    resolved parameter dict that arm passes to `run_mission`."""
    return {"schema": SCHEMA, "name": name,
            "scenarios": {k: scenario_input(v) for k, v in sorted(scenarios.items())},
            "arms": arms, "fixed": fixed, "seeds": [int(s) for s in seeds],
            "comparisons": comparisons, "analysis": analysis}


def source_revision(repo: str | Path = ".") -> dict:
    """The git commit and whether the working tree differs from it. Recorded, never hashed."""
    def git(*a):
        return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=False).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": sorted(line[3:] for line in git("status", "--porcelain").splitlines()
                                  if not line[3:].startswith("report/"))}


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(files: dict) -> str:
    return hashlib.sha256(canonical(sorted(files.items())).encode("ascii")).hexdigest()


def source_hashes(analysis_files, repo: str | Path = ".") -> dict:
    """Hashes of the simulation source and the analysis source as they are on disk now (see the module docstring)."""
    repo = Path(repo)
    sim = {str(p.relative_to(repo)): _file_hash(p) for p in sorted((repo / "src" / "sandtable").rglob("*.py"))}
    ana = {str(Path(f)): _file_hash(repo / f) for f in sorted(analysis_files)}
    import numpy
    import scipy
    return {"simulation": {"files": sim, "digest": _digest(sim)}, "analysis": {"files": ana, "digest": _digest(ana)},
            "scope_note": "simulation = src/sandtable/**/*.py; analysis = the tool's ANALYSIS_FILES; not covered: tests, "
                          "docs, scenario files (in the registration), outputs, third-party code (versions only)",
            "environment": {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__}}


def make_manifest(registration: dict, status: str, note: str = "", repo: str | Path = ".",
                  analysis_files=None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"manifest status must be one of {list(STATUSES)}, got {status!r}")
    prov = {"source_revision": source_revision(repo)}
    if analysis_files is not None:
        prov["source_hashes"] = source_hashes(analysis_files, repo)
    return {"registration_hash": registration_hash(registration), "status": status, "note": note,
            "provenance": prov, "registration": registration}


def verify_source(manifest: dict, analysis_files, repo: str | Path = ".") -> tuple[bool | None, str, dict]:
    """Compare the recorded source digests with the code on disk now. Returns (ok, message, current_hashes);
    ok is None when the manifest recorded no source hashes (nothing can be said about its code)."""
    now = source_hashes(analysis_files, repo)
    rec = manifest.get("provenance", {}).get("source_hashes")
    if rec is None:
        return None, "no source hashes were recorded in this manifest", now
    bad = [part for part in ("simulation", "analysis") if rec[part]["digest"] != now[part]["digest"]]
    if not bad:
        return True, "ok", now
    changed = sorted(f for part in bad for f in set(rec[part]["files"]) | set(now[part]["files"])
                     if rec[part]["files"].get(f) != now[part]["files"].get(f))
    return False, f"{' and '.join(bad)} source differs from the frozen hashes: {', '.join(changed[:8])}", now


def verify_manifest(manifest: dict, current_registration: dict) -> tuple[bool, str]:
    """True when the manifest's recorded hash equals the hash of the registration rebuilt from the
    CURRENT definitions, and also equals the hash of the registration stored in the manifest."""
    stored = registration_hash(manifest["registration"])
    now = registration_hash(current_registration)
    if stored != manifest["registration_hash"]:
        return False, "the manifest's stored registration no longer matches its recorded hash (edited by hand?)"
    if now != manifest["registration_hash"]:
        return False, f"current definitions hash to {now[:12]}, manifest recorded {manifest['registration_hash'][:12]}"
    return True, "ok"
