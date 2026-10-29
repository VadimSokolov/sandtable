"""One console per march unit and the attention term (Issue #19).

The unit tests drive `c2.step` directly with a constant random source, so every result is deterministic and
none depends on enemy fire or on the stochastic comms draws. The few full missions check the acceptance
cases of the issue on a constructed march unit with no Red shooter.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from conftest import same_run
from sandtable import behavior, c2, c2_units
from sandtable.comms_ew import build_comms
from sandtable.entities import BLUE
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

SC = load_scenario("scenarios/uc3_convoy.json")


class ConstRNG:
    """Deterministic stand-in: no message is ever dropped and every jittered interval is its lower bound."""

    def random(self, size=None):
        return 0.999 if size is None else np.full(size, 0.999)

    def integers(self, lo, hi=None, size=None):
        return lo if size is None else np.full(size, lo)


def params(units=3, level=0, **extra):
    p = {"control_mode": "direct", "autonomy_arm": "autonomous_march_unit", "console_per_march_unit": {},
         "comms_level": level, "cargo_per_vehicle": 5.0,
         "convoy": {"march_unit_size": 5, "march_units_per_serial": units, "serials_per_column": 1,
                    "pace": 10.0, "time_gap": 4.0}}
    p.update(extra)
    return p


def build(units=3, level=0, **extra):
    scn = SC.with_params(params(units, level, **extra))
    ent = build_entities(scn, make_rng(0, scn.id))
    return scn, ent, c2.build_c2(scn, ent, ConstRNG()), build_comms(scn)


def drive(scn, ent, op, comms, steps, bhv=None, start=0):
    rng = ConstRNG()
    for k in range(start, start + steps):
        c2.step(ent, op, comms, scn, k, rng, None, bhv=bhv)


# ---- the current attention term (what the issue says it is) ---------------------

def test_existing_attention_term_counts_every_blue_entity_and_ignores_n_operators():
    """Published model, no per-unit consoles: attention = min(1, span_capacity / ALL Blue entities), fixed at build."""
    for n_ops in (1, 3):
        scn = SC.with_params({"control_mode": "direct", "n_operators": n_ops,
                              "convoy": {"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1}})
        ent = build_entities(scn, make_rng(0, scn.id))
        op = c2.build_c2(scn, ent, ConstRNG())
        n_blue = int((ent.side == BLUE).sum())
        assert n_blue == 15 and op.units is None
        attention = min(1.0, 4.0 / n_blue)
        assert op.q_operator == pytest.approx(0.70 + (0.95 - 0.70) * attention)    # 0.7667 for 15 vehicles


# ---- off state and validation ----------------------------------------------------

def test_off_is_byte_identical():
    base = {k: v for k, v in params().items() if k != "console_per_march_unit"}
    for seed in range(3):
        a = run_mission(SC, seed=seed, params=base)
        for off in (None, False, "none"):
            b = run_mission(SC, seed=seed, params={**base, "console_per_march_unit": off})
            assert same_run(a, b)
        assert not any(k.startswith("c2u_") for k in a)


@pytest.mark.parametrize("bad", [
    {"console_per_march_unit": {"attention_basis": "x"}},
    {"console_per_march_unit": {"exceptions": "yes"}},
    {"console_per_march_unit": {"extra": 1}},
    {"console_per_march_unit": 3},
    {"control_mode": "supervisory"},
    {"n_operators": 2},
    {"queue_model": "buffer"},
    {"q_droop": 0.2},
    {"span_capacity": 0.0},
])
def test_validation(bad):
    with pytest.raises(ValueError):
        build(**bad)


def test_crew_must_be_declared_and_every_unit_needs_a_control_vehicle():
    with pytest.raises(ValueError, match="crew"):
        p = params()
        p.pop("autonomy_arm")
        scn = SC.with_params(p)
        c2.build_c2(scn, build_entities(scn, make_rng(0, scn.id)), ConstRNG())
    with pytest.raises(ValueError, match="control vehicle"):
        build(convoy={"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1,
                      "roles": ["cargo"] * 5})


# ---- assignment ------------------------------------------------------------------

def test_one_console_per_march_unit_hosted_by_the_control_vehicle():
    scn, ent, op, _ = build()
    u = op.units
    assert u.host.tolist() == [0, 5, 10] and u.n_assigned0.tolist() == [4, 4, 4]
    assert op.crew_free_at.size == 3
    for c, host in enumerate(u.host):
        members = np.nonzero(u.console_of == c)[0]
        assert members.tolist() == [host + j for j in range(1, 5)]            # the four crewless followers
    assert (u.console_of[u.host] == -1).all()                                   # the control vehicle is not supervised


def test_crewed_escorts_and_vehicles_outside_units_are_not_supervised():
    scn, ent, op, _ = build(convoy={"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 1,
                                    "roles": ["control", "cargo", "cargo", "security", "recovery"]},
                            crew={"cargo": 0, "security": 3, "recovery": 2})
    u = op.units
    agents = np.nonzero(u.console_of >= 0)[0]
    assert set(ent.convoy_role[agents].tolist()) == {1}                         # cargo only: crewed roles are excluded
    assert u.n_assigned0.tolist() == [2, 2, 2]


# ---- attention: below, at, above capacity ----------------------------------------

@pytest.mark.parametrize("span, expected", [(8.0, 1.0), (4.0, 1.0), (2.0, 0.5), (1.0, 0.25)])
def test_attention_below_at_and_above_capacity(span, expected):
    scn, ent, op, comms = build(span_capacity=span)
    drive(scn, ent, op, comms, 1)
    assert op.units.attention.tolist() == pytest.approx([expected] * 3)
    assert op.units.q_eff.tolist() == pytest.approx([0.70 + 0.25 * expected] * 3)


def test_four_crewless_followers_per_console_give_attention_one_and_q_operator():
    scn, ent, op, comms = build()
    drive(scn, ent, op, comms, 1)
    assert op.units.attention.tolist() == [1.0, 1.0, 1.0]
    assert op.units.q_eff.tolist() == pytest.approx([0.95] * 3)                  # decision quality equals q_operator
    assert math.isclose(min(1.0, 4.0 / 15.0) * 0.25 + 0.70, 0.7667, abs_tol=1e-3)  # the legacy term, for contrast


def test_attention_basis_assigned_is_fixed_and_living_follows_the_survivors():
    for basis, expect in (("assigned", 1.0), ("living", 1.0)):
        scn, ent, op, comms = build(span_capacity=2.0, console_per_march_unit={"attention_basis": basis})
        ent.alive[[1, 2]] = False                                                # two of unit 0's four agents die
        drive(scn, ent, op, comms, 1)
        a0 = op.units.attention[0]
        assert a0 == pytest.approx(0.5 if basis == "assigned" else 1.0)           # 2/4 vs 2/2
        assert op.units.attention[1] == pytest.approx(0.5)


def test_attention_never_changes_service_time_latency_or_loss():
    """Comms and queueing are independent of attention: changing span only changes the serviced quality."""
    runs = []
    for span in (1.0, 8.0):
        scn, ent, op, comms = build(level=3, span_capacity=span)
        drive(scn, ent, op, comms, 80)
        runs.append(c2_units.metrics(op.units))
    a, b = runs
    for key in ("c2u_requests", "c2u_serviced", "c2u_it", "c2u_wt", "c2u_nt", "c2u_comms_up", "c2u_comms_down",
                "c2u_abandon_link", "c2u_abandon_queue"):
        assert a[key] == b[key], key
    assert a["c2u_quality_mean"] < b["c2u_quality_mean"]


def test_comms_level_changes_delay_but_not_attention_or_quality():
    out = {}
    for level in (0, 3):
        scn, ent, op, comms = build(level=level)
        drive(scn, ent, op, comms, 120)
        out[level] = c2_units.metrics(op.units)
    assert out[3]["c2u_comms_up"] > out[0]["c2u_comms_up"]
    assert out[0]["c2u_attention_mean"] == out[3]["c2u_attention_mean"] == 1.0
    assert out[0]["c2u_quality_mean"] == pytest.approx(out[3]["c2u_quality_mean"])    # the same impairment is not applied twice
    assert 0.0 <= out[3]["c2u_quality_mean"] <= 1.0


# ---- routing and isolation --------------------------------------------------------

def test_requests_reach_only_the_agents_own_console():
    scn, ent, op, comms = build()
    u = op.units
    ent.decision_cooldown[:] = 99
    ent.decision_cooldown[[1, 2]] = 0                                            # only unit 0's agents ask
    drive(scn, ent, op, comms, 1)
    assert u.requests.tolist() == [2, 0, 0] and u.serviced.tolist() == [2, 0, 0]
    assert op.crew_free_at[0] > 0 and op.crew_free_at[1] == 0 and op.crew_free_at[2] == 0


def test_a_busy_console_does_not_delay_another_unit():
    scn, ent, op, comms = build()
    ent.decision_cooldown[:] = 99
    ent.decision_cooldown[[1, 2, 3, 4]] = 0                                      # unit 0 sends four at once
    ent.decision_cooldown[[6]] = 0                                               # unit 1 sends one
    drive(scn, ent, op, comms, 1)
    u = op.units
    assert u.qwait_sum[0] > 0 and u.qwait_sum[1] == 0                            # unit 0 queues; unit 1 does not
    assert u.serviced.tolist() == [4, 1, 0]


def test_two_units_versus_three_give_each_unit_the_same_deterministic_behavior():
    """Metamorphic: adding an independent identical unit leaves every existing unit's C2 results unchanged."""
    res = {}
    for n in (2, 3, 4):
        scn, ent, op, comms = build(units=n, level=2)
        drive(scn, ent, op, comms, 150)
        res[n] = c2_units.metrics(op.units)
    keys = [k for k in res[2] if k.startswith(("c2u_c0_", "c2u_c1_")) and not k.endswith(("_unit", "_nt_margin"))]
    for n in (3, 4):
        for k in keys:
            assert res[n][k] == res[2][k], (n, k)
    for k in ("c2u_c0_nt_margin", "c2u_c1_nt_margin"):
        assert res[3][k] == res[2][k] or (math.isnan(res[3][k]) and math.isnan(res[2][k]))
    # and the new unit behaves like the old ones
    assert res[3]["c2u_c2_requests"] == res[3]["c2u_c0_requests"] and res[3]["c2u_c2_serviced"] == res[3]["c2u_c0_serviced"]


# ---- console loss, leader loss, empty units ----------------------------------------

def test_losing_the_control_vehicle_zeroes_the_service_rate_of_that_console_only():
    scn, ent, op, comms = build()
    drive(scn, ent, op, comms, 40)
    before = op.units.serviced.copy()
    ent.alive[5] = False                                                         # unit 1's control vehicle
    drive(scn, ent, op, comms, 80, start=40)
    u = op.units
    assert u.lost_at.tolist() == [-1, 40, -1] and u.host_alive.tolist() == [True, False, True]
    assert u.serviced[1] == before[1]                                            # nothing served after the loss
    assert u.abandon_console[1] > 0 and u.abandon_console[0] == u.abandon_console[2] == 0
    assert u.serviced[0] > before[0] and u.serviced[2] > before[2]               # the other consoles keep working
    m = c2_units.metrics(u)
    assert m["c2u_consoles_lost"] == 1.0 and m["c2u_c1_active_steps"] <= 40


def test_assignments_stay_with_the_original_console_after_promote_and_absorb():
    for policy in ("promote", "absorb"):
        scn, ent, op, comms = build(leader_loss_policy=policy, blue_behavior="leader_follow")
        bhv = behavior.build_behavior(scn, ent)
        before = op.units.console_of.copy()
        ent.alive[0] = False
        behavior._update_leader_loss(ent, bhv, 1, np.zeros(ent.n, bool))
        drive(scn, ent, op, comms, 60, bhv=bhv)
        assert (op.units.console_of == before).all()                              # no re-assignment, no delay
        assert op.units.host_alive.tolist() == [False, True, True]                # the promoted truck does not host
        assert op.units.abandon_console[0] > 0 and op.units.serviced[0] == 0


def test_an_empty_unit_is_inactive_and_does_not_dilute_the_aggregates():
    scn, ent, op, comms = build()
    ent.alive[[1, 2, 3, 4]] = False                                              # unit 0 has no supervised agent left
    drive(scn, ent, op, comms, 100)
    u = op.units
    assert u.active_steps[0] == 0 and u.attention[0] == 1.0
    m = c2_units.metrics(u)
    assert m["c2u_c0_requests"] == 0 and m["c2u_c0_utilization"] == 0.0
    assert m["c2u_active_console_steps"] == u.active_steps[1] + u.active_steps[2]
    assert m["c2u_supervised_mean"] == pytest.approx(4.0)                         # over active console-steps only
    assert m["c2u_consoles_active_end"] == 2.0


def test_no_eligible_operator_left_is_defined():
    scn, ent, op, comms = build()
    ent.alive[[0, 5, 10]] = False                                                # every control vehicle is gone
    drive(scn, ent, op, comms, 80)
    m = c2_units.metrics(op.units)
    assert m["c2u_serviced"] == 0 and m["c2u_abandon_console"] == m["c2u_requests"] > 0
    assert m["c2u_consoles_lost"] == 3.0 and m["c2u_consoles_active_end"] == 0.0
    assert m["c2u_quality_mean"] == 0.0 and m["c2u_it"] == 0.0                    # defined zeros, no division by zero


# ---- exceptions ---------------------------------------------------------------------

def test_leader_follow_exceptions_file_a_request_at_once_to_the_agents_console():
    scn, ent, op, comms = build(console_per_march_unit={"exceptions": True}, blue_behavior="leader_follow")
    bhv = behavior.build_behavior(scn, ent)
    ent.decision_cooldown[:] = 99
    drive(scn, ent, op, comms, 1, bhv=bhv)                                       # prime the intervention baseline
    assert op.units.requests.sum() == 0
    bhv.interventions[7] += 1                                                    # a track timeout on a unit-1 follower
    bhv.interventions[0] += 1                                                    # and on a crewed vehicle: ignored
    drive(scn, ent, op, comms, 1, bhv=bhv, start=1)
    u = op.units
    assert u.exception_requests.tolist() == [0, 1, 0] and u.requests.tolist() == [0, 1, 0]
    drive(scn, ent, op, comms, 1, bhv=bhv, start=2)                              # no new intervention: nothing more
    assert u.exception_requests.sum() == 1


# ---- measures: IT, WT, NT and the neglect condition ---------------------------------

def test_interaction_wait_and_neglect_times_are_measured_and_the_margin_is_their_combination():
    scn, ent, op, comms = build(service_rate=0.5, decision_interval=60)
    drive(scn, ent, op, comms, 300)
    m = c2_units.metrics(op.units)
    assert m["c2u_c0_it"] == pytest.approx(2.0)                                   # 1 / service_rate
    assert m["c2u_c0_wt"] > 0                                                     # four agents asking together queue
    s = m["c2u_c0_supervised_mean"]
    assert m["c2u_c0_nt_margin"] == pytest.approx(m["c2u_c0_nt"] - (s - 1) * (m["c2u_c0_it"] + m["c2u_c0_wt"]))


def test_the_neglect_condition_holds_when_demand_is_slow_and_fails_when_it_is_fast():
    margins = {}
    for interval in (60, 4):
        scn, ent, op, comms = build(service_rate=0.5, decision_interval=interval)
        drive(scn, ent, op, comms, 400)
        margins[interval] = c2_units.metrics(op.units)["c2u_c0_nt_margin"]
    assert margins[60] > 0 > margins[4]


# ---- accounting ----------------------------------------------------------------------

def test_aggregates_are_sums_or_ratios_of_sums_of_the_per_console_results():
    scn, ent, op, comms = build(level=2)
    drive(scn, ent, op, comms, 200)
    m = c2_units.metrics(op.units)
    for key in ("requests", "serviced", "abandon_link", "abandon_queue", "abandon_console", "exception_requests"):
        assert m[f"c2u_{key}"] == sum(m[f"c2u_c{c}_{key}"] for c in range(3)), key
    assert m["c2u_requests"] == m["c2u_serviced"] + m["c2u_abandon_link"] + m["c2u_abandon_queue"] + m["c2u_abandon_console"]
    assert m["c2u_it"] == pytest.approx(sum(op.units.svc_sum) / m["c2u_serviced"])
    assert 0.0 <= m["c2u_utilization"] <= 1.0
    # the legacy accumulators still agree with the new ones
    assert op.n_request == m["c2u_requests"] and op.n_serviced == m["c2u_serviced"]


# ---- constructed march unit: the issue's acceptance cases --------------------------

def _constructed(policy, kill_at=30, **extra):
    """Two units of one control vehicle and four crewless followers, open route, no Red shooter. The control vehicle of
    unit 0 is destroyed at step `kill_at`. Returns (result, entities at the end)."""
    from dataclasses import replace
    scn = replace(SC, objective=replace(SC.objective, survive_fraction=1.0))
    seen = {}
    orig = behavior.step

    def spy(ent, bhv, op, comms, scn_, k, rng, world=None):
        seen["ent"] = ent
        if k == 0:
            ent.alive[ent.side != BLUE] = False                                  # no Red shooter
        if k == kill_at:
            ent.alive[0] = False
        return orig(ent, bhv, op, comms, scn_, k, rng, world=world)

    behavior.step = spy
    try:
        r = run_mission(scn, seed=0, params=params(units=2, leader_loss_policy=policy, **extra))
    finally:
        behavior.step = orig
    ent = seen["ent"]
    from sandtable import metrics
    short = (ent.side == BLUE) & ent.alive & ~metrics.blue_at_goal(ent, scn)
    return r, ent, short


def test_destroying_the_control_vehicle_leaves_four_followers_short_under_halt():
    r, ent, short = _constructed("halt")
    assert short[1:5].all() and short.sum() == 4                                  # the four followers of unit 0
    assert r["c2u_consoles_lost"] == 1.0


@pytest.mark.parametrize("policy, extra", [("continue", {}), ("absorb", {"handoff_steps": 5})])
def test_under_continue_and_absorb_none_are_short_once_the_handoff_has_passed(policy, extra):
    r, ent, short = _constructed(policy, **extra)
    assert short.sum() == 0
    assert r["c2u_abandon_console"] > 0                                           # the lost console served nobody


# ---- verification pass: what "neutral quality" means -----------------------------------------------
# Consumers of `control_quality` in the code: motion.step (speed x (0.35 + 0.65 q)), engagement._side_damage and
# belief.engage (kill probability x q[shooter] x (2 - q[target])), and the replay display. Sensing does not read it.
# `behavior` reads `await_until` (TELEOP hold only), which exempt vehicles never set.

class _FlatWorld:
    def speed_at(self, x, y):
        return np.ones_like(x, dtype=float)


def test_exempt_vehicles_keep_quality_one_and_supervised_ones_do_not():
    scn, ent, op, comms = build()
    ent.march_unit[14] = -1                              # a vehicle outside every march unit (like a UAS)
    op = c2.build_c2(scn, ent, ConstRNG())
    drive(scn, ent, op, comms, 1)
    ent.decision_cooldown[:] = 0
    drive(scn, ent, op, comms, 60, start=1)
    exempt = [0, 5, 10, 14]                              # three control vehicles and the out-of-unit vehicle
    assert (ent.control_quality[exempt] == 1.0).all()
    supervised = np.nonzero(op.units.console_of >= 0)[0]
    assert (ent.control_quality[supervised] < 1.0).all() and (ent.control_quality[supervised] >= 0.3).all()
    assert 14 not in supervised and (ent.await_until[exempt] == -1).all()   # they never wait, so TELEOP never holds them


def test_quality_one_is_the_best_value_on_every_consumer_so_exemption_is_an_advantage_over_supervision():
    """Tempo, the shooter's kill probability and the target's exposure all improve monotonically up to q = 1."""
    from sandtable import motion
    speeds = {}
    for label, q in (("exempt", 1.0), ("q_operator", 0.95), ("q_auto", 0.70)):
        scn, ent, op, comms = build()
        ent.control_quality[:] = q
        ent.tgt_x, ent.tgt_y = ent.x + 1000.0, ent.y.copy()
        ent.heading[:] = 0.0
        motion.step(ent, _FlatWorld(), 1.0)
        speeds[label] = float(ent.speed[1])
    assert speeds["exempt"] > speeds["q_operator"] > speeds["q_auto"]
    assert speeds["q_operator"] / speeds["exempt"] == pytest.approx(0.35 + 0.65 * 0.95)
    # engagement: shooter factor q, target factor (2 - q); the same shot, two Blue targets, a threshold draw between them
    from sandtable import engagement
    from sandtable.entities import RED

    class _W:
        def los(self, x0, y0, x1, y1):
            return np.ones(np.broadcast(x0, x1).shape, bool)

        def cover_at(self, x, y):
            return np.zeros_like(x, dtype=float)

    scn, ent, _, _ = build()
    ent.alive[:] = False
    red = int(np.nonzero(ent.side == RED)[0][0])
    ent.alive[[red, 1, 2]] = True
    ent.x[[red, 1, 2]], ent.y[[red, 1, 2]] = [3000.0, 2500.0, 2500.0], [1800.0, 1500.0, 1500.0]
    ent.seen[:] = True
    ent.weapon_range[red], ent.pk_base[red] = 1000.0, 0.008
    ent.control_quality[1], ent.control_quality[2] = 1.0, 0.70            # vehicle 1 exempt, vehicle 2 supervised at q_auto
    hit = {}
    for target in (1, 2):
        ent.alive[[1, 2]] = False
        ent.alive[target] = True
        dmg = np.zeros(ent.n)
        pos = np.column_stack([ent.x, ent.y])
        dist = np.hypot(pos[:, None, 0] - pos[None, :, 0], pos[:, None, 1] - pos[None, :, 1])

        class U:                                              # a draw of 0.0092 sits between 0.008 x 1.0 and 0.008 x 1.30
            def random(self, n):
                return np.full(n, 0.0092)
        engagement._side_damage(ent, _W(), dist, RED, U(), dmg)
        hit[target] = bool(dmg[target] > 0)
    assert hit == {1: False, 2: True}                          # the exempt vehicle is the harder target


def test_quality_does_not_enter_sensing():
    from sandtable import sensing
    from sandtable.world import build_world
    seen = []
    for q in (1.0, 0.3):
        scn, ent, _, _ = build()
        ent.control_quality[:] = q
        rng = make_rng(0, scn.id)
        sensing.step(ent, build_world(scn, rng), rng)
        seen.append(ent.seen.copy())
    assert (seen[0] == seen[1]).all()


# ---- verification pass: console ownership after host loss, promote and absorb --------------------------

@pytest.mark.parametrize("policy, succession", [("promote", "any"), ("promote", "manned_only"), ("absorb", "manned_only")])
def test_followers_after_host_loss_keep_their_dead_console_under_promote_and_absorb(policy, succession):
    """Model assumption (needs approval): assignments are fixed. Followers of a unit whose host died stay assigned to the
    dead console even when #17 promotes one of them or hands them to another unit."""
    scn, ent, op, comms = build(leader_loss_policy=policy, blue_behavior="leader_follow", succession=succession)
    bhv = behavior.build_behavior(scn, ent)
    drive(scn, ent, op, comms, 30, bhv=bhv)                                        # the opening round is served and settled
    served_before = op.units.serviced.copy()
    ent.alive[0] = False                                                           # unit 0's host
    behavior._update_leader_loss(ent, bhv, 1, np.zeros(ent.n, bool))
    followers = [1, 2, 3, 4]
    u = op.units
    if policy == "promote" and succession == "any":
        assert (ent.march_unit[followers] == 0).all()                              # still unit 0
        assert ent.leader[1] == -1 and (ent.leader[[2, 3, 4]] == 1).all()          # a crewless truck leads the rest
    elif policy == "promote":
        assert (ent.march_unit[followers] == 0).all()
        assert (ent.leader[followers] == -1).all()                                 # no crewed successor: each drives alone
    else:
        assert (ent.march_unit[followers] == 1).all()                              # handed to unit 1
        assert (ent.leader[followers] == 5).all()                                  # and follow unit 1's head
    assert (u.console_of[followers] == 0).all()                                    # but still owned by console 0
    ent.await_until[:] = -1                                                        # the opening requests are settled
    ent.decision_cooldown[:] = 99
    ent.decision_cooldown[followers] = 0
    before = u.requests.copy()
    drive(scn, ent, op, comms, 1, bhv=bhv, start=31)
    assert u.host_alive.tolist() == [False, True, True]                            # the dead console is the one asked
    assert (u.requests - before).tolist() == [4, 0, 0]                             # not unit 1's live console, even for absorbed ones
    assert (ent.control_quality[followers] == op.q_stall).all()                    # waiting on a console that will not answer
    drive(scn, ent, op, comms, op.patience + 2, bhv=bhv, start=32)
    assert u.serviced[0] == served_before[0]                                       # the dead console served nothing more
    assert (u.nt_sum >= 0).all()                                                   # no negative neglect sample
    assert (ent.control_quality[followers] <= op.q_fallback + 1e-9).all()          # fallback quality afterwards (stall in between)
    assert u.abandon_console[0] >= 4


# ---- verification pass: how NT, IT, WT and s are measured, and what is not counted ----------------------

def test_neglect_clock_starts_at_an_answer_and_ignores_unserved_and_censored_gaps():
    scn, ent, op, comms = build(service_rate=0.5, decision_interval=60)
    u = op.units
    ent.decision_cooldown[:] = 999
    ent.decision_cooldown[1] = 0
    drive(scn, ent, op, comms, 5)                                                  # vehicle 1 asks once and is answered
    assert u.serviced[0] == 1 and u.nt_n[0] == 0                                   # no neglect sample until it asks again
    assert u.ans_at[1] >= 0
    m = c2_units.metrics(u)
    assert math.isnan(m["c2u_c0_nt_margin"]) and m["c2u_c0_nt"] == 0.0              # a censored gap is not counted, not zero-filled
    ent.alive[0] = False                                                           # the console dies; vehicle 1 asks again
    ent.decision_cooldown[1] = 0
    drive(scn, ent, op, comms, 3, start=5)
    assert u.abandon_console[0] == 1 and u.serviced[0] == 1                        # an unserved request adds no IT or WT sample
    assert u.nt_n[0] == 1                                                          # but it closes the neglect gap that preceded it
    assert u.ans_at[1] == -1                                                       # and the clock is now off until the next answer


def test_it_and_wt_come_from_serviced_requests_only():
    scn, ent, op, comms = build(service_rate=0.5, decision_interval=60)
    ent.decision_cooldown[:] = 999
    ent.decision_cooldown[[1, 2, 3, 4]] = 0                                        # four ask together on one console
    drive(scn, ent, op, comms, 12)
    m = c2_units.metrics(op.units)
    assert m["c2u_c0_serviced"] == 4
    assert m["c2u_c0_it"] == pytest.approx(2.0)                                     # 1 / service_rate
    assert m["c2u_c0_wt"] == pytest.approx((0 + 2 + 4 + 6) / 4)                    # waits of the 1st to 4th in the queue
    assert m["c2u_c0_supervised_mean"] == pytest.approx(4.0)                        # s: mean living supervised agents over active steps
