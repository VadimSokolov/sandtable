"""Search methods, all spending the same currency: mission replications.

Every method is a generator-style callable `method(problem, budget, rng, pull) -> design`, where
`pull(design, n_reps) -> float` runs the simulator and is metered. Making replications the budget
rather than "evaluations" is the whole point of the comparison: with a stochastic simulator, a
method's real decision is not only WHICH design to try next but HOW MANY missions to spend
confirming the one it is looking at, and a benchmark that counts evaluations hides that decision.

Sign convention: every method internally maximizes. A minimizing problem is negated at the pull.
"""
from __future__ import annotations

import math

import numpy as np

from .problems import Problem


def _mk_pull(problem: Problem, pull):
    sign = 1.0 if problem.direction == "max" else -1.0
    return lambda d, n: sign * pull(d, n)


# ------------------------------------------------------------------ enumeration baselines

def grid(problem: Problem, budget: int, rng, pull) -> dict:
    """Spend the budget evenly over every design. The method a program office actually uses."""
    p = _mk_pull(problem, pull)
    designs = problem.designs()
    per = max(1, budget // len(designs))
    vals = [p(d, per) for d in designs]
    return designs[int(np.argmax(vals))]


def random_search(problem: Problem, budget: int, rng, pull) -> dict:
    """Uniform designs, one fixed batch each. The baseline that is usually skipped and often wins."""
    p = _mk_pull(problem, pull)
    designs = problem.designs()
    per = max(1, min(32, budget // 8))
    seen: dict[str, list] = {}
    spent = 0
    while spent + per <= budget:
        d = designs[int(rng.integers(len(designs)))]
        k = repr(sorted(d.items()))
        seen.setdefault(k, [d, 0.0, 0])
        v = p(d, per)
        rec = seen[k]
        rec[1] = (rec[1] * rec[2] + v * per) / (rec[2] + per)
        rec[2] += per
        spent += per
    return max(seen.values(), key=lambda r: r[1])[0]


# ------------------------------------------------------------------ bandit allocators

def successive_halving(problem: Problem, budget: int, rng, pull) -> dict:
    """Cut the field in half each round and re-spend the freed budget on the survivors.

    The natural fit for mission design: a small field of designs, a noisy evaluation, and a budget
    fixed in advance. It never estimates a response surface and never needs the design space to have
    a geometry, which is what makes it usable on the categorical axis where a surrogate is weakest.
    """
    p = _mk_pull(problem, pull)
    alive = problem.designs()
    rounds = max(1, int(math.ceil(math.log2(max(2, len(alive))))))
    per_round = budget // rounds
    while len(alive) > 1:
        per = max(1, per_round // len(alive))
        vals = [p(d, per) for d in alive]
        keep = max(1, len(alive) // 2)
        alive = [alive[i] for i in np.argsort(vals)[::-1][:keep]]
    return alive[0]


def ucb(problem: Problem, budget: int, rng, pull, c: float = 1.0, chunk: int = 8) -> dict:
    """Upper confidence bound with the bonus scaled to the metric's own noise.

    Textbook UCB1 adds `c * sqrt(2 log t / n)` and that constant is derived for rewards bounded in
    [0, 1]. Mission metrics are not. Delivered service lives near 0.15 with a per-mission spread of
    0.019 and a between-design gap of 0.006, so the unscaled bonus at eight pulls is 1.02: it
    exceeds the entire gap between the best and second-best design by a factor of 159, and by 31
    and 53 on mission success and loss fraction. An allocator whose bonus dominates its signal
    always picks the least-pulled arm, so unscaled UCB is not exploring too eagerly, it has stopped
    being UCB at all and is uniform allocation with an argmax stapled to the end. It would have
    tied the grid baseline on this benchmark and the tie would have been an artefact of units.

    The bonus is therefore carried in units of the estimate's own standard error, which is the
    same treatment `thompson` already gives its posterior and makes the two comparable. `ucb_raw`
    keeps the textbook constant on purpose, as the control that shows the effect.

    The general point is the one this benchmark exists to make, arriving inside a method rather
    than between two of them: an exploration constant is denominated in the metric's noise, so a
    bandit tuned on one mission metric is mistuned on another by whatever ratio separates their
    spreads, and on this simulator that ratio is large.
    """
    return _ucb(problem, budget, rng, pull, c=c, chunk=chunk, scaled=True)


def ucb_raw(problem: Problem, budget: int, rng, pull, c: float = 1.0, chunk: int = 8) -> dict:
    """UCB1 with the textbook constant and no scaling. The control for `ucb`, not a recommendation."""
    return _ucb(problem, budget, rng, pull, c=c, chunk=chunk, scaled=False)


def _ucb(problem: Problem, budget: int, rng, pull, c: float, chunk: int, scaled: bool,
         pooled: bool = False) -> dict:
    p = _mk_pull(problem, pull)
    designs = problem.designs()
    n = len(designs)
    draws: list[list[float]] = [[] for _ in range(n)]
    spent = 0
    # PERMUTED, not enumeration order. A budget below n * chunk cannot seed every arm, and walking
    # `range(n)` meant the arms that got seeded were always the first ones in the design list. On
    # the capacity problems the registered optimum sits at index 0 or 1 and on `discipline` at index
    # 4, so the low rungs of the ladder would have handed the bandits a free win on one family and a
    # guaranteed zero on the other, purely from the order the designs happen to be enumerated in.
    # `rng` is seeded by replicate, so this stays paired across methods.
    for i in rng.permutation(n):
        if spent + chunk > budget:
            break
        draws[int(i)].append(p(designs[int(i)], chunk))
        spent += chunk
    while spent + chunk <= budget:
        # A per-arm spread taken from two chunk means is itself extremely noisy, and an arm that
        # draws two close chunks early gets a collapsed bonus, stops being pulled, and so never
        # re-estimates the spread that starved it. Pooling across arms removes that trap without
        # assuming the scale. Whether the trap matters is the whole point of carrying both.
        if pooled:
            spreads = [float(np.std(d, ddof=1)) for d in draws if len(d) > 1]
            _pool = float(np.mean(spreads)) if spreads else 0.0
            if _pool <= 1e-12:
                lv = [abs(float(np.mean(d))) for d in draws if d]
                _pool = (float(np.mean(lv)) * 0.5 if lv else 1.0) + 1e-9
        score = []
        for i in range(n):
            if not draws[i]:
                score.append(float("inf"))
                continue
            k = len(draws[i])
            m = float(np.mean(draws[i]))
            # Scale in the metric's own units. Before any spread is observable, fall back to a
            # fraction of the level rather than to 1.0, which would reintroduce the same mismatch.
            if scaled:
                s = _pool if pooled else (
                    float(np.std(draws[i], ddof=1)) if k > 1 else abs(m) * 0.5 + 1e-9)
                score.append(m + c * s * math.sqrt(2.0 * math.log(max(spent, 2)) / k))
            else:
                score.append(m + c * math.sqrt(2.0 * math.log(max(spent, 2)) / k))
        i = int(np.argmax(score))
        draws[i].append(p(designs[i], chunk))
        spent += chunk
    means = [np.mean(d) if d else -np.inf for d in draws]
    return designs[int(np.argmax(means))]


def ucb_pooled(problem: Problem, budget: int, rng, pull, c: float = 1.0, chunk: int = 8) -> dict:
    """Scaled UCB whose noise scale is pooled across arms instead of estimated per arm.

    A discriminator, not an improvement proposal. `ucb` and `ucb_pooled` differ in exactly one
    thing, where the bonus's scale comes from, so if the scaled variant underperforms its unscaled
    control on the noisy axes and `ucb_pooled` does not, the cause is the variance ESTIMATOR
    starving arms rather than anything about adaptive allocation as such. If both underperform
    together, the estimator is exonerated and the regime explanation survives. `ucb` is left exactly
    as registered; this is a third arm.
    """
    return _ucb(problem, budget, rng, pull, c=c, chunk=chunk, scaled=True, pooled=True)


def thompson(problem: Problem, budget: int, rng, pull, chunk: int = 8) -> dict:
    """Thompson sampling with a Gaussian posterior per design.

    The variance is estimated from the design's own draws rather than assumed, because mission
    metrics on this simulator differ in spread by more than an order of magnitude across a design
    space and a shared variance would make the allocator confident about the wrong arms.
    """
    p = _mk_pull(problem, pull)
    designs = problem.designs()
    n = len(designs)
    draws: list[list[float]] = [[] for _ in range(n)]
    spent = 0
    # PERMUTED, not enumeration order. A budget below n * chunk cannot seed every arm, and walking
    # `range(n)` meant the arms that got seeded were always the first ones in the design list. On
    # the capacity problems the registered optimum sits at index 0 or 1 and on `discipline` at index
    # 4, so the low rungs of the ladder would have handed the bandits a free win on one family and a
    # guaranteed zero on the other, purely from the order the designs happen to be enumerated in.
    # `rng` is seeded by replicate, so this stays paired across methods.
    for i in rng.permutation(n):
        if spent + chunk > budget:
            break
        draws[int(i)].append(p(designs[int(i)], chunk))
        spent += chunk
    while spent + chunk <= budget:
        samples = []
        for i in range(n):
            if not draws[i]:
                samples.append(np.inf)
                continue
            m = float(np.mean(draws[i]))
            s = float(np.std(draws[i], ddof=1)) if len(draws[i]) > 1 else abs(m) * 0.5 + 1e-6
            samples.append(rng.normal(m, max(s, 1e-9) / math.sqrt(len(draws[i]))))
        i = int(np.argmax(samples))
        draws[i].append(p(designs[i], chunk))
        spent += chunk
    means = [np.mean(d) if d else -np.inf for d in draws]
    return designs[int(np.argmax(means))]


# ------------------------------------------------------------------ Bayesian surrogate

def gp_ei(problem: Problem, budget: int, rng, pull, chunk: int = 8, warm: int = 4,
          standardize: bool = True, incumbent: str = "observed") -> dict:
    """Gaussian-process surrogate with expected improvement over the discrete design set.

    Deliberately a plain implementation over the enumerated designs rather than a call into a BO
    package. On these spaces the design set is small enough to score exhaustively, so the
    acquisition maximization that a package spends most of its effort on is not the interesting
    part; what is interesting is whether the surrogate's smoothing helps at all when the axis is
    categorical or the response is a cliff. A package would hide that behind its own defaults.
    """
    from scipy.linalg import cho_factor, cho_solve

    p = _mk_pull(problem, pull)
    designs = problem.designs()
    X = _encode(problem, designs)
    n = len(designs)
    obs_i: list[int] = []
    obs_y: list[float] = []
    spent = 0
    order = rng.permutation(n)[:max(2, min(warm, n))]
    for i in order:
        if spent + chunk > budget:
            break
        obs_i.append(int(i))
        obs_y.append(p(designs[int(i)], chunk))
        spent += chunk
    while spent + chunk <= budget:
        mu, sd = _gp_posterior(X, np.array(obs_i), np.array(obs_y), cho_factor,
                               cho_solve, standardize=standardize)
        # The incumbent EI improves on. `observed` is textbook and is wrong under noise: the max
        # of fifty noisy chunk means is biased upward by roughly the chunk's own standard error, so
        # EI is measured against a value no design actually attains and the acquisition flattens
        # toward uniform. `posterior` uses the surrogate's own best mean, which is the usual repair
        # for noisy EI. Both ship, because which one a practitioner reaches for is exactly the kind
        # of default this benchmark exists to price.
        best = max(obs_y) if incumbent == "observed" else float(np.max(mu))
        z = (mu - best) / np.maximum(sd, 1e-9)
        from scipy.stats import norm
        ei = (mu - best) * norm.cdf(z) + sd * norm.pdf(z)
        ei[np.array(obs_i, dtype=int)] *= 0.25       # revisit is allowed, but discounted
        i = int(np.argmax(ei))
        obs_i.append(i)
        obs_y.append(p(designs[i], chunk))
        spent += chunk
    agg: dict[int, list[float]] = {}
    for i, y in zip(obs_i, obs_y):
        agg.setdefault(i, []).append(y)
    best_i = max(agg, key=lambda i: float(np.mean(agg[i])))
    return designs[best_i]


def gp_raw(problem: Problem, budget: int, rng, pull, chunk: int = 8, warm: int = 4) -> dict:
    """Expected improvement with the surrogate left in the metric's raw units. The control for
    `gp_ei`, and the exact analogue of `ucb_raw`: it shows what a scale-bearing hyperparameter
    costs when it is carried in units the data does not have."""
    return gp_ei(problem, budget, rng, pull, chunk=chunk, warm=warm, standardize=False)


def gp_noisy(problem: Problem, budget: int, rng, pull, chunk: int = 8, warm: int = 4) -> dict:
    """Expected improvement against the surrogate's own best posterior mean rather than the best
    number it happened to observe.

    The third arm in the same pattern as `ucb_pooled`: `gp_ei` is left exactly as registered and
    this varies one thing. If the standardized surrogate underperforms its raw control on the noisy
    axes and this does not, the cause is an incumbent inflated by noise rather than anything about
    surrogate search, and the two explanations are otherwise indistinguishable from the results.
    """
    return gp_ei(problem, budget, rng, pull, chunk=chunk, warm=warm, incumbent="posterior")


def _encode(problem: Problem, designs) -> np.ndarray:
    """Ordinal axes scaled to [0,1]; categorical axes one-hot. The standard, and its weakness on a
    categorical axis is exactly what the benchmark is trying to expose rather than to hide."""
    cols = []
    for v in problem.variables:
        vals = [d[v.name] for d in designs]
        if v.kind == "categorical":
            levels = list(v.values)
            cols.extend(np.array([[1.0 if x == lv else 0.0 for x in vals]]).T
                        for lv in levels)
        else:
            arr = np.array(vals, dtype=float)
            lo, hi = arr.min(), arr.max()
            cols.append(((arr - lo) / (hi - lo if hi > lo else 1.0)).reshape(-1, 1))
    return np.hstack(cols)


def _gp_posterior(X, idx, y, cho_factor, cho_solve, ls: float = 0.4, noise: float = 1e-2,
                  standardize: bool = True):
    """Posterior mean and standard deviation over the enumerated design set.

    `standardize` is not a convenience. A unit-amplitude RBF prior asserts that the response varies
    with a standard deviation of one, and a fixed `noise` asserts an observation error in the units
    of `y`. Neither holds for a mission metric. Measured on this simulator: the spread of true
    design values is 0.056 on delivered service, so the prior claims eighteen times more signal
    than exists; and the per-chunk observation noise on mission success is 0.153 against a fixed
    noise term of 0.01, so the surrogate is told the data are fifteen times cleaner than they are
    and interpolates noise as signal. The two errors push the acquisition in opposite directions
    and neither cancels.

    Standardizing `y` puts both hyperparameters in units the data actually has, which is what a
    Bayesian optimization package does in its own defaults. That this implementation is hand-rolled
    is what made the defect visible: a package would have standardized silently and the benchmark
    would have reported a number about the package's defaults while appearing to report one about
    the method. `gp_raw` keeps the unstandardized version as the control.
    """
    ym = float(np.mean(y))
    ys = float(np.std(y, ddof=1)) if (standardize and len(y) > 1) else 1.0
    ys = ys if ys > 1e-12 else 1.0
    yc = (y - ym) / ys
    Xo = X[idx]

    def k(A, B):
        d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
        return np.exp(-0.5 * d2 / (ls * ls))

    K = k(Xo, Xo) + noise * np.eye(len(idx))
    cf = cho_factor(K, lower=True)
    alpha = cho_solve(cf, yc)
    Ks = k(X, Xo)
    mu = (Ks @ alpha) * ys + ym
    vsol = cho_solve(cf, Ks.T)
    var = np.maximum(1.0 - np.einsum("ij,ji->i", Ks, vsol), 1e-12)
    return mu, np.sqrt(var) * ys


METHODS = {
    "ucb_raw": ucb_raw,
    "gp_raw": gp_raw,
    "grid": grid,
    "random": random_search,
    "halving": successive_halving,
    "ucb": ucb,
    "ucb_pooled": ucb_pooled,
    "thompson": thompson,
    "gp_ei": gp_ei,
    "gp_noisy": gp_noisy,
}
