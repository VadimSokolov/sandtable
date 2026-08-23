"""World rasters and O(1) terrain queries."""
from __future__ import annotations

import pytest
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


def _with_terrain(scn, extra):
    from dataclasses import replace

    return replace(scn, terrain={**scn.terrain, **extra})


def test_the_published_map_is_bit_identical_after_the_profile_knob():
    """Every result in this project was found on the `band` profile, so growing the generator a
    profile selector and a dozen parameters is only admissible if that path did not move. Pinned on
    three seeds and every metric, not on a summary."""
    from sandtable.scenario import load_scenario
    from sandtable.sim import run_mission

    scn = load_scenario("scenarios/sc_span_control.json")
    ref = {0: 0.7504, 3: 0.8146, 7: 0.8000}
    for seed in (0, 3, 7):
        m = run_mission(scn, seed=seed)
        explicit = run_mission(_with_terrain(scn, {"profile": "band"}), seed=seed)
        assert m == explicit                       # naming the default cannot change it
        assert m["operator_utilization"] == pytest.approx(ref[seed], abs=1e-4)


def test_the_three_profiles_are_three_different_maps():
    """The point of the knob. `open` must be UNIFORM, so route bias cannot mean anything on it,
    while still carrying the band profile's own mean cover: the control removes the choice and not
    the protection, because a bare field floors mission success and makes every contrast on it
    unreadable. `chokepoint` must have ground slower than anything the band profile contains,
    because that is what a constriction is."""
    import numpy as np

    from sandtable.scenario import load_scenario
    from sandtable.world import build_world

    scn = load_scenario("scenarios/sc_span_control.json")
    rng = np.random.default_rng(0)
    band = build_world(scn, np.random.default_rng(0))
    op = build_world(_with_terrain(scn, {"profile": "open"}), np.random.default_rng(0))
    ch = build_world(_with_terrain(scn, {"profile": "chokepoint"}), np.random.default_rng(0))
    assert op.cover.min() == op.cover.max()                 # uniform: no lateral choice
    assert op.conceal.min() == op.conceal.max()
    assert band.cover.min() < op.cover.max() < band.cover.max()   # and it is the band's own mean
    assert ch.speed.min() < band.speed.min() - 0.1
    assert ch.cover.max() > band.cover.max() - 1e-9
    assert build_world(scn, rng).speed.shape == band.speed.shape


def test_an_unknown_profile_is_an_error_and_not_a_silent_default():
    import numpy as np
    import pytest as _pt

    from sandtable.scenario import load_scenario
    from sandtable.world import build_world

    scn = load_scenario("scenarios/sc_span_control.json")
    with _pt.raises(ValueError, match="unknown terrain profile"):
        build_world(_with_terrain(scn, {"profile": "ridgeline"}), np.random.default_rng(0))
