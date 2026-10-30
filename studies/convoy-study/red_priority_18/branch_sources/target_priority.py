"""Red target priority (Issue #18): which eligible Blue vehicle a Red shooter fires at.

Eligibility and priority are separate. `engagement._side_damage` first builds the set of targets a
shooter may fire at (alive, seen, in weapon range, in line of sight, ground domain, shooter has
ammunition). Priority only chooses among those. It never widens the set, so it cannot bypass sensing,
range, LOS or ammunition.

The legacy rule is "nearest eligible target". A priority is an ordered list of target classes; a shooter
fires at the nearest eligible target of the first class that has one, and at the nearest eligible
target overall when none of the classes does. Ties go to the lowest entity index, so the selection is
deterministic and draws no random numbers; the number of kill draws is unchanged, so the RNG stream
keeps its length.

Classes (`order` entries):
  ends      the head and the trail of the column (see `end_definition` and `ends_basis`)
  security  Blue security vehicles                          GROUND TRUTH: reads `convoy_role`
  control   Blue control vehicles                           GROUND TRUTH: reads `convoy_role`
  armed     Blue vehicles with a weapon and a kill prob.    assumes Red can tell armed from unarmed
  armored   Blue vehicles with initial hp >= `armored_hp`   assumes Red can tell armored vehicles

Head and trail are defined two ways:
  position  the Blue convoy vehicle nearest to, and farthest from, the objective: a physical reading
            that follows the vehicles as they move and as they are lost
  identity  the current head (`leader == -1`) of the first occupied march unit and the last-indexed
            vehicle of the last occupied march unit: an organizational reading that follows
            succession (Issue #8, #17) and regrouping; it assumes index order is column order

`ends_basis` says which vehicles the ends are taken over: `seen` (only vehicles on Red's picture, the
observable reading) or `column` (the whole living column, a ground-truth assumption).

Nothing here adds a combat mechanic: a wreck does not block the road, and a priority does not change
any kill probability. A policy that "works" only does so by changing WHICH vehicle is shot.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sandtable.entities import BLUE, GROUND, Entities

CLASSES = ("ends", "security", "control", "armed", "armored")
GROUND_TRUTH_CLASSES = ("security", "control")
ATTRIBUTE_CLASSES = ("armed", "armored")
END_DEFINITIONS = ("position", "identity")
ENDS_BASES = ("seen", "column")
_KEYS = {"order", "end_definition", "ends_basis", "armored_hp", "applies_to"}


def resolve_target_priority(params: dict | None) -> dict | None:
    """Normalise and validate `params["target_priority"]`; None when absent (feature off).

    An empty `order` is a reporting-only configuration: the legacy rule still selects, and the
    end-vehicle statistics are collected.
    """
    if not params:
        return None
    raw = params.get("target_priority")
    if raw is None or raw == "none":
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"target_priority must be None, 'none' or a dict, got {raw!r}")
    extra = set(raw) - _KEYS
    if extra:
        raise ValueError(f"unknown target_priority keys {sorted(extra)}; allowed {sorted(_KEYS)}")
    order = raw.get("order")
    if not isinstance(order, (list, tuple)):
        raise ValueError("target_priority needs an 'order' list (empty = report only)")
    if len(set(order)) != len(order):
        raise ValueError(f"target_priority order has duplicates: {list(order)}")
    for c in order:
        if c not in CLASSES:
            raise ValueError(f"unknown target class {c!r}; must be one of {list(CLASSES)}")
    edef = raw.get("end_definition", "position")
    if edef not in END_DEFINITIONS:
        raise ValueError(f"target_priority end_definition must be one of {list(END_DEFINITIONS)}, got {edef!r}")
    basis = raw.get("ends_basis", "seen")
    if basis not in ENDS_BASES:
        raise ValueError(f"target_priority ends_basis must be one of {list(ENDS_BASES)}, got {basis!r}")
    hp = raw.get("armored_hp")
    if "armored" in order:
        if hp is None or isinstance(hp, bool) or not isinstance(hp, (int, float)) or hp <= 0:
            raise ValueError("target_priority class 'armored' needs a positive 'armored_hp' (no default: "
                             "the repository has no armor attribute)")
    elif hp is not None:
        raise ValueError("target_priority armored_hp applies only when 'armored' is in order")
    applies = raw.get("applies_to")
    if applies is not None and (not isinstance(applies, (list, tuple)) or not applies
                                or not all(isinstance(a, str) for a in applies)):
        raise ValueError("target_priority applies_to must be a non-empty list of platform type names")
    truth = [c for c in order if c in GROUND_TRUTH_CLASSES]
    if "ends" in order and basis == "column":
        truth.append("ends(column basis)")
    return {"order": tuple(order), "end_definition": edef, "ends_basis": basis,
            "armored_hp": None if hp is None else float(hp),
            "applies_to": None if applies is None else tuple(applies),
            "ground_truth": tuple(truth),
            "attribute_knowledge": tuple(c for c in order if c in ATTRIBUTE_CLASSES)}


@dataclass
class Prio:
    cfg: dict
    goal: tuple
    hp0: np.ndarray
    applies: np.ndarray | None          # bool per entity: shooters that use the priority (None = all Red)
    head: int = -1                      # entity index of the head this tick (-1 none)
    trail: int = -1
    shots: np.ndarray = None            # per class (+1 fallback): shots aimed at that class
    kills: np.ndarray = None            # per class (+1 fallback): kill draws that hit
    targeted: np.ndarray = None         # bool per entity: aimed at at least once
    targeted_head: int = 0
    targeted_trail: int = 0
    head_destroyed: int = 0
    trail_destroyed: int = 0
    end_steps: int = 0                  # ticks with at least one end defined
    cur_k: int = 0                      # tick index of the engagement in progress (set by `begin_step`)
    first_shot_step: int = -1
    last_shot_step: int = -1            # last tick on which any priority-path Red shooter fired
    _ends_now: tuple = field(default=(-1, -1))

    def __post_init__(self) -> None:
        k = len(self.cfg["order"]) + 1
        self.shots = np.zeros(k, np.int64)
        self.kills = np.zeros(k, np.int64)
        self.targeted = np.zeros(len(self.hp0), bool)


def build_target_priority(scn, ent: Entities) -> Prio | None:
    cfg = resolve_target_priority(scn.params)
    if cfg is None:
        return None
    applies = None
    if cfg["applies_to"] is not None:
        names = list(scn.platform_types)
        unknown = [a for a in cfg["applies_to"] if a not in names]
        if unknown:
            raise ValueError(f"target_priority applies_to names unknown platform types {unknown}")
        idx = [names.index(a) for a in cfg["applies_to"]]
        applies = np.isin(ent.ptype, idx)
    return Prio(cfg=cfg, goal=tuple(scn.objective.goal), hp0=ent.hp.copy(), applies=applies)


def _column(ent: Entities, seen_only: bool) -> np.ndarray:
    """Indices of the Blue ground vehicles that make up the column (convoy vehicles when there are any)."""
    veh = (ent.side == BLUE) & (ent.domain == GROUND) & ent.alive
    cv = veh & (ent.convoy_role >= 0)
    if cv.any():
        veh = cv
    if seen_only:
        veh = veh & ent.seen
    return np.nonzero(veh)[0]


def column_ends(ent: Entities, goal: tuple, definition: str, basis: str) -> tuple[int, int]:
    """(head, trail) entity indices under the chosen definition and basis; -1 when the set is empty."""
    idx = _column(ent, basis == "seen")
    if idx.size == 0:
        return -1, -1
    if definition == "identity" and (ent.march_unit[idx] >= 0).all():
        key = ent.serial[idx].astype(np.int64) * 10000 + ent.march_unit[idx].astype(np.int64)
        first = idx[key == key.min()]
        heads = first[ent.leader[first] == -1]
        head = int(heads[0] if heads.size else first[0])
        last = idx[key == key.max()]
        return head, int(last.max())
    d = np.hypot(ent.x[idx] - goal[0], ent.y[idx] - goal[1])
    return int(idx[int(np.argmin(d))]), int(idx[int(np.argmax(d))])    # first index wins a tie


def begin_step(ent: Entities, prio: Prio, k: int | None = None) -> None:
    """Fix this tick's column ends before anyone fires. `k` (optional) stamps the shots with the tick."""
    if k is not None:
        prio.cur_k = k
    prio.head, prio.trail = column_ends(ent, prio.goal, prio.cfg["end_definition"], prio.cfg["ends_basis"])
    if prio.head >= 0:
        prio.end_steps += 1


def end_step(ent: Entities, prio: Prio) -> None:
    """Count end vehicles destroyed this tick (read after damage is applied)."""
    if prio.head >= 0 and not ent.alive[prio.head]:
        prio.head_destroyed += 1
    if prio.trail >= 0 and prio.trail != prio.head and not ent.alive[prio.trail]:
        prio.trail_destroyed += 1


def _class_mask(ent: Entities, prio: Prio, name: str) -> np.ndarray:
    n = ent.n
    if name == "ends":
        m = np.zeros(n, bool)
        for i in (prio.head, prio.trail):
            if i >= 0:
                m[i] = True
        return m
    if name == "security":
        from sandtable.convoy import ROLE_SECURITY
        return ent.convoy_role == ROLE_SECURITY
    if name == "control":
        from sandtable.convoy import ROLE_CONTROL
        return ent.convoy_role == ROLE_CONTROL
    if name == "armed":
        return (ent.weapon_range > 0) & (ent.pk_base > 0)
    return prio.hp0 >= prio.cfg["armored_hp"]


def select(ent: Entities, prio: Prio, engageable: np.ndarray, dist: np.ndarray,
           shooter_idx: np.ndarray, legacy_target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (target_idx, class_idx) for the shooters in `shooter_idx`.

    `engageable` is the eligibility matrix from the engagement step; only its True cells can be chosen.
    `legacy_target` is the nearest-eligible choice, kept for shooters the policy does not apply to and
    for shooters none of the classes reaches. class_idx == len(order) marks a legacy/fallback shot.
    """
    order = prio.cfg["order"]
    target = legacy_target.copy()
    cls = np.full(shooter_idx.size, len(order), np.int64)
    use = np.ones(shooter_idx.size, bool) if prio.applies is None else prio.applies[shooter_idx]
    unresolved = use.copy()
    d = np.where(engageable[shooter_idx], dist[shooter_idx], np.inf)
    for ci, name in enumerate(order):
        if not unresolved.any():
            break
        dm = np.where(_class_mask(ent, prio, name)[None, :], d, np.inf)
        has = np.isfinite(dm).any(axis=1) & unresolved
        if has.any():
            target[has] = np.argmin(dm[has], axis=1)         # lowest index wins a distance tie
            cls[has] = ci
            unresolved &= ~has
    return target, cls


def record(prio: Prio, target: np.ndarray, cls: np.ndarray, killed: np.ndarray) -> None:
    if target.size:
        if prio.first_shot_step < 0:
            prio.first_shot_step = prio.cur_k
        prio.last_shot_step = prio.cur_k
    np.add.at(prio.shots, cls, 1)
    np.add.at(prio.kills, cls[killed], 1)
    prio.targeted[target] = True
    prio.targeted_head += int((target == prio.head).sum()) if prio.head >= 0 else 0
    prio.targeted_trail += int((target == prio.trail).sum()) if prio.trail >= 0 and prio.trail != prio.head else 0


def metrics(prio: Prio) -> dict:
    """Policy KPIs. `tp_vehicles_targeted` counts distinct Blue vehicles aimed at; it is not the number
    destroyed (`blue_losses`), and a kill draw can miss."""
    order = prio.cfg["order"]
    total = int(prio.shots.sum())
    out = {
        "tp_shots": float(total),
        "tp_priority_shots": float(prio.shots[:-1].sum()),
        "tp_fallback_shots": float(prio.shots[-1]),
        "tp_activation_frac": float(prio.shots[:-1].sum() / total) if total else 0.0,
        "tp_vehicles_targeted": float(prio.targeted.sum()),
        "tp_targeted_head": float(prio.targeted_head),
        "tp_targeted_trail": float(prio.targeted_trail),
        "tp_head_destroyed": float(prio.head_destroyed),
        "tp_trail_destroyed": float(prio.trail_destroyed),
        "tp_end_steps": float(prio.end_steps),
        "tp_first_shot_step": float(prio.first_shot_step),
        "tp_last_shot_step": float(prio.last_shot_step),
    }
    for ci, name in enumerate(order):
        out[f"tp_shots_{name}"] = float(prio.shots[ci])
        out[f"tp_kills_{name}"] = float(prio.kills[ci])
    return out
