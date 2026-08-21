# Autonomy Under Degraded Comms

Literature synthesis for SandTable (VIPR-GS FP6111). Searched 2026-08-21 across seven parallel
dimensions plus a user-supplied seed set, against CrossRef, OpenAlex, arXiv, Semantic Scholar, and
the local Zotero library. Roughly 183 verified provenance lines.

Every entry carries a resolved DOI or canonical arXiv ID, a recorded verification source and date,
and a claim read from the abstract rather than inferred from the title. Where a claim could not be
verified, that is stated rather than smoothed over. Nothing here enters `report/ref.bib` until it
passes `report/tools/audit.py` check 1.

Companion artifact: https://claude.ai/code/artifact/b0026bed-931a-481c-ae4b-22497509774a

**Evidence grades used below.** *Strong* means multiple independent literatures or a proof.
*Partial* means real but bounded (asymptotic theory, or a domain that does not fully transfer).
*Thin* means the claim outruns the peer-reviewed record.

---

# Part 1: Important Ideas

Eleven ideas, ordered by how much each changes what the project should build or claim.

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

---

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
Robotic Follower ATD, leader-follower as the near-term autonomy hedge. Nahavandi et al. 2022
(`10.1109/ACCESS.2022.3147251`) surveys convoying and notes human-in-loop decisions add delay relative
to automated ones. Andersson et al. 2025 (`10.1002/rob.22442`) reports a 16-battle virtual experiment
in which UGVs directed by a single soldier stalled a mechanized company in three of four battles.

**Bandwidth as forcing function.** Guivant et al. 2012 (`10.1002/rob.21432`) spans teleoperation to
point-and-click autonomy in one architecture with bandwidth and latency as the governing axis. Pace et
al. 2014 (`10.1117/12.2050394`) shows dense sensor reconstructions exceed real-time wireless capacity,
forcing onboard scene condensation. Autonomy is partly a bandwidth consequence.

**Currency flag.** CRS IF11876 states the Army's one-operator-many-RCVs aspiration and records the
1 May 2025 halt of the RCV program. If the paper motivates itself via RCV, that halt must be
acknowledged. No canonical peer-reviewed DARPA RACER paper exists.

**Could not verify.** TRADOC RAS Strategy 2017 (no reachable official .mil URL), Army Science Board
FY2016 RAS study, SMET (no DOI-bearing work), ExLF/AMAS (trade press only). The agent hit HTTP 429 on
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
