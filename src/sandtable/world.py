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
    buildings: np.ndarray | None = None      # optional [ny, nx] bool: True where buildings block LOS
    building_boxes: np.ndarray | None = None # optional [B, 4] float: [xmin, ymin, xmax, ymax]
    street_graph: Any = None                 # optional StreetGraph

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
        """Line-of-sight clear between (x0, y0) and (x1, y1).

        Returns boolean array matching the broadcast shape of the inputs.
        If self.buildings is None: returns np.ones(..., bool) (flat-terrain baseline).
        If self.buildings is present: checks ray traversal against building cells.
        """
        b_x0, b_y0, b_x1, b_y1 = np.broadcast_arrays(x0, y0, x1, y1)
        out_shape = b_x0.shape

        if self.buildings is None:
            return np.ones(out_shape, dtype=bool)

        flat_x0 = b_x0.ravel()
        flat_y0 = b_y0.ravel()
        flat_x1 = b_x1.ravel()
        flat_y1 = b_y1.ravel()

        k_rays = flat_x0.size
        if k_rays == 0:
            return np.ones(out_shape, dtype=bool)

        dx = flat_x1 - flat_x0
        dy = flat_y1 - flat_y0
        dist = np.hypot(dx, dy)
        max_d = float(np.max(dist)) if dist.size else 0.0

        if max_d < 1e-6:
            iy, ix = self._idx(flat_x0, flat_y0)
            clear = ~self.buildings[iy, ix]
            return clear.reshape(out_shape)

        step_len = max(1.0, self.cell * 0.5)
        n_steps = int(np.clip(np.ceil(max_d / step_len), 2, 200))

        t = np.linspace(0.01, 0.99, n_steps)
        pts_x = flat_x0[:, None] + dx[:, None] * t[None, :]
        pts_y = flat_y0[:, None] + dy[:, None] * t[None, :]

        ny, nx = self.buildings.shape
        ix = np.clip((pts_x / self.cell).astype(np.intp), 0, nx - 1)
        iy = np.clip((pts_y / self.cell).astype(np.intp), 0, ny - 1)

        blocked = np.any(self.buildings[iy, ix], axis=1)
        clear = ~blocked

        return clear.reshape(out_shape)

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

    cover = np.repeat(cover_col[:, None], nx, axis=1)
    conceal = np.repeat(conceal_col[:, None], nx, axis=1)
    speed = np.repeat(speed_col[:, None], nx, axis=1)

    buildings_mask: np.ndarray | None = None
    building_boxes: np.ndarray | None = None

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
    elif profile == "urban":
        block_w = float(t.get("block_width", 200.0))
        block_h = float(t.get("block_height", 200.0))
        street_w = float(t.get("street_width", 50.0))
        period_x = block_w + street_w
        period_y = block_h + street_w

        xs = (np.arange(nx) + 0.5) * cell
        ys_2d = ys[:, None]
        xs_2d = xs[None, :]

        mod_x = xs_2d % period_x
        mod_y = ys_2d % period_y

        is_building = (mod_x > street_w) & (mod_y > street_w)
        margin_x = int(np.ceil(street_w / cell))
        margin_y = int(np.ceil(street_w / cell))
        is_building[:, :margin_x] = False
        is_building[:, -margin_x:] = False
        is_building[:margin_y, :] = False
        is_building[-margin_y:, :] = False

        speed = np.where(is_building, 0.05, 1.0)
        cover = np.where(is_building, 0.90, 0.05)
        conceal = np.where(is_building, 0.90, 0.05)
        buildings_mask = is_building
    elif profile != "band":
        raise ValueError(f"unknown terrain profile {profile!r}; "
                         f"expected one of 'band', 'chokepoint', 'open', 'urban'")

    if profile != "urban":
        speed = np.clip(speed + rng.normal(0.0, 0.02, size=speed.shape), 0.1, 1.0)
    else:
        street_noise = rng.normal(0.0, 0.02, size=speed.shape)
        speed = np.where(is_building, 0.05, np.clip(speed + street_noise, 0.1, 1.0))

    raw_buildings = scn.params.get("buildings")
    if raw_buildings is None:
        raw_buildings = t.get("buildings") or t.get("building_boxes")

    if raw_buildings is not None:
        if isinstance(raw_buildings, np.ndarray) and raw_buildings.ndim == 2 and raw_buildings.shape == (ny, nx):
            buildings_mask = raw_buildings.astype(bool)
        elif isinstance(raw_buildings, (list, tuple, np.ndarray)):
            boxes = np.asarray(raw_buildings, dtype=np.float64)
            if boxes.ndim == 2 and boxes.shape[1] == 4:
                building_boxes = boxes
                if buildings_mask is None:
                    buildings_mask = np.zeros((ny, nx), dtype=bool)
                for b in boxes:
                    x_min, y_min, x_max, y_max = b
                    ix0 = int(np.clip(np.floor(x_min / cell), 0, nx - 1))
                    ix1 = int(np.clip(np.ceil(x_max / cell), 0, nx))
                    iy0 = int(np.clip(np.floor(y_min / cell), 0, ny - 1))
                    iy1 = int(np.clip(np.ceil(y_max / cell), 0, ny))
                    buildings_mask[iy0:iy1, ix0:ix1] = True
                    speed[iy0:iy1, ix0:ix1] = 0.05
                    cover[iy0:iy1, ix0:ix1] = 0.90
                    conceal[iy0:iy1, ix0:ix1] = 0.90

    raw_sg = scn.params.get("street_graph")
    if raw_sg is None:
        raw_sg = t.get("street_graph")

    street_graph_obj = None
    if raw_sg is not None:
        from sandtable.street_graph import StreetGraph
        if isinstance(raw_sg, StreetGraph):
            street_graph_obj = raw_sg
        elif isinstance(raw_sg, dict):
            street_graph_obj = StreetGraph.from_dict(raw_sg)
    elif profile == "urban":
        from sandtable.street_graph import StreetGraph
        block_w = float(t.get("block_width", 200.0))
        block_h = float(t.get("block_height", 200.0))
        street_w = float(t.get("street_width", 50.0))
        period_x = block_w + street_w
        period_y = block_h + street_w
        n_inter_x = max(2, int(np.ceil(w / period_x)) + 1)
        n_inter_y = max(2, int(np.ceil(h / period_y)) + 1)
        street_graph_obj = StreetGraph.create_grid(
            nx=n_inter_x,
            ny=n_inter_y,
            spacing_x=period_x,
            spacing_y=period_y,
            origin=(street_w * 0.5, street_w * 0.5),
            width=street_w,
            speed_mult=1.0,
            exposure=0.5,
        )

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
    elif street_graph_obj is not None:
        gx, gy = scn.objective.goal
        sx, sy = (0.0, h * 0.5)
        for f in scn.forces:
            if getattr(f, "spawn", None) is not None:
                sx, sy = f.spawn
                break
        u_start = street_graph_obj.find_nearest_node(sx, sy)
        u_goal = street_graph_obj.find_nearest_node(gx, gy)
        route_bias = float(scn.params.get("route_bias", 0.0))
        path_nodes = street_graph_obj.find_path(u_start, u_goal, route_bias=route_bias)
        if len(path_nodes) >= 2:
            route_obj = street_graph_obj.to_route_polyline(path_nodes)

    return World(
        size=(w, h),
        cell=cell,
        speed=speed,
        cover=cover,
        conceal=conceal,
        route=route_obj,
        buildings=buildings_mask,
        building_boxes=building_boxes,
        street_graph=street_graph_obj,
    )
