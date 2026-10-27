"""Street graph network topology and routing (Phase 3, Issue #16).

Provides discrete 2D graph representations of urban roadway networks:
- Intersections: StreetNode(id, x, y)
- Road segments: StreetEdge(u, v, width, speed_mult, exposure, length)
- Routing: Dijkstra path search parameterized continuously by route_bias in [0, 1]
- Bridge: Translation of graph paths into RoutePolyline (Issue #13) for arc-length stationing
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Any, Sequence

from sandtable.route import RoutePolyline


@dataclass(frozen=True)
class StreetNode:
    """An intersection or decision point in the street network."""

    id: str | int
    x: float
    y: float


@dataclass
class StreetEdge:
    """A street segment connecting two intersections."""

    u: str | int
    v: str | int
    width: float = 8.0          # Street width in meters (roadway capacity)
    speed_mult: float = 1.0     # Trafficability multiplier in (0, 1]
    exposure: float = 0.5       # Exposure factor in [0, 1] (0 = covered alley, 1 = open avenue)
    length: float = 0.0         # Segment length in meters (computed if <= 0)
    bidirectional: bool = True  # Can vehicles travel both directions
    geometry: tuple[tuple[float, float], ...] = ()  # Optional intermediate bend points


class StreetGraph:
    """Discrete 2D urban street network."""

    def __init__(
        self,
        nodes: dict[str | int, StreetNode] | Sequence[StreetNode],
        edges: Sequence[StreetEdge],
    ) -> None:
        if isinstance(nodes, dict):
            self.nodes: dict[str | int, StreetNode] = dict(nodes)
        else:
            self.nodes = {n.id: n for n in nodes}

        self.edges: list[StreetEdge] = list(edges)

        # Adjacency list: node_id -> list of (neighbor_id, edge)
        self._adj: dict[str | int, list[tuple[str | int, StreetEdge]]] = {nid: [] for nid in self.nodes}

        # Resolve edge lengths and populate adjacency
        for e in self.edges:
            if e.u not in self.nodes or e.v not in self.nodes:
                raise ValueError(f"StreetEdge connects unknown node: ({e.u}, {e.v})")

            if e.length <= 0.0:
                e.length = self._compute_edge_length(e)

            self._adj[e.u].append((e.v, e))
            if e.bidirectional:
                self._adj[e.v].append((e.u, e))

    def _compute_edge_length(self, edge: StreetEdge) -> float:
        """Compute Euclidean length along edge geometry or between endpoints."""
        u_node = self.nodes[edge.u]
        v_node = self.nodes[edge.v]

        pts = [(u_node.x, u_node.y)]
        pts.extend(edge.geometry)
        pts.append((v_node.x, v_node.y))

        total = 0.0
        for i in range(len(pts) - 1):
            dx = pts[i + 1][0] - pts[i][0]
            dy = pts[i + 1][1] - pts[i][1]
            total += math.hypot(dx, dy)
        return total

    def find_nearest_node(self, x: float, y: float) -> str | int:
        """Find the node closest in Euclidean distance to (x, y)."""
        best_id: str | int | None = None
        best_d2 = float("inf")
        for nid, node in self.nodes.items():
            d2 = (node.x - x) ** 2 + (node.y - y) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_id = nid
        if best_id is None:
            raise ValueError("StreetGraph contains no nodes")
        return best_id

    def edge_cost(self, edge: StreetEdge, route_bias: float = 0.0) -> float:
        """Compute traversal cost for an edge under route_bias in [0, 1].

        cost(e) = (1.0 - route_bias) * (length / speed_mult) + route_bias * (length * exposure)
        - route_bias = 0.0: Pure speed-optimal routing (arterials, highest speed).
        - route_bias = 1.0: Pure cover/safety-optimal routing (covered backstreets, minimum exposure).
        """
        bias = max(0.0, min(1.0, float(route_bias)))
        speed = max(1e-4, edge.speed_mult)
        travel_time = edge.length / speed
        exposure_cost = edge.length * edge.exposure
        return (1.0 - bias) * travel_time + bias * exposure_cost

    def find_path(
        self,
        start_node: str | int,
        goal_node: str | int,
        route_bias: float = 0.0,
    ) -> list[str | int]:
        """Find the lowest-cost path from start_node to goal_node using Dijkstra search.

        Returns list of node IDs [start_node, ..., goal_node].
        Returns [] if goal_node is unreachable.
        """
        if start_node not in self.nodes or goal_node not in self.nodes:
            return []

        if start_node == goal_node:
            return [start_node]

        dist: dict[str | int, float] = {start_node: 0.0}
        prev: dict[str | int, str | int] = {}
        # Priority queue stores (cost, counter, node_id)
        pq: list[tuple[float, int, str | int]] = [(0.0, 0, start_node)]
        counter = 0

        while pq:
            d, _, u = heapq.heappop(pq)
            if d > dist.get(u, float("inf")):
                continue

            if u == goal_node:
                break

            for v, edge in self._adj.get(u, []):
                cost = self.edge_cost(edge, route_bias=route_bias)
                alt = d + cost
                if alt < dist.get(v, float("inf")):
                    dist[v] = alt
                    prev[v] = u
                    counter += 1
                    heapq.heappush(pq, (alt, counter, v))

        if goal_node not in prev:
            return []

        path = []
        curr: str | int | None = goal_node
        while curr is not None:
            path.append(curr)
            curr = prev.get(curr)
        path.reverse()
        return path

    def _get_edge_between(self, u: str | int, v: str | int) -> StreetEdge | None:
        """Find edge directly connecting u and v."""
        for nbr, edge in self._adj.get(u, []):
            if nbr == v:
                return edge
        return None

    def to_route_polyline(self, path_nodes: Sequence[str | int]) -> RoutePolyline:
        """Convert a sequence of connected node IDs into a RoutePolyline.

        Includes intermediate geometry from connecting edges if defined.
        """
        if len(path_nodes) < 2:
            raise ValueError(f"path_nodes must contain at least 2 nodes, got {len(path_nodes)}")

        pts: list[tuple[float, float]] = []

        for i in range(len(path_nodes) - 1):
            u_id = path_nodes[i]
            v_id = path_nodes[i + 1]

            if u_id not in self.nodes or v_id not in self.nodes:
                raise ValueError(f"Unknown node ID in path: ({u_id}, {v_id})")

            u_node = self.nodes[u_id]
            v_node = self.nodes[v_id]

            if i == 0:
                pts.append((u_node.x, u_node.y))

            edge = self._get_edge_between(u_id, v_id)
            if edge is not None and edge.geometry:
                if edge.u == u_id:
                    # Traversed in forward direction
                    pts.extend(edge.geometry)
                else:
                    # Traversed in reverse direction
                    pts.extend(reversed(edge.geometry))

            pts.append((v_node.x, v_node.y))

        return RoutePolyline.from_waypoints(pts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize StreetGraph to dictionary."""
        return {
            "nodes": [
                {"id": n.id, "x": n.x, "y": n.y}
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "u": e.u,
                    "v": e.v,
                    "width": e.width,
                    "speed_mult": e.speed_mult,
                    "exposure": e.exposure,
                    "length": e.length,
                    "bidirectional": e.bidirectional,
                    "geometry": [list(pt) for pt in e.geometry],
                }
                for e in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreetGraph:
        """Deserialize StreetGraph from dictionary."""
        nodes = [
            StreetNode(id=nd["id"], x=float(nd["x"]), y=float(nd["y"]))
            for nd in data.get("nodes", [])
        ]
        edges = [
            StreetEdge(
                u=ed["u"],
                v=ed["v"],
                width=float(ed.get("width", 8.0)),
                speed_mult=float(ed.get("speed_mult", 1.0)),
                exposure=float(ed.get("exposure", 0.5)),
                length=float(ed.get("length", 0.0)),
                bidirectional=bool(ed.get("bidirectional", True)),
                geometry=tuple(tuple(float(c) for c in pt) for pt in ed.get("geometry", ())),
            )
            for ed in data.get("edges", [])
        ]
        return cls(nodes=nodes, edges=edges)

    @classmethod
    def create_grid(
        cls,
        nx: int,
        ny: int,
        spacing_x: float,
        spacing_y: float,
        origin: tuple[float, float] = (0.0, 0.0),
        width: float = 8.0,
        speed_mult: float = 1.0,
        exposure: float = 0.5,
    ) -> StreetGraph:
        """Helper to create a regular street grid network."""
        nodes: list[StreetNode] = []
        edges: list[StreetEdge] = []

        ox, oy = origin
        for j in range(ny):
            for i in range(nx):
                nid = f"n_{i}_{j}"
                x = ox + i * spacing_x
                y = oy + j * spacing_y
                nodes.append(StreetNode(id=nid, x=x, y=y))

        # Horizontal edges
        for j in range(ny):
            for i in range(nx - 1):
                u = f"n_{i}_{j}"
                v = f"n_{i+1}_{j}"
                edges.append(
                    StreetEdge(
                        u=u,
                        v=v,
                        width=width,
                        speed_mult=speed_mult,
                        exposure=exposure,
                        bidirectional=True,
                    )
                )

        # Vertical edges
        for j in range(ny - 1):
            for i in range(nx):
                u = f"n_{i}_{j}"
                v = f"n_{i}_{j+1}"
                edges.append(
                    StreetEdge(
                        u=u,
                        v=v,
                        width=width,
                        speed_mult=speed_mult,
                        exposure=exposure,
                        bidirectional=True,
                    )
                )

        return cls(nodes=nodes, edges=edges)
