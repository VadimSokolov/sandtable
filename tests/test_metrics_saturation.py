"""Instrument defect 13: `starved_frac` is saturated at the operating points we run.

It counts vehicles that asked and received exactly zero answers over the whole run. In the
`capped` battery (job 9449936) it was 0.000000 in every arm, at every span, in all 32 blocks,
because over a run of this length no vehicle is ever excluded outright. A metric pinned to its
floor by the run length cannot audit a policy, and a null read from it is not evidence of
fairness. These tests pin the failure and pin the replacements that do vary.
"""
import numpy as np

from sandtable.metrics import _distribution_of_answers


def test_starved_frac_reports_no_harm_where_the_distribution_is_ruinous():
    # Sixteen vehicles. One is answered once in a hundred asks, the rest are answered every time.
    # No vehicle is excluded, so the saturated metric says nobody is harmed.
    ask = np.full(16, 100)
    ans = np.full(16, 100)
    ans[0] = 1
    d = _distribution_of_answers(ans, ask)
    assert d["starved_frac"] == 0.0
    assert d["answer_rate_min"] == 0.01
    assert d["answer_rate_gap"] > 0.9


def test_the_replacements_separate_two_fleets_the_saturated_metric_calls_equal():
    ask = np.full(8, 50)
    even = np.full(8, 25)                       # everyone answered half the time
    skewed = np.array([2, 2, 2, 2, 48, 48, 48, 48])  # same total, split in two
    a, b = _distribution_of_answers(even, ask), _distribution_of_answers(skewed, ask)
    assert a["starved_frac"] == b["starved_frac"] == 0.0
    assert abs(a["answer_rate_v"] - b["answer_rate_v"]) < 1e-12
    assert b["answer_rate_min"] < a["answer_rate_min"]
    assert b["answer_rate_gap"] > a["answer_rate_gap"]


def test_starved_frac_is_the_right_metric_only_when_exclusion_actually_happens():
    ask = np.full(4, 10)
    ans = np.array([0, 0, 10, 10])
    d = _distribution_of_answers(ans, ask)
    assert d["starved_frac"] == 0.5
    assert d["answer_rate_min"] == 0.0


def test_the_quartiles_read_stratification_the_min_reads_luck():
    # A fleet the console serves in a smooth gradient, and one where fifteen do fine and one is
    # unlucky. The min calls them the same; the quartile spread does not.
    ask = np.full(16, 100)
    graded = np.linspace(5, 95, 16).astype(int)
    one_bad = np.full(16, 50)
    one_bad[0] = 5
    g, b = _distribution_of_answers(graded, ask), _distribution_of_answers(one_bad, ask)
    assert abs(g["answer_rate_min"] - b["answer_rate_min"]) < 0.01
    assert g["answer_rate_iqr"] > 0.4
    assert b["answer_rate_iqr"] == 0.0


def test_two_point_fleet_holds_the_mean_and_the_extremes_and_raises_the_variance():
    # The shape control for the dispersion cost. If a result holds under both layouts it is a
    # statement about the second moment; if it holds only under one it is about the shape.
    import numpy as _np
    from sandtable.c2 import _patience_vector
    blue = _np.arange(16)
    rng = _np.random.default_rng(0)
    uni = _patience_vector(16, blue, 20, 12, rng, "uniform")[:16]
    two = _patience_vector(16, blue, 20, 12, _np.random.default_rng(0), "twopoint")[:16]
    assert uni.mean() == two.mean() == 20.0
    assert uni.min() == two.min() and uni.max() == two.max()
    assert two.var() > 2.5 * uni.var()


def test_the_per_step_split_needs_a_dispersed_fleet_and_says_so():
    from sandtable.metrics import _stratified_by_deadline
    assert _stratified_by_deadline(np.array([5, 5]), np.array([20, 20]), 100) == {}
    d = _stratified_by_deadline(np.array([1, 9]), np.array([8, 32]), 100)
    assert d["answer_step_ratio"] == 9.0
