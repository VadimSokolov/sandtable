# Routing and Mission Viewer V3 architecture

## Scope and dependency direction

The integration extends the current `convoy-study-integration` history, merged into
`convoy-dev`, on the feature branch `convoy-routing-map-builder`. It does not mark
Issues #18 or #19 complete or merge the entire experimental #18 branch.

Dependencies flow from the browser to application services to domain code:

```text
Browser modules
  → HTTP transport → ViewerApplication
  → ScenarioCompiler → MapPlanningService / FormationBuilder / MissionSettings
  → JobManager → isolated worker → SimulationRunner → Sandtable simulation

MapPlanningService
  → MapValidator / MapExposureResolver / RoadGraphBuilder / RoutingReportBuilder
  → StreetGraph + routing policies and search strategies
```

The core `routing` and `map_builder` packages do not import the viewer or its HTTP
server. The JavaScript draws the backend's graph/cost report; it does not implement a
second mathematical path finder.

## One responsibility per collaborator

| Class or interface | Responsibility |
| --- | --- |
| `EdgeCostPolicy` | Map one road edge to a nonnegative scalar cost |
| `LegacyBlendCost` | Preserve the original Issue #16 cost formula |
| `ExposurePenaltyCost` | Add a positive travel baseline and exposure penalty |
| `PathSearch` | Find a least-cost path using a supplied cost policy |
| `DijkstraSearch`, `AStarSearch` | Implement the two search strategies |
| `RoutePlanner` | Compose a cost policy and search strategy |
| `RoadExposureModel` | Score a polyline's declared-map exposure |
| `RangeExposureModel` | Implement sampled range/proximity and building screening |
| `MapValidator` | Validate geometry, identifiers, input ranges and occupied areas |
| `MapExposureResolver` | Resolve automatic versus manual whole-road exposure |
| `RoadGraphBuilder` | Split crossings, T-junctions and anchors into connected edges |
| `RoutingReportBuilder` | Describe edge costs and the selected path |
| `MapPlanningService` | Orchestrate map validation, topology and initial routing |
| `FormationBuilder` | Produce a common formation specification and preview |
| `ScenarioCompiler` | Compile validated user inputs into a Sandtable scenario |
| `SimulationRunner` | Compose explicit adapters around one engine execution |
| `MissionRecorder` | Capture actual snapshots, events and delivery accounting |
| `JobRepository` | Confine and persist job inputs/status/results atomically |
| `JobManager` | Start processes, limit concurrency and request cancellation |
| `ViewerApplication` | Dispatch application operations through these services |
| `ViewerHttpServer` | Handle loopback HTTP transport and static assets |

`EdgeCostPolicy`, `PathSearch` and `RoadExposureModel` are structural protocols.
`MapPlanningService` accepts injected collaborators; exposure resolvers and topology
builders accept an exposure-model factory. Alternative algorithms or exposure models
can be substituted without rewriting validation or the HTTP layer.

## Automatic exposure and path cost

For each straight polyline segment, use midpoint samples spaced at most 50 m apart.
At sample p and eligible Red site r, with declared weapon range R_r:

```text
q_r(p) = 1 - distance(p,r)/R_r
```

Use q only inside the range and when no conservative raster building rectangle
intersects the sample-to-Red line. A site is eligible when its range and pk are
positive; pk magnitude is not a weight. Clip the sum across eligible sites to 1,
then average samples. For a bent polyline, combine segment averages by their lengths.
This gives E in [0,1]. Manual road values override automatic values and remain editable.
When topology splits a road, automatic exposure is evaluated for each resulting edge.

The builder's positive cost policy is:

```text
w_e = (L_e / s_e) × (1 + 10 β E_e)
C(path) = Σ w_e
```

L is length in metres, s is the dimensionless road trafficability multiplier, β is
the user-selected weight in [0,1], and E is exposure. Cost is in effective metres,
not seconds or casualty probability. Commanded convoy pace remains a separate
mission input. A longer road can have a lower cost when it avoids sufficient exposure.
The graph view reports every edge's length, exposure, multiplier and cost, plus the
selected route and its sum.

Dijkstra and A* minimize exactly the same cost. A* uses distance to the goal multiplied
by the minimum edge-cost/endpoint-distance ratio in the graph. This bounds the
heuristic even when road speeds exceed 1 or supplied lengths differ from geometry.
When the bound is zero it becomes Dijkstra. A result includes selected edge indices,
which preserve the chosen geometry for parallel edges in the core graph API.
The initial map editor rejects duplicate roads between the same nodes.

Exposure uses known static Red positions and simplified building screening. It is
an illustrative planning prior, not Blue's sensed belief or a calibrated risk model.
Routing is chosen before the run. Dynamic replanning around wrecks, moving threats
and bypass behavior are outside this integration.

## Core use without the viewer

```python
from sandtable.routing import ExposurePenaltyCost, RangeExposureModel, ThreatSite

model = RangeExposureModel([ThreatSite(400, 200, weapon_range=300)])
scored_graph = model.apply(graph, manual_edges=[0])
path = scored_graph.plan_path(
    start_id, goal_id, algorithm="astar", cost_policy=ExposurePenaltyCost(0.5)
)
route = scored_graph.to_route_polyline(path.nodes, edge_indices=path.edge_indices)
```

Native scenarios can opt in through `params`:

```json
{
  "route_algorithm": "astar",
  "route_cost_model": "exposure_penalty",
  "route_bias": 0.5,
  "route_exposure": {
    "sample_spacing": 50.0,
    "manual_edge_indices": [0],
    "threat_sites": [{"x": 400, "y": 200, "weapon_range": 300, "pk": 1.0}]
  }
}
```

These fields supplement the existing street graph/start/goal scenario inputs.
An explicit route continues to take precedence. Without opt-in fields, existing
scenarios retain Dijkstra and the exact original blend:

```text
w_legacy = (1 − β) L/s + β L E
```

The legacy policy can produce zero-cost edges; the search supports them. The builder
uses the positive policy to avoid that behavior for new editable maps.

## Simulation adapters and process boundaries

The existing V3 experimental behavior is preserved rather than silently replaced:

* `BuilderWorldAdapter`: declared initial positions and flat road/building terrain.
* `RouteMotionAdapter`: steering-aware arrival, route rejoin, boundary/building
  guards and explicitly selected experimental Herringbone parking.
* `ConsoleTransferAdapter`: explicitly selected successor/absorption console rules.
* `BehaviorEventAdapter`: leadership/contact event observation and declared hooks.
* `EngagementAdapter`: control-first selection from the preserved #18 checkpoint.

Each mission runs in a separate worker process. Scoped hooks temporarily adapt the
core's existing function entry points, then restore them on exit. They must not be
used for concurrent threaded missions in the same interpreter. The study worker
uses spawned processes, not simulation threads. These hooks are a compatibility
boundary; converting the whole simulation into an object hierarchy is not part of
this change. See `adapters/vendor/provenance.json` for the preserved #18 sources.

The renderer shows recorded positions and metrics. Current-frame values are separate
from the final outcome. Payload entered in kg is converted to the core's metric
tonnes; 900 kg = 0.9 tonnes. The 907.18474 kg capacity assumption remains explicit.
Crew exposure retains the core's living-crew, in-range definition; it does not gain
a communication or LOS factor merely because routing uses building screening.

## Data, reproducibility and migration

`ViewerPaths` discovers this repository. No external checkout or hardcoded user
directory is imported. Frontend assets ship in the package. Runtime inputs/results
live under `studies/convoy-study/mission-viewer-v3`; `--home` can override that root.

Requests, status, configuration hashes, recorded frames, outcomes, source hashes
and code revision are retained per job. Original saved records and manifests are
copied byte-for-byte with a SHA-256 audit; they retain historical provenance.
Moving the Python modules necessarily changes new runs' source identities. The
unchanged frozen study design remains the historical design, not a new preregistration.

The existing analysis methods and their limitations are preserved: one synthetic
map, placeholder threat parameters, shared-RNG divergence after behavior changes,
and the original interval estimators. Architecture verification is not evidence of
real-world tactical effectiveness or human workload calibration.

## Verification boundaries

Tests cover exhaustive least-cost solutions, directed/parallel edges, zero-cost
cycles, exposure screening/overrides, crossing and overlap geometry, old graph
compatibility, map-to-scenario compilation and actual spawned engine runs.
Migration checks compare the entire frames/events/outcomes of saved S1 and S12,
seed 0, against fresh runs. Browser checks cover the packaged map, cost report,
saved recordings and new Python job execution.
