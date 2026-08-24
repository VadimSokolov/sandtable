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


DIFF_DRAWS = 120
DIFF_SEED = 800_000           # disjoint from both the truth block and the searches


def difficulty(p: Problem, refresh: bool = False) -> dict:
    """How hard is this problem, measured rather than assumed?

    A design-space search problem is hard in proportion to how noisy one mission is against how far
    apart the two best designs are. Both halves are measured here: the per-mission spread of the top
    two designs, and their separation in the high-precision table. The ratio gives the replications
    per design a method needs before the two are even distinguishable, which is the natural unit for
    a budget ladder and the reason this benchmark does not use one budget ladder for every problem.

    The quantity is not a property of the simulator. It is a property of the (design space, MISSION
    METRIC) pair, and on this simulator the metric moves it by three orders of magnitude, which is
    larger than any difference between search methods.
    """
    path = _path(p).with_suffix(".difficulty.json")
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    import numpy as np

    t = truth(p)
    ranked = sorted(t, key=lambda k: t[k], reverse=(p.direction == "max"))
    top2 = [json.loads(k) for k in ranked[:2]]
    gap = abs(t[ranked[0]] - t[ranked[1]])
    scn = load_scenario(p.scenario)
    sds = []
    for j, d in enumerate(top2):
        draws = [evaluate(scn, n_reps=1, seed=DIFF_SEED + 7919 * j + 13 * i,
                          params=p.params(d))[p.metric] for i in range(DIFF_DRAWS)]
        sds.append(float(np.std(draws, ddof=1)))
    sd = float(np.sqrt(np.mean(np.square(sds))))          # pooled
    # Replications per design for the two to sit two standard errors apart. Infinite when the two
    # best designs are tied in the table, which is a real state and is reported as such.
    reps = float("inf") if gap <= 0 else float((2.0 * sd / gap) ** 2)
    out = {"gap": gap, "sd_per_mission": sd, "reps_per_design": reps,
           "best": ranked[0], "runner_up": ranked[1], "n_designs": p.n_designs,
           "budget_to_separate": (reps * p.n_designs if reps != float("inf") else None)}
    path.write_text(json.dumps(out, indent=2))
    return out


def budget_ladder(p: Problem, n: int = 5) -> list[int]:
    """A per-problem ladder spanning well below to well above the budget that can separate the top
    two designs. A single ladder shared across problems would put every method at ceiling on the
    easy ones and at floor on the hard ones, and measure nothing on either."""
    d = difficulty(p)
    b = d["budget_to_separate"]
    if not b or b != b:                                    # None or NaN
        b = 64.0 * p.n_designs
    lo = max(16.0, b / 8.0)
    return sorted({int(round(lo * (4.0 ** (i / max(1, n - 1) * 1.5)))) for i in range(n)})
