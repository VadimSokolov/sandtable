"""Local reproducibility-manifest helpers for Issue #19 diagnostics (a stand-in; see the notes below).

SCOPE AND LIMITATIONS (read before relying on it)
  * It hashes the CONFIGURATION: canonical JSON (sorted keys, no whitespace, ASCII, NaN rejected, numpy scalars
    converted) of the registration dict the experiment builds. Scenario files enter as parsed JSON content.
  * It records, separately, SHA-256 digests of `src/sandtable/**/*.py` and of the files an experiment lists as
    analysis files, from the bytes on disk (so uncommitted content counts), plus the git commit and branch, and
    numpy and Python versions. Not covered: tests, docs, outputs, third-party code.
  * It has NO status validation, NO verify command, and NO dirty-file listing. `freeze` refuses to overwrite.
  * It was written for this branch because the full manifest tooling (`sandtable.manifest`, `tools/manifest_cli.py`)
    exists only on the Issue #18 branch, which is not merged here. Its compatibility with that tooling is NOT
    claimed; see the plan for the one-way check that was actually run.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np


def _plain(o):
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    return o


def canonical(obj) -> str:
    return json.dumps(_plain(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def reg_hash(reg: dict) -> str:
    return hashlib.sha256(canonical(reg).encode("ascii")).hexdigest()


def scenario_input(path: str) -> dict:
    return {"path": path, "content": json.loads(Path(path).read_text())}


def source_hashes(analysis_files, repo: str = ".") -> dict:
    root = Path(repo)
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()   # noqa: E731
    sim = {str(p.relative_to(root)): h(p) for p in sorted((root / "src" / "sandtable").rglob("*.py"))}
    ana = {f: h(root / f) for f in sorted(analysis_files)}
    dig = lambda d: hashlib.sha256(canonical(sorted(d.items())).encode("ascii")).hexdigest()   # noqa: E731
    git = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True).stdout.strip()   # noqa: E731
    return {"simulation": {"files": sim, "digest": dig(sim)}, "analysis": {"files": ana, "digest": dig(ana)},
            "git_commit": git("rev-parse", "HEAD"), "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "environment": {"python": platform.python_version(), "numpy": np.__version__}}


def freeze(path: str, reg: dict, analysis_files, status: str, note: str) -> None:
    p = Path(path)
    if p.exists():
        raise SystemExit(f"{p} exists; a frozen manifest is never overwritten")
    man = {"registration_hash": reg_hash(reg), "status": status, "note": note,
           "provenance": {"source_hashes": source_hashes(analysis_files)}, "registration": reg}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"{status} {man['registration_hash']} -> {p}")


def check_before_run(path: str, reg: dict, analysis_files, accept_source_drift: bool) -> tuple[dict, dict, dict]:
    """Refuse unless the configuration and (by default) the source match the frozen manifest.
    Returns (manifest, current source hashes, check summary)."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"no manifest at {p}: freeze it first")
    man = json.loads(p.read_text())
    if reg_hash(man["registration"]) != man["registration_hash"] or reg_hash(reg) != man["registration_hash"]:
        raise SystemExit("configuration does not match the frozen manifest, not running")
    now = source_hashes(analysis_files)
    rec = man["provenance"]["source_hashes"]
    bad = [q for q in ("simulation", "analysis") if rec[q]["digest"] != now[q]["digest"]]
    ok = not bad
    msg = "ok" if ok else f"{' and '.join(bad)} source differs from the frozen hashes"
    if not ok and not accept_source_drift:
        raise SystemExit(f"source check failed, not running ({msg}); rerun with --accept-source-drift to record it")
    return man, now, {"ok": ok, "message": msg, "drift_accepted": bool(accept_source_drift and not ok)}
