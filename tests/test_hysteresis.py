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


def test_retry_spread_holds_the_backoff_mean_and_sets_only_its_width():
    """CR-21. The published rescale shrinks the backoff's MEAN and its JITTER by the same factor,
    so a retry that shortens the cycle also strips out the desynchronization. The control must
    separate them: identical mean at every width."""
    from sandtable import c2

    class Op:
        decision_interval = 22
        retry_backoff = 4
        retry_spread = -1
        retry_mode = "fixed"

    op = Op()
    draws = list(range(11, 34))          # the full support of _reset_cooldown at tau = 22
    rescaled = [c2._backoff(op, c) for c in draws]
    assert (min(rescaled), max(rescaled)) == (2, 6)
    base = sum(rescaled) / len(rescaled)
    for spread in (0, 1, 2, 3):
        op.retry_spread = spread
        v = [c2._backoff(op, c) for c in draws]
        assert abs(sum(v) / len(v) - base) < 1e-9
        assert max(v) - min(v) == 2 * spread
    # spread = 2 at rho = 4 IS the published rescale, so the control nests the shipped behaviour
    op.retry_spread = 2
    assert [c2._backoff(op, c) for c in draws] == rescaled
    # and at rho = 12 the width can reach the standing cycle's own 22 steps without moving the mean
    op.retry_backoff, op.retry_spread = 12, 11
    wide = [c2._backoff(op, c) for c in draws]
    assert (min(wide), max(wide)) == (1, 23)
    assert abs(sum(wide) / len(wide) - 12.0) < 1e-9


def test_retry_spread_defaults_off_and_costs_no_extra_draw(skirmish_scenario):
    """Off by default, and the transform reuses the interval's own draw, so a spread arm and a
    rescale arm stay paired on a shared seed."""
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities
    import numpy as np

    scn = skirmish_scenario.with_params({"control_mode": "direct", "retry_prob": 1.0,
                                         "retry_backoff": 4})
    rng = np.random.default_rng(0)
    op = build_c2(scn, build_entities(scn, rng), rng)
    assert op.retry_spread == -1
    scn2 = scn.with_params({"retry_spread": 3})
    op2 = build_c2(scn2, build_entities(scn2, np.random.default_rng(0)),
                   np.random.default_rng(0))
    assert op2.retry_spread == 3


def test_adaptive_backoff_doubles_and_caps_at_the_standing_interval():
    """CR-23. The doubling rule must reach the floor on its own and never hold a vehicle longer
    than not retrying would, so a retry can never be worse than no retry."""
    import numpy as np
    from sandtable import c2

    class Op:
        decision_interval = 22
        retry_backoff = 4
        retry_spread = -1
        retry_mode = "double"
        retry_streak = np.arange(8)

    op = Op()
    holds = [c2._backoff(op, 22, i) for i in range(8)]
    assert holds[:5] == [4, 4, 8, 16, 22]
    assert all(h <= op.decision_interval for h in holds)
    assert holds == sorted(holds)
    # it passes the band-closing floor of 15.33 by the fourth unanswered request
    assert holds[3] >= 15.33


def test_the_streak_resets_on_service(skirmish_scenario):
    """A vehicle that gets an answer must start again from the base hold, or the rule ratchets and
    an unlucky early patch would punish a vehicle for the rest of the mission."""
    import numpy as np
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    scn = skirmish_scenario.with_params({"control_mode": "direct", "retry_prob": 1.0,
                                         "retry_backoff": 4, "retry_mode": "double"})
    rng = np.random.default_rng(0)
    op = build_c2(scn, build_entities(scn, rng), rng)
    assert op.retry_mode == "double"
    assert op.retry_streak is not None and int(op.retry_streak.sum()) == 0


def test_retry_mode_rejects_an_unknown_rule(skirmish_scenario):
    import numpy as np
    import pytest as _pytest
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    scn = skirmish_scenario.with_params({"control_mode": "direct", "retry_mode": "exponential"})
    rng = np.random.default_rng(0)
    with _pytest.raises(ValueError, match="retry_mode"):
        build_c2(scn, build_entities(scn, rng), rng)


def test_cadence_aimd_needs_a_signal_to_consume(skirmish_scenario):
    """CR-26. AIMD is a response to an explicit refusal, so it is only defined under `admit`.
    Allowing it under `blind` would let a vehicle react to a message the operator never sent."""
    import numpy as np
    import pytest as _pytest
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    rng = np.random.default_rng(0)
    for policy in ("blind", "refund"):
        scn = skirmish_scenario.with_params({"control_mode": "direct", "queue_policy": policy,
                                             "admit_response": "aimd"})
        with _pytest.raises(ValueError, match="admit"):
            build_c2(scn, build_entities(scn, rng), rng)
    scn = skirmish_scenario.with_params({"control_mode": "direct", "queue_policy": "admit",
                                         "admit_response": "aimd"})
    op = build_c2(scn, build_entities(scn, rng), rng)
    assert op.admit_response == "aimd"
    assert float(op.cadence_rate.min()) == 1.0    # everyone starts at the standing cadence


def test_cadence_aimd_halves_on_refusal_and_recovers_in_eight(skirmish_scenario):
    """The schedule is TCP's: multiplicative decrease on the congestion signal, additive increase
    on the acknowledgement, floored so the cadence never stretches past four standing intervals."""
    import numpy as np
    from sandtable import c2
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    scn = skirmish_scenario.with_params({"control_mode": "direct", "queue_policy": "admit",
                                         "admit_response": "aimd"})
    rng = np.random.default_rng(0)
    op = build_c2(scn, build_entities(scn, rng), rng)
    r = 1.0
    for _ in range(4):                                   # four refusals in a row
        r = max(c2._AIMD_FLOOR, r * c2._AIMD_BETA)
    assert r == c2._AIMD_FLOOR                           # floored, not driven to zero
    n = 0
    while r < 1.0:                                       # and it climbs back additively
        r = min(1.0, r + c2._AIMD_ALPHA)
        n += 1
    assert n == 6                                        # 0.25 -> 1.0 at an eighth a time


def test_cadence_aimd_stretches_the_interval_it_scales(skirmish_scenario):
    """A halved request rate must double the drawn interval, and only for the vehicle that was
    refused: AIMD is per-vehicle, not a global dial."""
    import numpy as np
    from sandtable import c2
    from sandtable.c2 import build_c2
    from sandtable.scenario import build_entities

    scn = skirmish_scenario.with_params({"control_mode": "direct", "queue_policy": "admit",
                                         "admit_response": "aimd", "decision_interval": 22})
    op = build_c2(scn, build_entities(scn, np.random.default_rng(0)), np.random.default_rng(0))
    op.cadence_rate[0] = 0.5
    base = [c2._reset_cooldown(op, np.random.default_rng(s), 0.0, 1) for s in range(40)]
    slow = [c2._reset_cooldown(op, np.random.default_rng(s), 0.0, 0) for s in range(40)]
    assert all(b * 2 - 1 <= t <= b * 2 + 1 for b, t in zip(base, slow))
    assert sum(slow) > sum(base)


def test_jitter_arms_are_rejected_on_the_realized_mean_not_on_their_width():
    """CR-27 amendment. A width bound is the wrong guard: the hold is floored at one step, so a
    spread well inside any usable width bound can still truncate the low tail and raise the mean.
    An arm that claims to hold its mean is checked by value over the full support."""
    from sandtable import c2

    class Op:
        decision_interval = 22
        retry_backoff = 4
        retry_spread = 0
        retry_mode = "fixed"

    op = Op()
    # The arms every mean-matched battery uses: spread = rho - 1 puts the support on
    # [1, 2*rho - 1] and the floor never bites, so the mean is exactly rho.
    for rho in (4, 10, 18, 21):
        op.retry_backoff, op.retry_spread = rho, rho - 1
        assert abs(c2.backoff_mean(op) - rho) < 1e-9
    # And the case a width bound of `rho + tau` waves through.
    op.retry_backoff, op.retry_spread = 4, 12
    assert op.retry_spread <= op.retry_backoff + op.decision_interval
    assert c2.backoff_mean(op) > 5.5
    # The one deliberate exception the free-cell width ladder needs, and its size.
    op.retry_backoff, op.retry_spread = 21, 21
    assert abs(c2.backoff_mean(op) - 21.0) < 0.05


def test_the_published_rescale_is_not_held_to_the_mean_guard(skirmish_scenario):
    """`retry_spread = -1` is the shipped rescale, which shrinks the mean deliberately. The guard
    applies to arms that CLAIM a held mean, so it must not fire on the default."""
    from sandtable.sim import run_mission

    p = {"control_mode": "direct", "comms_level": 3, "n_blue": 5, "retry_prob": 1.0,
         "retry_backoff": 4}
    run_mission(skirmish_scenario.with_params(p), seed=5)                      # default, -1
    run_mission(skirmish_scenario.with_params({**p, "retry_spread": -1}), seed=5)
