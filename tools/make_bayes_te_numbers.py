"""Bayesian test-and-evaluation demonstration on SandTable's mission Monte-Carlo output.

Runs the span-control (centerpiece) scenario as a fair fight (n_red = n_blue, matching
studies/centerpiece_*_hopper.yaml), harvests the per-replication binary mission-success draws, and
runs the sandtable.bayes_te analysis to produce:
  A. credible intervals vs frequentist intervals for a headline design      -> bayes_te_intervals.csv
  B. a Bayesian Decision Theory decision chart + optimal stopping            -> bayes_te_stopping.csv,
                                                                                bayes_te_paths.csv
  C. a Bayesian paired contrast of two designs (direct vs supervisory)       -> bayes_te_contrast.csv
  D. SandTable as a discounted Bayesian prior updated by sparse high-fidelity
     runs (M&S-informed operational testing), and the expensive runs it saves -> bayes_te_prior.csv,
                                                                                 bayes_te_prior_curve.csv

Consumed by tools/make_numbers.py (the `bayes_te` block) and tools/make_figures.py (fig_bayes_te).

    PYTHONPATH=src python tools/make_bayes_te_numbers.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sandtable import bayes_te as bt
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SC = load_scenario("scenarios/sc_span_control.json")
DATA = Path("report/data"); DATA.mkdir(parents=True, exist_ok=True)
NREP = 300                       # replications per design (matches the centerpiece study)
GATE = bt.Utility(p_cut=0.60)    # compliance requirement: mission success at least 60%
CRED = 0.95
LAM = 0.10                       # M&S discount: weight the low-fidelity model at ~10% of its nominal
LAM_HALF = 0.05                  # sample (Ferry discounts higher-fidelity developmental data by 0.75)

_cache: dict[tuple, np.ndarray] = {}


def draws(mode: str, comms: int, n: int, reps: int = NREP) -> np.ndarray:
    """Binary mission-success draws, fair fight (n_red = n_blue), seeds 0..reps-1."""
    key = (mode, comms, n, reps)
    if key not in _cache:
        p = {"control_mode": mode, "comms_level": comms, "n_blue": n, "n_red": n}
        _cache[key] = np.array([run_mission(SC, seed=s, params=p)["success"] for s in range(reps)], float)
    return _cache[key]


def _write(name: str, fields: list[str], rows: list[dict]) -> None:
    with (DATA / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {DATA / name} ({len(rows)} rows)")


# --------------------------------------------------------------------------- A. intervals
def demo_A() -> None:
    d = draws("direct", 0, 2)                          # fair fight 2v2, ~0.8, near a 0.8 gate
    rows = []
    for label, sub in (("full", d), ("small", d[:8])):
        h, n = int(sub.sum()), len(sub)
        a, b = bt.posterior(h, n)
        blo, bhi = bt.credible_interval(a, b, CRED)
        wlo, whi = bt.wald_interval(h, n, CRED)
        slo, shi = bt.wilson_interval(h, n, CRED)
        rows.append({"label": label, "h": h, "n": n,
                     "beta_lo": round(blo, 4), "beta_hi": round(bhi, 4),
                     "wald_lo": round(wlo, 4), "wald_hi": round(whi, 4),
                     "wilson_lo": round(slo, 4), "wilson_hi": round(shi, 4),
                     "p_ge_80": round(bt.prob_at_least(a, b, 0.80), 4),
                     "p_ge_60": round(bt.prob_at_least(a, b, 0.60), 4)})
    _write("bayes_te_intervals.csv",
           ["label", "h", "n", "beta_lo", "beta_hi", "wald_lo", "wald_hi",
            "wilson_lo", "wilson_hi", "p_ge_80", "p_ge_60"], rows)


# --------------------------------------------------------------------------- B. decision chart + stop
DESIGNS_B = [("compliant", "direct", 0, 2), ("borderline", "direct", 0, 4),
             ("noncompliant", "direct", 4, 8)]
N_MAX = 60
COSTS = [0.02, 0.20]


def demo_B() -> None:
    rows, paths = [], []
    charts = {c: bt.decision_chart(N_MAX, c, GATE) for c in COSTS}
    for name, mode, comms, n in DESIGNS_B:
        seq = draws(mode, comms, n)[:N_MAX]
        rate = float(seq.mean())
        h = m = 0                                       # record the cumulative walk for the figure
        for k, y in enumerate(seq):
            paths.append({"design": name, "k": k, "hits": h, "misses": m})
            if y:
                h += 1
            else:
                m += 1
        for c in COSTS:
            dec, used = bt.optimal_stop(seq, charts[c])
            rows.append({"design": name, "true_rate": round(rate, 4), "cost": c,
                         "decision": {bt.ACCEPT: "accept", bt.REJECT: "reject", bt.TEST: "none"}[dec],
                         "n_used": used,
                         "continue_states": int((charts[c] == bt.TEST).sum())})
    _write("bayes_te_stopping.csv",
           ["design", "true_rate", "cost", "decision", "n_used", "continue_states"], rows)
    _write("bayes_te_paths.csv", ["design", "k", "hits", "misses"], paths)


# --------------------------------------------------------------------------- C. paired contrast
def demo_C() -> None:
    a = draws("direct", 4, 8)                            # crossover cell, span 1:8
    b = draws("supervisory", 4, 8)
    b_ind = np.array([run_mission(SC, seed=5000 + s,
                                  params={"control_mode": "supervisory", "comms_level": 4,
                                          "n_blue": 8, "n_red": 8})["success"]
                      for s in range(NREP)], float)
    ha, hb, n = int(a.sum()), int(b.sum()), NREP
    r = bt.contrast(ha, n, hb, n, seed=0)
    corr = float(np.corrcoef(a, b)[0, 1])
    var_crn = float((b - a).var(ddof=1) / n)
    var_ind = float((b_ind.var(ddof=1) + a.var(ddof=1)) / n)
    _write("bayes_te_contrast.csv",
           ["h_a", "n_a", "h_b", "n_b", "delta_mean", "delta_lo", "delta_hi", "p_b_gt_a",
            "crn_corr", "var_crn", "var_ind"],
           [{"h_a": ha, "n_a": n, "h_b": hb, "n_b": n,
             "delta_mean": round(r["mean"], 4), "delta_lo": round(r["lo"], 4),
             "delta_hi": round(r["hi"], 4), "p_b_gt_a": round(r["p_b_gt_a"], 4),
             "crn_corr": round(corr, 4), "var_crn": var_crn, "var_ind": var_ind}])


# --------------------------------------------------------------------------- D. M&S as discounted prior
def _mean_ci_width(prior, p_true, k, trials, seed):
    """Mean 95% credible-interval width after k high-fidelity Bernoulli(p_true) runs from `prior`."""
    a0, b0 = prior
    rng = np.random.default_rng(seed)
    hits = (rng.random((trials, k)) < p_true).sum(axis=1) if k > 0 else np.zeros(trials, int)
    widths = [bt.credible_interval(a0 + hh, b0 + (k - hh), CRED) for hh in hits]
    return float(np.mean([hi - lo for lo, hi in widths]))


def demo_D() -> None:
    # Cheap M&S evidence: the compliant design, which the low-fidelity model rates well above the
    # gate. We discount that evidence heavily (lambda = 0.10) before it becomes a prior for the
    # expensive high-fidelity test, then confirm against an emulated high-fidelity truth.
    sim = draws("direct", 0, 2)
    h_sim, n_sim = int(sim.sum()), NREP
    informed = bt.discounted_prior(h_sim, n_sim, LAM)          # discounted Beta prior from M&S
    uninformed = (1.0, 1.0)
    p_true = 0.78                                             # emulated high-fidelity truth (aligned, above gate)
    k_max = 30
    runs_inf = bt.expected_runs_to_confidence(informed, p_true, GATE, k_max, trials=4000, seed=7)
    runs_unf = bt.expected_runs_to_confidence(uninformed, p_true, GATE, k_max, trials=4000, seed=7)

    # Robustness / prior-data conflict: high-fidelity says the design is actually bad (below the
    # gate), against the optimistic M&S prior. How many high-fidelity runs to overturn the prior to a
    # confident reject (P(p >= gate) < 1 - p_conf), and how the discount lambda governs that speed:
    # a lighter discount (smaller lambda) trusts M&S less, so a wrong prior is overturned sooner.
    conflict_p = 0.40

    def runs_to_reject(lam, k_max_c=120, trials=4000, seed=11):
        a0, b0 = bt.discounted_prior(h_sim, n_sim, lam)
        rng = np.random.default_rng(seed)
        y = (rng.random((trials, k_max_c)) < conflict_p).astype(int)
        hits = np.cumsum(y, axis=1)
        ks = np.full(trials, k_max_c, float)
        for t in range(trials):
            for k in range(1, k_max_c + 1):
                if bt.prob_at_least(a0 + hits[t, k - 1], b0 + (k - hits[t, k - 1]), GATE.p_cut) < 1 - GATE.p_conf:
                    ks[t] = k
                    break
        return float(ks.mean())

    _write("bayes_te_prior.csv",
           ["lam", "lam_half", "h_sim", "n_sim", "p_true", "gate", "runs_informed", "runs_uninformed",
            "runs_saved", "conflict_p", "override_main", "override_half"],
           [{"lam": LAM, "lam_half": LAM_HALF, "h_sim": h_sim, "n_sim": n_sim, "p_true": p_true,
             "gate": GATE.p_cut, "runs_informed": round(runs_inf, 2),
             "runs_uninformed": round(runs_unf, 2), "runs_saved": round(runs_unf - runs_inf, 2),
             "conflict_p": conflict_p, "override_main": round(runs_to_reject(LAM), 2),
             "override_half": round(runs_to_reject(LAM_HALF), 2)}])

    # Curve for the figure: mean CrI width vs number of high-fidelity runs, informed vs uninformed.
    rows = []
    for k in range(0, k_max + 1):
        rows.append({"k": k,
                     "width_informed": round(_mean_ci_width(informed, p_true, k, 2000, 21), 4),
                     "width_uninformed": round(_mean_ci_width(uninformed, p_true, k, 2000, 21), 4)})
    _write("bayes_te_prior_curve.csv", ["k", "width_informed", "width_uninformed"], rows)


def main() -> None:
    print("Bayesian T&E study (fair fight, N=%d reps/design):" % NREP)
    demo_A()
    demo_B()
    demo_C()
    demo_D()
    print("done.")


if __name__ == "__main__":
    main()
