"""Acceptance tests for Convoy Cargo & Delivery Metrics (Issue #9, FM 4-0).

Verifies:
1. Byte-identity when cargo is off (zero regression for legacy scenarios).
2. Strict conservation invariant: C_loaded = C_delivered + C_lost + C_in_transit.
3. Non-cargo vehicle attrition does not lose cargo (resolving the Escort Paradox).
4. Cargo loss is proportional to cargo truck attrition.
5. Delivery threshold triggers mission success and early stopping.
6. Mission score multi-objective metric properly penalizes undelivered cargo.
7. Validation bounds on cargo capacity and delivery fraction.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import metrics, sim
from sandtable.convoy import (
    ROLE_CARGO,
    ROLE_CONTROL,
    ROLE_RECOVERY,
    validate_convoy_spec,
)
from sandtable.entities import BLUE, GROUND
from sandtable.scenario import ForceSpec, Objective, PlatformType, Scenario, build_entities, load_scenario

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



def _make_convoy_scenario(
    march_unit_size: int = 5,
    march_units_per_serial: int = 2,
    cargo_per_vehicle: float | None = None,
    delivery_fraction: float | None = None,
    roles: list[str] | None = None,
    ptype_cargo: float = 0.0,
) -> Scenario:
    """Helper to construct a deterministic scenario for cargo tests."""
    ptypes = {
        "truck": PlatformType(
            name="truck",
            max_speed=20.0,
            hp=1.0,
            domain=GROUND,
            cargo_capacity=ptype_cargo,
        ),
        "red_ambush": PlatformType(
            name="red_ambush",
            max_speed=0.0,
            hp=1.0,
            domain=GROUND,
            weapon_range=200.0,
            pk_base=0.9,
        ),
    }
    n_tot = march_unit_size * march_units_per_serial
    forces = [
        ForceSpec(
            side=BLUE,
            ptype="truck",
            count=n_tot,
            spawn=(0.0, 0.0),
            route=[(1000.0, 0.0)],
            spacing=30.0,
        ),
    ]
    convoy_dict: dict = {
        "march_unit_size": march_unit_size,
        "march_units_per_serial": march_units_per_serial,
        "serials_per_column": 1,
        "pace": 15.0,
    }
    if cargo_per_vehicle is not None:
        convoy_dict["cargo_per_vehicle"] = cargo_per_vehicle
    if delivery_fraction is not None:
        convoy_dict["delivery_fraction"] = delivery_fraction
    if roles is not None:
        convoy_dict["roles"] = roles

    params = {"convoy": convoy_dict}
    obj = Objective(
        goal=(1000.0, 0.0),
        goal_radius=120.0,
        survive_fraction=0.5,
        delivery_fraction=delivery_fraction,
    )
    return Scenario(
        name="test_cargo_convoy",
        size=(2000.0, 1000.0),
        platform_types=ptypes,
        forces=forces,
        objective=obj,
        params=params,
        duration=300.0,
        dt=1.0,
    )


def test_cargo_off_is_byte_identical():
    """When cargo is not configured, simulation output is 100% byte-identical."""
    scn = load_scenario("scenarios/uc3_route_defilade.json")
    for seed in range(5):
        run_a = sim.run_mission(scn, seed=seed)
        run_b = sim.run_mission(scn.with_params({"convoy": None}), seed=seed)
        assert same_run(run_a, run_b)
        assert "cargo_loaded" not in run_a
        assert "cargo_delivered" not in run_a
        assert "delivered_frac" not in run_a

    rng = np.random.default_rng(0)
    ent = build_entities(scn, rng)
    assert np.all(ent.cargo == 0.0)
    assert np.all(ent.cargo_delivered == 0.0)


def test_cargo_conservation_invariant():
    """At every point, C_loaded = C_delivered + C_lost + C_in_transit."""
    # 2 march units of 5 vehicles = 10 vehicles total
    # Roles per unit: 1 control, 3 cargo, 1 recovery => 6 cargo trucks total
    roles = ["control", "cargo", "cargo", "cargo", "recovery"]
    scn = _make_convoy_scenario(
        march_unit_size=5,
        march_units_per_serial=2,
        cargo_per_vehicle=5.0,
        roles=roles,
    )
    rng = np.random.default_rng(123)
    ent = build_entities(scn, rng)

    assert ent.n == 10
    assert int((ent.convoy_role == ROLE_CARGO).sum()) == 6
    assert float(ent.cargo[ent.convoy_role == ROLE_CARGO].sum()) == 30.0
    assert float(ent.cargo[ent.convoy_role == ROLE_CONTROL].sum()) == 0.0
    assert float(ent.cargo[ent.convoy_role == ROLE_RECOVERY].sum()) == 0.0

    c_loaded = float(ent.cargo[ent.side == BLUE].sum())
    assert c_loaded == 30.0

    # Simulate intermediate state:
    # 2 cargo trucks delivered (10 tons)
    # 2 cargo trucks destroyed (10 tons)
    # 2 cargo trucks in transit (10 tons)
    cargo_indices = np.where(ent.convoy_role == ROLE_CARGO)[0]
    delivered_idx = cargo_indices[:2]
    dead_idx = cargo_indices[2:4]
    transit_idx = cargo_indices[4:]
    assert len(transit_idx) == 2

    for idx in delivered_idx:
        ent.cargo_delivered[idx] = ent.cargo[idx]
    for idx in dead_idx:
        ent.alive[idx] = 0

    init_counts = {BLUE: 10, 1: 0}
    res = metrics.compute(scn, init_counts, ent, t_reached=100.0, t_elapsed=100.0)

    assert res["cargo_loaded"] == 30.0
    assert res["cargo_delivered"] == 10.0
    assert res["cargo_lost"] == 10.0
    assert res["cargo_in_transit"] == 10.0
    assert abs(res["cargo_loaded"] - (res["cargo_delivered"] + res["cargo_lost"] + res["cargo_in_transit"])) < 1e-6
    assert pytest.approx(res["delivered_frac"], 1e-6) == 10.0 / 30.0


def test_non_cargo_attrition_preserves_cargo():
    """Killing 100% of gun trucks/control results in 0 cargo lost (Escort Paradox fixed)."""
    # 2 march units of 5 vehicles = 10 vehicles total
    # Roles per unit: control, security, cargo, cargo, recovery => 4 cargo trucks total
    roles = ["control", "security", "cargo", "cargo", "recovery"]
    scn = _make_convoy_scenario(
        march_unit_size=5,
        march_units_per_serial=2,
        cargo_per_vehicle=10.0,
        roles=roles,
    )
    rng = np.random.default_rng(42)
    ent = build_entities(scn, rng)

    # Cargo loaded: 4 trucks * 10 tons = 40 tons
    c_loaded = float(ent.cargo[ent.side == BLUE].sum())
    assert c_loaded == 40.0

    # Kill control, both security gun trucks, and recovery (6 non-cargo vehicles)
    non_cargo_idx = np.where(ent.convoy_role != ROLE_CARGO)[0]
    assert len(non_cargo_idx) == 6
    for idx in non_cargo_idx:
        ent.alive[idx] = 0

    # All cargo trucks reach goal
    cargo_idx = np.where(ent.convoy_role == ROLE_CARGO)[0]
    assert len(cargo_idx) == 4
    for idx in cargo_idx:
        ent.cargo_delivered[idx] = ent.cargo[idx]

    init_counts = {BLUE: 10, 1: 0}
    res = metrics.compute(scn, init_counts, ent, t_reached=150.0, t_elapsed=150.0)

    assert res["cargo_lost"] == 0.0
    assert res["cargo_delivered"] == 40.0
    assert res["delivered_frac"] == 1.0
    assert res["cargo_success"] == 1.0
    assert res["success"] == 1.0
    # 6 out of 10 non-cargo vehicles died (60% vehicle attrition):
    assert res["blue_losses"] == 6.0


def test_cargo_loss_proportional_to_truck_attrition():
    """Destroying cargo trucks reduces delivered payload tonnage proportionally."""
    # 2 march units of 5 vehicles = 10 vehicles total
    # Roles: 1 control, 4 cargo per unit => 8 cargo trucks total
    roles = ["control", "cargo", "cargo", "cargo", "cargo"]
    scn = _make_convoy_scenario(
        march_unit_size=5,
        march_units_per_serial=2,
        cargo_per_vehicle=5.0,
        roles=roles,
        delivery_fraction=0.8,
    )
    rng = np.random.default_rng(99)
    ent = build_entities(scn, rng)

    cargo_idx = np.where(ent.convoy_role == ROLE_CARGO)[0]
    assert len(cargo_idx) == 8
    # 8 * 5.0 = 40 tons loaded
    # Kill 2 out of 8 cargo trucks (10 tons lost)
    for idx in cargo_idx[:2]:
        ent.alive[idx] = 0
    # Remaining 6 cargo trucks reach objective (30 tons delivered)
    for idx in cargo_idx[2:]:
        ent.cargo_delivered[idx] = ent.cargo[idx]

    init_counts = {BLUE: 10, 1: 0}
    res = metrics.compute(scn, init_counts, ent, t_reached=None, t_elapsed=200.0)

    assert res["cargo_loaded"] == 40.0
    assert res["cargo_delivered"] == 30.0
    assert res["cargo_lost"] == 10.0
    assert pytest.approx(res["delivered_frac"], 1e-6) == 30.0 / 40.0  # 75.0%
    # Since 75.0% < 80.0% required:
    assert res["success"] == 0.0
    assert res["cargo_success"] == 0.0


def test_delivery_threshold_stops_mission():
    """Simulation run stops early when the required delivery fraction is met."""
    # 2 march units of 3 vehicles = 6 vehicles total
    # Roles: 1 control, 2 cargo => 4 cargo trucks total
    scn = _make_convoy_scenario(
        march_unit_size=3,
        march_units_per_serial=2,
        cargo_per_vehicle=5.0,
        roles=["control", "cargo", "cargo"],
        delivery_fraction=0.5,
    )
    # Run dynamic mission
    res = sim.run_mission(scn, seed=1)

    assert "cargo_loaded" in res
    assert res["cargo_loaded"] == 20.0  # 4 cargo trucks * 5.0
    assert res["delivered_frac"] >= 0.5
    assert res["success"] == 1.0
    assert res["time_to_objective"] < scn.duration
    assert res["cargo_throughput"] > 0.0


def test_cargo_validation_bounds():
    """Negative or excessive cargo parameters raise ValueError."""
    # Negative cargo capacity on platform
    with pytest.raises(ValueError, match="platform cargo capacity"):
        PlatformType(name="bad", cargo_capacity=-1.0)

    # Invalid delivery fraction on Objective
    with pytest.raises(ValueError, match="delivery fraction"):
        Objective(goal=(0, 0), delivery_fraction=1.5)

    with pytest.raises(ValueError, match="delivery fraction"):
        Objective(goal=(0, 0), delivery_fraction=-0.1)

    # Invalid cargo_per_vehicle in validate_convoy_spec
    with pytest.raises(ValueError, match="cargo per vehicle"):
        validate_convoy_spec({
            "march_unit_size": 5,
            "march_units_per_serial": 2,
            "serials_per_column": 1,
            "cargo_per_vehicle": -5.0,
        })

    with pytest.raises(ValueError, match="cargo per vehicle"):
        validate_convoy_spec({
            "march_unit_size": 5,
            "march_units_per_serial": 2,
            "serials_per_column": 1,
            "cargo_per_vehicle": 150.0,
        })

    # Invalid delivery_fraction in validate_convoy_spec
    with pytest.raises(ValueError, match="delivery fraction"):
        validate_convoy_spec({
            "march_unit_size": 5,
            "march_units_per_serial": 2,
            "serials_per_column": 1,
            "delivery_fraction": 1.2,
        })


def test_mission_score_reflects_cargo_delivery():
    """MissionScoreMetric penalizes failure based on undelivered cargo fraction."""
    metric = MissionScoreMetric(w_fail=1.0, w_time=0.0, w_loss=0.0)

    # Convoy delivering 80% cargo
    out_80 = {
        "success": 1.0,
        "success_rate": 1.0,
        "delivered_frac": 0.8,
        "time_to_objective": 100.0,
        "blue_loss_frac": 0.1,
    }
    score_80 = metric.compute(out_80)[0]
    assert pytest.approx(score_80, 1e-6) == 0.20  # 1.0 - 0.80

    # Convoy delivering 40% cargo
    out_40 = {
        "success": 0.0,
        "success_rate": 0.0,
        "delivered_frac": 0.4,
        "time_to_objective": 100.0,
        "blue_loss_frac": 0.5,
    }
    score_40 = metric.compute(out_40)[0]
    assert pytest.approx(score_40, 1e-6) == 0.60  # 1.0 - 0.40
