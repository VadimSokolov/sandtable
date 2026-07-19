"""Morris elementary-effects analysis of the UC-3 mission cost.

Reconstructs the SALib sample matrix from the per-sample workspaces (in sim-id
order == SALib trajectory order) and runs morris.analyze to rank the three
mission-design knobs by influence (mu*) and interaction/nonlinearity (sigma).
"""
import json, os
import numpy as np
from SALib.analyze import morris as morris_analyze

root = os.path.expanduser("~/sandtable-runs/uc3-morris/experiments")
names = ["route_bias", "formation_spread", "tempo"]
bounds = [[0.0, 1.0], [20.0, 120.0], [0.5, 1.0]]

# mission_score weights (must match studies/uc3_morris.yaml metric options)
W_FAIL, W_TIME, W_LOSS, T_SCALE = 1.0, 0.3, 0.5, 1800.0

def mission_score(o):
    sr = float(o.get("success_rate", o.get("success", 0.0)))
    return (W_FAIL * (1.0 - sr)
            + W_TIME * float(o["time_to_objective"]) / T_SCALE
            + W_LOSS * float(o["blue_loss_frac"]))

X, Y = [], []
for d in sorted(os.listdir(root)):                       # sim-000001, sim-000002, ...
    folder = os.path.join(root, d)
    p = json.load(open(os.path.join(folder, "inputs.json")))["params"]
    o = json.load(open(os.path.join(folder, "outputs.json")))
    X.append([p[n] for n in names])
    Y.append(mission_score(o))

X = np.asarray(X, float)
Y = np.asarray(Y, float)
problem = {"num_vars": 3, "names": names, "bounds": bounds}

res = morris_analyze.analyze(problem, X, Y, num_levels=4, print_to_console=False)
print(f"Morris screening on mission_score  (n={len(Y)} evals, 10 trajectories)\n")
print(f"{'param':>16} {'mu*':>8} {'mu*_conf':>9} {'sigma':>8}")
order = np.argsort(res["mu_star"])[::-1]
for i in order:
    print(f"{res['names'][i]:>16} {res['mu_star'][i]:8.4f} {res['mu_star_conf'][i]:9.4f} {res['sigma'][i]:8.4f}")
