"""Tests for the opt-in personality-movement mode (sandtable.personality).

Covers (1) opt-in gating and a byte-identical baseline (no movement param -> the scripted lane path,
unchanged); (2) determinism; and (3) that emergent enemy-repulsion produces threat-avoiding maneuver
that lowers losses, the whole point of the propensity-movement lineage (ISAAC/EINSTein/MANA): route
choice emerges from local rules rather than a scripted lane. The mission-level direction asserted
here is the one measured in experiments/empirical.md.
"""
import numpy as np

from sandtable import personality
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

UC3 = "scenarios/uc3_route_defilade.json"


def _pers(**kw):
    return {"movement": "personality", "personality": {"w_goal": 1.0, **kw}}


def test_optin_none_by_default(skirmish_scenario):
    assert personality.build_personality(skirmish_scenario) is None          # no movement param
    assert personality.build_personality(skirmish_scenario.with_params({"movement": "scripted"})) is None
    on = skirmish_scenario.with_params(_pers(w_enemy=1.0))
    assert personality.build_personality(on) is not None


def test_non_personality_movement_is_byte_identical():
    # Any movement value other than "personality" leaves the scripted lane path exactly in place.
    base = run_mission(load_scenario(UC3), seed=7)
    same = run_mission(load_scenario(UC3), seed=7, params={"movement": "scripted"})
    assert base == same


def test_personality_deterministic():
    p = _pers(w_enemy=1.0, w_cover=0.5)
    assert run_mission(load_scenario(UC3), seed=4, params=p) == \
        run_mission(load_scenario(UC3), seed=4, params=p)


def _mean(params, key, seeds=range(12)):
    return float(np.mean([run_mission(load_scenario(UC3), seed=s, params=params)[key] for s in seeds]))


def test_enemy_repulsion_is_emergent_maneuver():
    # With no enemy propensity the force drives straight through the defense; turning it on makes the
    # agents bow around detected threats, a route choice that emerges from local rules and cuts
    # losses. Direction from empirical.md: losses fall sharply as w_enemy rises from 0.
    straight = _mean(_pers(w_enemy=0.0), "blue_losses")
    avoid = _mean(_pers(w_enemy=1.0), "blue_losses")
    assert avoid < straight
