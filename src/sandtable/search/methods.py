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
    """Upper confidence bound over designs, spending `chunk` missions per decision."""
    p = _mk_pull(problem, pull)
    designs = problem.designs()
    n = len(designs)
    mean, pulls = np.zeros(n), np.zeros(n)
    spent = 0
    for i in range(n):                                   # one chunk each, to start
        if spent + chunk > budget:
            break
        mean[i] = p(designs[i], chunk)
        pulls[i] = chunk
        spent += chunk
    while spent + chunk <= budget:
        with np.errstate(divide="ignore", invalid="ignore"):
            bonus = c * np.sqrt(2.0 * np.log(max(spent, 2)) / np.maximum(pulls, 1e-9))
        i = int(np.argmax(np.where(pulls > 0, mean + bonus, np.inf)))
        v = p(designs[i], chunk)
        mean[i] = (mean[i] * pulls[i] + v * chunk) / (pulls[i] + chunk)
        pulls[i] += chunk
        spent += chunk
    return designs[int(np.argmax(np.where(pulls > 0, mean, -np.inf)))]


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
    for i in range(n):
        if spent + chunk > budget:
            break
        draws[i].append(p(designs[i], chunk))
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

def gp_ei(problem: Problem, budget: int, rng, pull, chunk: int = 8, warm: int = 4) -> dict:
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
        mu, sd = _gp_posterior(X, np.array(obs_i), np.array(obs_y), cho_factor, cho_solve)
        best = max(obs_y)
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


def _gp_posterior(X, idx, y, cho_factor, cho_solve, ls: float = 0.4, noise: float = 1e-2):
    ym = float(np.mean(y))
    yc = y - ym
    Xo = X[idx]

    def k(A, B):
        d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
        return np.exp(-0.5 * d2 / (ls * ls))

    K = k(Xo, Xo) + noise * np.eye(len(idx))
    cf = cho_factor(K, lower=True)
    alpha = cho_solve(cf, yc)
    Ks = k(X, Xo)
    mu = Ks @ alpha + ym
    vsol = cho_solve(cf, Ks.T)
    var = np.maximum(1.0 - np.einsum("ij,ji->i", Ks, vsol), 1e-12)
    return mu, np.sqrt(var)


METHODS = {
    "grid": grid,
    "random": random_search,
    "halving": successive_halving,
    "ucb": ucb,
    "thompson": thompson,
    "gp_ei": gp_ei,
}
