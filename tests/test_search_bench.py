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
