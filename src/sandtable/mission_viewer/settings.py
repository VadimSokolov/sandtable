"""Mission input schema and relational constraints."""

from sandtable.map_builder.values import Invalid, number, option
from .templates import default_config


class MissionSettings:
    def normalize(self, raw, draft_mode=False):
        if not isinstance(raw, dict):
            raise Invalid("Mission must be an object.")
        base = default_config()["mission"]
        m = {}
        ints = {
            "vehicles_per_unit": (2, 25),
            "units_per_serial": (2, 5),
            "serials": (1, 5),
            "escorts": (0, 30),
            "control_crew": (1, 8),
            "cargo_crew": (0, 8),
            "escort_crew": (1, 8),
            "recovery_crew": (1, 8),
            "comms": (0, 5),
            "seed": (0, 2**31 - 1),
            "duration": (10, 7200),
            "handoff_steps": (0, 600),
            "halt_max_s": (0, 3600),
            "halt_clear_steps": (0, 3600),
            "console_delay_s": (0, 600),
            "decision_interval": (1, 600),
            "patience": (1, 600),
        }
        floats = {
            "payload_kg": (0.001, 50000),
            "capacity_kg": (0.001, 50000),
            "pace": (0.1, 30),
            "time_gap": (0.1, 60),
            "min_gap": (7, 500),
            "required_fraction": (0.01, 1),
            "contact_clear_s": (1, 3600),
            "span_capacity": (0.1, 100),
            "service_rate": (0.01, 10),
            "max_speed": (0.1, 30),
            "vehicle_length": (2, 20),
            "staging_m": (0, 10000),
            "herringbone_offset": (5, 50),
            "escort_range": (0, 5000),
            "escort_pk": (0, 1),
        }
        enums = {
            "layout": ["cargo", "recovery"],
            "crew_mode": ["crewed", "supervised"],
            "response": ["continue", "halt", "herringbone"],
            "leader_loss": ["promote", "halt", "absorb", "continue"],
            "succession": ["manned_only", "any"],
            "console_transfer": ["fixed", "successor"],
            "target_priority": ["nearest", "control_first"],
        }
        for key, (lo, hi) in ints.items():
            m[key] = number(raw.get(key, base[key]), key, lo, hi, True)
        for key, (lo, hi) in floats.items():
            m[key] = number(raw.get(key, base[key]), key, lo, hi)
        for key, vs in enums.items():
            m[key] = option(raw.get(key, base[key]), key, vs)
        m["exceptions"] = raw.get("exceptions", False)
        if not isinstance(m["exceptions"], bool):
            raise Invalid("exceptions must be true/false.")
        m["diagnostic_loss_s"] = raw.get("diagnostic_loss_s")
        if m["diagnostic_loss_s"] is not None:
            m["diagnostic_loss_s"] = number(
                m["diagnostic_loss_s"], "Diagnostic forced loss", 0, m["duration"] - 1, True
            )
        if not draft_mode and m["payload_kg"] > m["capacity_kg"]:
            raise Invalid("Loaded payload exceeds platform capacity. Both are kg.")
        if not draft_mode and m["pace"] > m["max_speed"]:
            raise Invalid("Commanded pace exceeds the platform maximum speed.")
        if not draft_mode and m["min_gap"] < m["vehicle_length"] + 1:
            raise Invalid("Minimum centre station gap must exceed vehicle length by at least 1 m.")
        if not draft_mode and m["layout"] == "recovery" and (m["vehicles_per_unit"] < 3):
            raise Invalid("Recovery layout needs at least three core vehicles per unit.")
        if (
            not draft_mode
            and m["console_transfer"] == "successor"
            and (m["leader_loss"] != "promote")
        ):
            raise Invalid(
                "Experimental console transfer is defined only for promote. Use fixed ownership with absorb/continue/halt."
            )
        return m
