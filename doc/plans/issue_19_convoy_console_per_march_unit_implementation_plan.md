# Implementation Plan: One Console per March Unit and the Attention Term in c2.py (Issue #19)

**Issue**: [#19 Convoy: one console per march unit and the attention term in c2.py](https://github.com/VadimSokolov/sandtable/issues/19) (part of #7, extends #14; depends on #8, #14). Opened Oct 20, 2026, label `enhancement`, no comments (checked 2026-10-29).
**Branch**: `issue-19-convoy-console-per-unit`, cut from `convoy-dev` at `6bd11f2` (includes #8, #9, #12, #14 and the #17 merge).
**Status**: Implemented 2026-10-29 and verified in a second pass (section 11); uncommitted, for review. #19 is **not complete** (section 11.6).
**UNRESOLVED MODEL ASSUMPTIONS (need approval; not decided by the evidence).**
1. *Console ownership after succession and absorption.* Assignments are fixed at build. After `promote` or `absorb` the followers keep asking their ORIGINAL console, even if it is dead; absorbed followers sit in a living unit but are unserved. No reassignment, no delay, no successor hosting.
2. *Quality of exempt vehicles.* Crewed vehicles and vehicles outside any unit keep `control_quality` 1.0, which is the best value on every consumer: they are not slowed, shoot at full probability and are harder targets than supervised vehicles.
3. *Exception routing is unit-tested but was never exercised in a mission experiment* (no track timeout occurred in any experiment run).
See `issue_19_decision_brief.md` for each question, the current behavior, a concrete alternative and the consequence.

**Dependencies**: #8 (march units), #14 (crew counts, autonomous arm), #17 (leader-loss policies, merged). **No dependence on #18.** Issue #18 is a separate branch (`issue-18-convoy-red-target-priority`, checkpoint `cbcfc4b`), not merged here, and nothing from it was merged, discarded or reused. Its manifest tooling is therefore not on this branch; `tools/make_console_arms.py` carries a small local stand-in (section 8).

---

## 1. The current model (verified in the code on `convoy-dev`)

- **Attention** (`c2.build_c2`, lines 378-383): `attention = min(1, span_capacity / n_span)` with `span_capacity` default 4 and
  `n_span = max(count of ALL Blue entities, 1)`, which includes UAS and the control vehicles. It is computed **once at build**
  (initialization only), `n_operators` is **ignored**, and it enters only as `q_operator_eff = q_auto + (q_operator - q_auto) * attention`.
  For a 15-vehicle convoy: attention 4/15 = 0.267, serviced quality 0.70 + 0.25 x 0.267 = 0.767 (the issue's number).
- **One operator**, or `n_operators > 1` consoles in a pool. In the pool a request goes to the earliest-free console (`argmin(crew_free_at)`):
  consoles are interchangeable service slots, not assigned to anyone.
- **Queues**: one global arrival stream. Reservation model (`queue_model="reserve"`): a request claims `start = max(free_at, arrival)`; the optional buffer model is a global FIFO.
- **Decisions are per vehicle**: every living Blue vehicle (ground and UAS) has a periodic decision event (`decision_interval`, jittered 0.5x-1.5x). `control_mode` is `direct` (request the operator over the link) or `supervisory` (decide locally at `q_auto`, no queue).
- **No notion of crew, march unit or host** in `c2.py` before this change. `operator_home` and a remote or TOC operator **do not exist** in the code (searched).
- **Behavior link**: `behavior.py` logs a LEADER_FOLLOW track timeout as an `intervention`, but nothing sent it to `c2`. `metrics._teaming_metrics` reads `fan_out` from `bhv.hold_steps`, which LEADER_FOLLOW never sets, so it is 0 for leader-follow runs.

### Terms (kept apart on purpose)

| Term | Meaning here |
|---|---|
| March unit | A group of vehicles under one head (`ent.march_unit`) |
| Console | One service station with its own queue (`crew_free_at[c]`), service rate and quality. One per march unit |
| Operator | The human at a console: the unit's commander on the control vehicle. Dedicated; not shared with another unit; not a separate entity |
| Service slot | A console serves one request at a time. A second slot would be a second console |
| Supervised agent | A living vehicle of the unit with **no assigned crew** (`ent.crew == 0`), other than the host |

## 2. Model contract (the decisions, with their basis)

| Question | Contract | Basis |
|---|---|---|
| Which vehicles does a console supervise? | The unit's crewless followers, assigned at build | Issue: "counting only vehicles without assigned crew" |
| Dedicated human or shared attention? | Dedicated: one commander, one console, one queue per unit; nothing is shared across units | Issue: "one console per march unit, tied to its control vehicle"; ATP 4-11 M-5 |
| Is the manned control vehicle a supervised agent? | No. Crewed vehicles (control, crewed escorts/recovery) and vehicles outside any unit (UAS) file no requests and keep the neutral quality 1.0 | Follows from "crewless only"; the neutral value for them is an **assumption** |
| Do escorts and recovery vehicles add workload? | Only if they have no crew (then they are supervised agents); crewed ones do not | Same rule |
| Attention depends on what? | `attention_basis="assigned"` (default): the agents assigned at build, as the issue states. `"living"`: the survivors now. Both are options | Issue says `n_assigned`; "living" is offered, not assumed |
| Capacity per operator or shared? | Per console. `span_capacity` is the capacity of one console. Adding a unit adds a console and does not change another's | Issue |
| Console ownership after promote / absorb / halt / continue | Fixed at build. A promoted successor does not host the console; an absorbed vehicle stays with its original console; `halt` and `continue` change movement only | **Assumption** (simplest; no re-assignment) |
| Console or host lost? | Service rate drops to zero. Its agents' requests are not worked, wait out patience, fall back to `q_fallback` (`abandon_console`). Their movement follows the #17 policy | Issue |
| Reassignment adds delay or workload? | There is no reassignment, so none | **Assumption**; an option for the Professor (section 9) |
| Exceptions | `exceptions: true`: a new intervention (track timeout) on a supervised agent files a request on that tick to its console, besides the periodic events | Issue: "route LEADER_FOLLOW exceptions ... to that console" |

**The attention equation is not replaced.** The existing form is kept and applied per console:
`attention_c = min(1, span_capacity / n_c)` (1 if `n_c = 0`), `q_c = q_auto + (q_operator - q_auto) * attention_c`.
Attention multiplies only the quality gain of a served decision; it never changes service time, latency or loss. **But `control_quality` is not only a decision-quality score: the same scalar also scales vehicle speed (x (0.35 + 0.65 q)) and, in engagement, the shooter's kill probability (x q) and the target's exposure (x (2 - q)).** A change in attention therefore reaches movement and combat as well as the served decision. Communications act only through latency, delivery and drops; queueing only through `crew_free_at[c]`. No cognitive model was introduced.

## 3. Configuration

```json
"control_mode": "direct", "autonomy_arm": "autonomous_march_unit",
"console_per_march_unit": {"attention_basis": "assigned", "exceptions": true},
"span_capacity": 4.0, "service_rate": 0.5, "q_operator": 0.95, "q_auto": 0.70, "decision_interval": 30
```

`console_per_march_unit` (absent, `null`, `false` or `"none"` = off, byte-identical) requires `control_mode: "direct"`, a convoy, **declared crew** (`autonomy_arm`, `crew` or `crew_metrics`), `n_operators` = 1, `queue_model` = `reserve`, `q_droop` = 0, a control vehicle in every unit, and `span_capacity > 0`. Anything else raises `ValueError`.

## 4. Metrics (units: steps; times times `dt` for seconds)

Per console `c2u_c<j>_*` (console j = j-th unit): `unit`, `assigned`, `supervised_mean`, `attention_mean`, `active_steps`, `lost_at`, `requests`, `exception_requests`, `serviced`, `abandon_link`, `abandon_queue`, `abandon_console`, `utilization`, `it`, `wt`, `nt`, `comms_up`, `comms_down`, `quality_mean`, `nt_margin`.
Pooled `c2u_*`: ratios of sums over the **active** consoles (alive with at least one living supervised agent) on each step, so lost and empty consoles do not dilute them. `c2u_requests = serviced + abandon_link + abandon_queue + abandon_console` (tested).
IT = mean service time; WT = mean queue wait (service start minus arrival); NT = mean time from a vehicle's last answer to its next request; `nt_margin = NT - (s - 1)(IT + WT)` with s the mean supervised count (the issue's condition NT >= (s - 1)(IT + WT) holds when it is >= 0). Utilization is a busy fraction of a server, **not measured cognitive workload**. `operator_utilization` (legacy key) uses the same pooled-active denominator in this mode. Cargo, losses and crew exposure are the existing metrics.

## 5. Acceptance criteria and status

| Criterion (issue wording) | Status |
|---|---|
| Parameter absent: byte-identical | **Met** (`test_off_is_byte_identical`; the full affected suite) |
| Four crewless followers per console: attention 1.0, decision quality = q_operator | **Met** (`test_four_crewless_followers_per_console_give_attention_one_and_q_operator`) |
| At the registered values, NT >= (s - 1)(IT + WT) on a constructed march unit | **Measurement implemented and tested; "registered values" undefined.** Tests show the condition holds at `decision_interval` 60 and fails at 4 (IT = 2 steps). The Crandall and Cummings numbers (IT 12-14 s, NT 21-55 s) quoted by the issue were **not verified** here. Awaiting the registered set (section 9) |
| Constructed unit, control vehicle destroyed at step k: 4 followers short under `halt`; none short under `continue` and `absorb` once the handoff passed | **Met**, with two units because the convoy validator requires at least two (`absorb` hands the followers to the second unit; with no receiver it would fall back to `continue`). No Red shooter; survive fraction 1.0 |
| Route LEADER_FOLLOW exceptions to the console; measure IT, NT, WT per unit | **Implemented and unit-tested** (exception file, per-console measures). **Not exercised by the experiment**: no track timeout occurred in the experiment runs |
| Compare with `operator_home: remote` and off-the-loop control from a TOC | **Not implemented**: neither exists in the code and the issue does not define them. Proposal in section 9 |

## 6. Tests (`tests/test_c2_units.py`, 36)

Feature off; validation; the existing attention term documented (all Blue entities, `n_operators` ignored); assignment and host; attention below / at / above capacity and both bases; attention changes quality only (service time, delay and loss unchanged); communications change delay but not attention or quality (no double application); request routing and isolation (a busy console does not delay another); a metamorphic test (2, 3 and 4 identical units give each existing unit identical results under a constant random source); console loss (service zero, others unaffected); assignments unchanged after promote and absorb; empty units and no operator left; exceptions; IT / WT / NT and the neglect condition both ways; metric accounting; the constructed-unit acceptance cases.
Stochastic mission outcomes are not required to improve with more consoles.

## 7. Source-to-assumption table

Labels: A mechanism, B mathematical model, C numerical calibration, D historical context only. Verified 2026-10-29 from the documents themselves unless stated.

| Claim | Source / year | Location | Supports | Does not support | Implication |
|---|---|---|---|---|---|
| Neglect time is the expected time a robot can be ignored before performance drops below a threshold; interaction time is the expected time a human must interact to bring it back; a human can manage several robots if neglect time exceeds interaction time | Crandall, Goodrich, Olsen, Nielsen, IEEE Trans. SMC-A 35(4), 438-449, 2005 (A, B) | Abstract and p. 438 | The mechanism behind NT, IT and a span limit | Any number for a convoy; wait time (not defined in this paper); a vehicle-to-operator ratio | Define IT and NT as measured quantities |
| Fan-out is one plus the ratio of neglect time to interaction time | same | p. 440 | The form `1 + NT/IT` already used in `metrics.fan_out` | The `NT >= (s - 1)(IT + WT)` inequality of the issue, which includes a wait time and is **not found** in this paper | The inequality is implemented as the issue specifies it, not as sourced |
| Robot autonomy is measured by neglect time; attention demand, free time and fan-out are measures of how much of a user's attention a robot takes | Goodrich and Olsen, "Metrics for Evaluating Human-Robot Interactions", 2003 (A) | Abstract page (the full text was not read) | Per-vehicle attention demand as a concept | Numeric human attention limits: **not found** | Attention stays the existing capacity term; no new coefficient |
| IT 12-14 s and NT 21-55 s in supervisory control | Crandall and Cummings 2007, cited by the issue (C) | **Not verified** (not among the documents read) | Nothing here | Everything: the numbers are quoted from the issue | "Registered values" must come from the Professor |
| Currently one leader to four unmanned followers, goal one to nine; lead crew of two now; operator workload not quantified; leader and followers electronically linked, method not given | "The Future is now at JRTC", Army Sustainment (Jul-Sep 2021), Johnson, Rothblatt, Overton, posted 11 Aug 2021 (program context, D) | Page text | The one-leader-to-four-followers span as program context | Workload, interventions, communications: **not found** | `span_capacity` 4 matches the program span; it is not derived from it |
| In the near term one control vehicle with a driver and the march unit commander provides command and control to four autonomous trucks; a march unit commander sets gap and speed through a tablet; in the future, units may be controlled externally with a human off-the-loop controlled from a tactical operations center | ATP 4-11, 16 March 2026, public release | Appendix M, para M-5, pp. 81-82 | The console-to-unit structure, the crewless-follower rule, and the existence of an off-the-loop TOC concept | A console service rate, a queue, an attention limit, a remote-operator model | Contract rows 1-3; the TOC comparator is a proposal only |
| Russian logistics: poor logistics hindered early operations | CRS R47068, Bowen, edition dated 14 Sep 2023 (D) | First 100,000 of 970,849 characters read | Context only | Convoys, unmanned trucks, operator ratios, human supervision: **not found** in the part read | None |
| Egyptian security forces in Sinai: attacks on convoys and checkpoints | Horton, CTC Sentinel 10(6), 2017 (D) | Read for #18 | Context only | Operator workload or ratios: **not found** | None |
| 1973 war and US-Israeli institutional cooperation | Orwin, Military Review, Jan-Feb 2020 (D) | Opening of the article (the rest was not read) | Context only | Operator ratios or convoy supervision: **not found** | None |
| Hybrid-war lessons from Lebanon and Gaza | RAND OP-285, Johnson, 2010 (D) | Landing page and abstract (the PDF text could not be extracted) | Context only | Operator ratios: **not found** | None |

Not inferred: console capacity from any organization's size; workload coefficients from communications failures; autonomous-convoy operator performance from other drone operations; attention limits from crew counts.
Labels in the model: **empirical** values: none. **Modeling assumptions**: crewed vehicles neutral at 1.0; fixed assignment; host death kills the console; no reassignment cost; exceptions add a request. **Sensitivity parameters**: `span_capacity`, `service_rate`, `q_operator`, `q_auto`, `decision_interval`, `patience`, the comms level.

## 8. Experiment (frozen before it ran)

`tools/make_console_arms.py`; manifest `doc/manifests/consoles.manifest.json` (`frozen_before_run`, configuration hash `dbc2385fba75...`, simulation and analysis source hashes recorded; the run checked both and found no drift). Before freezing, a single-seed smoke run of four arms was made to check the tool executed; its output set no definition. **Stand-in tooling**: the full manifest module is on the #18 branch and not here, so a small local equivalent (same canonical form; configuration hash separate from source hashes) is inside the tool.

Three families, 30 matched seeds each, paired against the family reference, 95% t intervals, Holm within (family, group, metric): **E1** units = 2, 3, 4, arrangement `legacy_single` (reference), `shared_crew` (`n_operators` = units), `per_unit`; **E2** `decision_interval` 15, 30 (reference), 60 at 3 units, per_unit; **E3** comms level C0 (reference) to C5 at 3 units, per_unit. Primary metrics: `delivered_frac`, `blue_losses`, `c2u_serviced_frac`, `operator_goodput`.

Confounds stated in advance: E1 changes convoy length (10, 15, 20 vehicles) and total personnel with the number of units, so it compares arrangements only within a size; `per_unit` also changes who files requests and the attention equation; attention equals 1.0 in every arm (four followers per console against a capacity of 4), so the attention term itself is not exercised by the experiment.

Results (42 of 104 comparisons have Holm p < 0.05; 18 are unavailable because `c2u_*` keys exist only for `per_unit`):
- **E1, delivery and losses**: no statistically clear difference between arrangements at any size (for example `per_unit` minus `legacy_single` on `delivered_frac`: -0.03, +0.01, +0.07 at 2, 3, 4 units; the last interval is [-0.003, +0.136], Holm 0.118). That is not evidence of equivalence.
- **E1, operator goodput**: `per_unit` serves a smaller share than `legacy_single` (-0.17, -0.15, -0.10, Holm < 0.001). An exploratory check afterwards (not registered, labelled so) found the unserved share equals the `abandon_console` share (0.18, 0.18, 0.14; no link or queue abandonment at C0): the dedicated consoles are lost with their control vehicles (about 1.8 to 2.1 consoles lost per run), whereas the legacy operator is not tied to any vehicle and cannot be destroyed. This is a structural consequence of the contract, not an attention effect, and it is the counter-intuitive result: dedicated consoles are more fragile.
- **E2**: no clear difference in delivery or serviced share for halving or doubling the request interval.
- **E3**: the serviced share falls monotonically with the comms level (C1 -0.15 to C5 -0.82, all Holm < 0.001), delivery is clearly lower from C3 (-0.18, Holm 0.006) and C4 and C5 (-0.22, Holm < 0.001), and Blue losses rise. This is mostly the existing ladder acting through dropped requests.
- **Exceptions**: zero exception requests occurred in these runs, so the routing is verified by unit tests only.

## 9. Open decisions for Professor Sokolov

Required (they change what the numbers mean):
1. **Registered values** for the neglect condition (NT >= (s - 1)(IT + WT)): which `service_rate`, `decision_interval` and `patience`, or the source of "12-14 s / 21-55 s"? The test only shows the condition can hold and fail.
2. **Host loss**: should a promoted crewed successor take over the console, and should reassignment cost delay or workload? Currently no.
3. **Crewed vehicles**: neutral quality 1.0 and no requests (current) or q_auto-style local decisions?
4. **Vehicles outside any unit** (UAS): neutral 1.0 (current) or supervised by something?
5. **Attention basis**: `assigned` (current default, as the issue states) or `living`?

Optional extensions (do not block acceptance):
6. **`operator_home: remote` and the TOC off-the-loop comparator.** Proposal, not built: a remote console is one pooled console off the vehicle (not destroyable by the convoy's losses) with extra one-way latency, serving all units' agents with its own attention `min(1, span_capacity / total agents)`; a TOC off-the-loop is the same with no per-request service and a longer exception latency. The latencies and the TOC service model are unspecified.
7. A supervisory-mode treatment of the console (exceptions only) is not built.
8. Per-console random substreams so a larger convoy never shifts another unit's draws.

## 10. Limitations

Constant sensitivity parameters, no calibration; crewed vehicles and UAS are outside the queue; the buffer queue model, `q_droop` and `n_operators > 1` are rejected in this mode; replay is not wired; one scenario (UC-3), 30 seeds; attention equals 1.0 in the experiment.

---

## 11. Verification pass (2026-10-29, uncommitted)

### 11.1 What "neutral quality" means (the audit)

Every consumer of `control_quality` in the code: `motion.step` (speed x (0.35 + 0.65 q)), `engagement._side_damage` and `belief.engage` (kill probability x q[shooter] x (2 - q[target])), and the replay display. **Sensing does not read it**
(tested). `behavior` reads `await_until` (a TELEOP hold), which exempt vehicles never set. Quality 1.0 is the **top** of every scale: relative to a vehicle served at `q_operator` (0.95) an exempt vehicle moves 3.4% faster (0.9675 vs 1.0), shoots at full
probability (x1.0 vs x0.95) and is the harder target ((2 - q) = 1.0 vs 1.05; against a vehicle at `q_auto`, 1.0 vs 1.30). So exempting crewed and out-of-unit vehicles removes the operator penalty entirely and is an **advantage over supervised vehicles**, not only
"no penalty"; it equals the no-C2 baseline, where every vehicle has quality 1.0. Tests: `test_exempt_vehicles_keep_quality_one_and_supervised_ones_do_not`, `test_quality_one_is_the_best_value_on_every_consumer_*`, `test_quality_does_not_enter_sensing`.
Nothing was changed; the choice is documented as a model assumption needing approval (question 3 in section 9). In the earlier experiment this also means the crewed control vehicles are not slowed or made easier to hit by the C2 layer, unlike in the legacy arm where they request like everyone else.

### 11.2 The attention term, exercised directly (two frozen designs)

`tools/make_attention_diagnostic.py` (manifest `attention`, hash `4c97a2a316c1...`, 300 s horizon) and its re-design `tools/make_attention_diagnostic_short.py` (manifest `attention_short`, hash `30c133d0c70c...`, 140 s horizon). Same vehicles, crew, route,
communications (C2: latency 2, drop 0.10) and request workload; combat disabled with `scenarios/uc3_convoy_no_threat.json` (the Red teams cannot fire), so no host is lost (checked: 0 hosts and 0 Blue vehicles lost in every run); only `span_capacity` varies (8, 4, 2, 1), so
attention is 1, 1, 0.5, 0.25. 30 matched seeds. A single-seed smoke run of one arm preceded the first freeze to check execution.

- **The equation holds exactly**: in every run attention equals min(1, span/4) and the served-decision quality equals q_auto + (q_operator - q_auto) x attention (maximum deviation 0 for attention, 5.6e-16 for quality): 1.0 -> 0.950, 0.5 -> 0.825, 0.25 -> 0.7625.
- **First design (300 s)**: attention and quality are exact, but waits and served share differ slightly between arms (for example wait +0.015 steps and served share -0.010 at span 1, intervals including zero). That was **not** the attention term. The convoy enters Blue weapon range of the Red teams after about 150 s, Blue-on-Red engagement draws begin, tempo depends on quality, and the shared random stream shifts. An exploratory check (not frozen) found the request counts, waits and served share bit-identical at 100 s and 140 s and different at 200 s and 300 s. This limitation is kept in the first tool's output.
- **Second design (140 s)**: chosen after seeing the first, so a corrected re-design and not an independent preregistration (its manifest was nevertheless frozen before it ran): wait and served share are **identical in every pair** across all four spans while attention and quality change as the equation says. Delivery is not meaningful in 140 s and is not claimed.
- Communications delay, queue wait, service time and served share are reported separately from attention and effective quality. This synthetic run **verifies that the implemented equation computes what it states; it does not validate a human cognitive-workload model**, says nothing about real workload or an empirical attention limit, and no monotonic delivery benefit is claimed.

**Chronology and shared-RNG coupling.** The first design (300 s) was frozen and run first. Its workload differed slightly between arms. The cause identified afterwards: all modules share one random stream, so once simulation paths diverge (here, tempo depends on quality, which changes when Blue engages Red) the draws each module receives shift, and matched seeds no longer give matched request streams. That explanation was checked only by an unfrozen exploratory comparison at 100, 140, 200 and 300 s. The second design (140 s) was chosen after seeing this, so it is a corrected re-design, not an independent preregistration. Its scope is narrow: one scenario and geometry, a horizon before any engagement, no mission outcome. It shows the equation without the coupling; it does not show the coupling is absent at longer horizons. Both designs and their chronology are kept. The same coupling applies to the other experiments (E1-E3 and the assignment diagnostic): once paths diverge, matched seeds no longer guarantee matched request streams, which may reduce the variance-reduction benefit of pairing. The reported paired intervals are computed correctly from the observed paired differences; there is no evidence that they are too narrow, and none is claimed.

### 11.3 Assignment effects separated from host survivability

`tools/make_assignment_diagnostic.py` (manifest `assignment`, hash `9789b4140dec...`). Equal host availability in every arm: the control vehicles are indestructible (hit points reset before each engagement step). **This is a diagnostic abstraction, not an implemented remote-operator or off-the-loop capability.** Red still kills other vehicles. The
original experiment (`tools/make_console_arms.py`, manifest `consoles`) is kept unchanged with its limitation: there, dedicated consoles died with their hosts and the single operator could not, so its goodput gap measured survivability.

Five arms at 3 units, comms C0, 30 seeds: `legacy_single`, `legacy_single_att1` (span 15, attention 1), `shared_crew` (3-console pool), `shared_crew_att1`, `per_unit`. Per_unit lost 0 consoles in every run. Results (paired, Holm within group and metric):
- **Dedicated against pooled, equal attention and host availability** (`per_unit` vs `shared_crew_att1`): goodput and delivery identical in every pair (+0.000); Blue losses +0.53 [-0.81, +1.88], no clear difference. This is an **observation in the tested setup** (3 units, C0, attention 1, indestructible hosts, 30 seeds, one scenario, goodput near saturation), **not a general equivalence** of dedicated and pooled arrangements; with load or loss near the limit the arrangements could differ.
- **Against one operator** (`per_unit` vs `legacy_single_att1`): goodput +0.021 [+0.020, +0.022] (Holm < 0.001), the same as `shared_crew_att1` vs `legacy_single_att1`, so the gain comes from the console count (queue capacity), not from the assignment. Delivery and losses show no clear difference.
- **Attention equation** (attention 1 against the legacy 0.267): Blue losses lower by 1.83 [-3.04, -0.63] (Holm 0.008) for the single operator and 1.07 [-2.25, +0.12] (Holm 0.076) for the pool, with no clear delivery difference. This follows from quality feeding tempo and exposure (11.1); it is not evidence about workload.
- Still confounded in the primary comparison: `per_unit` also stops the crewed control vehicles from asking, a difference from both legacy and pooled arms.

### 11.4 Ownership after host loss with #17 policies (explicit tests)

`test_followers_after_host_loss_keep_their_dead_console_under_promote_and_absorb` (three cases). Unit 0's host is destroyed:

| Policy | Followers' unit | Their leader | Console that receives their requests | Alive? | Behavior |
|---|---|---|---|---|---|
| promote, `succession=any` | still unit 0 | a crewless truck (vehicle 1) leads the rest | console 0 | no | requests unanswered; quality = `q_stall` while waiting, then `q_fallback` 0.5; they follow the promoted truck |
| promote, `manned_only` (the autonomous-arm default) | still unit 0 | none: no crewed survivor, so each drives alone | console 0 | no | same unanswered requests and fallback quality; independent waypoint driving |
| absorb | **unit 1** (march_unit rewritten) | unit 1's head | **console 0, not unit 1's** | no | requests unanswered although unit 1's console is alive; fallback quality; they follow unit 1's head |

Assignments are fixed: nothing is re-assigned and no reassignment delay is modelled. **This is a model assumption requiring approval.** The consequence worth the Professor's attention is the absorb row: absorbed followers are physically in a living unit but stay unserved. The alternative (re-assign on absorb or on promote of a crewed
successor, with or without a delay) is not built.

### 11.5 The neglect condition: definitions and handling

Units are **steps** (the scenarios use `dt` = 1 s, so steps are seconds; multiply by `dt` otherwise).
- **IT**: mean service time of serviced requests only (1 / `service_rate` when `service_cv` = 0).
- **WT**: mean queue wait of serviced requests only: service start minus arrival at the console. Waiting of requests that are never served is **censored** (not counted), so WT understates delay under overload.
- **NT**: for a vehicle, the time from the arrival of its last *answer* to its next request, averaged over those gaps. NT is estimated from **completed intervals only**. A gap still open at the end of the run is **censored and not counted** (not zero-filled); a gap spanning an *unserved* request closes at that request and the clock then stays off until the next answer. Dropped, abandoned and console-lost requests produce no IT, WT or NT-start sample. The censoring is potentially **informative** (the long gaps are the ones most likely to be open when a run ends, and runs end at different times), so the **direction and size of any bias are not established**; no bias direction is claimed.
- **s**: the mean number of living supervised agents over the steps in which the console was active (not the assigned count).
- `nt_margin = NT - (s - 1)(IT + WT)`, NaN if either side has no sample. It is computed from **averages** (per console, or pooled across consoles in the `c2u_*` aggregates). A non-negative margin of averages is **not proof that individual consoles, vehicles or moments satisfy the inequality**, and a pooled value does not show that each console does. The docstring of `c2_units.metrics` originally said a negative value means the unit asks "faster than the console can supply". It was corrected in a follow-up commit after `9d51766`: a negative margin is a violation of the configured inequality under the reported estimates, not proof that measured demand exceeds supply (11.10).
- **Source status**: Crandall et al. 2005 (p. 440) gives fan-out = 1 + NT/IT only. The wait-time inequality NT >= (s - 1)(IT + WT) is **the issue's specification, a model extension**; a source for it was **not found** in the documents read. The numbers (IT 12-14 s, NT 21-55 s) attributed to Crandall and Cummings 2007 are **not verified**, and no "registered values" were invented.
Tests: `test_neglect_clock_*`, `test_it_and_wt_come_from_serviced_requests_only`, `test_the_neglect_condition_holds_*`.

### 11.6 Acceptance and requirements review

| Item | Status |
|---|---|
| Change 1: one console per march unit, attention per console over crewless agents, host loss zeroes service and the policy takes over | **Implemented** |
| Change 2: route LEADER_FOLLOW exceptions to the console | **Implemented and unit-tested; untested in missions** (no exception occurred in any experiment run) |
| Change 2: measure interaction, neglect and wait time per march unit | **Implemented** (definitions in 11.5) |
| Change 3: compare against `operator_home: remote` and against off-the-loop control from a TOC | **Deferred and ambiguous.** Not implemented: neither exists in the code and neither is defined (latency, service model, attention). It is a Change item, **not an acceptance criterion**, so it is **not required to satisfy the listed acceptance criteria**, but the issue is incomplete without it. Proposal in section 9 |
| Acceptance 1: byte-identical when absent | **Met** |
| Acceptance 2: attention 1.0 and quality = q_operator with four crewless followers | **Met** (unit test; direct diagnostic) |
| Acceptance 3: NT >= (s - 1)(IT + WT) at the registered values on a constructed unit | **Ambiguous: the registered values are not given.** Measurement implemented and tested both ways; the condition is not verified at any registered set |
| Acceptance 4: control vehicle destroyed -> 4 followers short under `halt`; none under `continue` and `absorb` | **Met** (two units; the validator needs at least two) |
| "Why": default `service_rate` 0.5 is faster than the cited intervention times; `fan_out` is 0 for leader-follow | **Not addressed** (no default changed; legacy `fan_out` untouched). The new IT, NT, WT are the per-unit alternatives |

### 11.7 Provenance helper: scope and limitations

The experiments of this pass use `tools/local_manifest.py`; the first console experiment carries the same ideas inline. **Covers**: a configuration hash (canonical JSON of the registration, scenario files as parsed JSON), separate SHA-256 digests of `src/sandtable/**/*.py` and of the listed analysis files from the bytes on disk, git commit and branch, numpy and Python versions, and refusal to overwrite a frozen manifest. **Does not cover**: tests, docs, outputs, third-party code; it has no status validation, no verify command and no list of uncommitted files.
**Compatibility with #18's tooling** was tested one way only, read-only: the #18 `sandtable.manifest` module (extracted with `git show`, not added to this branch) computes the **same registration hash** for the consoles, assignment and attention registrations and its `verify_manifest` and `verify_source` accept all three manifests. That does not establish that #18's `freeze`, status checks or CLI would accept or produce equal manifests, and no such claim is made.

### 11.8 Open decisions (updated)

Added to section 9: (a) the neutral-quality advantage of exempt vehicles (11.1); (b) whether absorbed followers should be re-assigned to the receiving unit's console (11.4); (c) whether the remote and TOC comparators are needed before acceptance (11.6); and the unchanged questions about the registered values and about host succession.

### 11.9 Tests run

`tests/test_c2_units.py` now has 44 tests (+8). No source file was changed in the verification pass; the validation results are reused for the checkpoint. Affected suites (c2, queue, span, convoy, counter-UAS) and the broader run are reported in the delivery note; known baseline failure: `test_no_bare_dict_equality`, already on `convoy-dev`.

### 11.10 Follow-up correction after the checkpoint `9d51766`

- `src/sandtable/c2_units.py`: the `metrics` docstring is corrected (negative margin = violation of the configured inequality under the reported estimates; the key name is `c2u_c<j>_nt_margin`). Docstring only; no behavior changed.
- The shared-RNG wording is corrected (11.2): diverging paths mean matched seeds no longer guarantee matched request streams and may reduce the variance-reduction benefit of pairing; no claim that intervals are too narrow.
- **The frozen manifests are historical records and were not changed.** `doc/manifests/consoles`, `attention`, `attention_short` and `assignment` record the simulation-source digest of the code that ran them (the state at `9d51766`). Because `c2_units.py` changed, the current simulation source **no longer matches** those snapshots, and re-running any of those tools now fails its source check unless `--accept-source-drift` is passed (which records the drift). The old hashes were deliberately not updated.
