"""EW-immune command link (fiber / autonomous terminal guidance).

Opt-in via params["ew_immune_link"]. Off by default it must be a byte-identical no-op; on, it must let
DIRECT human control survive jamming that would otherwise collapse it, while touching nothing in
supervisory mode (which never requests the operator).
"""
from __future__ import annotations

from sandtable.scenario import load_scenario
from sandtable.sim import evaluate, run_mission

SC = load_scenario("scenarios/sc_span_control.json")


def _p(**kw):
    base = {"control_mode": "direct", "comms_level": 4, "n_blue": 4, "n_red": 4}
    base.update(kw)
    return base


def test_off_is_byte_identical():
    """Absent vs explicit-False give identical metrics: the gate's off-path is the original code and
    draws the same RNG stream."""
    for seed in range(8):
        assert run_mission(SC, seed=seed, params=_p()) == run_mission(SC, seed=seed, params=_p(ew_immune_link=False))


def test_immune_link_helps_direct_under_jamming():
    """Under heavy jamming (C4) a direct-control force on an EW-immune link succeeds far more often
    than one on the jammable ladder link, because its operator requests stop being dropped."""
    jammed = evaluate(SC, n_reps=60, params=_p(ew_immune_link=False))
    immune = evaluate(SC, n_reps=60, params=_p(ew_immune_link=True))
    assert immune["success_rate"] >= jammed["success_rate"] + 0.10


def test_immune_link_negligible_when_clear():
    """With clear comms there is nothing to be immune to, so the link buys almost nothing (the tiny
    residual is its fixed latency); the effect must be far smaller than under jamming."""
    clear_j = evaluate(SC, n_reps=60, params=_p(comms_level=0, ew_immune_link=False))
    clear_i = evaluate(SC, n_reps=60, params=_p(comms_level=0, ew_immune_link=True))
    assert clear_i["success_rate"] - clear_j["success_rate"] < 0.15


def test_immune_link_inert_for_supervisory():
    """Supervisory control never requests the operator, so the immune link changes nothing at all."""
    for seed in range(8):
        a = run_mission(SC, seed=seed, params=_p(control_mode="supervisory"))
        b = run_mission(SC, seed=seed, params=_p(control_mode="supervisory", ew_immune_link=True))
        assert a == b
