"""Instrument defect 18: `busy_*` is a fraction of the console's time on one console only.

The six `busy_*` metrics divide accumulated service time by `total_steps` and are documented as
fractions of the console's time. That is right on the buffer console, which refuses to begin a
service while it is still busy, so its book never runs past the clock. It is wrong on the published
RESERVE console, which commits a request to a slot at arrival and books forward without bound: at
thirty-two assets it holds a book almost five times longer than the mission, and the same division
returns almost five where a fraction was promised.

The genus is the project's usual one, a convention correctly derived for its first use case and then
carried silently into a second where it does not hold. What makes this instance worth a guard rather
than a footnote is that the wrong number is not obviously wrong: 4.74 looks like a utilization to
anyone who does not know which console produced it, and every battery that measures `busy_*` happens
to run on `buffer`, so nothing in the paper caught it.
"""
from __future__ import annotations

import math

import pytest

from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

FRACTIONS = ("busy_serviced", "busy_stale", "busy_lost", "busy_late", "busy_dead", "busy_total")
SCN = "scenarios/sc_span_control.json"


def _run(n, qm, seed=0):
    return run_mission(load_scenario(SCN), seed=seed, params={"n_blue": n, "queue_model": qm})


@pytest.mark.parametrize("n", [8, 16, 32])
def test_the_fractions_are_fractions_on_the_console_they_were_derived_for(n):
    """One service can overrun the horizon, so the bound is one plus a service, not one."""
    m = _run(n, "buffer")
    for name in FRACTIONS:
        assert math.isfinite(m[name]), f"{name} is not finite on buffer"
        assert 0.0 <= m[name] <= 1.02, f"{name} = {m[name]:.4f} is not a fraction"
    assert m["busy_dead"] <= m["busy_total"] + 1e-12


@pytest.mark.parametrize("n", [8, 16, 32])
def test_the_fractions_refuse_to_answer_on_the_console_they_were_not(n):
    """NaN rather than a plausible-looking number. `tools/ar_survey.py` refuses NaN loudly."""
    m = _run(n, "reserve")
    for name in FRACTIONS:
        assert math.isnan(m[name]), f"{name} = {m[name]!r} on reserve, expected nan"


def test_the_ratio_that_is_defined_on_both_consoles_is_reported_under_its_own_name():
    """`booked_per_step` is service time committed per mission step. On buffer it coincides with
    `busy_total` because the book never outruns the clock; on reserve it is the offered load."""
    for n in (8, 16, 32):
        b = _run(n, "buffer")
        assert b["booked_per_step"] == pytest.approx(b["busy_total"], abs=1e-12)
        r = _run(n, "reserve")
        assert math.isfinite(r["booked_per_step"])


def test_the_trap_was_real_and_the_repair_did_not_invent_it():
    """The negative control. If `booked_per_step` never exceeded one on the published console there
    would be nothing to guard, and this test would be theatre. It exceeds one by a factor of four
    and a half, which is the number a reader would have called a utilization."""
    small = _run(8, "reserve")["booked_per_step"]
    big = _run(32, "reserve")["booked_per_step"]
    assert small > 1.0, f"reserve at eight books {small:.4f} per step, expected over one"
    assert big > 4.0, f"reserve at thirty-two books {big:.4f} per step, expected over four"
    assert big > small                       # and it grows with the span, as an offered load does


def test_utilization_was_never_wrong_and_is_left_alone():
    """`operator_utilization` counts busy STEPS and divides by steps, so it was a fraction on both
    consoles all along. The repair must not have touched it, or the comparison it exists to support
    against `busy_total` would be broken in the other direction."""
    for n in (8, 32):
        for qm in ("reserve", "buffer"):
            u = _run(n, qm)["operator_utilization"]
            assert 0.0 <= u <= 1.0, f"{qm} at {n}: utilization {u:.4f}"


def test_the_published_buffer_numbers_did_not_move():
    """Every battery that measures `busy_*` runs on `buffer`, so the repair is required to be
    invisible there. Pinned on values, not on an invariant that could drift with them."""
    ref = {8: (1.0017, 0.9738), 16: (1.0000, 0.9889), 32: (1.0020, 0.9869)}
    for n, (total, dead) in ref.items():
        m = _run(n, "buffer")
        assert m["busy_total"] == pytest.approx(total, abs=1e-4)
        assert m["busy_dead"] == pytest.approx(dead, abs=1e-4)
