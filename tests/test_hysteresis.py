"""CR-17: closed-loop reliance, and the fold band it opens in span-of-control.

A vehicle that asked for help and did not get it may ask again sooner than one that was served.
That makes the offered load depend on the state the queue is already in, which is the one
ingredient the M/D/1+D model was missing to be bistable. These tests check the mechanism
(the retry fires, shortens the cycle, and leaves the OFF path untouched), the closed form
(band edges, width, backoff floor), and the agreement between them.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import queue_theory as qt  # noqa: E402
from sandtable import sim  # noqa: E402
from sandtable.c2 import build_c2  # noqa: E402

from sandtable.comms_ew import build_comms  # noqa: E402
from sandtable.scenario import Scenario, build_entities, load_scenario  # noqa: E402

BASE = load_scenario(ROOT / "scenarios" / "sc_span_control.json")
# The published queue operating point, so the numbers here are the paper's numbers.
P, TAU, MU = 20, 22, 0.15


def arm(**kw) -> Scenario:
    prm = dict(BASE.params, control_mode="direct", comms_level=0, **kw)
    return Scenario(**{**BASE.__dict__, "params": prm})


# ---------------------------------------------------------------- closed form


def test_band_is_empty_without_retry():
    """No reliance loop, no band: both edges fall back on the published threshold."""
    n_c, n_h = qt.fold_band(0.0, MU, P, TAU, retry_prob=0.0)
    assert n_c == pytest.approx(n_h)
    assert n_c == pytest.approx(qt.collapse_span(0.0, MU, P, TAU))


def test_band_is_empty_when_retry_does_not_shorten_the_cycle():
    """A retry that waits the full decision interval is not a retry, whatever it is called."""
    n_c, n_h = qt.fold_band(0.0, MU, P, TAU, retry_prob=1.0, retry_backoff=TAU)
    assert n_c == pytest.approx(n_h)


def test_band_width_is_independent_of_the_link():
    """`d` cancels out of `n_h - n_c` at the floor, so jamming moves the band, not its width."""
    w = []
    for p_drop in (0.0, 0.10, 0.35):
        n_c, n_h = qt.fold_band(p_drop, MU, P, TAU, retry_prob=0.7, retry_backoff=5)
        w.append(n_h - n_c)
    assert w[0] == pytest.approx(w[1]) == pytest.approx(w[2])
    assert w[0] == pytest.approx(1 * MU * 0.7 * (TAU - 5))


def test_backoff_floor_closes_the_band_to_under_one_vehicle():
    """The floor is a design rule, so it has to actually deliver a sub-vehicle band."""
    for pi in (0.3, 0.6, 1.0):
        rho = qt.backoff_floor(MU, TAU, pi)
        n_c, n_h = qt.fold_band(0.0, MU, P, TAU, retry_prob=pi, retry_backoff=rho)
        assert n_h - n_c == pytest.approx(1.0)
        n_c2, n_h2 = qt.fold_band(0.0, MU, P, TAU, retry_prob=pi, retry_backoff=rho + 1.0)
        assert n_h2 - n_c2 < 1.0


def test_healthy_abandonment_narrows_the_band_from_above():
    """The default `1 - d` is a floor on abandonment, hence an upper bound on `n_h`."""
    _, n_hi = qt.fold_band(0.0, MU, P, TAU, retry_prob=1.0, retry_backoff=4)
    _, n_lo = qt.fold_band(0.0, MU, P, TAU, retry_prob=1.0, retry_backoff=4,
                           abandon_healthy=0.222)
    assert n_lo < n_hi
    assert n_lo == pytest.approx(5.85, abs=0.01)


# ---------------------------------------------------------------- mechanism


def test_retry_off_draws_nothing_and_reproduces_the_published_run():
    """Opt-in discipline: the retry coin must not exist when the mechanism is off."""
    a = sim.run_mission(arm(n_blue=8), seed=3)
    b = sim.run_mission(arm(n_blue=8, retry_prob=0.0, retry_backoff=4), seed=3)
    assert a == b


def test_retry_shortens_the_cycle_and_raises_offered_load():
    """The whole mechanism in one number: same span, more requests, less of each served."""
    off = [sim.run_mission(arm(n_blue=8), seed=s) for s in range(12)]
    on = [sim.run_mission(arm(n_blue=8, retry_prob=1.0, retry_backoff=4), seed=s)
          for s in range(12)]
    assert np.mean([m["operator_goodput"] for m in on]) < \
        np.mean([m["operator_goodput"] for m in off])


def test_retry_rejects_out_of_range_parameters():
    for bad in (dict(retry_prob=-0.1), dict(retry_prob=1.5), dict(retry_backoff=0)):
        scn = arm(n_blue=4, **({"retry_prob": 0.5} | bad))
        rng = np.random.default_rng(0)
        ent = build_entities(scn, rng)
        with pytest.raises(ValueError):
            build_c2(scn, ent, rng)


# ---------------------------------------------------------------- transient jam


def test_jam_window_is_a_no_op_when_undeclared():
    c = build_comms(arm(n_blue=4))
    before = (c.latency, c.p_drop)
    for k in (0, 5, 500):
        c.set_step(k)
        assert (c.latency, c.p_drop) == before


def test_jam_window_swaps_the_link_only_inside_the_window():
    c = build_comms(arm(n_blue=4, jam_window=[10, 20], jam_level=5))
    c.set_step(9)
    assert (c.latency, c.p_drop) == (0, 0.0)
    c.set_step(10)
    assert (c.latency, c.p_drop) == (16, 0.55)
    c.set_step(19)
    assert c.p_drop == 0.55
    c.set_step(20)
    assert (c.latency, c.p_drop) == (0, 0.0)


def test_jam_window_rejects_a_bursty_channel_and_an_empty_window():
    with pytest.raises(ValueError):
        build_comms(arm(n_blue=4, jam_window=[10, 20], channel="gilbert_elliot"))
    with pytest.raises(ValueError):
        build_comms(arm(n_blue=4, jam_window=[20, 10]))


# ---------------------------------------------------------------- theory vs simulator


def test_simulator_is_bistable_inside_the_band_and_not_outside_it():
    """The claim, end to end: inside the band the initial condition decides the steady state.

    Five vehicles sit inside the predicted band and six do not (the healthy branch dies at 5.85
    once the measured healthy abandonment is fed in), so a burst start and a staggered start must
    separate at five and agree at three and eight. The retry-off arm is the control: staggering
    also perturbs the RNG stream, and only the DIFFERENCE of differences isolates the loop.
    """
    def gap(n, retry):
        kw = dict(retry_prob=1.0, retry_backoff=4) if retry else {}
        out = []
        for stag in (False, True):
            ms = [sim.run_mission(arm(n_blue=n, stagger_decisions=stag, **kw), seed=s)
                  for s in range(24)]
            out.append(np.mean([m["operator_goodput"] for m in ms]))
        return out[1] - out[0]

    inside = gap(5, True) - gap(5, False)
    below = gap(3, True) - gap(3, False)
    above = gap(8, True) - gap(8, False)
    assert inside > 0.4                       # two steady states at the same span
    assert abs(below) < 0.05 and abs(above) < 0.05
