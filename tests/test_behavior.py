"""Blue behavior layer (CR-1), teleoperation stop semantics (CR-2), intervention rate (CR-4)."""
from __future__ import annotations

import numpy as np
import pytest

from sandtable.scenario import load_scenario
from conftest import same_run
from sandtable.sim import evaluate, run_mission

SPAN = "scenarios/sc_span_control.json"
ALL_SCN = ["scenarios/sc_span_control.json", "scenarios/uc3_route_defilade.json",
           "scenarios/uc5_sensor_swarm.json", "scenarios/uc7_spoofed_advance.json"]


def test_layer_off_is_byte_identical():
    """The opt-in contract: blue_behavior unset must reproduce the previous build exactly."""
    for path in ALL_SCN:
        scn = load_scenario(path)
        for seed in range(4):
            base = run_mission(scn, seed=seed)
            explicit = run_mission(scn, seed=seed, params={"blue_behavior": None})
            assert same_run(base, explicit), f"{path} seed {seed}"


def test_new_metric_keys_are_zero_when_layers_absent():
    """Every recorded number must be unchanged, so the new families default to exactly 0.0."""
    m = run_mission(load_scenario("scenarios/uc3_route_defilade.json"), seed=0)
    for k in ("interventions", "intervention_rate", "operator_utilization",
              "mean_wait", "wait_p95", "queue_depth_mean"):
        assert m[k] == 0.0, f"{k} = {m[k]!r}, expected 0.0 with no C2 or behaviour layer"


def test_supervisory_auto_reduces_to_waypoint():
    """CR-1 acceptance 3: supervisory maps to WAYPOINT, which is exactly the pre-change script.

    If this fails the mode mapping is wrong, not the physics.
    """
    scn = load_scenario(SPAN)
    for seed in range(4):
        base = run_mission(scn, seed=seed, params={"control_mode": "supervisory"})
        auto = run_mission(scn, seed=seed,
                           params={"control_mode": "supervisory", "blue_behavior": "auto"})
        assert same_run(base, auto), \
            f"seed {seed}: supervisory+auto diverged from the scripted path"


def test_sentry_produces_zero_displacement():
    """CR-1 acceptance 2. Expressed purely as a target assignment, so motion needs no override."""
    scn = load_scenario(SPAN)
    m = run_mission(scn, seed=0, params={"control_mode": "direct", "blue_behavior": "sentry"})
    assert m["arrived"] == 0.0
    assert m["time_to_objective"] == pytest.approx(scn.duration)


def test_teleop_stop_false_reproduces_pre_cr2_motion():
    """The old 54.5%-speed semantics stay reachable as an ablation."""
    scn = load_scenario(SPAN)
    for seed in range(3):
        off = run_mission(scn, seed=seed, params={"control_mode": "direct"})
        abl = run_mission(scn, seed=seed, params={"control_mode": "direct",
                                                  "blue_behavior": "auto", "teleop_stop": False})
        assert off["success"] == abl["success"], f"seed {seed}: ablation diverged"


def test_teleop_stop_slows_the_mission_under_jamming():
    """CR-2 acceptance 3: holding on a severed link must cost time at the contested rungs."""
    scn = load_scenario(SPAN)
    for rung in (3, 4, 5):
        stop = evaluate(scn, n_reps=24, seed=0, params={
            "control_mode": "direct", "comms_level": rung, "blue_behavior": "auto",
            "teleop_stop": True})
        roll = evaluate(scn, n_reps=24, seed=0, params={
            "control_mode": "direct", "comms_level": rung, "blue_behavior": "auto",
            "teleop_stop": False})
        assert stop["time_to_objective"] > roll["time_to_objective"], f"C{rung}"


def test_operator_burden_rises_with_jamming_but_the_event_rate_falls():
    """CR-4 / CR-11: jamming lengthens each hold, so counting events understates the burden.

    The first version of this test asserted that `intervention_rate` rises with jamming. It does
    not, and the reason is the finding: a held vehicle is one intervention however long it stays
    held, and jamming pushes every request to the full `patience` timeout. Events per hour
    therefore *fall* while the share of the mission spent stopped rises. `hold_fraction` is the
    quantity that tracks the burden; the rate is reported beside it, never alone.
    """
    scn = load_scenario(SPAN)
    runs = [evaluate(scn, n_reps=16, seed=0, params={
        "control_mode": "direct", "comms_level": r, "blue_behavior": "auto"}
    ) for r in (0, 2, 4)]
    held = [r["hold_fraction"] for r in runs]
    rate = [r["intervention_rate"] for r in runs]
    assert held[0] < held[1] < held[2], f"burden not monotone in jamming: {held}"
    assert rate[2] < rate[0], f"event rate did not fall as holds lengthened: {rate}"


def test_supervisory_never_pays_the_intervention_cost():
    scn = load_scenario(SPAN)

    sup = evaluate(scn, n_reps=16, seed=0, params={
        "control_mode": "supervisory", "comms_level": 5, "blue_behavior": "auto"})
    assert sup["intervention_rate"] == 0.0, "supervisory should never hold for the operator"


def test_operator_utilization_rises_with_span():
    """CR-7 acceptance 2: one server, more agents, more of the mission spent clearing the queue."""
    scn = load_scenario(SPAN)
    us = [evaluate(scn, n_reps=16, seed=0, params={
        "control_mode": "direct", "comms_level": 1, "n_blue": n})["operator_utilization"]
        for n in (2, 4, 8)]
    assert us[0] < us[1] < us[2], f"not monotone in span: {us}"
