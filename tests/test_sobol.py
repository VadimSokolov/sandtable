"""The Sobol estimator against a function whose indices are known in closed form.

SALib's `analyze` calls `ndarray.ptp()`, which NumPy 2 removed, and the first CR-45 job died on
that line after running 79,872 missions. The estimators are reimplemented in `tools/sobol_nstar.py`
and this is their bench point: an instrument this paper reports a number from owes ground truth,
and the Ishigami function is the standard one for variance decomposition because its first-order
and total indices are analytic.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from sobol_nstar import sobol_indices  # noqa: E402

# Ishigami with a = 7, b = 0.1 over [-pi, pi]^3. Analytic values, Saltelli et al. (2008).
A, B = 7.0, 0.1
S1_TRUE = (0.3139, 0.4424, 0.0)
ST_TRUE = (0.5576, 0.4424, 0.2437)


def _ishigami(x: np.ndarray) -> np.ndarray:
    return np.sin(x[:, 0]) + A * np.sin(x[:, 1]) ** 2 + B * x[:, 2] ** 4 * np.sin(x[:, 0])


def _sample(n: int, d: int, seed: int) -> np.ndarray:
    """The Saltelli layout the estimator expects: per base draw, one A row, d AB rows, one B row."""
    rng = np.random.default_rng(seed)
    a = rng.uniform(-np.pi, np.pi, (n, d))
    b = rng.uniform(-np.pi, np.pi, (n, d))
    rows = []
    for i in range(n):
        rows.append(a[i])
        for j in range(d):
            ab = a[i].copy()
            ab[j] = b[i, j]
            rows.append(ab)
        rows.append(b[i])
    return np.array(rows)


@pytest.fixture(scope="module")
def idx() -> dict:
    x = _sample(8192, 3, seed=17)
    return sobol_indices(_ishigami(x), 3, resamples=60, seed=3)


@pytest.mark.parametrize("j", [0, 1, 2])
def test_first_order_indices_recover_the_analytic_values(idx, j):
    assert abs(idx["S1"][j] - S1_TRUE[j]) < 0.03


@pytest.mark.parametrize("j", [0, 1, 2])
def test_total_indices_recover_the_analytic_values(idx, j):
    assert abs(idx["ST"][j] - ST_TRUE[j]) < 0.03


def test_the_third_variable_has_no_first_order_effect_but_a_real_total_one(idx):
    """The point of the Ishigami bench: x3 enters only through its interaction with x1, so an
    estimator that confused S1 with ST would pass a test on x1 and x2 and fail here."""
    assert idx["S1"][2] < 0.03 < idx["ST"][2]


def test_a_constant_response_returns_zeros_rather_than_dividing_by_zero(idx):
    """The guard SALib was reaching for when it called the removed `ptp`. A degenerate response has
    no variance to decompose, and the honest answer is zero, not a nan that propagates into a
    reported index."""
    out = sobol_indices(np.full(5 * 8, 2.5), 3, resamples=5)
    assert out["S1"] == [0.0, 0.0, 0.0] and out["ST"] == [0.0, 0.0, 0.0]


def test_confidence_intervals_are_positive_and_shrink_with_sample_size():
    x_small, x_big = _sample(512, 3, seed=5), _sample(8192, 3, seed=5)
    small = sobol_indices(_ishigami(x_small), 3, resamples=80, seed=1)
    big = sobol_indices(_ishigami(x_big), 3, resamples=80, seed=1)
    assert all(c > 0 for c in small["S1_conf"])
    assert sum(big["S1_conf"]) < sum(small["S1_conf"])
