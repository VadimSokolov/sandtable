"""Shared pytest fixtures for the sandtable test suite.

Fixtures deliberately favor tiny scenarios, few entities, and short durations so every unit
test stays well under a second. The only heavier test is the sensitivity gate, which loads the
real UC-3 scenario (see test_sensitivity_gate.py).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from sandtable.entities import GROUND
from sandtable.scenario import Scenario

REPO_ROOT = Path(__file__).resolve().parents[1]
UC3_PATH = REPO_ROOT / "scenarios" / "uc3_route_defilade.json"

# A tiny, fast "skirmish" scenario: 4 blue UGV must cross 3 static AT teams to a goal.
# Moderate pk gives run-to-run variation (good for the reproducibility test) while a 250 s
# duration on a 2 km map keeps every replication to a few milliseconds.
SKIRMISH_DICT = {
    "name": "skirmish",
    "id": 5,
    "size": [2000, 1000],
    "dt": 1.0,
    "duration": 250.0,
    "platform_types": {
        "ugv": {
            "domain": GROUND,
            "max_speed": 12.0,
            "turn_rate": 0.6,
            "sensor_range": 1500.0,
            "weapon_range": 1000.0,
            "pk_base": 0.02,
            "hp": 1.0,
        },
        "at": {
            "domain": GROUND,
            "max_speed": 0.0,
            "turn_rate": 0.0,
            "sensor_range": 1800.0,
            "weapon_range": 900.0,
            "pk_base": 0.05,
            "hp": 1.0,
        },
    },
    "forces": [
        {"side": 0, "ptype": "ugv", "count": 4, "spawn": [150, 500], "formation": "column"},
        {"side": 1, "ptype": "at", "count": 3, "spawn": [1000, 500], "formation": "column"},
    ],
    "objective": {"goal": [1850, 500], "goal_radius": 120.0, "survive_fraction": 0.5},
    "terrain": {"cell": 25.0},
    "params": {"route_bias": 0.0},
}


@pytest.fixture
def rng() -> np.random.Generator:
    """A plain, fixed-seed Generator for building worlds / driving stochastic steps."""
    return np.random.default_rng(0)


@pytest.fixture
def skirmish_dict() -> dict:
    """A fresh, mutable copy of the skirmish scenario spec (JSON-shaped)."""
    return copy.deepcopy(SKIRMISH_DICT)


@pytest.fixture
def skirmish_scenario(skirmish_dict) -> Scenario:
    """A fresh Scenario object built from the skirmish spec."""
    return Scenario.from_dict(skirmish_dict)


@pytest.fixture
def uc3_path() -> str:
    """Absolute path to the real UC-3 route-vs-defilade scenario JSON."""
    assert UC3_PATH.exists(), f"missing scenario file: {UC3_PATH}"
    return str(UC3_PATH)


@pytest.fixture
def write_scenario(tmp_path):
    """Return a helper that writes a scenario dict to a temp .json and returns its path."""

    def _write(spec: dict | None = None, name: str = "scn.json") -> str:
        spec = SKIRMISH_DICT if spec is None else spec
        path = tmp_path / name
        path.write_text(json.dumps(spec))
        return str(path)

    return _write


@pytest.fixture
def make_world():
    """Return a factory for a uniform-raster World (constant speed/cover/conceal).

    Building rasters by hand keeps sensing/engagement/motion tests exactly controllable, decoupled
    from build_world's procedural corridor/defilade profile.
    """
    from sandtable.world import World

    def _make(width=2000.0, height=1000.0, cell=25.0, speed=1.0, cover=0.0, conceal=0.0) -> World:
        nx = int(np.ceil(width / cell))
        ny = int(np.ceil(height / cell))
        return World(
            size=(width, height),
            cell=cell,
            speed=np.full((ny, nx), float(speed)),
            cover=np.full((ny, nx), float(cover)),
            conceal=np.full((ny, nx), float(conceal)),
        )

    return _make
