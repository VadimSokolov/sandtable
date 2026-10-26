"""Tests for convoy hierarchy of march units, serials, and vehicle roles (Issue #8, ATP 4-11)."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable.behavior import Behavior, _update_convoy_succession, WAYPOINT, LEADER_FOLLOW
from sandtable.convoy import (
    ROLE_CARGO,
    ROLE_CONTROL,
    ROLE_RECOVERY,
    ROLE_SECURITY,
    SECTION_HEAD,
    SECTION_MAIN,
    SECTION_TRAIL,
    build_convoy_layout,
    validate_convoy_spec,
)
from sandtable.entities import BLUE, GROUND, Entities
from sandtable.scenario import build_entities, load_scenario
from sandtable.sim import run_mission

REF_SPEC = {
    "march_unit_size": 5,
    "march_units_per_serial": 3,
    "serials_per_column": 1,
}


# ---- 1. Byte-Identity when Convoy is OFF -------------------------------------

def test_off_is_byte_identical():
    """An absent convoy spec leaves simulation runs and entities byte-identical."""
    scn = load_scenario("scenarios/uc3_route_defilade.json")
    for seed in range(5):
        run_a = run_mission(scn, seed=seed)
        run_b = run_mission(scn.with_params({"convoy": None}), seed=seed)
        assert same_run(run_a, run_b)

    rng = np.random.default_rng(0)
    ent = build_entities(scn, rng)
    assert (ent.march_unit == -1).all()
    assert (ent.serial == -1).all()
    assert (ent.section == -1).all()
    assert (ent.convoy_role == -1).all()


# ---- 2. Doctrinal Bounds Rejection (ATP 4-11) -------------------------------

def test_doctrinal_bounds():
    """Sizes outside doctrinal ranges raise ValueError naming the range."""
    # 1 <= march_unit_size <= 25
    with pytest.raises(ValueError, match="march unit size must be between 1 and 25"):
        validate_convoy_spec({"march_unit_size": 0, "march_units_per_serial": 3, "serials_per_column": 1})
    with pytest.raises(ValueError, match="march unit size must be between 1 and 25"):
        validate_convoy_spec({"march_unit_size": 26, "march_units_per_serial": 3, "serials_per_column": 1})

    # 2 <= march_units_per_serial <= 5
    with pytest.raises(ValueError, match="march units per serial must be between 2 and 5"):
        validate_convoy_spec({"march_unit_size": 5, "march_units_per_serial": 1, "serials_per_column": 1})
    with pytest.raises(ValueError, match="march units per serial must be between 2 and 5"):
        validate_convoy_spec({"march_unit_size": 5, "march_units_per_serial": 6, "serials_per_column": 1})

    # 1 <= serials_per_column <= 5
    with pytest.raises(ValueError, match="serials per column must be between 1 and 5"):
        validate_convoy_spec({"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 0})
    with pytest.raises(ValueError, match="serials per column must be between 1 and 5"):
        validate_convoy_spec({"march_unit_size": 5, "march_units_per_serial": 3, "serials_per_column": 6})

    # 6 <= total <= 300
    # 2 * 2 * 1 = 4 (under 6)
    with pytest.raises(ValueError, match="convoy total vehicles must be between 6 and 300"):
        validate_convoy_spec({"march_unit_size": 2, "march_units_per_serial": 2, "serials_per_column": 1})

    # Roles length mismatch
    with pytest.raises(ValueError, match="roles length"):
        validate_convoy_spec({
            "march_unit_size": 5,
            "march_units_per_serial": 3,
            "serials_per_column": 1,
            "roles": ["control", "cargo"],  # only 2 roles for 5 vehicles
        })

    # Unknown role
    with pytest.raises(ValueError, match="unknown convoy role"):
        validate_convoy_spec({
            "march_unit_size": 3,
            "march_units_per_serial": 2,
            "serials_per_column": 1,
            "roles": ["control", "cargo", "spaceship"],
        })


# ---- 3. Reference Convoy Layout (15 vehicles: 1 serial of 3 MUs of 5) -------

def test_reference_convoy_layout():
    """15-vehicle reference convoy layout produces expected structure and roles."""
    layout = build_convoy_layout(REF_SPEC)
    assert layout["total"] == 15

    # Exactly 3 March Unit heads, 3 trail elements, and 9 main body vehicles
    sec = layout["section"]
    assert (sec == SECTION_HEAD).sum() == 3
    assert (sec == SECTION_TRAIL).sum() == 3
    assert (sec == SECTION_MAIN).sum() == 9

    # Default roles: 3 control (heads), 3 recovery (trails), 9 cargo
    crole = layout["convoy_role"]
    assert (crole == ROLE_CONTROL).sum() == 3
    assert (crole == ROLE_RECOVERY).sum() == 3
    assert (crole == ROLE_CARGO).sum() == 9

    # 3 leaders (role == 0) and 12 followers (role == 1)
    assert (layout["role"] == 0).sum() == 3
    assert (layout["role"] == 1).sum() == 12

    # Contiguous March Unit assignments
    mu = layout["march_unit"]
    assert (mu[0:5] == 0).all()
    assert (mu[5:10] == 1).all()
    assert (mu[10:15] == 2).all()

    # Custom roles layout verification
    custom_spec = {
        "march_unit_size": 5,
        "march_units_per_serial": 3,
        "serials_per_column": 1,
        "roles": ["control", "security", "cargo", "cargo", "recovery"],
    }
    custom_layout = build_convoy_layout(custom_spec)
    assert (custom_layout["convoy_role"] == ROLE_SECURITY).sum() == 3


# ---- 4. Leader Pointers per March Unit ---------------------------------------

def test_leader_pointers_per_march_unit():
    """Followers must point to their own march unit head, not to vehicle 0."""
    layout = build_convoy_layout(REF_SPEC)
    ldr = layout["leader"]

    # MU 0 (head is 0)
    assert ldr[0] == -1
    assert (ldr[1:5] == 0).all()

    # MU 1 (head is 5)
    assert ldr[5] == -1
    assert (ldr[6:10] == 5).all()

    # MU 2 (head is 10)
    assert ldr[10] == -1
    assert (ldr[11:15] == 10).all()


# ---- 5. Command Succession on Head Loss --------------------------------------

def test_head_loss_succession():
    """When a march unit head is destroyed, the next living vehicle succeeds to head."""
    n = 15
    ent = Entities.allocate(n)
    ent.side[:] = BLUE
    ent.domain[:] = GROUND
    layout = build_convoy_layout(REF_SPEC)
    ent.march_unit[:] = layout["march_unit"]
    ent.serial[:] = layout["serial"]
    ent.section[:] = layout["section"]
    ent.convoy_role[:] = layout["convoy_role"]
    ent.role[:] = layout["role"]
    ent.leader[:] = layout["leader"]

    # Mock behavior state
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

    # Kill lead vehicle of MU 0 (vehicle 0)
    ent.alive[0] = False
    _update_convoy_succession(ent, bhv)

    # Vehicle 1 must be promoted to Head of MU 0
    assert ent.role[1] == 0
    assert ent.leader[1] == -1
    assert bhv.state[1] == WAYPOINT

    # Vehicles 2, 3, 4 now follow vehicle 1
    assert (ent.leader[2:5] == 1).all()

    # MU 1 and MU 2 must be completely unaffected
    assert ent.leader[5] == -1
    assert (ent.leader[6:10] == 5).all()
    assert ent.leader[10] == -1
    assert (ent.leader[11:15] == 10).all()

    # Now kill vehicle 1 as well
    ent.alive[1] = False
    _update_convoy_succession(ent, bhv)

    # Vehicle 2 must now become Head of MU 0
    assert ent.role[2] == 0
    assert ent.leader[2] == -1
    assert bhv.state[2] == WAYPOINT
    assert (ent.leader[3:5] == 2).all()
