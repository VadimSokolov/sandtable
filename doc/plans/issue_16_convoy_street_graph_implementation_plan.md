# Implementation Plan: Convoy Street Graph with Blocking Line of Sight (Issue #16)

**Issue**: [#16: Convoy: street graph with blocking line of sight](https://github.com/VadimSokolov/sandtable/issues/16)  
**Parent Roadmap**: Phase 3: Route Stationing & Urban Street Graphs  
**Date**: October 2026 | **Status**: Proposed Plan  
**Doctrinal Standards**: 
- ATP 4-11 (Convoy Operations): Urban street navigation, formation width constraints, and cornering.
- ATP 4-16 (Movement Control): Road network capacity, routing, and route clearance.
- SandTable Design Manifesto: `doc/contested_logistics_one_pager.md` (Section: *Urban topology: the street graph*).

---

## 1. Problem Statement & Motivation

In open-terrain and unconstrained highway scenarios, vehicles operate under broad visibility and linear corridors. However, in urban environments, operations are fundamentally shaped by two physical realities:

1. **Discrete Street Network Topology (The Graph)**:
   - Roads form an interconnected graph of intersections (nodes) and street segments (edges).
   - Connectivity is what makes routing a choice: an autonomy or operator must decide whether to commit to a high-speed arterial boulevard or divert through covered, slower secondary streets.
   - Street edges carry physical attributes: `width` (constraining how many vehicles fit abreast) and `speed_multiplier`.

2. **Occlusion by Buildings (Blocking Line-of-Sight)**:
   - Buildings and urban infrastructure physically block electromagnetic and optical rays between observers and targets.
   - Ground sensors cannot detect targets through solid building footprints.
   - Direct-fire weapons cannot engage targets through buildings even if an aerial reconnaissance asset has broadcast the target's coordinates to the common operational picture.
   - Follower vehicles in a convoy lose visual contact with their leader when the leader turns around a blind street corner, requiring the follower to dead-reckon along the roadway until visual contact is re-established.

`world.los()` is currently a flat-terrain stub that unconditionally returns `True`. Issue #16 replaces this stub with authentic, vectorized segment-blocking line-of-sight tests over building footprints and integrates the street graph into routing, sensing, engagement, and follower behavior.

---

## 2. Explicit Scope Boundaries

As strictly specified in `doc/contested_logistics_one_pager.md` (Line 42):
> *"A street graph plus blocking line of sight is a topology, not a city. No building heights, no floors or interiors, no multipath, no civilian traffic, no pedestrians. Naming those exclusions beats letting the word 'urban' imply them."*

- **In Scope**:
  - 2D graph topology (nodes, edges, widths, speeds, exposures).
  - Shortest-path routing over the graph parameterized continuously by `route_bias` in [0, 1].
  - Translation of graph paths into `RoutePolyline` for seamless integration with Issue #13 arc-length stationing.
  - 2D building footprints (axis-aligned rectangular blocks and raster masks).
  - Vectorized ray-marching / slab-intersection line-of-sight test in `world.los()`.
  - Integration into `sensing.py`, `engagement.py`, and `behavior.py`.
  - Replay serialization and interactive visualization in `route_dashboard.html`.
  - 100% byte-identity when graph and buildings are unconfigured (`street_graph is None`, `buildings is None`).

- **Out of Scope**:
  - 3D indoor building floors, room interiors, and stairs.
  - Radio-frequency multipath reflections and diffraction around edges.
  - Non-combatant civilian vehicles and pedestrian traffic.
  - Dynamic building destruction / rubble formation.

---

## 3. Architecture & Technical Design

```
+-----------------------------------------------------------------------------------+
|                              Street Graph Topology                                |
|                                                                                   |
|   Node (Intersection) ---- Edge (Street Segment: width, speed, exposure) ---- Node   |
+-----------------------------------------+-----------------------------------------+
                                          |
                        Shortest Path by route_bias
                        (0.0 = speed, 1.0 = cover)
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        RoutePolyline (from Issue #13)                             |
|                                                                                   |
|           Continuous 1D arc-length coordinate s, point_at(s), project(x, y)       |
+-----------------------------------------+-----------------------------------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
+------------------------------------+   +------------------------------------------+
|  Convoy Vehicle Kinematics         |   |  Urban Environment (World & Buildings)   |
|                                    |   |                                          |
| - Pure-pursuit road carrot         |   | - Building Footprints ([ny, nx] raster)  |
| - Follower station: s* = s_ref - Δs|   | - Axis-aligned blocks [xmin, ymin, ...]  |
| - Dead-reckon on blind corner loss |   | - Vectorized world.los(x0, y0, x1, y1)   |
+-----------------+------------------+   +---------------------+--------------------+
                  |                                            |
                  +---------------------+----------------------+
                                        |
                                        v
                 +---------------------------------------------+
                 |       Combined Arms Occlusion Engine        |
                 |                                             |
                 | - sensing.py: Ground LOS blocked by blocks  |
                 | - engagement.py: Direct fire requires LOS   |
                 | - behavior.py: Tracking lost around corner  |
                 | - UAS Overwatch: Air LOS looks over roofs   |
                 +---------------------------------------------+
```

### Component 1: Street Graph Module (`src/sandtable/street_graph.py`)

A new module defining the graph topology:

```python
@dataclass(frozen=True)
class StreetNode:
    id: str | int
    x: float
    y: float

@dataclass(frozen=True)
class StreetEdge:
    u: str | int
    v: str | int
    width: float = 8.0          # Street width in meters (road capacity)
    speed_mult: float = 1.0     # Trafficability multiplier in (0, 1]
    exposure: float = 0.5       # Exposure factor in [0, 1] (0 = covered alley, 1 = open avenue)
    length: float = 0.0         # Segment length (computed or custom)
    geometry: tuple[tuple[float, float], ...] = () # Optional intermediate bend points

class StreetGraph:
    def __init__(self, nodes: dict[str | int, StreetNode], edges: list[StreetEdge]):
        ...

    def find_path(self, start_node: str | int, goal_node: str | int,
                  route_bias: float = 0.0) -> list[str | int]:
        """Dijkstra / A* path search optimizing cost:
        cost(e) = (1 - route_bias) * (length / speed_mult) + route_bias * (length * exposure)
        - route_bias = 0.0: Purest speed-optimal route (arterial boulevards).
        - route_bias = 1.0: Purest safety-optimal route (covered backstreets).
        """
        ...

    def to_route_polyline(self, path_nodes: list[str | int]) -> RoutePolyline:
        """Converts graph path into a continuous RoutePolyline for Issue #13 kinematics."""
        ...
```

### Component 2: Building Footprints & Vectorized LOS (`src/sandtable/world.py`)

1. **Building Footprints**:
   - `World` dataclass extended with:
     - `street_graph: StreetGraph | None = None`
     - `buildings: np.ndarray | None = None` (boolean array of shape `(ny, nx)` where `True` marks solid building structure).
     - `building_boxes: np.ndarray | None = None` (float array `[B, 4]` storing bounding coordinates `[xmin, ymin, xmax, ymax]`).

2. **Vectorized Line of Sight (`world.los`)**:
   ```python
   def los(self, x0, y0, x1, y1) -> np.ndarray:
       """Line-of-sight test between points (x0, y0) and (x1, y1).
       
       Returns boolean array matching the broadcast shape of the inputs.
       If self.buildings is None: returns np.ones(..., bool) (100% byte-identical).
       If self.buildings is present: checks ray traversal against building cells.
       """
   ```
   - **Algorithm**:
     - Fast vectorized ray-marching across the building raster:
       $$\vec{p}(t) = \vec{p}_0 + t \cdot (\vec{p}_1 - \vec{p}_0), \quad t \in [0, 1]$$
     - Sample interval $\Delta t \le \frac{\text{cell}}{2 \cdot \|\vec{p}_1 - \vec{p}_0\|}$, ensuring no building cell is skipped.
     - Early exit: Rays with zero distance or within the same cell are trivially unblocked.
     - For box lists: Exact 2D slab intersection (Liang-Barsky test).

### Component 3: Integration into Simulation Subsystems

1. **Sensing Subsystem (`src/sandtable/sensing.py`)**:
   - Line 44 already calls `world.los(ent.x[:, None], ent.y[:, None], ent.x[None, :], ent.y[None, :])`.
   - UAS domain handling: Observers with `domain == AIR` (e.g. overwatch drones at altitude $z = 200\text{m}$) have clear downward sightlines unless specified otherwise, whereas ground-to-ground sensor rays are blocked by buildings.

2. **Engagement Subsystem (`src/sandtable/engagement.py`)**:
   - Add direct-fire line-of-sight check in `_side_damage`:
     ```python
     los_ok = world.los(ent.x[shooters, None], ent.y[shooters, None],
                        ent.x[None, targets], ent.y[None, targets])
     engageable = engageable & los_ok
     ```
   - Prevents ground units from shooting through buildings even if an aerial reconnaissance drone has spotted the enemy on the shared tactical network.

3. **Behavior Subsystem (`src/sandtable/behavior.py`)**:
   - Line-of-sight follower tracking around blind corners:
     ```python
     if got:
         los_ref = world.los(ent.x[i], ent.y[i], ent.x[ref], ent.y[ref])
         got = got and bool(los_ref)
     ```
   - When a leader rounds a 90-degree corner behind a building block, the follower enters dead reckoning (`trk_stale_steps += 1`) along its route station until visual contact is re-acquired.

### Component 4: Procedural Urban Terrain Profile (`profile: "urban"`)

In `world.py::build_world`:
- New terrain profile option `"urban"`, creating a regular or irregular grid of street channels and rectangular building blocks.
- Street channels have high trafficability (`speed = 1.0`), while building blocks have `speed = 0.0` (impassable) and `buildings = True` (opaque).

---

## 4. Work Breakdown & Implementation Steps

### Phase 1: Street Graph Module & Shortest Path (`src/sandtable/street_graph.py`)
- [ ] Define `StreetNode`, `StreetEdge`, and `StreetGraph` data classes.
- [ ] Implement Dijkstra / A* routing with continuous `route_bias` cost weighting.
- [ ] Implement `to_route_polyline(path)` converting node sequences into `RoutePolyline`.
- [ ] Add serialization methods (`to_dict()`, `from_dict()`).

### Phase 2: Building Footprints & Vectorized `world.los()` (`src/sandtable/world.py`)
- [ ] Add `street_graph`, `buildings`, and `building_boxes` attributes to `World`.
- [ ] Implement fast vectorized ray traversal in `World.los(x0, y0, x1, y1)`.
- [ ] Implement `"urban"` procedural generator in `build_world(scn, rng)`.
- [ ] Preserve 100% byte-identity when `buildings is None` and `street_graph is None`.

### Phase 3: Subsystem Integration
- [ ] In `src/sandtable/scenario.py`: Parse `street_graph` and `buildings` from scenario dict. If `route` is a graph path or origin-destination pair, compute the active route.
- [ ] In `src/sandtable/sensing.py`: Ensure air-to-ground LOS vs ground-to-ground LOS distinction is handled properly.
- [ ] In `src/sandtable/engagement.py`: Enforce direct-fire LOS gating so fire does not penetrate buildings.
- [ ] In `src/sandtable/behavior.py`: Gate visual follower sensing through `world.los` to trigger dead-reckoning on blind corners.
- [ ] In `src/sandtable/replay.py`: Add `street_graph` and `buildings` to recorded trace metadata.

### Phase 4: Test Suite Verification (`tests/test_convoy_street_graph.py`)
- [ ] Test 1: `test_street_graph_off_is_byte_identical` (All baseline missions bit-identical).
- [ ] Test 2: `test_street_graph_shortest_path_bias_sweep` (Speed vs cover route selection).
- [ ] Test 3: `test_graph_to_polyline_preserves_kinematics` (Seamless interface with Issue #13).
- [ ] Test 4: `test_building_los_blocking` (Known geometric ray intersections return correct boolean).
- [ ] Test 5: `test_sensing_blocked_by_building` (Ground target hidden behind building is unseen).
- [ ] Test 6: `test_engagement_blocked_by_building` (No direct-fire damage through buildings).
- [ ] Test 7: `test_follower_blind_corner_dead_reckon` (Follower dead-reckons around building corner).

### Phase 5: Replay & Visualization Updates
- [ ] Update `tools/make_route_dashboard.py` to include an urban grid scenario with buildings and street graph.
- [ ] Update `report/viz/route_dashboard.html` canvas to render building blocks, street graph edges/nodes, and line-of-sight occlusion fans.

---

## 5. Verification & Acceptance Criteria

1. **Byte-Identity**: Existing tests (`tests/test_world.py`, `tests/test_convoy*.py`, `tests/test_sim_repro.py`) continue passing 100% with zero diffs when urban features are absent.
2. **Performance**: Vectorized `world.los()` must evaluate 400 rays in under 0.5 ms on standard CPU, maintaining real-time simulation throughput.
3. **Doctrinal Correctness**: Convoy adheres to street lane widths; blind corners induce realistic dead-reckoning rather than sudden halts.
4. **Clean Code**: Passes `ruff check .` with zero warnings and zero em dashes anywhere.
