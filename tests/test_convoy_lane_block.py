"""Physical lane blocking by destroyed vehicles (Issue #18, Change item 2).

Unit tests place vehicles by hand and call the blocking functions directly, so they depend on no enemy
fire. The mission tests force the kill through a patched `behavior.step` and remove Red, so nothing but the
wreck and the policies under test act on the column. See `src/sandtable/lane_block.py` for the contract.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import behavior, lane_block as lbk
from sandtable.entities import BLUE, RED
from sandtable.route import RoutePolyline
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

SC = load_scenario("scenarios/uc3_convoy.json")
CFG = {"recovery_time_s": 100.0, "standoff_m": 20.0}


def _state(cfg=None, route=None):
    scn = SC.with_params({"lane_blocking": cfg if cfg is not None else CFG})
    ent = build_entities(scn, make_rng(0, scn.id))
    world = type("W", (), {"route": route})()
    lb = lbk.build_lane_block(scn, ent, world)
    return scn, ent, lb


def _place(ent, spots):
    for i, (x, y) in spots.items():
        ent.x[i], ent.y[i] = x, y


def _targets(ent, ahead=400.0):
    return ent.x + ahead, ent.y.copy()


# ---- off state and validation ----------------------------------------------------

def test_off_is_byte_identical():
    for seed in range(4):
        a = run_mission(SC, seed=seed)
        for off in (None, "none"):
            assert same_run(a, run_mission(SC, seed=seed, params={"lane_blocking": off}))


def test_on_without_any_loss_changes_nothing_but_the_keys():
    """With no vehicle destroyed there is no wreck: outputs match bar the lane_ keys."""
    scn = SC.with_params({"duration": 30.0})
    a = run_mission(scn, seed=1)
    b = run_mission(scn, seed=1, params={"lane_blocking": CFG})
    assert a["blue_losses"] == 0.0
    assert same_run(a, {k: v for k, v in b.items() if not k.startswith("lane_")})
    assert b["lane_blockages"] == 0.0 and b["lane_first_block_step"] == -1.0


@pytest.mark.parametrize("bad", [
    {}, {"recovery_time_s": 10.0}, {"standoff_m": 5.0},
    {"recovery_time_s": 0, "standoff_m": 5.0}, {"recovery_time_s": 10.0, "standoff_m": -1},
    {"recovery_time_s": True, "standoff_m": 5.0},
    {"recovery_time_s": 10.0, "standoff_m": 5.0, "lane_width_m": 0},
    {"recovery_time_s": 10.0, "standoff_m": 5.0, "wreck_roles": []},
    {"recovery_time_s": 10.0, "standoff_m": 5.0, "wreck_roles": ["bogus"]},
    {"recovery_time_s": 10.0, "standoff_m": 5.0, "extra": 1},
])
def test_validation(bad):
    with pytest.raises(ValueError):
        lbk.resolve_lane_blocking({"lane_blocking": bad})


# ---- blockage begins, affects, ends ------------------------------------------------

def test_blocking_begins_the_tick_after_destruction_and_ends_after_recovery_time():
    scn, ent, lb = _state()
    _place(ent, {4: (1000.0, 1500.0)})
    ent.alive[4] = False
    lbk.update(ent, lb, 10, scn.dt)
    assert lb.blockages == 1
    assert not lbk.active(lb, 9, scn.dt) and lbk.active(lb, 10, scn.dt)
    assert lbk.active(lb, 109, scn.dt) and not lbk.active(lb, 110, scn.dt)       # 100 s later
    lbk.update(ent, lb, 11, scn.dt)
    assert lb.blockages == 1                                                    # one wreck, not one per tick


def test_vehicles_behind_stop_at_the_standoff_point_and_those_ahead_are_untouched():
    scn, ent, lb = _state()
    _place(ent, {4: (1000.0, 1500.0), 5: (700.0, 1500.0), 6: (990.0, 1500.0), 1: (1300.0, 1500.0)})
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    tx, ty = _targets(ent)
    before = (tx.copy(), ty.copy())
    lbk.apply(ent, lb, 0, scn.dt, tx, ty)
    s_w = lbk._coords(lb, np.array([1000.0]), np.array([1500.0]))[0][0]
    s_stop = s_w - 20.0
    assert lbk._coords(lb, tx[[5]], ty[[5]])[0][0] == pytest.approx(s_stop)     # 300 m behind: stops 20 m short
    assert tx[6] == pytest.approx(ent.x[6]) and ty[6] == pytest.approx(ent.y[6])  # inside the zone: holds, no reverse
    assert tx[1] == before[0][1] and ty[1] == before[1][1]                         # ahead of the wreck: unchanged
    assert lb.blocked_vehicle_steps >= 2 and lb.first_block_step == 0


def test_release_restores_the_original_targets():
    scn, ent, lb = _state()
    _place(ent, {4: (1000.0, 1500.0), 5: (700.0, 1500.0)})
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    tx, ty = _targets(ent)
    ref = tx.copy()
    lbk.apply(ent, lb, 100, scn.dt, tx, ty)                                    # t = 100 s: released
    assert (tx == ref).all() and lb.block_steps == 0


def test_lane_width_limits_which_vehicles_are_blocked():
    scn, ent, lb = _state({**CFG, "lane_width_m": 10.0})
    _place(ent, {4: (1000.0, 1500.0), 5: (700.0, 1500.0), 6: (700.0, 1560.0)})   # 6 is 60 m off the wreck's lane
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    tx, ty = _targets(ent)
    ref = tx.copy()
    lbk.apply(ent, lb, 0, scn.dt, tx, ty)
    assert tx[5] != ref[5] and tx[6] == ref[6]
    scn2, ent2, lb2 = _state(CFG)                                               # null width: the whole road
    _place(ent2, {4: (1000.0, 1500.0), 5: (700.0, 1500.0), 6: (700.0, 1560.0)})
    ent2.alive[4] = False
    lbk.update(ent2, lb2, 0, scn.dt)
    tx2, ty2 = _targets(ent2)
    lbk.apply(ent2, lb2, 0, scn.dt, tx2, ty2)
    assert tx2[5] != ref[5] and tx2[6] != ref[6]


def test_wreck_roles_filter_and_red_wrecks_block_nothing():
    scn, ent, lb = _state({**CFG, "wreck_roles": ["security"]})
    assert ent.convoy_role[4] == 3 and ent.convoy_role[3] == 2                  # recovery, security
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    assert lb.blockages == 0
    ent.alive[3] = False
    lbk.update(ent, lb, 1, scn.dt)
    assert lb.blockages == 1
    red = int(np.nonzero(ent.side == RED)[0][0])
    ent.alive[red] = False
    lbk.update(ent, lb, 2, scn.dt)
    assert lb.blockages == 1


def test_route_based_world_uses_arc_length():
    route = RoutePolyline.from_waypoints([(0.0, 1500.0), (2000.0, 1500.0), (2000.0, 2500.0)])
    scn, ent, lb = _state(route=route)
    _place(ent, {4: (2000.0, 1800.0), 5: (1500.0, 1500.0), 1: (2000.0, 2200.0)})  # wreck at s = 2300 on the 2nd leg
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    assert lb.wrecks[0].s == pytest.approx(2300.0)
    tx, ty = _targets(ent)
    tx[5], ty[5] = 2000.0, 2400.0                                              # carrot beyond the wreck
    keep = (tx[1], ty[1])
    lbk.apply(ent, lb, 0, scn.dt, tx, ty)
    assert (tx[5], ty[5]) == pytest.approx((2000.0, 1500.0 + (2280.0 - 2000.0)))   # s = 2280 on the second leg
    assert (tx[1], ty[1]) == keep                                              # s = 2700 is ahead of the wreck


# ---- missions: forced kill, Red removed --------------------------------------------

FREE = {"blue_behavior": "waypoint"}


def _run(params, kill_at=20, scn=SC, victim=0):
    orig = behavior.step

    def patched(ent, bhv, op, comms, scn_, k, rng, world=None):
        if k == 0:
            ent.alive[ent.side == RED] = False                                # nothing but the wreck acts
        if k == kill_at:
            ent.alive[victim] = False                                         # the lead vehicle by default
        return orig(ent, bhv, op, comms, scn_, k, rng, world=world)

    behavior.step = patched
    try:
        return run_mission(scn, seed=0, params={**FREE, **params})
    finally:
        behavior.step = orig


def test_a_wreck_in_front_holds_the_column_for_the_recovery_time():
    free = _run({})
    held = _run({"lane_blocking": {"recovery_time_s": 200.0, "standoff_m": 20.0}})
    assert free["success"] == held["success"] == 1.0
    assert held["time_to_objective"] - free["time_to_objective"] >= 150.0
    assert held["lane_blockages"] == 1.0 and held["lane_block_steps"] == 200.0
    assert held["lane_blocked_vehicle_steps"] > 0 and held["lane_first_block_step"] == 20.0


def test_longer_recovery_holds_longer():
    t = [_run({"lane_blocking": {"recovery_time_s": r, "standoff_m": 20.0}})["time_to_objective"] for r in (50.0, 200.0)]
    assert t[1] - t[0] >= 100.0


def test_contact_halt_and_lane_block_are_separate_and_both_must_clear():
    """A #12 halt ends on its own timeout; the wreck stays until its recovery time. Different counters."""
    p = {"lane_blocking": {"recovery_time_s": 200.0, "standoff_m": 20.0},
         "contact_reaction": {"action": "halt", "triggers": ["lead_lost"], "release": {"rule": "timeout", "clear_s": 15.0}}}
    r = _run(p)
    assert 0 < r["convoy_halt_steps"] < 15 * 20                               # about 15 s of a 15-vehicle column
    assert r["lane_block_steps"] == 200.0                                      # the halt's release did not clear the wreck
    assert r["lane_blocked_vehicle_steps"] > 0
    assert r["time_to_objective"] - _run({})["time_to_objective"] >= 150.0


@pytest.mark.parametrize("policy", [
    {"leader_loss_policy": "halt", "halt_release": {"max_hold_steps": 30}},
    {"leader_loss_policy": "continue"},
    {"leader_loss_policy": "promote", "handoff_steps": 5},
])
def test_leader_loss_policies_do_not_clear_or_ignore_the_wreck(policy):
    r = _run({**policy, "lane_blocking": {"recovery_time_s": 200.0, "standoff_m": 20.0}})
    assert r["lane_block_steps"] == 200.0 and r["lane_blocked_vehicle_steps"] > 0
    assert r["first_leader_loss_step"] == 20.0
    assert r["time_to_objective"] - _run({**policy})["time_to_objective"] >= 100.0
    if policy["leader_loss_policy"] == "halt":
        assert 0 < r["ll_halt_steps"] <= 30 * 5 * 1.0 + 1                     # the policy halt ended at 30 s; the wreck did not


def test_cargo_is_conserved_when_a_loaded_truck_is_the_wreck():
    p = {"lane_blocking": {"recovery_time_s": 100.0, "standoff_m": 20.0}, "cargo_per_vehicle": 5.0}
    r = _run(p, kill_at=20, victim=1)                                          # vehicle 1 is a cargo truck
    scn = SC.with_params(p)
    ent = build_entities(scn, make_rng(0, scn.id))
    loaded = float(ent.cargo[ent.side == BLUE].sum())
    assert ent.cargo[1] == 5.0 and r["cargo_lost"] == pytest.approx(5.0)
    assert loaded == pytest.approx(r["delivered_frac"] * loaded + r["cargo_lost"] + r["cargo_in_transit"])


# ---- audit: geometry, several wrecks, holds, scope -------------------------------

class _FlatWorld:
    """Just enough world for `motion.step`: no terrain slowdown."""

    def speed_at(self, x, y):
        return np.ones_like(x, dtype=float)


def _drive(ent, lb, scn, dt, ticks=1):
    """Planning's lane step followed by motion, for the Blue ground vehicles, with a far carrot."""
    from sandtable import motion
    for k in range(ticks):
        tx, ty = _targets(ent, 5000.0)
        lbk.apply(ent, lb, k, dt, tx, ty)
        ent.tgt_x, ent.tgt_y = tx, ty
        motion.step(ent, _FlatWorld(), dt)


@pytest.mark.parametrize("dt", [1.0, 10.0, 100.0])
def test_a_vehicle_cannot_cross_an_active_wreck_in_one_large_timestep(dt):
    scn, ent, lb = _state({"recovery_time_s": 1.0e6, "standoff_m": 20.0})
    ent.alive[:] = False
    ent.alive[[4, 5]] = True
    lb.prev_alive = ent.alive.copy()                 # only vehicles 4 and 5 exist for this test
    _place(ent, {4: (1000.0, 1500.0), 5: (700.0, 1500.0)})
    ent.heading[:] = 0.0
    ent.alive[4] = False
    lbk.update(ent, lb, 0, dt)
    s_w = lb.wrecks[0].s
    _drive(ent, lb, scn, dt, ticks=4)               # 12 m/s x 100 s would be 1200 m without the stand-off
    s, _ = lbk._coords(lb, ent.x[[5]], ent.y[[5]])
    assert s[0] <= s_w - 20.0 + 1e-6


def test_a_vehicle_cannot_cross_a_wreck_beyond_a_route_bend_in_one_step():
    route = RoutePolyline.from_waypoints([(0.0, 1500.0), (1000.0, 1500.0), (1000.0, 2500.0)])
    scn, ent, lb = _state({"recovery_time_s": 1.0e6, "standoff_m": 20.0}, route=route)
    ent.alive[:] = False
    ent.alive[[4, 5]] = True
    lb.prev_alive = ent.alive.copy()
    _place(ent, {4: (1000.0, 1900.0), 5: (900.0, 1500.0)})   # wreck at s = 1400 on the second leg
    ent.alive[4] = False
    lbk.update(ent, lb, 0, 50.0)
    ent.heading[:] = 0.0
    _drive(ent, lb, scn, 50.0, ticks=6)
    s, _ = route.project(ent.x[[5]], ent.y[[5]])
    assert s[0] <= lb.wrecks[0].s - 20.0 + 1.0


def test_clearing_one_wreck_does_not_release_vehicles_still_blocked_by_another():
    scn, ent, lb = _state({"recovery_time_s": 100.0, "standoff_m": 20.0})
    _place(ent, {4: (1500.0, 1500.0), 3: (1000.0, 1500.0), 5: (600.0, 1500.0)})
    lb.wrecks = [lbk.Wreck(lbk._coords(lb, np.array([1500.0]), np.array([1500.0]))[0][0], 0.0, 0.0, 50.0),    # far wreck, clears first
                 lbk.Wreck(lbk._coords(lb, np.array([1000.0]), np.array([1500.0]))[0][0], 0.0, 0.0, 200.0)]  # near wreck
    ent.alive[[3, 4]] = False
    s_near = lb.wrecks[1].s
    s_far = lb.wrecks[0].s

    def stop_s(k):
        tx, ty = _targets(ent, 5000.0)
        lbk.apply(ent, lb, k, 1.0, tx, ty)
        return lbk._coords(lb, tx[[5]], ty[[5]])[0][0]
    assert stop_s(10) == pytest.approx(s_near - 20.0)             # both active: the nearer one stops it
    assert stop_s(60) == pytest.approx(s_near - 20.0)             # the far wreck cleared; the near one still holds
    assert stop_s(250) > s_far                                    # both cleared: the carrot is untouched
    # the other order: the near wreck clears first, the far one then holds
    lb.wrecks[1].t_end, lb.wrecks[0].t_end = 50.0, 200.0
    assert stop_s(10) == pytest.approx(s_near - 20.0)
    assert stop_s(60) == pytest.approx(s_far - 20.0)


def test_release_changes_no_behavior_hold():
    """Neither `update` nor `apply` can see or write the behavior state: contact and leader-loss holds
    are exactly as they were before the wreck, while it is active and after it clears."""
    params = {"lane_blocking": CFG, "leader_loss_policy": "halt", "blue_behavior": "leader_follow",
              "contact_reaction": {"action": "halt", "triggers": ["lead_lost"], "release": {"rule": "timeout", "clear_s": 15.0}}}
    scn = SC.with_params(params)
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    lb = lbk.build_lane_block(scn, ent, type("W", (), {"route": None})())
    ent.alive[0] = False                                         # a head: both holds engage
    hold = np.zeros(ent.n, bool)
    behavior._update_leader_loss(ent, bhv, 0, hold)
    snap = (bhv.ll_halted.copy(), hold.copy(), bhv.holding.copy(), bhv.in_contact)
    for k in (0, 50, 99, 100, 150):                              # before, during and after the 100 s wreck
        lbk.update(ent, lb, k, scn.dt)
        tx, ty = _targets(ent)
        lbk.apply(ent, lb, k, scn.dt, tx, ty)
        assert (bhv.ll_halted == snap[0]).all() and (bhv.holding == snap[2]).all() and bhv.in_contact == snap[3]
    assert hold.any() and bhv.ll_halted[0]                       # the halt is still on; the wreck did not end it


def test_lane_width_uses_signed_lateral_offsets_on_both_sides():
    scn, ent, lb = _state({**CFG, "lane_width_m": 10.0})                  # half width 5 m
    _place(ent, {4: (1000.0, 1500.0), 5: (700.0, 1504.5), 6: (700.0, 1495.5), 7: (700.0, 1505.5), 8: (700.0, 1494.5)})
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    tx, ty = _targets(ent)
    ref = tx.copy()
    lbk.apply(ent, lb, 0, scn.dt, tx, ty)
    assert tx[5] != ref[5] and tx[6] != ref[6]                             # 4.5 m either side: inside
    assert tx[7] == ref[7] and tx[8] == ref[8]                             # 5.5 m either side: outside


def test_no_wreck_role_filter_means_every_destroyed_vehicle_blocks():
    scn, ent, lb = _state(CFG)
    ent.alive[[0, 3, 4]] = False                                 # control, security, recovery
    lbk.update(ent, lb, 0, scn.dt)
    assert lb.blockages == 3


class _NoGraphWorld:
    """A world whose street graph must never be read."""
    route = None

    @property
    def street_graph(self):
        raise AssertionError("lane blocking must not consult the street graph")


def test_the_street_graph_is_never_read():
    scn = SC.with_params({"lane_blocking": CFG})
    ent = build_entities(scn, make_rng(0, scn.id))
    lb = lbk.build_lane_block(scn, ent, _NoGraphWorld())
    _place(ent, {4: (1000.0, 1500.0), 5: (700.0, 1500.0)})
    ent.alive[4] = False
    lbk.update(ent, lb, 0, scn.dt)
    tx, ty = _targets(ent)
    lbk.apply(ent, lb, 0, scn.dt, tx, ty)


def test_timing_metrics_mark_creation_and_release():
    r = _run({"lane_blocking": {"recovery_time_s": 200.0, "standoff_m": 20.0}})
    assert r["lane_first_block_step"] == 20.0 and r["lane_last_release_step"] == 220.0


def test_a_late_blocked_mission_never_passes_the_wreck_while_it_is_active():
    """End to end at dt = 10 s: record every tick; no living Blue vehicle behind the wreck gets past it."""
    import json
    from pathlib import Path
    from sandtable.scenario import Scenario
    d = json.loads(Path("scenarios/uc3_convoy.json").read_text())
    d["dt"], d["duration"] = 10.0, 1800.0
    scn10 = Scenario.from_dict(d)
    seen = {}
    orig = behavior.step

    def spy(ent, bhv, op, comms, scn_, k, rng, world=None):
        if k == 0:
            ent.alive[ent.side == RED] = False
        if k == 3:
            ent.alive[0] = False
        if k > 3 and "lb" in seen and 3 <= k < 3 + 20:           # 200 s recovery
            w = seen["lb"].wrecks
            if w:
                s, _ = lbk._coords(seen["lb"], ent.x, ent.y)
                behind = (ent.side == BLUE) & ent.alive & (np.arange(ent.n) != 0)
                behind &= s < w[0].s
                seen.setdefault("viol", []).extend(np.nonzero(behind & (s > w[0].s - 20.0 + 1e-6))[0].tolist())
        return orig(ent, bhv, op, comms, scn_, k, rng, world=world)

    orig_build = lbk.build_lane_block

    def build(*a, **kw):
        seen["lb"] = orig_build(*a, **kw)
        return seen["lb"]
    behavior.step, lbk.build_lane_block = spy, build
    try:
        r = run_mission(scn10, seed=0, params={**FREE, "lane_blocking": {"recovery_time_s": 200.0, "standoff_m": 20.0}})
    finally:
        behavior.step, lbk.build_lane_block = orig, orig_build
    assert r["lane_blockages"] == 1.0 and not seen.get("viol")
