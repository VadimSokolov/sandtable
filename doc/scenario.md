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
