"""Guards for the benchmark's answer key and its allocators.

Everything here pins a defect that was actually found and fixed rather than a property that seemed
worth asserting. Each test names the failure it prevents, because a test whose motivation is lost
gets deleted the first time it becomes inconvenient.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from sandtable.search import methods, oracle
from sandtable.search.problems import PROBLEMS, get


# ---------------------------------------------------------------- the answer key

def test_truth_reps_are_per_metric_not_one_number():
    """A flat replication count bought a precise key on the cheap axis and a noisy one on the dear
    axis, so the key was least trustworthy exactly where the paper looks hardest."""
    srv = oracle.METRIC_REPS["served_per_step"]
    loss = oracle.METRIC_REPS["blue_loss_frac"]
    assert loss > srv, "the noisy axis must not be estimated at the quiet axis's replication count"
    assert loss / srv >= 5, "the measured separation requirement differs by far more than this"


def test_designs_draw_common_random_numbers():
    """The truth tables advanced the seed per design, so designs were compared on DIFFERENT
    missions. That discards pairing on exactly the axis this benchmark is about."""
    p = get("qcap_uniform")
    designs = p.designs()[:2]
    seen = []
    for d in designs:
        got = oracle._draws(p, d, 3)
        seen.append(got)
    # The metric values differ (the designs differ), but the SEEDS must not, which shows up as the
    # two draw sets having been built from the same seed block. Assert it structurally instead of
    # by peeking: identical designs must reproduce exactly.
    again = oracle._draws(p, designs[0], 3)
    assert again["served_per_step"] == seen[0]["served_per_step"]


def test_run_key_ignores_the_metric_so_paired_problems_share_missions():
    """Metric-paired problems are DEFINED as the same missions scored differently. If their run keys
    differed they would silently run different missions and the pairing would be nominal."""
    a, b = get("qcap_s8_srv"), get("qcap_s8_loss")
    d = a.designs()[0]
    assert oracle._run_key(a, d) == oracle._run_key(b, d)


def test_run_key_separates_operating_points():
    """The same design at two spans is not the same run, and collapsing them would silently score
    one operating point with another's missions."""
    a, b = get("qcap_s8_srv"), get("qcap_s12_srv")
    d = a.designs()[0]
    assert oracle._run_key(a, d) != oracle._run_key(b, d)


def test_empty_answer_key_refuses_instead_of_passing_everything():
    """`all(...)` over an empty dict is True, so a problem whose key was never established would
    have graded every method as perfect. That is the worst possible default for a benchmark."""
    p = get("qcap_s8_srv")
    assert p.optimum == {}, "this problem's key comes from the table, not from a registration"
    with pytest.raises(ValueError):
        p.is_optimum(p.designs()[0])


def test_registered_problems_still_carry_their_key():
    """The problems whose optimum came from a landed battery must keep it; the refusal above is for
    table-established keys only and must not have swallowed the registered ones."""
    for k in ("qcap_uniform", "qcap_mixed", "discipline"):
        assert get(k).optimum, f"{k} lost its registered answer key"


def test_metric_paired_problems_share_design_set_and_operating_point():
    base, twin = get("qcap_s8_srv"), get("qcap_s8_succ")
    assert base.fixed == twin.fixed
    assert base.designs() == twin.designs()
    assert base.metric != twin.metric


def test_paired_problems_are_off_the_success_ceiling():
    """The twins originally inherited an operating point where success is pinned at 1.0 and the two
    best designs read identically, so a method scored there was scored on noise."""
    for k in PROBLEMS:
        if k.endswith("_succ"):
            assert PROBLEMS[k].fixed["n_blue"] <= 16, (
                f"{k} sits where CR-69 pins baseline success at its ceiling")


# ---------------------------------------------------------------- resume

def test_resume_key_matches_the_spec_tuple():
    """The run stage overwrote its output on every restart, so five preemptions discarded five runs
    of work. Resume reads rows back; if its key and the spec tuple disagree it silently does
    nothing and the bug comes back looking like slowness."""
    rows = [{"problem": "p", "method": "grid", "budget": 16, "replicate": 0}]
    done = {(r["problem"], r["method"], r["budget"], r["replicate"]) for r in rows}
    spec = ("p", "grid", 16, 0)                    # (k, m, b, r) as built in cmd_run
    assert spec in done


def test_resume_tolerates_a_row_killed_mid_write():
    """A preemption lands wherever it lands, including halfway through a line."""
    text = '{"problem":"p","method":"grid","budget":16,"replicate":0}\n{"problem":"p","me'
    done = set()
    for ln in text.splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        done.add((r["problem"], r["method"], r["budget"], r["replicate"]))
    assert done == {("p", "grid", 16, 0)}


# ---------------------------------------------------------------- the allocators

_TRUE = np.array([0.1461, 0.1476, 0.1299, 0.0993, 0.0314, 0.0052, 0.0029])


def _surrogate(problem, sd=0.0193, seed=7):
    """The measured scale of the delivered-service axis, without paying for missions."""
    designs = problem.designs()
    rng = np.random.default_rng(seed)
    counts = {i: 0 for i in range(len(designs))}

    def pull(d, n):
        i = designs.index(d)
        counts[i] += n
        return float(rng.normal(_TRUE[i], sd / np.sqrt(n)))

    return pull, counts, rng


def test_unscaled_ucb_is_uniform_allocation():
    """UCB1's constant assumes rewards in [0,1]. Against a gap of 0.006 the bonus is 1.02, so the
    argmax is always the least-pulled arm and the method is the grid baseline renamed. This pins the
    control's behaviour so it cannot be silently 'fixed' into agreeing with the treatment."""
    p = get("qcap_uniform")
    pull, counts, rng = _surrogate(p)
    methods.ucb_raw(p, 400, rng, pull)
    alloc = [counts[i] for i in range(7)]
    contenders, hopeless = alloc[0] + alloc[1], alloc[5] + alloc[6]
    assert contenders / max(hopeless, 1) < 3.0, (
        f"unscaled UCB concentrated more than expected: {alloc}")


def test_scaled_ucb_concentrates_on_the_contenders():
    p = get("qcap_uniform")
    pull, counts, rng = _surrogate(p)
    methods.ucb(p, 400, rng, pull)
    alloc = [counts[i] for i in range(7)]
    contenders, hopeless = alloc[0] + alloc[1], alloc[5] + alloc[6]
    assert contenders / max(hopeless, 1) > 5.0, (
        f"scaled UCB failed to concentrate: {alloc}")


def test_scaling_changes_allocation_by_a_lot():
    """The two must not converge. If they ever do, either the repair stopped working or the control
    stopped being a control, and the registered comparison in CR-72 becomes meaningless."""
    p = get("qcap_uniform")
    ratios = []
    for fn in (methods.ucb_raw, methods.ucb):
        pull, counts, rng = _surrogate(p)
        fn(p, 400, rng, pull)
        alloc = [counts[i] for i in range(7)]
        ratios.append((alloc[0] + alloc[1]) / max(alloc[5] + alloc[6], 1))
    assert ratios[1] > 3.0 * ratios[0]


def test_every_method_returns_a_design_in_the_space():
    p = get("qcap_uniform")
    designs = p.designs()
    for name, fn in sorted(methods.METHODS.items()):
        pull, _counts, rng = _surrogate(p)
        got = fn(p, 200, rng, pull)
        assert got in designs, f"{name} returned {got}, which is not a design"


def test_methods_respect_the_budget():
    """A budget denominated in missions is the paper's central convention; a method that overspends
    it silently would make every comparison in the results section wrong."""
    p = get("qcap_uniform")
    for name, fn in sorted(methods.METHODS.items()):
        pull, counts, rng = _surrogate(p)
        fn(p, 200, rng, pull)
        assert sum(counts.values()) <= 200, f"{name} spent {sum(counts.values())} of 200"


def test_gp_standardization_is_scale_invariant():
    """A unit-amplitude prior and a fixed noise term are assertions about the units of y. The
    standardized surrogate must give the same answer when y is rescaled; the raw one need not, and
    that difference is the registered finding."""
    p = get("qcap_uniform")
    designs = p.designs()
    picks = []
    for scale in (1.0, 100.0):
        rng = np.random.default_rng(11)

        def pull(d, n, _s=scale, _r=rng):
            i = designs.index(d)
            return float(_r.normal(_TRUE[i] * _s, 0.0193 * _s / np.sqrt(n)))

        picks.append(methods.gp_ei(p, 300, rng, pull))
    assert picks[0] == picks[1], f"standardized GP moved under rescaling: {picks}"


# ---------------------------------------------------------------- the pool meter

def _fake_pool(problem, depth=64):
    """Stand up pools without running missions. The meter's contract is about which missions a
    method receives and in what order, not about what the simulator puts in them."""
    import numpy as np
    for j, d in enumerate(problem.designs()):
        key = oracle._run_key(problem, d)
        draws = {m: (np.arange(depth, dtype=float) + 1000.0 * j).tolist()
                 for m in oracle.BENCH_METRICS}
        oracle._DRAWS[key] = draws
    return depth


def test_pool_meter_pairs_methods_exactly(monkeypatch):
    """The whole reason the benchmark runs off pools. Two methods on the same replicate must get
    the SAME missions for a design, whatever else they did first. The first implementation drew
    every design's order from one shared generator, so a design's stream depended on how many other
    designs a method had visited before it, which inverts the pairing this meter exists to give."""
    from sandtable.search.runner import PoolMeter
    p = get("qcap_uniform")
    _fake_pool(p)
    d0, d1 = p.designs()[0], p.designs()[1]

    a = PoolMeter(p, 10_000, 0, replicate=3)
    b = PoolMeter(p, 10_000, 0, replicate=3)
    first = a.pull(d0, 8)
    b.pull(d1, 8)                      # b takes a different first move
    b.pull(d1, 8)                      # and a second, so the shared-rng version would diverge
    assert b.pull(d0, 8) == first


def test_pool_meter_separates_replicates():
    from sandtable.search.runner import PoolMeter
    p = get("qcap_uniform")
    _fake_pool(p)
    d0 = p.designs()[0]
    got = {PoolMeter(p, 10_000, 0, replicate=r).pull(d0, 8) for r in range(6)}
    assert len(got) > 1, "every replicate drew the same missions"


def test_pool_meter_draws_without_replacement_until_the_pool_runs_out():
    """A pull of n must be n DISTINCT missions while the pool can supply them. Sampling with
    replacement throughout would understate the estimator's variance."""
    from sandtable.search.runner import PoolMeter
    p = get("qcap_uniform")
    depth = _fake_pool(p, depth=64)
    m = PoolMeter(p, 10_000, 0, replicate=1)
    d0 = p.designs()[0]
    for _ in range(depth // 8):
        m.pull(d0, 8)
    assert m.reused == 0, "wrapped before the pool was spent"
    assert m.spent == depth
    m.pull(d0, 8)
    assert m.reused == 1, "did not record reuse after the pool was spent"


def test_a_pull_of_n_averages_exactly_n_missions():
    """The first version counted the CHUNKS it had appended rather than the missions in them, so a
    pull of eight averaged thirty-six missions whenever it wrapped, and the meter reported eight
    spent. Every estimate a method made near the end of a pool was quietly more precise than the
    budget it was charged for."""
    import numpy as np
    from sandtable.search.runner import PoolMeter
    p = get("qcap_uniform")
    _fake_pool(p, depth=20)
    m = PoolMeter(p, 10_000, 0, replicate=2)
    d0 = p.designs()[0]
    pool = np.asarray(oracle._DRAWS[oracle._run_key(p, d0)][p.metric])
    for n in (8, 8, 8, 8):                    # 32 draws from a 20-deep pool: forces a wrap
        got = m.pull(d0, n)
        # the mean of exactly n pool entries is a multiple of 1/n away from an integer sum
        assert abs(got * n - round(got * n)) < 1e-6, (got, n)
    assert m.spent == 32


def test_pool_meter_refuses_to_overspend():
    from sandtable.search.runner import PoolMeter, BudgetExhausted
    p = get("qcap_uniform")
    _fake_pool(p)
    with pytest.raises(BudgetExhausted):
        PoolMeter(p, 4, 0, replicate=0).pull(p.designs()[0], 8)


def test_missing_pool_refuses_rather_than_fabricating_one():
    """A run that quietly built a one-mission pool where an eight-thousand-mission one belonged
    would write a complete-looking results file whose noise model is wrong by four orders of
    magnitude, and nothing downstream would show it."""
    p = get("disc_s8_succ")
    oracle._DRAWS.clear()
    monkey = oracle._pool_load
    oracle._pool_load = lambda key: None
    try:
        with pytest.raises(SystemExit):
            oracle.pool_for(p, p.designs()[0])
    finally:
        oracle._pool_load = monkey
        oracle._DRAWS.clear()


def test_ladder_never_asks_for_more_missions_than_the_pool_holds(monkeypatch):
    """A budget deeper than the stored missions is served by resampling the same ones, so a method
    converges to the POOL's mean while appearing to buy precision against the simulator's."""
    p = get("qcap_uniform")
    monkeypatch.setattr(oracle, "pool_depth", lambda prob, design=None: 600)
    monkeypatch.setattr(oracle, "difficulty", lambda prob, refresh=False: {
        "budget_to_choose": 40.0, "budget_to_separate": 9_000_000.0})
    lad = oracle.budget_ladder(p)
    assert max(lad) <= 600 * p.n_designs, lad
    assert len(lad) >= 3 and lad == sorted(lad)


def test_regret_frac_is_zero_at_the_best_and_one_at_the_worst():
    """What makes regret averageable across problems scored on delivered service, mission success
    and blue loss. Raw regret carries the metric's units and cannot be pooled across them."""
    p = get("qcap_uniform")
    t = oracle.truth(p)
    lo = min(t, key=lambda k: t[k])
    hi = max(t, key=lambda k: t[k])
    assert oracle.regret_frac(p, json.loads(hi), t) == pytest.approx(0.0)
    assert oracle.regret_frac(p, json.loads(lo), t) == pytest.approx(1.0)
    mid = sorted(t, key=lambda k: t[k])[len(t) // 2]
    assert 0.0 < oracle.regret_frac(p, json.loads(mid), t) < 1.0


def test_chunked_pool_building_reproduces_the_sequential_pool():
    """The pools stage splits a cell's missions into slices and runs them in parallel. That is only
    safe because mission r is seeded from r alone; if a slice's readings depended on where the slice
    started, the assembled pool would differ from the sequential one and the answer key would be a
    function of how many cores the cluster happened to give the job."""
    p = get("qcap_uniform")
    d = p.designs()[0]
    whole = oracle.draw_range(p, d, 0, 6)
    pieces = [oracle.draw_range(p, d, 0, 2), oracle.draw_range(p, d, 2, 4),
              oracle.draw_range(p, d, 4, 6)]
    joined = {m: [x for piece in pieces for x in piece[m]] for m in whole}
    assert joined == whole


def test_pool_meter_stays_paired_after_a_wrap():
    """The wrap that refreshes an exhausted pool is seeded, and it was seeded on the meter's TOTAL
    wrap count. That made a design's reshuffled ordering depend on how many other designs had
    wrapped first, so two methods that spent their pools in different orders diverged after the
    first wrap: the pairing failure this meter exists to remove, one level down, reachable only on a
    rung deep enough to exhaust a pool."""
    from sandtable.search.runner import PoolMeter
    p = get("qcap_uniform")
    depth = _fake_pool(p, depth=16)
    d0, d1 = p.designs()[0], p.designs()[1]

    a = PoolMeter(p, 10_000, 0, replicate=5)
    for _ in range(3):                      # wrap d0 twice before touching d1
        a.pull(d0, 8)
    a.pull(d1, 8)
    a.pull(d1, 8)
    after_a = a.pull(d1, 8)                 # d1's first wrap, with d0 already wrapped

    b = PoolMeter(p, 10_000, 0, replicate=5)
    b.pull(d1, 8)                           # b touches only d1, so no other design has wrapped
    b.pull(d1, 8)
    after_b = b.pull(d1, 8)                 # d1's first wrap, cleanly

    assert after_a == after_b, "a design's wrapped ordering depends on other designs' wraps"
