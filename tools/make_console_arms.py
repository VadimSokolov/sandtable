#!/usr/bin/env python3
"""One console per march unit (Issue #19): three separate comparisons, frozen before they run.

Scenario: scenarios/uc3_convoy.json, autonomous march units (one control vehicle + four crewless followers each),
direct control, leader-follow behavior, leader-loss policy `continue`, 5 cargo units per vehicle, LEADER_FOLLOW
exceptions routed to the console. Seeds 0..29, matched across every arm of a family.

Family E1, scaling units with dedicated resources (units = 2, 3, 4). Three console arrangements per size:
  legacy_single   the published model: ONE operator, attention = min(1, span_capacity / all Blue vehicles)
  shared_crew     the published crew model with n_operators = units (a pool, attention unchanged)
  per_unit        one dedicated console per march unit, attention per console (Issue #19)
  CONFOUNDS, stated up front: units = 2, 3, 4 changes the CONVOY LENGTH (10, 15, 20 vehicles) and the TOTAL PERSONNEL
  as well as the C2 resources, so the arms are compared WITHIN a size (paired by seed) and never across sizes.
  Within a size, per_unit also changes who files requests (crewed control vehicles stop asking) and the attention
  equation, not only the console topology; `shared_crew` is the intermediate arm that changes only the console count.

Family E2, workload within a fixed arrangement (3 units, per_unit): decision_interval 15, 30 (reference), 60 steps.
  Convoy, cargo, terrain and threat are identical; only the request rate changes.

Family E3, communications levels already defined by the repository (3 units, per_unit): C0 (reference) to C5.

Primary metrics (fixed before running): delivered_frac, blue_losses, c2u_serviced_frac (E2, E3 and per_unit arms of E1),
operator_goodput (E1, every arm). Secondary: success, crew_steps_at_risk, c2u_quality_mean, c2u_wt.
Uncertainty: paired differences against the family reference within the same seeds, 95% t interval, two-sided paired t
p-values, Holm-adjusted within (family, metric). Comparison families: E1 per size {shared_crew, per_unit} vs legacy_single;
E2 {15, 60} vs 30; E3 {C1..C5} vs C0.

Not calibrated: no parameter is tuned toward a console advantage. Null and counter-intuitive outcomes are reported.
Later analyses of the output are exploratory and must be labelled so.

REGISTRATION: freeze with `python tools/make_console_arms.py freeze` before running (a local stand-in for the manifest tooling
of Issue #18, which this branch does not contain). The run verifies configuration and source hashes (refusing on mismatch
unless `--accept-source-drift`, which is recorded).

Output: report/viz/console_arms.json (generated; do not commit)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hashlib  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402

NAME = "consoles"
SCENARIO = "scenarios/uc3_convoy.json"
SEEDS = list(range(30))
OUT = "report/viz/console_arms.json"
MANIFEST = f"doc/manifests/{NAME}.manifest.json"
ANALYSIS_FILES = ["tools/make_console_arms.py"]
BASE = {"control_mode": "direct", "autonomy_arm": "autonomous_march_unit", "leader_loss_policy": "continue",
        "cargo_per_vehicle": 5.0}
SIZES = (2, 3, 4)
INTERVALS = (15, 30, 60)
LEVELS = (0, 1, 2, 3, 4, 5)
PRIMARY = ("delivered_frac", "blue_losses", "c2u_serviced_frac", "operator_goodput")
SECONDARY = ("success", "crew_steps_at_risk", "c2u_quality_mean", "c2u_wt")
METRICS = PRIMARY + SECONDARY


# ---- minimal reproducibility manifest (stand-in) -----------------------------------------------------------
# The full manifest tooling (src/sandtable/manifest.py, tools/manifest_cli.py) lives on the Issue #18 branch, which is
# not merged into this branch's base. This file carries the same ideas locally so #19 does not depend on #18:
# the registration hash covers the configuration only (canonical JSON, sorted keys, no whitespace, ASCII, no NaN);
# the git commit and the SHA-256 of the simulation source (src/sandtable/**/*.py, from the bytes on disk, so
# uncommitted edits count) and of this tool are recorded SEPARATELY. Not covered: tests, docs, scenario files
# (they are in the registration), outputs, third-party code (versions only). When #18 merges, this block should be
# replaced by `sandtable.manifest`; the canonical form is the same.


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


def source_hashes(repo: str = ".") -> dict:
    root = Path(repo)
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()   # noqa: E731
    sim = {str(p.relative_to(root)): h(p) for p in sorted((root / "src" / "sandtable").rglob("*.py"))}
    ana = {f: h(root / f) for f in ANALYSIS_FILES}
    dig = lambda d: hashlib.sha256(canonical(sorted(d.items())).encode("ascii")).hexdigest()   # noqa: E731
    git = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True).stdout.strip()   # noqa: E731
    return {"simulation": {"files": sim, "digest": dig(sim)}, "analysis": {"files": ana, "digest": dig(ana)},
            "git_commit": git("rev-parse", "HEAD"), "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "environment": {"python": platform.python_version(), "numpy": np.__version__}}


def convoy(units: int) -> dict:
    return {"march_unit_size": 5, "march_units_per_serial": units, "serials_per_column": 1, "pace": 10.0, "time_gap": 4.0}


def arm_params(family: str, key) -> dict:
    p = {**BASE}
    if family == "E1":
        units, arrangement = key
        p["convoy"] = convoy(units)
        if arrangement == "shared_crew":
            p["n_operators"] = units
        elif arrangement == "per_unit":
            p["console_per_march_unit"] = {"exceptions": True}
    elif family == "E2":
        p["convoy"], p["decision_interval"] = convoy(3), key
        p["console_per_march_unit"] = {"exceptions": True}
    else:
        p["convoy"], p["comms_level"] = convoy(3), key
        p["console_per_march_unit"] = {"exceptions": True}
    return p


def arm_label(family: str, key) -> str:
    return f"{family}|{'|'.join(str(x) for x in (key if isinstance(key, tuple) else (key,)))}"


def arms() -> dict:
    out = {}
    for n in SIZES:
        for a in ("legacy_single", "shared_crew", "per_unit"):
            out[arm_label("E1", (n, a))] = ("E1", (n, a))
    for iv in INTERVALS:
        out[arm_label("E2", iv)] = ("E2", iv)
    for lv in LEVELS:
        out[arm_label("E3", lv)] = ("E3", lv)
    return out


def comparisons() -> list:
    cs = []
    for n in SIZES:
        for a in ("shared_crew", "per_unit"):
            for m in METRICS:
                cs.append({"family": "E1", "group": f"units={n}", "metric": m, "arm": arm_label("E1", (n, a)),
                           "reference": arm_label("E1", (n, "legacy_single")), "pairing": "seed"})
    for iv in (15, 60):
        for m in METRICS:
            cs.append({"family": "E2", "group": "interval", "metric": m, "arm": arm_label("E2", iv),
                       "reference": arm_label("E2", 30), "pairing": "seed"})
    for lv in LEVELS[1:]:
        for m in METRICS:
            cs.append({"family": "E3", "group": "level", "metric": m, "arm": arm_label("E3", lv),
                       "reference": arm_label("E3", 0), "pairing": "seed"})
    return cs


def registration() -> dict:
    from sandtable.c2_units import resolve_unit_consoles
    reg_arms = {lab: {"params": arm_params(f, k),
                      "resolved": {"console_per_march_unit": resolve_unit_consoles(arm_params(f, k))}}
                for lab, (f, k) in arms().items()}
    analysis = {"estimate": "mean of paired differences against the family reference", "interval": "95% t interval",
                "p_values": "two-sided paired t, Holm-adjusted within (family, group, metric)",
                "primary_metrics": list(PRIMARY), "secondary_metrics": list(SECONDARY),
                "confounds": "E1 changes convoy length and total personnel with the number of units; arms are compared "
                             "only within a size. per_unit also changes who files requests and the attention equation.",
                "missing_metrics": "c2u_* keys exist only for per_unit arms; a comparison on such a key between arms "
                                   "that lack it is reported as unavailable, not as zero",
                "equivalence_claims": "none", "ranking": "none", "later_analyses": "exploratory"}
    return {"schema": 1, "name": NAME, "scenarios": {"convoy": {"path": SCENARIO, "content": json.loads(Path(SCENARIO).read_text())}},
            "arms": reg_arms, "fixed": BASE, "seeds": list(SEEDS), "comparisons": comparisons(), "analysis": analysis}


def _col(runs, k):
    return np.array([float(r[k]) if k in r and r[k] is not None else np.nan for r in runs])


def _paired(d: np.ndarray) -> dict:
    ok = np.isfinite(d)
    if ok.sum() < 3:
        return {"available": False, "n_pairs": int(ok.sum())}
    d = d[ok]
    n = d.size
    se = float(d.std(ddof=1) / np.sqrt(n))
    t = float(stats.t.ppf(0.975, n - 1))
    m = float(d.mean())
    return {"available": True, "n_pairs": int(n), "mean": m, "se": se, "ci95": [m - t * se, m + t * se],
            "p": 1.0 if se == 0 else float(2 * stats.t.sf(abs(m / se), n - 1))}


def _holm(items: list) -> None:
    items = [i for i in items if i["available"]]
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
    if reg_hash(man["registration"]) != man["registration_hash"] or reg_hash(reg) != man["registration_hash"]:
        raise SystemExit("configuration does not match the frozen manifest, not running")
    now = source_hashes()
    rec = man["provenance"]["source_hashes"]
    bad = [p for p in ("simulation", "analysis") if rec[p]["digest"] != now[p]["digest"]]
    sok, swhy = (not bad), ("ok" if not bad else f"{' and '.join(bad)} source differs from the frozen hashes")
    if not sok and not accept_source_drift:
        raise SystemExit(f"source check failed, not running ({swhy}); rerun with --accept-source-drift to record it")
    scn = load_scenario(SCENARIO)
    runs = {lab: [run_mission(scn, seed=s, params=a["params"]) for s in SEEDS] for lab, a in reg["arms"].items()}
    rows, groups = [], {}
    for c in reg["comparisons"]:
        d = _col(runs[c["arm"]], c["metric"]) - _col(runs[c["reference"]], c["metric"])
        row = {**c, **_paired(d)}
        rows.append(row)
        groups.setdefault((c["family"], c["group"], c["metric"]), []).append(row)
    for items in groups.values():
        _holm(items)
    means = {lab: {m: (None if not np.isfinite(_col(r, m)).any() else float(np.nanmean(_col(r, m)))) for m in METRICS}
             for lab, r in runs.items()}
    return {"registration_hash": man["registration_hash"], "manifest_status": man["status"],
            "source_hashes_at_freeze": man["provenance"].get("source_hashes"), "source_hashes_at_run": now,
            "source_check": {"ok": sok, "message": swhy, "drift_accepted": bool(accept_source_drift and not sok)},
            "arm_means": means, "comparisons": rows}


def freeze(status: str, note: str = "") -> None:
    path = Path(MANIFEST)
    if path.exists():
        raise SystemExit(f"{path} exists; a frozen manifest is never overwritten")
    reg = registration()
    man = {"registration_hash": reg_hash(reg), "status": status, "note": note,
           "provenance": {"source_hashes": source_hashes()}, "registration": reg}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"{status} {man['registration_hash']} -> {path}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "freeze":
        return freeze("frozen_before_run", "Frozen before the first run of this tool.")
    out = run("--accept-source-drift" in sys.argv)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(out, indent=2))
    print(f'manifest {out["manifest_status"]} {out["registration_hash"][:12]}; source check {out["source_check"]}')
    for lab, m in out["arm_means"].items():
        print(f"  {lab:24s}", {k: (None if v is None else round(v, 3)) for k, v in m.items() if k in PRIMARY})
    for c in out["comparisons"]:
        if c["metric"] in ("delivered_frac", "c2u_serviced_frac", "operator_goodput") and c["available"]:
            print(f'  {c["family"]} {c["group"]:10s} {c["arm"]:22s} vs ref {c["metric"]:18s} {c["mean"]:+.3f} '
                  f'[{c["ci95"][0]:+.3f},{c["ci95"][1]:+.3f}] holm {c["p_holm"]:.3f}')


if __name__ == "__main__":
    main()
