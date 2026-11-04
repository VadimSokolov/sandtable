"""Assemble a validated map, formation and mission into a native Scenario."""

import math, numpy as np
from sandtable.convoy import build_convoy_layout
from sandtable.scenario import Scenario
from sandtable.map_builder import MapPlanningService, Invalid
from sandtable.routing.geometry import segment_intersects_box as segment_box
from .identity import digest
from .formation import FormationBuilder
from .settings import MissionSettings


class ScenarioCompiler:
    def __init__(self, maps=None, formation=None, settings=None):
        self.maps = maps or MapPlanningService()
        self.formation = formation or FormationBuilder()
        self.settings = settings or MissionSettings()

    def compile(self, raw, load_target_kg=None):
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise Invalid("Expected a V3 schema_version=1 scenario file.")
        if not isinstance(raw.get("name"), str) or not 1 <= len(raw["name"]) <= 120:
            raise Invalid("Provide a mission name of 1-120 characters.")
        m = self.maps.normalize(raw.get("map"))
        v = self.settings.normalize(raw.get("mission"))
        plan = self.maps.plan(m)
        graph, path, route, warnings = (plan.graph, plan.nodes, plan.route, plan.warnings)
        convoy = self.formation.spec(v)
        if math.dist(route.waypoints[-1], m["goal"]) > m["goal_radius"]:
            raise Invalid(
                "Projected road endpoint is outside the goal radius; move the goal onto the road."
            )
        layout = build_convoy_layout(convoy)
        N = layout["total"]
        cargo = int((layout["convoy_role"] == 1).sum())
        if N > 80:
            raise Invalid(
                "V3 local viewer supports at most 80 Blue vehicles (an application performance limit, not doctrine)."
            )
        if not cargo:
            raise Invalid("At least one cargo truck is required.")
        payload = v["payload_kg"] if load_target_kg is None else float(load_target_kg) / cargo
        if payload > v["capacity_kg"] + 1e-07:
            raise Invalid("Fixed-cargo comparison exceeds an arm's total payload capacity.")
        if payload <= 0:
            raise Invalid("Load must be positive.")
        convoy["cargo_per_vehicle"] = payload / 1000
        if load_target_kg is not None:
            v["payload_kg"] = payload
        gap = max(v["min_gap"], v["pace"] * v["time_gap"])
        span = (N - 1) * gap
        if v["staging_m"] < span + 5:
            raise Invalid(
                f"Formation needs {span + 5:.1f} m of staging. Increase staging_m (currently {v['staging_m']:g}), reduce the fleet/gaps, or extend the road."
            )
        if route.total_length < v["staging_m"] + 2 * m["goal_radius"] + 20:
            raise Invalid(
                "Route is too short for staging plus the goal approach. Extend it or reduce staging/goal radius."
            )
        station = v["staging_m"] - np.arange(N) * gap
        x, y, head = route.point_at(station)
        spawn = np.column_stack([x, y])

        def raster_box(b):
            c = m["cell"]
            x0, y0, x1, y1 = b
            return [
                math.floor(x0 / c) * c,
                math.floor(y0 / c) * c,
                math.ceil(x1 / c) * c,
                math.ceil(y1 / c) * c,
            ]

        for i, p in enumerate(spawn):
            if not (0 < p[0] < m["width"] and 0 < p[1] < m["height"]):
                raise Invalid(f"Initial vehicle V{i + 1} is outside the map.")
            if any(
                (
                    segment_box(p, p, raster_box(b["box"]), v["vehicle_length"] / 2)
                    for b in m["buildings"]
                )
            ):
                raise Invalid(f"Initial vehicle V{i + 1} overlaps building footprint.")
        dd = np.linalg.norm(spawn[:, None, :] - spawn[None, :, :], axis=2)
        np.fill_diagonal(dd, np.inf)
        if dd.min() < v["vehicle_length"] + 1:
            raise Invalid("Initial formation overlaps at a bend. Move/extend the staging road.")
        crew = sum(
            (
                convoy["crew"][["control", "cargo", "security", "recovery"][int(r)]]
                for r in layout["convoy_role"]
            )
        )
        units = v["units_per_serial"] * v["serials"]
        if v["crew_mode"] == "crewed" and v["cargo_crew"] == 0:
            warnings.append(
                "Crewed mode has zero cargo crew; these followers will still be supervised by the console."
            )
        if v["response"] == "herringbone":
            warnings.append("Experimental Herringbone geometry; no automatic protection benefit.")
        if v["console_transfer"] == "successor":
            warnings.append(
                "Experimental console transfer to a surviving crewed promoted head. Queue reservations and agent assignments are retained."
            )
        if v["leader_loss"] == "halt" and (not v["halt_max_s"]) and (not v["halt_clear_steps"]):
            warnings.append("Leader-loss halt has no release rule and can hold indefinitely.")
        if v["diagnostic_loss_s"] is not None:
            warnings.append(
                "FORCED DIAGNOSTIC head destruction is enabled; this is not natural combat."
            )
        warnings.append(
            "Weapon ranges, lethality, routing exposure priors and vehicle dynamics are study assumptions, not battlefield calibration."
        )
        params = dict(
            convoy=convoy,
            formation_spread=v["min_gap"],
            blue_behavior="leader_follow",
            follow_mode="behavior",
            follow_topology="chain",
            track_timeout=40,
            sense_range=10000,
            converge_dist=300,
            lookahead=30,
            tempo=1,
            route=route.waypoints.tolist(),
            street_graph=graph.to_dict(),
            buildings=[b["box"] for b in m["buildings"]],
            comms_level=v["comms"],
            control_mode="direct",
            console_per_march_unit=dict(attention_basis="assigned", exceptions=v["exceptions"]),
            queue_model="reserve",
            n_operators=1,
            span_capacity=v["span_capacity"],
            service_rate=v["service_rate"],
            decision_interval=v["decision_interval"],
            patience=v["patience"],
            q_operator=0.95,
            q_auto=0.7,
            q_fallback=0.5,
            q_stall=0.3,
        )
        platform = dict(
            domain=0,
            max_speed=v["max_speed"],
            turn_rate=0.6,
            sensor_range=1500,
            weapon_range=0,
            pk_base=0,
            hp=1,
            length=v["vehicle_length"],
            cargo_capacity=v["capacity_kg"] / 1000,
        )
        escort = {**platform, "weapon_range": v["escort_range"], "pk_base": v["escort_pk"]}
        types = {"cargo": platform, "escort": escort}
        forces = [
            dict(
                side=0, ptype="cargo", count=N, spawn=spawn[0].tolist(), spawn_spread=0, spacing=gap
            )
        ]
        for i, e in enumerate(m["red"]):
            name = "red_" + str(i)
            types[name] = dict(
                domain=0,
                max_speed=0,
                turn_rate=0,
                sensor_range=e["sensor_range"],
                weapon_range=e["weapon_range"],
                pk_base=e["pk"],
                hp=1,
                length=1,
            )
            forces.append(dict(side=1, ptype=name, count=1, spawn=[e["x"], e["y"]], spawn_spread=0))
        cfg = dict(
            name=raw["name"],
            id=301,
            size=[m["width"], m["height"]],
            dt=1,
            duration=v["duration"],
            platform_types=types,
            forces=forces,
            objective=dict(
                goal=m["goal"],
                goal_radius=m["goal_radius"],
                survive_fraction=1,
                delivery_fraction=v["required_fraction"],
            ),
            terrain=dict(
                profile="open", cell=m["cell"], open_speed=1, open_cover=0, open_conceal=0
            ),
            params=params,
        )
        Scenario.from_dict(cfg)
        config = {"schema_version": 1, "name": raw["name"], "map": m, "mission": v}
        routing_report = plan.report
        summary = dict(
            formation=self.formation.preview(v),
            routing=routing_report,
            total_vehicles=N,
            core_vehicles=v["vehicles_per_unit"] * units,
            units=units,
            cargo_trucks=cargo,
            escorts=v["escorts"],
            control=units,
            recovery=units if v["layout"] == "recovery" else 0,
            crew=crew,
            loaded_kg=payload * cargo,
            effective_payload_kg=payload,
            initial_station_gap_m=gap,
            staging_span_m=span,
            route_length_m=route.total_length,
            route_nodes=path,
            route=route.waypoints.tolist(),
            spawn=spawn.tolist(),
            roles=layout["convoy_role"].tolist(),
            heads=np.flatnonzero(layout["role"] == 0).tolist(),
            graph=graph.to_dict(),
            warnings=warnings,
            definitions={
                "mass": "kg in builder; metric tonnes in Sandtable; 1 t = 1000 kg",
                "gap": "Centre reference station separation; g=max(min_gap, tracked_reference_speed*time_gap). No bumper clearance is silently added.",
                "staging": "Start marker is rear road origin. Lead starts staging_m along the selected route; every arm preserves this offset.",
                "escort": "Added to core vehicles, distributed after each control. Not prescribed by ATP.",
                "route": "Fixed at launch; initial Dijkstra/A* uses known-map exposure scores, not runtime replanning or casualty probabilities.",
                "motion": "V3 steering/arrival and building/boundary guards; no collision avoidance or wreck bypass.",
            },
        )
        return dict(config=config, scenario=cfg, summary=summary, config_hash=digest(config))
