"""Tests for the Bayesian test-and-evaluation analysis layer (sandtable.bayes_te).

Covers the conjugate posterior and compliance probability, the frequentist-interval degeneracy the
Bayesian form avoids, the decision-theory recursion (terminal actions, and the continue-testing
region shrinking as testing gets dearer), optimal stopping at the extremes, the paired contrast, and
the discounted-prior effective sample size plus the expensive-run saving it buys.
"""
import numpy as np

from sandtable import bayes_te as bt


def test_posterior_symmetric_and_interval_contains_mean():
    a, b = bt.posterior(5, 10, prior=(1.0, 1.0))          # Beta(6, 6), symmetric about 0.5
    assert (a, b) == (6.0, 6.0)
    lo, hi = bt.credible_interval(a, b)
    assert lo < 0.5 < hi
    assert abs((0.5 - lo) - (hi - 0.5)) < 1e-9            # symmetric interval


def test_prob_at_least_monotone_in_threshold():
    a, b = bt.posterior(48, 60)
    vals = [bt.prob_at_least(a, b, c) for c in (0.5, 0.6, 0.7, 0.8, 0.9)]
    assert all(x >= y for x, y in zip(vals, vals[1:]))    # non-increasing in p_cut
    assert 0.0 <= vals[-1] <= vals[0] <= 1.0


def test_wald_degenerates_where_beta_does_not():
    lo, hi = bt.wald_interval(8, 8)                       # all successes -> zero-width Wald
    assert hi - lo < 1e-9
    a, b = bt.posterior(8, 8)
    blo, bhi = bt.credible_interval(a, b)
    assert bhi - blo > 0.1                                # Beta stays honest


def test_decision_chart_terminal_actions():
    util = bt.Utility(p_cut=0.6)
    chart = bt.decision_chart(20, cost=0.05, util=util)   # chart[h, m]: h successes, m failures
    assert chart[0, 20] == bt.REJECT                      # 0/20 successes -> reject
    assert chart[20, 0] == bt.ACCEPT                      # 20/20 successes -> accept
    assert chart[18, 2] == bt.ACCEPT                      # 18/20 -> accept


def test_continue_region_shrinks_with_cost():
    util = bt.Utility(p_cut=0.6)
    cheap = (bt.decision_chart(30, 0.01, util) == bt.TEST).sum()
    dear = (bt.decision_chart(30, 0.40, util) == bt.TEST).sum()
    assert cheap > dear                                   # dearer testing -> stop sooner


def test_optimal_stop_extremes():
    util = bt.Utility(p_cut=0.6)
    chart = bt.decision_chart(40, cost=0.02, util=util)
    dec_hi, _ = bt.optimal_stop([1] * 40, chart)
    dec_lo, _ = bt.optimal_stop([0] * 40, chart)
    assert dec_hi == bt.ACCEPT
    assert dec_lo == bt.REJECT


def test_contrast_separates_clear_designs():
    r = bt.contrast(h_a=12, n_a=200, h_b=69, n_b=200, seed=1)   # B clearly better
    assert r["mean"] > 0
    assert r["p_b_gt_a"] > 0.99


def test_discounted_prior_effective_sample_size():
    a0, b0 = bt.discounted_prior(45, 60, lam=0.75)
    assert abs((a0 + b0) - (2.0 + 0.75 * 60)) < 1e-9      # base (1,1) + lam*n_sim pseudo-counts
    assert bt.discounted_prior(45, 60, lam=0.0) == (1.0, 1.0)  # lam=0 recovers the base prior


def test_ms_informed_prior_saves_expensive_runs():
    util = bt.Utility(p_cut=0.6, p_conf=0.90)
    informed = bt.discounted_prior(45, 60, lam=0.75)      # cheap runs say the design is good
    uninformed = (1.0, 1.0)
    k_informed = bt.expected_runs_to_confidence(informed, p_true=0.80, util=util, k_max=40,
                                                trials=1500, seed=3)
    k_uninformed = bt.expected_runs_to_confidence(uninformed, p_true=0.80, util=util, k_max=40,
                                                  trials=1500, seed=3)
    assert k_informed < k_uninformed                      # the prior buys confidence in fewer runs
