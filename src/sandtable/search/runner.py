"""The comparison protocol: same problem, same budget, same seeds, one design out.

Two design decisions carry most of the honesty here.

The budget is counted in MISSION REPLICATIONS, not in evaluations. With a stochastic simulator a
method's real choice includes how many missions to spend confirming a design, and a benchmark that
counts evaluations lets a method buy precision for free.

Methods are paired on SEEDS by replicate. Replicate r gives every method the same stream of mission
randomness, so a difference between two methods on one replicate is a difference in what they chose
to spend it on rather than in what they happened to draw. This is the same common-random-numbers
discipline the simulator's own gate uses.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict

import numpy as np

from ..scenario import load_scenario
from ..sim import evaluate
from . import oracle
from .methods import METHODS
from .problems import Problem, get


@dataclass
class Result:
    problem: str
    method: str
    replicate: int
    budget: int
    design: str
    found: bool                 # matches the independently registered optimum
    regret: float               # mission performance given up, from the high-precision table
    spent: int                  # replications actually consumed
    distinct: int               # designs the method looked at


class Meter:
    """Counts replications and refuses to let a method overspend its budget."""

    def __init__(self, problem: Problem, budget: int, base_seed: int):
        self.p, self.budget, self.base = problem, budget, base_seed
        self.scn = load_scenario(problem.scenario)
        self.spent = 0
        self.calls = 0
        self.seen: set[str] = set()

    def pull(self, design: dict, n_reps: int) -> float:
        n = int(n_reps)
        if n <= 0:
            raise ValueError("a pull must run at least one mission")
        if self.spent + n > self.budget:
            raise BudgetExhausted(self.spent, self.budget, n)
        # A fresh seed block per call, so two pulls of the same design are two independent
        # estimates rather than the same number twice.
        seed = self.base + 977 * self.calls
        m = evaluate(self.scn, n_reps=n, seed=seed, params=self.p.params(design))
        self.spent += n
        self.calls += 1
        self.seen.add(json.dumps(design, sort_keys=True))
        return float(m[self.p.metric])


class BudgetExhausted(RuntimeError):
    def __init__(self, spent, budget, wanted):
        super().__init__(f"budget {budget} exhausted: spent {spent}, wanted {wanted} more")


def run_one(problem_key: str, method: str, budget: int, replicate: int,
            truth: dict | None = None) -> Result:
    p = get(problem_key)
    t = truth if truth is not None else oracle.truth(p)
    # Paired on the replicate, so every method on replicate r sees the same mission randomness.
    base = 1000 * replicate
    rng = np.random.default_rng(replicate)
    meter = Meter(p, budget, base)
    try:
        design = METHODS[method](p, budget, rng, meter.pull)
    except BudgetExhausted:
        # A method that tries to overspend is not disqualified; it is recorded as having failed to
        # return inside its budget, which is a real property of a method and not a bug in the test.
        design = json.loads(sorted(meter.seen)[0]) if meter.seen else p.designs()[0]
    return Result(problem=problem_key, method=method, replicate=replicate, budget=budget,
                  design=json.dumps(design, sort_keys=True),
                  found=_found(p, design, t), regret=oracle.regret(p, design, t),
                  spent=meter.spent, distinct=len(meter.seen))


def _found(p, design, t) -> bool:
    """Did the method return the best design?

    For a problem carrying a registered key that is a comparison against the key. For one whose key
    is established by the high-precision table it is a comparison against the table's argmax, and
    `is_optimum` refuses rather than passing vacuously, so the two cases have to be separated here.
    A design inside the problem's tolerance of the best VALUE also counts, because two designs that
    the table cannot tell apart are not a search failure.
    """
    if p.optimum:
        return p.is_optimum(design)
    best_d, best_v = oracle.best_design(p, t)
    if json.dumps(design, sort_keys=True) == json.dumps(best_d, sort_keys=True):
        return True
    return oracle.regret(p, design, t) <= p.tolerance


def run_sweep(problem_key: str, methods, budgets, replicates: int, verbose: bool = True):
    p = get(problem_key)
    t = oracle.truth(p, verbose=verbose)
    if not oracle.agrees_with_key(p, t):
        d, _ = oracle.best_design(p, t)
        print(f"  !! {problem_key}: the high-precision table puts the optimum at {d}, the "
              f"registered study at {p.optimum}. Reported, not reconciled.")
    out = []
    for b in budgets:
        for m in methods:
            for r in range(replicates):
                out.append(run_one(problem_key, m, b, r, t))
    return out


def to_rows(results) -> list[dict]:
    return [asdict(r) for r in results]
