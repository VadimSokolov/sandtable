# Contested urban logistics: one-pager and plan

Project status as of September 11, 2026. 

## SandTable Simulator

SandTable developed at GMU is a pure-Python, mission-level simulator for autonomy-enabled ground and air formations. It is the fast inner loop. A single mission runs in about 120 ms (UC-3 route-vs-defilade). Thus, it can be used for large parameter sweeps, optimisation and reinforcement learning tasks. 

It is an agent-based dimulator with a top-level mission function, `run_mission(scenario, seed) -> metrics`. Agent state advances by a fixed-timestep loop. The simulator is stochastic but provides deterministic behavior given the fixed seed. Thus it allows for uncertainty quantification and paired comparisons.

What it models:

- **Terrain and movement.** Coarse `speed`, `cover` and `conceal` rasters in `band`, `open` or `chokepoint` profiles; pure-pursuit movement with a tempo multiplier.
- **Sensing and engagement.** Cookie-cutter detection, aspect-sector probability of kill, believed tracks and decoys, suppression, finite munitions, and counter-UAS attrition of a recon swarm.
- **Command and control.** Direct, mixed and supervisory control modalities, an operator console with queueing and admission control, and an information-free null arm to price what the console's information is actually worth.
- **Comms and EW.** The C0-C5 degradation ladder mapping to latency and per-message drop, with two channel models (memoryless Bernoulli and bursty Gilbert-Elliot) calibrated to the same mean so burstiness is separable from loss.
- **Formations.** Leader-follow station keeping with star and chain topologies, and a communication-graph reading of a formation scored by algebraic and vertex connectivity.
- **Analysis.** Mission KPIs, cost-weighted exchange ratios, replay traces, and Bayesian test-and-evaluation.

It plugs into polarisopt, the external DOE and Bayesian-optimization driver,  to perform Bayesian optimization. 

## The mission

Blue (vehicles, drones and people) moves goods and people through contested urban terrain. Red contests the move.  Attrition becomes a cost term and we use  TTP Effectiveness (delivery rate, time to delivery, cargo lost) and Contested Performance (delivery as a function of rung on the C0-C5 comms and EW degradation ladder) as metrics.

## Three focus areas

Moving forward we are to focus on the follwing extensiosn of the SandTable: optimisation for **formation concepts discovery**, an **ATV-size UGV moving goods and people**, and **jamming (EME)**. A street graph (Urban) will be used for our simulated scenarios. 

## Urban topology: the street graph

**The graph.** Nodes are intersections, edges are street segments carrying a width and a speed multiplier. Connectivity is the thing a graph gives that a raster cannot, and connectivity is what makes a route a choice. Keep the existing `cover` and `conceal` rasters underneath it unchanged, so the graph adds reachability without moving anything already measured.

**Routing over the graph.** This is the expensive piece, and the cost is worth knowing before anyone starts. `route_bias` is a declared continuous search dimension, `{min: 0.0, max: 1.0}`, in `plugin.py` and in five study configs (`uc3_sweep`, `uc3_morris`, `uc3_sweep_hopper`, `uc3_bo`, `uc3_frontier_hopper`), the last of which is a dense one-dimensional sweep of exactly that scalar.

The path that keeps those studies alive: define `route_bias` on the graph as a preference weight over edge exposure that a shortest-path search consumes. It keeps its current meaning at both ends (0 favours speed, 1 favours cover), the frontier study still reads, and route choice becomes an emergent consequence of the weight rather than a new categorical dimension. If discrete route selection is wanted later, `plugin.py` already coerces `type: int` parameters, so an integer route index is the cheap bridge; confirm against the polarisopt plugin contract before fixing that representation.

**Line of sight.** Make `world.los()` a segment-blocking test: a ray is clear if it crosses no building cell. It is cheap on the raster that already exists, and it is what gives the other two items their urban character. Occlusion is the first-order urban effect, and both sensing and jamming read it from the same function.

**What the graph unlocks, item by item.** Formations get an edge width, which is what determines how many vehicles fit abreast. Logistics gets a second route, which is what makes "which way do we go" a decision an operator or an autonomy can be scored on. Jamming gets geometry, so a jammer can be driven around rather than only endured.

**Scope boundary, to be stated wherever this ships.** A street graph plus blocking line of sight is a topology, not a city. No building heights, no floors or interiors, no multipath, no civilian traffic, no pedestrians. Naming those exclusions beats letting the word "urban" imply them.

## TTP as the baseline

The measurement discipline the whole plan hangs on, and not specific to any one item. A declared, fixed TTP is the arm every variation is read against. Without one, a formation comparison, a cargo-routing comparison and a jamming comparison each report a number with nothing underneath it.

The repository already runs this pattern, and this should use it rather than invent a second one. Every extension here is switchable with an "off" state byte-identical to the baseline (`mechanics`, `personality`, `belief` and `engagement` all state it in their module headers), and `c2.py` goes further with an information-free null: a console that refuses requests at random has admission tightness and no triage, so anything a foreseeing console reproduces over that arm was never information. A Red TTP baseline is the same construction pointed at the threat.

Two rules follow. Register the Red TTP before Blue variation runs, so the baseline is not chosen with knowledge of the result. And hold it fixed across all three items, so a formation result and a jamming result stay commensurable instead of each carrying its own private control.

## Baseline convoy

The Blue TTP (tactics, techniques and procedures) that formation, vehicle and jamming comparisons are read against is a doctrinal convoy built only from publications approved for public release. ATP 4-11 sends the reader to ATP 4-01.45 (multi-service tactical convoy operations, June 2026) for convoy security, battle drills and planning detail. Its release status is unconfirmed, so nothing here draws on it, and if the sponsor releases it, its numbers replace the placeholders below without changing the structure.

**The convoy.** A convoy is a group of vehicles moving from one origin to a common destination under a single commander. Doctrine nests it in three elements: a march unit (up to 25 vehicles, about a squad to a platoon), a serial (2 to 5 march units) and a column (2 to 5 serials), so a convoy runs from 6 vehicles to 300 (ATP 4-11, March 2026, G-7). Every element has a head (its first vehicle, carrying the pacesetter, who sets the pace, meaning the regulated speed, that meets the schedule), a main body, and a trail (recovery, maintenance and medical vehicles). On the road the formation is a column, which FM 3-90 (May 2023, 2-3) prescribes when contact is not expected early, the objective is distant, and speed and control matter most. The reference convoy is fifteen vehicles in one serial of three march units of five. Three march units per serial is ATP 4-11's own worked example (G-8) and five vehicles is the autonomous march unit below, so the two arms compare like for like. Both are declared choices and both are search dimensions.

**Two arms.** In the manned arm every vehicle has a driver and each march unit is led by its control vehicle. In the autonomous arm each march unit is one manned control vehicle leading four autonomous trucks, the near-term organization of the Army's Autonomous Transport Vehicle - System (ATV-S, an autonomy applique kit for tactical wheeled vehicles, first fitted to the M1075A2 Palletized Load System truck; it is not the all-terrain-vehicle-size UGV of item 2). The march unit commander sets the gap as a time, the desired speed, obstacle-detection sensitivity and blackout-drive mode from a tablet (ATP 4-11, M-4 and M-5). The arms differ in who rides in the trucks and in what the followers depend on, so both are read on delivery rate, time to delivery and cargo lost against the C0-C5 rung, and on personnel exposure, the crew-steps spent inside the weapon range of a living Red shooter.

**What doctrine fixes and what it leaves open.**

| Quantity | Source | Status |
|---|---|---|
| Element sizes and nesting | ATP 4-11, G-7 | Fixed ranges |
| Head, main body, trail; pacesetter | ATP 4-11, G-11 | Fixed |
| Column on the route | FM 3-90, 2-3 | Fixed |
| Keep march units large, split into serials when security needs separation | ATP 4-11, G-9 | Fixed rule, unquantified |
| Gap between vehicles (meters) and between elements (kilometers) | ATP 4-16 (April 2022), C-5 | Scale fixed, values open |
| Pace (regulated speed) and rate of march (average speed including short halts) | ATP 4-16, C-2 | Definitions fixed, values open |
| Time gap | ATP 4-16, C-4; ATP 4-11, M-5 | Definition fixed, value open |
| Security vehicle ratio | ATP 4-11, G-13 | Left to theater requirements, value open |
| Autonomous march unit of one control vehicle and four trucks | ATP 4-11, M-5 | Fixed for the near term |
| Battle drills and security details | ATP 4-01.45 | Unavailable, excluded |

Open values are placeholders declared before any variation runs, for the reason "TTP as the baseline" gives for the Red TTP, and a result that depends on one is reported across its swept range.

**The tension the baseline prices.** ATP 4-11 (G-9) says to keep march units large because the gaps between small ones consume road space, and to split into serials when security warrants more separation. FM 4-0 (March 2026, 1-46) says distributed operations are sustained at the cost of efficiency. Neither quantifies the trade. In SandTable it is a curve: separation (march unit size, number of serials, gaps between elements) against road space and pass time on one side, and exposure and cargo lost on the other. Road space is the length of road the column occupies, from the lead vehicle's front bumper to the trail vehicle's rear bumper with every gap included, plus a safety factor. Pass time is how long the column takes to pass a point, and the time gap is the time between the trail of one element and the head of the next passing that point (ATP 4-16, C-4 and C-5). The doctrinal convoy is one registered point on that curve, and formation concept discovery (item 1) searches the rest of it and is judged against that point. Army Sustainment commentary proposes leaving the convoy altogether, for node-based distribution with relocating nodes (1st Armored Division, 2025) or for mixed convoys with commercial vehicles under signature management (3rd Infantry Division, 2026). Those are candidate arms for item 1, not baseline, and they need a node model and a signature model that SandTable does not have.

**Capabilities to add.** Today SandTable places a force on one line (`ForceSpec.formation` is `column`, `line` or `wedge`, with one `spacing` in meters), steers each blue ground vehicle along a scripted lane (`ForceSpec.route` is declared and nothing reads it), and, when the behavior layer is on, holds each follower at a fixed distance behind a tracked leader (`rank * gap` for a star, one `gap` behind the vehicle ahead for a chain). `tempo` is the only speed control and it is one scalar for the whole force, and mission success is the fraction of the force that reaches the goal. The nearest existing scenario is `experiments/ar_scenarios/convoy_leader_follower.json`, six blue vehicles in one leader-follower column against five static Red defenders, and although its name says resupply, nothing in it is carried or delivered. Eight changes close the distance to the convoy above, and issue #7 tracks them. Each is opt-in with an off state byte-identical to the current output, the idiom `mechanics`, `personality`, `belief`, `counter_uas` and `behavior` already follow, and each ships an off-path test modelled on `tests/test_counter_uas.py::test_off_is_byte_identical`.

- **Convoy hierarchy (#8).** March units, serials and the column, head, main body and trail, and vehicle roles (control, cargo, security, recovery). A `convoy` block resolved at build time into optional `Entities` arrays (march unit, serial, section, role) with neutral defaults, `leader` set to the march unit head, and a succession rule for a lost head (today a star follower, which stations on the leader, reverts to waypoint navigation, and a chain follower, which stations on the vehicle ahead, closes up). Test: an absent block leaves `build_entities` unchanged, and sizes outside the doctrinal ranges are rejected.
- **Route and arc-length stationing (#13).** A column on a route with gaps measured along the road. A route polyline in `world.py` (a street-graph path once the topology work lands), a progress coordinate per vehicle, and stations as arc length behind the reference in place of a straight offset along its heading, which equals road distance only on a straight road. Test: positions match today's stationing on a straight route, and the gap holds on a dogleg.
- **Pace and time gap (#10).** Pace, rate of march and the gap as a time. A per-vehicle speed cap in `motion.step`, element heads driving at the declared pace, and a follower station of `max(gap, speed * time_gap)`. Test: cap off is byte-identical, and cap on gives the declared steady speed and a measured time gap within one step of the declared one.
- **Cargo and delivery (#9).** The convoy's purpose. Per-vehicle cargo, `delivered_frac`, `time_to_delivery` and `cargo_lost` in `metrics.py`, and a delivery condition in place of `survive_fraction` as the stopping test when cargo is declared (the cargo-as-state change item 2 calls for). Test: loaded cargo equals delivered plus lost plus in transit, and a scenario without cargo returns the metrics it returns now.
- **Doctrine arithmetic (#11).** The ATP 4-16 quantities: column length, road space, pass time and time gap. A `convoy_metrics.py` beside `formation_metrics.py` and a vehicle length on `PlatformType`. Test: the ATP 4-16 identities hold on constructed columns (time equals distance over rate of march, and road clearance time equals pass time plus time distance), which is also the evidence that the simulated convoy is the doctrinal one.
- **Security vehicles and reaction (#12).** A ratio of security vehicles (gun trucks) to other vehicles, which G-13 leaves to theater requirements. A security platform type placed by ratio and one reaction state in `behavior.py` (continue, halt or disperse on contact), declared as a single generic rule because the battle-drill detail sits in ATP 4-01.45. Test: no security vehicles is byte-identical, and the state draws no random numbers when absent.
- **Separation as a search dimension (#15).** The G-9 tradeoff. March unit size, march unit and serial counts, element gap, time gap, pace and security ratio exposed as `params` and declared in the polarisopt study, as `formation_spread` and `tempo` already are. Test: each parameter at its registered baseline value reproduces the registered baseline metrics.
- **Autonomous march unit and personnel exposure (#14).** ATP 4-11, M-5. A crew count per vehicle (zero for an autonomous truck) and a crew-steps-at-risk metric, the crew of each living vehicle summed over the steps it spends inside the weapon range of a living Red shooter, on top of the existing `LEADER_FOLLOW` mode, whose `follow_mode`, `follow_topology`, `track_timeout` and `follow_outage` controls already model a follower that depends on a link or on its own sensors. Test: existing metrics are unchanged with all vehicles manned, changing only the crew counts on one seed changes no other metric, and crew-steps at risk is zero when no Red shooter is ever in range and equals crew times steps alive when every living vehicle is in range throughout.

**Order.** Convoy hierarchy, pace and time gap, doctrine arithmetic and separation as a search dimension run on the existing `band` map as a straight road, and they are enough to run the manned arm and check it against ATP 4-16. Cargo and delivery then makes it a delivery problem. Route and arc-length stationing waits for the street graph, since a column on a bend is where straight-offset stationing breaks. Security vehicles and the autonomous march unit come last. Red stays the existing static defender for the first runs. Red finding and engaging the column with unmanned aircraft (FM 4-0 expects the enemy to use unmanned aircraft of every size against sustainment formations) and the jamming field of item 3 are what make the contest realistic. The jamming field has its own section (item 3), and the unmanned-aircraft contest has none yet.

## 1. Formation concepts

Make formation a scenario-level noun: a `formation` block resolved into per-vehicle station offsets, so `motion.step` keeps the job it already has and the geometry is data rather than code. `behavior.py` already supplies the mechanics to build on, with column leader-follow, star and chain follow topologies, and dead reckoning past `track_timeout`.

Let the street graph choose the admissible geometries rather than the author: edge width against vehicle width determines how many fit abreast, so column and staggered column fall out for urban segments. Wedge and echelon want open ground, so declare them out of scope rather than implement them and never exercise them.

`formation_metrics.py` is the read-out, and it makes a sharper point than it was written for. Each geometry induces a different disc graph, so each carries a different algebraic and vertex connectivity. The standing counterexample in that module, the path graph whose vertex connectivity stays at 1 however long it gets, is a column. A column in a city street is exactly the case the resilient-consensus literature warns about, and the testbed can state that.

Carry the module's scope boundary forward without softening it: it scores communication topology, not mission tolerance. A formation comparison must not become a claim that the formation tolerates f compromised vehicles.

## 2. ATV-size UGV, contested logistics

Cargo becomes state, and delivery becomes the success condition. That pair is what makes the scenario a logistics problem, and it comes before any vehicle-class detail.

ATV class is a mobility envelope: speed, width against the segment the platform is on, and whether it can leave the roadway. Each of those reads an edge attribute from the street graph, which is the dependency on the topology work above. `behavior.py` modes, `motion.py` tempo and `mechanics.py` finite munitions carry the rest.

The board's "TTP (Red dogs, provide baseline)" is the control requirement above, instantiated here: the Red TTP the delivery comparison is read against is the same fixed arm used for the formation and jamming comparisons.

## 3. Jamming (EME)

The first decision: does the ladder stay an abstract dial, or become a field over the map? A field is what lets a formation route around jamming, so it is worth it if and only if Blue moves relative to a jammer. With the street graph in place it does, which argues for the field.

The minimum honest emitter is position, effective radius, and a mapping from received power onto a ladder rung. Keeping C0-C5 as the interface matters: every result already measured is expressed in those rungs, so an emitter that maps onto them extends the existing record rather than restarting it.

Hold the Gilbert-Elliot calibration property through the change. `comms_ew.py` currently calibrates its two channels so their stationary drop rates match at every rung, which is what makes burstiness separable from mean loss. Whatever an emitter produces should preserve that, so paired comparisons survive.

Occlusion is the first-order urban effect and it arrives free with the `los()` work: a jammer a building blocks is a jammer that does not reach. That ordering is worth holding to, because multipath is the expensive half and occlusion carries most of the urban signal. Multipath is out of scope, named rather than gestured at.

## Standards

We will consider adopting the following standards. 

- **Symbology.** MIL-STD-2525D (US, 2014) and APP-6(D) (NATO, 2017), the latter promulgated under STANAG 2019, with MIL-STD-2525D as its base document. A display and interchange concern, so it attaches to HMI (O2) and to `replay`, not to the simulator core.
- **C2 to simulation.** C2SIM, SISO-STD-019-2020, with the Land Operations Extension SISO-STD-020-2020. It covers initialization, tasking and reporting, and explicitly covers robotic and autonomous systems, which is the sandtable case. Adopted as a NATO standardization agreement. Useful for sequencing: GMU's C4I center is a principal developer of C2SIM and Michael Hieb is already on the roster for HMI and multi-domain command, so this is the one standard where the expertise is in-house.
- **RF and spectrum.** VITA 49.2, the VITA Radio Transport extension. Its signal data packets carry digitized IF, baseband, broadband RF and spectral data, and 49.2 added command packets and a richer context set, making it two-way rather than the one-way transport 49.0 defined. This is the one that bears on item 3: adopting its field set constrains the emitter model to carry what a real receiver would report.
- **UCI.** The board pairs it with C2SIM on the A-to-B link. Identity and current revision not confirmed in this pass. Confirm before it enters a design.

