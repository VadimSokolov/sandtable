"""Extract the UC-3 LHS sweep response surface from the per-sample workspaces.

Usage: analyze_sweep.py [experiments_dir]
  default experiments_dir = ~/sandtable-runs/uc3-sweep/experiments (local run);
  pass /scratch/vsokolov/sandtable-runs/uc3-sweep-hopper/experiments for the Hopper run.
"""
import json, glob, os, sys
import numpy as np

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/sandtable-runs/uc3-sweep/experiments")
rows = []
for inp in glob.glob(os.path.join(root, "**", "inputs.json"), recursive=True):
    out = os.path.join(os.path.dirname(inp), "outputs.json")
    if not os.path.exists(out):
        continue
    p = json.load(open(inp))["params"]
    o = json.load(open(out))
    rows.append((p["route_bias"], p["formation_spread"], p["tempo"],
                 o["success_rate"], o["blue_losses"], o["red_losses"],
                 o["t_obj_success"], o["loss_exchange"]))

rows.sort()
print(f"n_samples = {len(rows)}")
hdr = f"{'bias':>5} {'spread':>7} {'tempo':>6} | {'succ':>5} {'bLoss':>6} {'rLoss':>6} {'tObj|S':>7} {'exch':>5}"
print(hdr)
for r in rows:
    print(f"{r[0]:5.2f} {r[1]:7.1f} {r[2]:6.2f} | {r[3]:5.2f} {r[4]:6.2f} {r[5]:6.2f} {r[6]:7.0f} {r[7]:5.2f}")

a = np.array(rows)
bias = a[:, 0]
print("\n-- Spearman-ish linear corr of KPIs with route_bias (dominant knob) --")
for name, col in [("success", 3), ("blue_losses", 4), ("red_losses", 5), ("t_obj|success", 6)]:
    r = np.corrcoef(bias, a[:, col])[0, 1]
    print(f"corr(route_bias, {name:14s}) = {r:+.3f}")

# Bin by route_bias tercile to show the monotone tradeoff cleanly.
print("\n-- binned by route_bias tercile --")
order = np.argsort(bias)
for lab, idx in [("low  [0.0-0.33]", bias <= 0.33),
                 ("mid  (0.33-0.66]", (bias > 0.33) & (bias <= 0.66)),
                 ("high (0.66-1.0]", bias > 0.66)]:
    sub = a[idx]
    if len(sub) == 0:
        continue
    print(f"{lab}: n={len(sub):2d}  succ={sub[:,3].mean():.2f}  "
          f"bLoss={sub[:,4].mean():.2f}  tObj|S={sub[:,6].mean():.0f}")
