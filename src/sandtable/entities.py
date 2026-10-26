"""Structure-of-arrays (SoA) entity state.

All agents (ground vehicles, UAS, sensors, targets) live in parallel NumPy arrays, one row per
entity, so every per-step update is a vectorized array operation rather than a per-object Python
loop. Platform-type parameters are denormalized into per-entity arrays for O(1) vectorized access
(AFSIM/OneSAF-style Platform = {mover, sensors, weapons, processor, comms}, flattened to columns).

This module defines the state container and how to build it from a scenario. The per-step model
modules (motion, planning, sensing, engagement) read and mutate this state in place.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Side codes
BLUE = 0
RED = 1

# Domain codes
GROUND = 0
AIR = 1


@dataclass
class Entities:
    """SoA agent state. Every array has shape (N,); index i is one agent across all arrays."""

    # Kinematics (local ENU metres, radians, m/s)
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    heading: np.ndarray
    speed: np.ndarray

    # Identity / status
    side: np.ndarray          # int8: BLUE / RED
    ptype: np.ndarray         # int8: index into the scenario platform-type table
    role: np.ndarray          # int8: 0 = leader, 1 = follower (formation), etc.
    alive: np.ndarray         # bool
    hp: np.ndarray            # float
    fuel: np.ndarray          # float, seconds of endurance remaining (air)

    # Command / movement target (current waypoint the mover steers toward)
    tgt_x: np.ndarray
    tgt_y: np.ndarray

    # Perception: is this entity currently on the opposing side's shared SA map
    seen: np.ndarray          # bool

    # Formation bookkeeping
    leader: np.ndarray        # int32: index of this entity's formation leader, or -1

    # Denormalized platform-type parameters (per entity, for vectorized access)
    max_speed: np.ndarray     # m/s
    turn_rate: np.ndarray     # rad/s
    sensor_range: np.ndarray  # m
    weapon_range: np.ndarray  # m
    pk_base: np.ndarray       # base probability of kill per engagement opportunity
    domain: np.ndarray        # int8: GROUND / AIR

    # Command-and-control / control state (Increment 2). Optional: defaulted in
    # __post_init__ to neutral no-op values so ground-core scenarios with no
    # operator behave byte-identically (control_quality 1.0 is a neutral multiplier).
    control_quality: np.ndarray = None   # float in [0, 1]: how well this agent is being controlled
    await_until: np.ndarray = None       # int32: step index a pending operator request resolves; -1 = idle
    decision_cooldown: np.ndarray = None  # float: steps until this agent's next decision event

    # Kill-web state (Increment 5, prototype). Optional: defaulted to neutral values so scenarios
    # that do not opt into the kill-web mechanics behave byte-identically (0 suppression is a neutral
    # multiplier, infinite ammo never gates fire).
    suppression: np.ndarray = None       # float in [0, 1]: incoming-fire suppression; degrades fire and acquisition
    ammo: np.ndarray = None              # float: rounds remaining (inf = unlimited)

    # Convoy hierarchy state (Increment: Convoy baseline, Issue #8). Optional: defaulted in
    # __post_init__ to -1 (neutral / non-convoy) so non-convoy scenarios behave byte-identically.
    march_unit: np.ndarray = None   # int16: march unit index (0, 1, 2, ...) or -1
    serial: np.ndarray = None       # int16: serial index (0, 1, ...) or -1
    section: np.ndarray = None      # int8: 0=HEAD, 1=MAIN, 2=TRAIL, or -1
    convoy_role: np.ndarray = None  # int8: 0=CONTROL, 1=CARGO, 2=SECURITY, 3=RECOVERY, or -1

    # Convoy pace and speed cap (Increment: Convoy pace, Issue #10). Optional: defaulted in
    # __post_init__ to inf (unconstrained) so non-convoy scenarios behave byte-identically.
    speed_cap: np.ndarray = None    # float: maximum allowed speed (m/s) or inf

    def __post_init__(self) -> None:
        n = self.x.shape[0]
        if self.control_quality is None:
            self.control_quality = np.ones(n)
        if self.await_until is None:
            self.await_until = np.full(n, -1, np.int32)
        if self.decision_cooldown is None:
            self.decision_cooldown = np.zeros(n)
        if self.suppression is None:
            self.suppression = np.zeros(n)
        if self.ammo is None:
            self.ammo = np.full(n, np.inf)

        if self.march_unit is None:
            self.march_unit = np.full(n, -1, np.int16)
        if self.serial is None:
            self.serial = np.full(n, -1, np.int16)
        if self.section is None:
            self.section = np.full(n, -1, np.int8)
        if self.convoy_role is None:
            self.convoy_role = np.full(n, -1, np.int8)
        if self.speed_cap is None:
            self.speed_cap = np.full(n, np.inf)

    @property
    def n(self) -> int:
        return self.x.shape[0]

    def side_mask(self, side: int) -> np.ndarray:
        """Boolean mask of living entities on `side`."""
        return self.alive & (self.side == side)

    @staticmethod
    def allocate(n: int) -> "Entities":
        """Allocate zeroed state for `n` entities."""
        z = lambda dt=np.float64: np.zeros(n, dt)  # noqa: E731
        return Entities(
            x=z(), y=z(), z=z(), heading=z(), speed=z(),
            side=z(np.int8), ptype=z(np.int8), role=z(np.int8),
            alive=np.ones(n, bool), hp=np.ones(n), fuel=np.full(n, np.inf),
            tgt_x=z(), tgt_y=z(), seen=np.zeros(n, bool),
            leader=np.full(n, -1, np.int32),
            max_speed=z(), turn_rate=z(), sensor_range=z(), weapon_range=z(),
            pk_base=z(), domain=z(np.int8),
        )
