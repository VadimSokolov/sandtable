"""Ground truth for the benchmark: every design in a discrete problem, at high precision, cached.

A search method is scored two ways, and both need this table. Whether it returned the design the
independent study named is a yes or no; how much mission performance it gave up by returning
something else is a number, and that number needs the true value of every design rather than the
noisy estimate the method happened to see.

The table is computed once per problem with a seed block DISJOINT from the ones the searches draw
on, so a method cannot be lucky by drawing the same missions the truth was measured on.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from ..scenario import load_scenario
from ..sim import evaluate, run_mission
from .problems import Problem

CACHE = pathlib.Path(__file__).resolve().parents[3] / "experiments" / "results" / "search_truth"
TRUTH_SEED = 900_000          # searches use seeds below 500_000; see `runner.py`

# One replication count for every metric was the first version of this file and it was wrong in a
# way this project has a name for. `served_per_step` separates its top two designs in tens of
# replications; `blue_loss_frac` needs thousands at the same operating point. A flat 400 therefore
# bought a precise answer key on one axis and a noisy one on another, and the noisy key would then
# have been used to grade search methods on the very axis the paper claims is expensive. The key
# would have been wrong exactly where the paper's own thesis says to look.
#
# These are measured, not assumed: they are three times the separation requirement observed on the
# qcap design set across spans 8 through 16, floored so that no axis is cheaper than the throughput
# axis was under the old constant. `truth()` records the precision it ACHIEVED beside every table,
# so a key that is still too noisy for its own gap announces itself rather than being trusted.
METRIC_REPS = {
    "served_per_step": 600,
    "arrived_frac":    900,
    "mission_time":   1200,
    "success":        2000,
    "blue_loss_frac": 8000,
}
TRUTH_REPS = 600              # fallback for a metric not named above


def truth_reps(p: Problem) -> int:
    return METRIC_REPS.get(p.metric, TRUTH_REPS)


def _path(p: Problem) -> pathlib.Path:
    return CACHE / f"{p.key}.json"


# Per-mission draws, cached by the RUN rather than by the problem. Two metric-paired problems are
# defined as the same missions scored on different axes, so sharing the missions between them is
# not an optimisation, it is the definition: it makes the pairing exact instead of nominal, and it
# removes the possibility that a "paired" comparison silently ran different missions because two
# problems happened to seed differently. It also means the dearest metric's replication count is
# paid once for a design set rather than once per axis.
_DRAWS: dict[str, dict[str, list[float]]] = {}
BENCH_METRICS = ("served_per_step", "success", "blue_loss_frac", "arrived_frac", "mission_time")


def _run_key(p: Problem, design: dict) -> str:
    return json.dumps([p.scenario, p.fixed, design], sort_keys=True)


def _draws(p: Problem, design: dict, reps: int) -> dict[str, list[float]]:
    """`reps` per-mission readings of every benchmark metric, under common random numbers.

    Every design draws the SAME mission seeds, so design-to-design comparison is paired and the
    variance that matters is the variance of the difference. The first version advanced the seed
    per design, which threw that pairing away on exactly the axis this benchmark is about.
    """
    key = _run_key(p, design)
    have = _DRAWS.get(key)
    if have is not None and len(next(iter(have.values()))) >= reps:
        return have
    disk = _pool_load(key)
    if disk is not None and len(next(iter(disk.values()))) >= reps:
        _DRAWS[key] = disk
        return disk
    scn = load_scenario(p.scenario)
    runs = [run_mission(scn, seed=TRUTH_SEED + r, params=p.params(design)) for r in range(reps)]
    got = {m: [float(r[m]) for r in runs] for m in BENCH_METRICS if m in runs[0]}
    _DRAWS[key] = got
    _pool_save(key, got)
    return got


def draw_range(p: Problem, design: dict, lo: int, hi: int) -> dict[str, list[float]]:
    """Missions `lo` through `hi` of a design's pool, as raw per-metric readings.

    The unit of parallelism when a pool is built. Mission `r` is seeded `TRUTH_SEED + r` and depends
    on nothing else, so any contiguous slice can be computed independently and the pieces
    concatenated: the pool a set of chunks assembles into is identical, mission for mission, to the
    one a single sequential loop would have produced. That matters because a cell is eight thousand
    missions on the dearest axis, and running a cell as one task made the critical path forty-seven
    minutes regardless of how many cores were thrown at it.
    """
    scn = load_scenario(p.scenario)
    runs = [run_mission(scn, seed=TRUTH_SEED + r, params=p.params(design)) for r in range(lo, hi)]
    return {m: [float(r[m]) for r in runs] for m in BENCH_METRICS if m in runs[0]}


def pool_store(p: Problem, design: dict, got: dict[str, list[float]]) -> None:
    """Persist an assembled pool and put it in the run cache."""
    key = _run_key(p, design)
    _DRAWS[key] = got
    _pool_save(key, got)


def pool_for(p: Problem, design: dict) -> dict[str, list[float]]:
    """The stored per-mission pool for one design, or a refusal.

    Deliberately not a cache miss that falls back to simulating. A benchmark run that quietly
    generated a one-mission pool where a eight-thousand-mission one was expected would produce a
    complete-looking results file whose noise model is wrong by four orders of magnitude, and
    nothing downstream would show it.
    """
    key = _run_key(p, design)
    got = _DRAWS.get(key) or _pool_load(key)
    if got is None:
        raise SystemExit(
            f"no mission pool for {p.key} at {design}: run 'search_bench.py truth' first "
            f"(expected {_pool_path(key)})")
    _DRAWS[key] = got
    return got


def pool_depth(p: Problem, design: dict | None = None) -> int:
    """How many real missions stand behind one design here. The ceiling on any honest budget."""
    d = design if design is not None else p.designs()[0]
    try:
        return len(next(iter(pool_for(p, d).values())))
    except SystemExit:
        return truth_reps(p)


def _pool_path(key: str) -> pathlib.Path:
    d = pathlib.Path("experiments/results/search_pools")
    return d / (hashlib.sha1(key.encode()).hexdigest()[:16] + ".npz")


def _pool_load(key: str) -> dict[str, list[float]] | None:
    """The per-mission readings behind a truth table entry, if they were kept.

    Kept on purpose. The design means alone let a benchmark be scored but not re-run, and every
    question about how a search method behaves under this simulator's noise needs the noise itself,
    not a summary of it. With the pools on disk the head-to-head resamples real missions instead of
    simulating new ones, which is what makes a thousand replicates affordable at all.
    """
    path = _pool_path(key)
    if not path.exists():
        return None
    try:
        import numpy as np
        with np.load(path) as z:
            return {m: z[m].tolist() for m in z.files}
    except (OSError, ValueError, KeyError):
        return None                       # a pool truncated by a preemption is a cache miss


def _pool_save(key: str, got: dict[str, list[float]]) -> None:
    import numpy as np
    path = _pool_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    # Written through an open handle rather than by name: savez appends ".npz" to any path that
    # does not already end in it, which would have renamed the temp file out from under the
    # replace below and left every pool unwritten.
    with tmp.open("wb") as fh:
        np.savez_compressed(fh, **{m: np.asarray(v, dtype=np.float64) for m, v in got.items()})
    tmp.replace(path)                     # atomic, so a kill mid-write cannot leave a half pool


_MEMO: dict[str, dict] = {}


def truth(p: Problem, refresh: bool = False, verbose: bool = False) -> dict:
    """{design-json: value} for every design, at `TRUTH_REPS` replications."""
    if not refresh and p.key in _MEMO:
        return _MEMO[p.key]
    path = _path(p)
    if path.exists() and not refresh:
        raw = json.loads(path.read_text())
        meta = raw.pop("_meta", None)
        # A table written before common random numbers and per-metric replications is not the same
        # object as one written after, and reusing it would put an unpaired key under a paper that
        # is about pairing. Refuse it rather than refresh it silently.
        if not meta or not meta.get("_crn"):
            raise SystemExit(f"{path} predates the CRN truth tables; delete it and re-run `truth`")
        _MEMO[p.key] = raw
        return raw
    import numpy as np

    reps = truth_reps(p)
    out, se = {}, {}
    for d in p.designs():
        vals = _draws(p, d, reps)[p.metric][:reps]
        k = json.dumps(d, sort_keys=True)
        out[k] = float(np.mean(vals))
        se[k] = float(np.std(vals, ddof=1) / np.sqrt(reps))
        if verbose:
            print(f"  {k:44s} {out[k]:.6f}  se {se[k]:.6f}")

    # Does the key resolve its own top two? A table whose leading gap is inside its own noise
    # cannot grade anything, and it says so here rather than being discovered downstream.
    ranked = sorted(out, key=lambda z: out[z], reverse=(p.direction == "max"))
    gap = abs(out[ranked[0]] - out[ranked[1]]) if len(ranked) > 1 else 0.0
    pooled = float(np.hypot(se[ranked[0]], se[ranked[1]])) if len(ranked) > 1 else 0.0
    meta = {"_reps": reps, "_metric": p.metric, "_gap": gap, "_se_top2": pooled,
            "_resolved": bool(gap > 2.0 * pooled and gap > 0.0),
            "_se": se, "_crn": True}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**out, "_meta": meta}, indent=2, sort_keys=True))
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


def spread(p: Problem, t: dict | None = None) -> float:
    """Best design to worst, in metric units. The size of the prize on this design axis."""
    t = t if t is not None else truth(p)
    vals = list(t.values())
    return abs(max(vals) - min(vals))


def regret_frac(p: Problem, design: dict, t: dict | None = None) -> float:
    """Regret as a fraction of the achievable spread: 0.0 for the best design, 1.0 for the worst.

    The raw regret above is in metric units and cannot be averaged across problems whose metrics are
    delivered service, mission success and blue loss. This one can, which is what makes it the
    grading rule rather than a second opinion. It also grades problems whose top two the answer key
    cannot separate: distinguishing the found design from the best is a far coarser question than
    distinguishing the best from the runner-up, and on this benchmark it is about eighty times
    cheaper.
    """
    t = t if t is not None else truth(p)
    s = spread(p, t)
    return 0.0 if s <= 0 else regret(p, design, t) / s


def agrees_with_key(p: Problem, t: dict | None = None) -> bool:
    """Does the high-precision table put the optimum where the registered study put it?

    This is the benchmark auditing itself. The answer key came from a battery at a different tier
    with different seeds, so agreement is a real check and disagreement is a finding about the
    battery or about `TRUTH_REPS`, not something to quietly paper over.
    """
    if not p.optimum:
        return True          # nothing registered to disagree with; the table IS the key
    d, _ = best_design(p, t)
    return p.is_optimum(d)


CAP_MULT = 2048        # missions per design at the top of any ladder
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
        cached = json.loads(path.read_text())
        if "budget_to_choose" in cached:
            return cached                     # a cache written before regret grading lacks it
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
    # The separation question and the choosing question are different, and on this benchmark they
    # differ by about two orders of magnitude. Both are recorded so the ladder can span them.
    sprd = abs(max(t.values()) - min(t.values()))
    reps_choose = float("inf") if sprd <= 0 else float((2.0 * sd / sprd) ** 2)
    out = {"gap": gap, "sd_per_mission": sd, "reps_per_design": reps,
           "spread": sprd, "reps_to_choose": reps_choose,
           "spread_over_gap": (sprd / gap if gap > 0 else float("inf")),
           "best": ranked[0], "runner_up": ranked[1], "n_designs": p.n_designs,
           "budget_to_choose": (reps_choose * p.n_designs if reps_choose != float("inf") else None),
           "budget_to_separate": (reps * p.n_designs if reps != float("inf") else None)}
    path.write_text(json.dumps(out, indent=2))
    return out


def budget_ladder(p: Problem, n: int = 5) -> list[int]:
    """A per-problem ladder spanning well below to well above the budget that can separate the top
    two designs. A single ladder shared across problems would put every method at ceiling on the
    easy ones and at floor on the hard ones, and measure nothing on either."""
    d = difficulty(p)
    # The ladder is sized to the CHOOSING question, not the separating one. Chasing separation put
    # the top rung at fourteen thousand missions on problems whose top two designs the answer key
    # itself cannot tell apart at eight thousand replications each, which is a ladder built to
    # measure something this benchmark argues nobody needs. Four times the budget that distinguishes
    # the best design from the worst puts the top rung where regret is near zero and the comparison
    # saturates, which is what the top of a ladder is for.
    lo_b = d.get("budget_to_choose") or 16.0 * p.n_designs
    hi_b = 4.0 * lo_b
    # Two hard ceilings. CAP_MULT bounds cost. The pool depth bounds honesty: a budget deeper than
    # the stored missions would be served by resampling the same missions repeatedly, and a method
    # would converge to the POOL's mean rather than the simulator's while appearing to gain
    # precision. Where either binds it is recorded rather than absorbed.
    ceiling = min(CAP_MULT, pool_depth(p)) * p.n_designs
    hi = max(min(hi_b, ceiling), 64.0)
    lo = max(16.0, min(lo_b / 4.0, hi / 16.0))
    return sorted({int(round(lo * (hi / lo) ** (i / max(1, n - 1)))) for i in range(n)})
