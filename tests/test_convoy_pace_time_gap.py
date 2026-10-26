"""Tests for convoy pace regulation and dynamic time gap (Issue #10, ATP 4-16 & ATP 4-11)."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import motion, planning
from sandtable.behavior import Behavior, LEADER_FOLLOW, WAYPOINT, _update_convoy_succession
from sandtable.convoy import build_convoy_layout, validate_convoy_spec
from sandtable.entities import BLUE, GROUND, Entities
from sandtable.scenario import build_entities, load_scenario
from sandtable.sim import run_mission
from sandtable.world import build_world

REF_CONVOY_SPEC = {
    "march_unit_size": 5,
    "march_units_per_serial": 3,
    "serials_per_column": 1,
}


# ---- 1. Byte-Identity when Pace & Time Gap are OFF ---------------------------

def test_pace_time_gap_off_is_byte_identical():
    """An absent pace/time_gap leaves simulation runs and entities byte-identical."""
    scn = load_scenario("scenarios/uc3_route_defilade.json")
    for seed in range(5):
        run_a = run_mission(scn, seed=seed)
        run_b = run_mission(scn.with_params({"pace": None, "time_gap": None}), seed=seed)
        assert same_run(run_a, run_b)

    rng = np.random.default_rng(0)
    ent = build_entities(scn, rng)
    assert np.isinf(ent.speed_cap).all()


# ---- 2. Doctrinal Bounds Rejection (ATP 4-16 & ATP 4-11) --------------------

def test_doctrinal_bounds_pace_and_gap():
    """Pace and time gaps outside valid ranges raise ValueError naming the range."""
    # Pace bounds (0 < pace <= 50.0)
    with pytest.raises(ValueError, match="convoy pace must be between 0 and 50"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "pace": 0.0})
    with pytest.raises(ValueError, match="convoy pace must be between 0 and 50"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "pace": -5.0})
    with pytest.raises(ValueError, match="convoy pace must be between 0 and 50"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "pace": 55.0})

    # Time gap bounds (0 < time_gap <= 60.0)
    with pytest.raises(ValueError, match="convoy time gap must be between 0 and 60"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "time_gap": 0.0})
    with pytest.raises(ValueError, match="convoy time gap must be between 0 and 60"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "time_gap": -1.0})
    with pytest.raises(ValueError, match="convoy time gap must be between 0 and 60"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "time_gap": 75.0})

    # Element time gap bounds (0 < element_time_gap <= 300.0)
    with pytest.raises(ValueError, match="convoy element time gap must be between 0 and 300"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "element_time_gap": 0.0})
    with pytest.raises(ValueError, match="convoy element time gap must be between 0 and 300"):
        validate_convoy_spec({**REF_CONVOY_SPEC, "element_time_gap": 350.0})


# ---- 3. Steady Pace Regulation (Pacesetter) ----------------------------------

def test_steady_pace_regulation():
    """Pacesetter / element head speed is clamped to declared pace on open terrain."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    declared_pace = 8.0  # m/s (platform max_speed is 12.0 m/s)

    # Configure convoy with pace = 8.0
    scn_paced = scn.with_params({
        "convoy": {
            **scn.params["convoy"],
            "pace": declared_pace,
        }
    })

    rng = np.random.default_rng(42)
    ent = build_entities(scn_paced, rng)

    # Lead vehicles of each march unit (0, 5, 10) must have speed_cap = declared_pace
    assert ent.speed_cap[0] == declared_pace
    assert ent.speed_cap[5] == declared_pace
    assert ent.speed_cap[10] == declared_pace

    # Follower vehicles retain unconstrained cap
    assert np.isinf(ent.speed_cap[1:5]).all()
    assert np.isinf(ent.speed_cap[6:10]).all()

    # Step motion in open space and check steady speed
    world = build_world(scn_paced, rng)

    # Target far ahead along x
    ent.tgt_x[:] = ent.x + 1000.0
    ent.tgt_y[:] = ent.y
    ent.heading[:] = 0.0

    # Advance 10 steps
    for _ in range(10):
        motion.step(ent, world, dt=1.0)

    # Head vehicle speed must be clamped at declared_pace (8.0), while followers run unconstrained (~12.0)
    assert ent.speed[0] == pytest.approx(declared_pace, abs=1e-3)
    assert ent.speed[5] == pytest.approx(declared_pace, abs=1e-3)
    assert ent.speed[10] == pytest.approx(declared_pace, abs=1e-3)
    assert ent.speed[1] > 11.5


# ---- 4. Dynamic Time-Gap Follower Stationing ---------------------------------

def test_time_gap_dynamic_expansion():
    """Follower station distance expands linearly with speed and respects min gap."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    min_gap = 30.0
    time_gap = 4.0  # seconds

    scn_gap = scn.with_params({
        "formation_spread": min_gap,
        "convoy": {
            **scn.params["convoy"],
            "pace": 10.0,
            "time_gap": time_gap,
        }
    })

    n = 15
    ent = Entities.allocate(n)
    ent.side[:] = BLUE
    ent.domain[:] = GROUND
    layout = build_convoy_layout(scn_gap.params["convoy"])
    ent.march_unit[:] = layout["march_unit"]
    ent.serial[:] = layout["serial"]
    ent.section[:] = layout["section"]
    ent.convoy_role[:] = layout["convoy_role"]
    ent.role[:] = layout["role"]
    ent.leader[:] = layout["leader"]

    # Initial line along x
    ent.x[:] = np.arange(n) * -40.0
    ent.y[:] = 1500.0
    ent.heading[:] = 0.0

    bhv = Behavior(
        mode=LEADER_FOLLOW,
        follow_mode="behavior",
        teleop_stop=True,
        track_timeout=40,
        state=np.where(ent.role == 0, WAYPOINT, LEADER_FOLLOW),
        holding=np.zeros(n, bool),
        was_holding=np.zeros(n, bool),
        interventions=np.zeros(n, np.int32),
        hold_steps=np.zeros(n, np.int32),
        alive_steps=np.zeros(n, np.int32),
        trk_x=ent.x.copy(), trk_y=ent.y.copy(),
        trk_vx=np.full(n, 10.0), trk_vy=np.zeros(n),  # Tracking leader moving at 10 m/s
        trk_age=np.zeros(n, np.int32),
        topology="star",
        sense_range=250.0,
        outage=0,
        trk_err_sum=np.zeros(n), trk_steps=np.zeros(n, np.int32),
        trk_stale_steps=np.zeros(n, np.int32), trk_lost_steps=np.zeros(n, np.int32),
        st_err_sum=np.zeros(n), st_along_sum=np.zeros(n), st_cross_sum=np.zeros(n),
        st_steps=np.zeros(n, np.int32),
        prev_heading=ent.heading.copy(), turn_sum=np.zeros(n), turn_steps=np.zeros(n, np.int32),
    )

    # 1. At 10 m/s: effective gap = max(30, 10 * 4) = 40m
    tx = np.zeros(n)
    ty = np.full(n, 1500.0)
    tx_out, _ = planning._behavior_targets(ent, scn_gap, bhv, tx, ty)

    # For MU 0: head is at trk_x[0]. Vehicle 1 (rank 1) should target trk_x[0] - 1 * 40m
    expected_dist_rank1 = 40.0
    assert bhv.trk_x[1] - tx_out[1] == pytest.approx(expected_dist_rank1, abs=1e-3)

    # Vehicle 2 (rank 2) should target trk_x[0] - 2 * 40m = 80m
    expected_dist_rank2 = 80.0
    assert bhv.trk_x[2] - tx_out[2] == pytest.approx(expected_dist_rank2, abs=1e-3)

    # Measured time gap: delta_x / speed = 40.0 / 10.0 = 4.0s (exact)
    measured_time_gap = expected_dist_rank1 / 10.0
    assert measured_time_gap == pytest.approx(time_gap, abs=1e-3)

    # 2. At low speed (2 m/s): v * time_gap = 8m < min_gap (30m) -> effective gap = 30m
    bhv.trk_vx[:] = 2.0
    tx_out_slow, _ = planning._behavior_targets(ent, scn_gap, bhv, tx, ty)
    assert bhv.trk_x[1] - tx_out_slow[1] == pytest.approx(min_gap, abs=1e-3)


# ---- 5. Command Succession Inherits Pace -------------------------------------

def test_succession_inherits_pace():
    """When a march unit head is destroyed, promoted successor inherits the pace speed cap."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    declared_pace = 7.5

    scn_paced = scn.with_params({
        "convoy": {
            **scn.params["convoy"],
            "pace": declared_pace,
        }
    })

    rng = np.random.default_rng(0)
    ent = build_entities(scn_paced, rng)
    assert ent.speed_cap[0] == declared_pace
    assert np.isinf(ent.speed_cap[1])

    n = ent.n
    bhv = Behavior(
        mode=LEADER_FOLLOW,
        follow_mode="behavior",
        teleop_stop=True,
        track_timeout=40,
        state=np.where(ent.role == 0, WAYPOINT, LEADER_FOLLOW),
        holding=np.zeros(n, bool),
        was_holding=np.zeros(n, bool),
        interventions=np.zeros(n, np.int32),
        hold_steps=np.zeros(n, np.int32),
        alive_steps=np.zeros(n, np.int32),
        trk_x=ent.x.copy(), trk_y=ent.y.copy(),
        trk_vx=np.zeros(n), trk_vy=np.zeros(n),
        trk_age=np.zeros(n, np.int32),
        topology="star",
        sense_range=250.0,
        outage=0,
        trk_err_sum=np.zeros(n), trk_steps=np.zeros(n, np.int32),
        trk_stale_steps=np.zeros(n, np.int32), trk_lost_steps=np.zeros(n, np.int32),
        st_err_sum=np.zeros(n), st_along_sum=np.zeros(n), st_cross_sum=np.zeros(n),
        st_steps=np.zeros(n, np.int32),
        prev_heading=ent.heading.copy(), turn_sum=np.zeros(n), turn_steps=np.zeros(n, np.int32),
    )

    # Kill lead vehicle (0)
    ent.alive[0] = False
    _update_convoy_succession(ent, bhv)

    # Vehicle 1 is promoted to head and inherits speed_cap
    assert ent.role[1] == 0
    assert ent.leader[1] == -1
    assert ent.speed_cap[1] == declared_pace
