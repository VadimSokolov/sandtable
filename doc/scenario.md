# SandTable Scenario Relevance to GVSC: Research Findings

**Classification:** UNCLASSIFIED (open-source web and literature only)
**Prepared:** 2026-08-12
**Author:** Vadim Sokolov (compiled with assistant-run independent web/literature research)
**Purpose:** Confirm whether SandTable's two headline variables (the C0-C5 communications/EW
degradation ladder and direct-vs-supervisory control modality) are the variables the U.S. Army
DEVCOM Ground Vehicle Systems Center (GVSC) actually cares about, and identify which mission
scenarios are of highest GVSC relevance. Feeds the Section 11.2 prioritization discussion with Joe
Bricio and Ali Raz, the RT3 sweeps, and the Year-1 demonstration (D1).

**Method:** three independent automated web/literature sweeps (GVSC programs and scenarios;
control-modality validation; contested-comms/EW plus other-variable discovery), prioritizing
UNCLASSIFIED primary sources (CRS, FM 3-0, DEVCOM ARL/GVSC, RAND, GVSETS) and corroborating
defense press. URLs and dates gathered via automated search on the date above; spot-check each URL
before using it in a formal deliverable.

---

## 1. Questions

1. Are C0-C5 (contested comms / EW degradation) and control modality (direct/teleoperation vs
   supervisory autonomy) the correct primary variables for GVSC?
2. Which mission scenarios are of highest relevance to GVSC, and how do they map to what SandTable
   already implements?

## 2. Executive verdict

- **Both variables are confirmed as first-order GVSC/Army concerns (HIGH evidence), and the
  literature explicitly couples them.** Autonomy is framed as the answer to the communications
  problem, which is exactly SandTable's centerpiece interaction (as comms degrade, the optimum
  shifts toward on-platform autonomy). The centerpiece is well-founded and GVSC-credible.
- **They are a defensible core, not a complete set.** The single most important variable GVSC
  emphasizes that SandTable does not vary is **terrain / off-road autonomy difficulty** (measured by
  human intervention rate). Secondary gaps: **GPS/PNT denial** (distinct from link jamming) and
  **trust/transparency** (GVSC's declared #1 priority area, Human-Machine Integration).
- **Scenario priorities:** the MUM-T span-of-control centerpiece and counter-UAS are strongly
  validated and already partly built; **breaching is the mission GVSC most clearly owns** and should
  be elevated; **leader-follower logistics convoy** is a fielded GVSC thread with no SandTable
  scenario yet.
- **Framing caveat:** the RCV platform program is volatile (halted, renamed, paused across
  2025-2026). Anchor on enduring mission threads and operating conditions and the Human-Machine
  Integrated Formations (HMIF) concept, not on a specific platform name.

## 3. Variable validation

### 3.1 Control modality (direct/teleop vs supervisory autonomy): CONFIRMED, headline-worthy

The teleoperation-to-supervised-autonomy shift is arguably *the* pacing problem for the Army's
flagship UGV effort. Load-bearing evidence:

- **CRS (primary):** the Army hopes AI/navigation will "eventually permit a single operator to
  control multiple RCVs or for RCVs to operate in a more autonomous mode"; today off-road autonomy
  needs "a lot of intervention where the soldier has to step in."
- **DEVCOM ARL Human-Autonomy Teaming ERP (primary):** built for NGCV, targeting "reduced
  Soldier-System ratios" and crew reduction.
- **ARL (Jessie Chen):** the shift is that "the human becomes a supervisor rather than an operator."
- **Real anchor (defense press):** at Fort Irwin, 5 soldiers teleoperated 2 RCVs (worse than 1:1);
  radio standoff roughly 1,000-2,000 m open and about 500 m in trees; latency over ~250 ms causes
  overcorrection; EW can sever the link. This is exactly the operator-burden and comms-entanglement
  the span-of-control axis models.

### 3.2 Contested comms / EW (the C0-C5 ladder): CONFIRMED, first-order

- **FM 3-0 Operations (2022):** dedicated section, "Command and Control During Degraded or Denied
  Communications"; adversaries "have demonstrated the ability to contest communications in the
  electromagnetic spectrum and degrade friendly C2."
- **Current requirement:** a June 2026 Army RFI names "Denied, Degraded, Intermittent, and Limited
  (DDIL)" communications verbatim.
- **DEVCOM ARL SARA program (primary):** frames the core autonomy condition as operating "without
  the ability to communicate and for which there are no maps."
- **Ukraine-informed:** RF jamming reportedly downed on the order of thousands of drones per month
  (RUSI-lineage reporting); the fielded responses (fiber tether, onboard autonomy) are the two
  mechanisms directly relevant to ground autonomy. Treat exact figures as "consistent with," not
  precisely validated.

### 3.3 The coupling: why the centerpiece is well-founded

The two variables are not just individually relevant; their interaction is what the Army cares
about. DARPA's RACER program manager states autonomy "is part of the solution to the comms problem"
and to span-of-control and bandwidth. That is precisely SandTable's IV-A x IV-B centerpiece: the
direct-to-supervisory optimum shifts toward autonomy as the link degrades.

### 3.4 Gaps: variables GVSC cares about that SandTable does not vary

Ranked by GVSC relevance:

1. **Terrain / environment-perception complexity (off-road vs urban, unmapped).** Repeatedly called
   THE autonomy bottleneck ("industry is nowhere near off-road autonomy"), measured by human
   intervention rate. SandTable has terrain (UC-3 cover/defilade) but models it as a route/cover
   tradeoff, not as autonomy difficulty that forces takeovers. This is the most important missing
   axis. Co-primary with comms for ground autonomy.
2. **GPS/PNT denial, distinct from link jamming.** A separate adversary action with its own materiel
   line (Assured PNT / MAPS). At minimum fold explicitly into the C0-C5 ladder; better as its own
   factor.
3. **Trust/reliance (over- and under-trust) and automation transparency.** GVSC's self-declared #1
   priority effort is Human-Machine Integration; RAND's 2025 "One Team, One Fight" makes trust the
   headline HMI risk. This is the Objective-1/Objective-2 gap already noted for SandTable.

Also relevant, lower priority: operator workload and span-of-control (cross number-of-vehicles with
modality, which the centerpiece already does); threat type and survivability (counter-UAS/drones,
ATGM, mines/IEDs); degraded visual environment and sensor degradation (dust, smoke, night).

### 3.5 Refinements to how the two current variables are modeled

- **Modality is binary; GVSC/ARL think in graded levels of autonomy.** Cite and optionally implement
  a graded or dynamically-switching level (LORA / ALFUS), not just two levels.
- **Keep span-of-control as its own factor crossed with modality** (SandTable already does this).
- **Add intervention / takeover rate as a metric**, since that is how the Army measures autonomy
  maturity.
- **Do not assume supervisory autonomy "just works."** Current off-road autonomy is immature, so the
  realistic near-term contrast is teleop vs assisted/waypoint autonomy with frequent takeover.
- **Fold PNT denial into or alongside the EW ladder** so a distinct EW mechanism is represented.

## 4. GVSC mission-scenario priorities and SandTable mapping

### 4.1 Ranked mission threads

| Rank | GVSC mission thread | GVSC pull | SandTable status |
|---|---|---|---|
| 1 | Reconnaissance / scout and security (screen, guard, overwatch) | Canonical RCV role | Partial (UC-5 recon; centerpiece is scout-like) |
| 2 | MUM-T robotic wingman, one operator to many | Explicit Army goal | Have (span-of-control centerpiece) |
| 3 | Direct-fire / lethality ("no blood for first contact") | Core RCV concept | Gap (UC-4 touches fires/authority) |
| 4 | Obstacle / minefield breaching (RCBC) | GVSC-owned (lead systems integrator) | Gap (maps to TDD UC-8) |
| 5 | Logistics resupply / leader-follower convoy (S-MET, ELF) | Fielded thread | Gap (new mission type) |
| 6 | Counter-UAS / formation air defense | Rising fast, Ukraine-driven | Have mechanics (M2 counter-UAS; TDD UC-4) |
| 7 | Route clearance / counter-mine / C-IED / EOD | Core RAS strategy | Gap |
| 8 | Electronic-warfare payload on expendable robots | Emerging | Gap |
| 9 | CBRN reconnaissance | Secondary (more PEO-CBRN) | Gap |
| 10 | CASEVAC / equipment recovery | Emerging, lowest confidence | Gap |

Baseline autonomy behaviors from the current Army RFI, useful as testbed modes: **teleoperation,
waypoint navigation, leader-follower, sentry.**

### 4.2 What the research changes about our priorities

- **Breaching (UC-8) should move up.** Previously filed as a trust-heavy, expensive scenario. But
  breaching is the mission GVSC most clearly owns (Robotic Complex Breach Concept, GVSC is lead
  systems integrator), so a breach scenario has strong GVSC pull as a mission thread, independent of
  the trust-veridicality build. A maneuver/breach version is worth doing before the full
  Objective-1/2 layer.
- **Counter-UAS (UC-4) is doubly justified:** a fast-rising GVSC concern and SandTable already has
  the M2 counter-UAS mechanic. Cheapest high-value add.
- **Leader-follower / logistics convoy is a fielded GVSC thread with no SandTable scenario.** A
  convoy-following-a-route-under-degraded-comms scenario would be new but relatively cheap on the
  existing motion/planning/comms stack (Expedient Leader-Follower, S-MET).
- **Scout/security (rank 1) is under-represented;** UC-5 is the closest. A dedicated scout/screen
  scenario would strengthen coverage of GVSC's single most canonical role.

Current SandTable scenarios for reference: UC-3 (route vs defilade), UC-5 (sensor swarm under EW),
the span-of-control by comms centerpiece (IV-A x IV-B), and UC-7-like (contested belief). Proposed
near-term additions: UC-4 (counter-air / engage-without-approval) and UC-2 (out-of-distribution
novel threat).

## 5. Credibility caveat: anchor on threads and conditions, not the platform

The RCV program churned across 2025-2026: single common chassis (2023-24), halted (May 2025),
restarted as a cheaper commercial "UGCRV" (Aug 2025), XM30/OMFV Milestone B paused (Feb 2026),
autonomy software efforts streamlined (Dec 2025). The mission threads and operating conditions
(DDIL comms, off-road autonomy) persist and have intensified under the Human-Machine Integrated
Formations (HMIF) concept and MARS (one soldier controlling multiple autonomous vehicles at range).
Cite the enduring concepts and conditions, not the volatile platform name, to avoid a dated claim.
This is the same discipline as the "consistent with" framing for Ukraine figures.

## 6. Recommendations

For the Joe and Ali discussion, the RT3 sweeps, and D1:

1. Keep the modality x comms x span centerpiece: it is the validated, GVSC-credible core, and its
   interaction is what the Army says matters.
2. Add a third axis to be GVSC-credible: terrain / environment complexity (off-road vs urban) with
   an intervention/takeover metric, and treat GPS/PNT denial explicitly.
3. Prioritize scenarios by GVSC mission-thread pull: scout/security + MUM-T (have) -> counter-UAS /
   UC-4 (have mechanics) -> breach / UC-8 (GVSC-owned, elevate) -> leader-follower convoy (new,
   fielded thread) -> OOD / UC-2.
4. Decide explicitly whether SandTable takes on the trust/transparency (Objective-1/2) space that
   GVSC prioritizes #1, or stays on mission-effectiveness (Objective-3/4) and says so.

## 7. References

Credibility: HIGH = primary government or peer-reviewed; MED = attributed defense press
corroborated by primary sources.

1. CRS IF11876, *The Army's Robotic Combat Vehicle (RCV) Program*, A. Feickert, updated 2025-05-20.
   Single-operator-to-multiple-RCVs goal; off-road autonomy immature; program halt. HIGH.
   https://crsreports.congress.gov/product/pdf/IF/IF11876
2. CRS IF12094, *XM-30 (formerly OMFV)*, updated 2026-04-22. Optionally-manned control node for
   robotic wingmen. HIGH. https://www.congress.gov/crs-product/IF12094
3. U.S. Army, *FM 3-0 Operations* (2022), Ch. 8, "Command and Control During Degraded or Denied
   Communications." HIGH.
4. DEVCOM ARL, *Human-Autonomy Teaming (HAT)* Essential Research Program. Reduced Soldier-System
   ratios; crew reduction; NGCV linkage. HIGH. https://arl.devcom.army.mil/what-we-do/hat/
5. DEVCOM ARL, *Scalable Adaptive Resilient Autonomy (SARA)* CRA overview. Comms-denied and unmapped
   terrain as core autonomy conditions. HIGH. https://arl.devcom.army.mil/cras/sara-cra/sara-overview/
6. Army.mil (J. Chen), *Human-autonomy teaming helps Army design trustworthy AI*, 2020-10-29.
   "Supervisor rather than operator." HIGH. https://www.army.mil/article/240350/
7. Breaking Defense, *Army looks to limit early RCV missions to keep soldiers out of harm's way*,
   A. Roque, 2024-07-23. 5 soldiers to 2 RCVs teleop; tether standoff; ~250 ms latency; EW severs
   link. MED. https://breakingdefense.com/2024/07/army-looks-to-limit-early-robotic-combat-vehicle-missions-to-keep-soldiers-out-of-harms-way/
8. DefenseScoop, *Army looking toward autonomous robots to recover its downed vehicles*, 2026-06-22.
   DDIL comms named verbatim in the RFI. MED. https://defensescoop.com/2026/06/22/army-autonomous-vehicle-recover-equipment-from-combat-zones/
9. RAND RR-A2764-1, Wong et al., *One Team, One Fight, Vol. I: Insights on Human-Machine Integration
   for the U.S. Army*, 2025-06-02. Trust as headline HMI risk. HIGH.
   https://www.rand.org/pubs/research_reports/RRA2764-1.html
10. RAND RR-A423-1, Tarraf et al., *An Experiment in Tactical Wargaming with Platforms Enabled by
    AI*, 2020. Remotely-operated vs autonomous vs manned RCVs. HIGH.
    https://www.rand.org/content/dam/rand/pubs/research_reports/RRA400/RRA423-1/RAND_RRA423-1.pdf
11. Road to Autonomy, *DARPA RACER program* interview (PM S. Young). Autonomy as answer to comms and
    span-of-control; off-road, no maps/GPS; interventions metric. MED.
    https://www.roadtoautonomy.com/transcript-darpa-racer-program/
12. Beer, Fitzgerald & Rogers (2014), *Toward a Framework for Levels of Robot Autonomy (LORA) in
    Human-Robot Interaction*, J. Human-Robot Interaction 3(2). Best framework to cite for a UGV
    "control modality" variable. HIGH.
13. Parasuraman, Sheridan & Wickens (2000), *A Model for Types and Levels of Human Interaction with
    Automation*, IEEE Trans. SMC-A 30(3):286-297. Foundational stages-by-levels framework. HIGH.
14. NIST, *Autonomy Levels for Unmanned Systems (ALFUS)*, Huang et al. US-government standard;
    "Human Independence" axis maps to control modality. HIGH.
    https://www.nist.gov/el/intelligent-systems-division-73500/cognition-and-collaboration-systems/autonomy-levels-unmanned
15. Chen & Barnes (2012), *Supervisory Control of Multiple Robots: Effects of Imperfect Automation
    and Individual Differences*, Human Factors. ARL span-of-control, reliability, trust. HIGH.
16. GVSETS 2019, Cymerman et al., *Evolving the Robotic Technology Kernel*. RTK, WMI operator UI,
    ANVEL simulation, RAS/RCBC. HIGH.
17. Modern War Institute, *Networked for War: Lessons from Ukraine's Ground Robots*, 2025-26. Drones
    destroy most UGVs; UGV as networked node; EW integration. MED. https://mwi.westpoint.edu/networked-for-war-lessons-from-ukraines-ground-robots/
18. Army.mil, *Army advances human-machine integration tests*, 2024-10-29. HIGH.
    https://www.army.mil/article/280910/
19. DEVCOM GVSC home page, Priority Efforts (Human-Machine Integration listed #1;
    "fail early and cheaply" digital-testing philosophy). HIGH. https://gvsc.devcom.army.mil/

Full sourced sweeps are retained in the scratchpad:
`gvsc_scenarios_findings.md`, `modality_variable_findings.md`, `comms_ew_and_other_variables_findings.md`.

## 8. Confidence and limitations

- **HIGH:** both current variables (comms/EW degradation and control modality) are correct and
  central, and their interaction is the right centerpiece.
- **HIGH:** terrain / off-road autonomy complexity is a co-equal variable currently missing.
- **MEDIUM-HIGH:** trust/transparency and span-of-control as GVSC priorities (they partly couple
  with control modality).
- **Caveats:** no public consolidated GVSC use-case library exists in the UNCLASSIFIED space (the
  TDD Section 11 library plus these mission threads are the best available proxies; a formal internal
  set likely exists but is distribution-restricted). Program and platform names are volatile.
  Ukraine quantitative figures should remain "consistent with," not precisely validated. URLs were
  gathered via automated search and should be spot-checked before formal citation. One access
  limitation: the RAND RR-A2764-1 full PDF returned an access error and was captured via its landing
  page and corroborating coverage. No classified or non-public information was used.

## Convoy security vehicles and contact reaction (Issue #12)

Both are opt-in under the `convoy` spec (or as flat params); absent, runs are byte-identical.

- `security_ptype`: platform type name. `ROLE_SECURITY` vehicles take `weapon_range`, `pk_base`,
  `sensor_range`, `max_speed`, `turn_rate` and `hp` from it. The count follows `security_ratio`
  (`round(ratio * (march_unit_size - 2))` per march unit, Python half-to-even) at the positions the
  `roles` list or the #15 allocation gives.
- `contact_reaction`: `null`/`"none"` or `{"action": "halt"|"continue", "triggers": [...],
  "range_m": 800, "release": {"rule": "timeout", "clear_s": 15}, "halt_scope": "all"|"non_security"}`.
  Triggers: `receive_fire` (a Red shooter selected a convoy vehicle as target on the previous
  engagement, one tick of latency; unavailable with belief tracks), `lead_lost` (a march-unit head
  died), `detect_range` (a detected living Red ground entity within `range_m` of a convoy vehicle,
  line of sight when buildings exist). `disperse` and the `leader_policy` release (Issue #17) are
  rejected. The reaction draws no random numbers.
- Metrics (only when declared): `escort_vehicle_steps`, `convoy_contact_count`,
  `convoy_contact_steps`, `convoy_first_contact_step`, `convoy_halt_steps`.
- Limitation: Red does not exploit a halted column, so `halt` carries no attrition cost beyond time.
  Do not read halt-vs-continue results as findings until that cost exists. Comparison arms:
  `tools/make_contact_arms.py`.

## Autonomous march unit and personnel exposure (Issue #14)

Opt-in under the `convoy` spec (or flat params); absent, runs are byte-identical and no new keys appear.

- `autonomy_arm`: `"manned"` | `"autonomous_march_unit"`. Without explicit `roles` or `security_ratio`, the
  autonomous arm is one control vehicle plus four cargo trucks per march unit. It defaults
  `blue_behavior` to `leader_follow` and `succession` to `manned_only`. The manned arm defaults
  `blue_behavior` to `leader_follow` with `follow_mode="human"`.
- `escort_vehicles`: number of security vehicles added on top of task vehicles (ATP 4-11 G-8),
  holding cargo payload constant across arms.
- `crew`: role -> count override; `crew_metrics`: turn the metrics on without an arm. Default crew: control 2,
  cargo 2 (0 in the autonomous arm), security 3, recovery 2 (ATP 4-11 2-56, M-1, M-5; security and recovery are
  assumptions). Crew is read by the metrics only.
- `succession`: `"any"` (existing) | `"manned_only"` (an unmanned vehicle is never promoted to head).
- Metrics: `crew_steps_at_risk` (+ `_control/_cargo/_security/_recovery`, summing exactly to the total),
  `crew_total`, `crew_lost` (+ by role), `autonomous_headless_steps`. At risk = within weapon range of a living
  Red entity with `weapon_range > 0` and `pk_base > 0`, no detection or line of sight needed, each crew member
  counted once per step. This is a model-defined geometric exposure, not casualty risk; a destroyed vehicle loses
  its whole crew. Mines and indirect fire are outside the metric.
- Followers in the manned arm hold station on the vehicle ahead using human perception (`follow_mode="human"`),
  matching column discipline without radio link dependence; the follower response after the control vehicle
  is lost is the existing waypoint fallback (Issue #17 owns the policy).
  Comparison arms: `tools/make_autonomy_arms.py`.

## Leader-loss policy and halt release (Issue #17)

What a march unit does after its head is destroyed. These are configurable simulation policies for
comparison. They are not documented ATV-S capabilities, and nothing in ATP 4-11 or the ATV-S material
specifies them. Opt-in through `convoy.leader_loss_policy`; absent
or `legacy` builds no new state and every run is byte-identical. A declared policy defaults
`blue_behavior` to `leader_follow`. The code, this section and `doc/blue_behavior_design.md` call the
event `LEADER_LOSS`.

| Policy | After the head dies |
|---|---|
| `legacy` | Pre-#17 path: instant promotion in `LEADER_FOLLOW`, waypoint fallback when nobody can lead. |
| `promote` | Earliest eligible survivor (lowest entity index) becomes head after `handoff_steps`. Eligibility follows `succession` (`manned_only` skips uncrewed trucks). With nobody eligible the unit behaves as `continue`. |
| `absorb` | **Experimental logical reassignment.** After `handoff_steps`, the survivors are re-attached to the nearest living unit of the same serial (rule below). If there is none, the survivors fall back to `continue` for the rest of the run. |
| `halt` | The unit's survivors hold in place (sensing and engagement continue) until the release rule fires, then the earliest eligible survivor leads. Other units are not held. |
| `continue` | Survivors drive the route independently at once (waypoint). |

Keys: `handoff_steps` (int >= 0, `promote`/`absorb` only) and
`halt_release: {"clear_steps": N, "max_hold_steps": T}` (`halt` only; no release rule holds
indefinitely, so the halt can then end only when the mission does).

**Handoff latency.** `handoff_steps = 0` is an **idealized baseline**: the new head or the new
attachment takes effect on the tick the loss is seen (one tick after the head dies). No public source gives
handoff times or a loss-of-leader procedure for autonomous followers, so nonzero values are swept
parameters, not measurements. While a handoff is pending nothing new is done for the followers: each keeps
stationing on its predecessor if one is alive (chain topology) and otherwise drops to waypoint navigation,
as under `legacy`.

**`absorb` rule.** The survivors of the unit are attached to the head of the nearest other unit that
(1) has a living head, (2) is in the same serial, and (3) is nearest by straight-line distance from the
first survivor to that head at the moment the handoff completes. Receiving-leader eligibility: under
`succession="manned_only"` the receiving head must also have crew (crew is zero unless declared, so
declare it); under `succession="any"` a living head is enough, and it may then be an unmanned truck or a
security or recovery vehicle that an earlier loss promoted. The survivors take the
receiving unit's `march_unit` index and follow its head. No receiving unit: `continue`. This is a
modelling device for comparing policies. ATP 4-11 and the ATV-S material do not describe arbitrary escort
or wrecker vehicles taking over other units' followers, and nothing here claims they do.

**`clear_steps` uses ground truth.** The count is of consecutive steps with no living Red shooter
(`weapon_range > 0`, `pk_base > 0`) within that shooter's weapon range of any survivor of the unit. It reads
true positions, not Blue's detections, so the column is assumed to know when contact has ended. Either
release condition ends the halt: whichever of `clear_steps` or `max_hold_steps` is reached first. On
release the earliest eligible survivor becomes head with no further delay.

`contact_reaction.release.rule = "leader_policy"` keeps a contact halt on while any unit is policy-halted;
it requires `halt`.

Metrics (only with a policy): `leaderless_steps` (unit-steps with survivors and no head),
`ll_halt_steps` (vehicle-steps held), `ll_handoffs`, `first_leader_loss_step` (-1 when none). No random
numbers are drawn. A loss is seen one tick after the head dies.

Verification and experiments are kept apart. `tests/test_convoy_leader_loss.py` forces the kill at a chosen
step to show that each policy does what it says. `tools/make_leader_loss_arms.py` compares the policies on
matched seeds, with a forced head kill and with real engagements, and reports means with standard errors;
it is exploration, not a ranking of policies. How to read its table:

- Every paired difference is against `legacy`. It says how an arm differs from `legacy`; it is not a
  comparison of two non-legacy arms with each other.
- An interval that contains zero means the data cannot separate the arm from `legacy` at 20 seeds. It does
  not show the two are equivalent.
- With about 110 comparisons, a few intervals will exclude zero by chance.
- `absorb` is above `legacy` on `delivered_frac` in both experiments. The cause is not established and
  has not been tested. It may come from the reassignment device itself (survivors are handed a living head)
  and not from anything a real convoy could do, so treat it as an open question.

## Red target priority and the abstract ambush template (Issue #18)

Two opt-in features for Red. Absent, every run is byte-identical. Neither adds a combat mechanic: no kill
probability changes, Red does not move, and a destroyed vehicle does not block the road. Loss of
leadership (Issue #17), a behavioral halt (Issue #12) and physical route blockage are three different
things, and only the first two exist in the simulator.

### `target_priority`

The legacy rule is "each Red shooter fires at its nearest eligible target". Eligibility (alive, seen, in
weapon range, line of sight, ground domain, ammunition) is computed first and is never widened. A priority
only chooses among the eligible targets: the nearest eligible target of the first listed class that has
one, else the nearest eligible target overall. Ties go to the lowest entity index. No random numbers are
drawn and the number of kill draws is unchanged.

```json
"target_priority": {"order": ["ends", "security"], "end_definition": "position",
                    "ends_basis": "seen", "applies_to": ["at_ambush"]}
```

| Class | Meaning | What Red must know |
|---|---|---|
| `ends` | head and trail of the column | `ends_basis="seen"`: only vehicles on Red's picture (observable). `"column"`: the whole living column (ground truth) |
| `security` | Blue security vehicles | ground truth (`convoy_role`) |
| `control` | Blue control vehicles | ground truth (`convoy_role`) |
| `armed` | weapon range and kill probability above zero | assumes Red can tell armed from unarmed |
| `armored` | initial hp at or above `armored_hp` (required, no default) | assumes Red can tell armored vehicles |

`end_definition` says what head and trail mean. `position` (default): the convoy vehicle nearest to, and
farthest from, the objective; it follows vehicles as they move and are lost. `identity`: the current head of
the first occupied march unit and the last-indexed vehicle of the last occupied unit; it follows
succession and regrouping (Issues #8, #17) and assumes index order is column order. `applies_to` limits the
rule to listed Red platform types; other Red shooters keep the legacy rule. An empty `order` is
report-only: the legacy rule selects and the statistics are collected.

Metrics (only when declared). Counts of targeting EVENTS (one per Red shooter per tick): `tp_shots`,
`tp_priority_shots`, `tp_fallback_shots`, `tp_activation_frac` (share of shots a class chose), `tp_shots_<class>`,
`tp_kills_<class>` (kill draws that hit), `tp_targeted_head`, `tp_targeted_trail`. Counts of distinct VEHICLES:
`tp_vehicles_targeted` (aimed at at least once; not the number destroyed, which is `blue_losses`). Counts of
ticks: `tp_head_destroyed`, `tp_trail_destroyed` (an end vehicle destroyed on the tick it was an end), `tp_end_steps`.
Leaderless time (`leaderless_steps`, Issue #17) is in unit-steps, so unit-seconds are `leaderless_steps * dt`.
Not available with belief tracks.

### `ambush`

A fire-control template for static Red. Red platform types are given a role; the roles and the launch and
withdrawal rules follow the public OPFOR description in TC 7-100.2 (see the plan for the source table), but
every number is a placeholder.

```json
"ambush": {"roles": {"ambush": ["at_ambush"], "support": ["at_support"], "security": ["at_security"]},
           "trigger": {"point": [2400, 1500], "radius": 250}, "security_rule": "let_pass",
           "withdraw": {"after_s": 120, "loss_fraction": 0.67, "support_delay_s": 20}}
```

Listed Red types hold fire until a Blue vehicle that Red has seen is within `trigger.radius` of
`trigger.point` (latched). `security_rule="let_pass"` ignores Blue security vehicles when launching
(ground truth: reads `convoy_role`); `"engage"` counts them. Withdrawal is ordered: `after_s` after launch
or when the ambush-role loss fraction reaches `loss_fraction`, whichever comes first, ambush-role units cease
fire, support-role units `support_delay_s` later, and security-role units stay. A withdrawn unit does not
leave the map. Metrics: `ambush_launched`, `ambush_launch_step`, `ambush_withdraw_step`,
`ambush_held_steps`. The template is `scenarios/uc3_convoy_ambush.json`; its Red types share the `at_team`
numbers and differ in fire control only.

### `lane_blocking` (Issue #18, Change item 2)

A destroyed Blue ground vehicle leaves a wreck that holds up the vehicles behind it. Absent, every run is byte-identical.

```json
"lane_blocking": {"recovery_time_s": 300, "standoff_m": 20, "lane_width_m": null, "wreck_roles": null}
```

`recovery_time_s` and `standoff_m` are required and have no default (both are placeholders with no public source). The wreck blocks the road at its
along-track coordinate (route arc length if the world has a route, else distance along the line from the Blue start centroid to the objective) from the
tick after the vehicle is destroyed until `recovery_time_s` later. Living Blue ground vehicles behind it, and within half of `lane_width_m` laterally when
that is given, stop `standoff_m` short and never reverse; vehicles already past are unaffected; Red wrecks block nothing. There is **no bypass and no
rerouting** and the street graph is not consulted. It is not a halt: contact halts (#12) and leader-loss halts (#17) go through `behavior.holding`, a lane
block only moves targets back and is counted separately. Metrics (only when declared): `lane_blockages`, `lane_block_steps` (ticks with an active wreck),
`lane_blocked_vehicle_steps` (vehicle-ticks whose target was pulled back), `lane_first_block_step`. Not wired into the replay path.

### Manifest and registration hash (Issue #18, Change item 5)

`src/sandtable/manifest.py` and `tools/manifest_cli.py`. The hash covers the scenario inputs, resolved arm configuration, fixed parameters, seed list, comparison
definitions and analysis settings, serialized canonically; it excludes results, timestamps, status, notes and the source revision, which is recorded separately.
Source hashes (simulation `src/sandtable/**/*.py` and the tool's analysis files, from the bytes on disk, so uncommitted edits count; tests, docs, scenario files, outputs and third-party code are not covered) are recorded beside it in `provenance`, never inside the registration hash. Scenario-input coverage: the registration contains the parsed content of exactly the scenario files the experiment lists (any other file, and seeds outside the listed range, are not covered). `freeze --status frozen_before_run` before running (the run tool then refuses a mismatched configuration or source hash, unless `--accept-source-drift`, which is recorded); `post_hoc` for an experiment already run, which is not a
preregistration. Manifests are in `doc/manifests/`.
