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

import hashlib
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
    regret_frac: float          # the same, as a fraction of the achievable spread, so it averages
    gradeable: bool             # can the answer key separate its own top two? argmax only
    spent: int                  # replications actually consumed
    distinct: int               # designs the method looked at
    reused: int = 0             # times a design's mission pool wrapped; 0 means no reuse at all


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


class PoolMeter(Meter):
    """A meter that draws missions from the stored per-mission pools instead of simulating them.

    Two things this buys, and only the second is about speed.

    It makes common random numbers EXACT across methods. Replicate r fixes one index stream per
    design; whichever method asks for the first eight missions of a design gets the same eight
    missions, in the same order, as every other method on that replicate. The fresh-mission meter
    could only pair methods by seeding them alike and hoping they consumed the stream the same way,
    which they do not, because how a method spends its budget is the thing being measured.

    And it makes the head-to-head cost nothing once the pools exist, so the replicate count is set
    by how much precision the comparison needs rather than by how much simulator time is left. The
    pools are real missions, eight thousand per design on the dearest axis, so what is resampled is
    the simulator's own mission distribution and not a fitted stand-in for it. The one thing this
    does not reproduce is a mission the pool never contained; with the pool exhausted by a single
    pull the sampling is with replacement, and the reuse that implies is reported rather than hidden.
    """

    def __init__(self, problem: Problem, budget: int, base_seed: int, replicate: int):
        self.p, self.budget, self.base = problem, budget, base_seed
        self.spent = 0
        self.calls = 0
        self.seen: set[str] = set()
        self.reused = 0                  # total wraps, reported; not used for seeding
        self._wraps: dict[str, int] = {}  # per DESIGN, and this one seeds the reshuffle
        self.replicate = replicate
        self._pos: dict[str, int] = {}
        self._order: dict[str, np.ndarray] = {}
        self._pool: dict[str, np.ndarray] = {}

    def _seed(self, key: str, wrap: int = 0) -> int:
        """A design's mission order depends on the replicate and the design, and on nothing else.

        Drawing every design's permutation from one shared generator made a design's stream depend
        on how many OTHER designs a method had touched first, so two methods that visited the design
        space in different orders got different missions for the same design on the same replicate.
        That is precisely the pairing this meter exists to guarantee, inverted.
        """
        h = hashlib.sha1(f"{self.replicate}|{key}|{wrap}".encode()).digest()
        return int.from_bytes(h[:8], "big")

    def _stream(self, key: str, design: dict) -> np.ndarray:
        if key not in self._pool:
            got = oracle.pool_for(self.p, design)           # refuses rather than simulating one
            self._pool[key] = np.asarray(got[self.p.metric], dtype=np.float64)
            rng = np.random.default_rng(self._seed(key))
            self._order[key] = rng.permutation(len(self._pool[key]))
            self._pos[key] = 0
        return self._pool[key]

    def pull(self, design: dict, n_reps: int) -> float:
        n = int(n_reps)
        if n <= 0:
            raise ValueError("a pull must run at least one mission")
        if self.spent + n > self.budget:
            raise BudgetExhausted(self.spent, self.budget, n)
        key = json.dumps(design, sort_keys=True)
        pool = self._stream(key, design)
        idx, pos, N = self._order[key], self._pos[key], len(pool)
        # An empty pool makes the loop below spin forever: `pos >= N` is always true, the
        # reshuffle yields an empty permutation, `want` is zero, `got` never advances, and `take`
        # grows without bound. It has never fired, because every stored pool holds at least six
        # hundred missions, but the failure mode is a silent hang rather than an error and it
        # would be indistinguishable from a slow run. Refuse instead.
        if N == 0:
            raise SystemExit(f"pool for {key} is empty; rebuild it before running the sweep")
        take, got = [], 0                                   # `got` counts MISSIONS, not chunks
        while got < n:
            if pos >= N:                                    # pool exhausted; reshuffle and reuse
                # Seeded on THIS design's wrap count, not on the meter's total. A shared counter
                # made the reshuffled ordering depend on how many other designs had wrapped first,
                # so two methods that exhausted different designs in different orders diverged after
                # their first wrap: the same pairing failure this meter was built to remove, moved
                # one level down and only reachable on a rung deep enough to spend a pool.
                self.reused += 1
                w = self._wraps[key] = self._wraps.get(key, 0) + 1
                idx = np.random.default_rng(self._seed(key, w)).permutation(N)
                self._order[key], pos = idx, 0
            want = min(n - got, N - pos)
            take.append(idx[pos:pos + want])
            pos += want
            got += want
        self._pos[key] = pos
        picked = np.concatenate(take)
        assert len(picked) == n, (len(picked), n)
        self.spent += n
        self.calls += 1
        self.seen.add(key)
        return float(np.mean(pool[picked]))


class BudgetExhausted(RuntimeError):
    def __init__(self, spent, budget, wanted):
        super().__init__(f"budget {budget} exhausted: spent {spent}, wanted {wanted} more")


def run_one(problem_key: str, method: str, budget: int, replicate: int,
            truth: dict | None = None, backend: str = "sim") -> Result:
    p = get(problem_key)
    t = truth if truth is not None else oracle.truth(p)
    # Paired on the replicate, so every method on replicate r sees the same mission randomness.
    base = 1000 * replicate
    rng = np.random.default_rng(replicate)
    meter = (PoolMeter(p, budget, base, replicate) if backend == "pool"
             else Meter(p, budget, base))
    try:
        design = METHODS[method](p, budget, rng, meter.pull)
    except BudgetExhausted:
        # A method that tries to overspend is not disqualified; it is recorded as having failed to
        # return inside its budget, which is a real property of a method and not a bug in the test.
        design = json.loads(sorted(meter.seen)[0]) if meter.seen else p.designs()[0]
    return Result(problem=problem_key, method=method, replicate=replicate, budget=budget,
                  design=json.dumps(design, sort_keys=True),
                  found=_found(p, design, t), regret=oracle.regret(p, design, t),
                  regret_frac=oracle.regret_frac(p, design, t),
                  gradeable=_gradeable(p),
                  spent=meter.spent, distinct=len(meter.seen),
                  reused=getattr(meter, "reused", 0))


def _gradeable(p: Problem) -> bool:
    """Whether this problem's `found` column means anything.

    A problem whose answer key cannot separate its own top two has no argmax to recover, so `found`
    there is a coin flip dressed as a score. It is still graded on regret, which asks the much
    coarser question of how far the returned design sits from the best one. Recording the flag per
    row rather than filtering the problem out keeps both gradings available from one sweep.
    """
    if p.optimum:
        return True
    try:
        meta = json.loads(oracle._path(p).read_text()).get("_meta", {})
    except (OSError, json.JSONDecodeError):
        return True
    return bool(meta.get("_resolved", True))


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
