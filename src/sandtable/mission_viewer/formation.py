"""Declare convoy roles and preview the exact engine layout."""

from sandtable.convoy import build_convoy_layout
from sandtable.map_builder.values import Invalid
from .settings import MissionSettings


class FormationBuilder:
    def spec(self, v):
        roles = ["control"] + ["cargo"] * (v["vehicles_per_unit"] - 1)
        if v["layout"] == "recovery":
            roles[-1] = "recovery"
        convoy = dict(
            march_unit_size=v["vehicles_per_unit"],
            march_units_per_serial=v["units_per_serial"],
            serials_per_column=v["serials"],
            roles=roles,
            escort_vehicles=v["escorts"],
            pace=v["pace"],
            time_gap=v["time_gap"],
            leader_loss_policy=v["leader_loss"],
            succession=v["succession"],
            security_ptype="escort",
            crew={
                "control": v["control_crew"],
                "cargo": v["cargo_crew"] if v["crew_mode"] == "crewed" else 0,
                "security": v["escort_crew"],
                "recovery": v["recovery_crew"],
            },
        )
        if v["leader_loss"] in ["promote", "absorb"]:
            convoy["handoff_steps"] = v["handoff_steps"]
        if v["leader_loss"] == "halt":
            rel = {}
            if v["halt_max_s"]:
                rel["max_hold_steps"] = v["halt_max_s"]
            if v["halt_clear_steps"]:
                rel["clear_steps"] = v["halt_clear_steps"]
            if rel:
                convoy["halt_release"] = rel
        convoy["contact_reaction"] = dict(
            action="continue" if v["response"] == "continue" else "halt",
            triggers=["receive_fire"],
            halt_scope="all",
            release=dict(rule="timeout", clear_s=v["contact_clear_s"]),
        )
        return convoy

    def preview(self, raw):
        """Map-independent draft layout from the same spec/builder as a real run."""
        v = MissionSettings().normalize(raw)
        spec = self.spec(v)
        layout = build_convoy_layout(spec)
        if layout["total"] > 80:
            raise Invalid("V3 supports at most 80 Blue vehicles.")
        gap = max(v["min_gap"], v["pace"] * v["time_gap"])
        names = ["control", "cargo", "security", "recovery"]
        heads = {
            int(layout["march_unit"][i]): i
            for i in range(layout["total"])
            if layout["role"][i] == 0
        }
        vehicles = []
        for i in range(layout["total"]):
            role = int(layout["convoy_role"][i])
            unit = int(layout["march_unit"][i])
            crew = spec["crew"][names[role]]
            vehicles.append(
                dict(
                    id=i,
                    label="V" + str(i + 1),
                    role=role,
                    unit=unit,
                    serial=int(layout["serial"][i]),
                    head=heads[unit],
                    leader=int(layout["leader"][i]),
                    console=unit if crew == 0 and i != heads[unit] else None,
                    crew=crew,
                    cargo_kg=v["payload_kg"] if role == 1 else 0,
                    capacity_kg=v["capacity_kg"] if role == 1 else 0,
                    length_m=v["vehicle_length"],
                    station_m=v["staging_m"] - i * gap,
                )
            )
        return dict(
            vehicles=vehicles,
            gap_m=gap,
            centre_span_m=(layout["total"] - 1) * gap,
            physical_span_m=(layout["total"] - 1) * gap + v["vehicle_length"],
            staging_m=v["staging_m"],
            units_per_serial=v["units_per_serial"],
            serials=v["serials"],
            loaded_kg=sum((x["cargo_kg"] for x in vehicles)),
            crew=sum((x["crew"] for x in vehicles)),
            warnings=["Straight-road illustration; map placement requires Validate."]
            + (
                ["Formation extends before the start origin. Increase staging or reduce size/gaps."]
                if vehicles[-1]["station_m"] < 5
                else []
            ),
        )
