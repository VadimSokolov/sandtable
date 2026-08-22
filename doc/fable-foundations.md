# Foundations review (Fable, 2026-08-22)

Brief from the project owner, superseding round-6 Q5 to Q7: question everything, attack the
foundations, and say what would make SandTable a highly useful simulator rather than a defensible
one. Standing on six rounds of adversarial review recorded in `doc/fable-review.md`. Read for this
round: `README.md`, `report/main.tex` (all thirteen results subsections plus Discussion),
`doc/sandtable-todo.md`, `doc/lit-ideas.md` (I5, I13 in full), the module inventory, and one new
probe run today (`r6_crossing.py` in the session scratchpad, 1,280 missions at n = 5, rung 3, step
clock, retry; its numbers appear under F5). No runlogs of still-running registered jobs were read.

## The five verdicts in one screen

- **F1.** SandTable is a queueing kernel plus a mission pricing engine plus a demo library. The
  kernel discovers, the pricing engine converts queue states into mission currency and has
  empirically earned its keep four times in six rounds, and the demo library is scenery that is
  currently dressed as results. Do not delete the ABM. Delete the pretense that thirteen results
  subsections are peers, and run the one battery that would fuse the two halves.
- **F2.** Verification exists and is above average; validation does not exist at all, and no amount
  of tuning creates it. The rescue is that every gated claim is secretly a claim about three
  dimensionless ratios, each of which has a published measurement literature. There is a real
  four-step program, no hardware required for three of the steps, and your own lit review (I13)
  already names the keystone measurement.
- **F3.** On Monday the PM can buy two things: a pruned human-in-the-loop test matrix for
  objective 3, and the sentence "console admission control before radio upgrade." That is
  non-empty but modest. The smallest change that makes it real is a calibration-ingest script that
  turns operator logs into (mu, P, tau, d) and emits the model's predictions for that population.
- **F4.** Ranked by decision impact: (1) the operator is an infallible oracle and the modality
  axis is a gain knob, which your own todo file already indicts; (2) demand is open-loop, with no
  surge at contact, which is the case doctrine actually cares about; (3) mission success is a
  threshold readout of a scripted advance, and it is quietly manufacturing nulls and interior
  maxima in the gated results today. Trust and adaptive red rank below all three.
- **F5.** The lever is real, but it is the classical retrial-queue stability condition wearing HMT
  units. The transferable product is the inequality and its adaptive form (backoff doubling), never
  the number 15.33. Your own jitter-flat result is the proof of mechanism: a booked queue punishes
  rate, not coincidence.

---

## F1. Simulator, or a queue with scenery?

### The audit

| subsection | evidence class | closed-form predicted | adversarially tested |
| --- | --- | --- | --- |
| queue | full-tier gated contrasts | yes, before measurement | six rounds |
| band | full-tier gated contrasts | yes, before measurement | six rounds |
| centerpiece | polarisopt sweep, 44k reps | partially (direct arm is the queue) | no |
| uc3 frontier | polarisopt sweep | no | no |
| uc5 swarm | polarisopt sweep | no | no |
| killweb | demo means, opt-in | no | no |
| drone | demo means, opt-in | hazard form only | no |
| personality | demo means, opt-in | no | no |
| bayes_te | analysis layer, stipulated utilities | n/a | no |
| validation | verification battery | Lanchester anchor | n/a |

The uncomfortable fact is real but the diagnosis is backwards. Everything sharp lives in one file
because sharpness was only ever demanded of one file. The queue is not the most important
subsystem; it is the only subsystem that was ever asked a falsifiable question at full tier. The
model did not collapse to a queue. The review process did, because it optimized for attackable
claims and only the queue offered any. That is a property of the claims, not of the code.

### What the agent-based layer is actually for, with receipts

The fair test of "queue with scenery" is whether the ABM ever changed an answer that queue
arithmetic got wrong. It did, four times, and twice the person it embarrassed was me:

1. Round 1: reasoning from the queue alone, I concluded notification was worth approximately
   zero. Under teleoperation physics (a behavior-layer property) it is +0.0801 at t = 4.97. The
   pricing of a stopped vehicle is not a queue quantity.
2. Round 3: the q_stall sweeps run in opposite directions under published and teleop physics
   because stalled vehicles still fight, so q_stall prices engagement exposure. No queueing model
   contains that sign flip.
3. Round 4: terrain-coupled demand moved the fold-band edge exactly as registered (gated at n = 5
   only). The coupling runs through the world model.
4. Today: at n = 5 the queue degrades smoothly in L (goodput 0.494 down to 0.157) while mission
   success holds flat and then breaks. The transfer function from queue state to mission outcome
   is nonlinear and threshold-shaped, and it is the ABM that supplies it.

So the honest architecture statement is: the closed forms are the discovery engine, the ABM is the
pricing engine that converts server states into mission currency, and predictability of the first
by hand is a feature, not an indictment. A mission simulator whose C2 core reduces to auditable
queueing theory is more trustworthy to a sponsor than one that does not, provided the paper says
this out loud instead of hoping nobody notices.

### The (b) answer, which was requested and is deserved

At the results-section level the model is over-claimed, not over-built. The cut list:

- **personality**: a movement-style demonstration with no decision content. One paragraph inside
  verification (it is a face-validity check that the propensity mode recovers the scripted
  corridor), or an appendix. Not a results subsection.
- **bayes_te**: methods, not results. It analyzes the simulator's output; it does not simulate.
  Move it to the methods side and it gets stronger, because as a "result" it invites the question
  of what was discovered, and the answer is nothing, it is a paradigm demonstration.
- **killweb + drone**: merge into one "mechanism library" subsection whose explicit claim is
  breadth-with-discipline (opt-in, byte-identical off, one falsifiable demo each). Keep the
  counter-UAS interior optimum as the only headline, since it is already correctly scoped as a
  mechanism demonstration.
- Keep as results: uc3, centerpiece, queue, band, uc5. Five defensible results, one mechanism
  library, one methods section. Nothing deleted from the code; the library is the testbed product.
  Everything demoted in the claims.

### The battery that dissolves the question

The centerpiece's direct-control surface should be predictable from the queue plus link arithmetic:
success_direct(n, rung) is priced link failure (1 - d(rung)) plus queue state (n against
n*(rung) = c mu Lambda / d(rung)), fed through the pricing layer. Overlay that predicted crossover
contour on the measured phase diagram (`fig:cp_phase`). If it lands, the paper's two halves fuse:
the moving optimum IS the collapse threshold moving with d, and "queue with scenery" inverts into
"the scenery was the queue all along, and we can prove it." If it misses, you have located the
first thing the ABM knows that the closed form does not, which is worth a subsection by itself.
Cost: analytic curve plus CSVs that already exist. This is the single highest-value cheap battery
available to the project right now.

## F2. Validation, stated without anesthesia

What exists is verification: purity, byte-identity gates, monotonicity, extreme conditions, and a
Lanchester cross-check. Real, above the field's average, and not validation. No parameter has an
external anchor. The Discussion already concedes "set, not measured" and "comparative, not
predictive," which is necessary and insufficient, because a reader currently discovers the
epistemic status of every number from a limitations paragraph three pages after believing it.

### The rescue is dimensional

The entire gated corpus depends on the parameters only through dimensionless ratios:

    n* d / c = mu P + mu tau + mu        (collapse span)
    band edges: mu P, mu tau, mu rho, pi, d
    backoff floor: mu rho against mu tau, c
    latency ceiling: mu P, mu lat

mu = 0.15, P = 20, tau = 22 are six arbitrary-looking numbers that are actually two ratios: patience
is 3.0 services long, the decision cadence is 3.3 services long. Those two ratios plus d are the
whole calibration surface of the queue story, and each has a measurement literature:

- 1/mu is interaction time (IT) in the fan-out literature; MAGIC 2010's 4.25 interactions per
  minute and the Crandall/Olsen IT measurements are direct anchors.
- P is neglect tolerance (NT): the neglect-tolerance curve is precisely "how long unattended
  before unacceptable," which is what patience does in this model.
- tau is consultation cadence, same sources.
- d is a radio property, measurable on the GFE simulator's link model today.

### The minimum credible program, in order

1. **Provenance table** (a week, no hardware). Each ratio mapped to two or three published ranges,
   with the model's point shown inside or outside. Label it consistency, not calibration.
2. **Retrodiction** (the first believable number, no hardware). Take the published saturation
   studies already in ref.bib and lit-ideas (Olsen and Wood; Crandall et al. 2005, which is
   measured on hardware; Cummings and Mitchell 2008; the MAGIC logs). Map each study's measured
   IT and NT into (mu P, mu tau), let Equation nstar predict that study's observed capacity
   plateau, and report the error with nothing fitted. If the model, fed ratios measured by other
   people on real operators, lands the observed 4-to-8-asset plateau, that is validation of the
   only kind this model can have. If it misses, you learn which term is wrong, which is also the
   product.
3. **The I13 measurement** (the keystone; needs only the GFE simulator). Run overlapping designs
   in both tiers and report correlation and rank agreement, with the calibration/validation split
   DoDM 5000.102 requires, designed in from the start. Your own lit review calls this the most
   concrete and cheapest experimental recommendation it makes, and it is the only thing that turns
   "screening tier" from a hope into a claim. Use I13's framing correction too: SandTable is a
   different model, not a coarsened ProjectGL, so multi-information-source is the defensible
   frame and "fidelity ladder" invites a question with no answer.
4. **Ordering robustness** (compute only). The Extensions section already promises Morris/Sobol
   over operator and ladder parameters. Aim it at the right target: score orderings and crossover
   existence across the plausible box of the three ratios, not output variance. A finding that
   holds its sign over the whole box (fold-band existence, policy ordering, jamming-relieves,
   backoff rule form) gets promoted; one that does not stays screening-grade.

### The honest reframe, said plainly

Yes: without steps 2 and 3, every absolute number in the paper is qualitative and will remain so
regardless of tuning, because tuning against nothing is not calibration. The paper survives this
honestly by tiering its claims in the abstract, not the limitations: Tier A, mechanism existence
and design orderings (defensible today); Tier B, threshold locations in dimensionless units
(defensible after retrodiction); Tier C, absolute success rates (explicitly not offered). Every
results subsection gets a tier tag. This costs a paragraph and buys the paper its integrity.

## F3. What the sponsor is buying

### The Friday-to-Monday test, answered without flattery

No doctrine decision, no staffing number, no radio specification follows from the current paper.
Two decisions do follow:

1. **Pruning the objective-3 HITL matrix.** The full grid (C0-C5 x modality x span x policy x
   reliance x backoff) is unaffordable in human-subject hours, and SandTable's surviving results
   prune it with reasons: drop backoff-jitter arms (flat twice at two backoffs); drop
   burst-microstructure arms when no reliance loop is closed (K1 null at all eight spans); treat
   C-rungs as equivalence classes of round-trip d for direct control; spend the hours on policy,
   backoff length, reliance on/off, and spans bracketing the predicted threshold. Every pruned
   cell is real money. This is a decision a PM can sign Monday.
2. **Sequencing: console software before radio hardware.** Near the threshold, admission control
   dominates link improvement, and link improvement without admission control can backfire
   because more delivery is more offered load (gated twice, in the queue section and again in the
   coherence bonus sign). "Fix the console's booking discipline before buying link margin" is a
   defensible procurement ordering today, at Tier A.

If the answer had to be one sentence: the sponsor is buying a hypothesis generator whose
hypotheses arrive pre-falsified at the cheap tier, plus the test matrix that survived.

### The smallest change that upgrades the answer

A calibration-ingest path, about 200 lines and no new mechanisms: read an operator log
(timestamped requests, service starts and ends, abandonments; the HITL consoles will emit exactly
this), estimate (mu, P, tau, d) for that operator population, and print the predicted collapse
span, band edges, backoff floor, and policy deltas with intervals. That converts SandTable from a
paper about a hypothetical operator into a calculator the program points at its own logs, and it
is the natural Year-1 demo artifact connecting the two tiers.

## F4. What is missing, ranked by how much it changes a decision

1. **The operator is an oracle, and modality is a gain knob.** q_operator = 0.95 unconditionally:
   no error, no degradation under load, no rework, no skill state. Your own todo file has already
   written the indictment: the modality axis scales a quality gain, and "a model that cannot
   represent the division cannot study the teaming." Two consequences the paper does not state.
   First, the centerpiece crossover's existence is an assumption (q_operator exceeds q_auto by
   construction); only its location is a model output. Second, the supervisory-control literature
   repeatedly finds operator performance kneeing near seventy percent utilization, well before a
   queue saturates (verify the exact anchors through the citation workflow before quoting; the
   Tomahawk and ATC-queueing studies are the usual ones). This model's operator is flawless until
   the mathematics of the queue stops it, which systematically flatters direct control at every
   span below n*. And error under load is not decoration: errors generate rework, rework is
   demand feedback, and demand feedback is exactly the loop that produced the fold band. A
   quality droop q_operator(utilization) plus a rework probability is a c2.py-sized change and
   plausibly yields a second, earlier fold. A knowledgeable HRI reviewer flags this before
   anything else in the model.
2. **Demand is open-loop.** Requests arrive on private clocks plus a static terrain scalar.
   Nothing couples demand to the fight: no surge at contact, no common-cause burst when an ambush
   makes every vehicle call at once. Six rounds of comms work just demonstrated that this
   system's characteristic failure is synchronized arrivals (the fade-end resync); the same
   mechanism on the demand side is the operationally dominant case and it is absent. Under
   surge-correlated demand the effective capacity question becomes "can the crew absorb a surge
   of size k in one patience window," which is nearly independent of the open-loop n*, so
   doctrine read off n* is optimistic in exactly the situations that matter. The cheap version
   is one coupling term: contact events (already in the engagement layer) zero the
   decision-cooldown of vehicles in radius. Register the prediction that the collapse span drops
   toward the surge size and gate it.
3. **Mission success is a threshold readout of a scripted advance, and it is already shaping the
   gated results.** Today's probe: goodput falls smoothly from L = 4 while success sits flat and
   then breaks past L = 40. Interior maxima, low-span nulls, and knee locations in success space
   are partly properties of where the scripted advance crosses its threshold, not of the team.
   This threatens the FORM of existing claims, which is why it outranks realism items. The fix is
   free: gate claims on the MOE family (success, advance distance or time-to-objective,
   attrition, goodput) with sign consistency required, and expect several current nulls to move.
   The scripted advance itself can stay; the readout must stop being one bit.

Triage of the owner's own candidates: **trust** does not need a new module first; recognize that
retry_prob and the reliance loop already constitute the behavioral trust dial (over-reliance is a
tight retry, and the fold is its price), then make pi endogenous on outcomes later, in I11's
calibration-as-discrimination sense. **Adaptive red** is I14 and is real, but it changes every
subsection at once; it is the next paper, not a missing piece of this one. **Graceful autonomy
degradation** partially exists (q_auto, q_fallback); the missing part with consequences is time
structure, fallback competence decaying with time since last contact, which couples directly to
the burst results. One absence nobody listed: the console never **preempts**. Real consoles drop a
low-value consult mid-service when a critical one arrives; blind/refund/admit does not bracket a
preempting server, and preempt-resume is standard queueing with known machinery, so the claim
"policy bracket covers what a console might plausibly do" is soft until that arm exists. The
triage-null paragraph in the Discussion is honest that heterogeneity was absent by construction;
preemption is the same gap seen from the server side.

## F5. The backoff lever, tested hard

New evidence from today's probe (n = 5, rung 3, blind, retry pi = 1, rho = 4, 128 paired seeds),
alongside the owner's cohort and crossing numbers:

| arm | goodput | success vs bern_retry | 1 - abandon_link (= mean round trip d) |
| --- | --- | --- | --- |
| bern_retry | 0.494 | baseline | 0.650 |
| ge co L=28 | 0.322 | -0.008 (t -0.2) | 0.700 |
| ge co L=40 | 0.265 | -0.086 (t -1.6) | 0.718 |
| ge co L=120 | 0.157 | -0.125 (t -1.9) | 0.761 |
| ge marginal L=120 | 0.285 | -0.086 (t -1.8) | 0.666 |

Three things in that table matter for F5. The measured round-trip delivery in the collapsed cell
(0.761, and the owner's 0.764 at full tier) sits at the self-consistent value c mu (P+1+rho)/n =
0.750 that makes the jammed loop exactly critical, which is the signature of a load-governed state.
The reply-pinned arm retains roughly two thirds of the effect at L = 120, so the lever is not
acting through the round-trip bonus alone. And goodput degrades smoothly while success is
buffered, the F4 item 3 caveat, which applies to the lever's own -0.088 and -0.010.

### The mechanism is settled, and it is not synchronization

Jitter flat at two backoffs while backoff length moves the effect ninefold is the discriminating
pair: a booked queue integrates arrival rate and is indifferent to phase, where a contention
channel punishes coincidence. In ALOHA you randomize; at a console you defer. The operative
inequality is that the failure cycle must cover the team's per-crew service demand:

    P + 1 + rho  >=  n d / (c mu),   i.e.,   rho*  =  n d / (c mu) - (P + 1)

At n = 5, d near 0.78, rho* is about 5, which is why 12 kills the interaction and 4 does not.
Registered prediction: a rho sweep shows a knee near 5 to 8, not a gradual slide to 12. If the
decline is gradual, the load rule is wrong and something else deserves the credit.

### Two floors, and the paper currently ships the wrong universal

The Discussion's floor tau - 1/(c mu pi) = 15.33 closes the band at every span (it restores the
standing cycle; the DON'T form: impatient re-request is the pathology). The jam floor rho* above
is span-dependent and smaller at small teams. They scale differently (one in tau, one in n), they
answer different questions (bistability existence versus jam sustainability), and conflating them
invites a reviewer to break the rule with one counterexample at n = 5. State both, or state only
the conservative envelope and say it is an envelope.

### Is it transferable?

The form, yes; the number, no. The inequality is the retrial-queue/random-access stability
condition the band section already cites (Falin; Carleial), and forty years of fielded systems run
on its adaptive form. What is new is not the rule; it is the demonstration that the rule reaches
mission outcomes through a reliance loop, and that in an HMT stack the lever sits on the vehicle
(software) rather than the console (staffing). The number 15.33 is made of two chosen timescales
and dies with F2. The recommendation that removes the number entirely: an adaptive backoff arm
(double the hold on consecutive unanswered requests, reset on service). It finds the floor without
knowing n, d, mu, or c, pays no latency when the system is healthy, and is the form real systems
field. If it matches rho = 12 at every dwell while beating it at low load, ship the doubling rule
as the design recommendation and let 15.33 retire to a derivation. One caveat travels with every
version: P does double duty (client give-up and stall booking length), so the lever's importance
scales with mu P, and that ratio is currently chosen, not measured. The rule's fate is tied to F2
step 2.

## What the paper should say it is

A screening-and-mechanism tier for an HMT testbed, whose quantitative claims are dimensionless,
predicted before they are measured, and explicitly tiered by validation status; whose job is to
hand the expensive tier a pruned matrix and pre-falsified hypotheses; and whose Year-1 deliverable
is the two-tier correlation measurement that no one in the multi-fidelity literature will let you
skip. In that frame the queue is not an embarrassment of narrowness; it is the existence proof
that the workflow (conjecture, closed form, registration, gate, retraction when owed) produces
survivable results. The critique this review sustains is that only one subsystem has yet been put
through that workflow, and the fix is not more queue; it is the centerpiece contour overlay first,
the retrodiction table second, the adaptive-backoff arm third.
