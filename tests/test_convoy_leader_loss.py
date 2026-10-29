"""Convoy leader-loss policy and halt release (Issue #17).

Opt-in via `convoy.leader_loss_policy`. Absent or `legacy`, every run is byte-identical.

These are POLICY VERIFICATION tests: each kill is forced at a chosen step through a patched
`behavior.step`, and in the halt tests Red is removed at a chosen step, so the result does not depend on
Red's aim or on a realistic engagement. They show that each policy does what it says. They are not
evidence about which policy is better; the matched multi-seed comparison under real engagements is
`tools/make_leader_loss_arms.py`.
"""
from __future__ import annotations

import numpy as np
import pytest

from dataclasses import replace

from conftest import same_run
from sandtable import behavior
from sandtable.convoy import resolve_contact_reaction, resolve_leader_loss, validate_convoy_spec
from sandtable.entities import BLUE, RED
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

SC = load_scenario("scenarios/uc3_convoy.json")
UNIT = {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1,
        "pace": 10.0, "time_gap": 4.0, "cargo_per_vehicle": 5.0}


CREWED_HEADS = {"control": 2, "cargo": 0, "security": 0, "recovery": 0}   # crew is zero unless declared


def _pol(policy, **kw):
    return {**UNIT, "leader_loss_policy": policy, **kw}


def _state(params):
    scn = SC.with_params(params)
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    return scn, ent, bhv


# The whole force must arrive, so a mission cannot end before a halted unit has had its chance.
FULL = replace(SC, objective=replace(SC.objective, survive_fraction=1.0))


def _run(params, kill_head_at=None, kill_red_at=None, seed=0, scn=SC, kill_cargo_at=None):
    """run_mission with the head of march unit 0 (and/or its first cargo truck) killed at a chosen
    step, and optionally all Red removed at another."""
    orig, seen = behavior.step, {}

    def patched(ent, bhv, op, comms, scn, k, rng, world=None):
        seen["bhv"], seen["ent"] = bhv, ent
        if k == kill_head_at:
            seen["head"] = int(np.nonzero(ent.march_unit == 0)[0][0])
            ent.alive[seen["head"]] = False
        if k == kill_cargo_at:
            idx = np.nonzero((ent.march_unit == 0) & (ent.convoy_role == 1))[0]
            seen["cargo_truck"] = int(idx[0])
            ent.alive[seen["cargo_truck"]] = False
        if k == kill_red_at:
            ent.alive[ent.side == RED] = False
        seen.setdefault("log", []).append((k, bhv.ll_halted.copy() if bhv.ll_halted is not None else None))
        return orig(ent, bhv, op, comms, scn, k, rng, world=world)

    behavior.step = patched
    try:
        r = run_mission(scn, seed=seed, params=params)
    finally:
        behavior.step = orig
    return r, seen


# ---- byte identity when off ---------------------------------------------------

def test_off_is_byte_identical():
    base = {**UNIT, "blue_behavior": "leader_follow"}
    for seed in range(4):
        a = run_mission(SC, seed=seed, params=base)
        b = run_mission(SC, seed=seed, params={**base, "leader_loss_policy": None})
        c = run_mission(SC, seed=seed, params={**base, "leader_loss_policy": "legacy"})
        assert same_run(a, b) and same_run(a, c)
        assert "leaderless_steps" not in c


def test_legacy_head_kill_matches_absent():
    base = {**UNIT, "blue_behavior": "leader_follow"}
    a, _ = _run(base, kill_head_at=20)
    b, _ = _run({**base, "leader_loss_policy": "legacy"}, kill_head_at=20)
    assert same_run(a, b)


# ---- validation ---------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"leader_loss_policy": "bogus"},
    {"leader_loss_policy": "promote", "handoff_steps": -1},
    {"leader_loss_policy": "promote", "handoff_steps": 1.5},
    {"leader_loss_policy": "halt", "handoff_steps": 3},
    {"leader_loss_policy": "continue", "halt_release": {"clear_steps": 5}},
    {"leader_loss_policy": "halt", "halt_release": {"clear_steps": 0}},
    {"leader_loss_policy": "halt", "halt_release": {"max_hold_steps": -2}},
    {"leader_loss_policy": "halt", "halt_release": {"other": 3}},
    {"handoff_steps": 3},
])
def test_validation_rejects(bad):
    with pytest.raises(ValueError):
        validate_convoy_spec({**UNIT, **bad})


def test_resolve_off_and_on():
    assert resolve_leader_loss({**UNIT}) is None
    assert resolve_leader_loss({**UNIT, "leader_loss_policy": "legacy"}) is None
    r = resolve_leader_loss({**UNIT, "leader_loss_policy": "halt", "halt_release": {"clear_steps": 4}})
    assert r == {"policy": "halt", "handoff_steps": 0, "clear_steps": 4, "max_hold_steps": None}


def test_policy_defaults_to_leader_follow():
    _, _, bhv = _state(_pol("promote"))
    assert bhv.mode == behavior.LEADER_FOLLOW and bhv.ll is not None


def test_leader_policy_release_needs_halt():
    rx = {"action": "halt", "triggers": ["receive_fire"], "release": {"rule": "leader_policy"}}
    with pytest.raises(ValueError):
        resolve_contact_reaction({**UNIT, "contact_reaction": rx})
    ok = resolve_contact_reaction({**UNIT, "contact_reaction": rx, "leader_loss_policy": "halt"})
    assert ok["release_rule"] == "leader_policy"


# ---- each policy, unit level --------------------------------------------------

def _tick(scn, ent, bhv, k):
    hold = np.zeros(ent.n, bool)
    behavior._update_leader_loss(ent, bhv, k, hold)
    return hold


def _unit0(ent):
    return np.nonzero(ent.march_unit == 0)[0]


def test_continue_everyone_drives_on():
    scn, ent, bhv = _state(_pol("continue"))
    u = _unit0(ent)
    ent.alive[u[0]] = False
    hold = _tick(scn, ent, bhv, 3)
    surv = u[1:]
    assert (ent.role[surv] == 0).all() and (ent.leader[surv] == -1).all()
    assert (bhv.state[surv] == behavior.WAYPOINT).all() and not hold.any()
    assert bhv.first_leader_loss_step == 3 and bhv.ll_handoffs == 0


def test_promote_instant():
    scn, ent, bhv = _state(_pol("promote"))
    u = _unit0(ent)
    ent.alive[u[0]] = False
    _tick(scn, ent, bhv, 5)
    assert ent.role[u[1]] == 0 and ent.leader[u[1]] == -1
    assert (ent.leader[u[2:]] == u[1]).all() and bhv.ll_handoffs == 1


def test_promote_latency():
    scn, ent, bhv = _state(_pol("promote", handoff_steps=3))
    u = _unit0(ent)
    ent.alive[u[0]] = False
    for k in range(3):
        _tick(scn, ent, bhv, k)
        assert ent.leader[u[1]] == u[0]          # still pointing at the dead head
    assert bhv.leaderless_steps == 3
    _tick(scn, ent, bhv, 3)
    assert ent.leader[u[1]] == -1 and bhv.ll_handoffs == 1 and bhv.ll_head[0] == u[1]


def test_promote_manned_only_without_crew_stays_headless():
    scn, ent, bhv = _state(_pol("promote", succession="manned_only", crew={"control": 0, "cargo": 0, "security": 0, "recovery": 0}))
    u = _unit0(ent)
    ent.alive[u[0]] = False
    _tick(scn, ent, bhv, 1)
    assert (ent.role[u[1:]] == 0).all() and bhv.ll_done[0] and bhv.ll_handoffs == 0
    _tick(scn, ent, bhv, 2)
    assert bhv.leaderless_steps >= 2


def test_absorb_joins_nearest_unit_in_serial():
    scn, ent, bhv = _state(_pol("absorb"))
    u0 = _unit0(ent)
    ent.alive[u0[0]] = False
    _tick(scn, ent, bhv, 2)
    surv = u0[1:]
    tgt = ent.leader[surv[0]]
    assert tgt in bhv.ll_head and tgt != u0[0] and ent.serial[tgt] == ent.serial[surv[0]]
    assert (ent.leader[surv] == tgt).all() and (ent.march_unit[surv] == ent.march_unit[tgt]).all()
    assert bhv.ll_handoffs == 1 and bhv.leaderless_steps == 0


def test_absorb_manned_only_skips_uncrewed_receiving_head():
    """Under manned_only the receiving head must be crewed. Unit 1's head is made unmanned; unit 2's
    stays crewed, so unit 0's survivors go to unit 2 even though unit 1 is nearer."""
    scn, ent, bhv = _state(_pol("absorb", succession="manned_only", crew=CREWED_HEADS))
    h1, h2 = int(bhv.ll_head[1]), int(bhv.ll_head[2])
    ent.crew[h1] = 0
    u = _unit0(ent)
    # make unit 1 strictly nearer than unit 2
    ent.x[u[1]], ent.y[u[1]] = ent.x[h1] + 5.0, ent.y[h1]
    ent.alive[u[0]] = False
    _tick(scn, ent, bhv, 1)
    assert (ent.leader[u[1:]] == h2).all() and bhv.ll_handoffs == 1


def test_absorb_manned_only_no_crewed_receiver_falls_back():
    scn, ent, bhv = _state(_pol("absorb", succession="manned_only", crew=CREWED_HEADS))
    for mu in (1, 2):
        ent.crew[int(bhv.ll_head[mu])] = 0
    u = _unit0(ent)
    ent.alive[u[0]] = False
    _tick(scn, ent, bhv, 1)
    assert (ent.role[u[1:]] == 0).all() and bhv.ll_done[0] and bhv.ll_handoffs == 0


def test_absorb_succession_any_may_use_uncrewed_head():
    scn, ent, bhv = _state(_pol("absorb", succession="any", crew=CREWED_HEADS))
    h1 = int(bhv.ll_head[1])
    ent.crew[h1] = 0
    u = _unit0(ent)
    ent.x[u[1]], ent.y[u[1]] = ent.x[h1] + 5.0, ent.y[h1]
    ent.alive[u[0]] = False
    _tick(scn, ent, bhv, 1)
    assert (ent.leader[u[1:]] == h1).all()


def test_absorb_without_neighbour_falls_back_to_continue():
    scn, ent, bhv = _state(_pol("absorb"))
    for mu in (1, 2):
        ent.alive[ent.march_unit == mu] = False
    u = _unit0(ent)
    ent.alive[u[0]] = False
    _tick(scn, ent, bhv, 1)
    assert (ent.role[u[1:]] == 0).all() and bhv.ll_done[0]


def test_halt_holds_unit_only_and_releases():
    scn, ent, bhv = _state(_pol("halt", halt_release={"max_hold_steps": 4}))
    u = _unit0(ent)
    ent.alive[u[0]] = False
    other = ent.march_unit == 1
    for k in range(3):
        hold = _tick(scn, ent, bhv, k)
        assert hold[u[1:]].all() and not hold[other].any()
    hold = _tick(scn, ent, bhv, 3)                   # 4th held step reaches max_hold_steps
    assert not hold.any() and not bhv.ll_halted[0]
    assert ent.leader[u[1]] == -1 and bhv.ll_handoffs == 1


def test_halt_release_by_clear_steps():
    scn, ent, bhv = _state(_pol("halt", halt_release={"clear_steps": 3}))
    u = _unit0(ent)
    red = int(np.nonzero(ent.side == RED)[0][0])
    ent.alive[u[0]] = False
    ent.alive[ent.side == RED] = False
    ent.alive[red] = True
    ent.weapon_range[red], ent.pk_base[red] = 500.0, 0.1
    ent.x[red], ent.y[red] = ent.x[u[1]] + 100.0, ent.y[u[1]]
    for k in range(5):
        assert _tick(scn, ent, bhv, k).any()         # shooter in range: clear count never builds
    ent.alive[red] = False
    for k in range(5, 7):
        assert _tick(scn, ent, bhv, k).any()
    assert not _tick(scn, ent, bhv, 7).any()         # third clear step releases


def test_halt_without_release_holds_forever():
    scn, ent, bhv = _state(_pol("halt"))
    u = _unit0(ent)
    ent.alive[u[0]] = False
    ent.alive[ent.side == RED] = False
    for k in range(200):
        assert _tick(scn, ent, bhv, k).any()


def test_no_rng_draws_without_a_loss():
    scn, ent, bhv = _state(_pol("promote", handoff_steps=2))
    for k in range(10):
        _tick(scn, ent, bhv, k)
    assert bhv.leaderless_steps == 0 and bhv.first_leader_loss_step == -1


# ---- full missions ------------------------------------------------------------

@pytest.mark.parametrize("policy", ["promote", "absorb", "halt", "continue"])
def test_head_kill_runs_and_reports(policy):
    r, seen = _run(_pol(policy), kill_head_at=15)
    assert r["first_leader_loss_step"] == 15.0
    assert "leaderless_steps" in r and "ll_handoffs" in r and "ll_halt_steps" in r
    if policy == "halt":
        assert r["ll_halt_steps"] > 0 and r["ll_handoffs"] == 0
    if policy in ("promote", "absorb"):
        assert r["ll_handoffs"] >= 1


def _cargo_dead_head(seen):
    ent = seen["ent"]
    return float(ent.cargo[seen["head"]] - ent.cargo_delivered[seen["head"]])


def test_paired_halt_vs_continue_cargo():
    halt, sh = _run(_pol("halt"), kill_head_at=15, kill_red_at=16, scn=FULL)
    cont, sc = _run(_pol("continue"), kill_head_at=15, kill_red_at=16, scn=FULL)
    assert halt["cargo_in_transit"] > 0
    assert halt["cargo_lost"] == pytest.approx(_cargo_dead_head(sh))
    assert cont["delivered_frac"] > halt["delivered_frac"]


def test_halt_release_resumes_delivery():
    p = _pol("halt")
    stuck, _ = _run(p, kill_head_at=15, kill_red_at=16, scn=FULL)
    freed, seen = _run({**p, "halt_release": {"clear_steps": 5}}, kill_head_at=15, kill_red_at=16, scn=FULL)
    assert freed["delivered_frac"] > stuck["delivered_frac"]
    # the halt is lifted within N steps of the last shooter dying
    released = [k for k, h in seen["log"] if k > 16 and h is not None and not h[0]]
    assert released and released[0] <= 16 + 5 + 2


# ---- cargo accounting ---------------------------------------------------------

def _balance(r, ent):
    blue = ent.side == BLUE
    loaded = float(ent.cargo[blue].sum())
    delivered = float(ent.cargo_delivered[blue].sum())
    assert loaded == pytest.approx(delivered + r["cargo_lost"] + r["cargo_in_transit"])


@pytest.mark.parametrize("policy", ["legacy", "promote", "absorb", "halt", "continue"])
def test_head_kill_does_not_mark_surviving_cargo_lost(policy):
    """The head is the control vehicle (no payload): losing it loses no cargo under any policy, and
    the survivors' payload stays in transit or is delivered."""
    r, seen = _run(_pol(policy, blue_behavior="leader_follow"), kill_head_at=15, kill_red_at=16, scn=FULL)
    ent = seen["ent"]
    assert ent.cargo[seen["head"]] == 0.0
    assert r["cargo_lost"] == 0.0
    assert r["cargo_in_transit"] + r["delivered_frac"] * float(ent.cargo[ent.side == BLUE].sum()) > 0
    _balance(r, ent)


@pytest.mark.parametrize("policy", ["legacy", "promote", "absorb", "halt", "continue"])
def test_cargo_truck_kill_loses_exactly_its_payload(policy):
    """Killing a loaded cargo truck (not the head) loses that truck's undelivered payload only, and
    is not a leader loss."""
    r, seen = _run(_pol(policy, blue_behavior="leader_follow"), kill_cargo_at=15, kill_red_at=16, scn=FULL)
    ent, i = seen["ent"], seen["cargo_truck"]
    assert ent.cargo[i] == 5.0 and ent.cargo_delivered[i] == 0.0
    assert r["cargo_lost"] == pytest.approx(5.0)
    assert r.get("first_leader_loss_step", -1.0) == -1.0
    _balance(r, ent)


def test_cargo_balance_closes_after_head_and_cargo_kill():
    r, seen = _run(_pol("continue"), kill_head_at=15, kill_cargo_at=16, kill_red_at=17, scn=FULL)
    ent = seen["ent"]
    blue = ent.side == BLUE
    loaded = float(ent.cargo[blue].sum())
    delivered = float(ent.cargo_delivered[blue].sum())
    assert loaded == pytest.approx(delivered + r["cargo_lost"] + r["cargo_in_transit"])
    assert r["cargo_lost"] == pytest.approx(5.0)
