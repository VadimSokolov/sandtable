"""CR-43: the tempo budget tested per run, which is the level it is a statement about.

CR-42 compared the budget against arm means and its falsifier fired. Success is a threshold applied
to one run's arrived fraction, and a threshold does not commute with an average, so the per-arm
comparison asked a different question from the one the budget answers. This collects the pair the
budget is actually about, (hold fraction, arrived fraction) per run, and reports the separation.

v_eff = 5.28 m/s is carried in from tools/measure_veff.py and nothing here is fitted to these runs.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from sandtable.scenario import load_scenario                     # noqa: E402
from sandtable.sim import run_mission                            # noqa: E402

SC = "scenarios/sc_span_control.json"
V_EFF = 6.12                # measured at n=6, rung 0, retry off; see tools/measure_veff.py
SEEDS = 128


def main() -> None:
    scn = load_scenario(SC)
    raw = json.loads(pathlib.Path(SC).read_text())
    start = np.array(raw["forces"][0]["spawn"], dtype=float)
    goal = np.array(raw["objective"]["goal"], dtype=float)
    D = float(np.hypot(*(goal - start)) - raw["objective"]["goal_radius"])
    T = float(raw["duration"])
    h_star = 1.0 - D / (V_EFF * T)
    print(f"D={D:.0f} T={T:.0f} v_eff={V_EFF} -> predicted separating hold h* = {h_star:.4f}\n")

    # n=6 trained v_eff and is held out of the test entirely; 5 and 8 are out of sample.
    for n in (5, 8):
        rows = []
        for rho in (4, 8, 12, 16, 21):
            for s in range(SEEDS):
                m = run_mission(scn, seed=s, params={
                    "n_blue": n, "control_mode": "direct", "comms_level": 3,
                    "channel": "gilbert_elliot", "retry_prob": 1.0, "retry_backoff": rho,
                    "blue_behavior": "teleop", "teleop_stop": True})
                rows.append((m["hold_fraction"], m["arrived_frac"], m["success"]))
        h = np.array([r[0] for r in rows]); a = np.array([r[1] for r in rows])
        # The budget's claim is a separation, so report it as one: arrival rate on each side of the
        # predicted hold, and the empirical hold that separates best, which must NOT be fitted into
        # the prediction and is printed only so the miss is visible.
        lo, hi = h < h_star, h >= h_star
        best, bh = -1.0, None
        for c in np.linspace(h.min(), h.max(), 200):
            l, g = h < c, h >= c
            if l.sum() < 10 or g.sum() < 10:
                continue
            sep = (a[l] > 0.05).mean() - (a[g] > 0.05).mean()
            if sep > best:
                best, bh = sep, c
        print(f"n={n}  runs={len(rows)}  hold range [{h.min():.3f}, {h.max():.3f}]")
        print(f"   below h*={h_star:.4f}: {lo.sum():4d} runs, arrived>0.05 in {(a[lo] > 0.05).mean():.3f}"
              if lo.sum() else f"   below h*: 0 runs")
        print(f"   at/above h*:          {hi.sum():4d} runs, arrived>0.05 in {(a[hi] > 0.05).mean():.3f}"
              if hi.sum() else "   at/above h*: 0 runs")
        if bh is None:
            print("   no empirical separator: the hold range does not straddle any cut")
        else:
            print(f"   best empirical separator (NOT the prediction): h={bh:.4f}, "
                  f"separation {best:.3f}, miss |h-h*| = {abs(bh - h_star):.4f}")


if __name__ == "__main__":
    main()
