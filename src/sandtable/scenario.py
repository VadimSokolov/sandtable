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

from sandtable.entities import AIR, GROUND, BLUE, Entities
from sandtable.convoy import (
    ROLE_CARGO, ROLE_SECURITY, build_convoy_layout, resolve_convoy_spec, resolve_crew_table,
)

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
    length: float = 6.0                # m, physical vehicle length (front to rear bumper)
    cargo_capacity: float = 0.0        # payload capacity in metric tons / units

    def __post_init__(self) -> None:
        if self.length < 0.0:
            raise ValueError(f"platform length must be non-negative, got {self.length}")
        if self.cargo_capacity < 0.0:
            raise ValueError(f"platform cargo capacity must be non-negative, got {self.cargo_capacity}")


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
    delivery_fraction: float | None = None  # min fraction of cargo that must be delivered

    def __post_init__(self) -> None:
        if self.delivery_fraction is not None and not (0.0 <= self.delivery_fraction <= 1.0):
            raise ValueError(f"delivery fraction must be between 0.0 and 1.0, got {self.delivery_fraction}")


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


def _force_count(f: ForceSpec, scn: Scenario, convoy_total: int | None = None,
                 is_convoy: bool = False) -> int:
    """Effective platform count for a force (a `count_param` lets the optimizer sweep N)."""
    if f.count_param is not None and f.count_param in scn.params:
        return max(0, int(scn.params[f.count_param]))
    if is_convoy and convoy_total is not None:
        return convoy_total
    return f.count


def build_entities(scn: Scenario, rng: np.random.Generator) -> Entities:
    """Instantiate SoA `Entities` from the scenario force specs."""
    convoy_spec = resolve_convoy_spec(scn.params)
    convoy_layout = build_convoy_layout(convoy_spec) if convoy_spec else None
    crew_table = resolve_crew_table(convoy_spec)
    sec_pt = None
    if convoy_spec and convoy_spec.get("security_ptype") is not None:
        sec_name = convoy_spec["security_ptype"]
        if sec_name not in scn.platform_types:
            raise ValueError(f"security_ptype {sec_name!r} is not a platform type of this scenario "
                             f"({sorted(scn.platform_types)})")
        sec_pt = scn.platform_types[sec_name]

    convoy_applied = False
    force_counts = []
    for f in scn.forces:
        pt = scn.platform_types[f.ptype]
        is_convoy = (convoy_layout is not None) and (f.side == BLUE) and (pt.domain == GROUND) and (not convoy_applied)
        c_tot = convoy_layout["total"] if is_convoy else None
        n = _force_count(f, scn, convoy_total=c_tot, is_convoy=is_convoy)
        force_counts.append(n)
        if is_convoy:
            convoy_applied = True

    total = sum(force_counts)
    e = Entities.allocate(total)
    ptype_index = {name: i for i, name in enumerate(scn.platform_types)}
    spread = float(scn.params.get("formation_spread", 30.0))

    i = 0
    convoy_applied = False
    for f_idx, f in enumerate(scn.forces):
        pt = scn.platform_types[f.ptype]
        fdir = _FORMATION_DIR.get(f.formation, (-1.0, 0.0))
        gap = f.spacing if f.spacing is not None else spread   # per-force unit spacing (depth of laydown)
        cx, cy = f.spawn

        n_f = force_counts[f_idx]
        is_convoy = (convoy_layout is not None) and (f.side == BLUE) and (pt.domain == GROUND) and (not convoy_applied)

        if is_convoy:
            if n_f != convoy_layout["total"]:
                raise ValueError("Convoy layout size must match force size")
            base_i = i
            convoy_applied = True

        # Check if route polyline is specified for this force or scenario
        f_route_data = getattr(f, "route", None)
        if f_route_data is None and f.side == BLUE and pt.domain == GROUND:
            f_route_data = scn.params.get("route") or scn.terrain.get("route")

        f_route_poly = None
        if f_route_data is not None and f.side == BLUE and pt.domain == GROUND:
            from sandtable.route import RoutePolyline
            f_route_poly = f_route_data if isinstance(f_route_data, RoutePolyline) else RoutePolyline.from_waypoints(f_route_data, start_point=f.spawn)

        s_spawn = 0.0
        if f_route_poly is not None:
            s_spawn, _ = f_route_poly.project(cx, cy)

        for k in range(n_f):
            # place along the formation direction or route with small lateral jitter
            if f_route_poly is not None and f.formation == "column":
                s_k = s_spawn - k * gap
                rx, ry, rth = f_route_poly.point_at(s_k)
                lat_jitter = float(rng.normal(0.0, f.spawn_spread * 0.1))
                e.x[i] = rx - np.sin(rth) * lat_jitter
                e.y[i] = ry + np.cos(rth) * lat_jitter
                e.progress[i] = s_k
                e.heading[i] = rth
            else:
                ox = fdir[0] * gap * k
                oy = fdir[1] * gap * k + rng.normal(0.0, f.spawn_spread * 0.1)
                e.x[i], e.y[i] = cx + ox, cy + oy
            e.z[i] = 200.0 if pt.domain == AIR else 0.0
            e.side[i] = f.side
            e.ptype[i] = ptype_index[f.ptype]

            if is_convoy:
                e.march_unit[i] = convoy_layout["march_unit"][k]
                e.serial[i] = convoy_layout["serial"][k]
                e.section[i] = convoy_layout["section"][k]
                e.convoy_role[i] = convoy_layout["convoy_role"][k]
                e.role[i] = convoy_layout["role"][k]
                e.leader[i] = convoy_layout["leader"][k] + base_i if convoy_layout["leader"][k] != -1 else -1
                pace = convoy_layout.get("pace")
                if pace is not None and e.role[i] == 0:
                    e.speed_cap[i] = float(pace)
                # Cargo payload: only ROLE_CARGO carries freight
                if e.convoy_role[i] == ROLE_CARGO:
                    c_veh = convoy_layout.get("cargo_per_vehicle")
                    if c_veh is not None:
                        e.cargo[i] = float(c_veh)
                    elif pt.cargo_capacity > 0.0:
                        e.cargo[i] = float(pt.cargo_capacity)
                    else:
                        e.cargo[i] = 0.0
                else:
                    e.cargo[i] = 0.0
            else:
                e.role[i] = 0 if k == 0 else 1
                e.leader[i] = -1 if k == 0 else (i - k)
                pace = scn.params.get("pace")
                if pace is not None and e.role[i] == 0:
                    e.speed_cap[i] = float(pace)
                e.cargo[i] = float(pt.cargo_capacity) if pt.cargo_capacity > 0.0 else 0.0

            e.hp[i] = pt.hp
            e.fuel[i] = pt.endurance
            e.max_speed[i] = pt.max_speed
            e.turn_rate[i] = pt.turn_rate
            e.sensor_range[i] = pt.sensor_range
            e.weapon_range[i] = pt.weapon_range
            e.pk_base[i] = pt.pk_base
            e.domain[i] = pt.domain
            e.length[i] = pt.length
            if is_convoy and crew_table is not None:
                e.crew[i] = crew_table[int(e.convoy_role[i])]
            if is_convoy and sec_pt is not None and e.convoy_role[i] == ROLE_SECURITY:
                # Dedicated gun-truck platform (Issue #12): armament and mobility come from
                # `security_ptype`, not from the force's cargo-truck type.
                e.hp[i] = sec_pt.hp
                e.fuel[i] = sec_pt.endurance
                e.max_speed[i] = sec_pt.max_speed
                e.turn_rate[i] = sec_pt.turn_rate
                e.sensor_range[i] = sec_pt.sensor_range
                e.weapon_range[i] = sec_pt.weapon_range
                e.pk_base[i] = sec_pt.pk_base
            # initial heading toward objective (blue) or toward map centre (red)
            if f_route_poly is None or f.formation != "column":
                gx, gy = scn.objective.goal
                e.heading[i] = np.arctan2(gy - e.y[i], gx - e.x[i])
            i += 1
    return e
