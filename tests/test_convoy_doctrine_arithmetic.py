"""Tests for ATP 4-16 convoy doctrine arithmetic (Issue #11).

Verifies standard movement-control formulas: column length, road space, pass time,
time distance, road clearance time, and inter-element time gaps from ATP 4-16 (App. C).
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import convoy_metrics
from sandtable.convoy import validate_convoy_spec
from sandtable.scenario import PlatformType, build_entities, load_scenario
from sandtable.sim import run_mission


# ---- 1. Byte-Identity when Convoy is OFF -------------------------------------

def test_convoy_doctrine_arithmetic_off_is_byte_identical():
    """An absent convoy parameter leaves runs and metrics 100% byte-identical."""
    scn = load_scenario("scenarios/uc3_route_defilade.json")
    for seed in range(3):
        run_a = run_mission(scn, seed=seed)
        run_b = run_mission(scn.with_params({"convoy": None}), seed=seed)
        assert same_run(run_a, run_b)
        assert "convoy_column_length" not in run_a

    rng = np.random.default_rng(0)
    ent = build_entities(scn, rng)
    assert (ent.length == 6.0).all()


# ---- 2. PlatformType Length Parameter & Bounds ------------------------------

def test_platform_type_length():
    """PlatformType supports vehicle length defaulting to 6.0 m with non-negative validation."""
    p_default = PlatformType(name="truck")
    assert p_default.length == 6.0

    p_custom = PlatformType(name="heavy_transporter", length=11.5)
    assert p_custom.length == 11.5

    with pytest.raises(ValueError, match="platform length must be non-negative"):
        PlatformType(name="invalid", length=-1.0)


# ---- 3. Doctrinal Bounds Rejection (ATP 4-16) -------------------------------

def test_doctrinal_bounds_safety_factor_and_halts():
    """Safety factor, serial time gap, and halt durations outside bounds raise ValueError."""
    spec_base = {
        "march_unit_size": 5,
        "march_units_per_serial": 2,
        "serials_per_column": 1,
    }

    # Safety factor bounds [0.0, 1.0]
    with pytest.raises(ValueError, match="convoy safety factor must be between 0.0 and 1.0"):
        validate_convoy_spec({**spec_base, "safety_factor": -0.1})
    with pytest.raises(ValueError, match="convoy safety factor must be between 0.0 and 1.0"):
        validate_convoy_spec({**spec_base, "safety_factor": 1.5})

    # Serial time gap bounds (0, 600.0]
    with pytest.raises(ValueError, match="convoy serial time gap must be between 0 and 600"):
        validate_convoy_spec({**spec_base, "serial_time_gap": 0.0})
    with pytest.raises(ValueError, match="convoy serial time gap must be between 0 and 600"):
        validate_convoy_spec({**spec_base, "serial_time_gap": 700.0})

    # Halt duration bounds [0, 3600.0]
    with pytest.raises(ValueError, match="convoy halt duration must be between 0 and 3600"):
        validate_convoy_spec({**spec_base, "halt_duration": -10.0})
    with pytest.raises(ValueError, match="convoy halt duration must be between 0 and 3600"):
        validate_convoy_spec({**spec_base, "halt_duration": 4000.0})


# ---- 4. The Five ATP 4-16 Core Invariant Identities -------------------------

def test_atp416_identities_hold_on_constructed_columns():
    """The 5 invariant ATP 4-16 identities hold exactly on constructed columns."""
    test_cases = [
        # (march_size, march_per_ser, ser_per_col, pace, tg, elem_tg, sf, halt, dist, p_len)
        (5, 3, 1, 10.0, 4.0, 20.0, 0.0, 0.0, 5000.0, 6.0),
        (4, 2, 2, 12.0, 3.0, 15.0, 0.1, 0.0, 8000.0, 7.5),
        (5, 2, 1, 8.0, 5.0, 25.0, 0.2, 600.0, 4000.0, 6.0),   # with 10-minute halt
        (3, 2, 3, 15.0, 2.5, 12.0, 0.05, 0.0, 10000.0, 10.0),
    ]

    for (k, m, s, pace, tg, elem_tg, sf, halt, dist, p_len) in test_cases:
        spec = {
            "march_unit_size": k,
            "march_units_per_serial": m,
            "serials_per_column": s,
            "pace": pace,
            "time_gap": tg,
            "element_time_gap": elem_tg,
            "safety_factor": sf,
            "halt_duration": halt,
        }

        summary = convoy_metrics.doctrinal_convoy_summary(
            spec, route_distance=dist, platform_length=p_len
        )

        checks = convoy_metrics.verify_atp416_identities(summary)
        assert checks["all_valid"], f"Identity failed for {spec}: {checks}"
        assert checks["identity_td"]
        assert checks["identity_pt"]
        assert checks["identity_rct"]
        assert checks["identity_rs"]
        assert checks["identity_rct_dist"]


# ---- 5. Worked Textbook Example from ATP 4-16 (App. C) -----------------------

def test_atp416_worked_example_doctrine():
    """Verify hand-calculated movement quantities against ATP 4-16 Appendix C principles.

    Example:
      20 vehicles in 4 march units of 5 (1 serial).
      Vehicle length = 8.0 m.
      Pace = 10.0 m/s (36 km/h).
      Intra-element time gap = 4.0 s -> intra-gap = 40.0 m.
      Inter-element time gap = 15.0 s -> inter-gap = 150.0 m.
      Safety factor = 10% (0.10).
      Route distance = 6000.0 m.

    Hand calculations:
      Total vehicles = 20
      Vehicle lengths = 20 * 8.0 = 160.0 m
      Intra-element gaps = 4 march units * (5 - 1) = 16 gaps * 40.0 m = 640.0 m
      Inter-element gaps = (4 - 1) = 3 gaps * 150.0 m = 450.0 m
      Total Column Length (CL) = 160 + 640 + 450 = 1250.0 m
      Road Space (RS) = 1250 * 1.10 = 1375.0 m
      Pass Time (PT) = 1250.0 / 10.0 = 125.0 s
      Time Distance (TD) = 6000.0 / 10.0 = 600.0 s
      Road Clearance Time (RCT) = TD + PT = 600.0 + 125.0 = 725.0 s
    """
    spec = {
        "march_unit_size": 5,
        "march_units_per_serial": 4,
        "serials_per_column": 1,
        "pace": 10.0,
        "time_gap": 4.0,
        "element_time_gap": 15.0,
        "safety_factor": 0.10,
    }

    summary = convoy_metrics.doctrinal_convoy_summary(
        spec, route_distance=6000.0, platform_length=8.0
    )

    assert summary["column_length"] == pytest.approx(1250.0)
    assert summary["road_space"] == pytest.approx(1375.0)
    assert summary["pass_time"] == pytest.approx(125.0)
    assert summary["time_distance"] == pytest.approx(600.0)
    assert summary["road_clearance_time"] == pytest.approx(725.0)


# ---- 6. Measured Column Length Geometry -------------------------------------

def test_measured_column_length():
    """Empirical column length projects 1D/2D vehicle positions + bumper extents."""
    # 5 vehicles spaced 40 m apart along x: x = [160, 120, 80, 40, 0]
    # Physical length of each = 6.0 m
    # Lead front bumper = 160 + 3 = 163 m
    # Trail rear bumper = 0 - 3 = -3 m
    # Expected Column Length = 163 - (-3) = 166.0 m
    x = np.array([160.0, 120.0, 80.0, 40.0, 0.0])
    y = np.zeros(5)

    cl = convoy_metrics.measured_column_length(x, y, lengths=6.0)
    assert cl == pytest.approx(166.0)

    # Single vehicle: column length equals its own length
    cl_single = convoy_metrics.measured_column_length(np.array([50.0]), np.array([50.0]), lengths=7.0)
    assert cl_single == pytest.approx(7.0)

    # Empty mask
    cl_empty = convoy_metrics.measured_column_length(x, y, lengths=6.0, mask=np.zeros(5, bool))
    assert cl_empty == 0.0


# ---- 7. Empirical Passage Tracker -------------------------------------------

def test_passage_tracker_pass_time():
    """PassageTracker records crossing times and measures empirical pass time and time gaps."""
    tracker = convoy_metrics.PassageTracker(checkpoint_x=100.0)

    # Simulate 3 vehicles crossing x=100 at pace 10 m/s with 4s time gaps
    # Vehicle 0 crosses at t=10.0
    # Vehicle 1 crosses at t=14.0
    # Vehicle 2 crosses at t=18.0
    mask = np.ones(3, bool)

    # Step t=9.0: none crossed
    x_9 = np.array([90.0, 50.0, 10.0])
    tracker.update(9.0, x_9, mask)
    assert tracker.first_cross_t is None

    # Step t=10.0: vehicle 0 crosses
    x_10 = np.array([100.0, 60.0, 20.0])
    tracker.update(10.0, x_10, mask)
    assert tracker.first_cross_t == 10.0

    # Step t=14.0: vehicle 1 crosses
    x_14 = np.array([140.0, 100.0, 60.0])
    tracker.update(14.0, x_14, mask)

    # Step t=18.0: vehicle 2 crosses
    x_18 = np.array([180.0, 140.0, 100.0])
    tracker.update(18.0, x_18, mask)

    assert tracker.measured_pass_time == pytest.approx(8.0)  # 18.0 - 10.0
    assert tracker.measured_time_gaps == pytest.approx([4.0, 4.0])


# ---- 8. Convoy KPIs in Mission Scoring ---------------------------------------

def test_convoy_kpis_in_mission_scoring():
    """A scenario configured with convoy parameters outputs all doctrinal convoy KPIs."""
    scn = load_scenario("scenarios/uc3_convoy.json")
    res = run_mission(scn, seed=42)

    expected_kpis = [
        "convoy_column_length",
        "convoy_road_space",
        "convoy_pass_time",
        "convoy_time_distance",
        "convoy_road_clearance_time",
        "convoy_rate_of_march",
        "convoy_measured_column_length",
    ]

    for kpi in expected_kpis:
        assert kpi in res, f"Missing KPI {kpi} in mission result"
        assert res[kpi] > 0.0, f"KPI {kpi} expected positive, got {res[kpi]}"

    # Verify road clearance time equals time distance plus pass time in the output
    assert res["convoy_road_clearance_time"] == pytest.approx(
        res["convoy_time_distance"] + res["convoy_pass_time"]
    )
