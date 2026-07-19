"""Low-fidelity motion: vectorized unicycle kinematics with terrain-limited speed.

Each living entity turns its heading toward its current target (turn-rate limited) and advances at
min(commanded, trafficability) speed. Ground speed is gated by the terrain `speed` raster; air
platforms ignore trafficability. This captures mission-relevant timing, tempo, and formation
geometry without any vehicle dynamics (validated "accurate enough" well below ~0.5 g lateral
acceleration; Polack 2017).
"""
from __future__ import annotations

import numpy as np

from sandtable.entities import GROUND, Entities
from sandtable.world import World


def _wrap(a: np.ndarray) -> np.ndarray:
    """Wrap angle(s) to (-pi, pi]."""
    return (a + np.pi) % (2 * np.pi) - np.pi


def step(ent: Entities, world: World, dt: float, tempo: float = 1.0) -> None:
    """Advance all entities one timestep in place."""
    alive = ent.alive
    dx = ent.tgt_x - ent.x
    dy = ent.tgt_y - ent.y
    dist = np.hypot(dx, dy)

    # turn heading toward the target, limited by turn rate
    desired = np.arctan2(dy, dx)
    dtheta = _wrap(desired - ent.heading)
    max_dtheta = ent.turn_rate * dt
    ent.heading = _wrap(ent.heading + np.clip(dtheta, -max_dtheta, max_dtheta))

    # commanded speed, terrain-gated for ground platforms
    traffic = np.where(ent.domain == GROUND, world.speed_at(ent.x, ent.y), 1.0)
    v = ent.max_speed * float(tempo) * traffic
    # Control-quality tempo penalty (Increment 2): a poorly-controlled or awaiting agent
    # hesitates. Neutral at control_quality 1.0, so ground-core scenarios are unaffected.
    q = getattr(ent, "control_quality", None)
    if q is not None:
        v = v * (0.35 + 0.65 * q)
    # do not overshoot the target within a single step
    v = np.minimum(v, dist / dt)
    v = np.where(alive, v, 0.0)

    ent.x = ent.x + v * np.cos(ent.heading) * dt
    ent.y = ent.y + v * np.sin(ent.heading) * dt
    ent.speed = v
