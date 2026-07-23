"""Drone-war increment studies: EW-immune command link, counter-UAS/SHORAD, and cost-exchange.

Writes two tidy CSVs of seeded-replication KPI means:

  report/data/drone_fiber_link.csv   Centerpiece span-of-control (direct control), sweep the comms
                                     ladder C0..C5 with the command link jammable vs EW-immune
                                     (fiber / autonomous terminal guidance). Shows the immune link
                                     flattening the jamming collapse of human-in-the-loop control.
  report/data/drone_cuas_swarm.csv   UC-5 sensor swarm, sweep swarm size with counter-UAS/SHORAD off
                                     vs on. Off, success is monotone in size (bigger is always
                                     better); on, a superlinear signature attrites massed swarms and
                                     the response gains an interior optimum. Carries the cost-exchange
                                     KPI on the same rows (cheap attritable drones vs a lost assault).

Every mechanic is opt-in and byte-identical when off: the jammable rows reproduce the pre-increment
command model exactly, and the cuas=off rows reproduce the unopposed swarm exactly. Consumed by
tools/make_numbers.py (the `drone` block) and tools/make_figures.py (the two drone figures).

    PYTHONPATH=src python tools/make_drone_numbers.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SPAN = "scenarios/sc_span_control.json"
UC5 = "scenarios/uc5_sensor_swarm.json"
NREP = 200
DATA = Path("report/data")

# Counter-UAS calibration (see experiments/empirical.md): a superlinear signature so a massed swarm is
# attrited before it can cue the ground force, placing the survivable-swarm optimum at an interior size.
CUAS_ON = {"cuas_rate": 0.00006, "cuas_signature": 2.0}

# Stipulated illustrative relative platform costs for the cost-exchange KPI. A small recon drone is
# cheap and attritable; an assault vehicle is not; a destroyed red anti-tank element is the value won.
COSTS = {"cost_uas": 1.0, "cost_ugv": 20.0, "cost_red": 15.0}


def _means(scn_path: str, params: dict, keys: tuple, nrep: int = NREP) -> dict:
    """Mean KPIs over `nrep` seeded replications of one scenario/param condition."""
    scn = load_scenario(scn_path)
    runs = [run_mission(scn, seed=s, params=params) for s in range(nrep)]
    return {k: float(np.mean([r[k] for r in runs])) for k in keys}


def _write(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} (N={NREP})")


def fiber_link() -> None:
    """M1: direct-control success across the comms ladder, jammable link vs EW-immune link."""
    rows = []
    for comms in range(6):
        for link, immune in (("jammable", False), ("immune", True)):
            p = {"control_mode": "direct", "n_blue": 4, "n_red": 4,
                 "comms_level": comms, "ew_immune_link": immune}
            m = _means(SPAN, p, ("success",))
            rows.append({"comms_level": comms, "link": link,
                         "success": round(m["success"], 4), "n_rep": NREP})
            print(f"  C{comms} {link:8s} success={m['success']:.3f}")
    _write(DATA / "drone_fiber_link.csv", ["comms_level", "link", "success", "n_rep"], rows)


def cuas_swarm() -> None:
    """M2/M3: UC-5 success, coverage, attrition, and cost-exchange vs swarm size, C-UAS off vs on.

    The cost-exchange is the ratio of means (mean red value destroyed / mean blue cost lost), not the
    mean of per-run ratios: the exchange ratio is an aggregate, and the mean-of-ratios is dominated by
    the handful of runs with almost no blue loss in the denominator.
    """
    keys = ("success", "detection_coverage", "blue_air_losses", "blue_ground_losses",
            "blue_cost_lost", "red_losses")
    rows = []
    for n in (1, 2, 3, 4, 5, 6, 8):
        for cuas, extra in (("off", {}), ("on", CUAS_ON)):
            p = {"n_uas": n, **COSTS, **extra}
            m = _means(UC5, p, keys)
            cost_exchange = m["red_losses"] * COSTS["cost_red"] / max(m["blue_cost_lost"], 1e-9)
            rows.append({
                "n_uas": n, "cuas": cuas,
                "success": round(m["success"], 4),
                "coverage": round(m["detection_coverage"], 4),
                "air_losses": round(m["blue_air_losses"], 4),
                "ground_losses": round(m["blue_ground_losses"], 4),
                "blue_cost_lost": round(m["blue_cost_lost"], 4),
                "cost_exchange": round(cost_exchange, 4),
                "red_losses": round(m["red_losses"], 4),
                "n_rep": NREP,
            })
            print(f"  n_uas={n} cuas={cuas:3s} succ={m['success']:.3f} cov={m['detection_coverage']:.3f} "
                  f"air_loss={m['blue_air_losses']:.2f} cost_exch={cost_exchange:.2f}")
    _write(DATA / "drone_cuas_swarm.csv",
           ["n_uas", "cuas", "success", "coverage", "air_losses", "ground_losses",
            "blue_cost_lost", "cost_exchange", "red_losses", "n_rep"], rows)


def main() -> None:
    print("=== M1: EW-immune command link (centerpiece span-of-control) ===")
    fiber_link()
    print("=== M2/M3: counter-UAS swarm sweep + cost-exchange (UC-5) ===")
    cuas_swarm()


if __name__ == "__main__":
    main()
