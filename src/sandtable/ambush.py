"""Abstract Red ambush template (Issue #18): fire discipline for a static Red force.

This is a fire-control template, not a reconstruction of any battle and not a tactics guide. It adds
three things to a scenario whose Red units already exist: Red units are given an ambush role, they hold
fire until a launch condition, and they cease fire on an order. Nothing else changes: Red does not
move, no kill probability changes, no obstacle or indirect fire is added, and a wreck still does not
block the road.

Roles follow the structure of the public OPFOR ambush description (TC 7-100.2, 9 Dec 2011, 3-147 to
3-148 and 3-159 to 3-161): ambush and support elements fire from the signal and withdraw; the security
element holds fire until the signal and does not withdraw on the order (it "may remain to provide
warning and to delay"). Which Red platform types hold which role is configuration.

Launch: fire is held until a Blue vehicle that Red has seen is within `trigger.radius` of
`trigger.point`. `security_rule` decides which Blue vehicles count: `let_pass` ignores Blue security
vehicles (the ambush lets them go by; GROUND TRUTH: reads `convoy_role`) and `engage` counts any vehicle.
The launch is latched.

Withdrawal: `after_s` seconds after launch, or when the ambush-role Red loss fraction reaches
`loss_fraction`, whichever comes first. Ambush-role units stop firing; support-role units stop
`support_delay_s` later; security-role units never stop. A withdrawn unit does not leave the map.

The template draws no random numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.entities import BLUE, GROUND, RED, Entities

ROLES = ("ambush", "support", "security")
SECURITY_RULES = ("let_pass", "engage")
_KEYS = {"roles", "trigger", "security_rule", "withdraw"}


def resolve_ambush(params: dict | None) -> dict | None:
    """Normalise and validate `params["ambush"]`; None when absent (feature off)."""
    if not params:
        return None
    raw = params.get("ambush")
    if raw is None or raw == "none":
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"ambush must be None, 'none' or a dict, got {raw!r}")
    extra = set(raw) - _KEYS
    if extra:
        raise ValueError(f"unknown ambush keys {sorted(extra)}; allowed {sorted(_KEYS)}")
    roles = raw.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise ValueError("ambush needs a 'roles' dict: role -> list of Red platform type names")
    seen: dict[str, str] = {}
    for role, names in roles.items():
        if role not in ROLES:
            raise ValueError(f"unknown ambush role {role!r}; must be one of {list(ROLES)}")
        if not isinstance(names, (list, tuple)) or not names or not all(isinstance(n, str) for n in names):
            raise ValueError(f"ambush role {role!r} needs a non-empty list of platform type names")
        for n in names:
            if n in seen:
                raise ValueError(f"platform type {n!r} is in two ambush roles ({seen[n]!r}, {role!r})")
            seen[n] = role
    if not any(r in roles for r in ("ambush", "support")):
        raise ValueError("ambush needs at least one 'ambush' or 'support' role to hold and release fire")
    trig = raw.get("trigger")
    if not isinstance(trig, dict) or set(trig) != {"point", "radius"}:
        raise ValueError("ambush trigger must be {'point': [x, y], 'radius': r}")
    pt = trig["point"]
    if not (isinstance(pt, (list, tuple)) and len(pt) == 2 and all(isinstance(v, (int, float)) for v in pt)):
        raise ValueError(f"ambush trigger point must be [x, y], got {pt!r}")
    rad = trig["radius"]
    if isinstance(rad, bool) or not isinstance(rad, (int, float)) or rad <= 0:
        raise ValueError(f"ambush trigger radius must be positive, got {rad!r}")
    rule = raw.get("security_rule", "let_pass")
    if rule not in SECURITY_RULES:
        raise ValueError(f"ambush security_rule must be one of {list(SECURITY_RULES)}, got {rule!r}")
    wd = raw.get("withdraw")
    if wd is not None:
        if not isinstance(wd, dict) or not set(wd) <= {"after_s", "loss_fraction", "support_delay_s"}:
            raise ValueError("ambush withdraw must be a dict of after_s, loss_fraction, support_delay_s")
        if "after_s" not in wd and "loss_fraction" not in wd:
            raise ValueError("ambush withdraw needs after_s and/or loss_fraction")
        if "after_s" in wd and not wd["after_s"] > 0:
            raise ValueError(f"ambush withdraw after_s must be positive, got {wd['after_s']!r}")
        if "loss_fraction" in wd and not 0.0 < wd["loss_fraction"] <= 1.0:
            raise ValueError(f"ambush withdraw loss_fraction must be in (0, 1], got {wd['loss_fraction']!r}")
        if "support_delay_s" in wd and not wd["support_delay_s"] >= 0:
            raise ValueError(f"ambush withdraw support_delay_s must be >= 0, got {wd['support_delay_s']!r}")
    return {"roles": {r: tuple(v) for r, v in roles.items()}, "point": (float(pt[0]), float(pt[1])),
            "radius": float(rad), "security_rule": rule,
            "after_s": None if not wd or "after_s" not in wd else float(wd["after_s"]),
            "loss_fraction": None if not wd or "loss_fraction" not in wd else float(wd["loss_fraction"]),
            "support_delay_s": 0.0 if not wd else float(wd.get("support_delay_s", 0.0)),
            "ground_truth": ("security_rule(let_pass)",) if rule == "let_pass" else ()}


@dataclass
class Ambush:
    cfg: dict
    role: np.ndarray                 # int8 per entity: index into ROLES, -1 = not in the template
    n_ambush0: int
    launched: bool = False
    launch_step: int = -1
    withdraw_step: int = -1
    support_withdrawn: bool = False
    ambush_withdrawn: bool = False
    held_steps: int = 0              # Red-ticks of fire held before launch


def build_ambush(scn, ent: Entities) -> Ambush | None:
    cfg = resolve_ambush(scn.params)
    if cfg is None:
        return None
    names = list(scn.platform_types)
    role = np.full(ent.n, -1, np.int8)
    for r, ptypes in cfg["roles"].items():
        for p in ptypes:
            if p not in names:
                raise ValueError(f"ambush role {r!r} names unknown platform type {p!r}")
            role[(ent.ptype == names.index(p)) & (ent.side == RED)] = ROLES.index(r)
    return Ambush(cfg=cfg, role=role, n_ambush0=int((role == ROLES.index("ambush")).sum()))


def step(ent: Entities, amb: Ambush, k: int, dt: float) -> np.ndarray:
    """Advance the template one tick and return the mask of Red entities that must hold fire."""
    cfg = amb.cfg
    t = k * dt
    ia, isup, isec = (ROLES.index(r) for r in ROLES)
    if not amb.launched:
        veh = (ent.side == BLUE) & (ent.domain == GROUND) & ent.alive & ent.seen
        if cfg["security_rule"] == "let_pass":
            from sandtable.convoy import ROLE_SECURITY
            veh = veh & (ent.convoy_role != ROLE_SECURITY)
        if veh.any():
            d = np.hypot(ent.x[veh] - cfg["point"][0], ent.y[veh] - cfg["point"][1])
            if bool((d <= cfg["radius"]).any()):
                amb.launched, amb.launch_step = True, k
    hold = np.zeros(ent.n, bool)
    listed = (amb.role >= 0) & ent.alive
    if not amb.launched:
        hold[listed] = True
        amb.held_steps += int(listed.sum())
        return hold
    since = t - amb.launch_step * dt
    ambush_alive = int(((amb.role == ia) & ent.alive).sum())
    lost = 1.0 - ambush_alive / amb.n_ambush0 if amb.n_ambush0 else 0.0
    if not amb.ambush_withdrawn:
        if (cfg["after_s"] is not None and since >= cfg["after_s"]) or \
                (cfg["loss_fraction"] is not None and amb.n_ambush0 and lost >= cfg["loss_fraction"]):
            amb.ambush_withdrawn, amb.withdraw_step = True, k
    if amb.ambush_withdrawn and not amb.support_withdrawn and \
            (t - amb.withdraw_step * dt) >= cfg["support_delay_s"]:
        amb.support_withdrawn = True
    if amb.ambush_withdrawn:
        hold[(amb.role == ia) & ent.alive] = True
    if amb.support_withdrawn:
        hold[(amb.role == isup) & ent.alive] = True
    return hold


def metrics(amb: Ambush) -> dict:
    return {"ambush_launched": float(amb.launched), "ambush_launch_step": float(amb.launch_step),
            "ambush_withdraw_step": float(amb.withdraw_step), "ambush_held_steps": float(amb.held_steps)}
