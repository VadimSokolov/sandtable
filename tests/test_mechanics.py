"""Tests for the opt-in kill-web mechanics (sandtable.mechanics): suppression and munitions.

Covers (1) opt-in gating and a byte-identical baseline (with no mech the engagement path and its RNG
draws are unchanged); (2) the munitions ceiling (a shooter that runs dry stops firing); (3) the
suppression multiplier (a suppressed shooter fires less effectively) and that incoming fire raises
suppression, which decays; and (4) that both are first-order at the mission level (they move mission
outcomes), which is the whole point of carrying the state rather than folding it into a fixed Pk
table. The mission-level directions asserted here are the ones measured in experiments/empirical.md.
"""
import numpy as np
import pytest

from sandtable import engagement, mechanics
from sandtable.entities import BLUE, RED, Entities
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

UC3 = "scenarios/uc3_route_defilade.json"


def _mech(**kw):
    return {"mech": {**kw}}


def _M(**kw):
    """A Mech with inert defaults; override only the fields a unit test exercises."""
    cfg = dict(suppression=False, munitions=False, supp_gain=0.25, supp_decay=0.85,
               supp_fire=0.8, ammo_load=30.0)
    cfg.update(kw)
    return mechanics.Mech(**cfg)


# --- opt-in gating + byte-identical baseline -------------------------------------------------

def test_optin_none_by_default(skirmish_scenario):
    assert mechanics.build_mech(skirmish_scenario) is None                       # no mech param
    assert mechanics.build_mech(skirmish_scenario.with_params(_mech())) is None  # both flags off
    on = skirmish_scenario.with_params(_mech(suppression=True))
    assert mechanics.build_mech(on) is not None


def test_null_mech_is_byte_identical():
    # A mech config that disables both effects builds to None and takes the baseline path exactly.
    base = run_mission(load_scenario(UC3), seed=7)
    null = run_mission(load_scenario(UC3), seed=7, params=_mech())
    assert base == null


def test_mech_on_is_deterministic():
    p = _mech(suppression=True, munitions=True, ammo_load=8)
    assert run_mission(load_scenario(UC3), seed=3, params=p) == \
        run_mission(load_scenario(UC3), seed=3, params=p)


# --- munitions (unit) ------------------------------------------------------------------------

def _shooter_vs_fat_target(make_world, hp=10.0):
    """One blue shooter (pk 1, cover 0) vs a fat-hp red target it can never miss or be fired on."""
    w = make_world(cover=0.0)
    e = Entities.allocate(2)
    e.side[:] = [BLUE, RED]
    e.x[:] = [0.0, 50.0]
    e.y[:] = 0.0
    e.weapon_range[:] = [500.0, 0.0]
    e.pk_base[:] = [1.0, 0.0]
    e.hp[:] = [1.0, hp]
    e.seen[:] = [False, True]
    return w, e


def test_munitions_cap_total_shots(make_world):
    w, e = _shooter_vs_fat_target(make_world, hp=10.0)
    mech = _M(munitions=True, ammo_load=3)
    mechanics.arm(e, mech)
    rng = np.random.default_rng(0)
    for _ in range(8):
        engagement.step(e, w, dt=1.0, rng=rng, mech=mech)
    assert e.hp[1] == pytest.approx(7.0)     # exactly 3 hits (pk 1), then the shooter is dry
    assert e.ammo[0] == pytest.approx(0.0)


def test_munitions_off_is_unlimited(make_world):
    w, e = _shooter_vs_fat_target(make_world, hp=6.0)
    mech = _M(munitions=False, ammo_load=3)   # munitions off -> arm is a no-op, ammo stays inf
    mechanics.arm(e, mech)
    assert np.isinf(e.ammo[0])
    rng = np.random.default_rng(0)
    for _ in range(8):
        engagement.step(e, w, dt=1.0, rng=rng, mech=mech)
    assert e.hp[1] == pytest.approx(0.0)      # destroyed: no ammunition ceiling


# --- suppression (unit) ----------------------------------------------------------------------

def _many_duels(make_world, k, pk=0.5):
    """K independent blue-vs-red duels, 2 km apart so none cross-engage; red is disarmed."""
    w = make_world(width=k * 2000.0, cover=0.0)
    e = Entities.allocate(2 * k)
    e.side[:k] = BLUE
    e.side[k:] = RED
    xs = np.arange(k) * 2000.0
    e.x[:k] = xs
    e.x[k:] = xs + 50.0
    e.y[:] = 0.0
    e.weapon_range[:k] = 100.0
    e.weapon_range[k:] = 0.0
    e.pk_base[:k] = pk
    e.pk_base[k:] = 0.0
    e.seen[k:] = True
    e.hp[:] = 1.0
    return w, e


def test_suppression_multiplier_cuts_pk(make_world):
    # Fully-suppressed shooters fire at pk*(1-supp_fire); far fewer kills than the unsuppressed run.
    k = 800
    mech = _M(suppression=True, supp_fire=0.8, supp_gain=0.0)
    w, e = _many_duels(make_world, k, pk=0.5)
    e.suppression[:k] = 1.0                                        # shooters fully suppressed
    engagement.step(e, w, dt=1.0, rng=np.random.default_rng(1), mech=mech)
    supp_kills = int((~e.alive[k:]).sum())

    w2, e2 = _many_duels(make_world, k, pk=0.5)
    engagement.step(e2, w2, dt=1.0, rng=np.random.default_rng(1))  # no mech
    base_kills = int((~e2.alive[k:]).sum())

    assert base_kills > 300                     # pk 0.5 over 800 duels
    assert supp_kills < base_kills / 2          # suppression clearly degrades fire (pk ~0.1)


def test_incoming_fire_raises_suppression(make_world):
    # After a mutual exchange, both units carry suppression from being fired upon.
    w = make_world(cover=0.0)
    e = Entities.allocate(2)
    e.side[:] = [BLUE, RED]
    e.x[:] = [0.0, 50.0]
    e.y[:] = 0.0
    e.weapon_range[:] = 100.0
    e.pk_base[:] = 0.0            # nobody dies, so both survive to be measured
    e.seen[:] = True
    mech = _M(suppression=True, supp_gain=0.25)
    engagement.step(e, w, dt=1.0, rng=np.random.default_rng(0), mech=mech)
    assert e.suppression[0] == pytest.approx(0.25)   # each was engaged once
    assert e.suppression[1] == pytest.approx(0.25)


def test_suppression_decays():
    e = Entities.allocate(3)
    e.suppression[:] = [0.0, 0.5, 1.0]
    mechanics.decay(e, _M(suppression=True, supp_decay=0.5))
    assert np.allclose(e.suppression, [0.0, 0.25, 0.5])


# --- mission-level first-order effects (directions measured in empirical.md) ------------------

def _mean(params, key, seeds=range(10)):
    return float(np.mean([run_mission(load_scenario(UC3), seed=s, params=params)[key] for s in seeds]))


def test_scarce_munitions_spare_the_attacker():
    # A defender with a small basic load cannot service every vehicle crossing its engagement area,
    # so the attacker loses fewer platforms. A fixed Pk table (the infinite-ammo limit) cannot show
    # this. Direction from empirical.md: blue losses rise monotonically with defender ammo.
    scarce = _mean(_mech(munitions=True, ammo_load=4), "blue_losses")
    plenty = _mean(_mech(munitions=True, ammo_load=1000), "blue_losses")
    assert scarce < plenty


def test_suppression_helps_the_maneuver_force():
    # The attacking echelon out-guns the defenders here, so suppressing them lets the maneuver force
    # cross at lower cost (a base-of-fire effect). Direction from empirical.md: blue losses fall as
    # suppression strengthens.
    base = _mean(_mech(), "blue_losses")                       # null mech == baseline
    supp = _mean(_mech(suppression=True, supp_fire=1.0), "blue_losses")
    assert supp < base
