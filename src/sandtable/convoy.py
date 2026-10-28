"""Convoy baseline: hierarchy of march units, serials, and vehicle roles (ATP 4-11)."""
from __future__ import annotations

from typing import Any

import numpy as np


# Convoy Sections (within a March Unit)
SECTION_HEAD = 0        # Pacesetter / Lead vehicle
SECTION_MAIN = 1        # Main body (cargo, fuel)
SECTION_TRAIL = 2       # Trail element (recovery, maintenance)

# Convoy Roles
ROLE_CONTROL = 0        # Command & control / pacesetter
ROLE_CARGO = 1          # Logistics / freight
ROLE_SECURITY = 2       # Armed escort / gun truck
ROLE_RECOVERY = 3       # Maintenance / wrecker

ROLE_MAP = {
    "control": ROLE_CONTROL,
    "cargo": ROLE_CARGO,
    "security": ROLE_SECURITY,
    "recovery": ROLE_RECOVERY,
}

CONVOY_KEYS = (
    "march_unit_size",
    "march_units_per_serial",
    "serials_per_column",
    "pace",
    "time_gap",
    "element_time_gap",
    "serial_time_gap",
    "security_ratio",
    "safety_factor",
    "halt_duration",
    "cargo_per_vehicle",
    "delivery_fraction",
    "roles",
    "security_ptype",
    "contact_reaction",
)

# Contact reaction (Issue #12). One generic rule: a trigger set, an action while in contact, and a
# release. `disperse` is reserved for the herringbone increment and is rejected until it exists.
CONTACT_ACTIONS = ("halt", "continue")
CONTACT_TRIGGERS = ("receive_fire", "lead_lost", "detect_range")
CONTACT_HALT_SCOPES = ("all", "non_security")
DEFAULT_DETECT_RANGE_M = 800.0
DEFAULT_CLEAR_S = 15.0


def resolve_contact_reaction(spec: dict | None) -> dict | None:
    """Normalise and validate `spec["contact_reaction"]`.

    Returns None when the reaction is absent (missing, None, or ``"none"``), so every spelling of
    "off" resolves to the same thing and no reaction state is built.
    """
    if not spec:
        return None
    raw = spec.get("contact_reaction")
    if raw is None or raw == "none":
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"contact_reaction must be None, 'none' or a dict, got {raw!r}")

    action = raw.get("action")
    if action == "disperse":
        raise NotImplementedError("contact_reaction action 'disperse' is reserved for the herringbone increment")
    if action not in CONTACT_ACTIONS:
        raise ValueError(f"contact_reaction action must be one of {list(CONTACT_ACTIONS)}, got {action!r}")

    triggers = raw.get("triggers")
    if not isinstance(triggers, (list, tuple)) or not triggers:
        raise ValueError(f"contact_reaction needs a non-empty triggers list from {list(CONTACT_TRIGGERS)}")
    for t in triggers:
        if t not in CONTACT_TRIGGERS:
            raise ValueError(f"unknown contact trigger {t!r}; must be one of {list(CONTACT_TRIGGERS)} "
                             "(ied_event and obstacle have no generator yet)")

    rng_m = float(raw.get("range_m", DEFAULT_DETECT_RANGE_M))
    if not 0.0 < rng_m <= 5000.0:
        raise ValueError(f"contact_reaction range_m must be in (0, 5000] m, got {rng_m}")

    release = raw.get("release", {"rule": "timeout", "clear_s": DEFAULT_CLEAR_S})
    rule = release.get("rule") if isinstance(release, dict) else None
    if rule == "leader_policy":
        raise ValueError("contact_reaction release rule 'leader_policy' depends on the leader-loss "
                         "policy (Issue #17), which is not implemented; use rule 'timeout'")
    if rule != "timeout":
        raise ValueError(f"contact_reaction release rule must be 'timeout', got {rule!r}")
    clear_s = float(release.get("clear_s", DEFAULT_CLEAR_S))
    if not 1.0 <= clear_s <= 3600.0:
        raise ValueError(f"contact_reaction release clear_s must be between 1 and 3600 s, got {clear_s}")

    scope = raw.get("halt_scope", "all")
    if scope not in CONTACT_HALT_SCOPES:
        raise ValueError(f"contact_reaction halt_scope must be one of {list(CONTACT_HALT_SCOPES)}, got {scope!r}")

    return {"action": action, "triggers": tuple(triggers), "range_m": rng_m,
            "clear_s": clear_s, "halt_scope": scope}


def resolve_convoy_spec(params: dict | None) -> dict | None:
    """Resolve convoy configuration from scenario params, merging any flat search overrides.

    Allows optimization frameworks (like polarisopt) to sweep parameters like `pace`, `time_gap`,
    `march_unit_size`, and `security_ratio` as flat design variables without requiring a nested dict.

    Returns None if convoy is not active, preserving 100% byte-identity for non-convoy scenarios.
    """
    if not params:
        return None

    base_spec = params.get("convoy")
    if base_spec is not None:
        spec = dict(base_spec)
    elif "march_unit_size" in params:
        spec = {
            "march_unit_size": params["march_unit_size"],
            "march_units_per_serial": params.get("march_units_per_serial", 2),
            "serials_per_column": params.get("serials_per_column", 1),
        }
    else:
        return None

    # Merge flat overrides
    for k in CONVOY_KEYS:
        if k in params and k != "convoy":
            spec[k] = params[k]

    # If security_ratio or march_unit_size is swept without explicit roles,
    # clear static base roles if security_ratio is specified or length mismatches
    if "roles" not in params:
        if "security_ratio" in params:
            spec.pop("roles", None)
        elif "roles" in spec and "march_unit_size" in params and len(spec["roles"]) != spec["march_unit_size"]:
            spec.pop("roles", None)

    return spec


def resolve_delivery_fraction(scn_or_params: Any) -> float:
    """Return the required delivery fraction for the mission.

    Checks:
    1. scn.objective.delivery_fraction if Scenario object passed.
    2. convoy_spec["delivery_fraction"] or params["delivery_fraction"].
    3. scn.objective.survive_fraction (or 0.5 default).
    """
    if hasattr(scn_or_params, "objective"):
        if scn_or_params.objective.delivery_fraction is not None:
            return float(scn_or_params.objective.delivery_fraction)
        params = scn_or_params.params
        default_frac = float(scn_or_params.objective.survive_fraction)
    elif isinstance(scn_or_params, dict):
        params = scn_or_params
        default_frac = 0.5
    else:
        params = getattr(scn_or_params, "params", {})
        default_frac = 0.5

    spec = resolve_convoy_spec(params)
    if spec and spec.get("delivery_fraction") is not None:
        return float(spec["delivery_fraction"])
    if isinstance(params, dict) and "delivery_fraction" in params:
        return float(params["delivery_fraction"])
    return default_frac



def validate_convoy_spec(spec: dict) -> None:
    """Validate convoy parameters against Army doctrine (ATP 4-11, G-7 & G-11).

    Raises ValueError naming the range if any parameter is outside doctrinal limits.
    """
    march_size = spec.get("march_unit_size")
    if march_size is None or march_size < 1 or march_size > 25:
        raise ValueError(f"march unit size must be between 1 and 25, got {march_size}")

    march_per_serial = spec.get("march_units_per_serial")
    if march_per_serial is None or march_per_serial < 2 or march_per_serial > 5:
        raise ValueError(f"march units per serial must be between 2 and 5, got {march_per_serial}")

    serials_per_column = spec.get("serials_per_column")
    if serials_per_column is None or serials_per_column < 1 or serials_per_column > 5:
        raise ValueError(f"serials per column must be between 1 and 5, got {serials_per_column}")

    total = march_size * march_per_serial * serials_per_column
    if total < 6 or total > 300:
        raise ValueError(f"convoy total vehicles must be between 6 and 300, got {total}")

    roles = spec.get("roles")
    if roles is not None:
        if len(roles) != march_size:
            raise ValueError(f"roles length ({len(roles)}) must match march unit size ({march_size})")
        for r in roles:
            if r not in ROLE_MAP:
                raise ValueError(f"unknown convoy role {r!r}; must be one of {sorted(ROLE_MAP)}")

    pace = spec.get("pace")
    if pace is not None:
        if not isinstance(pace, (int, float)) or pace <= 0 or pace > 50.0:
            raise ValueError(f"convoy pace must be between 0 and 50 m/s, got {pace}")

    time_gap = spec.get("time_gap")
    if time_gap is not None:
        if not isinstance(time_gap, (int, float)) or time_gap <= 0 or time_gap > 60.0:
            raise ValueError(f"convoy time gap must be between 0 and 60 s, got {time_gap}")

    elem_gap = spec.get("element_time_gap")
    if elem_gap is not None:
        if not isinstance(elem_gap, (int, float)) or elem_gap <= 0 or elem_gap > 300.0:
            raise ValueError(f"convoy element time gap must be between 0 and 300 s, got {elem_gap}")

    safety_factor = spec.get("safety_factor")
    if safety_factor is not None:
        if not isinstance(safety_factor, (int, float)) or safety_factor < 0.0 or safety_factor > 1.0:
            raise ValueError(f"convoy safety factor must be between 0.0 and 1.0, got {safety_factor}")

    serial_gap = spec.get("serial_time_gap")
    if serial_gap is not None:
        if not isinstance(serial_gap, (int, float)) or serial_gap <= 0 or serial_gap > 600.0:
            raise ValueError(f"convoy serial time gap must be between 0 and 600 s, got {serial_gap}")

    halt_dur = spec.get("halt_duration")
    if halt_dur is not None:
        if not isinstance(halt_dur, (int, float)) or halt_dur < 0.0 or halt_dur > 3600.0:
            raise ValueError(f"convoy halt duration must be between 0 and 3600 s, got {halt_dur}")

    sec_ratio = spec.get("security_ratio")
    if sec_ratio is not None:
        if not isinstance(sec_ratio, (int, float)) or sec_ratio < 0.0 or sec_ratio > 1.0:
            raise ValueError(f"convoy security ratio must be between 0.0 and 1.0, got {sec_ratio}")

    cargo_veh = spec.get("cargo_per_vehicle")
    if cargo_veh is not None:
        if not isinstance(cargo_veh, (int, float)) or cargo_veh <= 0 or cargo_veh > 100.0:
            raise ValueError(f"convoy cargo per vehicle must be between 0 and 100 tons, got {cargo_veh}")

    del_frac = spec.get("delivery_fraction")
    if del_frac is not None:
        if not isinstance(del_frac, (int, float)) or del_frac < 0.0 or del_frac > 1.0:
            raise ValueError(f"convoy delivery fraction must be between 0.0 and 1.0, got {del_frac}")

    sec_ptype = spec.get("security_ptype")
    if sec_ptype is not None and not isinstance(sec_ptype, str):
        raise ValueError(f"convoy security_ptype must be a platform type name, got {sec_ptype!r}")

    resolve_contact_reaction(spec)


def build_convoy_layout(spec: dict) -> dict:
    """Compute per-vehicle hierarchy arrays for the convoy from spec."""
    validate_convoy_spec(spec)

    march_size = int(spec["march_unit_size"])
    march_per_serial = int(spec["march_units_per_serial"])
    serials_per_column = int(spec["serials_per_column"])
    total = march_size * march_per_serial * serials_per_column

    # (Default: Head=Control, Trail=Recovery, Middle=Cargo, with security_ratio allocating Gun Trucks)
    raw_roles = spec.get("roles")
    sec_ratio = spec.get("security_ratio")
    if raw_roles:
        pos_roles = [ROLE_MAP[r] for r in raw_roles]
    elif sec_ratio is not None and march_size > 2:
        n_middle = march_size - 2
        n_sec = min(n_middle, max(0, int(round(n_middle * float(sec_ratio)))))
        n_cargo = n_middle - n_sec
        middle = [ROLE_CARGO] * n_cargo + [ROLE_SECURITY] * n_sec
        pos_roles = [ROLE_CONTROL] + middle
        if march_size > 1:
            pos_roles.append(ROLE_RECOVERY)
    else:
        pos_roles = [ROLE_CONTROL] + [ROLE_CARGO] * max(0, march_size - 2)
        if march_size > 1:
            pos_roles.append(ROLE_RECOVERY)

    march_units = np.zeros(total, dtype=np.int16)
    serials = np.zeros(total, dtype=np.int16)
    sections = np.zeros(total, dtype=np.int8)
    convoy_roles = np.zeros(total, dtype=np.int8)
    leaders = np.full(total, -1, dtype=np.int32)
    roles = np.ones(total, dtype=np.int8)  # 0=Leader, 1=Follower

    for i in range(total):
        march_idx = i // march_size
        serial_idx = i // (march_size * march_per_serial)

        k = i % march_size
        march_units[i] = march_idx
        serials[i] = serial_idx
        convoy_roles[i] = pos_roles[k]

        # Head / Main / Trail
        head_idx = march_idx * march_size

        if k == 0:
            sections[i] = SECTION_HEAD
            roles[i] = 0        # Leader
            leaders[i] = -1     # No leader above it in the march unit
        elif k == march_size - 1:
            sections[i] = SECTION_TRAIL
            roles[i] = 1        # Follower
            leaders[i] = head_idx  # Follow the leader of its march unit
        else:
            sections[i] = SECTION_MAIN
            roles[i] = 1        # Follower
            leaders[i] = head_idx  # Follow the leader of its march unit

    pace = float(spec["pace"]) if spec.get("pace") is not None else None
    time_gap = float(spec["time_gap"]) if spec.get("time_gap") is not None else None
    elem_gap = float(spec["element_time_gap"]) if spec.get("element_time_gap") is not None else None
    safety_factor = float(spec["safety_factor"]) if spec.get("safety_factor") is not None else 0.0
    serial_gap = float(spec["serial_time_gap"]) if spec.get("serial_time_gap") is not None else None
    halt_dur = float(spec["halt_duration"]) if spec.get("halt_duration") is not None else 0.0
    sec_ratio_val = float(sec_ratio) if sec_ratio is not None else None
    cargo_veh_val = float(spec["cargo_per_vehicle"]) if spec.get("cargo_per_vehicle") is not None else None
    del_frac_val = float(spec["delivery_fraction"]) if spec.get("delivery_fraction") is not None else None

    return {
        "march_unit": march_units,
        "serial": serials,
        "section": sections,
        "convoy_role": convoy_roles,
        "leader": leaders,
        "role": roles,
        "total": total,
        "pace": pace,
        "time_gap": time_gap,
        "element_time_gap": elem_gap,
        "safety_factor": safety_factor,
        "serial_time_gap": serial_gap,
        "halt_duration": halt_dur,
        "security_ratio": sec_ratio_val,
        "cargo_per_vehicle": cargo_veh_val,
        "delivery_fraction": del_frac_val,
    }
