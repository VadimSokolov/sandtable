# Decision brief for Professor Sokolov: Issue #19 (one console per march unit)

**State**: an incomplete, reviewable checkpoint. The mechanism is implemented and tested; five points below are assumptions or gaps that the evidence does not settle. Nothing was silently chosen: each question shows the
current behavior, one concrete alternative, and what it would change in how results are read.

## 1. Should C2 quality affect movement and combat together?

- **Current behavior**: one scalar, `control_quality`, scales vehicle speed (x (0.35 + 0.65 q)), the shooter's kill probability (x q) and the target's exposure (x (2 - q)). A served decision, a stall and a fallback all set the same scalar. So attention, comms loss and queueing reach movement and combat together.
- **Alternative**: separate switches or coefficients, for example `quality_effects: {"movement": true, "engagement": false}`, so a C2 impairment can be applied to tempo only, to engagement only, or to both.
- **Consequence**: today a Blue-loss difference between arms cannot be attributed to movement or to exposure. For example, raising attention from 0.267 to 1 lowered Blue losses by 1.83 in the assignment diagnostic through speed and exposure, not through "decisions". With separate switches the attribution is possible; the published single-scalar results would be a special case.

## 2. What quality should exempt vehicles retain?

- **Current behavior**: crewed vehicles (the control vehicles) and vehicles outside any march unit file no requests and keep quality 1.0, the best value on every scale. They are not slowed, shoot at full probability, and are harder targets than a supervised truck (exposure factor 1.0 against 1.05 at q_operator and 1.30 at q_auto). This equals a scenario without C2.
- **Alternative**: a stated quality for a crewed vehicle, for example `q_auto` (0.70) to mean "a human decides locally and imperfectly", or `q_operator` (0.95) to mean "as good as a served decision", set by a parameter such as `q_exempt`.
- **Consequence**: at 1.0 the C2 layer cannot hurt the control vehicle, so comparisons with the legacy single operator (where it requests like any vehicle) mix the topology change with a built-in advantage. A lower exempt quality would reduce that advantage and change the size, and possibly the sign, of the per-unit versus legacy differences.

## 3. Console ownership after succession and absorption

- **Current behavior**: assignments are fixed at build. After the host dies, `promote` (to a crewless truck, or nobody under `manned_only`) and `absorb` leave the followers owned by the dead console. Absorbed followers move into a living unit and follow its head, but their requests go to the dead console, not to the receiving unit's live one. They fall back to `q_fallback` after their patience. No reassignment delay.
- **Alternative**: (a) on `absorb`, re-assign the followers to the receiving unit's console, optionally after `reassign_steps`, which also raises that console's agent count and lowers its attention; (b) on `promote` to a crewed successor, let that vehicle host the console; (c) neither, as now.
- **Consequence**: today an absorbed follower is physically supported but unserved, which makes `absorb` look worse on C2 than it would under re-assignment, and it interacts with the #17 comparisons (the earlier `absorb` delivery advantage was measured without any console). Re-assignment adds workload to the receiving console, so it could also lower the quality it gives its own agents.

## 4. The intended NT, IT and WT definitions and the registered values

- **Current definitions** (steps; seconds at dt = 1): IT is the mean service time of served requests; WT is the mean queue wait of served requests (waiting of unserved requests is not counted); NT is the mean interval from a vehicle's last answer to its next request, from completed intervals only (open gaps are censored, the censoring may be informative, the direction of bias is not established); s is the mean living supervised agents over active steps. The condition NT >= (s - 1)(IT + WT) is the issue's wording; it is a model extension (the only verified source gives fan-out = 1 + NT/IT) and is computed from averages. A non-negative margin of averages does not show that every console or moment satisfies it.
- **Alternative**: define NT and WT with survival-style handling of open intervals and unserved waits (report a lower bound for WT and an interval for NT), compute the condition per console and per request cohort, and take the **registered values** (IT, NT, `service_rate`, `decision_interval`, `patience`) from a source you name.
- **Consequence**: with no registered set the acceptance item "NT >= (s - 1)(IT + WT) at the registered values" cannot be checked: the tests only show the condition can hold (interval 60) and fail (interval 4) at an IT of 2 steps, far below the 12 to 14 s the issue quotes (unverified here). A different definition of censoring could move NT in either direction.

## 5. The remote and off-the-loop comparators

- **Current behavior**: not implemented. `operator_home: remote` and a tactical-operations-center operator do not exist in the code, and the issue does not define them. They are a Change item, not a listed acceptance criterion. ATP 4-11 M-5 (pp. 81-82) says only that a future unit may be controlled externally by a human off the loop from a tactical operations center.
- **Alternative**: a remote console as one pooled console off the vehicles (not destroyable by convoy losses), with extra one-way latency L_r, serving all units' agents with attention min(1, span_capacity / total agents); an off-the-loop TOC as the same with no per-request service and a slower exception path (latency L_toc, rate r_toc). Every value would be a labelled placeholder, swept and not tuned.
- **Consequence**: without them the issue cannot be compared against the remote cases it names. With them, the comparison inherits the placeholders, and the equal-host-availability diagnostic (indestructible control vehicles) is the closest existing stand-in for a remote console's survivability only; it is not that capability. Whether they are needed before acceptance is your call.

## Required decisions and optional extensions

Required before the checkpoint can be called complete: 4 (registered values) and 5 (whether the comparators are required). Needed to interpret results: 1, 2 and 3. Everything else (the per-console random substreams, a supervisory-mode treatment of the console) is optional.
