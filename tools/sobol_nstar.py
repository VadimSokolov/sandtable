"""CR-45: the same Sobol design on the simulator and on the closed form, compared index by index.

A global sensitivity analysis usually answers "which knob matters most," which is a description. The
collapse threshold here has a closed form, so a sharper question is available: does the SIMULATOR's
variance decomposition match the EQUATION's, over the identical sample?

That tests something the point check in the validation section cannot. A point check says the
equation lands on the right number at one operating point. This says the equation is right about how
the threshold responds to every parameter at once, which is the claim the paper actually makes when
it calls the equation the mechanism.

Both sides return the same quantity in the same units. The equation returns n*. The simulator returns
the span at which delivered service falls below half its own maximum over the span grid, which is the
empirical version of the same threshold.

Usage:  python3 tools/sobol_nstar.py [--n 128] [--seeds 8] [--out sobol.json]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pathlib
import sys

import numpy as np
from SALib.sample import saltelli

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402

SC = "scenarios/sc_span_control.json"
SPANS = (2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24)
PROBLEM = {
    "num_vars": 4,
    "names": ["service_rate", "patience", "decision_interval", "comms_p_drop"],
    "bounds": [[0.10, 0.22], [12.0, 30.0], [14.0, 30.0], [0.0, 0.25]],
}


def sobol_indices(Y: np.ndarray, d: int, resamples: int = 200,
                  seed: int = 0) -> dict[str, list[float]]:
    """First-order and total Sobol indices from a Saltelli sample, estimated here rather than
    called out to.

    SALib's own `analyze` is unusable on NumPy 2: it calls `ndarray.ptp()`, removed in 2.0, and the
    job that produced this sample died on that line after running 79,872 missions. The estimators
    are four lines each and are worth owning, because an index this paper reports should not depend
    on a third party's guard clause.

    The layout `saltelli.sample(..., calc_second_order=False)` writes is, per base draw, one row of
    A, then `d` rows of AB, then one row of B. Reshaping to (N, d+2) recovers the three matrices.

    S1 is Saltelli et al. (2010): E[B (AB_j - A)] / Var Y. ST is Jansen (1999):
    E[(A - AB_j)^2] / 2 Var Y. Both are benched against the Ishigami function's analytic values in
    tests/test_sobol.py, because an estimator with no bench point is a number with no error bar.
    """
    Y = np.asarray(Y, dtype=float).reshape(-1, d + 2)
    rng = np.random.default_rng(seed)

    def one(rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        a, b = Y[rows, 0], Y[rows, d + 1]
        var = np.var(np.r_[a, b])
        if var <= 0.0:
            return np.zeros(d), np.zeros(d)
        ab = Y[rows, 1:d + 1]
        s1 = np.mean(b[:, None] * (ab - a[:, None]), axis=0) / var
        st = 0.5 * np.mean((a[:, None] - ab) ** 2, axis=0) / var
        return s1, st

    full = np.arange(Y.shape[0])
    s1, st = one(full)
    # The confidence interval is a bootstrap over base draws, which is the resampling unit: a draw's
    # A, AB and B rows share a parameter vector and cannot be resampled apart.
    bs = [one(rng.integers(0, full.size, full.size)) for _ in range(resamples)]
    return {"S1": list(map(float, s1)), "ST": list(map(float, st)),
            "S1_conf": [float(1.96 * v) for v in np.std([b[0] for b in bs], axis=0)],
            "ST_conf": [float(1.96 * v) for v in np.std([b[1] for b in bs], axis=0)]}


def closed_form(x: np.ndarray, consoles: int = 1) -> np.ndarray:
    """Equation (nstar): c (P + tau + 1) mu / (1 - p_drop)^2."""
    mu, P, tau, drop = x[:, 0], x[:, 1], x[:, 2], x[:, 3]
    return consoles * (P + tau + 1.0) * mu / (1.0 - drop) ** 2


def empirical(scn, x: np.ndarray, seeds: int) -> float:
    """The span at which delivered service falls below half its own maximum over the grid.

    Half of the arm's OWN peak, not a fixed level: the peak moves with the service rate, and a
    fixed level would confound the threshold's location with the console's capacity. Linear
    interpolation between the bracketing spans, so the answer is continuous and Sobol sees a
    smooth response rather than a step.
    """
    mu, P, tau, drop = float(x[0]), float(x[1]), float(x[2]), float(x[3])
    served = []
    for n in SPANS:
        tot = 0.0
        for s in range(seeds):
            m = run_mission(scn, seed=s, params={
                "n_blue": n, "control_mode": "direct", "comms_level": 0,
                "service_rate": mu, "patience": int(round(P)),
                "decision_interval": int(round(tau)), "comms_p_drop": drop})
            tot += m["served_per_step"]
        served.append(tot / seeds)
    served = np.asarray(served)
    peak = served.max()
    if peak <= 0:
        return float(SPANS[0])
    half = 0.5 * peak
    k = int(served.argmax())
    for i in range(k, len(SPANS) - 1):
        if served[i] >= half > served[i + 1]:
            f = (served[i] - half) / (served[i] - served[i + 1])
            return float(SPANS[i] + f * (SPANS[i + 1] - SPANS[i]))
    return float(SPANS[-1])          # never falls below half inside the grid


_SCN = None


def _init() -> None:
    global _SCN
    _SCN = load_scenario(SC)


def _one(row: np.ndarray, seeds: int) -> float:
    return empirical(_SCN, row, seeds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=128)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--out", default="sobol.json")
    a = ap.parse_args()

    X = saltelli.sample(PROBLEM, a.n, calc_second_order=False)
    print(f"Saltelli design: {len(X)} parameter draws, {a.seeds} seeds x {len(SPANS)} spans each "
          f"= {len(X) * a.seeds * len(SPANS)} missions", flush=True)

    # One process per core over the draws. Each draw is an independent span sweep with its own
    # seeds, so there is nothing to share and nothing to synchronize; the scenario is loaded once
    # per worker rather than once per draw because parsing it repeatedly dominates otherwise.
    nproc = int(os.environ.get("SLURM_CPUS_PER_TASK", 0)) or mp.cpu_count()
    print(f"running on {nproc} processes", flush=True)
    with mp.Pool(nproc, initializer=_init) as pool:
        Y_sim = np.array(pool.starmap(_one, [(row, a.seeds) for row in X], chunksize=4))
    Y_eq = closed_form(X)

    res = {}
    for tag, Y in (("simulator", Y_sim), ("closed_form", Y_eq)):
        s = sobol_indices(Y, PROBLEM["num_vars"])
        res[tag] = {**s, "mean": float(Y.mean()), "std": float(Y.std()),
                    # The raw responses ride along, 768 floats, so the decomposition can be redone
                    # without re-running 79,872 missions. That is what the first attempt cost.
                    "Y": list(map(float, Y))}
    res["names"] = PROBLEM["names"]
    res["bounds"] = PROBLEM["bounds"]
    res["n_draws"] = len(X)
    res["corr"] = float(np.corrcoef(Y_sim, Y_eq)[0, 1])
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))

    print(f"\n{'parameter':>20} {'S1 sim':>9} {'S1 eq':>9} {'diff':>8}   "
          f"{'ST sim':>9} {'ST eq':>9}")
    for i, nm in enumerate(PROBLEM["names"]):
        d = res["simulator"]["S1"][i] - res["closed_form"]["S1"][i]
        print(f"{nm:>20} {res['simulator']['S1'][i]:9.3f} {res['closed_form']['S1'][i]:9.3f} "
              f"{d:+8.3f}   {res['simulator']['ST'][i]:9.3f} {res['closed_form']['ST'][i]:9.3f}")
    rs = np.argsort(res["simulator"]["S1"])[::-1]
    re_ = np.argsort(res["closed_form"]["S1"])[::-1]
    print(f"\nrank, simulator:   {[PROBLEM['names'][i] for i in rs]}")
    print(f"rank, closed form: {[PROBLEM['names'][i] for i in re_]}")
    print(f"rank order identical: {list(rs) == list(re_)}")
    print(f"largest |S1 difference|: "
          f"{max(abs(res['simulator']['S1'][i] - res['closed_form']['S1'][i]) for i in range(4)):.3f} "
          f"(P1 falsifier fires above 0.10)")
    print(f"correlation of the two responses over the sample: {res['corr']:.3f}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
