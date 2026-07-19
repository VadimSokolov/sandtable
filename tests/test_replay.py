"""Replay recorder: a trace must faithfully reproduce the run it claims to visualize.

The load-bearing property is that `record_trace` replays `run_mission` step-for-step (same seed,
same RNG draws), so the recorded outcome equals the KPIs the optimizer scored and the animation the
user watches is the actual simulated run, not an approximation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sandtable.replay import record_trace
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

REPO_ROOT = Path(__file__).resolve().parents[1]
UC5_PATH = REPO_ROOT / "scenarios" / "uc5_sensor_swarm.json"


def _outcome_matches(kpi: dict, tr: dict) -> None:
    # Fields the trace exposes must equal run_mission exactly (coverage only to the trace's rounding).
    for k in ("success", "blue_losses", "red_losses", "mission_time"):
        assert float(tr["outcome"][k]) == pytest.approx(float(kpi[k]), abs=0), k
    assert float(tr["outcome"]["detection_coverage"]) == pytest.approx(
        float(kpi["detection_coverage"]), abs=1e-4)


def test_trace_outcome_matches_run_mission_ground(skirmish_scenario):
    """Ground-core scenario (no C2, no air): the recorder is byte-faithful to run_mission."""
    for seed in (0, 3, 7):
        kpi = run_mission(skirmish_scenario, seed=seed)
        tr = record_trace(skirmish_scenario, seed=seed, stride=3)
        _outcome_matches(kpi, tr)


def test_trace_outcome_matches_run_mission_air():
    """UC-5 (UAS swarm + shared-SA relay under EW): recorder faithful on the air/comms path too."""
    scn = load_scenario(str(UC5_PATH))
    for params in ({"n_uas": 6, "comms_level": 0}, {"n_uas": 6, "comms_level": 5}):
        kpi = run_mission(scn, seed=5, params=params)
        tr = record_trace(scn, seed=5, params=params, stride=8)
        _outcome_matches(kpi, tr)


def test_frames_are_well_formed(skirmish_scenario):
    tr = record_trace(skirmish_scenario, seed=1, stride=4)
    n = len(tr["entities"])
    assert n > 0 and len(tr["frames"]) >= 2
    assert tr["frames"][0]["t"] == 0.0
    prev = -1.0
    for f in tr["frames"]:
        assert f["t"] >= prev            # mission clock never runs backward
        prev = f["t"]
        for key in ("x", "y", "alive", "seen", "cq"):
            assert len(f[key]) == n      # every per-entity array matches the entity count
        assert set(f["alive"]) <= {0, 1}
        assert set(f["seen"]) <= {0, 1}


def test_recording_is_deterministic(skirmish_scenario):
    a = record_trace(skirmish_scenario, seed=2, stride=5)
    b = record_trace(skirmish_scenario, seed=2, stride=5)
    assert a["frames"] == b["frames"]
    assert a["outcome"] == b["outcome"]


def test_terrain_is_downsampled(skirmish_scenario):
    tr = record_trace(skirmish_scenario, seed=0, stride=5)
    cover = tr["terrain"]["cover"]
    assert len(cover) <= 40 and len(cover[0]) <= 80    # coarsened for a light payload
    assert all(0.0 <= v <= 1.0 for row in cover for v in row)


def test_entities_carry_static_metadata(skirmish_scenario):
    tr = record_trace(skirmish_scenario, seed=0, stride=5)
    for e in tr["entities"]:
        assert e["side"] in (0, 1)
        assert e["domain"] in (0, 1)
        assert e["sensor_range"] >= 0.0 and e["weapon_range"] >= 0.0
