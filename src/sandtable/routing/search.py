"""Shortest-path strategies over the StreetGraph data model."""

from __future__ import annotations
from dataclasses import dataclass
from itertools import count
from typing import Protocol, TYPE_CHECKING, Union
import heapq
import math
from .costs import EdgeCostPolicy

if TYPE_CHECKING:
    from sandtable.street_graph import StreetGraph
NodeId = Union[str, int]


@dataclass(frozen=True)
class PathResult:
    nodes: tuple[NodeId, ...] = ()
    edge_indices: tuple[int, ...] = ()
    cost: float = math.inf
    expanded_nodes: int = 0

    @property
    def found(self) -> bool:
        return bool(self.nodes)


class PathSearch(Protocol):
    def search(
        self, graph: StreetGraph, start: NodeId, goal: NodeId, cost: EdgeCostPolicy
    ) -> PathResult: ...


def _search(graph, start, goal, cost, use_heuristic):
    if start not in graph.nodes or goal not in graph.nodes:
        return PathResult()
    adjacency = {n: [] for n in graph.nodes}
    minimum_rate = math.inf
    for i, edge in enumerate(graph.edges):
        weight = float(cost(edge))
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("Shortest-path costs must be finite and nonnegative.")
        adjacency[edge.u].append((edge.v, i, weight))
        if edge.bidirectional:
            adjacency[edge.v].append((edge.u, i, weight))
        a, b = graph.nodes[edge.u], graph.nodes[edge.v]
        chord = math.hypot(a.x - b.x, a.y - b.y)
        if chord > 0:
            minimum_rate = min(minimum_rate, weight / chord)
    # Safe for legacy zero costs, fast roads, bent edges and supplied edge lengths.
    rate = minimum_rate if use_heuristic and math.isfinite(minimum_rate) else 0.0
    target = graph.nodes[goal]

    def heuristic(node):
        n = graph.nodes[node]
        return rate * math.hypot(n.x - target.x, n.y - target.y)

    serial = count()
    queue = [(heuristic(start), next(serial), 0.0, start)]
    distance = {start: 0.0}
    parent = {}
    expanded = 0
    while queue:
        _, _, g, node = heapq.heappop(queue)
        if g > distance[node]:
            continue
        expanded += 1
        if node == goal:
            nodes, edges = [goal], []
            while nodes[-1] != start:
                previous, edge_index = parent[nodes[-1]]
                nodes.append(previous)
                edges.append(edge_index)
            return PathResult(tuple(reversed(nodes)), tuple(reversed(edges)), g, expanded)
        for neighbor, edge_index, weight in adjacency[node]:
            alternative = g + weight
            if alternative < distance.get(neighbor, math.inf):
                distance[neighbor] = alternative
                parent[neighbor] = (node, edge_index)
                heapq.heappush(
                    queue, (alternative + heuristic(neighbor), next(serial), alternative, neighbor)
                )
    return PathResult(expanded_nodes=expanded)


class DijkstraSearch:
    def search(self, graph, start, goal, cost):
        return _search(graph, start, goal, cost, False)


class AStarSearch:
    def search(self, graph, start, goal, cost):
        return _search(graph, start, goal, cost, True)


class RoutePlanner:
    """Compose a search strategy with a cost policy; no map/UI dependencies."""

    def __init__(self, search: PathSearch, cost: EdgeCostPolicy):
        self.search = search
        self.cost = cost

    def plan(self, graph, start, goal):
        return self.search.search(graph, start, goal, self.cost)

    @classmethod
    def for_algorithm(cls, algorithm, cost):
        strategies = {"dijkstra": DijkstraSearch, "astar": AStarSearch}
        if algorithm not in strategies:
            raise ValueError(f"Unknown routing algorithm: {algorithm}")
        return cls(strategies[algorithm](), cost)
