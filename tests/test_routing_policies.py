"""Search correctness against exhaustive paths, including non-Euclidean costs."""

import itertools
import math
import numpy as np
import pytest
from sandtable.street_graph import StreetGraph, StreetNode, StreetEdge
from sandtable.routing import (
    RoutePlanner,
    LegacyBlendCost,
    ExposurePenaltyCost,
    RangeExposureModel,
    ThreatSite,
)


def exhaustive_cost(graph, start, goal, policy):
    other = [n for n in graph.nodes if n not in (start, goal)]
    best = math.inf
    for k in range(len(other) + 1):
        for middle in itertools.permutations(other, k):
            path = (start, *middle, goal)
            cost = 0
            for a, b in zip(path, path[1:]):
                edges = [
                    e
                    for e in graph.edges
                    if (e.u == a and e.v == b) or (e.bidirectional and e.u == b and e.v == a)
                ]
                if not edges:
                    break
                cost += min(policy(e) for e in edges)
            else:
                best = min(best, cost)
    return best


@pytest.mark.parametrize("algorithm", ["dijkstra", "astar"])
def test_search_matches_exhaustive_optimum_with_fast_and_supplied_length_edges(algorithm):
    rng = np.random.default_rng(13)
    for _ in range(6):
        nodes = [StreetNode(i, *rng.uniform(0, 1000, 2)) for i in range(6)]
        edges = [
            StreetEdge(
                a,
                b,
                length=float(rng.uniform(0.1, 100)),
                speed_mult=float(rng.uniform(0.2, 3)),
                exposure=float(rng.random()),
                bidirectional=bool(rng.integers(2)),
            )
            for a, b in itertools.combinations(range(6), 2)
            if rng.random() < 0.6
        ]
        graph = StreetGraph(nodes, edges)
        for policy in [LegacyBlendCost(1), ExposurePenaltyCost(0.7)]:
            result = RoutePlanner.for_algorithm(algorithm, policy).plan(graph, 0, 5)
            expected = exhaustive_cost(graph, 0, 5, policy)
            assert result.cost == pytest.approx(expected)


def test_zero_cost_cycle_and_missing_nodes_are_safe():
    graph = StreetGraph(
        [StreetNode(i, i, 0) for i in range(4)],
        [
            StreetEdge(0, 1, exposure=0),
            StreetEdge(1, 2, exposure=0),
            StreetEdge(2, 0, exposure=0),
            StreetEdge(2, 3, exposure=0),
        ],
    )
    for algorithm in ["dijkstra", "astar"]:
        result = graph.plan_path(0, 3, route_bias=1, algorithm=algorithm)
        assert result.found and result.cost == 0
        assert graph.find_path("missing", 3, algorithm=algorithm) == []
        assert graph.find_path(2, 2, algorithm=algorithm) == [2]


def test_selected_parallel_edge_controls_replayed_geometry():
    graph = StreetGraph(
        [StreetNode("a", 0, 0), StreetNode("b", 10, 0)],
        [
            StreetEdge("a", "b", length=100, geometry=((5, 50),)),
            StreetEdge("a", "b", length=10, geometry=((5, 0),)),
        ],
    )
    result = graph.plan_path("a", "b", algorithm="astar")
    assert result.edge_indices == (1,)
    route = graph.to_route_polyline(result.nodes, edge_indices=result.edge_indices)
    np.testing.assert_array_equal(route.waypoints, [[0, 0], [5, 0], [10, 0]])


def test_exposure_follows_bent_geometry_and_keeps_manual_override():
    graph = StreetGraph(
        [StreetNode("a", 0, 0), StreetNode("b", 1000, 0)],
        [StreetEdge("a", "b", exposure=0.123, geometry=((500, 1000),))],
    )
    model = RangeExposureModel([ThreatSite(500, 1000, 200)])
    resolved = model.apply(graph)
    assert resolved.edges[0].exposure > 0
    assert model.segment_score([0, 0], [1000, 0]) == 0
    assert model.apply(graph, manual_edges=[0]).edges[0].exposure == 0.123
    assert graph.edges[0].exposure == 0.123


def test_invalid_algorithm_and_negative_cost_fail_fast():
    graph = StreetGraph([StreetNode(0, 0, 0), StreetNode(1, 1, 0)], [StreetEdge(0, 1)])
    with pytest.raises(ValueError, match="Unknown routing"):
        graph.find_path(0, 1, algorithm="typo")
    with pytest.raises(ValueError, match="nonnegative"):
        graph.plan_path(0, 1, cost_policy=lambda edge: -1)


def test_native_world_can_use_astar_and_known_threat_exposure():
    from sandtable.world import build_world
    from sandtable.scenario import Scenario

    nodes = [
        StreetNode("s", 100, 500),
        StreetNode("g", 1900, 500),
        StreetNode("nw", 100, 1500),
        StreetNode("ne", 1900, 1500),
    ]
    graph = StreetGraph(
        nodes,
        [
            StreetEdge("s", "g"),
            StreetEdge("s", "nw"),
            StreetEdge("nw", "ne"),
            StreetEdge("ne", "g"),
        ],
    )
    raw = dict(
        name="native-routing",
        size=[2000, 2000],
        dt=1,
        duration=10,
        platform_types={"truck": dict(domain=0, max_speed=10)},
        forces=[dict(side=0, ptype="truck", count=1, spawn=[100, 500])],
        objective=dict(goal=[1900, 500], goal_radius=50, survive_fraction=1),
        terrain=dict(profile="open", cell=25),
        params=dict(
            street_graph=graph.to_dict(),
            route_algorithm="astar",
            route_cost_model="exposure_penalty",
            route_bias=1,
            route_exposure=dict(threat_sites=[dict(x=1000, y=500, weapon_range=900, pk=1)]),
        ),
    )
    world = build_world(Scenario.from_dict(raw), np.random.default_rng(1))
    assert world.route.total_length > 1800
    assert world.street_graph.edges[0].exposure > 0
    np.testing.assert_array_equal(
        world.route.waypoints, [[100, 500], [100, 1500], [1900, 1500], [1900, 500]]
    )


def test_map_builder_rejects_reverse_order_contained_collinear_roads():
    from sandtable.map_builder import MapPlanningService, Invalid
    from sandtable.mission_viewer.templates import default_config

    m = default_config()["map"]
    m["nodes"] += [dict(id="inside1", x=500, y=1500), dict(id="inside2", x=1000, y=1500)]
    m["roads"].insert(
        0, dict(id="duplicate", u="inside1", v="inside2", width=100, speed_mult=1, exposure=0.5)
    )
    service = MapPlanningService()
    with pytest.raises(Invalid, match="Overlapping"):
        service.plan(service.normalize(m))


def test_map_exposure_model_can_be_replaced_without_changing_search_or_validation():
    from sandtable.map_builder import MapPlanningService
    from sandtable.map_builder.exposure import MapExposureResolver
    from sandtable.mission_viewer.templates import default_config

    class ConstantExposure:
        def score(self, points):
            return 0.42

    service = MapPlanningService(
        exposure_resolver=MapExposureResolver(lambda document: ConstantExposure())
    )
    document = service.normalize(default_config()["map"])
    plan = service.plan(document)
    assert all(r["exposure_auto"] == 0.42 for r in document["roads"])
    assert all(e.exposure == 0.42 for e in plan.graph.edges)
