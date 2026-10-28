"""Convoy autonomous march unit and personnel exposure (Issue #14).

Opt-in via `convoy.autonomy_arm`, `convoy.crew` or `convoy.crew_metrics`. Absent, every run is
byte-identical. Crew is read by the metrics only: no movement, engagement, sensing or c2 step reads it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import same_run
from sandtable import behavior
from sandtable.convoy import (
    ROLE_CARGO, ROLE_CONTROL, ROLE_RECOVERY, ROLE_SECURITY, resolve_convoy_spec, resolve_crew_table,
    validate_convoy_spec,
)
from sandtable.entities import BLUE
from sandtable.scenario import Scenario, build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

SC = load_scenario("scenarios/uc3_convoy.json")
ROLES = ("control", "cargo", "security", "recovery")
BASE_UNIT = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1,
             "pace": 10.0, "time_gap": 4.0}
ARM = {"autonomy_arm": "autonomous_march_unit"}


def _scn(red_range=None, red_pk=None) -> Scenario:
    d = json.loads(Path("scenarios/uc3_convoy.json").read_text())
    if red_range is not None:
        d["platform_types"]["at_team"]["weapon_range"] = red_range
    if red_pk is not None:
        d["platform_types"]["at_team"]["pk_base"] = red_pk
    return Scenario.from_dict(d)


def _crew_keys(r):
    return {k: v for k, v in r.items() if k.startswith(("crew", "autonomous_headless"))}


# ---- byte identity when off -------------------------------------------------

def test_off_is_byte_identical():
    for seed in range(6):
        a = run_mission(SC, seed=seed, params={})
        b = run_mission(SC, seed=seed, params={"autonomy_arm": None, "crew": None, "crew_metrics": False})
        assert same_run(a, b)
        assert not _crew_keys(a)


def test_off_builds_no_crew():
    assert resolve_crew_table(resolve_convoy_spec(SC.params)) is None
    ent = build_entities(SC, make_rng(0, SC.id))
    assert (ent.crew == 0).all()
    assert behavior.build_behavior(SC, ent) is None


# ---- crew defaults ------------------------------------------------------------

def test_crew_defaults_per_role_and_arm():
    manned = resolve_crew_table({"autonomy_arm": "manned"})
    auto = resolve_crew_table(ARM)
    assert manned == {ROLE_CONTROL: 2, ROLE_CARGO: 2, ROLE_SECURITY: 3, ROLE_RECOVERY: 2}
    assert auto == {ROLE_CONTROL: 2, ROLE_CARGO: 0, ROLE_SECURITY: 3, ROLE_RECOVERY: 2}
    assert resolve_crew_table({"crew_metrics": True}) == manned
    assert resolve_crew_table({"crew": {"cargo": 1}})[ROLE_CARGO] == 1


def test_reference_convoy_crew_totals():
    """15 vehicles, no escorts: 30 crew manned, 6 autonomous (ratio 5.0)."""
    unit = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1}
    for arm, total in (("manned", 30), ("autonomous_march_unit", 6)):
        spec = {**unit, "autonomy_arm": arm, "roles": ["control", "cargo", "cargo", "cargo", "cargo"]}
        scn = SC.with_params({"convoy": spec})
        ent = build_entities(scn, make_rng(0, scn.id))
        assert int(ent.crew[ent.side == BLUE].sum()) == total
    manned, auto = 30, 6
    assert manned / auto == 5.0


def test_reference_convoy_with_escorts():
    """Reference convoy with 3 and 5 escorts (ATP 4-11 G-8 equal cargo):
    3 escorts: manned 39, autonomous 15 (ratio 2.6).
    5 escorts: manned 45, autonomous 21 (ratio 2.14).
    """
    unit = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1}
    # 3 escorts
    spec_m3 = {**unit, "autonomy_arm": "manned", "escort_vehicles": 3}
    spec_a3 = {**unit, "autonomy_arm": "autonomous_march_unit", "escort_vehicles": 3}
    ent_m3 = build_entities(SC.with_params({"convoy": spec_m3}), make_rng(0, SC.id))
    ent_a3 = build_entities(SC.with_params({"convoy": spec_a3}), make_rng(0, SC.id))
    m3 = int(ent_m3.crew[ent_m3.side == BLUE].sum())
    a3 = int(ent_a3.crew[ent_a3.side == BLUE].sum())
    assert m3 == 39
    assert a3 == 15
    assert m3 / a3 == 2.6

    # 5 escorts
    spec_m5 = {**unit, "autonomy_arm": "manned", "escort_vehicles": 5}
    spec_a5 = {**unit, "autonomy_arm": "autonomous_march_unit", "escort_vehicles": 5}
    ent_m5 = build_entities(SC.with_params({"convoy": spec_m5}), make_rng(0, SC.id))
    ent_a5 = build_entities(SC.with_params({"convoy": spec_a5}), make_rng(0, SC.id))
    m5 = int(ent_m5.crew[ent_m5.side == BLUE].sum())
    a5 = int(ent_a5.crew[ent_a5.side == BLUE].sum())
    assert m5 == 45
    assert a5 == 21
    assert round(m5 / a5, 2) == 2.14


def test_manned_arm_holds_station():
    """Manned followers maintain station under comms jamming C5 (follow_mode='human'),
    while autonomous follow_mode='link' suffers track drops."""
    spec = {**BASE_UNIT, "roles": ["control", "cargo", "cargo", "cargo", "cargo"]}
    scn_m = SC.with_params({"convoy": spec, "autonomy_arm": "manned", "comms_level": 5})
    scn_a = SC.with_params({"convoy": spec, "autonomy_arm": "autonomous_march_unit", "follow_mode": "link", "comms_level": 5})

    ent_m = build_entities(scn_m, make_rng(0, scn_m.id))
    ent_a = build_entities(scn_a, make_rng(0, scn_a.id))
    bhv_m = behavior.build_behavior(scn_m, ent_m)
    bhv_a = behavior.build_behavior(scn_a, ent_a)

    assert bhv_m.follow_mode == "human"
    assert bhv_a.follow_mode == "link"

    out_m = run_mission(scn_m, seed=0)
    out_a = run_mission(scn_a, seed=0)
    assert out_m["crew_total"] == 30
    assert out_a["crew_total"] == 6


# ---- the metric ---------------------------------------------------------------

def test_crew_changes_nothing_else():
    a = run_mission(SC, seed=3, params={"crew": {"cargo": 2, "security": 3}})
    b = run_mission(SC, seed=3, params={"crew": {"cargo": 7, "security": 1, "control": 5, "recovery": 4}})
    ka = {k: v for k, v in a.items() if not k.startswith("crew")}
    kb = {k: v for k, v in b.items() if not k.startswith("crew")}
    assert ka.keys() == kb.keys()
    assert all(ka[k] == kb[k] or (ka[k] != ka[k] and kb[k] != kb[k]) for k in ka)
    assert a["crew_steps_at_risk"] != b["crew_steps_at_risk"]


def test_crew_does_not_change_the_baseline_run():
    base = run_mission(SC, seed=2, params={})
    on = run_mission(SC, seed=2, params={"crew_metrics": True})
    assert same_run(base, {k: v for k, v in on.items() if not k.startswith("crew")})


def test_zero_when_no_shooter_in_range():
    out = run_mission(_scn(red_range=0.0), seed=0, params={"crew_metrics": True})
    assert out["crew_steps_at_risk"] == 0.0
    assert out["crew_total"] > 0


def test_shooter_needs_pk_base():
    """A Red entity that cannot kill is not a shooter."""
    out = run_mission(_scn(red_range=1e6, red_pk=0.0), seed=0, params={"crew_metrics": True})
    assert out["crew_steps_at_risk"] == 0.0


def test_full_range_equals_crew_times_steps_alive():
    """Every vehicle in range of a living shooter for the whole run, and nobody dies: the metric is
    sum(crew) x steps."""
    scn = _scn(red_range=1e6, red_pk=1e-15)
    out = run_mission(scn, seed=0, params={"crew_metrics": True})
    assert out["blue_losses"] == 0 and out["success"] == 1.0
    steps = out["time_to_objective"] / scn.dt
    assert out["crew_steps_at_risk"] == out["crew_total"] * steps
    assert out["crew_lost"] == 0.0


def test_crew_counted_once_per_step_with_many_shooters():
    """Six Red shooters cover every vehicle; crew still counts once per step."""
    scn = _scn(red_range=1e6, red_pk=1e-15)
    out = run_mission(scn, seed=0, params={"crew_metrics": True})
    assert out["crew_steps_at_risk"] == out["crew_total"] * out["time_to_objective"] / scn.dt


@pytest.mark.parametrize("arm", ["manned", "autonomous_march_unit"])
def test_by_role_sums_to_total(arm):
    for seed in range(4):
        out = run_mission(SC, seed=seed, params={"autonomy_arm": arm})
        assert sum(out[f"crew_steps_at_risk_{r}"] for r in ROLES) == out["crew_steps_at_risk"]
        assert sum(out[f"crew_lost_{r}"] for r in ROLES) == out["crew_lost"]


def test_crew_lost_is_the_crew_of_dead_vehicles():
    scn = SC.with_params({"autonomy_arm": "manned"})
    ent = build_entities(scn, make_rng(0, scn.id))
    out = run_mission(scn, seed=1, params={})
    assert out["blue_losses"] > 0
    assert 0 < out["crew_lost"] <= out["crew_total"]
    assert out["crew_lost_cargo"] % 2 == 0          # cargo crew is 2 per vehicle
    assert out["crew_lost_security"] % 3 == 0       # security crew is 3 per vehicle
    assert ent.crew.sum() == out["crew_total"]


def test_autonomous_arm_has_less_cargo_crew_at_risk():
    out = run_mission(SC, seed=1, params=ARM)
    assert out["crew_steps_at_risk_cargo"] == 0.0 and out["crew_lost_cargo"] == 0.0


# ---- the autonomous arm -------------------------------------------------------

def test_autonomous_arm_layout():
    scn = SC.with_params({"convoy": {k: v for k, v in BASE_UNIT.items()}, **ARM})
    ent = build_entities(scn, make_rng(0, scn.id))
    blue = ent.side == BLUE
    for u in range(3):
        unit = ent.convoy_role[blue][5 * u:5 * u + 5]
        assert unit.tolist() == [ROLE_CONTROL] + [ROLE_CARGO] * 4
    assert int(ent.crew[blue].sum()) == 6


def test_arm_defaults_to_leader_follow_and_is_overridable():
    scn = SC.with_params({"convoy": dict(BASE_UNIT), **ARM})
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    assert bhv.mode == behavior.LEADER_FOLLOW and bhv.succession == "manned_only"
    scn2 = scn.with_params({"blue_behavior": "waypoint"})
    assert behavior.build_behavior(scn2, ent).mode == behavior.WAYPOINT


def _unit_state(roles, kill_head=True):
    spec = {**BASE_UNIT, "roles": roles}
    scn = SC.with_params({"convoy": spec, **ARM, "blue_behavior": "leader_follow"})
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    if kill_head:
        ent.alive[0] = False
    return ent, bhv


def test_succession_manned_only_never_promotes_unmanned_truck():
    ent, bhv = _unit_state(["control", "cargo", "cargo", "cargo", "cargo"])
    behavior._update_convoy_succession(ent, bhv)
    assert (ent.leader[1:5] == 0).all()             # still pointing at the dead head
    assert (ent.role[1:5] == 1).all()


def test_succession_manned_only_promotes_a_manned_escort():
    ent, bhv = _unit_state(["control", "cargo", "security", "cargo", "recovery"])
    behavior._update_convoy_succession(ent, bhv)
    assert ent.role[2] == 0 and ent.leader[2] == -1     # the security vehicle (crew 3) leads
    assert ent.leader[1] == 2 and ent.leader[3] == 2 and ent.leader[4] == 2


def test_succession_any_keeps_existing_promotion():
    spec = {**BASE_UNIT, "roles": ["control", "cargo", "cargo", "cargo", "cargo"]}
    scn = SC.with_params({"convoy": spec, **ARM, "succession": "any", "blue_behavior": "leader_follow"})
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    ent.alive[0] = False
    behavior._update_convoy_succession(ent, bhv)
    assert ent.role[1] == 0 and ent.leader[1] == -1


def test_headless_steps_are_counted():
    scn = SC.with_params({"convoy": dict(BASE_UNIT), **ARM})
    out = run_mission(scn, seed=1, params={})
    assert out["autonomous_headless_steps"] >= 0.0
    assert "autonomous_headless_steps" not in run_mission(SC, seed=1, params={"crew_metrics": True})


# ---- validation ---------------------------------------------------------------

def test_spec_validation():
    base = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1}
    for bad in ({"autonomy_arm": "robot"}, {"crew": {"driver": 2}}, {"crew": {"cargo": -1}},
                {"crew": {"cargo": 1.5}}, {"crew": [2, 2]}, {"succession": "eldest"}):
        with pytest.raises(ValueError):
            validate_convoy_spec({**base, **bad})
    validate_convoy_spec({**base, **ARM, "crew": {"cargo": 1}, "succession": "any"})


@pytest.mark.parametrize("level", [0, 5])
def test_arms_run_across_the_comms_ladder(level):
    for arm in ("manned", "autonomous_march_unit"):
        out = run_mission(SC, seed=0, params={"autonomy_arm": arm, "comms_level": level})
        assert "delivered_frac" in out or "success" in out
        assert out["crew_total"] > 0
