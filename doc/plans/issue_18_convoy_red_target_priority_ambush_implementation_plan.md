# Implementation Plan: Convoy Red Target Priority and an Ambush Template (Issue #18)

**Issue**: [#18 Convoy: Red target priority and an ambush template](https://github.com/VadimSokolov/sandtable/issues/18) (part of #7, extends #12)
**Roadmap**: Phase 4: Autonomy, C2 & Force Protection
**Branch**: `issue-18-convoy-red-target-priority` -> `convoy-dev`
**Status**: Reviewable checkpoint (`8a2ad6a`) plus uncommitted follow-up and verification pass, 2026-10-29. **#18 is not complete**: the Red halt cost (item 4) is a proposal awaiting Professor Sokolov, the prediction (item 6) is untested, and the negative-control margin (A2) is pending clarification (section 4). Lane blocking (item 2) and the manifest and registration hash (item 5) are now implemented.
**Depends on**: #8 (roles), #12 (contact reaction), #14 (crew), #17 (leader-loss). Related, not started: #19.

---

## 1. Implementation contract (what the code did before this issue)

| Question | Answer, from the code on `convoy-dev` (`6bd11f2`) |
|---|---|
| Target selection | `engagement._side_damage`: each living shooter fires at its nearest eligible target (`argmin` of distance; ties to the lowest index). No priority term. |
| What Red knows | Only `ent.seen`, the per-tick detection from `sensing.step` (range gate, LOS, concealment, one Bernoulli draw per entity). Roles (`convoy_role`) are ground truth in `Entities`; nothing in engagement reads them. |
| Where eligibility is enforced | All in `_side_damage`: shooter alive and (with `mech`) has ammunition; target alive, opposing, `seen`, within `weapon_range`, ground domain, `world.los`. |
| Do wrecks block movement? | No. `behavior._predecessor` closes up on a lost vehicle, motion has no obstacle from dead entities, and the street graph is a route constraint. A destroyed vehicle does not stop the vehicles behind it. |
| Head and trail identity | Two readings exist. Physical: whoever is nearest to the objective. Organizational: `ent.leader == -1` and `ent.role == 0`, updated by `_update_convoy_succession` and by #17 (`promote`, `absorb`, `continue`). The policy exposes both. |
| Contact reaction (#12) | Reads `fired_at`, set from the target index the shooter selected. Priority changes who is targeted, so it changes who triggers `receive_fire`; the reaction itself is untouched. |
| Leader loss (#17) | Heads are found by `leader == -1`; priority on `ends` or `control` raises the chance a head dies and so the exposure to the #17 policy. |

## 2. What was implemented

1. **`target_priority`** (`src/sandtable/target_priority.py`, wired in `engagement.py`, `sim.py`). Ordered classes
   `ends`, `security`, `control`, `armed`, `armored`; first class with an eligible target wins, then nearest;
   fallback is the legacy nearest; ties go to the lowest index. Eligibility is computed first and never widened.
   `end_definition` (`position`|`identity`), `ends_basis` (`seen`|`column`), `applies_to` (Red platform types, so
   weapon types may differ), `armored_hp` (required with `armored`; the repository has no armor attribute and none
   is invented). Empty `order` is report-only. No RNG draws; the kill-draw count is unchanged.
2. **`ambush`** (`src/sandtable/ambush.py`). Red platform types get a role (`ambush`, `support`, `security`); listed
   types hold fire until a seen Blue vehicle reaches a trigger point; `security_rule` `let_pass`|`engage`; ordered
   withdrawal (`after_s` and/or `loss_fraction`, support later by `support_delay_s`, security stays). Fire is
   removed through a `hold_fire` mask in `engagement.step`. No RNG draws. Red does not move.
3. **Template scenario** `scenarios/uc3_convoy_ambush.json`: 15 Blue vehicles, 6 static Red teams 300 m off the
   route (abeam), three Red types that share the `at_team` numbers. Every Red parameter is a placeholder.
4. **Metrics** `tp_*` and `ambush_*` (see `doc/scenario.md`). `tp_vehicles_targeted` (distinct Blue vehicles aimed at)
   is kept separate from `blue_losses` (destroyed), and `tp_head_destroyed`/`tp_trail_destroyed` count end vehicles
   destroyed whatever the rule.
5. **Tests** `tests/test_convoy_red_priority.py` (50): controlled fixtures with a stub world and a rigged RNG.
6. **Comparison tool** `tools/make_red_priority_arms.py` (output `report/viz/red_priority_arms.json`, not committed).

## 3. Scope decisions: what the issue lists and this change leaves out

| Issue item | Decision | Why |
|---|---|---|
| 1 `target_priority` | Implemented | Required. The issue's order "column ends, armed, armored" is the default shape; `security` and `control` are added because the issue's own motivation (TC 3-162, the control vehicle) needs them. |
| 3 Ambush template with three roles, held fire, launch, ordered withdrawal | Implemented as fire control only | Required. "A launch rule reacts to observed security vehicles" is implemented as `security_rule`. |
| 2 Lane-blocking rule for a destroyed vehicle with `recovery_time` | **Not implemented** | It is a new road-blockage subsystem that needs the street graph and its own tests. Without it, destroying the first and last vehicle does not trap the column; this is documented as a limitation. Needs a decision (section 7). |
| 4 Red halt cost (indirect fire after a halt, secondary devices; 120-900 s) | **Not implemented** | New combat mechanics with a placeholder delay and no public source; adding them would make a priority policy look effective for reasons unrelated to targeting. |
| 5 Register the Red set before any Blue variation; one hash across arms | Partly (no hash) | Parameters are labelled below (sourced / bounded / placeholder) and the tool holds every non-varied input fixed. A registration hash is not implemented. |
| 6 Registered prediction (control vehicle ranked first by criticality) | **Not tested** | Needs a mission-web criticality ranking not in this repository. A first look at manned vs autonomous in these scenarios gave identical delivery and losses (same roles and behavior; only crew counts differ), so it was dropped as uninformative. |

## 4. Requirements and status (issue checked again 2026-10-29: no comments, only the `enhancement` label)

The issue has a **Change** section (six items) and an **Acceptance** section (off state, negative control, positive
control, and a registered prediction that the issue itself calls "not an acceptance test"). **#18 is NOT complete:**
three Change items are deferred or partial and one is untested.

| # | Requirement (issue wording, shortened) | Status |
|---|---|---|
| C1 | Deterministic `target_priority` in `engagement._side_damage`; ends, then armed, then armored; off by default, byte-identical when off | **Implemented** (adds `security`, `control`) |
| C2 | Lane-blocking rule for a destroyed vehicle with `recovery_time` (needs the street graph) | **Implemented (uncommitted)** as a minimal model with no bypass and no rerouting; the street graph is not consulted (contract below) |
| C3 | Opt-in Red ambush template: roles, fire held until the head reaches a trigger, launch rule reacting to observed security vehicles, ordered withdrawal | **Implemented** as fire control |
| C4 | Red halt cost: indirect fire after a halt (120 to 900 s swept placeholder, no public source) and secondary devices against responders | **Not implemented; proposal written** (`issue_18_red_halt_cost_proposal.md`). The issue gives the delay only; the effect (area, probability, duration, what a responder or a device is) is not specified, so building it would invent the result. Awaiting Professor Sokolov |
| C5 | Register the Red set before any Blue variation; label each parameter sourced / bounded / placeholder; one hash across both arms; say "simulation-based analysis, not wargames" | **Implemented (uncommitted)**: `src/sandtable/manifest.py`, `tools/manifest_cli.py`, `doc/manifests/`. The lane-blocking experiment's manifest was frozen before its first run; the target-priority sweep's manifest is `post_hoc` (created after its results were seen) and is not a preregistration. Labels in section 5 |
| C6 | Prediction to test (control vehicle ranked first by mission-web criticality in the autonomous arm; flat in the manned arm) | **Explicitly untested; blocked** until the mission-web criticality ranking is supplied or its definition is agreed. Target role and nearest-target rank are NOT substitutes and are not used. Under Acceptance the issue says the arm-difference sign/size change is "not an acceptance test" and is reported either way; it is **not required for acceptance** but is **not reported either** |
| A1 | Off state byte-identical in the style of `test_counter_uas.py::test_off_is_byte_identical` | **Met** (`test_off_is_byte_identical`, `test_report_only_keeps_the_legacy_choice_and_stream`) |
| A2 | Negative control: Red head-on, nothing ahead of the head; on/off equivalent on Blue losses by `ar_gate.tost`, margin "0.06 of the contrast spread", at least 30 paired blocks | **PENDING CLARIFICATION.** The margin is undefined in the issue. Three readings are preserved below with their provenance; one passes and two do not. The scenario, sample size and margin are not tuned to make it pass |
| A3 | Positive control: Red abeam, a priority on the ends changes which vehicles die | **Met** (below) |

### Negative control: margin, rationale, alpha, interval

- **Metric and setting**: Blue-loss fraction (`blue_losses / 15`), arm `ends` (position, seen basis) against the legacy rule,
  `scenarios/uc3_convoy.json` (Red on the route axis, no ambush), 40 paired seeds. The claim is limited to this.
- **Margin**: "0.06 of the contrast spread" is not defined in the issue. The primary margin is an absolute 0.06 of the loss
  fraction, `ar_gate.FULL_MPE`; `ar_gate.margin` itself says a bounded [0, 1] quantity already has a scale meaning at 0.06.
  It was fixed in the tool before any result was inspected.
- **Test**: `ar_gate.tost` at `t_min = 1.70`. Each one-sided test has alpha 0.0485 (40 pairs, 39 degrees of freedom), so this is
  the 90.3% two-sided interval lying inside plus or minus the margin.
- **Result**: mean paired difference -0.0017, standard error 0.0138, interval [-0.0251, +0.0218], TOST statistic 4.22 > 1.70:
  equivalent at margin 0.06.
- **Provenance of the three analyses**: (1) absolute 0.06 of the loss fraction, fixed in the tool before any result was inspected; (2) `ar_gate.margin`, 0.06 times the legacy level, and (3) 0.06 times the standard deviation of the paired contrast, both added after the results were seen (exploratory). None was chosen to produce a pass, and none is dropped.
- **Sensitivity (exploratory, added after the results were seen)**: with the margin `ar_gate.margin` would give for a
  non-rate metric, 0.06 times the legacy level (0.0245), the statistic is 1.65 < 1.70, **not equivalent** (narrowly); with 0.06
  times the standard deviation of the paired contrast (0.0052), it is 0.26, **not equivalent**. So the equivalence holds under
  the absolute reading of the margin and fails under the two stricter readings. The interval itself, [-0.025, +0.022] on a legacy loss
  fraction of 0.41, is what the data say. **Which margin the issue means is an open question for Professor Sokolov.**
- This is equivalence for one metric, one arm and one setting. It says nothing about delivery, crew exposure, or the abeam setting.

### Positive control

Red abeam (`scenarios/uc3_convoy_ambush.json`), `ends`: head destroyed +0.40 per run, trail destroyed +0.35 per run (paired
against legacy, Holm-adjusted p 0.006 and 0.023, 40 seeds), with no detectable change in Blue losses (+0.07, 95% interval
-0.06 to +0.21). Priority on the ends changes which vehicles are destroyed. "Head destroyed" is the physical column head
(position), which is the unit head only at the start of this layout.

### Deterministic trace: why control-first raises leaderless time

Unit heads are the control vehicles 0, 5 and 10 (indices); physical column order is 0, 1, 2, ... 14, so vehicle 0 is both the first
vehicle and a unit head, and `ends` aims at 0 and 14, while `control` aims at all three unit heads.
`test_control_first_trace_*` places one Red shooter beside the column (all kill draws succeed) and runs the leader-loss pass
before each shot, as `behavior.step` does. Leader-loss policy `continue`, `dt` = 1 s:

| Tick | Shot (control-first) | Head slots after the pass | `leaderless_steps` |
|---|---|---|---|
| 0 | vehicle 10 destroyed (control, unit 2 head) | [0, 5, 10] | 0 |
| 1 | vehicle 5 destroyed (control, unit 1 head) | [0, 5, -1]: unit 2 leaderless | 1 |
| 2 | vehicle 0 destroyed (control, unit 0 head) | [0, -1, -1] | 3 |
| 3 | vehicle 8 (no control left: fallback to nearest) | [-1, -1, -1] | 6 |
| 4 | vehicle 6 (fallback) | [-1, -1, -1] | 9 |

A loss is seen one tick after it happens, and under `continue` a unit never gets a head again, so each later tick adds one per
leaderless unit. The legacy nearest rule in the same fixture destroys vehicles 8, 6, 9, 7, 4 and no head, so the counter stays 0.
Under `promote` (latency 0) the same shots give successors 11, 6 and 1 and the counter stays 0. In the sweep this is the
mechanism behind the +372 to +444 unit-steps for control-first. Leaderless time is reported in **unit-steps**
(`leaderless_steps`); with `dt` = 1.0 s in these scenarios a unit-step is a unit-second, so +372 to +444 unit-steps is +372 to +444
unit-seconds, summed over the three units. That is the cumulative time units spent without a head, not time per unit.

### Metric definitions: unique vehicles vs events

`tp_shots`, `tp_priority_shots`, `tp_fallback_shots`, `tp_shots_<class>`, `tp_targeted_head` and `tp_targeted_trail` count
**targeting events** (one per Red shooter per tick). `tp_vehicles_targeted` counts **distinct Blue vehicles** aimed at at least once.
`blue_losses` counts vehicles destroyed. `test_unique_vehicles_targeted_is_not_the_number_of_targeting_events` shows three events
on one vehicle give `tp_vehicles_targeted` = 1.

### What the sweep does and does not show

No statistically clear difference in delivery or total Blue losses was detected for any policy in either tested setting, after
Holm adjustment. That is not evidence the policies are equivalent: the intervals are wide (for example a Blue-loss difference
of -0.90 with a 95% interval of -1.84 to +0.04 for control-first in the head-on setting), and only the one equivalence test above
was run, on one metric.

### Lane-blocking contract (Change item 2; `src/sandtable/lane_block.py`)

| Question | Answer in this model |
|---|---|
| What makes a wreck block a lane? | A Blue ground vehicle destroyed while `lane_blocking` is declared leaves a wreck at its position. It blocks the road at that point (along-track coordinate = arc length on the route if there is one, else distance along the line from the Blue start centroid to the objective). Red-side wrecks block nothing |
| Which vehicles are affected? | Living Blue ground vehicles behind the wreck; with `lane_width_m` given, only those within half a lane width laterally; with it null, the whole road width. Vehicles already past are unaffected. A vehicle waits `standoff_m` short of the wreck and never reverses. `wreck_roles` optionally limits which destroyed roles leave a wreck |
| When does it begin and end? | It begins the tick after the vehicle is destroyed and ends `recovery_time_s` seconds after that tick |
| What is `recovery_time_s`? | The time an unmodelled clearing or recovery effort needs to remove the wreck. One swept PLACEHOLDER constant, not derived from any recovery vehicle in the convoy |
| Bypass or rerouting? | **None.** The column waits the whole recovery time. The street graph is not consulted, so a column on a graph with an alternative street still waits. A bypass would need runtime replanning |

**Physical blockage is not a halt.** A contact halt (#12) and a leader-loss halt (#17) are decisions held in `behavior.holding`, counted by
`convoy_halt_steps` and `ll_halt_steps`, and ended by their own rules. A lane block is a constraint of the world: it moves a vehicle's target
back to the stand-off point and is counted by separate `lane_*` metrics. Releasing a halt does not clear a wreck and a cleared wreck does not release
a halt (tests `test_contact_halt_and_lane_block_are_separate_and_both_must_clear`, `test_leader_loss_policies_do_not_clear_or_ignore_the_wreck`).
Not wired into the replay path (`replay.py` calls `planning.step` without it). The street graph requirement in the issue is therefore met only in the sense
that the world's route (which may come from a graph) supplies the along-track coordinate.

### Manifest and registration hash (Change item 5)

`src/sandtable/manifest.py` hashes a canonical JSON of: schema version, name, the parsed scenario inputs, each arm's resolved configuration, the fixed parameters,
the seed list, the comparison definitions and the analysis settings. It does **not** hash results, timestamps, the status, notes, or the source revision, which is
recorded separately in `provenance` (commit, branch, uncommitted files). `tools/manifest_cli.py freeze|verify`; a frozen manifest is never overwritten;
`tools/make_lane_block_arms.py` refuses to run unless the frozen hash matches its definitions. Statuses: `frozen_before_run` (may be called a registration) and
`post_hoc` (documentation only; never a preregistration). `doc/manifests/lane_block.manifest.json` was frozen before the experiment ran;
`doc/manifests/red_priority.manifest.json` is `post_hoc` because that sweep ran first. The analysis code of a registered tool is not hashed: a crash in
the analysis code before any output (a missing key for arms without lane metrics) was fixed after freezing without changing a definition, and the hash still verified.

### Lane-blocking experiment (frozen before it ran)

`tools/make_lane_block_arms.py`, manifest `doc/manifests/lane_block.manifest.json` (status `frozen_before_run`, hash `6bc4a5602a00...`): the abeam ambush scenario, three Red
targeting rules by lane blocking off or at 60, 300 and 900 s recovery, 30 seeds, paired and Holm-adjusted. The first launch crashed on a missing key for the
"off" arms before producing any output; the analysis code was fixed and the hash re-verified unchanged. Observations (22 of 68 comparisons have Holm p < 0.05):

- Blocked-vehicle time rises with recovery time and is larger when control-first has destroyed unit heads (about +625, +2419 and +5470 vehicle-steps for legacy at 60, 300 and 900 s).
- **Delivered fraction was HIGHER with blocking** than without in several arms (for example +0.07 for legacy at 60 s and +0.18 for control-first at 60 s), and Blue
  losses were higher for control-first (+0.7 to +1.2). This is counter-intuitive and is not a finding about wrecks helping a convoy. A follow-up diagnostic tested one possible
  cause, the scripted withdrawal (section 9): it does not explain the delivery increase.
- Nothing here ranks policies. One road, one layout, placeholder recovery times, no bypass.

## 5. Parameter labels (issue item 5)

| Parameter | Label |
|---|---|
| Order of classes, `end_definition`, `ends_basis`, `security_rule` | design choices (explicit configuration) |
| Ambush roles and what they do | BOUNDED by TC 7-100.2 3-147/3-148/3-159 to 3-161 (structure only) |
| Withdrawal rule shape (ordered, security stays) | BOUNDED by TC 7-100.2 3-161 |
| Trigger point and radius, `after_s`, `loss_fraction`, `support_delay_s`, Red positions, Red numbers | PLACEHOLDER |
| `armored_hp` | PLACEHOLDER (no armor attribute exists) |
| Red hold-fire probability of detection, kill probability | unchanged from `at_team` (existing scenario values) |

## 6. Source-to-assumption table

Status: DOCTRINE (public-release doctrine), SECONDARY (analysis by a research organization or journal). No PROGRAM
or ACADEMIC (peer-reviewed) source was verified. Page numbers are the printed page numbers read from the publication.

| Claim | Source / year | Exact location | What it supports | What it does not establish | Model implication |
|---|---|---|---|---|---|
| The ambush force decides whether to execute; security elements position first; decision depends on the enemy force, its security and the estimated value of the target | TC 7-100.2, 9 Dec 2011, approved for public release (DOCTRINE) | para 3-147, p. 3-28 | Ambush fire is conditional, not automatic | Any probability or timing of the decision | `ambush` holds fire until a launch condition |
| Enemy security elements or advance guards are allowed to pass; when the head of the main force reaches a predetermined point, fire, demolitions or obstacles halt it; the whole ambush element opens fire; designated security elements engage the enemy's advance and rear security | TC 7-100.2 | para 3-148, p. 3-28 | The head of the main force is the trigger; Red security elements engage the convoy's security | Which vehicle each weapon fires at after the signal; any kill probability | `trigger` + `security_rule` (`let_pass`); security-role Red can be given their own priority with `applies_to` |
| Hunter-killer antiarmor teams prefer to trap vehicle columns in city streets, where destruction of the first and last vehicles will trap the column and allow its total destruction | TC 7-100.2, para 3-156, p. 3-31 (the same sentence is in 15-61, p. 15-12, for SPF direct action teams) | 3-156 and 15-61 | A stated preference of one OPFOR team type in urban streets | A general rule for all ambushes or terrain; that destroying two vehicles actually traps a column; any frequency | `ends` class, as an experimental policy. The "trap" effect is NOT modelled (wrecks do not block). The paragraph is about armored vehicles in city streets, not logistics convoys on open routes |
| Ambush and support elements are often combined; the security element provides early warning | TC 7-100.2, para 3-159, p. 3-33 (may begin on 3-32) | 3-159 | Role structure | Numbers per role | Three roles |
| While the ambush and support elements withdraw, the security element may remain to provide warning and delay | TC 7-100.2, para 3-161, p. 3-33 | 3-161 | Ordered withdrawal with security staying | Timing, routes, who covers whom | `withdraw`: ambush then support, security stays; withdrawn units do not move |
| Harassment ambushes can affect convoy activity; the convoy's security element may be selected as the specific target; repeated ambushes can draw disproportionately strong escorts | TC 7-100.2, para 3-162, p. 3-33 | 3-162 | Security vehicles as a deliberate target class | How often, or that it works | `security` class, labelled ground truth |
| Russian convoy problems in 2022 included traffic pileups and ambushes partly attributed to too few combined-arms units to protect advancing column flanks | CNA, Russian Military Logistics in the Ukraine War, 2023 (document dated September 2023; page lists 17 Oct 2023) (SECONDARY) | Section on the 2022 invasion, PDF page 45 (printed number not extracted); in text near footnote 161 | Columns on poor roads were ambushed; flank protection mattered | Any targeting order, vehicle priority, probability or geometry | None. Not used to set any parameter. Targeting priority: **not found** |
| Insurgent attacks on Egyptian security forces in Sinai include IEDs, mortar and RPG hit-and-run strikes, and convoys struck by IED or ambush | Horton, "Crossing the Canal", CTC Sentinel 10(6), June/July 2017 (SECONDARY) | Section "Wilayat Sinai Evolves" (unnumbered paragraphs); "Scorched Earth" mentions convoy ambush in passing | The setting is one of frequent attacks on convoys | Ambush tactics, targeting order, first/last vehicle, escort targeting: **not found** | None |
| The October 1973 war: logistics and maintenance shaped the Egyptian and Israeli approaches | Powell, AUSA, 19 Aug 2019 (SECONDARY). Only the abstract page was read; the full report was not | AUSA landing page | Maintenance and logistics as an operational factor | Convoy ambush targeting: **not found** (full text not read) | None |
| Hybrid-war lessons from Lebanon and Gaza (combined arms, precision fires, heavy forces) | Johnson, RAND OP-285, 17 Mar 2010 (SECONDARY). Landing page and abstract read; the PDF loaded in the browser but its text could not be extracted | RAND landing page | Context only | Any Hezbollah vehicle-targeting sequence: **not found** (full text not read) | None |
| Lane-blocking, Red halt cost and a Red target order for logistic vehicles | Issue #18 (Defense News Oct 2024; Raz et al. 2024; `doc/lit-ideas.md`) | not verified here | The issue's own motivation | These were not among the sources the work was asked to verify, and were not checked | The issue's claim that the control vehicle is "very easy to target" is **unverified** here |

The issue cites the doctrine paragraphs correctly (3-147, 3-148, 3-156, 3-162). The key limit: general discussions of
logistics vulnerability (CNA, CTC, AUSA, RAND) were NOT used to infer any targeting priority, probability, timing or geometry.

## 7. Unresolved, for Professor Sokolov

1. **Lane blocking.** Should a destroyed vehicle block a lane for `recovery_time`? It is the only way "trapping the column" can
   happen, and it needs the street graph and its own tests. Until then no priority policy can trap anything.
2. **Which end definition is intended**: physical position or organizational identity? Both exist; the default is position.
3. **Should `security` and `control` priorities be allowed?** They read ground truth Red may not have. The observable alternatives are
   `ends` (seen basis) and attribute classes.
4. **Red halt cost.** Is a placeholder 120-900 s sweep acceptable, or should it wait for a source?
5. **Registered prediction.** Where does the mission-web criticality ranking come from?
6. **Equivalence margin.** What does "0.06 of the contrast spread" mean? The negative control passes at an absolute 0.06 of the loss fraction and narrowly fails at `ar_gate.margin`'s 0.06 times the legacy level (section 4).
7. **Registration hash.** What should it hash (the Red parameter set, the scenario file, or both), and is it needed before the lane-blocking and halt-cost items exist?

## 8. Limitations

- Priority only reorders eligible targets. It adds no kill probability and no obstacle, so a policy cannot "trap" the column.
- Several classes read ground truth (labelled in config and docs). The `seen` basis for `ends` is observable.
- All Red parameters in the template are placeholders. One road, one convoy layout, one terrain, 40 seeds.
- Loss of leadership (#17), a behavioral halt (#12) and physical blockage are separate; only the first two exist.
- The sweep is exploration, not a ranking.

---

## 9. Verification pass (2026-10-29, uncommitted)

### 9.1 Lane-blocking audit (tests added only where coverage was missing)

- **No crossing in one large timestep**: with `dt` 1, 10 and 100 s, and across a route bend with `dt` 50 s, a vehicle behind an active wreck ends no nearer than the
  stand-off point (`test_a_vehicle_cannot_cross_*`); without the lane step the same vehicle runs 3.7 km past it, so the test discriminates. End to end at `dt` = 10 s no
  living vehicle behind the wreck passes the stand-off point while it is active. The reason is structural: the target is pulled back to the stand-off point and `motion.step` never moves a
  vehicle farther than its distance to the target.
- **Two wrecks**: clearing the nearer or the farther one does not release vehicles still blocked by the other (`test_clearing_one_wreck_*`, both orders).
- **Holds**: `update` and `apply` cannot read or write behavior state; a leader-loss halt and a contact reaction are unchanged before, during and after the wreck
  (`test_release_changes_no_behavior_hold`). The mission tests show the converse: a halt's release does not clear the wreck.
- **Lane width and roles**: signed lateral offsets 4.5 m inside / 5.5 m outside a 10 m lane on both sides; no `wreck_roles` filter means every destroyed role leaves a wreck; the filter is covered earlier.
- **Scope**: the model is route-only (or the straight line to the objective). `test_the_street_graph_is_never_read` fails if the street graph is touched. It is not traffic handling: no queueing,
  overtaking, lane choice, other streets or bypass. The module docstring and `doc/scenario.md` say so.

### 9.2 Mechanism diagnostic: the delivery increase and the scripted withdrawal

`tools/make_withdrawal_diagnostic.py`, manifest `doc/manifests/withdrawal.manifest.json` (`frozen_before_run`, configuration hash `f57026d47c80...`, source hashes recorded). Same abeam
scenario; the ambush withdrawal as scripted, and disabled (the `withdraw` key removed, everything else unchanged); lane blocking off, 60 s, 300 s; legacy and control-first targeting; 30 matched
seeds. The scripted withdrawal is timed from **ambush activation** (the launch tick, about tick 190), not from mission start (`ambush.step` measures from `launch_step`). One single-seed smoke run of one arm
was made before freezing only to check the tool executed. No parameter was changed after seeing results.

Timing (legacy, scripted, 60 s recovery, means): wreck first appears about tick 199, launch about 190, ambush and support withdraw about tick 300, blockage last released about 388, Red's last shot about 437,
head passes Red's position about 336 and the last vehicle about 404. **Red does not fall silent at the withdrawal**: the security-role team never withdraws, so Red's last shot (mean tick 349 to 473) comes after the mean withdrawal tick (about 300 to 305) in every scripted arm.

Results (paired by seed, delivered fraction, blocking minus off):

| Targeting | Recovery | Scripted withdrawal | Withdrawal disabled | Interaction (disabled - scripted) |
|---|---|---|---|---|
| legacy | 60 s | +0.067 [+0.028, +0.105] (Holm 0.006) | +0.050 [+0.006, +0.094] (Holm 0.062) | -0.017 [-0.064, +0.031] |
| legacy | 300 s | +0.067 [+0.011, +0.122] (Holm 0.062) | +0.006 [-0.052, +0.063] | -0.061 [-0.121, -0.001] (Holm 0.092) |
| control-first | 60 s | +0.178 [+0.101, +0.254] (Holm < 0.001) | +0.150 [+0.057, +0.243] (Holm 0.008) | -0.028 [-0.108, +0.052] |
| control-first | 300 s | +0.122 [+0.039, +0.205] (Holm 0.011) | +0.072 [-0.043, +0.187] | -0.050 [-0.135, +0.035] |

Also (legacy targeting): with the withdrawal disabled, blocking raised Blue losses (+0.83 at 60 s, +1.37 at 300 s with Holm 0.057) and lowered success at 300 s (-0.13; interaction -0.17, Holm 0.045, the only
interaction below 0.05 among the 36 comparisons); with it scripted, the legacy effects on losses and success are smaller and their intervals include zero. For control-first, blocking raised Blue losses with the
withdrawal scripted (+0.67 at 60 s, +1.10 at 300 s; Holm 0.031 and 0.023) as well as disabled (+1.37 at 300 s, Holm 0.031). 8 of the 36 comparisons have Holm p < 0.05 (three delivered-fraction block effects for
control-first, one for legacy, three Blue-loss block effects for control-first, and the one interaction).

### 9.3 Provenance

- **Configuration hash** (what is run) and **source hashes** (which code ran it) are separate. `manifest.source_hashes` records SHA-256 digests of `src/sandtable/**/*.py` (simulation) and the tool's
  `ANALYSIS_FILES` (analysis), from the bytes on disk, so uncommitted content counts. Scope: not covered are tests, docs, scenario files (they are in the configuration), generated outputs and third-party code
  (only numpy, scipy and Python versions are recorded). The run tool verifies configuration and source before executing, refuses on any mismatch unless `--accept-source-drift` (then recorded), and writes both source-hash sets and the
  check into the results. The withdrawal run's check was `ok`, no drift.
- **The original `lane_block` manifest is kept unchanged.** It hashes configuration only and has no source hashes. Its configuration stayed fixed while the analysis code was repaired after a crash
  (a missing key for arms without lane metrics, before any output). Nothing about its code can be verified, and it is not claimed to have stronger preregistration than that: configuration frozen before the run, analysis code not frozen.
  Since then the simulation also gained timing metrics (`lane_last_release_step`, `tp_first_shot_step`, `tp_last_shot_step`); these add keys only when the feature is declared.
- The `red_priority` manifest remains `post_hoc`.

### 9.4 Supported conclusions

- Lane blocking holds the column: blocked vehicle-time rises with recovery time, the last vehicle passes Red later, and no vehicle crosses an active wreck in these tests, in the tested settings.
- Priority and the ambush template behave as specified in controlled fixtures; priority changes which vehicles are destroyed when Red is abeam (head and trail), with no detectable change in total Blue losses.
- The withdrawal is not the main cause of the delivery increase: it persists at 60 s with the withdrawal disabled (+0.05 legacy, +0.15 control-first).
- A withdrawal-by-blocking interaction is suggested for success at 300 s (one of 36 comparisons below 0.05 after adjustment); it is not established.

### 9.5 Unexplained observations

- Why delivered fraction is higher with blocking than without. Not the scripted withdrawal alone. Untested candidates: how blocking changes the tick the mission ends (delivery is read at termination), the security-role Red team that never withdraws, and
  the wreck stopping vehicles at a position that changes their exposure. None was tested.
- Why Blue losses rise with blocking mainly for control-first and when no withdrawal exists.
- Why the lane-block experiment's `success` falls at 900 s recovery while delivered fraction stays above the no-block level.

### 9.6 Simplifications (all deliberate)

Route-only blocking; no bypass, rerouting, queueing or overtaking; one swept recovery constant not tied to recovery vehicles; a wreck blocks the whole road unless `lane_width_m` is given; Red does not move
and a withdrawn unit stays on the map; the security-role team never withdraws; the passage ticks in the diagnostic compare the Blue vehicles' x with the initial Red mean x; recovery times 60 and 300 s and the 20 m stand-off are placeholders;
30 seeds, one road and layout.

### 9.7 Awaiting Professor Sokolov

1. The negative-control margin (A2): what is "0.06 of the contrast spread"?
2. The Red halt cost (C4): the proposal and its seven open questions (`issue_18_red_halt_cost_proposal.md`). Not to be implemented until the mechanism is resolved.
3. The criticality ranking for the registered prediction (C6), or its definition. Role and nearest-target rank are not substitutes.
4. Whether lane blocking must reroute over the street graph, or the route-only model is acceptable.
5. Whether a security-role team that never withdraws is the intended reading of TC 7-100.2 3-161 ("may remain to provide warning and to delay").
6. Whether the scripted withdrawal should be timed from activation (as now) or from mission start.
