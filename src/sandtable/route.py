"""Route polyline geometry and 1D arc-length coordinate system (Phase 3, Issue #13).

Provides continuous arc-length parameterization along arbitrary 2D piecewise-linear routes:
- Forward mapping: s in [0, L] -> (x, y, heading)
- Backward mapping: (x, y) -> (s, orthogonal_distance)

Follows Army Movement Control doctrine (ATP 4-16, para C-4) where convoy spacing, column
length, and road clearance are measured strictly along the road centerline rather than
as Euclidean straight-line chords across open terrain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class RoutePolyline:
    """Piecewise-linear route parameterized by arc-length distance s."""

    waypoints: np.ndarray      # shape (K, 2), float64: vertex coordinates
    segments: np.ndarray       # shape (K-1, 2), float64: segment vectors (w_{k+1} - w_k)
    segment_lengths: np.ndarray  # shape (K-1,), float64: Euclidean length of each segment
    cum_dist: np.ndarray       # shape (K,), float64: cumulative arc length at each vertex
    total_length: float        # total route length in meters

    @classmethod
    def from_waypoints(
        cls,
        pts: Sequence[tuple[float, float] | Sequence[float]] | np.ndarray,
        start_point: tuple[float, float] | None = None,
    ) -> RoutePolyline:
        """Construct a RoutePolyline from a sequence of 2D waypoints [(x0, y0), (x1, y1), ...]."""
        arr = np.asarray(pts, dtype=np.float64)
        if arr.ndim == 1 and arr.shape[0] == 2:
            arr = arr.reshape(1, 2)
        if arr.ndim != 2 or arr.shape[1] != 2:
            raise ValueError(f"waypoints must have shape (K, 2), got {arr.shape}")
        if arr.shape[0] == 1:
            sp = np.asarray(start_point if start_point is not None else (0.0, 0.0), dtype=np.float64)
            if not np.allclose(sp, arr[0]):
                arr = np.vstack([sp, arr])

        if arr.shape[0] < 2:
            raise ValueError(f"route polyline requires at least 2 waypoints, got {arr.shape[0]}")

        # Deduplicate consecutive identical waypoints
        diffs = arr[1:] - arr[:-1]
        dist = np.hypot(diffs[:, 0], diffs[:, 1])
        valid_steps = dist > 1e-9

        # Keep first point and any point that advances beyond 0 distance
        keep_indices = [0] + [i + 1 for i, v in enumerate(valid_steps) if v]
        clean_pts = arr[keep_indices]

        if clean_pts.shape[0] < 2:
            raise ValueError("route polyline has zero total length after deduplicating waypoints")

        segments = clean_pts[1:] - clean_pts[:-1]
        seg_lengths = np.hypot(segments[:, 0], segments[:, 1])
        cum_dist = np.zeros(clean_pts.shape[0], dtype=np.float64)
        cum_dist[1:] = np.cumsum(seg_lengths)
        tot_len = float(cum_dist[-1])

        return cls(
            waypoints=clean_pts,
            segments=segments,
            segment_lengths=seg_lengths,
            cum_dist=cum_dist,
            total_length=tot_len,
        )

    def point_at(self, s: float | np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute 2D coordinates (x, y) and tangent heading at arc-length distance s.

        Returns:
            (x, y, heading): arrays matching the broadcast shape of s.
        """
        scalar = np.isscalar(s)
        s_arr = np.atleast_1d(np.asarray(s, dtype=np.float64))

        # Endpoint clamps
        s_clamped = np.clip(s_arr, 0.0, self.total_length)

        # Segment index k such that cum_dist[k] <= s <= cum_dist[k+1]
        # np.searchsorted(side='right') - 1 gives k in [0, K-2]
        k = np.searchsorted(self.cum_dist, s_clamped, side="right") - 1
        k = np.clip(k, 0, len(self.segment_lengths) - 1)

        ds = self.segment_lengths[k]
        s0 = self.cum_dist[k]
        tau = np.where(ds > 1e-9, (s_clamped - s0) / ds, 0.0)
        tau = np.clip(tau, 0.0, 1.0)

        # Handle backward extrapolation if s < 0
        neg_mask = s_arr < 0.0
        if np.any(neg_mask):
            k_first = 0
            tau[neg_mask] = s_arr[neg_mask] / max(self.segment_lengths[k_first], 1e-9)

        # Handle forward extrapolation if s > total_length
        pos_mask = s_arr > self.total_length
        if np.any(pos_mask):
            k_last = len(self.segment_lengths) - 1
            tau[pos_mask] = 1.0 + (s_arr[pos_mask] - self.total_length) / max(self.segment_lengths[k_last], 1e-9)

        w_k = self.waypoints[k]
        seg_k = self.segments[k]

        x = w_k[:, 0] + tau * seg_k[:, 0]
        y = w_k[:, 1] + tau * seg_k[:, 1]
        heading = np.arctan2(seg_k[:, 1], seg_k[:, 0])

        if scalar:
            return float(x[0]), float(y[0]), float(heading[0])
        return x, y, heading

    def project(self, x: float | np.ndarray, y: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Orthogonal projection of 2D point(s) (x, y) onto the route polyline.

        Returns:
            (s, dist):
                s: arc-length coordinate along the route (meters from route origin)
                dist: shortest orthogonal distance from (x, y) to the polyline (meters)
        """
        scalar = np.isscalar(x) and np.isscalar(y)
        x_arr = np.atleast_1d(np.asarray(x, dtype=np.float64))
        y_arr = np.atleast_1d(np.asarray(y, dtype=np.float64))
        n_pts = len(x_arr)
        n_segs = len(self.segment_lengths)

        pts = np.column_stack([x_arr, y_arr])  # (N, 2)

        # Vectorized projection across all N points and all K-1 segments
        # pts[:, None, :] is (N, 1, 2)
        # waypoints[:-1] is (n_segs, 2)
        # segments is (n_segs, 2)
        a = self.waypoints[:-1]  # segment origins (n_segs, 2)
        v = self.segments        # segment vectors (n_segs, 2)
        v_len_sq = v[:, 0] ** 2 + v[:, 1] ** 2  # (n_segs,)

        # u = P - A -> (N, n_segs, 2)
        u_x = pts[:, 0, None] - a[None, :, 0]
        u_y = pts[:, 1, None] - a[None, :, 1]

        # dot product u . v -> (N, n_segs)
        dot = u_x * v[None, :, 0] + u_y * v[None, :, 1]

        raw_tau = dot / np.maximum(v_len_sq[None, :], 1e-12)
        tau = np.clip(raw_tau, 0.0, 1.0)
        tau[:, 0] = np.minimum(raw_tau[:, 0], 1.0)
        if n_segs > 1:
            tau[:, -1] = np.maximum(raw_tau[:, -1], 0.0)
        else:
            tau[:, 0] = raw_tau[:, 0]

        # proj = A + tau * v -> (N, n_segs, 2)
        proj_x = a[None, :, 0] + tau * v[None, :, 0]
        proj_y = a[None, :, 1] + tau * v[None, :, 1]

        # dist_sq = (P - proj)^2
        dist_sq = (pts[:, 0, None] - proj_x) ** 2 + (pts[:, 1, None] - proj_y) ** 2  # (N, n_segs)

        # Best segment for each point
        best_seg = np.argmin(dist_sq, axis=1)  # (N,)
        row_indices = np.arange(n_pts)

        best_tau = tau[row_indices, best_seg]
        best_dist = np.sqrt(dist_sq[row_indices, best_seg])
        best_s = self.cum_dist[best_seg] + best_tau * self.segment_lengths[best_seg]

        if scalar:
            return float(best_s[0]), float(best_dist[0])
        return best_s, best_dist

    def sample_path(self, step: float = 10.0) -> np.ndarray:
        """Sample equidistant (x, y) coordinates along the route for visualization."""
        if step <= 0.0:
            raise ValueError(f"step must be positive, got {step}")
        s_vals = np.arange(0.0, self.total_length + step * 0.5, step)
        if s_vals[-1] < self.total_length:
            s_vals = np.append(s_vals, self.total_length)
        x, y, _ = self.point_at(s_vals)
        return np.column_stack([x, y])
