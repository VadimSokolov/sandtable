"""polarisopt metric plugin: registers the ``mission_score`` metric type.

Discovered through the ``polarisopt.metrics`` entry point declared in this
package's ``pyproject.toml``. It reduces the runner's averaged KPIs to a single
scalar *mission cost* so a single-objective study (BO) has a smooth thing to
minimize:

.. math::

    J = w_{fail}\\,(1 - \\text{success\\_rate})
        + w_{time}\\,\\frac{\\text{time\\_to\\_objective}}{\\text{time\\_scale}}
        + w_{loss}\\,\\text{blue\\_loss\\_frac}

Every term is on a comparable 0..1 scale, so the weights express doctrine (how
much a commander trades tempo against attrition against outright failure), not
units. Lower is better; studies minimize it by default.

Example study snippet::

    metric:
      type: mission_score
      options:
        w_fail: 1.0        # penalty for not accomplishing the mission
        w_time: 0.3        # penalty per unit of (normalized) time-to-objective
        w_loss: 0.5        # penalty per unit of blue attrition fraction
        time_scale: 1800.0 # normalizer for time (typically scenario duration, s)

For a pure parameter sweep where you want the raw KPIs stored per sample rather
than a scalarized objective, use polarisopt's built-in ``identity`` metric
instead (``metric: {type: identity, options: {keys: [...]}}``).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from polarisopt.metrics.base import Metric, MetricError, metric_registry


@metric_registry.register("mission_score")
class MissionScoreMetric(Metric):
    """Weighted scalar mission cost over failure, tempo, and attrition.

    Parameters
    ----------
    w_fail, w_time, w_loss : float
        Non-negative weights for the failure, time, and attrition terms.
    time_scale : float
        Positive normalizer applied to ``time_to_objective`` (typically the
        scenario duration in seconds) so the time term lands on a 0..1 scale.
    """

    def __init__(
        self,
        w_fail: float = 1.0,
        w_time: float = 0.3,
        w_loss: float = 0.5,
        time_scale: float = 1800.0,
    ) -> None:
        weights = {"w_fail": w_fail, "w_time": w_time, "w_loss": w_loss}
        bad = [k for k, v in weights.items() if float(v) < 0]
        if bad:
            raise MetricError(f"mission_score: weights must be >= 0, got negative {bad}")
        if float(time_scale) <= 0:
            raise MetricError(f"mission_score: time_scale must be > 0, got {time_scale}")
        self.w_fail = float(w_fail)
        self.w_time = float(w_time)
        self.w_loss = float(w_loss)
        self.time_scale = float(time_scale)

    @property
    def n_objectives(self) -> int:
        return 1

    def _get(self, output: dict[str, Any], key: str) -> float:
        if key not in output:
            raise MetricError(
                f"mission_score: key {key!r} not in simulator output (keys={list(output)})"
            )
        value = float(output[key])
        if not np.isfinite(value):
            raise MetricError(f"mission_score: output[{key!r}] is not finite: {value}")
        return value

    def compute(self, output: dict[str, Any]) -> np.ndarray:
        # success_rate falls back to the mean success indicator (same quantity).
        success_rate = float(output.get("success_rate", output.get("success", 0.0)))
        if not np.isfinite(success_rate):
            raise MetricError(f"mission_score: success_rate is not finite: {success_rate}")
        time_norm = self._get(output, "time_to_objective") / self.time_scale
        loss_frac = self._get(output, "blue_loss_frac")

        j = (
            self.w_fail * (1.0 - success_rate)
            + self.w_time * time_norm
            + self.w_loss * loss_frac
        )
        return np.asarray([float(j)])
