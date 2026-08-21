# FP6111 Literature: Human-Machine Teaming in a Virtual Prototyping Testbed

Literature synthesis for VIPR-GS project FP6111, "Virtual Prototyping of Mission and Formation
Concepts with Autonomy Enabled Ground and Air Systems." The deliverable is a testbed built as
ProjectGL extensions, with SandTable as the fast pure-Python tier alongside it. Searched 2026-08-21
across nineteen parallel dimensions in three rounds, against CrossRef, OpenAlex, arXiv, Semantic
Scholar, and the local Zotero library.

Every entry carries a resolved DOI or canonical arXiv ID, a recorded verification source and date,
and a claim read from the abstract rather than inferred from the title. Where a claim could not be
verified, that is stated rather than smoothed over. Nothing here enters `report/ref.bib` until it
passes `report/tools/audit.py` check 1.

**Evidence grades used below.** *Strong* means multiple independent literatures or a proof.
*Partial* means real but bounded (asymptotic theory, or a domain that does not fully transfer).
*Thin* means the claim outruns the peer-reviewed record.

---

# Part 0: Scope

## The project is the testbed, not one experiment

The Statement of Work commits to four numbered objectives, two research questions, five metric
families, and a Year 1 demonstration. It does not commit to any single experiment. In particular,
**the grid of control modality crossed with a C0 to C5 comms and EW degradation ladder is not in
the SOW.** That grid is a later, sharper cut of objective (3) combined with the promised EW work.
It is a good experiment and it is the paper's centerpiece, but it is one slice of objective (3),
not the program.

Rounds 1 and 2 of this review (dimensions D1 to D11) were scoped around that grid. They are deep on
objective (3) and on the comms axis, and they are correspondingly thin everywhere else. Round 3
(D12 to D19) exists to cover the rest of the SOW. Read the coverage tables below before treating
any part of this document as complete.

## The four objectives

| # | Objective (verbatim from the SOW) | Dimensions | Coverage |
| --- | --- | --- | --- |
| 1 | Detect patterns of success and failure in human-machine collaboration using machine learning | D14 | round 3 |
| 2 | Evaluate HMI designs that optimize cognitive load distribution | D12, partial D4, D7 | round 3 |
| 3 | Assess the effectiveness of direct versus supervisory control approaches | D4, D7, D1, D2, D3, D5, D6 | strong |
| 4 | Extend mission engineering and kill web analysis to measure mission success, operational efficiency, and collaboration effectiveness | D13 | round 3 |

Objective (3) is the only one that rounds 1 and 2 covered properly. Objectives (1), (2) and (4)
returned essentially zero hits on their own vocabulary in the round 1 and 2 output: no "kill web,"
no "mission engineering," no "cognitive load," no "process mining," no "data mining."

## The two research questions

| Research question | Dimensions | Coverage |
| --- | --- | --- |
| What metrics are most appropriate for evaluating mission success, efficiency, and feasibility in human-machine teaming? | D17 | round 3 |
| What best practices and standards should be adopted for HMI, command protocols, and cybersecurity in multi-domain missions? | D12 (HMI), D15 (command protocols), D16 (cybersecurity) | round 3 |

Both are open questions the project committed to ANSWERING, not background it can assume. RQ1 in
particular means the five metric families below are a hypothesis, not a settled instrument set.

## The promised method

| Promised element | Dimensions | Coverage |
| --- | --- | --- |
| Agent-based modeling of vehicles, sensors and operators | D10 | strong |
| Reinforcement learning to explore strategies | D8 | strong |
| **Bayesian** learning to explore strategies | D18 | round 3 |
| ABM to deep-learning surrogate with uncertainty to RL, closed loop | D18, partial D9 | round 3 |
| Unscripted and emergent behavior generation | D8, D11, D10 | partial |
| Cyber-physical elements: comms links, autonomy levels, mission planning | D1, D2, D5 | partial |
| Cyber-physical elements: **power systems** | none | **uncovered** |
| EW effect injection (jamming) | D5 | strong |
| **Cyber** effect injection (spoofing, malware), distinct from EW | D16 | round 3 |
| Simulated C2 interfaces for human-in-the-loop work | D19 | round 3 |
| Command architectures: doctrinal planning versus bidding | D15 | round 3 |
| Scenarios in SysML/LML traced to Army doctrine, Innoslate conformance flagging | D13, D14 | round 3 |
| ML and data mining over decision, communication and state-transition logs | D14 | round 3 |

## The five promised metric families

| Family | Named sub-metrics | Dimensions | Coverage |
| --- | --- | --- | --- |
| TTP effectiveness | mission success rate, time to objective, attrition | D10, D11, D17 | partial |
| Coordination | communication frequency, teamwork graphs, task handoff | D17, D3 | thin |
| Human-AI trust | operator surveys, override rates, trust calibration indices | D7, D17 | partial, and see I11 |
| Adaptability | re-planning time, mission recovery after disruption | D17 | round 3 |
| Contested performance | impact of EW and cyber actions on mission outcomes | D5, D16 | partial |

Only "contested performance" and parts of "TTP effectiveness" are things SandTable currently
measures. Note I11: the project's trust metric is measuring trust resolution, not trust, and the
name should change before the metric is published.

## Promised outcomes and Year 1 tasks

| Promised outcome | Dimensions | Coverage |
| --- | --- | --- |
| Novel autonomous formation concepts balancing human control and autonomy | D19, D1 | round 3 |
| Evaluation of those formations on resilience, efficiency, operational feasibility | D17, D13 | round 3 |
| Translation of mission requirements into human-technology-interface frameworks | D12, D13 | round 3 |
| Published design patterns, evaluation metrics, testbed architectures | D17, D13 | round 3 |
| Year 1 demonstration D1, simulated and hybrid, hardware-in-the-loop or emulated vehicles | D19 | round 3 |

| Year 1 task | Dimensions | Coverage |
| --- | --- | --- |
| RT1 Scenario requirements gathering and architecture design | D13, D19 | round 3 |
| RT2 Baseline testbed development, ABM integration | D10, D18 | partial |
| RT3 Initial HMI evaluation and TTP modeling | D12, D14, D11 | round 3 |

## Residual gaps this review does not close

Stated plainly so they are not mistaken for coverage.

- **Power and energy systems.** Named in the SOW methodology as a cyber-physical element to model.
  No dimension in any round covers vehicle energy, endurance, or recharge logistics. If endurance
  constrains formation concepts, and for a UAV relay it certainly does, this is a real hole.
- **Classified mission requirements.** The SOW promises translation of classified needs into HTI
  frameworks. Everything in this repository is unclassified and stays that way, so this review can
  only cover the unclassified method, never the requirements themselves.
- **Innoslate specifically.** Prior art for automated doctrinal-conformance checking is sought under
  D13 and D14, but tool-specific literature for this vendor may not exist.

---

# Part 1: Important Ideas

Sixteen ideas in two groups, each ordered by how much it changes what the project should build or
claim. Group A came from the autonomy and communication sweep, Group B from the algorithms and
simulation-method sweep.

## Group A: Autonomy and inter-agent communication

## I1. The comms-autonomy crossover is real, and four independent literatures already found it

**Strong. Four independent literatures.**

SandTable's headline result, that the optimum shifts toward on-platform autonomy as communications
degrade, is not a new discovery. It has been established separately in four fields that appear not to
cite one another.

| Field | Work | Form of the result |
| --- | --- | --- |
| Networked control | Ballotta, Jovanovic, Schenato 2023, `10.1109/TCNS.2023.3237483` | Analytic: sparse nearest-neighbour control beats centralized all-to-all once latency grows fast enough with link count |
| Human factors, real robots | Luck, McDermott, Allender, Russell 2006, `10.1145/1121241.1121277` | Empirical: latency penalties concentrate at low autonomy and vanish at high autonomy |
| Ground vehicle convoying | Cheung, Rawashdeh, Mohammadi 2022, `10.3390/app12199863` | Empirical: on-platform behavior-based control beat a delayed-follower controller across all jammer types and path plans |
| Multi-agent RL | Li et al. 2025, arXiv `2510.11824` | Empirical, 82,620 runs: clean-channel-optimal tuning is not degradation-robust tuning |

**Repositioning required.** Luck et al. 2006 ran essentially SandTable's centerpiece design, level of
automation crossed with latency, on real hardware under ARL sponsorship. Frame the contribution as
*extending* a known effect to mission scale under an adversarial ladder, not as discovering it. Not
citing this would be a visible gap to any reviewer from the human-factors community.

## I2. Connectivity is not binary. It is a scalar with a threshold

**Partial. Asymptotic theory, 2 of 19 works hardware-validated.**

- **Ren and Beard 2005** (`10.1109/TAC.2005.846556`): consensus holds if the *union* of the directed
  communication graphs over time contains a spanning tree frequently enough. Intermittent contact
  suffices; a live link is not required.
- **Olfati-Saber and Murray 2004** (`10.1109/TAC.2004.834113`): the *speed* of convergence is set by
  the algebraic connectivity, the Fiedler eigenvalue of the graph Laplacian.
- **Tsitsiklis, Bertsekas, Athans 1986** (`10.1109/TAC.1986.1104412`): the guarantee holds only while
  inter-communication interval and delay stay bounded, and voids above that.

Together these map each rung of the C0-C5 ladder to an algebraic connectivity value predicting
coordination latency, plus a threshold where the guarantee disappears. That threshold is a candidate
theoretical locus for the crossover, which currently rests on simulation alone, and it would upgrade
the ladder from an ordinal device to a quantitative one.

**Honest limit.** 17 of the 19 works in this dimension are asymptotic theory on integrator agents in
simulation. Only Rubenstein 2014 (`10.1126/science.1254295`, 1,024 physical robots) and Vasarhelyi
2018 (`10.1126/scirobotics.aat3536`, 30 outdoor drones) are hardware-validated, and only Kar and
Moura 2009 offers anything close to a finite-horizon bound. The theory motivates the mapping; it does
not certify it at mission timescales.

## I3. Decentralization is hard by theorem, so removing comms changes the optimal policy class

**Strong. Transfers by proof.**

- **Bernstein, Givan, Immerman, Zilberstein 2002** (`10.1287/moor.27.4.819.297`): decentralized MDP
  and POMDP control is NEXP-hard for even two agents.
- **Goldman and Zilberstein 2004** (`10.1613/jair.1427`): maps which decentralized subclasses fall
  from NEXP to P, and formalizes information sharing. Adding communication does not change the
  worst-case complexity, but it does change which subclass you are in.
- **Pynadath and Tambe 2002** (`10.1613/jair.1024`): COM-MTDP, complexity indexed jointly by
  observability and communication cost.

Degrading the link is not a perturbation on a fixed problem. It moves the team into a different
complexity class, which is why the best *design* changes rather than merely scoring worse. This is
the theoretical backbone for treating comms as a crossed experimental factor.

## I4. What is communicated matters more than how much

**Strong. Consistent across 30 years.**

- **Tan 1993** (`10.1016/b978-1-55860-307-3.50049-6`, 1,847 cites): three separable sharing modes,
  sensation, episodes, and learned policies, with different cost and benefit profiles. Its framing
  question is verbatim the project's: "What is the price for such cooperation?"
- **Balch and Arkin 1994** (`10.1007/BF00735341`): communication helps some tasks and not others, and
  the *lowest* level of communication is nearly as good as the richest.
- **Roth, Simmons, Veloso 2005** (`10.1145/1082473.1082593`): communicate only when the observation
  would actually change team performance.
- **Wang et al. 2020, IMAC** (arXiv `1911.06992`): a bandwidth limit provably forces low-entropy
  messages.
- **Zhang, Lin, Zhang 2020, TMC** (arXiv `2010.14391`): temporal smoothing cuts message rate and
  improves robustness to transmission loss at the same time.

**Highest-payoff design change in this review.** A scalar comms-quality ladder understates the
phenomenon. If C0-C5 degraded *what is shared* (full shared picture, then episodic updates, then task
or policy updates only) rather than only how well a scalar channel performs, the model would align
with the mechanism the literature actually identifies, and the ladder would become interpretable
rather than stipulated.

## I5. Degrading comms attacks span of control from both sides at once

**Strong. Measured on hardware and in simulation.**

Crandall, Goodrich, Olsen, Nielsen 2005 (`10.1109/TSMCA.2005.850587`) give fan-out as

```
FO = NT / IT + 1
```

with NT neglect time and IT interaction time (confirmed verbatim from full text). Degradation
inflates IT and simultaneously shrinks safe NT, so span of control falls from numerator and
denominator together.

| Measured effect | Value | Source |
| --- | --- | --- |
| Inter-command interval, 10 s each-way latency | 26.6 to 42.4 s | Walker et al. 2012, `10.1109/ICSMC.2012.6378253` |
| Targets found, same condition | 19.86 to 16.71 (p=.021) | Walker et al. 2012 |
| Recovery with predictive display | 18.86 (p=.467) | Walker et al. 2012 |
| Operator capacity lost to wait times | up to 67% | Cummings and Mitchell 2008, `10.1109/TSMCA.2007.914757` |
| Residual loss under management-by-exception | 36% | Cummings and Mitchell 2008 |
| Low LOA under latency | +50% time, +33% errors | Luck et al. 2006 |
| High LOA under latency | flat | Luck et al. 2006 |
| Variable vs fixed lag | 11.38 vs 9.75 min | Luck et al. 2006 |
| Workload threshold, simulated HMMWV | 0.8 s delay | Lu et al. 2019, `10.1080/10447318.2019.1574059` |

This is an analytic mechanism for the moving optimum, not merely a curve, and it supplies calibration
values for an operator model whose parameters are currently hand-set.

## I6. Interior optima recur, for genuinely different reasons

**Partial. Mechanisms differ, do not conflate them.**

- **Lerman and Galstyan 2002** (`10.1023/A:1019633424543`): physical interference produces an optimal
  group size that maximizes group performance.
- **Span of control**: performance rises from 4 to 8 robots and falls from 8 to 12, a direct-control
  ceiling near 8 to 12.
- **SandTable's counter-UAS result**: a signature-driven interior optimum in swarm size.
- **Sellner et al. 2006** (`10.1109/JPROC.2006.876966`): sliding autonomy empirically beats *both*
  endpoints, full teleoperation and full autonomy.
- **Wickens and Dixon 2007** (`10.1080/14639220500370105`): a reliability crossover at 0.70, below
  which automation is worse than no automation at all. A threshold on a different axis, with a number.

The project's interior optimum is one instance of a recurring pattern, which strengthens its
plausibility. But precisely because interior optima arise from several distinct mechanisms
(interference, operator capacity, attrition signature, reliability), the paper must be specific about
which one it demonstrates. The existing scoping of the counter-UAS result as a mechanism
demonstration is the right instinct.

## I7. Link quality flips the ranking of coordination mechanisms, not just their scores

**Strong. Validates the experimental design.**

**Otte, Kuhlman, Sofge 2020** (`10.1007/s10514-019-09828-5`): six auction mechanisms that perform
identically under perfect communication degrade differently under packet loss, and the *best*
mechanism changes with link reliability.

This is the strongest single methodological justification for the centerpiece design. Communication
quality cannot be held constant or averaged over, because doing so selects a coordination mechanism
that is optimal nowhere in particular. It must be a crossed factor.

## I8. The always-connected assumption is the field default, and that is precisely the gap

**Strong. Four agents converged independently.**

- **Amigoni, Banfi, Basilico 2017** (`10.1109/MIS.2017.4531226`): survey stating explicitly that
  assuming continuous connectivity is the field's default.
- **Gielis, Shankar, Prorok 2022** (`10.1007/s43154-022-00090-9`): critical review naming the dearth
  of joint robot-plus-network co-design.
- **D4**: no paper models operator capacity as a function of packet loss or outage probability.
  Everything is latency or bandwidth.
- **D1 and D5, independently**: no study crosses control modality against a graded EW ladder at
  formation scale.
- **D7**: no paper computes an ROC, AUC, or d-prime of operator trust against agent ground-truth
  correctness in a multi-vehicle or degraded-comms setting.

**The defensible novelty claim, stated precisely.** Not "we discovered that autonomy helps under
degraded comms." Rather: crossing a *graded, adversarial* degradation ladder against a *graded human
control modality*, at *formation scale*, in a single experiment, with *dropout* as well as latency and
bandwidth. Every qualifier is load-bearing and each maps to a specific absence in the literature.

**Methodological ancestor to cite.** Giachetti et al. 2013 (`10.1002/sys.21216`), a low-fidelity
agent-based military simulation using fractional factorial DOE that found centralized decision
authority creates commander communications bottlenecks. Same method, same class of finding, published
in *Systems Engineering*. Citing it converts a bare novelty assertion into a lineage.

## I9. Fidelity-for-throughput is a validated bet, but the transfer evidence is automotive

**Partial. Architecture yes, empirics do not transfer.**

- **Cusumano-Towner et al. 2025** (arXiv `2502.03349`): Gigaflow, 1.6 billion km of self-play, 42
  years of driving experience per hour on one 8-GPU node, state of the art on three independent
  benchmarks, outperforming prior work on recorded real-world scenarios without ever seeing human data
  in training, averaging 17.5 simulated years between incidents.
- **Kazemkhani et al. 2024, GPUDrive** (arXiv `2408.01584`): throughput named as the binding
  constraint on multi-agent research.
- **Rowe et al. 2026** (arXiv `2606.19641`): Gigapixel renders "a simplified bounding-box world that
  preserves essential scene structure" at 50k agent steps per second, an explicit statement of the
  fidelity-for-throughput trade.
- **Cornelisse et al. 2025** (arXiv `2502.14706`): a simulation agent's first requirement is
  reliability, because unreliable agents distort the signal-to-noise ratio of any analysis built on
  them. An external argument for SandTable's byte-identical-when-disabled gating discipline.

**Caveat that must appear in the paper.** This cluster is automotive. Dense urban driving has no
adversary actively degrading sensing and communication, which is the exact variable the C0-C5 ladder
manipulates, and it has abundant real-world validation data that ground military formations do not.
The cluster supports SandTable's *architectural* choice strongly. It does not transfer the empirical
result.

## I10. The EW-immune link: mechanism supported, magnitude unquantified

**Thin. Zero peer-reviewed sources.**

Fiber-optic FPV control has zero peer-reviewed literature across five indexes. The available material
is trade press, plus one preprint that turns out to concern discarded-cable pollution. Both
authoritative 2024-25 counter-UAS reviews (RUSI, and CRS R48477) do not mention fiber at all.

The best available mechanism statement is **Watling and Bronk 2024** (RUSI, grey literature): jamming
the receiver ends the ISR mission, whereas autonomous terminal guidance shifts vulnerability to the
*seeker*, where obscurants remain highly effective.

**Recommendation.** The supported shape is flattening, not immunity: the slope against jamming goes
to zero while the *level* is set by non-RF defeat. Model it as a swept parameter and describe results
as consistent with the reported mechanism rather than validated by it, matching the project's existing
citation convention.

## I11. The project's trust metric is right, but it is using the wrong word for it

**Actionable. Terminology correction.**

The project defines Human-AI Trust as "trust calibration as discrimination, not mean trust." That
construct is correct and the literature supports it. The word is not.

**Lee and See 2004** (`10.1518/hfes.46.1.50_30392`), the canonical reference, decomposes appropriate
trust into *calibration*, *resolution*, and *specificity*. What the project means, how precisely trust
differentiates cases where the agent is actually right from cases where it is wrong, is what Lee and
See call **resolution**. They reserve **calibration** for exactly the mean-level correspondence the
project is trying to move away from.

**Recommendation.** Define the metric as *trust resolution* (Lee and See 2004), noting that the
AI-decision-making literature loosely calls it calibration. Using "calibration" for the discrimination
construct inverts the canonical term in front of exactly the human-factors reviewers most likely to
notice.

Supporting machinery: **Sheridan 2019** (`10.1177/0018720819829951`) reinterprets signal detection
theory and model-based control as quantitative trust models with explicit measures. **Schemmer et al.
2023** (`10.1145/3581641.3584066`) gives Appropriateness of Reliance as a two-dimensional measure
scoring correct-following and incorrect-rejecting separately. **Wischnewski et al. 2023**
(`10.1145/3544548.3581197`), a 96-study survey, finds that calibration *measurement* is what limits
interpretation, which is the warrant for investing in the metric at all.

**Scope the claim as a new operationalization, not a new construct.** No paper was found that computes
an ROC, AUC, or d-prime of operator trust against agent ground-truth correctness in a multi-vehicle or
degraded-comms setting. That is the genuinely novel part.

## Group B: Algorithms and simulation method

## I12. Use RL for scenario generation, not for blue behaviors

**Strong. The methodological argument is specific to this paper.**

The literature does not support learning blue agent behaviors at this fidelity, for a reason that is
about your experiment rather than about RL:

- An RL policy adds a **training-seed nuisance term on top of mission-seed variance**. Henderson et al.
  2018 (`10.1609/aaai.v32i1.11694`) and Agarwal et al. 2021 (arXiv `2108.13264`) show that variance can
  swamp the effect being reported. The control-modality by C0-C5 contrast is the entire paper, so
  adding a second variance source to the measured quantity is a bad trade.
- **Black and Darken 2023** (arXiv `2402.06694`, I/ITSEC) state that deep RL "has yet to perform at or
  above the human level in the long-horizon, complex tasks typically found in combat modeling and
  simulation." Choi et al. 2022 (`10.1109/ACCESS.2022.3227797`), a four-environment CGF study,
  concludes only that RL "is applicable."
- **Knox et al. 2023** (`10.1016/j.artint.2022.103829`): reward misdesign fails near-universally across
  a published subfield, and SandTable's mission metrics would become that reward.

**Where RL does earn its place: unsupervised environment design.** Dennis et al. 2020, PAIRED (arXiv
`2012.02096`) names the project's exact problem, that hand-authoring environment distributions is
"error prone", and SandTable hand-authors both its scenarios and its C0-C5 ladder. Jiang et al. 2021,
PLR-perp (arXiv `2110.02439`) makes it cheap, requiring no adversary network, only a scoring rule over
missions already being run. Parker-Holder et al. 2022, ACCEL (arXiv `2203.01302`) adds evolutionary
level editing on a regret curriculum. At 7 to 11 missions per second, UED converts SandTable's speed
into a comparative advantage, precisely because UED needs vast cheap episodes that Unreal cannot supply.

**Two honesty notes.** No canonical PPO-versus-SAC head-to-head exists, so do not cite one. And PPO's
advantage over TRPO is largely code-level rather than algorithmic (Engstrom et al. 2020,
`10.48550/arXiv.2005.12729`), across a configuration surface of more than 50 design choices
(Andrychowicz et al. 2020, `10.48550/arXiv.2006.05990`).

## I13. The two-tier design has a formal frame, and one missing measurement would unlock it

**Strong on the frame. The enabling measurement has not been made.**

Two literatures converge on SandTable's fast-tier plus high-fidelity-tier structure, from different
directions:

- **Multifidelity optimization.** Peherstorfer, Willcox and Gunzburger 2018 (`10.1137/16M1082469`)
  defines the paradigm and licenses the architecture, with the premise that the high-fidelity model
  stays *in* the loop rather than merely downstream. Peherstorfer, Willcox and Gunzburger 2016
  (`10.1137/15M1046472`) gives a unique analytic optimum for how many runs of each model to buy, from
  the cost ratio and the correlation. Cutler et al. 2015 (`10.1109/TRO.2015.2419431`) supplies
  sample-complexity proofs for multifidelity simulators, concluding one should run at "the lowest level
  simulator that will still provide useful information."
- **Multi-resolution modeling**, the defense M&S term. Davis, Bigelow and McEver 2000
  (`10.1109/WSC.2000.899734`) calibrated a low-resolution model against a high-resolution simulation and
  in doing so *exposed defects in the high-resolution sim*. Ahner, Buss and Ruck 2007
  (`10.1109/WSC.2007.4419742`, TRAC/NPS) use a low-resolution entity model to shape initial conditions
  for high-resolution runs.

**The missing measurement.** Both analytic results are unlocked by one thing the project appears not to
have done: run overlapping designs in *both* tiers and report the correlation. Without that number,
multi-fidelity is motivation, not justification. This is the most concrete and cheapest experimental
recommendation in this review.

**Design it correctly the first time.** DoDM 5000.102 (9 Dec 2024) imposes a non-circularity rule: runs
used to calibrate cannot also validate. So split the overlapping ProjectGL designs into a calibration
set and a held-out validation set from the outset. Cheap now, expensive to retrofit.

**A framing correction.** SandTable is a *different model*, not a coarsened Unreal run, so
multi-information-source (Poloczek, Wang and Frazier 2017, arXiv `1603.00389`, which handles a cheap
source with unknown region-dependent bias) is more defensible than claiming a fidelity hierarchy.
Calling it a fidelity ladder invites the question of which knob coarsens ProjectGL, and there is none.

**Cautions.** Fernandez-Godino et al. 2019 (`10.2514/1.J057750`) document cases where low-fidelity data
made surrogates *worse*. Reynolds, Natrajan and Srinivasan 1997 (`10.1145/259207.259235`) show
cross-resolution inconsistency arises even when each level is separately valid. Hyun et al. 2025
(`10.52682/jkidt.2025.7.4.028`) found a uniformly low-resolution model increased miss-distance error
against a high-resolution reference, while *selective* tiering did not. No general "low fidelity holds
when X" result exists, so the claim must be scoped per scenario with measured agreement. RAND MR-1750-AF
offers a survivable phrasing: "valid, subject to the principal assumptions, for exploratory analysis."

## I14. A static red force is a structural bias, not a conservative approximation

**Strong on direction. Magnitudes come from allocation problems, not maneuver.**

This is the project's most-cited self-declared limitation, and the literature says it is worse than a
loss of precision. Four independent results:

- **Golany et al. 2009** (`10.1016/j.ejor.2007.09.001`): probabilistic risk and strategic risk give
  *opposite* prescriptions, concentrate versus spread. Modeling an adaptive adversary as a fixed
  distribution can invert the recommendation, not merely blur it.
- **Roberson 2006** (`10.1007/s00199-005-0071-5`): the Colonel Blotto equilibrium is a *distribution*
  over allocations, not a single allocation, so one fixed red disposition answers the wrong question.
- **Bier, Oliveros and Samuelson 2007** (`10.1111/j.1467-9779.2007.00320.x`): the optimal defender
  leaves some targets deliberately undefended, a recommendation a static-red model can never produce.
- **Brown and Cox 2011** (`10.1111/j.1539-6924.2010.01492.x`): probabilistic risk analysis applied to an
  adversary is unjustified even with perfectly calibrated assessors. Calibration does not rescue it.

Merrick and Parnell 2011 (`10.1111/j.1539-6924.2011.01590.x`) run the same problem both ways and get
significantly different results. RAND RR-A161-1 (Davis et al. 2021) reports that a best-estimate Red
"often proves wrong."

**Minimum viable adaptive red, and it is cheap.** An ensemble of 3 to 5 doctrinal red templates, each
best-responding *once* to the posted blue plan, in the bilevel attacker-defender form of Brown,
Carlyle, Salmeron and Wood 2006 (`10.1287/inte.1060.0252`). Add dynamic scripting (Spronck et al. 2006,
`10.1007/s10994-006-6205-6`) only if red must adapt mid-run. Skip self-play, which fails Guikema's
(`10.1111/j.1539-6924.2011.01737.x`) tractability and confidence conditions for adversary models.

**Honest caveat.** All quantitative results above come from defender-attacker allocation problems, not
maneuver simulation. The direction transfers; the magnitudes do not.

## I15. Migrate to behavior trees for verifiability, not for expressiveness

**Actionable. Implementation choice with a named cost.**

SandTable currently uses trigger state machines. The case for behavior trees is real but narrower than
usually claimed:

- **Biggar, Zamani and Shames 2022** (`10.1145/3511606`): BT modules are subtrees, and module edits have
  no greater flow-on than single-action edits, so **verification stays local**. That is the actual win.
- **Iovino et al. 2022** (`10.1016/j.robot.2022.104096`) report that FSMs "scaled poorly and were
  difficult to extend, adapt and reuse."
- **Colledanchise and Ogren 2017** (`10.1109/TRO.2016.2633567`) show BTs generalize subsumption
  architectures, sequential composition, and decision trees, with properties preserved under composition.

**The named cost.** Biggar et al. 2021 (`10.1109/LRA.2021.3074337`) establish a formal expressiveness
hierarchy and show BTs are *not* a free superset of FSMs. Recovering the lost expressiveness requires a
blackboard, which costs exactly the readability the migration was for. Budget for that and state it
rather than discovering it mid-implementation. Practical ceiling from the games side: Isla 2005 (GDC,
Halo 2) reports that tuning behavior priorities becomes "almost impossible" past roughly 20 behaviors.

---

## I16. Thicken blue scripts to the Army's present behavior set, not to RACER

**Partial to strong. One quantified comparison, one architecture template, one program record.**

I12 says what not to do: do not learn blue behaviors with RL, because a training seed adds variance
on top of the mission seed and the modality contrast is the whole result. This is the constructive
half. What blue should get instead is a **thicker script**, and the literature is unusually clear
about how thick it should be and where it must stop.

**Real ground autonomy is a stack, not one policy.** Urmson et al. 2008 (`10.1002/rob.20255`) is the
published template, and its abstract states the decomposition directly: "A three-layer planning
system combines mission, behavioral, and motion planning," where the mission layer "considers which
street to take," the behavioral layer "determines when to change lanes and precedence at
intersections and performs error recovery maneuvers," and the motion layer "selects actions to avoid
obstacles." The middle layer is the one SandTable is missing. (The commonly repeated detail that
Boss's behavioral layer is implemented as a family of state machines is body-level content, not in
the abstract. Cite the three-layer decomposition from the abstract; do not attribute the state-machine
implementation without reading the paper body.)

**SandTable's modality axis currently changes a gain, not a behavior.** In `src/sandtable/c2.py`,
control modality resolves to a per-agent scalar `control_quality` in [0, 1], which `motion.py` reads
as a speed multiplier (`0.35 + 0.65 * q`) and the engagement kernel reads similarly. That models
*how well* an agent is being controlled. It does not model *what the agent is doing*. Meanwhile
`planning.py` gives blue ground exactly one behavior: an independent pure-pursuit carrot along a
lane set by `route_bias`, explicitly documented as having "no dead-leader dependency," with
`formation_spread` accepted and then discarded (`_ = spread  # reserved for the richer formation
model`). So the project's headline axis is currently a gain knob on a single script.

**The honest target is the fielded behavior set.** The June 2026 Army RFI names the current baseline
modes as teleoperation, waypoint navigation, leader-follower, and sentry (recorded in
`doc/scenario.md`, grey literature). Those four, plus a small set of recovery triggers (stop, wait,
hand back to the operator), are what a mission-level simulator can represent faithfully. GVSC's own
software direction supports this reading: Pirozzo et al. 2019 (`10.4271/2024-01-3821`) records the
consolidation of AMAS into the government-owned Robotic Technology Kernel, and the fielded thread
with the most operational history is leader-follower resupply, whose lineage runs back to the
TARDEC/ARL Robotic Follower ATD (Brendle and Jaczkowski 2002, `10.1117/12.474441`).

**And there is a quantified reason to prefer on-platform behavior over link-dependent following.**
Cheung, Rawashdeh and Mohammadi 2022 (`10.3390/app12199863`) put a behavior-based convoy controller
against a basic delayed-follower controller under jamming and measured **13.33% to 86.61% reductions
in path error** across jammer types and path plans. That is the thicken-the-script thesis, measured.
It is simulation and it scores path error rather than mission success, so it licenses the mechanism,
not a mission-level effect size.

**Where this must stop.** SandTable has no LiDAR, no vehicle dynamics, and no slope or belly-clearance
model, by design. Thickening scripts can therefore approach how an Army UGV is **tasked and
commanded**. It cannot approach how RACER drives off-road without map or GPS, because that gap is
perception and local motion. The Army measures off-road autonomy by how often a soldier has to take
over, and SandTable does not currently vary intervention rate at all (`doc/scenario.md` already flags
this as the most important missing mechanism). A thickened blue script is not a digital twin of a
driving stack, and the paper should say so in those words rather than let the reader infer otherwise.

**What changes.** Add a behavioral layer between C2 and motion, holding the four fielded modes plus
recovery triggers, and let control modality select the mode repertoire rather than only scaling a
quality gain. This also finally consumes `formation_spread`, and it gives the leader-follower
scenario that `doc/scenario.md` lists as a fielded GVSC thread with no SandTable counterpart. Design
spec in `doc/blue_behavior_design.md`.

# Part 2: Comprehensive Review

| Dim | Topic | Verified | Notable absence found |
| --- | --- | --- | --- |
| D0 | User-supplied seeds | 3 + 6 + 1 | MathWorks page is not citable |
| D1 | Ground military vehicle autonomy | 12 + 4 + 2 | No modality x EW-ladder study |
| D2 | Coordination under comms constraints | 22 + 10 | Always-connected is the default |
| D3 | Decentralized control and consensus | 14 + 5 | Almost no finite-horizon bounds |
| D4 | Span of control, neglect tolerance | 12 + 5 | No capacity-vs-packet-loss model |
| D5 | Contested EM environment | 10 + 2 + 3 | No fiber-link peer-reviewed work |
| D6 | MARL and learned communication | 14 + 11 | No MARL-under-military-jamming study |
| D7 | Adjustable autonomy and trust | 14 + 2 + 7 | No trust ROC vs agent ground truth |
| D8 | RL algorithms | 16 + 8 | No RL-vs-scripted study in military sim |
| D9 | Optimization, DOE, surrogates | 16 + 18 | No multi-fidelity precedent in combat sim |
| D10 | ABM combat simulation as method | 15 + 5 grey | No general "low fidelity holds when X" |
| D11 | Red and blue behavior policies | 19 + 3 grey | No scripted-vs-adaptive red study in mission sim |

## D1: Ground military vehicle autonomy

**Taxonomy and framing.** Huang 2008, ALFUS (`10.6028/NIST.SP.1011-I-2.0`) fixes the standard
terminology, Teleoperation / Human-Delegated / Human-Supervised, on a three-axis model. Bradshaw,
Hoffman, Woods, Johnson 2013 (`10.1109/MIS.2013.70`) is the necessary corrective: autonomy is not a
scalar level, and raising it does not monotonically reduce operator demand. Any framing that treats
direct-to-supervisory as one dial should cite and respect this.

**Capability lineage.** Thrun et al. 2006 (`10.1002/rob.20147`, Stanley) and Urmson et al. 2008
(`10.1002/rob.20255`, Boss, a three-layer mission/behavioral/motion planner) anchor the Grand and
Urban Challenges. Min et al. 2026 (`10.1002/rob.70154`) is a 250-paper survey establishing that
off-road autonomy still lags urban, with military need a named driver.

**Military-specific.** Brendle and Jaczkowski 2002 (`10.1117/12.474441`) documents the TARDEC/ARL
Robotic Follower ATD, leader-follower as the near-term autonomy hedge. Note the abstract announces a
program start, not a result, so it supports lineage only. Nahavandi et al. 2022
(`10.1109/ACCESS.2022.3147251`) surveys convoying and notes human-in-loop decisions add delay relative
to automated ones. Andersson et al. 2025 (`10.1002/rob.22442`) reports a 16-battle virtual experiment
in which UGVs directed by a single soldier stalled a mechanized company in three of four battles.

**The software the Army actually owns.** Pirozzo, Hecker, Dickinson, Schulteis, Ratowski and Theisen
2019 (`10.4271/2024-01-3821`, GVSETS 2019, SAE-indexed) is the citable record that GVSC folded the
Lockheed Martin Autonomous Mobility Applique System into the government-owned Robotic Technology
Kernel rather than maintain two autonomy stacks. This closes a gap D1 previously recorded as
unverifiable ("ExLF/AMAS, trade press only"). Read the DOI carefully: the `2024-01-3821` string is
SAE's own numbering and the work is dated **2019**. It must not be cited as a 2024 paper.

**Behavior-based scripting beats link-dependent following under jamming.** Cheung, Rawashdeh and
Mohammadi 2022 (`10.3390/app12199863`) is the sharpest single finding for this project's blue-agent
design. They compare a behavior-based architecture (layered costmaps plus vector-field-histogram
motor schemas, assembled into a convoy controller) against a basic delayed-follower convoy
controller, under several jammer types and path plans, and report path-error reductions of
**13.33% to 86.61%** for the behavior-based assemblage. The mechanism is exactly the one this
project cares about: move competence onto the platform so the radio is not carrying every steering
command. It is simulation, not field trial, and it measures path error rather than mission outcome,
so it supports the mechanism and not a mission-level magnitude.

**Bandwidth as forcing function.** Guivant et al. 2012 (`10.1002/rob.21432`) spans teleoperation to
point-and-click autonomy in one architecture with bandwidth and latency as the governing axis. Pace et
al. 2014 (`10.1117/12.2050394`) shows dense sensor reconstructions exceed real-time wireless capacity,
forcing onboard scene condensation. Autonomy is partly a bandwidth consequence.

**Currency flag.** CRS IF11876 states the Army's one-operator-many-RCVs aspiration and records the
1 May 2025 halt of the RCV program. If the paper motivates itself via RCV, that halt must be
acknowledged. No canonical peer-reviewed DARPA RACER paper exists.

**Could not verify.** TRADOC RAS Strategy 2017 (no reachable official .mil URL), Army Science Board
FY2016 RAS study, SMET (no DOI-bearing work), ExLF (trade press only). AMAS is no longer on this
list: it is verified above via Pirozzo et al. 2019. The agent hit HTTP 429 on
arXiv throughout and reported it, so no D1 entry rests on an unconfirmed arXiv ID.

## D2: Coordination under communication constraints

**Crossovers, thresholds, interior optima.** The closest prior art to the headline result: Ballotta
2023 (architecture crossover in latency), Otte 2020 (mechanism-ranking crossover in packet loss),
Lerman and Galstyan 2002 (interior optimum in team size), Balch and Arkin 1994 (saturation of
communication value), Rosenfeld et al. 2008 (`10.1016/j.artint.2007.09.008`, negative returns to scale
as coordination cost rises), Zhivkov, Schneider, Sklar 2017 (`10.1007/978-3-319-64107-2_32`, measured
non-linear degradation across 0 to 75 percent packet loss).

**Scaling.** Otte, Kuhlman, Sofge 2018 (`10.1007/s10514-017-9687-0`) gives a closed form in which the
benefit of communication grows with team size, which matters because the centerpiece varies span of
control.

**Bandwidth economy.** Best, Forrai, Mettu, Fitch 2018 (`10.1109/ICRA.2018.8460617`) cuts channel
utilisation by up to four fifths with little coordination loss; Marcotte, Wang, Mehta, Olson 2020
(`10.1007/s10514-019-09849-0`) beats state of the art with an order of magnitude less traffic. Both
suggest a well-designed team is far less comms-hungry than a naive one, which bears directly on where
the crossover sits.

**Intermittent connectivity as a design target.** Hollinger and Singh 2012 (`10.1109/TRO.2012.2190178`,
periodic instead of continuous connectivity, plus an inapproximability result), Kantaros and Zavlanos
2017 (`10.1109/TAC.2016.2626400`, intermittent connectivity as a temporal-logic requirement), Wu,
Zilberstein, Chen 2011 (`10.1016/j.artint.2010.09.008`, online Dec-POMDP planning under a periodically
unavailable channel), Karabag, Neary, Topcu 2022 (`10.65109/iuha8463`, AAMAS, minimum-dependency
policies hold performance when comms drops while the baseline loses 20 percent).

**DOI cross-check worth recording.** The `10.65109/` prefix is a legitimate registered AAMAS
proceedings prefix, confirmed at CrossRef. A sibling agent rejected the prefix as a placeholder; that
rejection was overcautious. Separately, an OpenAlex title search conflated this work with an IJCAI 2025
paper by Soudijani and Dimitrova (`10.24963/ijcai.2025/30`), a different paper by different authors on
a related topic.

**Realism check.** Selden et al. 2021 (arXiv `2108.13606`) shows realistic RF mesh models limit
flocking and formation across 10 to 2,500 agents.

## D3: Decentralized control and consensus

**Foundations.** Tsitsiklis, Bertsekas, Athans 1986; Jadbabaie, Lin, Morse 2003
(`10.1109/TAC.2003.812781`, alignment despite changing neighbour sets, a switched linear system with no
common quadratic Lyapunov function); Olfati-Saber and Murray 2004; Fax and Murray 2004
(`10.1109/TAC.2004.834433`, a separation principle splitting formation stability into information flow
and per-vehicle control); Ren and Beard 2005.

**Rate and robustness.** Xiao and Boyd 2004 (`10.1016/j.sysconle.2004.02.022`, optimal averaging
weights via SDP substantially beat Laplacian heuristics), Boyd, Ghosh, Prabhakar, Shah 2006
(`10.1109/TIT.2006.874516`, gossip averaging time as a random-walk mixing time), Kar and Moura 2009
(`10.1109/TSP.2008.2007111`, a bias-variance dilemma under link failures and channel noise).

**Communicate only when worthwhile.** Tabuada 2007 (`10.1109/TAC.2007.904277`), Dimarogonas, Frazzoli,
Johansson 2012 (`10.1109/TAC.2011.2174666`), Heemels, Johansson, Tabuada 2012
(`10.1109/CDC.2012.6425820`, the reactive vs proactive tutorial), Nowzari, Garcia, Cortes 2019
(`10.1016/j.automatica.2019.03.009`, explicit about which triggers assume continuous monitoring). This
is the control-theoretic counterpart to D6's learned gating.

**The two hardware exceptions.** Rubenstein, Cornejo, Nagpal 2014 (`10.1126/science.1254295`, 1,024
physical robots) and Vasarhelyi et al. 2018 (`10.1126/scirobotics.aat3536`, 30 outdoor drones, where
idealized flocking failed until delays and comms limits were modelled, direct evidence for treating
comms realism as first-order).

**Flagged.** Fiedler 1973 (`10.21136/CMJ.1973.101168`): identifier verified, content unread (no
abstract in CrossRef, OpenAlex, or Semantic Scholar; dml.cz refused connection). Marked
UNVERIFIED-CLAIM.

## D4: Span of control, neglect tolerance, latency

**Delay behavior.** Ferrell 1965 (`10.1109/THFE.1965.6591253`): operators adopt move-and-wait, so
completion time becomes a function of open-loop move count. Sheridan 1993 (`10.1109/70.258052`): a
30-year review concluding the remedy for delay is predictive display plus higher-level local autonomy,
which is the project's thesis stated as a remedy three decades early.

**Capacity models.** Crandall et al. 2005 (fan-out), Crandall and Cummings 2007
(`10.1109/TRO.2007.907480`, metric classes predicting team size and autonomy level), Cummings and
Mitchell 2008, Lewis et al. 2010 (`10.1177/0018720810366859`, 4/8/12 robots, navigation is the binding
subtask).

**Latency effects.** Luck et al. 2006 (the key result, see I1), Chen, Haas, Barnes 2007
(`10.1109/TSMCC.2007.905819`, a 150-plus paper review attributing teleoperation decrements to
bandwidth, time lag, and frame rate), Davis, Smyth, McDowell 2010 (`10.1109/TRO.2010.2046695`, variable
lag hurts more than fixed and predictive display recovers), Walker et al. 2012, Nunnally et al. 2012
(`10.1109/ICSMC.2012.6377723`, swarm supervision under bandwidth restriction), Lu et al. 2019.

**Could not verify.** French, Ghirardelli, Swoboda 2003 I/ITSEC bandwidth paper (no DOI, dropped).
Several specific numeric values inside Davis 2010 and Nunnally 2012, and per-mode NT/IT values in
Crandall 2005, could not be confirmed from accessible text.

## D5: Contested electromagnetic environment

### Tier A, peer reviewed

**Pang, Kendall, Clarke** (arXiv `2501.07743`) is methodologically the closest paper found anywhere in
this review: Monte Carlo mission-success envelopes against communication latency and availability,
deriving a maximum tolerable latency. **Felux et al. 2024** (`10.33012/navi.657`) measures real GNSS
jamming via ADS-B: 38.3 percent of eastern-Mediterranean flights affected with daily peaks near 80
percent, 6.5 percent Black Sea, 0.35 percent Baltic. Usable calibration data. **Kerns et al. 2014**
(`10.1002/rob.21513`) is the live field capture of a hovering UAV by GPS spoofing. **Otsu et al. 2020**
(`10.1109/AERO47225.2020.9172537`) runs CoSTAR supervised autonomy under degraded links across four
one-hour DARPA SubT missions: real robots, real link degradation. **Targowski et al. 2026**
(`10.3390/s26154785`) measures a 12.2 pp packet-delivery-ratio gain from periodic hopping under
jamming. **Anbar Jafari and Anbarjafari 2026** (arXiv `2602.08477`) gives high-power-microwave C-UAS
kill probability 51.4 percent at 20 m falling to 13.1 percent at 40 m over 10,000 Monte Carlo trials.
**Li et al. 2023** (`10.23919/CSMS.2023.0003`) does adversarial air-defense siting against
reconnaissance drone swarms, close to UC-5's red side. **Morales-Ferre et al. 2020**
(`10.1109/COMST.2019.2949178`) is the reference interference-management survey. **Jarraya et al. 2025**
(`10.1186/s43020-025-00162-z`) finds no single sensor suffices for GNSS-denied UAV localization, vision
best. **Chaari 2025** (`10.35467/sdq/208347`) is a peer-reviewed case study of RF, laser, and HPM
counter-drone measures failing, framed around a roughly $1,000 drone against a $4M tank.

Actionable: Chaari 2025 is a citable anchor for the `cost_exchange` KPI, whose unit costs currently
default to 1.0 and therefore reduce it exactly to `loss_exchange`.

### Tier B, grey literature, not peer reviewed

**Watling and Reynolds 2023** (RUSI, *Meatgrinder*) reports Ukrainian UAV losses at approximately
10,000 per month and EW density near one major system per 10 km of front. **Watling and Bronk 2024**
(RUSI) supplies the receiver-versus-seeker mechanism behind I10. **CRS R48477, Gettinger 2025** gives
the DOD counter-UAS baseline, the stated objective of reducing the cost imbalance, and the criticism
that nonrealistic test targets overestimate C-UAS effectiveness.

**Miscitation trap.** The widely-quoted RUSI figure of roughly 10,000 Ukrainian UAV losses per month is
*not* attributed to EW in the source. Citing it as an EW-attrition number overreads it.

**Flagged and not found.** Plichta 2025, RUSI Journal (`10.1080/03071847.2025.2527923`): DOI verified,
abstract paywalled, marked UNVERIFIED-CLAIM. Not found: any open EW-versus-kinetic loss attribution
split, and any study crossing control modality against a jamming ladder.

## D6: Multi-agent RL and learned communication

**Complexity backbone.** Bernstein et al. 2002, Goldman and Zilberstein 2004, Pynadath and Tambe 2002,
plus Oliehoek and Amato (`10.1007/978-3-319-28929-8`) as the standard reference.

**Learned protocols.** Foerster et al. 2016 (arXiv `1605.06676`, RIAL and DIAL, backpropagating through
a noisy channel at training time) and Sukhbaatar et al. 2016 (arXiv `1605.07736`, CommNet).

**When, and to whom.** Jiang and Lu 2018 (arXiv `1805.07733`, ATOC, attention learns when
communication is needed and all-to-all hurts at scale), Das et al. 2019 (arXiv `1810.11187`, TarMAC,
learns whom to address), Singh et al. 2019 (arXiv `1812.09755`, IC3Net, a learned binary gate; when to
talk is scenario-dependent), Kim et al. 2019 (arXiv `1902.01554`, SchedNet, learned medium access under
a shared contended channel, 32 to 43 percent over baselines).

**Bandwidth and loss.** IMAC, TMC, and Tung et al. 2021 (`10.1109/JSAC.2021.3087248`, folds the noisy
channel into the MA-POMDP and shows joint beats separate design).

**Adversarial.** Tu et al. 2021 (`10.1109/ICCV48922.2021.00767`): indistinguishable adversarial
messages severely degrade teams, though the effect dilutes as the benign agent count grows. This is the
closest analogue to a spoofing attack on UC-7's believed-track layer.

**Delay and robustness.** Yuan et al. 2023, DACOM (`10.1609/aaai.v37i10.26389`): delay-oblivious
communication actively harms collaboration, and how long to wait is itself a policy. Li et al. 2025
(arXiv `2510.11824`), the 82,620-run study behind I1.

**Benchmark-versus-operational caveat.** 9 of the core 14 are validated only on particle worlds,
traffic-junction gridworlds, or StarCraft micromanagement. The qualitative direction transfers; the
numbers are not operational evidence. Only the two complexity results transfer by proof.

**Gap.** No dedicated study of learned MARL coordination under military RF jamming exists. Jamming
searches returned only radio-resource-management work.

## D7: Adjustable autonomy and trust

**Autonomy level as the decision variable.** Scerri, Pynadath and Tambe 2002 (`10.1613/jair.1037`) is
structurally the same problem as the centerpiece: transfer-of-control strategies solved as MDPs, where
autonomy is the decision variable, transfers carry coordination cost, and the optimal strategy is
solved against environmental uncertainty. Miller and Parasuraman 2007 (`10.1518/001872007779598037`)
recasts "level of automation" as a delegable pattern of roles (Playbook) rather than a rung on a
ladder, which pairs with Bradshaw's warning in D1. Sellner et al. 2006 (`10.1109/JPROC.2006.876966`)
shows empirically that sliding autonomy beats both endpoints. Feigh et al. 2012
(`10.1177/0018720812443983`) gives the taxonomy of adaptive-system triggers.

**Consequence for the contribution.** Taken together, this literature already predicts an interior
optimum in autonomy level. So the contribution is not that an interior optimum exists, it is that the
optimum moves with the comms ladder. That is a narrower and much more defensible claim.

**Trust theory and measurement.** Lee and See 2004 (`10.1518/hfes.46.1.50_30392`) is the decomposition
behind I11. Jian, Bisantz and Drury 2000 (`10.1207/s15327566ijce0401_04`) is the 12-factor trust scale.
Hoff and Bashir 2015 (`10.1177/0018720814547570`) separates dispositional, situational, and learned
trust. de Visser et al. 2020 (`10.1007/s12369-019-00596-x`) covers longitudinal calibration,
relationship equity, and trust dampening versus repair.

**Reliance behavior, directly relevant to engineered veridicality.** Wickens and Dixon 2007
(`10.1080/14639220500370105`) find a reliability crossover at 0.70, below which automation is worse
than none. Dixon, Wickens and McCarley 2007 (`10.1518/001872007X215656`) find false alarms hurt more
than misses, and that compliance and reliance are not independent. Parasuraman and Manzey 2010
(`10.1177/0018720810376055`) treat complacency and automation bias as one attentional phenomenon.
McGuirl and Sarter 2006 (`10.1518/001872006779166334`) show per-case confidence beats aggregate
reliability for calibration, and Zhang, Liao and Bellamy 2020 (`10.1145/3351095.3372852`) report that
confidence-based calibration alone did not improve joint performance.

**Design implication.** Because false alarms and misses affect reliance asymmetrically (Dixon 2007),
the dial-able agent error rate should expose the false-alarm / miss split, not a single scalar error
rate. Otherwise the trust measurements average over the asymmetry that drives the behavior.

**Could not verify.** Cohen, Parasuraman and Freeman 1998 (no DOI; the apparent origin of
"resolution"). NASA TM-20205003378, Chancey and Politowicz 2020 (no DOI; the clearest plain-language
statement of the idea). Mostafa 2017, Bradshaw 2004, Zuniga 2014: DOIs verified but abstracts
unreadable, marked UNVERIFIED-CLAIM. Lee and See 2004 full text is paywalled; the definitions were
confirmed through three secondary sources, but a page anchor needs journal access.

## D8: Reinforcement learning algorithms

**Algorithm baselines, with the honest caveats.** Schulman et al. 2017, PPO (arXiv `1707.06347`) claims
a "favorable balance between sample complexity, simplicity, and wall-time", not dominance. Haarnoja et
al. 2018, SAC (`10.48550/arXiv.1801.01290`) claims "very similar performance across different random
seeds." **No canonical PPO-versus-SAC head-to-head exists, so do not cite one.** Andrychowicz et al.
2020 (`10.48550/arXiv.2006.05990`) mapped more than 50 design choices across 250,000 trained agents,
and Engstrom et al. 2020 (`10.48550/arXiv.2005.12729`) found code-level details, not the algorithm,
cause most of PPO's gain over TRPO.

**Curriculum and environment design.** Narvekar et al. 2020 (`10.48550/arXiv.2003.04960`) is the
curriculum-RL survey. Dennis et al. 2020, PAIRED (`10.48550/arXiv.2012.02096`), Jiang et al. 2021, Dual
Curriculum Design (`10.48550/arXiv.2110.02439`), and Parker-Holder et al. 2022, ACCEL
(`10.48550/arXiv.2203.01302`) are the unsupervised-environment-design line behind I12. OpenAI 2019,
automatic domain randomization (`10.48550/arXiv.1910.07113`), and Tobin et al. 2017
(`10.1109/IROS.2017.8202133`) cover randomization-driven transfer.

**Multifidelity and sim-to-real.** Cutler et al. 2015 (`10.1109/TRO.2015.2419431`) gives
sample-complexity proofs for multifidelity simulators. Kaufmann et al. 2023
(`10.1038/s41586-023-06419-4`) is the existence proof that sim-trained RL can beat human champions, in
drone racing.

**Robustness.** Pinto et al. 2017, RARL (`10.48550/arXiv.1703.02702`): an adversarially trained agent
beats the baseline even when the adversary is removed at test time. Zhang et al. 2020
(`10.48550/arXiv.2003.08938`): the state-adversarial MDP, and naive adversarial training fails in RL.

**Evaluation methodology, which is why I12 lands as it does.** Henderson et al. 2018
(`10.1609/aaai.v32i1.11694`) show seed and method variance make deep-RL results hard to interpret.
Agarwal et al. 2021 (`10.48550/arXiv.2108.13264`) show point estimates over few runs contradict proper
statistics, and recommend interquartile mean with intervals.

**Military-simulation specific.** Black and Darken 2023 (arXiv `2402.06694`) and Choi et al. 2022
(`10.1109/ACCESS.2022.3227797`). Knox et al. 2023 (`10.1016/j.artint.2022.103829`) on reward misdesign.

**Could not verify.** No canonical PPO-vs-SAC comparison. Sutton, Precup and Singh 1999 options paper:
DOI verified but abstract unretrievable, excluded as UNVERIFIED-CLAIM. No study directly comparing RL
against scripted behaviors in constructive military simulation. CleanRL JMLR volume and pages
unverified. Semantic Scholar API returned nulls throughout.

## D9: Optimization, design of experiments, and surrogates

**Multifidelity, the core finding.** Peherstorfer, Willcox and Gunzburger 2018 (`10.1137/16M1082469`)
and 2016 (`10.1137/15M1046472`), covered in I13. Kennedy and O'Hagan 2000 (`10.1093/biomet/87.1.1`)
give autoregressive co-kriging linking cheap and expensive codes. Forrester, Sobester and Keane 2007
(`10.1098/rspa.2007.1900`) add a noise-aware variance estimator. Huang et al. 2006
(`10.1007/s00158-005-0587-0`) give augmented expected improvement, which selects both location *and*
fidelity with cost inside the criterion. Poloczek, Wang and Frazier 2017 (arXiv `1603.00389`) handle a
cheap source with unknown region-dependent bias. Fernandez-Godino et al. 2019 (`10.2514/1.J057750`)
document low-fidelity data making surrogates worse.

**Bayesian optimization under noise and in batches.** Letham et al. 2019 (`10.1214/18-BA1110`) give
batch expected improvement under noisy observations, which is BoTorch's qNEI. Wang, Clark, Liu and
Frazier 2020 (`10.1287/opre.2019.1966`) choose q-EI batches jointly.

**How many replications.** Ankenman, Nelson and Staum 2010 (`10.1287/opre.1090.0754`) separate
intrinsic from extrinsic variance and show replications compete with design points. Chen, Lin, Yucesan
and Chick 2000 (`10.1023/A:1008349927281`) give OCBA, reporting a 20x speedup on 210 designs. Nelson et
al. 2001 (`10.1287/opre.49.6.950.10019`) screen before selecting when alternatives are many.

**The 300-replication question.** The literature challenges the *shape* of the allocation, not the
size. Equal allocation is dominated, screening should precede selection, and replications compete with
design points. The honest defense is that SandTable's compute is nearly free, so the efficiency loss is
not worth the added complexity. That defense fails in exactly one case: if 147 x 300 is used to *claim
a best design*, since fixed allocation carries no correct-selection guarantee.

**Common random numbers.** Glasserman and Yao 1992 (`10.1287/mnsc.38.6.884`) establish when CRN is
provably beneficial. Chen, Ankenman and Nelson 2012 (`10.1145/2133390.2133391`) find CRN *hurts*
prediction while helping gradient estimation. SandTable's byte-identical-when-disabled discipline is
still correct for the additive-diff proof, but should not be assumed to improve the metamodel.

**Sensitivity.** Morris 1991 (`10.1080/00401706.1991.10484804`) elementary effects; Saltelli et al. 2010
(`10.1016/j.cpc.2009.09.018`) total-index estimators and their dimension-dependent cost.

**Could not verify.** SALib's own method list (UNVERIFIED-CLAIM). Any multi-fidelity precedent in
military or combat simulation: none found, a possible novelty claim. Letham 2019 page range. Proceedings
DOIs and pages for five NeurIPS/ICML/UAI entries (arXiv DataCite DOIs used instead). Sobol' 2001 verbatim
abstract (paraphrase only). A closed-form optimal replication count under heteroscedastic GP noise.

## D10: Agent-based combat simulation as a method

### Tier A, peer reviewed

Multi-resolution modeling: Davis and Hillestad 1993 (`10.1145/256563.256913`, the origin of
variable-resolution "families of models"), Davis 2000 (`10.1109/WSC.2000.899731`, MRMPM as the enabler
of uncertainty-spanning exploratory analysis), Davis, Bigelow and McEver 2000
(`10.1109/WSC.2000.899734`), Davis and Tolk 2007 (`10.1109/WSC.2007.4419682`, layering syntax,
semantics, pragmatics, assumptions, validity), Ahner, Buss and Ruck 2007 (`10.1109/WSC.2007.4419742`),
Petty, Franceschini and Panagos 2012 (`10.1002/9781118180310.ch25`), Rabelo et al. 2025
(`10.3390/info16080635`, current review treating ABM as an MRM approach), Reynolds, Natrajan and
Srinivasan 1997 (`10.1145/259207.259235`), Hyun et al. 2025 (`10.52682/jkidt.2025.7.4.028`).

Validation and credibility: Balci 1997 (`10.1145/268437.268462`, 77+ V&V techniques), Oberkampf et al.
2004 (`10.1115/1.1767847`), Owen and Chakrabortty 2024 (`10.1177/15485129221134632`), Collins et al.
2024 (`10.18564/jasss.5258`), Lee et al. 2020 (`10.3390/info11100480`, PRISMA review), Jee et al. 2020
(`10.1177/1548512920966107`).

### Tier B, grey literature, not peer reviewed

RAND MR-1004-DARPA (Davis and Bigelow 1998, introduces a consistency measure across resolutions),
RAND MR-1750-AF (Bigelow and Davis 2003, the "valid, subject to the principal assumptions, for
exploratory analysis" verdict), RAND MG-101-OSD (Davis and Anderson 2004), DoDI 5000.61 (17 Sep 2024)
and DoDM 5000.102 (9 Dec 2024). Edmonds and Hales 2003, JASSS 6(4)11, is peer reviewed but has no DOI.

### The credibility gap

Beyond the reproducibility and Lanchester checks SandTable already performs, the binding requirements
are: a written statement of specific intended use with acceptability criteria fixed *in advance*;
numeric validation metrics rather than monotonicity plots; uncertainty quantification split into
statistical and systematic components; an explicit range-of-conditions and extrapolation statement;
and DoDM 5000.102's non-circularity rule, that ProjectGL runs used to calibrate cannot also validate.

Two gifts from current policy: DoD policy explicitly names high-fidelity model comparison as a valid
substitute for live data, which licenses the whole validation approach for a project that will never
get live trials; and it names structural validation, which maps onto the AFSIM-style component model.

**Could not verify.** SISO Fidelity ISG / Roza; MORS Phalanx; NASA-STD-7009A revision letter (cited
indirectly via `10.2514/6.2009-1011`); MIL-STD-3022 full text; DoD VV&A RPG edition; any NPS or TRAC
MANA-versus-high-fidelity comparison. The OpenAlex budget was exhausted mid-search.

## D11: Red and blue behavior policies

### Tier A, peer reviewed

Behavior representation: Colledanchise and Ogren 2017 (`10.1109/TRO.2016.2633567`), Iovino et al. 2022
(`10.1016/j.robot.2022.104096`), Biggar, Zamani and Shames 2021 (`10.1109/LRA.2021.3074337`) and 2022
(`10.1145/3511606`). All four covered in I15.

Intelligent adversary: Brown, Carlyle, Salmeron and Wood 2006 (`10.1287/inte.1060.0252`), Golany et al.
2009 (`10.1016/j.ejor.2007.09.001`), Merrick and Parnell 2011 (`10.1111/j.1539-6924.2011.01590.x`),
Brown and Cox 2011 (`10.1111/j.1539-6924.2010.01492.x`), Guikema 2012
(`10.1111/j.1539-6924.2011.01737.x`, four necessary conditions for adversary models), Bier, Oliveros and
Samuelson 2007 (`10.1111/j.1467-9779.2007.00320.x`), Roberson 2006 (`10.1007/s00199-005-0071-5`). All
covered in I14.

Adaptive opponents: Spronck et al. 2006 (`10.1007/s10994-006-6205-6`, dynamic scripting, an
online-adaptive opponent from a weighted rulebase), Vinyals et al. 2019 (`10.1038/s41586-019-1724-z`, a
league of adapting counter-strategies).

Deception: Zhuang and Bier 2011 (`10.1080/10242694.2010.491668`, truth, secrecy and deception
equilibria), Zhuang, Bier and Alagoz 2010 (`10.1016/j.ejor.2009.07.028`, multi-period signaling where
the attacker updates on both signals and contest outcomes). These are the formal counterpart to the
believed-track and decoy layer.

CGF practice and behavior validation: Jones et al. 1999 (`10.1609/aimag.v20i1.1438`, TacAir-Soar flew
all US fixed-wing aircraft in STOW-97), Wray et al. 2005 (`10.1609/aimag.v26i3.1828`, a six-requirement
rubric for synthetic adversaries), NRC (Pew and Mavor) 1998 (`10.17226/6173`, behavior realism is the
binding constraint), Hingston 2009 (`10.1109/TCIAIG.2009.2032534`, the BotPrize behavioral Turing test).

### Tier B, grey literature, not peer reviewed

JP 3-13.4 Military Deception (the doctrinal "see, think, do" framing plus counterdeception), RAND
RR-A161-1 (Davis et al. 2021, a best-estimate Red "often proves wrong"), Isla 2005 GDC (tuning behavior
priorities is "almost impossible" past roughly 20 behaviors).

**Could not verify.** Whaley 1982 (DOI good, no abstract exists, content UNVERIFIED-CLAIM); DSB 2003 red
teaming ADA430100 (DTIC unreachable all session); any study quantifying scripted versus adaptive red in
mission-level combat simulation; OneSAF primary documentation; NPS theses via DTIC.

## D0: Seed set and the Vinitsky cluster

Covered in I4 and I9. One item needs explicit handling.

**Not citable.** The MathWorks "Train Multiple Agents for Area Coverage" page is vendor documentation
with no DOI and no verifiable empirical claim. It stays useful as a reference implementation of
multi-agent area coverage, which is structurally UC-5, but it cannot support a claim.

The citable anchor for that task is **Cortes, Martinez, Karatas, Bullo 2004**
(`10.1109/TRA.2004.824698`), already in the Zotero library as the 2002 ICRA version (item `8JQW9BFP`).
It establishes that near-optimal coverage is reachable with local information only, which is the formal
reason a sensor swarm should degrade gracefully rather than catastrophically as the shared picture
thins.

Also verified from the seed set: Tan 1993 (I4), Busoniu, Babuska and De Schutter 2010
(`10.1007/978-3-642-14435-6_7`, MARL taxonomy and the exponential joint-action-space barrier),
Papoudakis, Christianos, Rahman and Albrecht 2019 (arXiv `1906.04737`, non-stationarity, which worsens
under a degraded link because agents cannot observe each other's policy shifts), Vinitsky et al. 2022
Nocturne (arXiv `2206.09889`, partial observability as the interesting regime), and Yu et al. 2022
MAPPO (arXiv `2103.01955`, the default cooperative baseline).

---

# What to do next

1. **Cite Luck et al. 2006 and reposition the contribution.** Highest priority. Extending, not
   discovering.
2. **Add Giachetti et al. 2013 as the methodological ancestor.** Converts a novelty assertion into a
   lineage.
3. **Consider restructuring C0-C5 to degrade what is shared, not only how well.** Largest payoff in
   interpretability (I4).
4. **Map ladder rungs to algebraic connectivity** to give the crossover a theoretical locus (I2), with
   the asymptotic-theory caveat stated.
5. **Soften the EW-immune link to a swept parameter,** flattening rather than immunity (I10).
6. **Anchor `cost_exchange` unit costs** to Chaari 2025 rather than leaving them at 1.0.
7. **Re-run the Zotero semantic sweep after reindexing.** Several items returned 404, so the library
   likely holds more than this pass surfaced.
8. **Rename the trust metric to trust resolution** per Lee and See 2004, and scope the claim as a new
   operationalization rather than a new construct (I11).
9. **Expose the false-alarm / miss split** in the dial-able agent error rate, since the two affect
   reliance asymmetrically (Dixon et al. 2007).
10. **State the automotive-to-military transfer caveat** wherever the Vinitsky cluster is used.

From the algorithms and simulation-method sweep:

11. **Run overlapping designs in both tiers and report the correlation.** Cheapest high-value
    experiment in this review. It converts the two-tier design from motivation into justification
    (I13), and it is the input to the analytic high-fidelity budget result.
12. **Split those overlapping ProjectGL designs into calibration and held-out validation sets now.**
    DoDM 5000.102 forbids using the same runs for both. Cheap to do up front, expensive to retrofit.
13. **Reframe the two tiers as multi-information-source, not a fidelity hierarchy.** SandTable is a
    different model, not a coarsened Unreal run (I13).
14. **Replace the static red force with 3 to 5 doctrinal templates, each best-responding once.**
    Addresses the project's most-cited limitation, which is a structural bias rather than a
    conservative approximation (I14).
15. **Do not learn blue behaviors with RL. Apply RL to scenario generation instead** via PLR-perp,
    which needs only a scoring rule over missions already running (I12).
16. **Check how the paper phrases its optimum.** Fixed 147 x 300 allocation carries no
    correct-selection guarantee, so it cannot support a claim that a particular design is best (D9).
17. **If migrating to behavior trees, budget for the blackboard.** BTs are not a free superset of
    FSMs, and recovering the expressiveness costs the readability the migration was for (I15).
18. **Write the specific-intended-use statement and acceptability criteria in advance,** and add
    numeric validation metrics rather than monotonicity plots (D10 credibility gap).
