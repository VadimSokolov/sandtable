"""Unicycle motion: progress toward target, terrain-gated ground speed, wrapped heading."""
from __future__ import annotations

import numpy as np

from sandtable.entities import GROUND, Entities
from sandtable import motion


def test_step_moves_entity_toward_target(make_world):
    w = make_world(speed=1.0)
    e = Entities.allocate(1)
    e.x[0], e.y[0] = 100.0, 500.0
    e.tgt_x[0], e.tgt_y[0] = 1900.0, 500.0
    e.max_speed[0], e.turn_rate[0], e.domain[0] = 10.0, 1.0, GROUND
    e.heading[0] = np.arctan2(0.0, 1.0)   # already pointing at the target

    d0 = float(np.hypot(e.tgt_x[0] - e.x[0], e.tgt_y[0] - e.y[0]))
    motion.step(e, w, dt=1.0, tempo=1.0)
    d1 = float(np.hypot(e.tgt_x[0] - e.x[0], e.tgt_y[0] - e.y[0]))
    assert d1 < d0                        # got closer
    assert e.x[0] > 100.0                 # advanced in +x toward the goal


def test_ground_speed_gated_by_trafficability(make_world):
    traffic = 0.5
    w = make_world(speed=traffic)
    e = Entities.allocate(1)
    e.x[0], e.y[0] = 100.0, 500.0
    e.tgt_x[0], e.tgt_y[0] = 1900.0, 500.0   # far enough that the step is speed-limited, not dist-limited
    e.max_speed[0], e.turn_rate[0], e.domain[0] = 10.0, 1.0, GROUND
    e.heading[0] = np.arctan2(0.0, 1.0)

    v_at = float(w.speed_at(e.x[0], e.y[0]))   # sample BEFORE the entity moves
    motion.step(e, w, dt=1.0, tempo=1.0)
    bound = e.max_speed[0] * v_at
    assert e.speed[0] <= bound + 1e-9          # never exceeds max_speed * trafficability
    assert np.isclose(e.speed[0], bound)       # and the gate actually binds (== max_speed * traffic)


def test_air_platform_ignores_trafficability(make_world):
    from sandtable.entities import AIR

    w = make_world(speed=0.2)   # very slow ground; air should ignore it
    e = Entities.allocate(1)
    e.x[0], e.y[0] = 100.0, 500.0
    e.tgt_x[0], e.tgt_y[0] = 1900.0, 500.0
    e.max_speed[0], e.turn_rate[0], e.domain[0] = 10.0, 1.0, AIR
    e.heading[0] = np.arctan2(0.0, 1.0)

    motion.step(e, w, dt=1.0, tempo=1.0)
    assert np.isclose(e.speed[0], 10.0)   # full commanded speed, unaffected by the speed raster


def test_heading_stays_wrapped(make_world):
    w = make_world(speed=1.0)
    n = 12
    e = Entities.allocate(n)
    r = np.random.default_rng(1)
    e.x[:] = r.uniform(0, 2000, n)
    e.y[:] = r.uniform(0, 1000, n)
    e.tgt_x[:] = r.uniform(0, 2000, n)
    e.tgt_y[:] = r.uniform(0, 1000, n)
    e.heading[:] = r.uniform(-10, 10, n)   # deliberately unwrapped inputs
    e.max_speed[:] = 10.0
    e.turn_rate[:] = 0.6

    motion.step(e, w, dt=1.0, tempo=1.0)
    assert np.all(e.heading > -np.pi) and np.all(e.heading <= np.pi)


def test_dead_entity_does_not_move(make_world):
    w = make_world(speed=1.0)
    e = Entities.allocate(1)
    e.x[0], e.y[0] = 100.0, 500.0
    e.tgt_x[0], e.tgt_y[0] = 1900.0, 500.0
    e.max_speed[0], e.turn_rate[0] = 10.0, 1.0
    e.alive[0] = False
    motion.step(e, w, dt=1.0, tempo=1.0)
    assert e.x[0] == 100.0 and e.speed[0] == 0.0
