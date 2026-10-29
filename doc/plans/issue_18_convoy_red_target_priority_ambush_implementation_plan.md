# Implementation Plan: Convoy Red Target Priority and an Ambush Template (Issue #18)

**Issue**: [#18 Convoy: Red target priority and an ambush template](https://github.com/VadimSokolov/sandtable/issues/18) (part of #7, extends #12)
**Roadmap**: Phase 4: Autonomy, C2 & Force Protection
**Branch**: `issue-18-convoy-red-target-priority` -> `convoy-dev`
**Status**: Reviewable checkpoint, 2026-10-29. **#18 is not complete**: the lane-blocking rule and the Red halt cost (Change items 2 and 4) are deferred, the registration hash (item 5) and the prediction (item 6) are not done (section 4).
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
| C2 | Lane-blocking rule for a destroyed vehicle with `recovery_time` (needs the street graph) | **Deferred**: a new road-blockage subsystem; the issue lists it as a change, so it is a required item still open |
| C3 | Opt-in Red ambush template: roles, fire held until the head reaches a trigger, launch rule reacting to observed security vehicles, ordered withdrawal | **Implemented** as fire control |
| C4 | Red halt cost: indirect fire after a halt (120 to 900 s swept placeholder, no public source) and secondary devices against responders | **Deferred**: new combat mechanics on an unsourced placeholder; a required item still open |
| C5 | Register the Red set before any Blue variation; label each parameter sourced / bounded / placeholder; one hash across both arms; say "simulation-based analysis, not wargames" | **Partial**: labels done (section 5), non-varied inputs held fixed in the tool, wording used; **no registration hash**. It is a Change item, not an acceptance criterion |
| C6 | Prediction to test (control vehicle ranked first by mission-web criticality in the autonomous arm; flat in the manned arm) | **Not tested; blocked** on a criticality ranking that is not in the repository. Under Acceptance the issue says the arm-difference sign/size change is "not an acceptance test" and is reported either way; it is **not required for acceptance** but is **not reported either** |
| A1 | Off state byte-identical in the style of `test_counter_uas.py::test_off_is_byte_identical` | **Met** (`test_off_is_byte_identical`, `test_report_only_keeps_the_legacy_choice_and_stream`) |
| A2 | Negative control: Red head-on, nothing ahead of the head; on/off equivalent on Blue losses by `ar_gate.tost`, margin "0.06 of the contrast spread", at least 30 paired blocks | **Met under one reading of the margin only** (below) |
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
