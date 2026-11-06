"""Physical lane blocking by destroyed vehicles (Issue #18, Change item 2).

MODEL CONTRACT (minimal; every number is an explicit placeholder, none has a public source)

What makes a wreck block a lane
    A Blue ground vehicle destroyed while `lane_blocking` is declared leaves a wreck at the place it died.
    The wreck blocks the road at that point: along-track coordinate `s_w`, lateral offset `l_w`. Along-track
    is the arc length on the route when the world has one, otherwise the distance along the straight line
    from the Blue ground start centroid to the objective. Red-side wrecks block nothing.

Which vehicles are affected
    Living Blue ground vehicles that are BEHIND the wreck (smaller along-track coordinate) and, when
    `lane_width_m` is given, whose lateral offset is within half a lane width of the wreck's. With
    `lane_width_m` null the wreck blocks the whole road width (a one-lane road). Vehicles already past the
    wreck are unaffected. A vehicle waits at `standoff_m` before the wreck: it is never ordered through it.
    `wreck_roles` (optional) limits which destroyed convoy roles leave a blocking wreck.

When blocking begins and ends
    It begins on the tick after the vehicle is destroyed (the same one-tick latency as the contact reaction)
    and ends `recovery_time_s` seconds after that tick.

What `recovery_time_s` represents
    The time an unmodelled clearing or recovery effort needs to remove the wreck from the lane. It is one
    swept constant, not derived from any recovery vehicle in the convoy (the `recovery` role is not
    consulted), and it is a PLACEHOLDER.

Scope: a ROUTE-ONLY model (or the straight line to the objective). It is not traffic handling
    No queueing, overtaking, passing, lane choice, other streets or street-graph traffic. The street graph is
    never read here; at most the world's route (which a graph may have produced) gives the along-track coordinate.

Bypass or rerouting
    None. A blocked column waits for the whole recovery time. The street graph is not consulted: no other
    street is tried and no vehicle drives around the wreck. A bypass would need runtime path replanning,
    which this model does not have.

Physical blockage is NOT a halt
    A contact halt (Issue #12) and a leader-loss halt (Issue #17) are decisions: they go through
    `behavior.holding`, are counted by `convoy_halt_steps` and `ll_halt_steps`, and end by their own rules.
    A lane block is a constraint of the world: it only moves a vehicle's target back to the stand-off point,
    it does not touch `behavior` state, and it is counted separately (`lane_*` metrics). A vehicle can be
    under all three at once; the lane block never releases a halt and a release never clears a wreck.

The module draws no random numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sandtable.entities import BLUE, GROUND, Entities

_KEYS = {"recovery_time_s", "standoff_m", "lane_width_m", "wreck_roles"}


def resolve_lane_blocking(params: dict | None) -> dict | None:
    """Normalise and validate `params["lane_blocking"]`; None when absent (feature off)."""
    if not params:
        return None
    raw = params.get("lane_blocking")
    if raw is None or raw == "none":
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"lane_blocking must be None, 'none' or a dict, got {raw!r}")
    extra = set(raw) - _KEYS
    if extra:
        raise ValueError(f"unknown lane_blocking keys {sorted(extra)}; allowed {sorted(_KEYS)}")
    out = {}
    for key in ("recovery_time_s", "standoff_m"):
        v = raw.get(key)
        if v is None:
            raise ValueError(f"lane_blocking needs '{key}' (no default: it is a placeholder, state it)")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
            raise ValueError(f"lane_blocking {key} must be positive, got {v!r}")
        out[key] = float(v)
    lw = raw.get("lane_width_m")
    if lw is not None and (isinstance(lw, bool) or not isinstance(lw, (int, float)) or not lw > 0):
        raise ValueError(f"lane_blocking lane_width_m must be positive or null, got {lw!r}")
    out["lane_width_m"] = None if lw is None else float(lw)
    roles = raw.get("wreck_roles")
    if roles is not None:
        from sandtable.convoy import ROLE_MAP
        if not isinstance(roles, (list, tuple)) or not roles or any(r not in ROLE_MAP for r in roles):
            raise ValueError(f"lane_blocking wreck_roles must be a non-empty list from {sorted(ROLE_MAP)}")
        out["wreck_roles"] = tuple(roles)
    else:
        out["wreck_roles"] = None
    return out


@dataclass
class Wreck:
    s: float            # along-track coordinate
    lat: float          # lateral offset
    t_start: float      # seconds; blocking begins
    t_end: float        # seconds; blocking ends (exclusive)


@dataclass
class LaneBlock:
    cfg: dict
    origin: tuple
    u: tuple                      # unit vector origin -> objective
    route: object                 # RoutePolyline or None
    prev_alive: np.ndarray
    dt: float = 1.0
    wrecks: list = field(default_factory=list)
    blockages: int = 0
    block_steps: int = 0          # ticks with at least one active wreck
    blocked_vehicle_steps: int = 0   # vehicle-ticks whose target was pulled back to the stand-off point
    first_block_step: int = -1


def build_lane_block(scn, ent: Entities, world) -> LaneBlock | None:
    cfg = resolve_lane_blocking(scn.params)
    if cfg is None:
        return None
    bg = (ent.side == BLUE) & (ent.domain == GROUND)
    ox, oy = (float(ent.x[bg].mean()), float(ent.y[bg].mean())) if bg.any() else (0.0, 0.0)
    gx, gy = scn.objective.goal
    d = float(np.hypot(gx - ox, gy - oy)) or 1.0
    return LaneBlock(cfg=cfg, origin=(ox, oy), u=((gx - ox) / d, (gy - oy) / d),
                     route=getattr(world, "route", None), prev_alive=ent.alive.copy(), dt=float(scn.dt))


def _coords(lb: LaneBlock, x, y):
    """(along-track, lateral) of points."""
    if lb.route is not None:
        s, lat = lb.route.project(x, y)
        return np.asarray(s, float), np.asarray(lat, float)
    dx, dy = np.asarray(x, float) - lb.origin[0], np.asarray(y, float) - lb.origin[1]
    return dx * lb.u[0] + dy * lb.u[1], -dx * lb.u[1] + dy * lb.u[0]


def update(ent: Entities, lb: LaneBlock, k: int, dt: float) -> None:
    """Register wrecks of Blue ground vehicles destroyed since the last tick."""
    died = lb.prev_alive & ~ent.alive & (ent.side == BLUE) & (ent.domain == GROUND)
    lb.prev_alive = ent.alive.copy()
    roles = lb.cfg["wreck_roles"]
    if roles is not None:
        from sandtable.convoy import ROLE_MAP
        died = died & np.isin(ent.convoy_role, [ROLE_MAP[r] for r in roles])
    idx = np.nonzero(died)[0]
    if idx.size == 0:
        return
    s, lat = _coords(lb, ent.x[idx], ent.y[idx])
    t0 = k * dt
    for si, li in zip(s, lat):
        lb.wrecks.append(Wreck(float(si), float(li), t0, t0 + lb.cfg["recovery_time_s"]))
        lb.blockages += 1


def active(lb: LaneBlock, k: int, dt: float) -> list:
    t = k * dt
    return [w for w in lb.wrecks if w.t_start <= t < w.t_end]


def apply(ent: Entities, lb: LaneBlock, k: int, dt: float, tx: np.ndarray, ty: np.ndarray) -> None:
    """Pull the targets of vehicles behind an active wreck back to the stand-off point, in place."""
    act = active(lb, k, dt)
    if not act:
        return
    lb.block_steps += 1
    if lb.first_block_step < 0:
        lb.first_block_step = k
    veh = np.nonzero((ent.side == BLUE) & (ent.domain == GROUND) & ent.alive)[0]
    if veh.size == 0:
        return
    s, lat = _coords(lb, ent.x[veh], ent.y[veh])
    s_stop = np.full(veh.size, np.inf)
    half = None if lb.cfg["lane_width_m"] is None else lb.cfg["lane_width_m"] / 2.0
    for w in act:
        hit = s < w.s
        if half is not None:
            hit = hit & (np.abs(lat - w.lat) <= half)
        s_stop = np.where(hit, np.minimum(s_stop, w.s - lb.cfg["standoff_m"]), s_stop)
    capped = np.isfinite(s_stop)
    if not capped.any():
        return
    ts, _ = _coords(lb, tx[veh], ty[veh])
    over = capped & (ts > s_stop)
    if not over.any():
        return
    i = veh[over]
    if lb.route is not None:
        px, py, _ = lb.route.point_at(np.maximum(s_stop[over], s[over]))     # inside the zone: hold, never reverse
        tx[i], ty[i] = px, py
    else:
        ahead = np.maximum(s_stop[over] - s[over], 0.0)
        tx[i] = ent.x[i] + lb.u[0] * ahead
        ty[i] = ent.y[i] + lb.u[1] * ahead
    lb.blocked_vehicle_steps += int(over.sum())


def metrics(lb: LaneBlock) -> dict:
    return {"lane_blockages": float(lb.blockages), "lane_block_steps": float(lb.block_steps),
            "lane_blocked_vehicle_steps": float(lb.blocked_vehicle_steps),
            "lane_first_block_step": float(lb.first_block_step),
            "lane_last_release_step": float(max(w.t_end for w in lb.wrecks) / lb.dt) if lb.wrecks else -1.0}
