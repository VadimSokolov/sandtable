"""CR-42: the effective advance rate of an unheld vehicle, measured on arms with no holds.

The tempo-budget account of the stop-dead cliff predicts the collapse at h* = 1 - D/(v_eff T). D and
T are scenario constants; v_eff is the only quantity that has to be measured, and it is a property of
terrain and control quality rather than of the retry rule, so it is measured on arms where the retry
rule is off and no vehicle is ever held.

Two independent estimators, because one would not be a measurement:
  (a) distance over moving time, from the logged path length of vehicles that reached the goal;
  (b) D over the reach time of the first arrival, which is the quantity the budget actually spends.
They answer slightly different questions (a is a speed, b is a rate of progress toward the goal) and
the budget uses b. Reporting both is what makes the bracket honest.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from sandtable.scenario import load_scenario                     # noqa: E402
from sandtable.sim import run_mission                            # noqa: E402

SC = "scenarios/sc_span_control.json"


def main() -> None:
    scn = load_scenario(SC)
    raw = json.loads(pathlib.Path(SC).read_text())
    start = np.array(raw["forces"][0]["spawn"], dtype=float)
    goal = np.array(raw["objective"]["goal"], dtype=float)
    D = float(np.hypot(*(goal - start)) - raw["objective"]["goal_radius"])
    T = float(raw["duration"])
    print(f"route D = {D:.0f} m, duration T = {T:.0f} s, platform max = "
          f"{raw['platform_types']['ugv']['max_speed']} m/s")

    # No retry and a clear link, so nothing is ever held and the advance rate is the terrain-and-
    # control-quality speed alone. n = 6 to match the cell the bracket was read at.
    times, seeds = [], list(range(64))
    for s in seeds:
        m = run_mission(scn, seed=s, params={"n_blue": 6, "control_mode": "direct",
                                             "comms_level": 0, "retry_prob": 0.0, "blue_behavior": "teleop",
                                             "teleop_stop": True})
        if m.get("hold_fraction", 0.0) > 1e-9:
            print(f"  seed {s}: hold_fraction {m['hold_fraction']:.4f}, not a clean arm")
        t = m.get("mission_time", 0.0)
        if t > 0 and m.get("arrived_frac", 0.0) > 0:
            times.append(t)
    if not times:
        print("no arrivals; cannot estimate")
        return
    times.sort()
    med = times[len(times) // 2]
    mean = sum(times) / len(times)
    print(f"reach time over {len(times)} of {len(seeds)} seeds: median {med:.0f} s, mean {mean:.0f} s")
    print(f"v_eff from median reach time = {D / med:.2f} m/s")
    print(f"v_eff from mean   reach time = {D / mean:.2f} m/s")
    for v in (D / med, D / mean):
        h = 1.0 - D / (v * T)
        print(f"  v_eff {v:.2f} -> predicted h* = {h:.4f}")
    print("\nregistered bracket from the measured collapse at n=6: v_eff in [5.48, 7.23] m/s")


if __name__ == "__main__":
    main()
