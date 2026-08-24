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


def test_an_undefined_ratio_is_nan_and_not_a_number_that_looks_like_a_measurement():
    """Instrument defect 15's genus, in a metric rather than in a reference arm.

    When the impatient half of the fleet receives nothing at all the ratio is undefined. It used to
    return the fleet size, which averages, gates and reads as a very large but finite stratification.
    Two cells of a landed battery sat on it in seventeen of thirty-two blocks. It is now NaN, which
    cannot be silently scored, and the count is exposed separately so nothing is lost.
    """
    import math

    from sandtable.metrics import _stratified_by_deadline

    pat = np.array([5, 5, 5, 5, 40, 40, 40, 40], dtype=float)
    ans = np.array([0, 0, 0, 0, 9, 9, 9, 9])          # the impatient half got nothing
    d = _stratified_by_deadline(ans, pat, total_steps=100)
    assert math.isnan(d["answer_step_ratio"])
    assert d["answer_step_censored"] == 1.0
    assert d["answer_step_impatient"] == 0.0
    assert d["answer_step_patient"] > 0.0


def test_a_defined_ratio_is_unchanged_and_flagged_uncensored():
    from sandtable.metrics import _stratified_by_deadline

    pat = np.array([5, 5, 5, 5, 40, 40, 40, 40], dtype=float)
    ans = np.array([2, 2, 2, 2, 8, 8, 8, 8])
    d = _stratified_by_deadline(ans, pat, total_steps=100)
    assert abs(d["answer_step_ratio"] - 4.0) < 1e-12
    assert d["answer_step_censored"] == 0.0


def test_the_share_reads_perfect_fairness_when_both_halves_are_equally_excluded():
    """Instrument defect 16, pinned at the moment it was found rather than after it shipped.

    `answer_step_share` is a ratio of two rates, so it reads 1.0 when both halves of the fleet get
    almost nothing. That is equal exclusion, not proportionate service. Measured: on a console with
    no admission rule, deadline order scores a perfect 1.0000 while starving 95 percent of the
    fleet. The metric is only interpretable next to a level.
    """
    from sandtable.metrics import _stratified_by_deadline

    pat = np.array([5, 5, 5, 5, 40, 40, 40, 40], dtype=float)
    ruinous = _stratified_by_deadline(np.array([1, 1, 1, 1, 1, 1, 1, 1]), pat, total_steps=1000)
    healthy = _stratified_by_deadline(np.array([90, 90, 90, 90, 90, 90, 90, 90]), pat, 1000)
    assert ruinous["answer_step_share"] == healthy["answer_step_share"] == 1.0
    # And what tells them apart: the level, which is why the share never ships alone.
    assert ruinous["answer_step_impatient"] < healthy["answer_step_impatient"] / 50.0


def test_the_share_and_the_ratio_agree_wherever_the_ratio_is_defined():
    from sandtable.metrics import _stratified_by_deadline

    pat = np.array([5, 5, 5, 5, 40, 40, 40, 40], dtype=float)
    for ans in ([2, 2, 2, 2, 8, 8, 8, 8], [1, 1, 1, 1, 9, 9, 9, 9], [5, 5, 5, 5, 5, 5, 5, 5]):
        d = _stratified_by_deadline(np.array(ans), pat, total_steps=100)
        assert abs(d["answer_step_share"] * d["answer_step_ratio"] - 1.0) < 1e-12
