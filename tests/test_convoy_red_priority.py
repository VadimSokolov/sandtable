"""Red target priority and the abstract ambush template (Issue #18).

Controlled fixtures: selection is checked with a stub world, a rigged RNG (every kill draw succeeds)
and hand-placed vehicles, so no result depends on enemy accuracy. The few full missions only check that
the features compose and that conserved quantities stay conserved.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import ambush, behavior, engagement, target_priority as tp
from sandtable.convoy import ROLE_CONTROL, ROLE_SECURITY
from sandtable.entities import BLUE, RED
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

SC = load_scenario("scenarios/uc3_convoy_ambush.json")
BASE = {k: v for k, v in SC.params.items() if k != "ambush"}


class StubWorld:
    """No terrain: line of sight everywhere unless a pair is listed in `blocked`, no cover."""

    def __init__(self, blocked=()):
        self.blocked = set(blocked)

    def los(self, x0, y0, x1, y1):
        out = np.ones(np.broadcast(x0, x1).shape, bool)
        for a, b in self.blocked:
            out[a, b] = False
        return out

    def cover_at(self, x, y):
        return np.zeros_like(x, dtype=float)


class Sure:
    """A rigged RNG: every kill draw succeeds."""

    def random(self, n):
        return np.zeros(n)


def _fixture(blue: dict, red=((3000.0, 1800.0),), params=None):
    """Entities with only the listed Blue vehicles ({index: (x, y)}) and the first `len(red)` Red alive."""
    scn = SC.with_params(params or {})
    ent = build_entities(scn, make_rng(0, scn.id))
    ent.alive[:] = False
    for i, (x, y) in blue.items():
        ent.alive[i], ent.x[i], ent.y[i], ent.seen[i] = True, x, y, True
    reds = np.nonzero(ent.side == RED)[0]
    for r, (x, y) in zip(reds, red):
        ent.alive[r], ent.x[r], ent.y[r] = True, x, y
    ent.weapon_range[:] = np.where(ent.side == RED, 1000.0, ent.weapon_range)
    return scn, ent, reds


def _dist(ent):
    return np.hypot(ent.x[:, None] - ent.x[None, :], ent.y[:, None] - ent.y[None, :])


def _fire(scn, ent, order, world=None, **cfg):
    prio = tp.build_target_priority(scn.with_params({"target_priority": {"order": order, **cfg}}), ent)
    tp.begin_step(ent, prio)
    dmg = np.zeros(ent.n)
    engagement._side_damage(ent, world or StubWorld(), _dist(ent), RED, Sure(), dmg, prio=prio)
    return prio, np.nonzero(dmg)[0]


def _strip(r):
    return {k: v for k, v in r.items() if not k.startswith("tp_")}


# ---- off state ------------------------------------------------------------------

def test_off_is_byte_identical():
    for seed in range(4):
        a = run_mission(SC, seed=seed, params={})
        for off in (None, "none"):
            assert same_run(a, run_mission(SC, seed=seed, params={"target_priority": off}))


def test_report_only_keeps_the_legacy_choice_and_stream():
    """`order: []` collects statistics but selects exactly as the legacy rule does."""
    for seed in range(4):
        a = run_mission(SC, seed=seed)
        b = run_mission(SC, seed=seed, params={"target_priority": {"order": []}})
        assert same_run(a, _strip(b))
        assert b["tp_activation_frac"] == 0.0 and b["tp_shots"] == b["tp_fallback_shots"]


def test_ambush_off_when_absent():
    r = run_mission(SC.with_params({"ambush": None}), seed=0)
    assert "ambush_launched" not in r


# ---- validation -----------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"order": ["ends", "ends"]},
    {"order": ["bogus"]},
    {"order": "ends"},
    {},
    {"order": ["armored"]},
    {"order": ["armored"], "armored_hp": -1},
    {"order": ["ends"], "armored_hp": 2.0},
    {"order": ["ends"], "end_definition": "x"},
    {"order": ["ends"], "ends_basis": "x"},
    {"order": ["ends"], "applies_to": []},
    {"order": ["ends"], "extra": 1},
])
def test_priority_validation(bad):
    with pytest.raises(ValueError):
        tp.resolve_target_priority({"target_priority": bad})


def test_priority_labels_ground_truth():
    r = tp.resolve_target_priority({"target_priority": {"order": ["ends", "security", "armed"],
                                                        "ends_basis": "column"}})
    assert r["ground_truth"] == ("security", "ends(column basis)") and r["attribute_knowledge"] == ("armed",)


def test_applies_to_unknown_type_rejected():
    ent = build_entities(SC, make_rng(0, SC.id))
    with pytest.raises(ValueError):
        tp.build_target_priority(SC.with_params({"target_priority": {"order": ["ends"], "applies_to": ["nope"]}}), ent)


@pytest.mark.parametrize("bad", [
    {"roles": {}}, {"roles": {"bogus": ["at_ambush"]}}, {"roles": {"security": ["at_security"]}},
    {"roles": {"ambush": ["a"], "support": ["a"]}},
    {"roles": {"ambush": ["a"]}, "trigger": {"point": [0, 0]}},
    {"roles": {"ambush": ["a"]}, "trigger": {"point": [0, 0], "radius": 0}},
    {"roles": {"ambush": ["a"]}, "trigger": {"point": [0, 0], "radius": 5}, "security_rule": "x"},
    {"roles": {"ambush": ["a"]}, "trigger": {"point": [0, 0], "radius": 5}, "withdraw": {}},
    {"roles": {"ambush": ["a"]}, "trigger": {"point": [0, 0], "radius": 5}, "withdraw": {"loss_fraction": 2}},
])
def test_ambush_validation(bad):
    with pytest.raises(ValueError):
        ambush.resolve_ambush({"ambush": bad})


# ---- eligibility before priority ------------------------------------------------

def test_priority_picks_preferred_class_among_eligible():
    scn, ent, _ = _fixture({1: (2500.0, 1500.0), 3: (2300.0, 1500.0)})
    assert ent.convoy_role[3] == ROLE_SECURITY
    assert list(_fire(scn, ent, [])[1]) == [1]                # legacy: nearest
    assert list(_fire(scn, ent, ["security"])[1]) == [3]      # security is farther but preferred


def test_unseen_preferred_target_is_never_chosen():
    scn, ent, _ = _fixture({1: (2500.0, 1500.0), 3: (2300.0, 1500.0)})
    ent.seen[3] = False
    assert list(_fire(scn, ent, ["security"])[1]) == [1]


def test_out_of_range_preferred_target_is_never_chosen():
    scn, ent, _ = _fixture({1: (2500.0, 1500.0), 3: (1000.0, 1500.0)})
    assert list(_fire(scn, ent, ["security"])[1]) == [1]


def test_blocked_los_preferred_target_is_never_chosen():
    scn, ent, reds = _fixture({1: (2500.0, 1500.0), 3: (2300.0, 1500.0)})
    _, hit = _fire(scn, ent, ["security"], world=StubWorld(blocked=[(int(reds[0]), 3)]))
    assert list(hit) == [1]


def test_shooter_without_ammunition_cannot_fire_whatever_the_priority():
    from sandtable import mechanics
    scn, ent, _ = _fixture({1: (2500.0, 1500.0)})
    prio = tp.build_target_priority(scn.with_params({"target_priority": {"order": ["ends"]}}), ent)
    tp.begin_step(ent, prio)
    dmg = np.zeros(ent.n)
    orig = mechanics.has_ammo
    mechanics.has_ammo = lambda e, m: np.zeros(e.n, bool)
    try:
        engagement._side_damage(ent, StubWorld(), _dist(ent), RED, Sure(), dmg, mech=object(), prio=prio)
    finally:
        mechanics.has_ammo = orig
    assert not dmg.any() and prio.shots.sum() == 0


# ---- determinism, fallback ------------------------------------------------------

def test_tie_goes_to_lowest_index():
    scn, ent, _ = _fixture({1: (3000.0, 1500.0), 2: (3000.0, 2100.0)})     # both 300 m from the shooter
    assert list(_fire(scn, ent, ["control"])[1]) == [1]
    ent.x[1], ent.y[1], ent.x[2], ent.y[2] = 3000.0, 2100.0, 3000.0, 1500.0
    assert list(_fire(scn, ent, ["control"])[1]) == [1]


def test_tie_inside_a_class_goes_to_lowest_index():
    scn, ent, _ = _fixture({3: (3000.0, 1500.0), 8: (3000.0, 2100.0)})     # two security vehicles, equidistant
    assert ent.convoy_role[3] == ent.convoy_role[8] == ROLE_SECURITY
    assert list(_fire(scn, ent, ["security"])[1]) == [3]


def test_fallback_to_nearest_when_no_class_reaches_anyone():
    scn, ent, _ = _fixture({1: (2800.0, 1500.0), 2: (2500.0, 1500.0)})
    prio, hit = _fire(scn, ent, ["security", "control"])
    assert list(hit) == [1] and prio.shots[-1] == 1 and prio.shots[:-1].sum() == 0


def test_next_class_used_when_the_first_is_destroyed():
    scn, ent, _ = _fixture({0: (2300.0, 1500.0), 3: (2400.0, 1500.0), 1: (2800.0, 1500.0)})
    assert ent.convoy_role[0] == ROLE_CONTROL
    assert list(_fire(scn, ent, ["control", "security"])[1]) == [0]
    ent.alive[0] = False
    assert list(_fire(scn, ent, ["control", "security"])[1]) == [3]
    ent.alive[3] = False
    assert list(_fire(scn, ent, ["control", "security"])[1]) == [1]


def test_priority_draws_no_extra_random_numbers():
    scn, ent, _ = _fixture({1: (2500.0, 1500.0), 3: (2300.0, 1500.0)})

    class Count(Sure):
        n = 0

        def random(self, n):
            Count.n += n
            return super().random(n)
    counts = []
    for order in ([], ["security"]):
        Count.n = 0
        prio = tp.build_target_priority(scn.with_params({"target_priority": {"order": order}}), ent)
        tp.begin_step(ent, prio)
        engagement._side_damage(ent, StubWorld(), _dist(ent), RED, Count(), np.zeros(ent.n), prio=prio)
        counts.append(Count.n)
    assert counts == [1, 1]


def test_applies_to_leaves_other_shooters_on_the_legacy_rule():
    scn, ent, reds = _fixture({1: (2500.0, 1500.0), 3: (2300.0, 1500.0)})
    assert list(scn.platform_types)[int(ent.ptype[reds[0]])] == "at_ambush"
    assert list(_fire(scn, ent, ["security"], applies_to=["at_support"])[1]) == [1]
    assert list(_fire(scn, ent, ["security"], applies_to=["at_ambush"])[1]) == [3]


# ---- column ends: position vs identity, seen vs column ------------------------

def test_position_ends_follow_the_vehicles():
    scn, ent, _ = _fixture({1: (500.0, 1500.0), 2: (900.0, 1500.0), 6: (1500.0, 1500.0)})
    goal = tuple(scn.objective.goal)
    assert tp.column_ends(ent, goal, "position", "seen") == (6, 1)
    ent.alive[6] = False
    assert tp.column_ends(ent, goal, "position", "seen") == (2, 1)


def test_identity_ends_follow_succession_not_position():
    """After unit 0 loses its head and #17 `promote` runs, the identity head is the promoted vehicle,
    even though a vehicle of another unit is physically nearer the goal."""
    scn = SC.with_params({**BASE, "leader_loss_policy": "promote", "blue_behavior": "leader_follow"})
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    ent.seen[:] = True
    goal = tuple(scn.objective.goal)
    assert tp.column_ends(ent, goal, "identity", "column")[0] == 0
    ent.alive[0] = False
    behavior._update_leader_loss(ent, bhv, 1, np.zeros(ent.n, bool))
    assert int(bhv.ll_head[0]) == 1 and ent.leader[1] == -1
    assert tp.column_ends(ent, goal, "identity", "column")[0] == 1
    ent.x[6], ent.y[6] = 5000.0, 1500.0                          # a vehicle of unit 1 far ahead
    assert tp.column_ends(ent, goal, "position", "column")[0] == 6
    assert tp.column_ends(ent, goal, "identity", "column")[0] == 1


def test_seen_basis_ignores_unseen_vehicles():
    scn, ent, _ = _fixture({1: (500.0, 1500.0), 6: (1500.0, 1500.0)})
    ent.seen[6] = False
    goal = tuple(scn.objective.goal)
    assert tp.column_ends(ent, goal, "position", "seen") == (1, 1)
    assert tp.column_ends(ent, goal, "position", "column") == (6, 1)


# ---- ambush template ------------------------------------------------------------

def _amb(params=None):
    scn = SC.with_params(params or {})
    ent = build_entities(scn, make_rng(0, scn.id))
    ent.seen[:] = False
    return scn, ent, ambush.build_ambush(scn, ent)


def test_ambush_holds_until_a_seen_vehicle_reaches_the_trigger():
    scn, ent, amb = _amb()
    listed = amb.role >= 0
    assert ambush.step(ent, amb, 0, 1.0)[listed].all() and not amb.launched
    ent.x[1], ent.y[1], ent.seen[1] = 2400.0, 1500.0, False
    assert ambush.step(ent, amb, 1, 1.0)[listed].all() and not amb.launched    # in place but not seen
    ent.seen[1] = True
    hold = ambush.step(ent, amb, 2, 1.0)
    assert amb.launched and amb.launch_step == 2 and not hold.any()
    ent.x[1] = 0.0
    assert not ambush.step(ent, amb, 3, 1.0).any() and amb.launched            # latched


def test_let_pass_ignores_security_vehicles_and_engage_counts_them():
    for rule, launches in (("let_pass", False), ("engage", True)):
        scn, ent, amb = _amb({"ambush": {**SC.params["ambush"], "security_rule": rule}})
        ent.x[3], ent.y[3], ent.seen[3] = 2400.0, 1500.0, True
        assert ent.convoy_role[3] == ROLE_SECURITY
        ambush.step(ent, amb, 0, 1.0)
        assert amb.launched is launches


def test_withdrawal_order_ambush_then_support_then_security_stays():
    scn, ent, amb = _amb()
    ent.x[1], ent.y[1], ent.seen[1] = 2400.0, 1500.0, True
    ambush.step(ent, amb, 10, 1.0)                               # launch at tick 10
    roles = {r: np.nonzero(amb.role == ambush.ROLES.index(r))[0] for r in ambush.ROLES}
    assert not ambush.step(ent, amb, 129, 1.0).any()             # 119 s after launch
    h = ambush.step(ent, amb, 130, 1.0)                          # 120 s: ambush withdraws
    assert h[roles["ambush"]].all() and not h[roles["support"]].any()
    h = ambush.step(ent, amb, 150, 1.0)                          # support follows 20 s later
    assert h[roles["ambush"]].all() and h[roles["support"]].all() and not h[roles["security"]].any()


def test_withdrawal_on_ambush_loss_fraction():
    scn, ent, amb = _amb({"ambush": {**SC.params["ambush"],
                                     "withdraw": {"loss_fraction": 0.5, "support_delay_s": 20.0}}})
    ent.x[1], ent.y[1], ent.seen[1] = 2400.0, 1500.0, True
    ambush.step(ent, amb, 0, 1.0)
    idx = np.nonzero(amb.role == ambush.ROLES.index("ambush"))[0]
    ent.alive[idx[:1]] = False
    assert not ambush.step(ent, amb, 1, 1.0)[idx[1:]].any()      # 1 of 3 lost: 0.33 < 0.5
    ent.alive[idx[:2]] = False
    assert ambush.step(ent, amb, 2, 1.0)[idx[2:]].all() and amb.withdraw_step == 2


def test_held_red_does_not_fire_through_the_engagement_step():
    scn, ent, reds = _fixture({1: (2500.0, 1500.0)})
    hold = np.zeros(ent.n, bool)
    hold[reds[0]] = True
    dmg = np.zeros(ent.n)
    engagement._side_damage(ent, StubWorld(), _dist(ent), RED, Sure(), dmg, hold_fire=hold)
    assert not dmg.any()
    engagement._side_damage(ent, StubWorld(), _dist(ent), RED, Sure(), dmg, hold_fire=np.zeros(ent.n, bool))
    assert dmg.any()


def test_template_run_launches_and_is_reproducible():
    a, b = run_mission(SC, seed=3), run_mission(SC, seed=3)
    assert same_run(a, b) and a["ambush_launched"] == 1.0 and a["ambush_launch_step"] > 0


# ---- composition with #12, #14, #17 ---------------------------------------------

PRIO = {"target_priority": {"order": ["ends", "security"]}}


@pytest.mark.parametrize("extra", [
    {},
    {"contact_reaction": {"action": "halt", "triggers": ["receive_fire"]}},
    {"leader_loss_policy": "halt", "halt_release": {"clear_steps": 10}},
    {"leader_loss_policy": "promote", "handoff_steps": 5},
])
def test_composes_with_contact_reaction_leader_loss_and_crew(extra):
    params = {**PRIO, **extra, "crew_metrics": True}
    r = run_mission(SC, seed=2, params=params)
    ent = build_entities(SC.with_params(params), make_rng(2, SC.id))
    loaded = float(ent.cargo[ent.side == BLUE].sum())
    assert r["tp_shots"] > 0 and r["ambush_launched"] == 1.0
    assert loaded == pytest.approx(r["delivered_frac"] * loaded + r["cargo_lost"] + r["cargo_in_transit"])
    assert r["crew_steps_at_risk"] == pytest.approx(sum(r[f"crew_steps_at_risk_{n}"]
                                                        for n in ("control", "cargo", "security", "recovery")))
    assert r["tp_vehicles_targeted"] >= r["blue_losses"]         # destroyed implies targeted


def test_policy_matching_legacy_choice_changes_nothing():
    """A preferred class nobody belongs to reduces to the legacy rule: same outputs bar the tp_ keys."""
    a = run_mission(SC, seed=1)
    b = run_mission(SC, seed=1, params={"target_priority": {"order": ["armored"], "armored_hp": 99.0}})
    assert same_run(a, _strip(b))


# ---- control-first trace, and unique vehicles vs targeting events ----------------

def _trace(order, policy, ticks=5):
    """Hand-placed single Red shooter beside the column, every kill draw succeeds; per tick the
    leader-loss pass (as `behavior.step` runs it before engagement) and then one shot."""
    params = {"leader_loss_policy": policy, "blue_behavior": "leader_follow"}
    scn = SC.with_params(params)
    ent = build_entities(scn, make_rng(0, scn.id))
    bhv = behavior.build_behavior(scn, ent)
    reds = np.nonzero(ent.side == RED)[0]
    ent.alive[reds[1:]] = False
    ent.x[reds[0]], ent.y[reds[0]] = -30.0, 600.0
    ent.weapon_range[reds] = 1000.0
    ent.seen[ent.side == BLUE] = True
    prio = tp.build_target_priority(scn.with_params({"target_priority": {"order": order}}), ent)
    rows = []
    for k in range(ticks):
        behavior._update_leader_loss(ent, bhv, k, np.zeros(ent.n, bool))
        tp.begin_step(ent, prio)
        dmg = np.zeros(ent.n)
        engagement._side_damage(ent, StubWorld(), _dist(ent), RED, Sure(), dmg, prio=prio)
        ent.hp = ent.hp - dmg
        ent.alive = ent.alive & (ent.hp > 0)
        rows.append(([int(i) for i in np.nonzero(dmg)[0]], bhv.leaderless_steps, [int(h) for h in bhv.ll_head]))
    return rows, prio, SC.dt


def test_control_first_trace_under_continue_accumulates_leaderless_time():
    """Unit heads are 0, 5, 10 (control vehicles). Killing a control vehicle leaves its unit leaderless for
    good under `continue`; each later tick adds one per leaderless unit, so the counter runs 0, 1, 3, 6, 9."""
    rows, prio, dt = _trace(["control"], "continue")
    assert [r[0] for r in rows] == [[10], [5], [0], [8], [6]]          # three control vehicles, then fallback
    assert [r[1] for r in rows] == [0, 1, 3, 6, 9]                     # unit-steps; a loss is seen a tick later
    assert [r[2] for r in rows] == [[0, 5, 10], [0, 5, -1], [0, -1, -1], [-1, -1, -1], [-1, -1, -1]]
    assert rows[-1][1] * dt == 9.0                                     # unit-seconds = unit-steps x dt (1 s)
    assert list(prio.shots) == [3, 2]                                  # 3 priority shots, 2 fallback shots


def test_legacy_nearest_trace_kills_no_head_in_the_same_window():
    rows, prio, _ = _trace([], "continue")
    assert [r[0] for r in rows] == [[8], [6], [9], [7], [4]] and rows[-1][1] == 0


def test_control_first_trace_under_promote_hands_each_unit_a_successor():
    rows, _, _ = _trace(["control"], "promote")
    assert [r[0] for r in rows] == [[10], [5], [0], [8], [6]]          # same shots: the policy chose them
    assert [r[2] for r in rows] == [[0, 5, 10], [0, 5, 11], [0, 6, 11], [1, 6, 11], [1, 6, 11]]
    assert all(r[1] == 0 for r in rows)                                # idealized zero latency: never leaderless


def test_unique_vehicles_targeted_is_not_the_number_of_targeting_events():
    scn, ent, _ = _fixture({1: (2500.0, 1500.0), 2: (2600.0, 1500.0)})
    prio = tp.build_target_priority(scn.with_params({"target_priority": {"order": ["ends"]}}), ent)
    for _ in range(3):                                                  # one vehicle aimed at three times
        tp.begin_step(ent, prio)
        engagement._side_damage(ent, StubWorld(), _dist(ent), RED, type("NoKill", (), {"random": lambda s, n: np.ones(n)})(),
                                np.zeros(ent.n), prio=prio)
    m = tp.metrics(prio)
    assert m["tp_shots"] == 3.0 and m["tp_vehicles_targeted"] == 1.0
    assert m["tp_targeted_head"] + m["tp_targeted_trail"] == 3.0       # also events, not vehicles


# ---- withdrawal: timed from activation, and can be disabled ----------------------

def test_scripted_withdrawal_is_timed_from_the_launch_not_the_mission_start():
    scn, ent, amb = _amb()
    ent.x[1], ent.y[1], ent.seen[1] = 2400.0, 1500.0, True
    assert not ambush.step(ent, amb, 500, 1.0).any() and amb.launch_step == 500     # launch late, at tick 500
    assert not ambush.step(ent, amb, 619, 1.0).any()                                 # 119 s after launch (600 s after start)
    assert ambush.step(ent, amb, 620, 1.0).any() and amb.withdraw_step == 620        # 120 s after launch


def test_without_a_withdraw_block_the_ambush_never_withdraws():
    cfg = {k: v for k, v in SC.params["ambush"].items() if k != "withdraw"}
    scn, ent, amb = _amb({"ambush": cfg})
    ent.x[1], ent.y[1], ent.seen[1] = 2400.0, 1500.0, True
    for k in (0, 1, 500, 5000):
        assert not ambush.step(ent, amb, k, 1.0).any()
    assert amb.launched and amb.withdraw_step == -1


def test_shot_timing_metrics_record_first_and_last_priority_path_shot():
    scn, ent, _ = _fixture({1: (2500.0, 1500.0)})
    prio = tp.build_target_priority(scn.with_params({"target_priority": {"order": []}}), ent)
    for k in (7, 9):
        tp.begin_step(ent, prio, k)
        engagement._side_damage(ent, StubWorld(), _dist(ent), RED, Sure(), np.zeros(ent.n), prio=prio)
    m = tp.metrics(prio)
    assert m["tp_first_shot_step"] == 7.0 and m["tp_last_shot_step"] == 9.0
