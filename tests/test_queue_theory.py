"""The closed-form operator queue, and its agreement with the simulator it explains.

`tools/queue_theory.py` is the analytic counterpart to `c2.py`: the same single server, the same
deterministic service, the same abandonment after `patience`, with the mission stripped away. It
exists so that SandTable's operator behaviour can be checked against something solvable rather
than only against itself.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "queue_theory", pathlib.Path(__file__).resolve().parents[1] / "tools" / "queue_theory.py")
qt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qt)

# The centerpiece scenario's operating point.
OP = dict(service_rate=0.15, patience=20.0, decision_interval=22.0)


def test_latency_cutoff_matches_the_c2_arithmetic():
    """A reply must fit inside patience even with an idle operator: 2*lat + 1/rate <= patience."""
    sp = {"service_rate": OP["service_rate"], "patience": OP["patience"]}
    assert qt.serviceable(6, **sp)          # 12 + 6.67 = 18.67
    assert not qt.serviceable(7, **sp)      # 14 + 6.67 = 20.67
    # The published ladder: C3 has latency 4 and is serviceable, C4 has latency 8 and is not.
    assert qt.serviceable(4, **sp)
    assert not qt.serviceable(8, **sp)


def test_c4_and_c5_are_the_same_rung_for_direct_control():
    """Both are latency-blocked, so the drop rate cannot separate them. Conjecture C2."""
    r4 = qt.solve(8, 8, 0.35, **OP)
    r5 = qt.solve(8, 16, 0.55, **OP)
    assert r4["regime"] == r5["regime"] == "latency-blocked"
    assert r4["goodput"] == r5["goodput"] == 0.0


def test_collapse_span_rises_with_jamming():
    """A dropped request is a request the operator never has to work, so loss raises capacity."""
    spans = [qt.collapse_span(d, **OP) for d in (0.0, 0.05, 0.10, 0.20, 0.35, 0.55)]
    assert spans == sorted(spans)
    assert spans[0] == pytest.approx((20.0 + 22.0 + 1.0) * 0.15)   # 6.45 at a clean link


def test_the_published_span_sits_on_the_threshold():
    """sc_span_control runs six vehicles against a threshold of 6.45, which is the whole story."""
    assert qt.collapse_span(0.0, **OP) == pytest.approx(6.45, abs=0.01)


def test_the_closed_form_uses_the_cycle_the_simulator_actually_runs():
    """The threshold is mu times the collapsed cycle, so the cycle is the thing to guard.

    An earlier version of the closed form used `patience + decision_interval` and was low by one
    step: the cooldown counter is decremented on each of `decision_interval` steps and the decision
    fires on the step AFTER it reaches zero. Asserting the number alone let that survive; asserting
    it against the cycle the model actually runs does not.
    """
    import numpy as np

    from sandtable import c2, sim
    from sandtable.scenario import Scenario, load_scenario

    base = load_scenario("scenarios/sc_span_control.json")
    prm = dict(base.params, control_mode="direct", comms_level=0, n_blue=12)  # deep in collapse
    scn = Scenario(**{**base.__dict__, "params": prm})

    fires, cur, orig = {}, [0], c2.step

    def spy(ent, op, comms, sc, k, rng, world=None):
        before = ent.await_until.copy()
        orig(ent, op, comms, sc, k, rng, world)
        for i in np.nonzero((before < 0) & (ent.await_until >= 0))[0]:
            fires.setdefault((cur[0], int(i)), []).append(k)

    c2.step = spy
    try:
        for sd in range(2):
            cur[0] = sd
            sim.run_mission(scn, seed=sd)
    finally:
        c2.step = orig

    gaps = [d for ks in fires.values() for d in np.diff(ks)]
    cycle = float(np.mean(gaps))
    P, tau, mu = prm["patience"], prm["decision_interval"], prm["service_rate"]
    assert cycle == pytest.approx(P + tau + 1, abs=0.6), f"measured cycle {cycle:.2f}"
    assert qt.collapse_span(0.0, **OP) == pytest.approx(mu * cycle, abs=0.15)


def test_blind_goodput_rises_with_loss_above_the_threshold_and_falls_below_it():
    """The signature of congestion collapse, in the queue alone: no terrain, no combat."""
    above = [qt.queue_only_sim(8, lat, d, **OP, policy="blind")["goodput"]
             for lat, d in [(0, 0.0), (1, 0.05), (2, 0.10), (4, 0.20)]]
    below = [qt.queue_only_sim(4, lat, d, **OP, policy="blind")["goodput"]
             for lat, d in [(0, 0.0), (1, 0.05), (2, 0.10), (4, 0.20)]]
    assert above[-1] > above[0], f"n=8 should be relieved by loss: {above}"
    assert below == sorted(below, reverse=True), f"n=4 should only be hurt by loss: {below}"


def test_refunding_the_slot_removes_the_relief():
    """With the slot refunded there is no collapse to relieve, so loss can only hurt."""
    g = [qt.queue_only_sim(8, lat, d, **OP, policy="refund")["goodput"]
         for lat, d in [(0, 0.0), (1, 0.05), (2, 0.10), (4, 0.20)]]
    assert g == sorted(g, reverse=True), f"not monotone under refund: {g}"
    assert g[0] > 0.6


def test_queue_accounting_partitions_requests():
    r = qt.queue_only_sim(8, 2, 0.10, **OP, steps=4000)
    assert r["goodput"] + r["abandon_queue_frac"] + r["abandon_link_frac"] == pytest.approx(1.0)


def test_collapse_span_is_linear_in_crew_size():
    """c consoles carry c times the load, so staffing and span are the same question."""
    one = qt.collapse_span(0.0, **OP, n_operators=1)
    two = qt.collapse_span(0.0, **OP, n_operators=2)
    assert two == pytest.approx(2.0 * one)
    # Eight vehicles sit above the one-console threshold and below the two-console one, which is
    # why a second operator is the difference between a collapsed queue and a working one.
    assert one < 8 < two


def test_a_second_console_rescues_the_collapsed_queue():
    solo = qt.queue_only_sim(8, 0, 0.0, **OP, policy="blind", n_operators=1)["goodput"]
    pair = qt.queue_only_sim(8, 0, 0.0, **OP, policy="blind", n_operators=2)["goodput"]
    assert solo < 0.2 and pair > 0.9, f"solo={solo:.3f} pair={pair:.3f}"


# ---------------------------------------------------------------- bursty round trip (C1)


def test_bursty_round_trip_matches_the_simulator_channel():
    """The closed form is checked against the channel `c2.step` actually draws from.

    `comms_ew.delivered` advances a shared two-state chain, and the request and the reply are two
    consecutive draws on it. Asserting the formula alone would not catch a change in that draw
    order, so the channel is run.
    """
    import sys

    import numpy as np

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
    from sandtable.comms_ew import build_comms
    from sandtable.scenario import Scenario, load_scenario

    root = pathlib.Path(__file__).resolve().parents[1]
    base = load_scenario(root / "scenarios" / "sc_span_control.json")
    for level in (1, 2, 3, 4, 5):
        prm = dict(base.params, comms_level=level, channel="gilbert_elliot")
        c = build_comms(Scenario(**{**base.__dict__, "params": prm}))
        rng = np.random.default_rng(11)
        ok = 0
        n = 120000
        for _ in range(n):
            up = c.delivered(rng)
            down = c.delivered(rng)
            ok += up and down
        predicted = qt.two_way_delivery_bursty(c.p_drop, 4.0)
        assert ok / n == pytest.approx(predicted, abs=0.006), f"rung {level}"


def test_burstiness_helps_the_handshake_and_so_lowers_the_threshold():
    """The counterintuitive direction, asserted so it cannot silently flip.

    Correlated loss makes a two-message handshake MORE likely to complete than independent loss at
    the same mean, which delivers more work to the bottleneck and moves the cliff left.
    """
    for p in (0.05, 0.10, 0.20, 0.35, 0.55):
        assert qt.two_way_delivery_bursty(p, 4.0) > qt.two_way_delivery(p)
        assert qt.collapse_span(p, 0.15, 20, 22, burst_len=4.0) < \
            qt.collapse_span(p, 0.15, 20, 22)


def test_the_memoryless_point_of_the_burst_family_is_not_burst_length_one():
    """Pins the parameterization, which is easy to get wrong by inspection.

    A chain is memoryless when the next state does not depend on the current one, `p_gb + p_bg = 1`,
    which puts the mean bad-state dwell at `1 / (1 - p)` and not at 1. `burst_len = 1` is the
    ANTI-correlated corner (the bad state never repeats), and it delivers WORSE round trips than
    the memoryless channel, not the same.
    """
    for p in (0.05, 0.20, 0.55):
        assert qt.two_way_delivery_bursty(p, 1.0 / (1.0 - p)) == \
            pytest.approx(qt.two_way_delivery(p))
        assert qt.two_way_delivery_bursty(p, 1.0) < qt.two_way_delivery(p)


def test_the_burst_effect_is_bounded_by_the_marginal_survival_rate():
    """`d` cannot exceed `(1-p)`, so the threshold cannot fall by more than that factor.

    This is the scope bound on the whole burstiness result: the model draws the request and the
    reply adjacently, which is the MOST correlated a channel can make them, and even that only
    buys `(1-p)` instead of `(1-p)^2`.
    """
    for p in (0.05, 0.20, 0.55):
        memoryless = 1.0 / (1.0 - p)
        for burst in (memoryless, 4.0, 64.0, 4096.0):
            assert burst >= memoryless, "the ladder default must sit above the memoryless point"
            d = qt.two_way_delivery_bursty(p, burst)
            assert qt.two_way_delivery(p) <= d + 1e-12 and d <= 1.0 - p + 1e-12
        assert qt.two_way_delivery_bursty(p, 1e9) == pytest.approx(1.0 - p, abs=1e-6)
        # Below the memoryless point the chain is anti-correlated and the bound does not apply.
        assert qt.two_way_delivery_bursty(p, 1.0) < qt.two_way_delivery(p)
