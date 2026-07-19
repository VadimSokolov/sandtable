"""Simulation loop: determinism per seed, variation across seeds, evaluate aggregation."""
from __future__ import annotations

import numpy as np

from sandtable.sim import evaluate, run_mission


def test_run_mission_is_deterministic(skirmish_scenario):
    a = run_mission(skirmish_scenario, seed=3)
    b = run_mission(skirmish_scenario, seed=3)
    assert a == b   # same (scenario, seed) -> identical KPI dict


def test_run_mission_is_a_pure_function_of_seed(skirmish_scenario):
    # a caller reusing the scenario object between runs must not perturb results
    first = run_mission(skirmish_scenario, seed=11)
    _ = run_mission(skirmish_scenario, seed=99)
    assert run_mission(skirmish_scenario, seed=11) == first


def test_different_seeds_can_differ(skirmish_scenario):
    signatures = {
        (
            run_mission(skirmish_scenario, seed=s)["blue_losses"],
            run_mission(skirmish_scenario, seed=s)["time_to_objective"],
        )
        for s in range(10)
    }
    assert len(signatures) > 1   # stochastic engagement makes outcomes vary by seed


def test_evaluate_adds_summary_keys(skirmish_scenario):
    n_reps = 5
    agg = evaluate(skirmish_scenario, n_reps=n_reps, seed=0)
    assert agg["n_reps"] == n_reps
    assert "success_rate" in agg
    assert agg["success_rate"] == agg["success"]   # success_rate mirrors the mean success indicator
    # every KPI is a scalar float mean
    for k, v in agg.items():
        assert isinstance(v, (int, float))


def test_evaluate_averages_per_run_kpis(skirmish_scenario):
    n_reps, seed = 6, 2
    agg = evaluate(skirmish_scenario, n_reps=n_reps, seed=seed)
    # evaluate draws seeds seed*n_reps + i; reproduce the mean of one KPI independently
    manual = np.mean(
        [run_mission(skirmish_scenario, seed=seed * n_reps + i)["blue_losses"] for i in range(n_reps)]
    )
    assert np.isclose(agg["blue_losses"], manual)
