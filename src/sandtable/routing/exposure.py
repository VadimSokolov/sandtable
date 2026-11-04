"""Known-map range/proximity exposure model, independent of routing strategy."""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Protocol
import math
from .geometry import segment_intersects_box, raster_box


@dataclass(frozen=True)
class ThreatSite:
    x: float
    y: float
    weapon_range: float
    pk: float = 1.0

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.x, self.y, self.weapon_range, self.pk)):
            raise ValueError("Threat values must be finite.")
        if self.weapon_range < 0 or self.pk < 0:
            raise ValueError("Threat range and eligibility must be nonnegative.")


class RoadExposureModel(Protocol):
    def score(self, points) -> float: ...


class RangeExposureModel:
    """Midpoint-sampled clipped proximity sum. Not a casualty probability.

    Positive pk gates eligibility; its magnitude and sensor detection are not used.
    Optional conservative raster building boxes screen the static known positions.
    """

    def __init__(self, threats, buildings=(), cell=25.0, sample_spacing=50.0):
        if (
            not math.isfinite(cell)
            or cell <= 0
            or not math.isfinite(sample_spacing)
            or sample_spacing <= 0
        ):
            raise ValueError("Cell size and sampling spacing must be finite and positive.")
        self.threats = tuple(threats)
        self.boxes = tuple(raster_box(b, cell) for b in buildings)
        self.sample_spacing = sample_spacing

    @classmethod
    def from_map(cls, document, sample_spacing=50.0):
        threats = [ThreatSite(r["x"], r["y"], r["weapon_range"], r["pk"]) for r in document["red"]]
        return cls(
            threats, [b["box"] for b in document["buildings"]], document["cell"], sample_spacing
        )

    def segment_score(self, a, b):
        n = max(1, math.ceil(math.dist(a, b) / self.sample_spacing))
        total = 0.0
        for j in range(n):
            t = (j + 0.5) / n
            p = [a[i] + t * (b[i] - a[i]) for i in (0, 1)]
            score = 0.0
            for r in self.threats:
                if r.weapon_range <= 0 or r.pk <= 0:
                    continue
                q = [r.x, r.y]
                d = math.dist(p, q)
                if d >= r.weapon_range or any(
                    segment_intersects_box(p, q, box) for box in self.boxes
                ):
                    continue
                score += 1 - d / r.weapon_range
            total += min(1.0, score)
        return total / n

    def score(self, points):
        if len(points) < 2:
            raise ValueError("Exposure needs a polyline with at least two points.")
        if len(points) == 2:
            return self.segment_score(points[0], points[1])
        lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
        total = sum(lengths)
        if total == 0:
            return self.segment_score(points[0], points[-1])
        return (
            sum(
                length * self.segment_score(a, b)
                for a, b, length in zip(points, points[1:], lengths)
            )
            / total
        )

    def apply(self, graph, manual_edges=()):
        """Return a graph copy, retaining explicit manual edge overrides."""
        from sandtable.street_graph import StreetGraph

        manual = set(manual_edges)
        edges = []
        for i, e in enumerate(graph.edges):
            a, b = graph.nodes[e.u], graph.nodes[e.v]
            value = e.exposure if i in manual else self.score([(a.x, a.y), *e.geometry, (b.x, b.y)])
            edges.append(replace(e, exposure=value))
        return StreetGraph(graph.nodes, edges)
