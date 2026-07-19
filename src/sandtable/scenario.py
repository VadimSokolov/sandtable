"""Declarative scenario specification.

A Scenario is a plain, serializable description of a mission-design problem: the world spec, the
platform types, the force laydown, the objective, and a `params` dict of design variables that the
optimizer overrides. It is intentionally data-only so it round-trips through JSON (the `polarisopt`
slave contract passes `params` as JSON) and so a run is a pure function of (scenario, seed).
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from sandtable.entities import AIR, GROUND, Entities


@dataclass
class PlatformType:
    """Per-type platform parameters (denormalized into entity arrays at build time)."""

    name: str
    domain: int = GROUND               # GROUND or AIR
    max_speed: float = 12.0            # m/s
    turn_rate: float = 0.6             # rad/s
    sensor_range: float = 1500.0       # m
    weapon_range: float = 1000.0       # m
    pk_base: float = 0.25              # base probability of kill per opportunity
    hp: float = 1.0
    endurance: float = np.inf          # s (finite for UAS)


@dataclass
class ForceSpec:
    """One group of identical platforms placed on the map."""

    side: int                          # BLUE or RED
    ptype: str                         # key into Scenario.platform_types
    count: int
    spawn: tuple                       # (x, y) group centroid
    spawn_spread: float = 40.0         # m, lateral jitter of spawn
    route: list | None = None          # [(x, y), ...] waypoints (blue); None = static (red)
    formation: str = "column"          # column | line | wedge
    count_param: str | None = None     # if set, scn.params[count_param] overrides count (sweep knob)
    spacing: float | None = None       # m between successive units along the formation (default: formation_spread)


@dataclass
class Objective:
    """Mission objective and success criteria."""

    goal: tuple                        # (x, y) objective location
    goal_radius: float = 120.0         # m, arrival tolerance
    survive_fraction: float = 0.5      # min fraction of the assaulting force that must arrive


@dataclass
class Scenario:
    name: str
    size: tuple                        # (width, height) metres
    platform_types: dict               # name -> PlatformType
    forces: list                       # [ForceSpec, ...]
    objective: Objective
    terrain: dict = field(default_factory=dict)   # spec consumed by world.build_world
    params: dict = field(default_factory=dict)    # design variables (optimizer overrides these)
    dt: float = 1.0                    # s, fixed timestep
    duration: float = 1800.0           # s, max mission time
    id: int = 0                        # stable id for reproducible seeding

    # ---- (de)serialization -------------------------------------------------
    @staticmethod
    def from_dict(d: dict) -> "Scenario":
        ptypes = {k: PlatformType(name=k, **v) for k, v in d["platform_types"].items()}
        forces = [ForceSpec(**f) for f in d["forces"]]
        obj = Objective(**d["objective"])
        return Scenario(
            name=d["name"], size=tuple(d["size"]), platform_types=ptypes, forces=forces,
            objective=obj, terrain=d.get("terrain", {}), params=d.get("params", {}),
            dt=d.get("dt", 1.0), duration=d.get("duration", 1800.0), id=d.get("id", 0),
        )

    def with_params(self, overrides: dict) -> "Scenario":
        """Return a copy with `params` merged (optimizer knobs applied)."""
        merged = {**self.params, **(overrides or {})}
        return replace(copy.deepcopy(self), params=merged)


def load_scenario(path: str | Path) -> Scenario:
    return Scenario.from_dict(json.loads(Path(path).read_text()))


# ---- build entities from the force laydown ---------------------------------
_FORMATION_DIR = {"column": (-1.0, 0.0), "line": (0.0, 1.0), "wedge": (-1.0, 1.0)}


def _force_count(f: ForceSpec, scn: Scenario) -> int:
    """Effective platform count for a force (a `count_param` lets the optimizer sweep N)."""
    if f.count_param is not None and f.count_param in scn.params:
        return max(0, int(scn.params[f.count_param]))
    return f.count


def build_entities(scn: Scenario, rng: np.random.Generator) -> Entities:
    """Instantiate SoA `Entities` from the scenario force specs."""
    total = sum(_force_count(f, scn) for f in scn.forces)
    e = Entities.allocate(total)
    ptype_index = {name: i for i, name in enumerate(scn.platform_types)}
    spread = float(scn.params.get("formation_spread", 30.0))

    i = 0
    for f in scn.forces:
        pt = scn.platform_types[f.ptype]
        fdir = _FORMATION_DIR.get(f.formation, (-1.0, 0.0))
        gap = f.spacing if f.spacing is not None else spread   # per-force unit spacing (depth of laydown)
        cx, cy = f.spawn
        for k in range(_force_count(f, scn)):
            # place along the formation direction with small lateral jitter
            ox = fdir[0] * gap * k
            oy = fdir[1] * gap * k + rng.normal(0.0, f.spawn_spread * 0.1)
            e.x[i], e.y[i] = cx + ox, cy + oy
            e.z[i] = 200.0 if pt.domain == AIR else 0.0
            e.side[i] = f.side
            e.ptype[i] = ptype_index[f.ptype]
            e.role[i] = 0 if k == 0 else 1
            e.leader[i] = -1 if k == 0 else (i - k)     # first entity of the group is leader
            e.hp[i] = pt.hp
            e.fuel[i] = pt.endurance
            e.max_speed[i] = pt.max_speed
            e.turn_rate[i] = pt.turn_rate
            e.sensor_range[i] = pt.sensor_range
            e.weapon_range[i] = pt.weapon_range
            e.pk_base[i] = pt.pk_base
            e.domain[i] = pt.domain
            # initial heading toward objective (blue) or toward map centre (red)
            gx, gy = scn.objective.goal
            e.heading[i] = np.arctan2(gy - e.y[i], gx - e.x[i])
            i += 1
    return e
