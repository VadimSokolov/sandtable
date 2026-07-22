"""Bayesian Decision Theory for test and evaluation, applied to mission Monte-Carlo output.

Post-hoc analysis, not a simulation mechanic: everything here consumes the per-replication binary
mission-success outcomes that :func:`sandtable.sim.evaluate` already produces, treating the simulator
as the likelihood. It implements the tractable core of the Bayesian T&E paradigm (maintain a
posterior over a design's mission-success probability instead of a point estimate, and use Bayesian
Decision Theory to make cost-aware accept/reject/continue-testing decisions) in the
conjugate Beta-Bernoulli form. Pure functions on counts and arrays; deterministic given a seed.

The pieces:
  * ``posterior`` / ``credible_interval`` / ``prob_at_least`` -- Beta posterior and the quantities a
    design gate needs (a credible interval and a compliance probability P(p >= threshold)).
  * ``wald_interval`` / ``wilson_interval`` -- frequentist intervals, for contrast.
  * ``decision_chart`` / ``optimal_stop`` -- the Bayesian Decision Theory backward recursion
    (stochastic dynamic programming) over a compliance utility with a per-trial cost, and the
    resulting sequential accept/reject/continue-testing rule.
  * ``contrast`` -- posterior on the success-rate difference between two designs.
  * ``discounted_prior`` / ``expected_runs_to_confidence`` -- use cheap model-and-simulation runs as a
    discounted Bayesian prior that sparse expensive (high-fidelity) runs then update, and count how
    many expensive runs that saves.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

REJECT, ACCEPT, TEST = 0, 1, 2                     # decision-chart action codes


# --------------------------------------------------------------------------- posterior + intervals
def posterior(h: int, n: int, prior: tuple[float, float] = (0.5, 0.5)) -> tuple[float, float]:
    """Beta posterior parameters for h successes in n Bernoulli trials under a Beta prior."""
    a0, b0 = prior
    return a0 + h, b0 + (n - h)


def credible_interval(a: float, b: float, cred: float = 0.95) -> tuple[float, float]:
    """Equal-tailed Beta(a, b) credible interval."""
    lo, hi = stats.beta.ppf([(1 - cred) / 2, 1 - (1 - cred) / 2], a, b)
    return float(lo), float(hi)


def prob_at_least(a: float, b: float, p_cut: float) -> float:
    """P(p >= p_cut | Beta(a, b)); the compliance probability against a threshold requirement."""
    return float(1.0 - stats.beta.cdf(p_cut, a, b))


def wald_interval(h: int, n: int, cred: float = 0.95) -> tuple[float, float]:
    """Frequentist Wald interval; degenerates (zero width, or past [0,1]) at extreme counts."""
    p = h / n
    z = stats.norm.ppf(1 - (1 - cred) / 2)
    se = np.sqrt(p * (1 - p) / n)
    return p - z * se, p + z * se


def wilson_interval(h: int, n: int, cred: float = 0.95) -> tuple[float, float]:
    """Frequentist Wilson score interval; better-behaved than Wald but still not a probability on p."""
    p = h / n
    z = stats.norm.ppf(1 - (1 - cred) / 2)
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return center - half, center + half


# --------------------------------------------------------------------------- decision theory
@dataclass(frozen=True)
class Utility:
    """Compliance utility: accepting is worth ``u_accept`` when the posterior is confident the design
    meets the threshold ``p_cut`` (mass >= ``p_conf`` above it), otherwise it costs ``c_reject``."""
    p_cut: float
    p_conf: float = 0.90
    u_accept: float = 20.0
    c_reject: float = 10.0


def accept_utility(a: float, b: float, util: Utility) -> float:
    return util.u_accept if prob_at_least(a, b, util.p_cut) >= util.p_conf else -util.c_reject


def decision_chart(n_max: int, cost: float, util: Utility,
                   prior: tuple[float, float] = (0.5, 0.5)) -> np.ndarray:
    """Solve the Bayesian Decision Theory recursion; return an action grid ``act[h, m]`` for every
    reachable state (h successes, m failures, h + m <= n_max), each Accept/Reject/Test.

    Backward induction: the value of continuing is the cost-discounted expectation of the next
    knowledge state under the posterior-predictive hit probability a/(a+b); a state acts to whichever
    of accept, reject (value 0), or test is worth most. Invalid cells (h + m > n_max) are -1.
    """
    a0, b0 = prior
    val = np.full((n_max + 1, n_max + 1), np.nan)
    act = np.full((n_max + 1, n_max + 1), -1, dtype=int)
    for tot in range(n_max, -1, -1):
        for h in range(tot + 1):
            m = tot - h
            a, b = a0 + h, b0 + m
            best, who = accept_utility(a, b, util), ACCEPT
            if 0.0 > best:
                best, who = 0.0, REJECT
            if tot < n_max:                                  # continue-testing is available
                p_hit = a / (a + b)
                v_test = -cost + p_hit * val[h + 1, m] + (1 - p_hit) * val[h, m + 1]
                if v_test > best:
                    best, who = v_test, TEST
            val[h, m], act[h, m] = best, who
    return act


def optimal_stop(outcomes, chart: np.ndarray) -> tuple[int, int]:
    """Follow a decision chart on a 0/1 outcome sequence; return (terminal action, trials used)."""
    h = m = 0
    for y in outcomes:
        if chart[h, m] != TEST:
            break
        if y:
            h += 1
        else:
            m += 1
    return int(chart[h, m]), h + m


# --------------------------------------------------------------------------- paired contrast
def contrast(h_a: int, n_a: int, h_b: int, n_b: int, prior: tuple[float, float] = (0.5, 0.5),
             draws: int = 200_000, seed: int = 0) -> dict:
    """Posterior on the success-rate difference delta = p_B - p_A between two designs (independent
    Beta marginals, Monte-Carlo over the difference). Returns mean, 95% CrI, and P(p_B > p_A)."""
    rng = np.random.default_rng(seed)
    aa, ba = posterior(h_a, n_a, prior)
    ab, bb = posterior(h_b, n_b, prior)
    sa = stats.beta.rvs(aa, ba, size=draws, random_state=rng)
    sb = stats.beta.rvs(ab, bb, size=draws, random_state=rng)
    d = sb - sa
    return {"mean": float(d.mean()), "lo": float(np.percentile(d, 2.5)),
            "hi": float(np.percentile(d, 97.5)), "p_b_gt_a": float((d > 0).mean())}


# --------------------------------------------------------------------------- M&S as discounted prior
def discounted_prior(h_sim: int, n_sim: int, lam: float,
                     base: tuple[float, float] = (1.0, 1.0)) -> tuple[float, float]:
    """Turn model-and-simulation counts into a discounted Beta prior for high-fidelity testing.

    The M&S evidence is down-weighted to an effective sample size ``lam * n_sim`` before it becomes a
    prior, so a low-fidelity model informs but does not dominate the expensive test. ``lam = 1``
    trusts M&S fully; ``lam = 0`` recovers the uninformative ``base`` prior.
    """
    ba, bb = base
    return ba + lam * h_sim, bb + lam * (n_sim - h_sim)


def expected_runs_to_confidence(prior: tuple[float, float], p_true: float, util: Utility,
                                k_max: int, trials: int = 2000, seed: int = 0) -> float:
    """Mean number of high-fidelity Bernoulli(``p_true``) runs needed for the posterior (starting from
    ``prior``) to become confident the design complies, i.e. P(p >= p_cut) >= p_conf. Averaged over
    ``trials`` seeded high-fidelity sequences; a sequence that never reaches confidence counts k_max.
    """
    a0, b0 = prior
    if prob_at_least(a0, b0, util.p_cut) >= util.p_conf:
        return 0.0                                        # the prior alone already clears the gate
    rng = np.random.default_rng(seed)
    y = (rng.random((trials, k_max)) < p_true).astype(int)
    hits = np.cumsum(y, axis=1)
    ks = np.full(trials, k_max, dtype=float)
    for t in range(trials):
        for k in range(1, k_max + 1):
            a, b = a0 + hits[t, k - 1], b0 + (k - hits[t, k - 1])
            if prob_at_least(a, b, util.p_cut) >= util.p_conf:
                ks[t] = k
                break
    return float(ks.mean())
