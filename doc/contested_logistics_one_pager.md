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

