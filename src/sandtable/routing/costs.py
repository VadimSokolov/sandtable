"""Edge-cost policies. Values are effective metres, not casualty probabilities."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from sandtable.street_graph import StreetEdge


class EdgeCostPolicy(Protocol):
    def __call__(self, edge: StreetEdge) -> float: ...


@dataclass(frozen=True)
class LegacyBlendCost:
    """Preserve the original Issue #16 arithmetic and clamping exactly."""

    route_bias: float = 0.0

    def __call__(self, edge: StreetEdge) -> float:
        bias = max(0.0, min(1.0, float(self.route_bias)))
        travel = edge.length / max(1e-4, edge.speed_mult)
        return (1.0 - bias) * travel + bias * (edge.length * edge.exposure)


@dataclass(frozen=True)
class ExposurePenaltyCost:
    """Positive travel baseline plus an explicit exposure penalty."""

    weight: float = 0.5
    scale: float = 10.0

    def __post_init__(self):
        if not math.isfinite(self.weight) or not 0 <= self.weight <= 1:
            raise ValueError("Exposure weight must be in [0, 1].")
        if not math.isfinite(self.scale) or self.scale < 0:
            raise ValueError("Exposure penalty scale must be finite and nonnegative.")

    def __call__(self, edge: StreetEdge) -> float:
        if not math.isfinite(edge.speed_mult) or edge.speed_mult <= 0:
            raise ValueError("Road trafficability must be finite and positive.")
        if not math.isfinite(edge.exposure) or not 0 <= edge.exposure <= 1:
            raise ValueError("Road exposure must be in [0, 1].")
        return edge.length / edge.speed_mult * (1 + self.scale * self.weight * edge.exposure)
