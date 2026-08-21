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
    assert spans[0] == pytest.approx((20.0 + 22.0) * 0.15)      # 6.30 at a clean link


def test_the_published_span_sits_on_the_threshold():
    """sc_span_control runs six vehicles against a threshold of 6.3, which is the whole story."""
    assert qt.collapse_span(0.0, **OP) == pytest.approx(6.30, abs=0.01)


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
