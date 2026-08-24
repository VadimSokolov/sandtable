"""Ground truth for the benchmark: every design in a discrete problem, at high precision, cached.

A search method is scored two ways, and both need this table. Whether it returned the design the
independent study named is a yes or no; how much mission performance it gave up by returning
something else is a number, and that number needs the true value of every design rather than the
noisy estimate the method happened to see.

The table is computed once per problem with a seed block DISJOINT from the ones the searches draw
on, so a method cannot be lucky by drawing the same missions the truth was measured on.
"""
from __future__ import annotations

import json
import pathlib

from ..scenario import load_scenario
from ..sim import evaluate
from .problems import Problem

CACHE = pathlib.Path(__file__).resolve().parents[3] / "experiments" / "results" / "search_truth"
TRUTH_REPS = 400
TRUTH_SEED = 900_000          # searches use seeds below 500_000; see `runner.py`


def _path(p: Problem) -> pathlib.Path:
    return CACHE / f"{p.key}.json"


_MEMO: dict[str, dict] = {}


def truth(p: Problem, refresh: bool = False, verbose: bool = False) -> dict:
    """{design-json: value} for every design, at `TRUTH_REPS` replications."""
    if not refresh and p.key in _MEMO:
        return _MEMO[p.key]
    path = _path(p)
    if path.exists() and not refresh:
        _MEMO[p.key] = json.loads(path.read_text())
        return _MEMO[p.key]
    scn = load_scenario(p.scenario)
    out = {}
    for i, d in enumerate(p.designs()):
        m = evaluate(scn, n_reps=TRUTH_REPS, seed=TRUTH_SEED + 1000 * i, params=p.params(d))
        out[json.dumps(d, sort_keys=True)] = float(m[p.metric])
        if verbose:
            print(f"  {json.dumps(d, sort_keys=True):44s} {out[json.dumps(d, sort_keys=True)]:.6f}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True))
    _MEMO[p.key] = out
    return out


def best_design(p: Problem, t: dict | None = None) -> tuple[dict, float]:
    t = t if t is not None else truth(p)
    pick = (max if p.direction == "max" else min)(t, key=lambda k: t[k])
    return json.loads(pick), t[pick]


def regret(p: Problem, design: dict, t: dict | None = None) -> float:
    """How much mission performance the returned design gives up. Always non-negative."""
    t = t if t is not None else truth(p)
    _, best = best_design(p, t)
    got = t[json.dumps(design, sort_keys=True)]
    return (best - got) if p.direction == "max" else (got - best)


def agrees_with_key(p: Problem, t: dict | None = None) -> bool:
    """Does the high-precision table put the optimum where the registered study put it?

    This is the benchmark auditing itself. The answer key came from a battery at a different tier
    with different seeds, so agreement is a real check and disagreement is a finding about the
    battery or about `TRUTH_REPS`, not something to quietly paper over.
    """
    d, _ = best_design(p, t)
    return p.is_optimum(d)
