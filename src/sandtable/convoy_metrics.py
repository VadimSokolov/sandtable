"""Convoy doctrine arithmetic: standard movement-control formulas from ATP 4-16.

This module implements the doctrinal movement-control calculations defined in U.S. Army
ATP 4-16 (Movement Control, April 2022, Appendix C) and ATP 4-11 (Army Motor Transport
Operations, March 2026, Appendix G & M).

The core planning quantities are:
1. Column Length (CL): Distance from the front bumper of the lead vehicle to the rear bumper
   of the trail vehicle, including intra-element gaps and inter-element gaps.
2. Road Space (RS): Column length plus a safety factor buffer (CL * (1 + safety_factor)).
3. Pass Time (PT): Time required for the entire column to pass a single given point (CL / v).
4. Time Distance (TD): Time required for a vehicle (or lead element) to travel route distance D
   (D / v).
5. Road Clearance Time (RCT): Total time a route segment is occupied from lead entry until trail
   clearance (RCT = TD + PT = (D + CL) / v).
6. Time Gap: Time elapsed between successive vehicles or elements passing a stationary point (G / v).

The Five ATP 4-16 Invariant Identities:
  (1) TD * v = D
  (2) PT * v = CL
  (3) RCT = TD + PT
  (4) RS = CL * (1 + safety_factor)
  (5) RCT * v = D + CL
"""
from __future__ import annotations

import numpy as np


def doctrinal_rate_of_march(pace: float, halt_duration: float = 0.0,
                            march_duration: float = 3600.0) -> float:
    """Compute rate of march (average speed including scheduled short halts).

    In ATP 4-16 (para C-2), rate of march is the average speed over the route including
    operational halts (e.g., 10 minutes halt per hour of march). When halts are absent,
    rate of march equals regulated pace.
    """
    if pace <= 0.0:
        return 0.0
    if halt_duration <= 0.0 or march_duration <= 0.0:
        return float(pace)
    moving_frac = max(0.0, march_duration - halt_duration) / march_duration
    return float(pace * moving_frac)


def doctrinal_column_length(spec: dict, platform_lengths: list[float] | float = 6.0,
                            default_spacing: float = 30.0) -> float:
    """Compute theoretical Column Length (CL) in meters (ATP 4-16, C-5).

    CL = sum(vehicle_lengths) + sum(intra_gaps) + sum(inter_element_gaps)
    """
    march_size = int(spec["march_unit_size"])
    march_per_serial = int(spec["march_units_per_serial"])
    serials_per_column = int(spec["serials_per_column"])
    total_vehicles = march_size * march_per_serial * serials_per_column

    # Vehicle physical lengths
    if isinstance(platform_lengths, (int, float)):
        sum_lengths = total_vehicles * float(platform_lengths)
    else:
        p_list = list(platform_lengths)
        if len(p_list) == 0:
            sum_lengths = total_vehicles * 6.0
        elif len(p_list) == total_vehicles:
            sum_lengths = sum(float(x) for x in p_list)
        else:
            sum_lengths = total_vehicles * float(p_list[0])

    # Gaps based on pace and time gaps
    pace = spec.get("pace")
    time_gap = spec.get("time_gap")
    elem_gap = spec.get("element_time_gap")
    serial_gap = spec.get("serial_time_gap", elem_gap)

    if pace is not None and time_gap is not None:
        intra_gap = max(default_spacing, float(pace) * float(time_gap))
    else:
        intra_gap = float(default_spacing)

    if pace is not None and elem_gap is not None:
        unit_gap = max(intra_gap, float(pace) * float(elem_gap))
    else:
        unit_gap = intra_gap

    if pace is not None and serial_gap is not None:
        ser_gap = max(unit_gap, float(pace) * float(serial_gap))
    else:
        ser_gap = unit_gap

    # Structure counts
    total_march_units = serials_per_column * march_per_serial
    n_intra = total_march_units * (march_size - 1)
    n_unit = serials_per_column * (march_per_serial - 1)
    n_serial = serials_per_column - 1

    total_gap_dist = n_intra * intra_gap + n_unit * unit_gap + n_serial * ser_gap
    return float(sum_lengths + total_gap_dist)


def doctrinal_road_space(column_length: float, safety_factor: float = 0.0) -> float:
    """Compute Road Space (RS) in meters (ATP 4-16, C-5).

    RS = CL * (1 + safety_factor)
    """
    sf = max(0.0, float(safety_factor))
    return float(column_length * (1.0 + sf))


def doctrinal_pass_time(column_length: float, pace: float,
                        rate_of_march: float | None = None) -> float:
    """Compute Pass Time (PT) in seconds (ATP 4-16, C-4).

    PT = CL / Rate of March
    """
    v = rate_of_march if rate_of_march is not None else pace
    if v <= 0.0:
        return float("inf")
    return float(column_length / v)


def doctrinal_time_distance(distance: float, pace: float,
                            rate_of_march: float | None = None) -> float:
    """Compute Time Distance (TD) in seconds (ATP 4-16, C-4).

    TD = Distance / Rate of March
    """
    v = rate_of_march if rate_of_march is not None else pace
    if v <= 0.0:
        return float("inf")
    return float(distance / v)


def doctrinal_road_clearance_time(time_distance: float, pass_time: float) -> float:
    """Compute Road Clearance Time (RCT) in seconds (ATP 4-16, C-5).

    RCT = TD + PT
    """
    return float(time_distance + pass_time)


def doctrinal_convoy_summary(spec: dict, route_distance: float,
                             platform_length: float = 6.0,
                             default_spacing: float = 30.0) -> dict:
    """Compute a complete doctrinal movement-control summary for a convoy."""
    pace = float(spec.get("pace", 10.0))
    halt_dur = float(spec.get("halt_duration", 0.0))
    safety_factor = float(spec.get("safety_factor", 0.0))
    rom = doctrinal_rate_of_march(pace, halt_duration=halt_dur)

    cl = doctrinal_column_length(spec, platform_lengths=platform_length,
                                 default_spacing=default_spacing)
    rs = doctrinal_road_space(cl, safety_factor=safety_factor)
    pt = doctrinal_pass_time(cl, pace=pace, rate_of_march=rom)
    td = doctrinal_time_distance(route_distance, pace=pace, rate_of_march=rom)
    rct = doctrinal_road_clearance_time(td, pt)

    march_size = int(spec["march_unit_size"])
    march_per_serial = int(spec["march_units_per_serial"])
    serials_per_column = int(spec["serials_per_column"])
    total_vehicles = march_size * march_per_serial * serials_per_column

    return {
        "column_length": cl,
        "road_space": rs,
        "pace": pace,
        "rate_of_march": rom,
        "pass_time": pt,
        "time_distance": td,
        "road_clearance_time": rct,
        "safety_factor": safety_factor,
        "total_vehicles": total_vehicles,
        "route_distance": float(route_distance),
    }


def verify_atp416_identities(summary: dict, tol: float = 1e-6) -> dict[str, bool]:
    """Verify that the 5 foundational ATP 4-16 identities hold exactly."""
    cl = summary["column_length"]
    rs = summary["road_space"]
    rom = summary["rate_of_march"]
    pt = summary["pass_time"]
    td = summary["time_distance"]
    rct = summary["road_clearance_time"]
    sf = summary["safety_factor"]
    d = summary["route_distance"]

    id_td = abs(td * rom - d) < tol
    id_pt = abs(pt * rom - cl) < tol
    id_rct = abs(rct - (td + pt)) < tol
    id_rs = abs(rs - cl * (1.0 + sf)) < tol
    id_rct_dist = abs(rct * rom - (d + cl)) < tol

    all_valid = bool(id_td and id_pt and id_rct and id_rs and id_rct_dist)

    return {
        "identity_td": id_td,
        "identity_pt": id_pt,
        "identity_rct": id_rct,
        "identity_rs": id_rs,
        "identity_rct_dist": id_rct_dist,
        "all_valid": all_valid,
    }


def measured_column_length(x: np.ndarray, y: np.ndarray,
                           lengths: np.ndarray | float = 6.0,
                           mask: np.ndarray | None = None) -> float:
    """Measure empirical column length from entity positions (front bumper to rear bumper).

    Projects coordinates onto the principal column axis.
    """
    if mask is not None:
        mx = x[mask]
        my = y[mask]
        mlen = lengths[mask] if isinstance(lengths, np.ndarray) else lengths
    else:
        mx = x
        my = y
        mlen = lengths

    n = len(mx)
    if n == 0:
        return 0.0
    if n == 1:
        return float(mlen if isinstance(mlen, (int, float)) else mlen[0])

    # Direction vector between lead (index 0) and trail (index n - 1)
    dx = float(mx[0] - mx[-1])
    dy = float(my[0] - my[-1])
    dist = float(np.hypot(dx, dy))

    if dist < 1e-6:
        # Stationary or overlapping
        proj = mx
    else:
        ux, uy = dx / dist, dy / dist
        proj = mx * ux + my * uy

    min_proj = float(proj.min())
    max_proj = float(proj.max())
    span = max_proj - min_proj

    # Add front and rear bumper extents (half length each end)
    if isinstance(mlen, np.ndarray):
        bumper_extent = 0.5 * float(mlen[0]) + 0.5 * float(mlen[-1])
    else:
        bumper_extent = float(mlen)

    return float(span + bumper_extent)


class PassageTracker:
    """Observer that records timestamps when vehicles cross a checkpoint line.

    Used to measure empirical pass time and inter-vehicle time gaps.
    """

    def __init__(self, checkpoint_x: float) -> None:
        self.checkpoint_x = float(checkpoint_x)
        self.first_cross_t: float | None = None
        self.last_cross_t: float | None = None
        self.cross_events: list[tuple[int, float]] = []  # (entity_idx, timestamp)
        self.seen_indices: set[int] = set()

    def update(self, t: float, x: np.ndarray, mask: np.ndarray) -> None:
        """Record newly crossing vehicles at time t."""
        active_indices = np.where(mask)[0]
        for idx in active_indices:
            if idx not in self.seen_indices and x[idx] >= self.checkpoint_x:
                self.seen_indices.add(idx)
                self.cross_events.append((idx, float(t)))
                if self.first_cross_t is None:
                    self.first_cross_t = float(t)
                self.last_cross_t = float(t)

    @property
    def measured_pass_time(self) -> float | None:
        if self.first_cross_t is None or self.last_cross_t is None:
            return None
        return float(self.last_cross_t - self.first_cross_t)

    @property
    def measured_time_gaps(self) -> list[float]:
        if len(self.cross_events) < 2:
            return []
        return [float(self.cross_events[i][1] - self.cross_events[i - 1][1])
                for i in range(1, len(self.cross_events))]
