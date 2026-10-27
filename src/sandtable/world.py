"""Terrain / mobility world.

The world is a set of coarse rasters over the operating area:
  - `speed`   in [0, 1]: trafficability multiplier on a platform's max speed (NRMM-style
               speed-made-good; 0 = NoGo).
  - `cover`   in [0, 1]: physical cover; reduces incoming probability of kill.
  - `conceal` in [0, 1]: concealment; reduces the enemy's probability of detection.

Runtime terrain queries are O(1) vectorized array gathers (never an online mobility model). LOS is
a stub (flat terrain -> always visible) that the sensing enhancement will replace with an
elevation ray-cast; concealment already carries the mission-relevant "harder to see me" effect.

`build_world` procedurally constructs the terrain for a scenario. The default profile (used by the
UC-3 route-vs-defilade scenario) lays a fast, exposed corridor beside a slow, covered route so that
a routing parameter trades time-to-objective against attrition.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from sandtable.scenario import Scenario


@dataclass
class World:
    size: tuple                # (width, height) metres
    cell: float                # metres per raster cell
    speed: np.ndarray          # [ny, nx] trafficability multiplier in [0, 1]
    cover: np.ndarray          # [ny, nx] in [0, 1]
    conceal: np.ndarray        # [ny, nx] in [0, 1]
    route: Any = None          # optional RoutePolyline along which ground units navigate

    def _idx(self, x: np.ndarray, y: np.ndarray) -> tuple:
        ny, nx = self.speed.shape
        ix = np.clip((np.asarray(x) / self.cell).astype(np.intp), 0, nx - 1)
        iy = np.clip((np.asarray(y) / self.cell).astype(np.intp), 0, ny - 1)
        return iy, ix

    def sample(self, field: np.ndarray, x, y) -> np.ndarray:
        iy, ix = self._idx(x, y)
        return field[iy, ix]

    def speed_at(self, x, y) -> np.ndarray:
        return self.sample(self.speed, x, y)

    def cover_at(self, x, y) -> np.ndarray:
        return self.sample(self.cover, x, y)

    def conceal_at(self, x, y) -> np.ndarray:
        return self.sample(self.conceal, x, y)

    def in_bounds(self, x, y) -> np.ndarray:
        w, h = self.size
        x = np.asarray(x)
        y = np.asarray(y)
        return (x >= 0) & (x < w) & (y >= 0) & (y < h)

    def los(self, x0, y0, x1, y1) -> np.ndarray:
        """Line-of-sight clear? Flat-terrain stub: always True (shape-broadcast)."""
        return np.ones(np.broadcast(x0, x1).shape, bool)

    # covered-route centre-line y (used by planning to steer toward defilade)
    @property
    def covered_y(self) -> float:
        return self.size[1] * 0.78

    @property
    def corridor_y(self) -> float:
        return self.size[1] * 0.5


def build_world(scn: Scenario, rng: np.random.Generator) -> World:
    """Build terrain rasters from scn.terrain (falls back to the UC-3 corridor/defilade profile).

    Every result in this project was found on ONE map, a single lateral Gaussian band of cover
    broadcast along the whole length of the field, which has no longitudinal structure at all: a
    route choice here is a choice of latitude and nothing else. That is a real limit on external
    validity, so the profile is now selectable and parameterized.

      ``band``       the published map, and the default. Bit-identical to what it was before this
                     function grew any parameters, which `tests/test_world.py` pins.
      ``chokepoint`` slow ground everywhere except a gap at a given longitude, so the force is
                     funnelled and arrives at the console in a burst it did not choose.
      ``open``       a featureless field carrying the band profile's OWN MEAN cover, uniformly.
                     The control is meant to remove the route CHOICE, not the protection: a bare
                     field would floor mission success and make every contrast on it unreadable,
                     which was caught before any arm was run and is recorded in CR-52.

    Positions are fractions of the field so the same profile transfers between field sizes.
    """
    w, h = scn.size
    # Terrain keys may arrive either in the scenario's `terrain` block or as `terrain_*` params, so
    # that a sweep or an arm, which can only set params, can change the map. Params win, which is
    # the same precedence every other knob in this model uses.
    t = {**scn.terrain,
         **{k[len("terrain_"):]: v for k, v in scn.params.items() if k.startswith("terrain_")}}
    cell = float(t.get("cell", 25.0))
    nx, ny = int(np.ceil(w / cell)), int(np.ceil(h / cell))
    ys = (np.arange(ny) + 0.5) * cell           # cell-centre y for each row
    profile = str(t.get("profile", "band"))

    corridor_y = h * float(t.get("corridor_frac", 0.50))
    covered_y = h * float(t.get("covered_frac", 0.78))
    sig = float(t.get("band_sigma", h * 0.10))
    cover_amp = float(t.get("cover_amp", 0.85))

    # covered route: a lateral Gaussian band of high cover/concealment, lower trafficability
    band = np.exp(-((ys - covered_y) ** 2) / (2 * sig**2))          # [ny] in (0, 1]
    open_band = np.exp(-((ys - corridor_y) ** 2) / (2 * (sig * 1.2) ** 2))

    cover_col = cover_amp * band
    conceal_col = (0.80 / 0.85) * cover_amp * band
    # trafficability: fast on the open corridor (~1.0), slower on the covered route (~0.4),
    # moderate elsewhere (~0.6). This is the speed-vs-cover tradeoff route_bias explores.
    speed_col = np.clip(0.60 + 0.40 * open_band - 0.20 * band, 0.15, 1.0)

    # broadcast lateral profiles across x, add light spatial noise for texture
    cover = np.repeat(cover_col[:, None], nx, axis=1)
    conceal = np.repeat(conceal_col[:, None], nx, axis=1)
    speed = np.repeat(speed_col[:, None], nx, axis=1)

    if profile == "open":
        cover = np.full_like(cover, float(t.get("open_cover", cover_col.mean())))
        conceal = np.full_like(conceal, float(t.get("open_conceal", conceal_col.mean())))
        speed = np.full_like(speed, float(t.get("open_speed", speed_col.mean())))
    elif profile == "chokepoint":
        # A transverse ridge with one gap. The gap is the only fast ground across it, so a force
        # that spreads out has to converge, and it converges at a place the map chooses rather than
        # at a place the operator does.
        xs = (np.arange(nx) + 0.5) * cell
        ridge_x = w * float(t.get("ridge_frac", 0.45))
        ridge_w = float(t.get("ridge_sigma", w * 0.04))
        gap_y = h * float(t.get("gap_frac", 0.30))
        gap_w = float(t.get("gap_sigma", h * 0.07))
        ridge = np.exp(-((xs - ridge_x) ** 2) / (2 * ridge_w**2))[None, :]
        gap = np.exp(-((ys - gap_y) ** 2) / (2 * gap_w**2))[:, None]
        block = ridge * (1.0 - gap)                                  # [ny, nx] in [0, 1)
        speed = np.clip(speed - float(t.get("ridge_slow", 0.55)) * block, 0.05, 1.0)
        cover = np.clip(cover + float(t.get("ridge_cover", 0.30)) * ridge * gap, 0.0, 1.0)
    elif profile != "band":
        raise ValueError(f"unknown terrain profile {profile!r}; "
                         f"expected one of 'band', 'chokepoint', 'open'")

    speed = np.clip(speed + rng.normal(0.0, 0.02, size=speed.shape), 0.1, 1.0)

    route_data = scn.params.get("route")
    start_pt = None
    if route_data is None:
        for f in scn.forces:
            if getattr(f, "route", None) is not None:
                route_data = f.route
                start_pt = f.spawn
                break
    if route_data is None:
        route_data = t.get("route")

    route_obj = None
    if route_data is not None:
        from sandtable.route import RoutePolyline
        if isinstance(route_data, RoutePolyline):
            route_obj = route_data
        else:
            route_obj = RoutePolyline.from_waypoints(route_data, start_point=start_pt)

    return World(size=(w, h), cell=cell, speed=speed, cover=cover, conceal=conceal, route=route_obj)
