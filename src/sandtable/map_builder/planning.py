"""Map-planning application service: validation, graph construction and routing."""

from __future__ import annotations

from dataclasses import dataclass
from sandtable.routing import ExposurePenaltyCost, RoutePlanner
from .validation import MapValidator
from .topology import RoadGraphBuilder
from .values import Invalid
from .exposure import MapExposureResolver
from sandtable.street_graph import StreetGraph
from sandtable.route import RoutePolyline


@dataclass
class MapPlan:
    graph: StreetGraph
    nodes: list
    route: RoutePolyline
    warnings: list
    report: dict


class RoutingReportBuilder:
    def build(self, document, built, path, policy):
        graph = built.graph
        selected = []
        chosen = {frozenset((a, b)) for a, b in zip(path, path[1:])}
        all_edges = []
        roads = {r["id"]: r for r in document["roads"]}
        for i, e in enumerate(graph.edges):
            record = dict(
                id="E" + str(i + 1),
                road_id=built.source_roads[i],
                u=e.u,
                v=e.v,
                length_m=e.length,
                speed_mult=e.speed_mult,
                exposure=e.exposure,
                exposure_mode=roads[built.source_roads[i]]["exposure_mode"],
                baseline_cost=e.length / e.speed_mult,
                penalty_multiplier=1 + policy.scale * policy.weight * e.exposure,
                cost=policy(e),
                selected=frozenset((e.u, e.v)) in chosen,
            )
            all_edges.append(record)
        for a, b in zip(path, path[1:]):
            e = next(e for e in graph.edges if {e.u, e.v} == {a, b})
            selected.append(
                dict(
                    u=a,
                    v=b,
                    length_m=e.length,
                    exposure=e.exposure,
                    speed_mult=e.speed_mult,
                    cost=policy(e),
                )
            )
        length = sum(e["length_m"] for e in selected)
        return dict(
            algorithm=document["route_algorithm"] if document["route_mode"] == "auto" else "manual",
            cost=sum(e["cost"] for e in selected),
            mean_exposure=sum(e["length_m"] * e["exposure"] for e in selected) / length,
            formula="w = length / speed_mult * (1 + 10 * weight * exposure)",
            sample_spacing_m=50,
            ground_truth=True,
            selected_edges=selected,
            all_edges=all_edges,
            penalty_weight=policy.weight,
        )


class MapPlanningService:
    """Injectable collaborators keep geometry, search and reporting independent."""

    def __init__(
        self, validator=None, graph_builder=None, report_builder=None, exposure_resolver=None
    ):
        self.validator = validator or MapValidator()
        self.exposure_resolver = exposure_resolver or MapExposureResolver()
        self.graph_builder = graph_builder or RoadGraphBuilder(self.exposure_resolver.model_for)
        self.report_builder = report_builder or RoutingReportBuilder()

    def normalize(self, raw, draft_mode=False):
        return self.exposure_resolver.resolve(self.validator.normalize(raw, draft_mode))

    def plan(self, document):
        if not document.get("roads"):
            raise Invalid("Draw at least one road before route planning.")
        built = self.graph_builder.build(document)
        policy = ExposurePenaltyCost(document["route_bias"])
        if document["route_mode"] == "auto":
            result = RoutePlanner.for_algorithm(document["route_algorithm"], policy).plan(
                built.graph, built.anchors["start"], built.anchors["goal"]
            )
            path = list(result.nodes)
        else:
            manual = document["manual_path"]
            if len(manual) < 2:
                raise Invalid("Manual route needs at least two nodes.")
            if manual[0] != built.anchors["start"] or manual[-1] != built.anchors["goal"]:
                raise Invalid("Manual path must start/end at start-area and goal road nodes.")
            path = [manual[0]]
            for a, b in zip(manual, manual[1:]):
                road = next((r for r in document["roads"] if {r["u"], r["v"]} == {a, b}), None)
                if road is None:
                    raise Invalid(f"Manual path has no road between {a} and {b}.")
                chain = built.expansions[road["id"]]
                path.extend((chain if chain[0] == a else list(reversed(chain)))[1:])
        if len(path) < 2:
            raise Invalid("No connected road path reaches the goal.")
        if len(set(path)) != len(path):
            raise Invalid(
                "Route revisits an intersection; single-pass stationing requires a simple path."
            )
        return MapPlan(
            built.graph,
            path,
            built.graph.to_route_polyline(path),
            built.warnings,
            self.report_builder.build(document, built, path, policy),
        )
