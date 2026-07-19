"""World rasters and O(1) terrain queries."""
from __future__ import annotations

import numpy as np

from sandtable.scenario import Objective, PlatformType, Scenario
from sandtable.world import build_world


def _world(rng):
    scn = Scenario(
        name="w",
        size=(6000.0, 3000.0),
        platform_types={"u": PlatformType("u")},
        forces=[],
        objective=Objective(goal=(5750.0, 1500.0)),
        terrain={"cell": 25.0},
    )
    return build_world(scn, rng)


def test_raster_shapes_are_ny_nx(rng):
    w = _world(rng)
    nx = int(np.ceil(6000.0 / w.cell))
    ny = int(np.ceil(3000.0 / w.cell))
    for name, field in (("speed", w.speed), ("cover", w.cover), ("conceal", w.conceal)):
        assert field.shape == (ny, nx), f"{name} shape {field.shape} != {(ny, nx)}"


def test_rasters_within_unit_interval(rng):
    w = _world(rng)
    for name, field in (("speed", w.speed), ("cover", w.cover), ("conceal", w.conceal)):
        assert field.min() >= 0.0 and field.max() <= 1.0, f"{name} out of [0,1]"


def test_covered_and_corridor_lanes_are_distinct(rng):
    w = _world(rng)
    assert w.covered_y != w.corridor_y
    assert abs(w.covered_y - w.corridor_y) > w.cell   # a meaningful lateral separation


def test_sample_is_o1_gather_and_in_bounds(rng):
    w = _world(rng)
    # vectorized gather returns one value per query coordinate...
    xs = np.array([10.0, 3000.0, 5990.0])
    ys = np.array([10.0, 1500.0, 2990.0])
    v = w.speed_at(xs, ys)
    assert v.shape == xs.shape
    assert np.all((v >= 0.0) & (v <= 1.0))
    # ...and out-of-range coordinates are clipped, not errors (constant-time index clamp).
    edge = float(w.speed_at(10 ** 9, 10 ** 9))
    assert 0.0 <= edge <= 1.0


def test_los_stub_returns_true_shaped_bool(rng):
    w = _world(rng)
    x0 = np.array([0.0, 100.0, 200.0])
    y0 = np.zeros(3)
    x1 = np.array([500.0, 600.0, 700.0])
    y1 = np.zeros(3)
    los = w.los(x0, y0, x1, y1)
    assert los.shape == (3,)
    assert los.dtype == bool
    assert bool(los.all())


def test_in_bounds_at_corners(rng):
    w = _world(rng)
    width, height = w.size
    assert bool(w.in_bounds(0.0, 0.0))                       # lower-left corner inside
    assert bool(w.in_bounds(width - 1.0, height - 1.0))      # just inside upper-right
    assert not bool(w.in_bounds(width, height))              # exact upper bound is out (x<w, y<h)
    assert not bool(w.in_bounds(-1.0, 0.0))                  # negative is out
    assert not bool(w.in_bounds(0.0, height + 10.0))
