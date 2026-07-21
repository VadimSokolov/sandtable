"""Kill-web mechanics studies: suppression, munitions, and the layered UC-7 contested-belief case.

Writes three tidy CSVs of seeded-replication KPI means:

  report/data/suppression_sweep.csv  UC-3, sweep the suppression strength supp_fire (0 = off).
  report/data/munitions_sweep.csv    UC-3, sweep the defenders' basic load ammo_load (inf = off).
  report/data/uc7_layers.csv         UC-7, peel the kill-web on one layer at a time from a truth
                                     baseline (fires vs truth) up to the full contested case.

Each mechanic is opt-in and byte-identical when off, so the supp_fire = 0 row of the suppression
sweep and the ammo_load = 1000 (effectively unlimited) row of the munitions sweep reproduce the
fixed-Pk baseline exactly: the kill-web is a strict superset, the baseline its degenerate limit.
The point, in reply to the kill-web review, is that suppression, munitions, belief, jamming, and
deception each move mission outcomes as first-order effects that emerge from the engagement event
stream, not as probability-of-kill modifier tables. Consumed by tools/make_numbers.py (the
`killweb` block) and tools/make_figures.py (the two sweep figures).

    PYTHONPATH=src python tools/make_killweb_numbers.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

UC3 = "scenarios/uc3_route_defilade.json"
UC7 = "scenarios/uc7_spoofed_advance.json"
NREP = 48
DATA = Path("report/data")


def _means(scn_path: str, params: dict | None, nrep: int = NREP) -> dict:
    """Mean KPIs over `nrep` seeded replications of one scenario/param condition."""
    runs = [run_mission(load_scenario(scn_path), seed=s, params=params) for s in range(nrep)]
    keys = ("blue_losses", "red_losses", "success")
    return {k: float(np.mean([r[k] for r in runs])) for k in keys}


def _write(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} (N={NREP})")


def suppression_sweep() -> None:
    rows = []
    for sf in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        p = {"mech": {"suppression": True, "supp_fire": sf, "supp_gain": 0.25, "supp_decay": 0.85}}
        m = _means(UC3, p)
        rows.append({"supp_fire": sf, "blue_losses": round(m["blue_losses"], 4),
                     "red_losses": round(m["red_losses"], 4),
                     "success": round(m["success"], 4), "n_rep": NREP})
        print(f"  supp_fire={sf:.1f}  blue={m['blue_losses']:.2f}  succ={m['success']:.2f}")
    _write(DATA / "suppression_sweep.csv",
           ["supp_fire", "blue_losses", "red_losses", "success", "n_rep"], rows)


def munitions_sweep() -> None:
    rows = []
    for al in (2, 4, 8, 16, 30, 60, 120, 1000):
        p = {"mech": {"munitions": True, "ammo_load": al}}
        m = _means(UC3, p)
        rows.append({"ammo_load": al, "blue_losses": round(m["blue_losses"], 4),
                     "red_losses": round(m["red_losses"], 4),
                     "success": round(m["success"], 4), "n_rep": NREP})
        print(f"  ammo_load={al:<5d} blue={m['blue_losses']:.2f}  succ={m['success']:.2f}")
    _write(DATA / "munitions_sweep.csv",
           ["ammo_load", "blue_losses", "red_losses", "success", "n_rep"], rows)


# UC-7 layered peel-back: each layer switches on one more kill-web element over a truth baseline.
_BELIEF_OFF = {"model": "off"}
_BELIEF_CLEAR = {"model": "tracks", "decoys": 0, "decoy_rate": 0.6,
                 "max_age": 5, "conf_decay": 0.75, "meas_noise": 30.0}
_BELIEF_DECOY = {**_BELIEF_CLEAR, "decoys": 6}
_MECH_OFF: dict = {}
_MECH_SUPP = {"suppression": True, "supp_fire": 0.8, "supp_gain": 0.25, "supp_decay": 0.85}
_MECH_FULL = {**_MECH_SUPP, "munitions": True, "ammo_load": 120}

# (label, comms_level, belief, mech). Order matters: it is the peel sequence the figure/table shows.
_LAYERS = [
    ("truth", 0, _BELIEF_OFF, _MECH_OFF),      # single seen-bit, fires vs truth (baseline kernel)
    ("belief", 0, _BELIEF_CLEAR, _MECH_OFF),   # persistent tracks, clear comms, fires vs belief
    ("jam", 3, _BELIEF_CLEAR, _MECH_OFF),      # + jamming: tracks go stale and drift
    ("decoys", 3, _BELIEF_DECOY, _MECH_OFF),   # + spoofing: decoy tracks draw wasted fire
    ("suppress", 3, _BELIEF_DECOY, _MECH_SUPP),  # + suppression: incoming fire degrades return fire
    ("full", 3, _BELIEF_DECOY, _MECH_FULL),    # + munitions: finite basic load (full contested case)
]


def uc7_layers() -> None:
    rows = []
    for order, (label, comms, belief, mech) in enumerate(_LAYERS):
        p = {"comms_level": comms, "belief": belief, "mech": mech}
        m = _means(UC7, p)
        rows.append({"layer": label, "order": order,
                     "blue_losses": round(m["blue_losses"], 4),
                     "red_losses": round(m["red_losses"], 4),
                     "success": round(m["success"], 4), "n_rep": NREP})
        print(f"  {label:9s} blue={m['blue_losses']:.2f}  red={m['red_losses']:.2f}  "
              f"succ={m['success']:.2f}")
    _write(DATA / "uc7_layers.csv",
           ["layer", "order", "blue_losses", "red_losses", "success", "n_rep"], rows)


def main() -> None:
    print("=== suppression sweep (UC-3) ===")
    suppression_sweep()
    print("=== munitions sweep (UC-3) ===")
    munitions_sweep()
    print("=== UC-7 contested-belief layers ===")
    uc7_layers()


if __name__ == "__main__":
    main()
