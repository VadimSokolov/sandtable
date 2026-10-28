"""Convoy security vehicles and a contact reaction (Issue #12, Increment A).

Opt-in via `convoy.security_ptype` and `convoy.contact_reaction`. Absent, every run is byte-identical
to the code before this existed and the reaction draws no random numbers. Present, a security platform
type arms the gun trucks and one generic rule (trigger, action, release) halts or does not halt the
column on contact.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from conftest import same_run
from sandtable import behavior, engagement
from sandtable.convoy import (
    ROLE_CARGO, ROLE_SECURITY, build_convoy_layout, resolve_contact_reaction, resolve_convoy_spec,
    validate_convoy_spec,
)
from sandtable.entities import BLUE, RED, Entities
from sandtable.scenario import Scenario, build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

SC = load_scenario("scenarios/uc3_convoy.json")
ALL_TRIGGERS = ["receive_fire", "lead_lost", "detect_range"]


def _rx(action="halt", triggers=None, **kw):
    return {"action": action, "triggers": ALL_TRIGGERS if triggers is None else triggers, **kw}


def _scenario_with_gun_truck(red_pk=None) -> Scenario:
    d = json.loads(Path("scenarios/uc3_convoy.json").read_text())
    d["platform_types"]["gun_truck"] = {
        "domain": 0, "max_speed": 12.0, "turn_rate": 0.6, "sensor_range": 2000.0,
        "weapon_range": 900.0, "pk_base": 0.05, "hp": 2.0,
    }
    if red_pk is not None:
        d["platform_types"]["at_team"]["pk_base"] = red_pk
    return Scenario.from_dict(d)


# ---- byte identity when off -------------------------------------------------

def test_off_is_byte_identical():
    """Absent, None and "none" are the same run on every seed (no reaction state is built)."""
    for seed in range(6):
        a = run_mission(SC, seed=seed, params={})
        b = run_mission(SC, seed=seed, params={"contact_reaction": None})
        c = run_mission(SC, seed=seed, params={"contact_reaction": "none"})
        assert same_run(a, b) and same_run(a, c)


def test_off_builds_no_reaction():
    assert resolve_contact_reaction(None) is None
    assert resolve_contact_reaction({"contact_reaction": "none"}) is None
    assert behavior.build_behavior(SC, build_entities(SC, make_rng(0, SC.id))) is None


def test_fired_at_is_a_pure_write(make_world):
    """Passing `fired_at` changes neither the outcome nor the RNG stream."""
    def duel():
        e = Entities.allocate(2)
        e.side[:] = [BLUE, RED]
        e.x[:] = [0.0, 50.0]
        e.y[:] = [0.0, 0.0]
        e.weapon_range[:] = [500.0, 500.0]
        e.pk_base[:] = [0.4, 0.4]
        e.hp[:] = [1.0, 1.0]
        e.seen[:] = [True, True]
        return e

    w = make_world(cover=0.0)
    a, b = duel(), duel()
    ra, rb = np.random.default_rng(3), np.random.default_rng(3)
    fired = np.zeros(2, bool)
    for _ in range(5):
        engagement.step(a, w, 1.0, ra)
        engagement.step(b, w, 1.0, rb, fired_at=fired)
    assert (a.hp == b.hp).all() and (a.alive == b.alive).all()
    assert ra.bit_generator.state == rb.bit_generator.state


def test_fired_at_marks_targets_before_any_kill(make_world):
    """A shot that cannot kill (pk 0) still marks its target: the signal precedes the loss."""
    e = Entities.allocate(2)
    e.side[:] = [BLUE, RED]
    e.x[:] = [0.0, 50.0]
    e.y[:] = [0.0, 0.0]
    e.weapon_range[:] = [0.0, 500.0]
    e.pk_base[:] = [0.0, 0.0]
    e.hp[:] = [1.0, 1.0]
    e.seen[:] = [True, False]
    fired = np.zeros(2, bool)
    engagement.step(e, make_world(cover=0.0), 1.0, np.random.default_rng(0), fired_at=fired)
    assert fired.tolist() == [True, False] and e.alive.all()


# ---- specification ------------------------------------------------------------

def test_spec_validation():
    base = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1}
    for bad in (
        _rx(action="retreat"),
        _rx(triggers=[]),
        _rx(triggers=["ied_event"]),
        _rx(release={"rule": "leader_policy"}),
        _rx(release={"rule": "timeout", "clear_s": 0.0}),
        _rx(range_m=-5.0),
        _rx(halt_scope="some"),
        "halt",
    ):
        with pytest.raises(ValueError):
            validate_convoy_spec({**base, "contact_reaction": bad})
    with pytest.raises(NotImplementedError):
        validate_convoy_spec({**base, "contact_reaction": _rx(action="disperse")})
    with pytest.raises(ValueError):
        validate_convoy_spec({**base, "security_ptype": 3})
    validate_convoy_spec({**base, "contact_reaction": _rx(), "security_ptype": "gun_truck"})


def test_flat_params_resolve():
    spec = resolve_convoy_spec({**SC.params, "contact_reaction": _rx(), "security_ptype": "ugv"})
    assert spec["security_ptype"] == "ugv" and resolve_contact_reaction(spec)["action"] == "halt"


def test_unknown_security_ptype_rejected():
    with pytest.raises(ValueError, match="security_ptype"):
        build_entities(SC.with_params({"security_ptype": "nope"}), make_rng(0, SC.id))


# ---- security ratio and platform ---------------------------------------------

@pytest.mark.parametrize("size,ratio,expected", [
    (5, 0.0, 0), (5, 0.33, 1), (5, 1.0, 3),
    (5, 0.5, 2),     # round(1.5) = 2 (half to even)
    (7, 0.5, 2),     # round(2.5) = 2 (half to even), not 3
    (9, 0.25, 2),    # round(1.75) = 2
])
def test_security_count_follows_ratio_rule(size, ratio, expected):
    """n_security = round(ratio * (march_unit_size - 2)) per march unit, Python half-to-even."""
    lay = build_convoy_layout({"march_unit_size": size, "march_units_per_serial": 2,
                               "serials_per_column": 1, "security_ratio": ratio})
    per_unit = (lay["convoy_role"][:size] == ROLE_SECURITY).sum()
    assert per_unit == expected
    assert (lay["convoy_role"] == ROLE_SECURITY).sum() == 2 * expected


def test_security_positions_follow_roles_list():
    roles = ["control", "security", "cargo", "security", "recovery"]
    lay = build_convoy_layout({"march_unit_size": 5, "march_units_per_serial": 2,
                               "serials_per_column": 1, "roles": roles})
    for u in range(2):
        assert (lay["convoy_role"][5 * u:5 * u + 5] == ROLE_SECURITY).nonzero()[0].tolist() == [1, 3]


def test_security_ptype_arms_only_security_vehicles():
    scn = _scenario_with_gun_truck()
    base = build_entities(scn, make_rng(0, scn.id))
    armed = build_entities(scn.with_params({"security_ptype": "gun_truck"}), make_rng(0, scn.id))
    sec = armed.convoy_role == ROLE_SECURITY
    assert sec.sum() == 3
    assert (armed.weapon_range[sec] == 900.0).all() and (armed.pk_base[sec] == 0.05).all()
    assert (armed.hp[sec] == 2.0).all()
    assert (base.weapon_range[sec] == 1200.0).all()
    assert (armed.weapon_range[~sec] == base.weapon_range[~sec]).all()
    assert (armed.pk_base[~sec] == base.pk_base[~sec]).all()


# ---- triggers (unit level, so each is tested in isolation) -------------------

def _convoy_state(triggers, **rx_kw):
    scn = SC.with_params({"contact_reaction": _rx(triggers=triggers, **rx_kw)})
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    ent.seen[:] = False
    return scn, ent, bhv


def _step(scn, ent, bhv, k, world=None):
    hold = np.zeros(ent.n, bool)
    behavior._update_contact(ent, bhv, scn, k, world, hold)
    return hold


def test_receive_fire_trigger():
    scn, ent, bhv = _convoy_state(["receive_fire"])
    assert not _step(scn, ent, bhv, 0).any() and not bhv.in_contact
    bhv.fired_at[3] = True
    hold = _step(scn, ent, bhv, 1)
    assert bhv.in_contact and bhv.contact_count == 1 and bhv.first_contact_step == 1
    assert hold[ent.convoy_role >= 0].all()


def test_receive_fire_ignores_red_being_shot():
    scn, ent, bhv = _convoy_state(["receive_fire"])
    red = int(np.nonzero(ent.side == RED)[0][0])
    bhv.fired_at[red] = True
    _step(scn, ent, bhv, 0)
    assert not bhv.in_contact


def test_lead_lost_trigger():
    scn, ent, bhv = _convoy_state(["lead_lost"])
    _step(scn, ent, bhv, 0)
    assert not bhv.in_contact
    ent.alive[bhv.heads[0]] = False
    _step(scn, ent, bhv, 1)
    assert bhv.in_contact
    # an event, not a state: the loss is not re-reported on the next tick
    bhv.in_contact, bhv.last_trigger_k = False, -1
    _step(scn, ent, bhv, 2)
    assert not bhv.in_contact


def test_detect_range_trigger_and_occlusion():
    scn, ent, bhv = _convoy_state(["detect_range"], range_m=500.0)
    red = int(np.nonzero(ent.side == RED)[0][0])
    veh = int(np.nonzero(ent.convoy_role >= 0)[0][0])
    ent.x[red], ent.y[red] = ent.x[veh] + 800.0, ent.y[veh]
    ent.seen[red] = True
    _step(scn, ent, bhv, 0)
    assert not bhv.in_contact                       # seen but out of range
    ent.x[red] = ent.x[veh] + 400.0
    ent.seen[red] = False
    _step(scn, ent, bhv, 1)
    assert not bhv.in_contact                       # in range but not detected
    ent.seen[red] = True
    _step(scn, ent, bhv, 2)
    assert bhv.in_contact

    scn, ent, bhv = _convoy_state(["detect_range"], range_m=500.0)
    ent.x[red], ent.y[red], ent.seen[red] = ent.x[veh] + 400.0, ent.y[veh], True

    class Blocked:
        buildings = object()

        @staticmethod
        def los(*_a):
            return False

    _step(scn, ent, bhv, 0, world=Blocked())
    assert not bhv.in_contact                       # a building blocks the line of sight


def test_reaction_draws_no_rng():
    scn, ent, bhv = _convoy_state(ALL_TRIGGERS)
    rng = make_rng(0, scn.id)
    before = rng.bit_generator.state
    bhv.fired_at[2] = True
    behavior.step(ent, bhv, None, None, scn, 0, rng)
    assert bhv.in_contact and rng.bit_generator.state == before


# ---- halt, release -----------------------------------------------------------

def test_halt_holds_column_then_times_out():
    scn, ent, bhv = _convoy_state(["receive_fire"], release={"rule": "timeout", "clear_s": 5.0})
    bhv.fired_at[3] = True
    assert _step(scn, ent, bhv, 0).any()
    bhv.fired_at[:] = False
    for k in range(1, 5):
        assert _step(scn, ent, bhv, k).any()        # still inside the 5 s window
    assert not _step(scn, ent, bhv, 5).any() and not bhv.in_contact
    bhv.fired_at[3] = True                          # a fresh trigger is a second contact
    _step(scn, ent, bhv, 6)
    assert bhv.contact_count == 2


def test_halt_scope_non_security_keeps_gun_trucks_moving():
    scn, ent, bhv = _convoy_state(["receive_fire"], halt_scope="non_security")
    bhv.fired_at[3] = True
    hold = _step(scn, ent, bhv, 0)
    sec = ent.convoy_role == ROLE_SECURITY
    assert not hold[sec].any() and hold[(ent.convoy_role >= 0) & ~sec].all()


def test_continue_is_the_control_arm():
    """`continue` counts contact and changes nothing physical."""
    for seed in range(3):
        base = run_mission(SC, seed=seed, params={})
        cont = run_mission(SC, seed=seed, params={"contact_reaction": _rx("continue")})
        assert cont["convoy_contact_count"] >= 1 and cont["convoy_halt_steps"] == 0
        for k in ("success", "time_to_objective", "blue_losses", "red_losses", "arrived"):
            assert cont[k] == base[k]


def test_never_triggered_reaction_matches_baseline():
    """A reaction whose trigger cannot fire reproduces the baseline run: nothing extra was drawn."""
    rx = _rx("halt", ["detect_range"], range_m=0.01)
    for seed in range(3):
        base = run_mission(SC, seed=seed, params={})
        out = run_mission(SC, seed=seed, params={"contact_reaction": rx})
        assert out["convoy_contact_count"] == 0
        for k in ("success", "time_to_objective", "blue_losses", "red_losses"):
            assert out[k] == base[k]


# ---- metrics and the comparison ----------------------------------------------

def test_escort_vehicle_steps_counts_living_gun_trucks():
    scn = _scenario_with_gun_truck(red_pk=0.0)       # no losses, so the count is exact
    out = run_mission(scn, seed=0, params={"security_ptype": "gun_truck"})
    assert out["blue_losses"] == 0 and out["success"] == 1.0
    assert out["escort_vehicle_steps"] == 3 * out["time_to_objective"] / scn.dt


def test_zero_escort_arm_reports_zero_cost():
    scn = _scenario_with_gun_truck()
    out = run_mission(scn, seed=0, params={"security_ptype": "gun_truck", "security_ratio": 0.0})
    assert out["escort_vehicle_steps"] == 0.0


def test_metric_keys_absent_when_off():
    out = run_mission(SC, seed=0, params={})
    assert not any(k.startswith("convoy_contact") or k == "escort_vehicle_steps" for k in out)


def test_reaction_is_not_dominated_by_construction():
    """Halt trades tempo for attrition; neither arm wins on both. If one did, the model would not be
    testing the reaction. The cost on the halting side is TIME only: Red does not exploit a halted
    column (no indirect fire or secondary devices are modelled), so a halt result must not be read
    as a finding about halting until that cost exists (see the plan, open question 3)."""
    seeds = range(4)
    cont = [run_mission(SC, seed=s, params={"contact_reaction": _rx("continue")}) for s in seeds]
    halt = [run_mission(SC, seed=s, params={"contact_reaction": _rx("halt")}) for s in seeds]
    mean = lambda rs, k: float(np.mean([r[k] for r in rs]))     # noqa: E731
    assert mean(halt, "blue_losses") < mean(cont, "blue_losses")
    assert mean(halt, "time_to_objective") > mean(cont, "time_to_objective")
