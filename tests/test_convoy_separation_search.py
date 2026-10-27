"""Tests for convoy separation parameters as search dimensions (Issue #15).

Verifies that vehicle spacing, element gaps, march speed, and security ratio are
exposed as design parameters for DOE sweeps and Bayesian optimization via polarisopt,
and that baseline parameters reproduce registered baseline metrics.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable.convoy import (
    ROLE_CARGO,
    ROLE_CONTROL,
    ROLE_RECOVERY,
    ROLE_SECURITY,
    build_convoy_layout,
    resolve_convoy_spec,
    validate_convoy_spec,
)
from sandtable.entities import BLUE, GROUND
from sandtable.scenario import build_entities, load_scenario
from sandtable.sim import run_mission

try:
    import polarisopt  # noqa: F401
except ImportError:
    import sys
    import types

    p = types.ModuleType("polarisopt")
    pm = types.ModuleType("polarisopt.metrics")
    pmb = types.ModuleType("polarisopt.metrics.base")

    class Metric:
        pass

    class MetricError(ValueError):
        pass

    class _Registry:
        def register(self, name):
            return lambda cls: cls

    pmb.Metric = Metric
    pmb.MetricError = MetricError
    pmb.metric_registry = _Registry()
    sys.modules["polarisopt"] = p
    sys.modules["polarisopt.metrics"] = pm
    sys.modules["polarisopt.metrics.base"] = pmb

from sandtable.opt_metrics import MissionScoreMetric


# ---- 1. Registered Baseline Reproduction -------------------------------------

def test_registered_baseline_reproduction():
    """Flat baseline parameters reproduce registered scenario metrics with 100% fidelity."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    flat_baseline_params = {
        "pace": 10.0,
        "time_gap": 4.0,
        "march_unit_size": 5,
        "march_units_per_serial": 3,
        "serials_per_column": 1,
    }

    for seed in range(3):
        run_base = run_mission(scn, seed=seed)
        run_flat = run_mission(scn, seed=seed, params=flat_baseline_params)
        assert same_run(run_base, run_flat)


# ---- 2. Flat Parameter Overrides --------------------------------------------

def test_flat_parameter_overrides_update_kinematics_and_doctrine():
    """Flat parameter overrides cleanly update speed caps, pass time, and road space."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    overrides = {
        "pace": 12.0,
        "time_gap": 5.0,
        "element_time_gap": 30.0,
        "safety_factor": 0.15,
    }

    rng = np.random.default_rng(42)
    ent = build_entities(scn.with_params(overrides), rng)

    # Lead vehicles of each march unit (0, 5, 10) must receive speed_cap = 12.0
    assert ent.speed_cap[0] == 12.0
    assert ent.speed_cap[5] == 12.0
    assert ent.speed_cap[10] == 12.0

    res = run_mission(scn, seed=42, params=overrides)
    # At pace 12.0 and safety factor 0.15, road space must be 1.15 * column_length
    assert res["convoy_rate_of_march"] == 12.0
    assert res["convoy_road_space"] == pytest.approx(res["convoy_column_length"] * 1.15)


# ---- 3. Security Ratio Dynamic Role Allocation ------------------------------

def test_security_ratio_role_allocation():
    """Security ratio allocates gun trucks proportionally across flexible middle slots."""
    base_spec = {
        "march_unit_size": 5,
        "march_units_per_serial": 2,
        "serials_per_column": 1,
    }

    # Ratio 0.0 -> 0 security, 3 cargo
    layout_0 = build_convoy_layout({**base_spec, "security_ratio": 0.0})
    roles_0 = layout_0["convoy_role"][:5]
    assert roles_0[0] == ROLE_CONTROL
    assert (roles_0[1:4] == ROLE_CARGO).all()
    assert roles_0[4] == ROLE_RECOVERY

    # Ratio 0.33 -> 1 security (round(3 * 0.33) = 1), 2 cargo
    layout_1 = build_convoy_layout({**base_spec, "security_ratio": 0.33})
    roles_1 = layout_1["convoy_role"][:5]
    assert roles_1[0] == ROLE_CONTROL
    assert (roles_1[1:3] == ROLE_CARGO).all()
    assert roles_1[3] == ROLE_SECURITY
    assert roles_1[4] == ROLE_RECOVERY

    # Ratio 0.67 -> 2 security, 1 cargo
    layout_2 = build_convoy_layout({**base_spec, "security_ratio": 0.67})
    roles_2 = layout_2["convoy_role"][:5]
    assert roles_2[0] == ROLE_CONTROL
    assert roles_2[1] == ROLE_CARGO
    assert (roles_2[2:4] == ROLE_SECURITY).all()
    assert roles_2[4] == ROLE_RECOVERY

    # Ratio 1.0 -> 3 security, 0 cargo
    layout_3 = build_convoy_layout({**base_spec, "security_ratio": 1.0})
    roles_3 = layout_3["convoy_role"][:5]
    assert roles_3[0] == ROLE_CONTROL
    assert (roles_3[1:4] == ROLE_SECURITY).all()
    assert roles_3[4] == ROLE_RECOVERY


def test_security_ratio_bounds_rejection():
    """Security ratio outside [0.0, 1.0] raises ValueError."""
    spec = {"march_unit_size": 5, "march_units_per_serial": 2, "serials_per_column": 1}
    with pytest.raises(ValueError, match="convoy security ratio must be between 0.0 and 1.0"):
        validate_convoy_spec({**spec, "security_ratio": -0.1})
    with pytest.raises(ValueError, match="convoy security ratio must be between 0.0 and 1.0"):
        validate_convoy_spec({**spec, "security_ratio": 1.2})


# ---- 4. Dynamic Force Sizing during Sweeps -----------------------------------

def test_dynamic_force_sizing_on_hierarchy_sweep():
    """Sweeping march unit size scales force count dynamically without size mismatch errors."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    rng = np.random.default_rng(0)

    # Base scenario has 15 blue ground + 6 red defenders = 21 entities
    ent_base = build_entities(scn, rng)
    assert ent_base.n == 21

    # Sweep to 4 vehicles per march unit (4 * 3 * 1 = 12 blue ground + 6 red = 18 total)
    ent_12 = build_entities(scn.with_params({"march_unit_size": 4}), rng)
    assert ent_12.n == 18
    blue_ground_mask = ent_12.side_mask(BLUE) & (ent_12.domain == GROUND)
    assert int(blue_ground_mask.sum()) == 12

    # Sweep to 6 vehicles per march unit (6 * 3 * 1 = 18 blue ground + 6 red = 24 total)
    ent_24 = build_entities(scn.with_params({"march_unit_size": 6}), rng)
    assert ent_24.n == 24
    assert int((ent_24.side_mask(BLUE) & (ent_24.domain == GROUND)).sum()) == 18


# ---- 5. MissionScoreMetric Road Space Penalty --------------------------------

def test_mission_score_road_space_penalty():
    """MissionScoreMetric penalizes road space when w_road > 0."""
    base_output = {
        "success_rate": 1.0,
        "time_to_objective": 500.0,
        "blue_loss_frac": 0.1,
        "convoy_road_space": 1000.0,
    }

    # Baseline with w_road = 0.0 (unchanged)
    m_default = MissionScoreMetric()
    score_default = float(m_default.compute(base_output)[0])

    # With road space penalty w_road = 0.2, road_scale = 1000.0
    m_road = MissionScoreMetric(w_road=0.2, road_scale=1000.0)
    score_road = float(m_road.compute(base_output)[0])

    # Expected addition: 0.2 * (1000.0 / 1000.0) = 0.2
    assert score_road == pytest.approx(score_default + 0.2)

    # Larger road space yields worse (higher) score
    score_larger = float(m_road.compute({**base_output, "convoy_road_space": 2000.0})[0])
    assert score_larger > score_road


# ---- 6. Helper resolve_convoy_spec -------------------------------------------

def test_resolve_convoy_spec_helper():
    """resolve_convoy_spec correctly handles empty, nested, and flat override dictionaries."""
    assert resolve_convoy_spec(None) is None
    assert resolve_convoy_spec({}) is None
    assert resolve_convoy_spec({"tempo": 1.0, "route_bias": 0.5}) is None

    # Nested spec
    nested = {"convoy": {"march_unit_size": 5, "pace": 10.0}}
    res_nested = resolve_convoy_spec(nested)
    assert res_nested["march_unit_size"] == 5
    assert res_nested["pace"] == 10.0

    # Flat overrides over nested spec
    merged = resolve_convoy_spec({
        "convoy": {"march_unit_size": 5, "pace": 10.0, "roles": ["control", "cargo", "recovery"]},
        "pace": 14.0,
        "security_ratio": 0.4,
    })
    assert merged["pace"] == 14.0
    assert merged["security_ratio"] == 0.4
    # roles should be cleared when security_ratio is swept
    assert "roles" not in merged
