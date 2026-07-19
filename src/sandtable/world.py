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

import numpy as np

from sandtable.scenario import Scenario


@dataclass
class World:
    size: tuple                # (width, height) metres
    cell: float                # metres per raster cell
    speed: np.ndarray          # [ny, nx] trafficability multiplier in [0, 1]
    cover: np.ndarray          # [ny, nx] in [0, 1]
    conceal: np.ndarray        # [ny, nx] in [0, 1]

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
        x = np.asarray(x); y = np.asarray(y)
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
    """Build terrain rasters from scn.terrain (falls back to the UC-3 corridor/defilade profile)."""
    w, h = scn.size
    cell = float(scn.terrain.get("cell", 25.0))
    nx, ny = int(np.ceil(w / cell)), int(np.ceil(h / cell))
    ys = (np.arange(ny) + 0.5) * cell           # cell-centre y for each row

    corridor_y = h * 0.5
    covered_y = h * 0.78
    sig = float(scn.terrain.get("band_sigma", h * 0.10))

    # covered route: a lateral Gaussian band of high cover/concealment, lower trafficability
    band = np.exp(-((ys - covered_y) ** 2) / (2 * sig**2))          # [ny] in (0, 1]
    open_band = np.exp(-((ys - corridor_y) ** 2) / (2 * (sig * 1.2) ** 2))

    cover_col = 0.85 * band
    conceal_col = 0.80 * band
    # trafficability: fast on the open corridor (~1.0), slower on the covered route (~0.4),
    # moderate elsewhere (~0.6). This is the speed-vs-cover tradeoff route_bias explores.
    speed_col = np.clip(0.60 + 0.40 * open_band - 0.20 * band, 0.15, 1.0)

    # broadcast lateral profiles across x, add light spatial noise for texture
    cover = np.repeat(cover_col[:, None], nx, axis=1)
    conceal = np.repeat(conceal_col[:, None], nx, axis=1)
    speed = np.repeat(speed_col[:, None], nx, axis=1)
    speed = np.clip(speed + rng.normal(0.0, 0.02, size=speed.shape), 0.1, 1.0)

    return World(size=(w, h), cell=cell, speed=speed, cover=cover, conceal=conceal)
