# Adversarial review: the operator-queue result and four hard questions

Reviewer: Fable 5 (autonomous review agent), 2026-08-22.
Scope: repo at commit b2f73f7, branch autoresearch/aug12. Read in full: src/sandtable/c2.py,
metrics.py, behavior.py, comms_ew.py, sim.py, tools/queue_theory.py, doc/autoresearch-conjectures.md,
the queue-related sections of report/main.tex, scenarios/sc_span_control.json. Three new probes were
run for this review (no gated experiment was re-run, no repo file modified); scripts lived in the
session scratchpad and every probe is fully specified below so it can be reproduced from the
parameters given. All probe runs use sc_span_control with params overrides, seeds 0..255
(identical to proxy-tier blocks 0-15 x 16, seed-matched across arms).

Summary of verdicts, one line each:

- Q1: blind is a defensible worst case of a real protocol class, not a fiction, but the paper leans
  on the wrong contrast: the load-bearing fix is refund (the server-side discard), and the
  notification the Discussion recommends measures approximately zero. Keep the result, re-center it.
- Q2: not bistable, and n* is not a saddle-node. It is a boundary-equilibrium collision of a
  monotone scalar drift: unique attractor at every n, no coexistence, no hysteresis. Proved
  analytically and confirmed with a preloaded pure-queue replica.
- Q3: C7's test was decisive for the slope but never tested the headline; a new stall_eq x admit
  cell shows the headline survives at 57 percent of its size, so q_stall prices about 40 percent of
  the published-physics magnitude and none of the teleoperation magnitude. The semantics are
  coherent, with one real wart at C5.
- Q4: not a denominator artifact: interventions cancels exactly, fan_out is identically
  1/hold_fraction, and the flatness is the analytic floor 1 + (tau+1)/P. But one sentence in the
  paper ("never equals the true sustainable span") holds only for one of three possible bookings of
  wait time, and the model's own instrumentation computes a booking that lands on n* to 1 percent.
- Q5: closed-loop reliance (an adaptive ask policy, with retry as its dangerous variant). It is the
  client-side dual of queue_policy, it is the only listed gap that touches the headline mechanism,
  and its retry variant is the one mechanism that could make the collapse genuinely bistable.

## Q1. Is blind a straw man, and does the contribution survive if it is?

Verdict: blind is partly a straw man as a claim about consoles and not at all a straw man as a
claim about models. The contribution survives, but only under a framing the manuscript is currently
half-committed to, and one sentence of the Discussion crosses the line that framing defends.

### The attack, stated at full strength

A reviewer will say: no fielded console works a request whose requester drove off twenty seconds
ago. Any console that displays request age, plus a doctrinal timeout, implements refund for free.
So the realistic baseline is refund, and against refund your admission-control gain is not
+23.7 points, it is +2.4 points at proxy tier (0.840 vs 0.816, below your own full-tier MDE once
paired), and the paper's headline measures the distance between a coding artifact and a fix.

This attack is strong because the numbers back its second half. I ran the decomposition the paper
does not report, at n=8, C0, published physics, seeds 0..255, paired per-seed:

| arm | success | delta vs blind | paired t | goodput |
| --- | --- | --- | --- | --- |
| blind | 0.512 | | | 0.180 |
| refund | 0.816 | +0.305 | 11.4 | 0.797 |
| admit | 0.840 | +0.328 | 14.2 | 0.730 |

Refund carries 93 percent of the admit-blind gap. And under teleoperation physics
(blue_behavior=auto), where telling the vehicle should matter most because a waiting vehicle is
physically stopped, refund scores 0.703 and admit 0.695: the notification channel is worth nothing
measurable even there. The mechanism is visible in the goodput column: admit sends the refused
vehicle back into the request cycle after one round trip, which raises offered load and eats the
saved stall time as extra contention (goodput 0.730 vs 0.797). The two effects cancel at mission
level. So the specific interface feature the Discussion recommends ("a console that tells a
requester it will not be answered in time", main.tex line 422, and the ledger's "tell the vehicle
the operator cannot reach it, immediately") is exactly the part of admit that does no measurable
work. What does the work is the server not spending slots on expired requests.

### Why blind nonetheless describes something real

Three real systems are blind in this model's sense:

1. Store-and-forward tasking without expiry metadata. A request queue (RFI cell, message-based
   fires channel, DTN-style C2 under EW) where requests carry no TTL and the server has no shared
   state with the requester. The requester's timeout is local; the server cannot observe it.
   Working stale requests is exactly what such queues do.
2. Cancellation costs comms. Under jamming, a cancel message drops with the same probability as the
   request. A protocol that relies on the vehicle retracting its request degrades toward blind as
   p_drop rises. (Refund does not have this problem, which is precisely why refund is the strong
   baseline: it needs only a timestamp on the request plus knowledge of P and the return latency.)
3. Refund as coded is clairvoyant. c2.py computes wait = reply - k exactly at arrival because
   service is deterministic and latency known. A real console estimates whether its answer will
   arrive in time, under variable latency, and misestimates in both directions; every misestimate
   toward optimism is a blind slot. Real consoles sit between blind and refund, not at refund.

So the honest position: blind and admit bracket a real range, blind is the pessimistic end and the
no-metadata limit, refund is the achievable-with-timestamps point, and where a fielded console sits
is empirical. The manuscript already says most of this (line 431, and the ledger's "the one claim
not made"). That defence is sufficient for the modeling claim. It is not sufficient for the
Discussion's operational guidance, which presupposes fielded consoles are blind-like and then
attributes the remedy to the notification channel that measures zero.

### Is the shipped-with defence enough?

No, not alone. "It is what the model shipped with" concedes the bug framing: it explains why the
number exists, not why a reader should care. The framing that survives review has three legs, all
already in the repo, none dependent on blind being realistic:

1. The sign pathology (G2/G3). The published model class (capacity-limited operator server in the
   savla2012queue tradition, imported without abandonment-disposal semantics) predicts that jamming
   improves mission success at high span (+11.4 pp, t=7.3, 29/32). That is a wrong-sign EW response,
   and any EW tradeoff study run on such a model inherits it. Admission control reverses the sign
   (t=2.63, 23/32, the weakest gate in the set; the paper's "small but gated" phrasing is correct
   and should not be strengthened). This leg does not care whether consoles are blind, because the
   claim is about models, and models demonstrably are: blind is what one gets by coding "a server
   with a backlog" naively, which is how it got into SandTable.
2. The closed forms. The latency ceiling holds for every policy; n* is the blind collapse
   threshold and the simulator obeys both, plus the staffing multiples. These are structure, not
   bug repair.
3. The decision-relevant reversals: staffing vs admission as non-interchangeable levers, the
   ladder confound (latency monotone harmful, loss hump-shaped), the route-choice coupling.

Stated that way the contribution is: any fast mission model that includes a capacity-limited
operator and impatient clients silently chooses an abandonment-disposal semantic; the choice is
worth 20 to 74 points of mission success and flips the sign of the EW response at exactly the
operating points the model exists to explore; therefore the semantic must be an explicit, reported
modeling parameter, and here are the closed forms that say when it bites. That is falsifiable,
class-level, and does not require defending blind as a portrait of any console.

### What should change

- Add the refund decomposition to the paper (tab:queue_gate or the queue subsection text). The
  numbers exist at proxy tier in the ledger and reproduce exactly; a reviewer who knows Erlang-A
  will ask for this split within minutes of reading. Reporting refund is also self-protective: it
  shows the authors measured the gap between "worst case" and "achievable with timestamps" and did
  not hide that most of the headline lives there.
- Reweight the Discussion's ordered guidance (line 422). The load-bearing recommendation is: the
  console must not spend service time on requests that will expire before the answer lands, which
  needs timestamps and doctrine, not comms. The notification is a cheap extra whose measured
  marginal value here is +2.4 pp at published physics and -0.8 pp under teleoperation. As written,
  the guidance attributes the mechanism to the notification.
- Keep +23.7 pp, but label it consistently as the sensitivity of the published model to an
  undocumented semantic (equivalently, the worst-case cost of fielding a no-metadata tasking
  protocol), never as the expected fielded gain of an interface feature.

Demotion is not warranted. The result should be re-centered, not demoted: the sign reversal and the
closed forms are the headline; the +23.7 is the magnitude exhibit.

## Q2. Is the system bistable, and is n* a saddle-node?

Verdict: no and no. The blind queue as coded cannot be bistable; n* is the point where the unique
healthy equilibrium collides with the abandonment-saturation boundary and ceases to exist, a
boundary-equilibrium (border-collision) bifurcation of a piecewise-linear monotone flow, not a
saddle-node. There is no coexistence band and no hysteresis. The staggered-start sensitivity was a
transient, which the ledger's own 16-block check already showed (stagger moved goodput 0.01-0.05,
not 0.35). I confirmed all of this numerically with a preloaded replica.

### The analysis

Let B(k) = max(operator_free_at - k, 0), the backlog horizon in steps. At C0 (latency 0, d=1) an
arrival finding backlog B waits W(B) = B + 1/mu and abandons iff W(B) > P, i.e. iff B > B_c = P - 1/mu
= 13.33. Each agent's cycle is wait-then-cooldown: cycle(B) = min(B + 1/mu, P) + 1 + c with
E[c] = tau (the +1 is the adoption step in c2.step branch 1; the exact mean cycle at saturation is
P + tau + 1 = 43, so n* as coded is mu(P+tau+1) = 6.45 rather than the paper's 6.30; the sweeps
bracket 6-7 either way, but the +1 belongs in a footnote). Under blind, every delivered arrival
adds 1/mu to the backlog whether or not it will be serviced (c2.py line 305-306: _claim runs
unconditionally). So the fluid drift is

    dB/dt = n d (1/mu) / cycle(B) - 1.

cycle(B) is continuous, nondecreasing in B, and constant (= P + tau + 1) for B >= B_c. Therefore
dB/dt is continuous, nonincreasing in B, and constant beyond B_c. Three consequences:

1. At most one equilibrium (a nonincreasing scalar field crosses zero at most once, up to a flat
   segment), and it is globally attracting when it exists. No coexisting attractors at any n, so
   no bistability and no hysteresis, period.
2. The equilibrium exists iff the saturated drift is negative: n d/(mu (P+tau+1)) < 1, i.e. n < n*.
   As n -> n*, the equilibrium backlog B* = n d/mu - (1/mu + tau + 1) rises continuously to exactly
   B_c: the healthy branch does not lose stability, it marches into the saturation boundary and is
   annihilated there. That is why the "assume collapse" self-consistency derivation is tight: at
   saturation the healthy cycle equals the collapsed cycle (waits pinned at P) and blind makes the
   server cost per delivered request (1/mu) independent of B, so the healthy branch's feasibility
   limit and the collapsed branch's existence threshold are the same number. The derivation looked
   like it only proved existence of collapse; monotonicity upgrades it to the full bifurcation.
3. For n > n* there is no equilibrium at all: B grows linearly at rate n/n* - 1 forever. The
   collapsed "state" is not a second equilibrium, it is a runaway. (What makes the mission-level
   readout look like a state is the deadline, which the ledger's duration study already
   established.)

The structural reason there is no positive feedback: abandonment in this model lengthens the
requester's cycle (P + tau + 1 >= any healthy cycle), so overload reduces offered rate. Congestion
collapse with bistability (ALOHA, redial storms) requires the opposite: abandonment that shortens
the cycle (retries). This model has no retries. See Q5.

### Numerical confirmation (new probe)

Replica of tools/queue_theory.py queue_only_sim (same arithmetic as c2.step, C0, blind, staggered
cooldowns) with two additions: an initial-backlog preload (free_at = 200 at k=0) and goodput
measured only over the last 10,000 of 20,000 steps, so transients cannot contaminate. Three seeds
per cell:

| n | preload 0, late goodput | preload 200, late goodput |
| --- | --- | --- |
| 4 | 0.995, 0.994, 0.996 | 0.995, 0.994, 0.996 |
| 5 | 0.962, 0.965, 0.968 | 0.962, 0.964, 0.966 |
| 6 | 0.677, 0.668, 0.677 | 0.676, 0.671, 0.676 |
| 7 | 0.000, 0.000, 0.000 | 0.000, 0.000, 0.000 |
| 8 | 0.000, 0.000, 0.000 | 0.000, 0.000, 0.000 |

Identical to the third decimal at every span: no hysteresis band anywhere, cliff between 6 and 7 as
mu(P+tau+1) = 6.45 predicts. The backlog trajectory at n=6 preloaded with 200 drains linearly at
0.080/step (fluid prediction 1 - 6/6.45 = 0.070) and settles at the same B* as the unpreloaded run;
at n=8 unpreloaded it grows at 0.248/step (prediction 8/6.45 - 1 = 0.240). The drift is the fluid
drift, monotone, one attractor.

This also explains why the staggered start mattered and then stopped mattering: a synchronized
step-0 burst is a preload of about n/mu = 53 steps, far above B_c = 13.3. Below n* it drains at
rate 1 - n/n*, which at n=6 is about 750 steps, a large fraction of a mission, so whole-mission
metrics near the threshold are transient-blended; above n* both starts collapse, which is why the
ledger's n=8 check found only 0.01-0.05 of goodput difference. Transient, not hysteresis. The
one-seed 0.35 jump was noise, as the ledger already concluded.

### The cheapest decisive experiment, and where bistability could still hide

For the record, the minimal opt-in ABM change, if you want the check inside SandTable rather than
in the replica: params["queue_preload"] (float, steps). In build_c2: if present, set
op.operator_free_at = value (and crew_free_at[:] = value when a crew exists). No RNG touched, off
path byte-identical. Pair it with two output-only counters, n_request_late and n_serviced_late,
accumulated for k >= duration/2, so late-window goodput is observable. Bistability signature: a
span band where late-window goodput depends on preload. Expected result, per the analysis and the
replica: no band. A zero-code variant also exists: compare duration 1800 vs 5400 with
stagger_decisions off; if the synchronized-start deficit is a transient its absolute size is
constant as the window grows, if bistable it scales with the window.

Two honest caveats. First, the no-bistability proof is for the queue as coded. terrain_demand
(CR-15) introduces the missing positive feedback in space: a stalled vehicle moves slowly, stays on
difficult ground longer, and difficult ground raises its request rate. The CR-15 numbers (collapse
moving from 6-8 down to 4-6, strong dose response) are consistent with that loop, and hysteresis in
the terrain-coupled configuration is genuinely open; the preload knob plus a terrain_demand arm is
the test. Second, retry behavior (absent from the model) is the classic bistability ingredient; see
Q5. So the correct paper-level statement is: the published configuration's cliff is a capacity
crossing with a computable location and no memory; making it path-dependent requires a client-side
feedback the model does not yet have.

## Q3. Is the collapse the queue, or the punitive stall quality?

Verdict: the collapse is the queue; the size of its mission-level price is partly the stall
parameter. C7's stall_eq test was decisive for what it claimed (the slope, i.e. the interior
optimum survives with the gap closed) and silent on what Q3 actually asks (how much of the
admit-blind headline is stall-priced), because the ledger never ran stall_eq x admit. I ran that
cell. The headline survives at 57 percent of its size under published physics and at full size
under teleoperation physics. The semantics are defensible, with one genuine wart.

### What C7 tested and what it did not

The C7 battery (ledger, "C7 falsification battery") raised q_stall to q_fallback (0.30 -> 0.50) and
observed that blind's rise with jamming survives (0.664 at C0 to 0.820 at C3), refuting "the stall
gap is the mechanism of the interior optimum". That inference is sound: the slope is the queue.
But the level shifted +15.2 pp at C0 (0.512 -> 0.664), which is 46 percent of the proxy admit-blind
gap of +32.8, so stall punishment was still an open suspect for the headline's magnitude. New cell,
seeds 0..255, q_stall = 0.50 for both arms:

| arm (published physics, n=8, C0) | success |
| --- | --- |
| blind, q_stall 0.50 | 0.664 |
| admit, q_stall 0.50 | 0.852 |

admit - blind = +18.8 pp, paired t = 8.0. So with the punitive stall removed entirely the effect
is 57 percent of its published-physics size, and comfortably above the contract MDE of 2.5 pp.
Note admit itself moves only +1.2 pp when q_stall is raised (0.840 -> 0.852): admit vehicles barely
stall, so q_stall is close to a blind-only lever, which is exactly why it inflates the contrast.
Scaling the full-tier headline by the same ratio puts the stall-free gap near +13 to +14 pp. Under
teleoperation physics q_stall is nearly irrelevant (a holding vehicle is stopped regardless) and
the gap is +68 to +74 pp. So the honest statement of the headline's robustness is: the admit-blind
gap ranges from about +19 pp (scalar physics, stall punishment removed) through +23.7 pp (published
operating point, full tier) to +74.5 pp (teleoperation physics, full tier); its existence and sign
owe nothing to q_stall, roughly 40 percent of its published-physics magnitude does. One sentence in
the results or limitations should say this; the run to back it at full tier costs 78 seconds.

### Is waiting-worse-than-not-asking coherent?

Yes, for this modality, and the model contains its own best defence. A direct-control vehicle that
has ceded decision authority and is holding for guidance is not executing anyone's plan: it
hesitates at a contact or a fork, which is worse than a supervisory vehicle acting on its own
mediocre plan (q_auto) and worse than a fallback vehicle that has given up and re-seized authority
(q_fallback). The ordering q_stall < q_fallback < q_auto encodes committed deference, and the CR-2
teleoperation arm shows the scalar version is if anything generous: the physically honest rendering
of "waiting" for a teleoperated vehicle is speed zero, which is q_stall = 0 in effect, and the
result there is 26x larger, not absent. So q_stall = 0.30 is a mild stand-in for a real asymmetry,
not a thumb on the scale. Two genuine issues, though:

1. The admit hold at C5 is incoherent. c2.py line 307: hold = 2*lat if admit else patience. At C5,
   2*lat = 32 > P = 20, so an admitted-then-refused vehicle waits 12 steps longer than its own
   patience for a refusal it does not know is coming. An agent's patience should cap every wait:
   hold = min(2*lat, patience). As shipped this slightly biases against admit at C5 (measured
   admit 0.551-0.605 vs blind 0.598 at C4-C5, within noise, since nothing is serviceable there
   anyway), but the semantics are wrong and a referee reading the code will find it. One-line fix,
   byte-identical everywhere 2*lat <= P, i.e. everywhere that currently matters.
2. A link-dropped request waits the full P at q_stall for a reply that can never arrive. This is
   coherent (no ack, the vehicle cannot know) but worth one sentence in the model section, because
   it means p_drop buys the operator relief while still costing the vehicle its full patience,
   which is part of why jamming's net effect needs the decomposition of Figure fig:queue(b).

## Q4. Is the fan-out negative result an estimator artifact?

Verdict: the flatness is real and provably so, not a shared-denominator artifact; the negative
result survives and gets stronger when stated correctly. But one categorical sentence in the paper
is falsified by the model's own instrumentation under a different (equally defensible) booking of
wait time, and the paper should pre-empt that rather than let a referee land it.

### The arithmetic

metrics.py lines 128-130: interaction = held/I, neglect = (live-held)/I, fan_out = 1 +
neglect/interaction. The intervention count I cancels exactly: fan_out = live/held = 1/hold_fraction.
Verified on 256/256 teleop missions: fan_out equals 1/hold_fraction to machine precision. Two
immediate consequences. First, there is no 0/0 or odd-denominator pathology in the collapsed
regime: interventions and hold_steps do behave oddly there (every request becomes one hold of
length P), but their oddities cancel; the statistic is well defined and equals the duty-cycle
inverse. Second, fan_out and hold_fraction are the same statistic; neither may ever be cited as
corroborating the other (the manuscript currently does not, but the ledger's deadline-correction
section comes close; keep them apart).

The flatness has a closed form. In collapse every request abandons after exactly P held steps and
the cycle is P + c + 1 with E[c] = tau, so

    fan_out -> 1 + (tau + 1)/P = 1 + 23/20 = 2.15,

a ratio of two client timing constants. Measured: 2.18 at n=8, 2.14 at n=10, 2.13 at n=12,
converging on 2.15 from above as the serviced remnant vanishes. The operator's service rate and the
console count have vanished from the formula. That is the sharp statement of the negative result:
past the cliff, the duty-cycle estimator is a function of the clients' patience and decision
interval only, so it cannot contain information about server capacity even in principle. It is not
that fan-out fails to see this cliff; it is that at the cliff the quantity stops being about the
operator at all. The paper's mechanism sentence ("it does not measure whether help arrives") is
right; this is the quantitative version, and I would put the 1 + (tau+1)/P identity in the paper.

A second structural fact worth one sentence: measured neglect is constant at tau + 1 = 22.4 across
the entire span sweep (back out NT = (fan_out - 1) x IT from the C9 table: 22.2, 22.4, 22.7, 22.4,
22.6, 22.4 at n = 2..12). Every bit of the load dependence lives in the "interaction" term, because
what is being measured there is not interaction, it is the request sojourn W(n), which grows with
congestion and saturates at P. The implemented fan-out is exactly 1 + (tau+1)/W(n): a sojourn-time
statistic wearing a capacity statistic's name.

### The part that overreaches

"It never equals the true sustainable span at any load" (main.tex line 256) is true only for this
booking of wait time, where the vehicle's whole held period is counted as interaction. Wait time in
a queue is a third category (Cummings and Mitchell's WTQ), and there are three defensible bookings.
At the collapsed operating point (teleop, blind, n=8, from my probe, using busy_steps that
metrics.py already collects via operator_utilization):

| booking of the wait | IT | resulting fan-out |
| --- | --- | --- |
| wait counted as interaction (implemented) | 18.96 | 2.18 |
| wait in neither (classic Olsen-Goodrich) | busy/I = 6.34 | 4.53 |
| wait counted as neglect (utilization identity) | busy/I = 6.34 | cycle/IT = 6.52 |

n* as coded is 6.45. The third booking lands on the true collapse span to within 1 percent, and it
is not a coincidence: cycle/(1/mu) at wait saturation is mu(P+tau+1), which is n* by definition.
So a referee can compute, from numbers the paper's own pipeline emits, a fan-out variant that does
equal the sustainable span at the cliff, and the categorical "never" dies. The defensible claims,
which I would substitute: (1) the wait-inclusive estimate is floor-capped at 1 + (tau+1)/P and
pinned there across the entire collapsed range, so it cannot warn of the cliff; (2) the classic
estimate excludes the wait and reads 4.5, wrong in the other direction; (3) the utilization-identity
variant touches n* only at saturation, i.e. it confirms capacity exactly when you have already run
out of it, and reads mu x cycle < n* below; (4) therefore no booking of the duty cycle predicts the
cliff in advance, and the closed form is the only forward-looking instrument here. That is a
stronger negative result than the current paragraph, and it is artifact-proof.

One more caution for the C9 table caption: the admit fan-out column (3.88 down to 3.05 back up to
3.76) is described in the ledger as "roughly flat, which is what a load-invariant capacity metric
should look like". It is a U with a 25 percent swing, and under admit the estimator still never
reads anywhere near 6.3. I would not claim admit rescues fan-out; the safe claim is that admit
keeps the estimator off its patience floor, nothing more.

## Q5. The one mechanism: closed-loop reliance (adaptive ask policy, with retry as its variant)

Pick: make the client's decision to ask endogenous. A per-agent reliance state r_i in [0,1] that
sets the probability a decision event becomes an operator request (else the agent acts autonomously
at q_fallback immediately), updated by outcomes: serviced pulls r_i up, abandonment or drop pulls
it down. Optional second knob: retry_on_abandon, an impatient re-request after abandonment instead
of a fresh cooldown draw.

### Why this one is load-bearing rather than merely absent

Every number in the queue result assumes open-loop clients: agents request at a fixed rate no
matter what happened to their last ten requests. The offered-load side of both closed forms, the
(P + tau) cycle, is not physics, it is a behavioral assumption about vehicles and the humans who
configure them, and it is the assumption the HMT literature specifically says is false: reliance
adapts to experienced reliability (the trust-calibration pole structure the paper already cites via
parasuraman1997humans). Among the missing mechanisms in the list (reactive red, GNSS denial,
learned policies, trust dynamics, operator error, handoff), this is the only one that acts on the
paper's central mechanism rather than adding an orthogonal layer: adaptive reliance changes the
arrival process of the very queue the headline is about. It is also the client-side dual of
queue_policy: CR-10 gave the server three ways to handle a load it cannot carry; the clients
currently have none. The project's centerpiece question (protocol vs staffing vs autonomy) is
missing its fourth arm, training/calibration, and this mechanism is that arm. And it converts
trust calibration from a survey construct into an executable, measurable control loop: r_i is
reliance, its trajectory is calibration, its equilibrium against the queue's capacity is
miscalibration made quantitative, which is objective-3 territory (the C0-C5 x modality grid is one
cut; r-dynamics is the cut the grid cannot see).

The bonus mechanism, not on the list: retries. A real operator whose request goes unanswered asks
again. Retry is the canonical ingredient of genuine congestion collapse (ALOHA, redial storms), and
per Q2 it is exactly what this model lacks to be bistable: abandonment currently lengthens the
cycle (negative feedback, self-stabilizing); retry shortens it (positive feedback). Reliance
adaptation and retry are the same mechanism with opposite gain signs, which is why I count them as
one addition with two parameters rather than two additions.

### Minimal implementation preserving the opt-in discipline

About 20 lines in c2.py, one new state array. build_c2: if params has reliance_adapt (gain alpha >
0), allocate op.reliance = np.ones(n); absent means the attribute stays None and no RNG is ever
touched (byte-identical off, same pattern as stagger_decisions). In step branch 4, direct mode
only: if op.reliance is not None, draw one uniform; if u >= r_i, resolve immediately as autonomous
(control_quality = q_fallback, re-arm cooldown) and continue; else proceed down the existing
request path unchanged. Update at adoption (branch 1, where resolved_quality is adopted): serviced
outcome r_i += alpha (1 - r_i); abandoned or dropped r_i -= alpha r_i (an asymmetry parameter can
wait). retry_on_abandon: at adoption of an abandoned request, set decision_cooldown to a fixed
retry_delay instead of drawing _reset_cooldown; to keep the off path byte-identical and the arms
seed-paired, draw the cooldown either way and override the value, the CR-15 pattern. Output-only
metrics: mean and final reliance, ask rate. All defaults absent, byte-identical off, and the ON
arms document that they add one draw per decision event.

### The falsifiable predictions it buys

1. Self-calibration to the threshold: under blind with adaptive reliance, the equilibrium ask rate
   should satisfy r_bar approximately min(1, n*/n), because the fixed point of the update is where
   the serviced fraction balances the gain. Measurable as a -1 log-log slope of r_bar against n
   above n*. If instead r collapses to 0 (reliance death spiral) the model has reproduced automation
   disuse from queueing alone, which is a publishable HMT result either way.
2. Substitutability: adaptive reliance under blind at n=8, C0 should recover most of the
   admit-blind gap (clients shed the load the server cannot refuse), and it should also neutralize
   the G2 sign pathology (jamming no longer helps, because clients already stopped over-asking). If
   the gap does not close, protocol and calibration are complements, not substitutes. Either
   outcome is decision-relevant to GVSC: it says whether an interface change or operator training
   buys the same resilience.
3. Bistability on demand: with retry_on_abandon and no backoff, the Q2 preload experiment should
   flip: a hysteresis band in n appears (preloaded runs stay collapsed where unpreloaded runs stay
   healthy), and it should disappear again with exponential backoff. That gives the testbed a
   controlled demonstration that the difference between a graceful capacity boundary and a
   path-dependent collapse is client discipline, which is a statement about interface design (what
   the vehicle does when unanswered) that no current mechanism can express.

## The single most important change

Add the refund arm to the paper's gated table and reweight the Discussion's recommendation
accordingly: the measured lever is the console not spending service time on expired requests
(refund, +30.5 of the +32.8 proxy gap, and refund equals admit even under teleoperation physics),
not the "tell the vehicle immediately" notification the text currently foregrounds, which measures
+2.4 pp at published physics and nothing under teleop. This one edit simultaneously defuses the
straw-man attack on blind (the paper visibly quantifies the realistic-baseline gap instead of
hiding it), corrects the one operational claim the evidence does not support, and costs one
proxy-tier table row plus two sentences.

## Round 2 (2026-08-22, repo at 8aa7170)

Read for this round: the ledger from "Review round 1 (Fable)" to end, the current queue subsection,
decomposition paragraph, fan-out paragraph, and Discussion in report/main.tex, and the corrected
tools/queue_theory.py. Two new probes were run (specified inline below; neither is a gated
experiment): a utilization-versus-goodput probe on the full simulator (64 seeds per cell, n in
{6, 8, 12}, C0, published physics), and a retry-on-abandon extension of the round-1 pure-queue
replica that tests the fold closed form of question D at three (retry probability, backoff) points.

Up front, the round-1 error, owned: my claim that notification "measures approximately zero" was
wrong as a general statement. The full tier gates admit minus refund at +0.0801 (t=4.97) under
teleoperation. The post-mortem of how I got there is in section C; the mechanism of why the effect
is regime-dependent is in section A, and my corrected account predicts the regime structure rather
than merely absorbing it.

### A. The R3 reading is half right, and the wrong half changes the prediction

Verdict: the favour-direction reading (freeing the slot helps the operator, notifying helps the
requester, and a notified requester asks again sooner) is correct and nicely put. The clause "at
the price of operator efficiency" is wrong as written, and because it is wrong, the crossover it
predicts does not exist: there is no request rate or patience at which admit and refund swap on
mission success. The variable that closes the admit-refund gap is the cost of waiting, not the
rate of asking.

The competing explanation, and the measurement that separates them. Goodput is served divided by
requests. Refund and admit have identical server-side rules (both claim only feasible work, c2.py
lines 305-306), so they can differ only through the arrival process, and admit's refused requester
re-enters the cycle after about tau + 2 steps instead of P + tau + 1. More requests, same server.
If "operator efficiency" meant delivered decisions per unit time, it would have to be measured as
served per step, which for refund and admit is exactly service_rate times operator_utilization
(their busy time is serviced work only). Probe (64 seeds per cell, published physics, C0):

| n | policy | goodput | utilization | served/step | mean wait | success |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | refund | 0.919 | 0.746 | 0.1120 | 11.18 | 0.656 |
| 6 | admit | 0.908 | 0.783 | 0.1175 | 11.64 | 0.750 |
| 8 | refund | 0.795 | 0.877 | 0.1315 | 13.10 | 0.812 |
| 8 | admit | 0.730 | 0.904 | 0.1355 | 13.86 | 0.812 |
| 12 | refund | 0.585 | 0.975 | 0.1462 | 15.50 | 0.922 |
| 12 | admit | 0.444 | 0.991 | 0.1486 | 16.89 | 0.953 |

The operator under admit delivers MORE decisions per step at every span, not fewer. The goodput
ordering that R3 shows is the denominator carrying the tempo channel: at n=12 admit generates
roughly 30 percent more requests and serves slightly more of them in absolute terms. Nothing the
operator produces is lost. Two real costs do exist and are visible above, and both are small: the
accepted-wait inflation (admit's extra load lengthens the waits of the requests that are accepted,
+0.5 to +1.4 steps here) and, off a clean link, extra link exposure (more asks means more drops,
each costing a full patience window, which is why the teleop margin falls from +8.0 at C0 to +3.2
at C2). So the corrected reading: notification buys requester tempo at the price of per-request
goodput and slightly longer accepted waits; operator output is unchanged or better. I would
rewrite the paragraph's sentence accordingly and print served-per-step (or utilization) beside
goodput wherever R3 appears, because as published the goodput column invites exactly the
misreading the current prose makes.

Where the margin comes from, in closed form. At saturation both policies deliver the same
q_operator time share (c mu / n serviced completions per agent-step times tau + 1). The margin
lives in how a non-serviced request spends the rest of its cycle. Under refund every non-serviced
request (dropped or refused) waits the full P at q_stall; under admit a refused one waits
h = min(2 ell, P) + 1 and a dropped one still waits P. Per unit of non-serviced time, the
admit-minus-refund quality difference is

    (q_fallback - q_stall) x (tau + 1) x [ 1/(h + tau + 1) - 1/(P + tau + 1) ]

weighted by the share d(1 - s) of refusals among non-serviced outcomes, and the whole thing scales
with the non-serviced time fraction F. At the operating point (h = 1, tau + 1 = 23) the bracket is
1/24 - 1/43, giving about +0.085 mean quality per unit of refused time under published physics, and
a stopped-versus-moving conversion of 0.958 against 0.535 under teleoperation, which is why the
same mechanism is worth about one point in one setting and eight in the other. Every factor in
that expression is nonnegative, and the two adverse channels (wait inflation, drop exposure) scale
with the same F that the gain scales with, at a fixed ratio well below one. Hence: no crossover in
n, tau, mu, or P anywhere in the reachable range. The margin has closed-form zeros instead: F -> 0
(span at or below the collapse onset, the bit-identical regime the ledger already documents),
h -> P + 1 (2 ell >= P, the C5 end, where the refusal arrives no sooner than giving up unaided),
d -> 0 (nothing is delivered to refuse), and, under published physics only, q_stall -> q_fallback
(waiting costs nothing, so ending it early buys nothing).

Three pre-registerable cells that separate my account from the tempo-versus-efficiency reading:

1. Published physics, q_stall = 0.50, n = 8 or 12, C0, admit vs refund. My account: zero within
   the MDE (the tempo channel is nulled and there is no efficiency price to pay). The efficiency
   reading: refund gated better (the price remains, the benefit is gone). This is the cheapest
   decisive cell.
2. Teleoperation, n = 12, C0, admit vs refund. My account: the margin GROWS with span (F grows;
   the moving-time conversion applies to more of the mission), so expect clearly more than the
   +0.0801 measured at n=8. The efficiency reading, taken at face value, says the price is largest
   exactly there (the goodput gap is widest, 0.579 vs 0.449), so the margin should shrink or flip.
3. Low-F regime with waiting still expensive: teleop physics, service_rate 0.30 (threshold 12.9),
   n = 8. My account: both channels are small together, null within MDE. The efficiency reading:
   refund measurably better, since tempo is worthless but the extra load is still offered.

If cell 1 or 3 gates in refund's favour, the efficiency reading wins and I am wrong twice; my
derivation says neither will.

### B. What to lead with now

Verdict: yes, re-center, and the gated split makes the case stronger than my round-1 version of
it. The right lead is the mechanism plus the two-lever decomposition, with the sign reversal as
the qualitative punchline. The bundled +23.7 should not lead, because it is now a documented sum
of two levers with different owners (a discard rule that is doctrine and software, and a
notification that is an interface feature justified by tasking tempo), different evidence grades
(always-gated versus teleop-only), and different rebuttals. A bundled number invites the reviewer
to price the whole against the cheapest realistic baseline and call the remainder a bug fix; the
split preempts that, and the teleop-gated notification is now the paper's honest answer to "you
fixed your own defect": the second lever is not a defect repair relative to refund, it is a design
choice with a mechanism and a regime.

Concretely, the abstract's queue passage. Keep its current mechanism sentence ("The operator is a
server whose clients abandon it, and an operator that never learns it has been abandoned spends
service time producing answers nobody is waiting for, so congestion rather than attention dilution
is what defeats direct control at high span."). That is the right first claim. Replace the single
admission-control sentence that follows with the split, in this shape: "Two closed forms predict
where the collapse begins and the simulator obeys both. The remedy decomposes: a console that
discards requests whose answers will expire recovers \qRefundClear\% against \qBlindClear\%
mission success at the centerpiece operating point, about nine tenths of the full
admission-control gain, and telling the requester adds a further gated \qNotifyTele{} points only
under teleoperation, where waiting dominates an asset's duty cycle." Then the existing jamming
sentence follows unchanged, and the teleop bundle number (\qTeleBlindClear\% to
\qTeleAdmitClear\%) can survive as the magnitude exhibit inside the results section rather than
the abstract.

Two defects to fix while editing there, both found this round:

1. Contribution 3 (main.tex line 54) still displays the OLD formula, $n^{\star} = c(P+\tau)\mu/d$,
   while Equation eq:nstar now says $c(P+\tau+1)\mu/d$. The paper currently states two different
   closed forms for the same threshold. The same contribution item also still sells the bundled
   "explicit admission control is worth \qAdmitClear\% against \qBlindClear\%"; it should carry
   the split in one clause ("a discard rule recovers most of it; notification gates only under
   teleoperation").
2. The decomposition paragraph's clause "Notification therefore buys requester tempo at the price
   of operator efficiency" should become "at the price of per-request goodput and slightly longer
   accepted waits; the operator's delivered decisions per step are unchanged or slightly higher
   under admit". With that correction the paragraph's regime conclusion (pays when waiting
   dominates the duty cycle) stands on the tempo channel alone, which is the part the full tier
   actually gated. The clause "which is a good trade only when" should likewise become "which
   buys anything only when": my derivation and the probe above find no regime where the trade
   goes net negative, so the current wording concedes a downside the data does not show.

### C. Post-mortem: how I detected the off-by-one and still failed to report it as an error

What actually happened, verbatim from round 1, Q2: "(the +1 is the adoption step in c2.step
branch 1; the exact mean cycle at saturation is P + tau + 1 = 43, so n* as coded is mu(P+tau+1) =
6.45 rather than the paper's 6.30; the sweeps bracket 6-7 either way, but the +1 belongs in a
footnote)". I detected the discrepancy, re-derived the correct form, used 6.45 for everything
downstream (the replica threshold, and the fan-out booking where I wrote "6.52 against n* = 6.45"
while the paper's own n* was 6.30), and then filed the difference as a footnote suggestion instead
of as what it was: a published equation that is wrong. Three process failures, named:

1. Severity anchored to the container, not the object. Findings that answered one of the five
   commissioned questions got verdict-level treatment; a finding discovered en route inherited the
   prominence of the parenthesis it happened to be born in. The classification rule I actually
   applied was "how central is this to the question I am answering", when the correct rule is
   "what kind of artifact does this contradict". An exact equation in a published paper admits no
   footnote-grade discrepancies.
2. The empirical-indistinguishability fallacy. I reasoned that the sweeps bracket the threshold
   between 6 and 7, both 6.30 and 6.45 sit in the bracket, therefore the difference is immaterial.
   But a closed form claims exactness, so the standard of comparison is derivation against
   derivation, not derivation against noisy data. Materiality to current measurements is the wrong
   test for the correctness of an equation.
3. Silent local resolution. When my algebra disagreed with the artifact, I resolved the
   disagreement privately (adopted my value, moved on) rather than surfacing the disagreement
   itself as a first-class finding with a proposed adjudicating measurement. You then did exactly
   the adjudication I should have demanded (instrument fresh cycles: 42.840 measured, 43.00
   predicted), which is what settles it.

The notification-null overreach in R1 has the same root plus a fourth failure: asserting a null
without stating its power. Back-computing from your full-tier t: block sd of the paired difference
at 64 reps is 0.0801 x sqrt(32)/4.97, about 0.091, so per-seed paired sd is about 0.73 and my
256-seed probe resolved the admit-refund contrast to about +/-0.046 at one sigma... my observed
-0.008 was under two sigma from the true +0.080. Not a freak draw: an ordinary one, converted into
the categorical phrase "measures approximately zero" because I never wrote down what my probe
could and could not exclude. Had I been required to attach "cannot exclude effects up to +/-0.09"
to that sentence, the overreach dies in draft.

What to put in front of me next round, concretely:

- A standing discrepancy register: instruct me that every point where my derivation, the code, and
  the paper disagree, however small I judge it, must appear as its own numbered finding with a
  proposed measurement that would settle it. No materiality filter; materiality is your call.
- An explicit claim inventory when you want equations audited: list the displayed equations and
  generated macros and require a verified / refuted / unchecked mark on each. I audited mechanisms
  in round 1 because mechanisms were what the five questions named; I never treated the equations
  as enumerated claims under review.
- A power statement attached to any null I assert: the sentence "X measures zero" is banned in
  favour of "X is a null at resolution +/-r".

And the fresh instance proving the lesson generalizes: this round I grepped for the stale form and
the round-1 correction missed three sites. main.tex line 54 (the live inconsistency flagged in B),
the module docstring of tools/queue_theory.py (lines 19-29 still derive n_collapse without the +1
while the code at line 71 is corrected; the docstring is the first thing a reader of that tool
sees), and doc/sandtable-todo.md line 520 (historical CR rationale; your left-as-written policy
may cover it, but it should be a decision, not an accident). Fixes propagate along the paths the
fixer remembers; a mechanical sweep catches the rest. The one-liner:
grep -rn "patience + decision_interval" --include="*.py" --include="*.tex" --include="*.md" . | grep -v "+ 1"

### D. The retry fold, in closed form, and verified in replica before you build it

Setup, matching the Q5 proposal: after an abandonment (queue-refused or link-dropped), with
probability pi the agent re-requests after a fixed backoff rho instead of drawing its normal
cooldown (mean tau); serviced requests always draw the normal cooldown. Blind server, c consoles,
two-way delivery d, service time S = 1/mu, adoption step included as before.

The two thresholds. The healthy branch sees abandonment only through link drops, so its saturation
cycle is P + 1 + tau - (1-d) pi (tau - rho), and the collapsed cycle is P + 1 + pi rho +
(1-pi) tau. Hence

    n_c = c mu (P + 1 + pi rho + (1 - pi) tau) / d      (collapse becomes self-sustaining)
    n_h = c mu (P + 1 + tau - (1-d) pi (tau - rho)) / d (healthy equilibrium ceases to exist)

and the fold (bistable band) is n_c < n < n_h, with width

    n_h - n_c = c mu pi (tau - rho),

which is independent of both d and P: jamming shifts the band's location by 1/d but never its
width, and patience moves both edges together. Both are falsifiable regularities the build can
test. The band is nonempty for ANY pi > 0 with rho < tau, so the fold exists for every retry
policy that shortens the mean re-ask gap at all; what has a threshold is detectability at integer
spans: the band spans at least one whole vehicle iff

    pi (tau - rho) >= 1/(c mu) = S/c,

which at the operating point is 6.67 steps. So the answer to "does the fold require an insane
policy" is no, emphatically: a single immediate re-ask after a full patience wait (pi = 1, rho =
0), which is the naive default of any unmanaged client and of most humans, gives a band 3.3
vehicles wide, (3.15, 6.45). Even pi = 0.3 with no backoff sits at the detectability edge. The
design rule that restores effective monostability is a backoff floor:

    rho >= tau - S/(c pi)        (pi = 1: rho >= 15.3 steps at the operating point),

and for exponential backoff the same condition applies to the expected deferral. Note this retry
is the mild kind (re-ask only after waiting out P); a client that re-asks before its patience
expires folds sooner.

Replica verification (round-1 replica plus the retry rule; C0, blind, late-window goodput over the
last 10,000 of 20,000 steps, preload 0 vs 200, two seeds per cell):

| policy, pi, rho | predicted band | n=2 | n=3 | n=4 | n=5 | n=6 | n=7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| blind, 1.0, 0 | (3.15, 6.45) | 1.00/1.00 | 1.00/1.00 | 0.99/0.00 | 0.00/0.00 | 0.00/0.00 | 0.00/0.00 |
| blind, 0.5, 0 | (4.80, 6.45) | | | 0.99/0.99 | 0.95 and 0.61/0.00 | 0.00/0.00 | |
| blind, 1.0, 15 | (5.40, 6.45) | | | | 0.96/0.96 | 0.00/0.00 | |

(cells are unpreloaded/preloaded goodput; blanks not run). Read the three quantitative hits:
at pi = 1, rho = 0, n=4 is textbook hysteresis (healthy from a cold start, permanently collapsed
from a preload) while n=2 and n=3 recover from the same preload, bracketing n_c = 3.15. Halving pi
moves n_c to 4.80 and the SAME n=4 cell flips to monostable (preloaded run recovers), while n=5
becomes the hysteretic cell, and one unpreloaded n=5 seed shows a mid-window escape (0.61): the
fold's stochastic signature, a metastable healthy branch with finite escape time. Backing off to
rho = 15 moves n_c to 5.40 and n=5 flips back to monostable. All three edges land where the
formula puts them. One honesty note: inside the band but near its upper edge (n=5, 6 at pi=1) both
starts collapse within 20,000 steps, because the healthy basin is shallow there and jittered
cooldowns kick the backlog over B_c early; the deterministic band is where the fold exists, and
the OBSERVED hysteresis band at horizon T shrinks from above as escape times fall below T. At
mission length (1800 steps) the observable band in SandTable will be wider than in this replica.

Admit is retry-proof, as predicted: with pi = 1, rho = 0, admit shows no preload sensitivity at
any span (n=5: 0.96/0.96; n=6: 0.67/0.67; n=8: 0.16/0.16) because the backlog stays bounded at the
admission boundary; retry under admit degrades per-request goodput smoothly (the denominator
again) and nothing folds. That yields the paper-grade sentence the build would earn: the collapse
becomes path-dependent only when BOTH sides lack discipline, a server that works expired requests
and a client that re-asks without backoff; discipline on either side (a discard rule at the
console, or a backoff floor of tau - S/(c pi) at the client) removes the fold. And inside the
band, CR-13's synchronized start stops being a cosmetic transient and becomes a genuine lock-in
mechanism (the opening burst is a preload past B_c), so stagger_decisions turns from a
reproducibility knob into a design variable. Verdict: build it; pre-register n_c, n_h, the
d-invariant and P-invariant width, the pi and rho edge flips above, and admit's immunity.

### Round 2 in one line each

- A: favour-direction right, "price of operator efficiency" wrong (admit's operator delivers more
  per step at every span; the goodput ordering is the denominator); no admit-refund crossover in
  rate or patience; the closing variable is the cost of waiting; three decisive cells named.
- B: lead with mechanism plus the two-lever split (discard \qRefundClear\% always-gated,
  notification teleop-only), sign reversal as the punchline; fix the stale c(P+tau)mu/d in
  contribution 3 and the "operator efficiency" clause.
- C: I detected the off-by-one and misfiled it as a footnote: severity anchored to the container,
  exactness judged by empirical indistinguishability, disagreement resolved silently, and a null
  asserted without power; the fixes are a discrepancy register, a claim inventory, and a mandatory
  resolution statement on every null; the stale-formula grep found three more sites this round.
- D: fold band (n_c, n_h) with width c mu pi (tau - rho), independent of d and P; exists for any
  cycle-shortening retry, detectable when pi (tau - rho) >= S/c = 6.67 steps; sane defaults are
  deep inside it; backoff floor tau - S/(c pi) or a console discard rule removes it; verified in
  replica at three (pi, rho) points; build it.

## Round 3 (2026-08-22, repo at 7d53cef)

Read for this round: the CR-17 ledger entry, the st-waitcost-9443162 record in
experiments/empirical.md, the st-hyst-9443432 registration, and the round-2 resolution notes. No
new simulator probes were needed this round; the analysis below is worked from the gated tables,
the levels already sitting in the run logs, and the fold algebra.

### Scorekeeping first, because the record matters

The message says "Your prediction was a null at q_stall=0.50. It is not a null." My registered
prediction (round 2, section A, cell 1) was scoped: "Published physics, q_stall = 0.50, n = 8 or
12, C0, admit vs refund. My account: zero within the MDE." The published-physics column gates at
no q_stall (+0.0093, t=0.89 at 0.50), so that registered cell CONFIRMED. I also wrote "teleop:
stays gated positive regardless of q_stall," and it did (+0.0459, t=3.72). Both registered
predictions held. What the sweep refuted is something I implied without registering: my mechanism
account attributed the teleop margin to stopped motion alone ("the moving-time conversion... is
why the same mechanism is worth about one point in one setting and eight in the other"), which
predicts a FLAT teleop profile in q_stall. The profile halves. The channel I missed: a stopped
vehicle still fights. control_quality feeds engagement on both sides (shooter effectiveness q,
target exposure 2 - q), so q_stall prices the combat and survivability of a vehicle that is
stopped inside weapon range, and refund's vehicles spend P steps per refusal in that state where
admit's spend one. My round-2 sentence "the exposure and effectiveness part can be nulled by
q_stall, the motion part cannot" had the pieces and I still dropped the first one when I summed
the teleop margin. Half credit, and the sweep design that caught it was better than my cell.

One registration-hygiene note that cuts at both of us: the empirical.md registration framed the
alternatives as "monotone decline to zero (wait-cost reading) or flat (artifact reading)."
That is a false dichotomy as registered; the hypothesis family always included "declines to a
positive floor set by a second channel," which is what happened. Register the lattice, not the
poles, or the outcome gets narrated as refuting a reading nobody fully held.

### 1. The three-way decomposition: directionally sound, not yet gateable, and the quality term is mislabeled

The inference chain has three specific defects.

First, the middle term (stopped motion, 0.0459 - 0.0093 = 0.037) subtracts across two different
response surfaces. The two physics settings differ in baseline success (published sits near 0.83
against teleop near 0.70), and a bounded metric compresses margins differently at different
operating points, so a cross-physics difference at matched q_stall is not the stop channel alone
even if the behavior layer were otherwise inert. Second, the residual (0.0093, t=0.89) is not
gated, and a decomposition that presents an ungated quantity as a 12 percent component launders
noise into structure. Third, the quality term (0.0801 - 0.0459 = 0.034) is a difference of two
gated numbers, which is not itself gated: from the reported t values the unpaired combination
gives se about 0.020 and t about 1.68, just under the contract's 1.70. The arms share block
seeds, so the paired difference-of-differences will do better than that, but it has to be
computed from the per-block values, not asserted from the headline subtraction.

The direct design, which fixes all three at once: a 2x2 factorial INSIDE the teleop stack, using
the knob that already exists for exactly this purpose. behavior.py takes teleop_stop, and False
reproduces the pre-CR-2 waiting-means-driving behavior while keeping everything else of the
teleop configuration. Arms: {stop=True, stop=False} x {q_stall=0.30, 0.50}, each measured as
admit minus refund on shared block seeds; st-waitcost already supplies the two stop=True cells,
so this is two new full-tier runs. Gate three contrasts by paired difference of differences: the
stop main effect at q_stall=0.50, the quality main effect at stop=False, and the interaction.

Registered predictions for that factorial, from the four cells already known, assuming the
stop=False column reproduces the published column (which is itself the consistency check that
CR-2's layer has no second live channel):

    base (stop=False, q=0.50):     +0.009   not gated
    quality main (stop=False):     +0.005   not gated
    stop main (q=0.50):            +0.037   gated
    quality x stop interaction:    +0.029   gated
    sum:                            0.080   (reconstructs the +0.0801 cell exactly)

If those land, the correct labels are: the notification increment under teleoperation is about
half stopped motion and about a third quality-of-waiting-WHILE-STOPPED. There is almost no
standalone quality-of-waiting channel (the published-physics sweep already says so: +0.016 to
+0.009, never gated). The current three-way split books the interaction silently into the quality
term, and "quality of waiting, 43 percent" overstates what a moving vehicle's stall quality is
worth by roughly a factor of seven. Same arithmetic, different ontology, and the factorial gates
every piece of it.

### 2. The opposite-sign sweep is floor-pinning, and it dissolves when you print the levels

refund - blind rises with q_stall under teleop (0.596, 0.665, 0.750) and falls under published
physics (0.306, 0.223, 0.177). The resolution: a difference of bounded metrics inherits the slope
of whichever arm has headroom.

Under teleoperation, blind is deadline-pinned. Its tempo is set by holding (binary stopped, not
quality-scaled), the formation cannot finish inside 1800 s no matter what quality its waits carry,
and its success sits near 0.01 to 0.03 at every q_stall; the only thing q_stall buys a pinned arm
is marginal combat while stopped. So the teleop difference tracks the refund LEVEL, and refund's
level rises with q_stall because its vehicles spend roughly a third of the mission stopped inside
red weapon range, where q_stall prices both their fire (q) and their exposure (2 - q). Under
published physics both arms are interior, and the arm with more stall time (blind waits about 46
percent of live steps against refund's roughly 33) gains more when waiting gets cheaper, so the
gap compresses as q_stall rises. Opposite signs, one mechanism apiece, no paradox.

The zero-compute check, from logs you already have: print the six levels behind each difference.
Predictions: blind-teleop spans at most about 0.03 across the whole sweep (pinned); refund-teleop
spans about 0.15; blind-published spans about 0.19 and more than refund-published spans. If
blind-teleop instead moves substantially with q_stall, my explanation is wrong. And the general
rule this buys the paper: never publish a contrast sweep without its level curves; near a floor or
ceiling the contrast's slope belongs to the unpinned arm, which is also why "refund - blind falls
with q_stall" under published physics is not evidence against the queue mechanism, just the
familiar fact from round 1 that stall pricing carries part of blind's penalty.

### 3. CR-17's a_h correction: accepted, and here is the tightening it still needs

You are right that my round-2 healthy edge was the fluid a -> 0 limit and overstates the observed
edge; at C0 it predicted retry-invariant n_h = 6.45 and the simulator kills the healthy branch at
n=6. The correction direction is right. Three tightenings before it goes anywhere near the paper:

1. a_h is endogenous, and the 0.222 you fed in is the retry-OFF abandonment at n=6. With retry
   on, near-edge abandonment triggers retries, which raise load, which raises abandonment: the
   healthy branch's true state solves a = A(n, a), and the branch dies where the stable root of
   that map vanishes (a saddle-node in a at fixed n), which is generally BELOW the frozen-a_h
   estimate. So publish the edges as a bracket: n_c exact (the collapsed branch has a = 1 by
   definition, no approximation), n_h in [measured, frozen-a_h estimate, fluid bound] with 5.85
   the middle member, not "the" value.
2. "Jamming moves the band but does not widen it" holds only at the a_h floor. With endogenous
   a_h(n, d) the width picks the link back up. State it as a floor property or the first
   independent-drop sweep will falsify the sentence as written.
3. The 15.33 backoff floor is conservative under the correction (a_h > 1 - d shrinks the width,
   so the true floor is lower). That is the safe direction for a design rule, and worth saying:
   the rule as published cannot under-protect.

One ABM-specific channel neither formula contains: attrition is load shedding. A dead vehicle
leaves the queue, so inside the band the collapsed branch must survive its own casualties to stay
locked. At n=4 (formally inside (3.75, 5.85)) a single loss drops the team below n_c = 3.75 and
the queue heals; at n=5 it takes two. Registered prediction for st-hyst H1: the
difference-of-differences at n=4 is smaller than at n=5, even though both spans are inside the
deterministic band. If H1 instead shows n=4 as bistable as n=5, the attrition-healing channel is
weaker than I think. Also registered: H3's refund cell gates as band-closed (the local -0.078 is
noise; refund never claims infeasible work, its backlog is bounded, same argument that made admit
retry-proof in my round-2 replica), and H4 opens at rho = 4, 8, 12 and closes at 16, 20, with the
transition between 12 and 16 exactly where pi(tau - rho) crosses one service time.

### 4. Question 1: a finding, not a retraction, but do not enthrone the synchronized start either

The retraction worry is mechanical, and it closes mechanically. Every published gated cell ran
retry-off. Retry-off is monostable: proved by the round-1 drift argument (abandonment lengthens
cycles, the backlog field is monotone, one attractor per n), tested by CR-13 (stagger moved n=8
goodput 0.01 to 0.05), re-tested by your own retry-off row this round (n=5: 0.960 burst against
0.978 staggered). In a monostable system the initial condition cannot select a branch, so no
published number is an artifact of the start; the start only shaded transients, which CR-13
already priced. CR-17 is therefore a new finding about a new, opt-in feedback loop, not a
retraction. If you want that bulletproof rather than argued, one full-tier stagger replication of
G1 and G4 closes it forever; the proxy-tier version in the round-1 ledger already points the
right way. What must NOT happen: the ledger sentence "the published configuration uses the
synchronized start; inside the band, that is the initial condition that lands on the collapsed
branch" migrating into the paper without the retry-off qualifier attached, because as a bare
sentence it insinuates exactly the artifact reading you are worried about, for cells where no
band exists.

But the question "is the synchronized start the defensible default" is the wrong question, and
answering it either way loses. Zero-dispersion phase lock (every cooldown initialized to zero) is
a numerical artifact; a formation crossing the line of departure together is real but has
seconds-to-minutes of natural spread; neither makes a principled default INSIDE a fold, where
there is no single number to publish at all. The move that survives review: stop treating the
burst as an initial condition and model it as what it physically is, a correlated demand event
with a size, a contact, a phase line, a defile entry, an obstacle. The onset arithmetic is
already in the model's constants: k simultaneous requests serialize on the console, the j-th
reply lands at jS + 2*ell, so abandonment begins at bursts of k > (P - 2*ell)/S, which is 3 at
the operating point, and inside the band the retry cascade locks anything much past onset. A
fire-team-sized subset of an eight-vehicle formation asking together is enough, which is the
strongest form of the finding, and it converts the arbitrary-IC objection into a measured basin
boundary (critical burst size against span), which is a deliverable, not an embarrassment.
Inside the band, report branch-conditional pairs plus that boundary, never one number.

And the demonstration that ends the argument, because it has no artificial initial condition in
it at all: terrain_demand plus retry, staggered start, n=5. The column starts healthy, enters the
defile, the ground itself generates the correlated burst (CR-15 already showed the defile is a
burst generator), and the team either locks into collapse and does not recover after the ground
eases, or it does not. If that runs the way the band says, it is the manuscript figure: endogenous
hysteresis, terrain in, no knob touched mid-run.

### 5. Question 2: subsection yes, under four conditions, and one clause to fix

The fold earns a subsection IF st-hyst gates, for three reasons that are about the paper and not
about the simulator: it is the paper's first genuinely dynamical result (everything else is
steady-state); its remedies are closed-form interface requirements (a backoff floor, a discard
rule) in exactly the genre the paper already trades in; and it is the first crisp qualitative
handoff to the high-fidelity tier: "same burst, two outcomes, which branch does ProjectGL land
on" is precisely the kind of cheap, sharp prediction the two-tier workflow exists to hand over.

The conditions. First, scope the disturbance. Your own negative result shows the most obvious
military disturbance, a transient jam, UNLOADS the queue and cannot tip it; publish that
alongside, because it kills the likeliest misreading and it is independently interesting ("EW
cannot tip you into locked collapse; your own tasking discipline can"). "Brief disturbance" as
written invites the jam reading; say demand burst. Second, fix "the fix is a backoff floor rather
than more operators": staffing DOES fix it, both edges scale with c, so a second console moves
the whole band above the operating span; discipline removes the band at software cost while
staffing relocates it at people cost. "Before," not "rather than," and it then slots into the
paper's existing ordered guidance without contradiction. Third, the realism limitation must
mirror the queue_policy one: which retry behavior fielded clients implement (firmware for UGVs,
procedure for crews) is an observation this model cannot supply; the claim is conditional on an
undisciplined loop existing. Fourth, the phenomenon has a literature: bistability from retrials
and reattempts is known in retrial-queue and random-access work (the redial-storm and ALOHA
family). Cite it and claim the placement (span-of-control terms, closed-form edges, interface
remedies, HMT reading), not the fold itself; a queueing referee will find the lineage in minutes.

On "explains why a team that was working can stop working after a brief disturbance and not come
back": scoped to demand bursts and stated as a candidate mechanism, that is not overreach,
because it comes with a falsifiable telemetry fingerprint that distinguishes locked congestion
from the rival explanations (fatigue, damage, degraded comms): console utilization pinned near
one, goodput near zero, and per-vehicle request rate ELEVATED at roughly d/(P + 1 + rho) against
the healthy d/(W + 1 + tau). A team that stopped because it is overwhelmed asks more often, not
less, while accomplishing nothing, and that signature is checkable in any exercise log that
records requests. Put the fingerprint in the subsection and the operational reading is a
hypothesis with a test, not a metaphor.

### Round 3 in one line each

- Scorekeeping: both of my registered cells confirmed; what failed was an unregistered implication
  (flat teleop profile), and the miss was the combat channel of q_stall for stopped vehicles.
- Decomposition: directionally sound, not gateable as built; run the 2x2 teleop_stop factorial
  (two new runs), predicted split: base +0.009, quality main +0.005, stop main +0.037,
  interaction +0.029; the real channel is quality-of-waiting-while-stopped.
- Opposite signs: floor-pinning; teleop blind is deadline-pinned so the contrast inherits
  refund's positive q_stall slope, published physics compresses toward the arm that waits more;
  print the six levels and it dissolves.
- CR-17 algebra: a_h correction accepted; a_h is endogenous so publish n_h as a bracket, scope
  the jamming-width claim to the floor, note 15.33 is conservative; attrition heals the band from
  below, predict weaker bistability at n=4 than n=5.
- Q1: finding, not retraction (published cells are retry-off and monostable, mechanically
  closed); but recast the burst as a sized demand event with onset k > (P - 2*ell)/S = 3, and run
  the defile-tips-the-team demo for an IC-free demonstration.
- Q2: subsection yes if st-hyst gates, with the jam-unloads negative published alongside,
  "before more operators" not "rather than," the retry-realism limitation, the retrial-queue
  lineage cited, and the utilization-high/goodput-zero/request-rate-elevated fingerprint that
  makes the operational reading falsifiable.

## Round 4 (2026-08-22, repo at c31a2d4)

Read for this round: st-stopf-9443653, the CR-17 gate (H1/H2), the defile table, the burstiness
derivation and its d measurements, and the current c2.py (retry implementation, and the new
late-window counters that now exist at late_from = 0.75 x duration). Two micro-checks run this
round, both decisive: (1) blue_behavior="auto" with teleop_stop=False is BIT-IDENTICAL to the
published-physics path, verified on 16 of 16 run pairs across seeds and policies on every shared
metric; (2) the retry cooldown is the ordinary jittered draw rescaled by rho/tau and therefore
inherits terrain scaling, which slightly moves one claim below.

### 1. The three-decimal registration: no paradox, once the degrees of freedom are counted

The puzzle dissolves under the bit-identity check. The factorial's four cells were: two numbers
already measured in st-waitcost (the stopped column), and two byte-identical re-executions of the
published-physics arms (the driving column; that is why they reproduce W1 to four decimals
INCLUDING the t statistics, which is the fingerprint of the same runs re-executed, not of a
confirmed statistical prediction). My registration therefore contained exactly one falsifiable
claim, the structural equivalence of the driving column with the published column, which is a
code-path identity that behavior.py's docstring already asserted and my check has now verified at
bit level. Given that one fact, all four term values follow by arithmetic on known numbers. So "a
pre-registered quantitative prediction that lands to three decimals" carried zero statistical
information about whether the terms are non-null. There was never a collision between the prior
and the gate, because the prior never bet on the noise.

And where my registration DID bet on the noise, score it honestly: I predicted base and quality
would not gate (correct, twice), and that stop main and interaction WOULD gate (wrong, twice).
Stop main cleared |t| and MPE and failed only sign consistency at 53 percent; interaction missed
both narrowly (t = 1.58 against 1.70, 0.0293 against 0.030). My error was variance arithmetic: I
assumed the difference of two seed-paired contrasts keeps most of the pairing benefit, and it
does not; the DoD mean halves while its se barely drops (0.0151 against 0.0161 for the stopped
contrast alone).

Shipping the four cells with a conditional reading and no subtraction is the right call, for a
reason worth stating: no information is discarded. The decomposition is a linear map of the
cells; any reader can compute it. The gate governs which ASSERTIONS the paper makes, not which
numbers it carries, and the cells are each gated on their own terms. Add one sentence noting the
bit identity of the driving column with the published arm, because it retires the
surface-equivalence question permanently and explains the four-decimal reproduction a sharp
reader will otherwise puzzle over.

What the contract is missing is not a way to price a prior but a sequential rule. A registered
prediction whose term lands in a near-miss band (say |t| in [1.2, 1.70), point estimate within
the registered interval) should buy exactly one pre-declared extension, sized in advance: here 32
to about 44 blocks would gate the interaction if the estimate holds (1.58 x sqrt(44/32) = 1.85).
That prices registration correctly: it cannot override the gate, it can only purchase a second,
larger look whose alpha cost is budgeted. Without such a rule every near-miss becomes a judgment
call, which is what the contract exists to prevent.

On the 60 percent consistency criterion: under homogeneous per-block effects, expected
consistency is Phi(t/sqrt(B)), which at the gate boundary (t = 1.70, B = 32) is 62 percent. So
for direct paired contrasts the criterion is nearly redundant with the t rule, and its marginal
content is a heterogeneity tripwire: observed 53 percent against an expected 67 at t = 2.43 says
the stop-main effect is concentrated in a subpopulation of blocks with large magnitude. For a
DERIVED term that is the expected case, not a pathology; interactions are moderator-driven by
construction. Keep consistency as a veto for primary direct contrasts; for linear combinations,
demote it to a flag that triggers a moderator analysis, with a sign test or block-median as the
robust guard. And run the moderator analysis here, because it converts the failure into content:
registered prediction, the per-block stop-main DoD correlates with how much of that block's hold
time is spent inside red weapon range. If that lands, the correct paper sentence is conditional
and gated at cell level anyway: the notification increment exists where waits happen under fire.

### 2. The rule for two-factor objections

Concede the instance first: my round-3 objection was issued at maximum severity when the repo
documented, and one 40-second check would have confirmed, that the second factor was zero by
construction. behavior.py says teleop_stop=False reproduces the pre-CR-2 path; I neither cited
the contract nor ran a seed before objecting. The objection came with its resolving design (the
factorial), which is the half I got right; it lacked the price tag, which is the half I got
wrong.

The rule, in three grades, with the burden on the objector to state the grade:

- Grade A, documented zero: the repo asserts equivalence of the second factor (byte-identity
  contract, off-path guarantee). Reviewer's duty: cite the contract and run or request the
  one-seed check. The objection is a checklist item, never a block.
- Grade B, boundable: the second factor's magnitude can be bounded from numbers in hand (an
  operating-point compression bound, a share-of-time bound). The bound ships WITH the objection,
  and it blocks only if the bound is comparable to the effect, say within a factor of two.
- Grade C, unbounded: no bound available. Blocks the causal LABEL, never the cells: report the
  measurements, withhold the attribution, and the objector owes the cheapest discriminating
  design alongside the objection.

Plus the meta-rule that would have saved a round here: when the resolving run costs less than
the argument about it, run it before writing the objection. Two 78-second batteries beat three
paragraphs, every time, and this codebase's byte-identity discipline makes grade-A checks
unusually cheap. The reflex you should keep from this exchange is not "reviewer objections about
confounds are cheap noise": the objection forced the factorial, and the factorial produced the
bit-identity receipt and the cell-level presentation, which is better than what it replaced. The
reflex to drop is letting a grade-A objection carry grade-C rhetoric.

### 3. The defile: the 0.4 percent margin is dressing, and the story does not need it

Drop the "5.00 against 5.02" sentence. The a_h machinery is a first iterate of an endogenous
fixed point; it cannot support three-digit placement of the edge, and a referee who notices will
discount the parts of the result that are actually gated. The load-bearing structure is already
in hand and does not touch the in-defile edge at all:

1. The band at n=5 on FLAT ground is gated, hard: H1 +0.3130 (t=18.2, 32/32), H2 +0.5722
   (t=61.1, 32/32). Coexistence of two branches at the operating span is established.
2. At pi=1 the collapsed branch barely notices terrain. Its cycle is P + 1 + rho_eff, and the
   implementation makes rho_eff the jittered draw rescaled by rho/tau, so terrain scales only the
   small rho term: n_c is about 3.75 on flat ground and about 3.45 in the defile at
   terrain_demand=1. The collapsed branch is self-sustaining at n=5 everywhere on the map.
3. Therefore the defile needs to supply exactly two things: entry (the collapse begins in the
   defile) and persistence (the state survives onto easy ground, where the gated flat-ground
   band does the locking). Whether the in-defile healthy branch was destroyed (moved cliff) or
   merely made shallow (basin escape) is a real question about the entry mechanism, but the
   lock-in headline is insensitive to its answer.

The cells that separate moved-cliff from shallow-basin, cheapest first:

- Zero compute: the per-seed histogram of the defile runs you already have. At terrain_demand
  0.5 the mean is 0.509, which is almost exactly the midpoint of the two candidate modes.
  Registered prediction: that cell is bimodal, modes near 0.8 and 0.15 with a hollow middle
  (stochastic tipping out of a coexisting basin). A unimodal pile near 0.5 instead means graded
  slowdown, and the tip story weakens badly. Print the 24 points before anything else.
- The persistence instrument now exists: operator_goodput_late (late_from = 0.75 x duration).
  Registered prediction for st-defile: at demand 1.0, retry-on late-window goodput below 0.15
  while retry-off sits above 0.85, provided the column clears the defile before three quarters
  of the mission; and the reversed-geometry control (defile late in the route) shows a healthy
  early window in both arms. Note also the whole-mission arithmetic already argues persistence:
  retry-off dips only to 0.908 at demand 1.0, so in-defile time alone cannot produce retry-on's
  0.287 unless the state persists after exit or the collapse traps the column in the defile,
  which is the same lock-in expressed spatially.
- The clamp, if you want the in-defile question answered on its own: flat map, decision_interval
  set to the defile-effective value, IC contrast at n=5. Two branches at fixed parameters means
  the shifted band is real; a single collapsed state means demand moved the cliff below the
  operating point and the defile entry is a threshold crossing, not a basin escape. Either
  answer leaves the headline intact, which is exactly why the paper should not stake it on 5.02.

### 4. Burstiness: the closed form is right about the simulator, and the simulator contradicts its own timescales

The derivation itself is correct for the code as written, and I verified the logic against
c2.step and comms_ew: the two draws are consecutive same-vehicle calls with nothing interleaved,
survival means the chain lands GOOD, so d = (1-p)(1-p_gb) exactly, and your five measured rungs
confirm it to three or four decimals. No dispute there.

The artifact is real and it is precisely locatable: the reply is drawn zero chain-transitions
after the request, while the model's own physics separates the two transmissions by 2*lat + 1/mu
sim-steps plus queue delay. Worse, the chain is clocked per MESSAGE and shared across every
vehicle and the sensing relay, so its coherence unit ("burst_len = 4") is four messages, a
duration in sim-time that floats with offered load. A channel whose coherence time depends on how
often blue asks is not a channel property, and the sim's declared timescales already contradict
the adjacency assumption: physical separations of roughly 9 to 39 steps against a dwell of about
4 messages. So: exactly right about the simulator, and the simulator is wrong about itself.

The repair is cheap and exact. For a two-state chain the lagged conditional is closed-form:

    P(reply survives | request survived, lag L) = 1 - p(1 - lambda^L),  lambda = 1 - p_gb - p_bg.

Check the endpoints: L=1 gives 1 - p(p_gb + p_bg) = 1 - p_gb (using p_gb = p*p_bg/(1-p)), your
adjacent formula; L to infinity gives 1 - p, Bernoulli. One uniform per message survives (only
the threshold changes), streams stay aligned, and it is opt-in behind something like
ge_clock = "message" (default, byte-identical) | "step" with L = 2*lat + ceil(1/mu), or the
actual computed wait if you accept reordering the draw site (flag: that moves a draw relative to
the Bernoulli path and needs its own pairing note).

Now the stakes, quantified at burst 4: lambda is 0.74 at rung 1 and 0.69 at rung 3; lambda^L is
0.064 at rung 1 (L about 9) and 0.004 at rung 3 (L about 15). The GE-minus-Bernoulli delivery gap
becomes (1-p) * p * lambda^L: 0.003 at rung 1 against the current 0.034, and 0.0006 at rung 3
against the current 0.110. Eleven times smaller at the mildest rung, two hundred times smaller
where your n* shift is largest. Under physical clocking the handshake advantage, the 3.7 to 35.2
percent n* shift, and st-bspan's sign-flip bracket all effectively vanish. Hold st-bspan's result
out of the manuscript until the clocking question is settled.

But do not just delete it, because the adjacency limit is CORRECT physics in a named regime: a
slow-sweep jammer or shadowing with dwell times much longer than the round trip really does show
both legs the same channel; fast fading really is Bernoulli. Which limit applies is governed by
one dimensionless ratio, coherence time over round-trip-plus-service time, and the current code
hard-codes that ratio to infinity within a handshake and to about eight steps between handshakes,
both by accident of draw order. So the salvage is a sharper conjecture that subsumes the current
result as an endpoint: mean drop rate is not a sufficient statistic for the ladder (C1's claim)
because the sufficient pair is (p, coherence/RTT), and the SIGN of burstiness's effect on n*
depends on where that ratio sits. Expose coherence in time units, sweep it, and the st-bspan
bracket becomes one slice of a surface instead of an artifact-dependent point claim.

On the second half: yes, in the model as clocked, burstiness is entirely a scalar change to d.
Your Fano measurement (0.878 against 0.876, under-dispersed everywhere), the raised request rate,
and the lowered link abandonment are all pure-d signatures, and the message-clocked shared chain
guarantees it: interleaving scrambles any temporal structure before a second message from the
same vehicle sees the chain. But that conclusion is bound to the same clocking artifact. A
step-clocked chain produces common-mode outages, windows in which every vehicle's messages fail
together, and a common-mode outage with retry on is a correlated demand burst arriving at lag
about P + rho_eff: the CR-17 tipping input, manufactured by the channel itself. Registered as a
question rather than a prediction, because the cohort arithmetic is marginal (a 20-step dwell at
n=5 catches roughly 2 to 5 requests against an onset near 3): with ge_clock="step" and retry on,
inside the band, does a bad dwell of at least the backoff tip the team? If yes, EW regains
tipping power through client indiscipline, and the round-3 finding "a jam only unloads the queue"
acquires its scope condition: true for uncorrelated drops without retry, false for correlated
outages with it. That would tie Q4, CR-17, and the jam-window capability into one mechanism, and
it is the only reading under which burst structure matters in this model at all.

### Round 4 in one line each

- Q1: no paradox: the driving column is bit-identical to the published arms (verified 16/16), so
  the three-decimal hit was one structural fact plus arithmetic; my genuinely statistical bets
  went 2 of 4; ship the cells, add a sequential-extension rule to the contract, demote
  consistency to a heterogeneity flag for derived terms, and run the moderator analysis.
- Q2: grade objections A (documented zero: check, never block), B (bound ships with the
  objection), C (blocks the label, never the cells, and owes the discriminating design); run any
  check that costs less than the argument; my round-3 objection was grade A wearing grade C.
- Q3: drop the 5.02 dressing; the flat-ground band at n=5 is gated and n_c is everywhere below 5,
  so the defile needs only entry plus persistence; print the 24-seed histogram (bimodality test),
  then read operator_goodput_late, then clamp tau if the in-defile question still matters.
- Q4: derivation right about the sim, sim inconsistent with its own timescales (message-clocked
  shared chain, zero-lag reply); lagged conditional 1 - p(1 - lambda^L) fixes it for one uniform
  per message; under physical clocking the entire burstiness result shrinks 11x to 200x, so hold
  st-bspan and reframe as the (p, coherence/RTT) surface; burst structure currently IS scalar d,
  and the only route by which it could matter is step-clocked common-mode outages feeding retry.

## Round 5 (2026-08-22, repo at 988c26c)

Read for this round: the CR-18/CR-19/CR-20 code (comms_ew.py reply_survives and the step-clocked
delivered, the c2.step reordering that prices the reply on done - k), K1/K2, and the CR-19
registration. One probe run on the live Comms class, decisive for Q1: round-trip delivery d
against burst length L at rung 3, empty-queue handshake lag (lat + S = 11 steps), 200k handshakes
per point:

| L | 4 | 14 | 28 | 60 | 120 |
| --- | --- | --- | --- | --- | --- |
| d measured | 0.642 | 0.698 | 0.740 | 0.767 | 0.776 |
| d analytic (1-p)[1-p(1-lam^11)] | 0.643 | 0.699 | 0.738 | 0.768 | 0.783 |
| n* = 6.45/d | 10.03 | 9.23 | 8.74 | 8.40 | 8.24 |

Bernoulli reference: d = 0.640, n* = 10.08. Hold that table; three of the four answers run
through it. Also noted for Q4: K1's message-clock column gated NEGATIVE at n=8 and n=9, which is
the st-bspan sign-flip bracket (8.60, 10.08) landing exactly as registered, under the old clock,
just before being retracted. That fact is an asset; use it (below).

### Q1. e(theta) is decorative in its current role, for three separable reasons

**First and largest: the premise "d and n* do not move" is false, and your own code comment says
so.** The registration reads "mean throughput is untouched (marginal rate held fixed by
construction, so d and n* do not move)". The reply_survives docstring you shipped in the same
session reads "the round-trip delivery rate therefore runs from (1-p)(1-p_gb) down to (1-p)^2 as
the service delay outruns the channel's coherence". Both cannot be true, and the second one is
right: holding the per-message marginal p fixed does not hold the round-trip d fixed under the
step clock, because the handshake correlation lam^(done-k) is itself a function of L. The table
above is that sentence measured: across your own CR-19 sweep, d rises 21 percent and n* falls
from 10.03 to 8.24, so at the registered operating point n=8 the system moves from a 25 percent
margin below collapse to 3 percent. L1's success curve will be dominated by a FIRST-MOMENT drift
toward the threshold, not by any dispersion statistic, and a negative result will be read as
confirming e(theta) unless the mean channel is removed first. The fix is a design change, not an
analysis change: add a d-MATCHED arm, retuning p per L so that
(1-p)[1 - p(1 - lam^lag)] is held at 0.64 (one-dimensional root-find per L; lag = lat + S plus
the mean queue delay if you want it exact). Hold d fixed, not p. The residual after d-matching is
the dispersion story; before d-matching there is no dispersion story, only a confounded sweep.

**Second: the within-vehicle lag is wrong, because the mechanism you priced does not exist in the
code.** "A vehicle retries tau steps later" and "it retries repeatedly inside its patience
window" both misdescribe c2.step: a dropped request sets await_until = k + P, the vehicle waits
out its FULL patience with no further attempts, and the next attempt comes one adoption step plus
a cooldown later. The gap between a failed attempt and the next attempt is Lambda = P + 1 + tau,
about 43 steps, not tau = 22 (with CR-17 retry it is P + 1 + rho_eff, about 25). Rerunning your
own crossover formula with the correct lag moves L* from 28.1 to about 54, and it breaks the L4
falsifier: at L = 14, theta is 0.26 under tau = 22 and 0.35 under tau = 11, both far below the
knee, so the one-radio-two-sides contrast you registered will read flat on both sides for the
within-vehicle channel (whatever it shows will be the d(L) mean channel again). If you want a
lag falsifier that works, use CR-17: retry-on halves the failure-to-attempt lag (43 to about 25)
and should shift the within-vehicle knee from L of about 54 to about 31, a predicted knee
MOVEMENT with everything else fixed.

**Third, the question you actually asked: one-step conditional against run-length exceedance.**
For this channel it is a distinction without a difference: Gilbert-Elliot dwells are geometric,
so P(run >= T) and the lag-T conditional excess are the same exponential family with rates 1/L
and 1/(L(1-p)); no functional form changes. The worry becomes real only if the dwell distribution
is heavy-tailed (semi-Markov jamming with Pareto dwells, which real sweep jammers can resemble):
then exceedance and conditional diverge and the knee structure changes qualitatively. That is a
channel-realism question to flag in limitations, not an algebra error in CR-19.

**And the channel your derivation does not contain at all, which knees first: the shared chain.**
Every vehicle draws from one chain, and CR-20 made same-step transmitters share the fade, so a
BAD dwell is a common-mode outage: every request inside it fails together, producing a
synchronized cohort of P-waiters that re-enters together Lambda steps later. That channel turns
on when tau_corr reaches the team's inter-request spacing, about cycle/n = 4 to 5 steps at n=8,
i.e. L of about 6, material by L = 14: earlier than the handshake knee (about 14, where lam^11
reaches 0.4) and far earlier than the within-vehicle knee (about 54). The right dispersion
statistic for the queue is therefore not the within-vehicle e(theta) but the burstiness of the
FAILURE process at the operator: registered check, the Fano factor of link-failure events on
windows of order S rises above 1 by L = 14 while e(theta) still reads 1e-3. Ladder of knees, all
computable in advance: cohort (about 6), handshake mean (about 14), within-vehicle (about 54,
retry 31). e(theta) is the last and smallest term in the sweep you are running.

### Q2. The registered sign will probably verify, for the wrong reason

The mechanism you registered ("clustering puts several consecutive failures inside one patience
window") is not expressible in this model: one failure consumes the whole window; there are no
attempts inside it. What will actually drive L1 at n=8, rung 3: the d(L) mean channel (negative,
because rung 3 sits at the interior optimum of the blind operator, so RAISING delivery walks the
system back toward congestion: your own P3 surface shows goodput and success falling as drop
relief is removed at this span), then the common-mode cohort channel (negative: synchronized
abandonment raises arrival dispersion at a near-saturated blind server). The competing convexity
argument you recorded (clustering concentrates failure on few vehicles, more get clean runs, and
success at arrived >= n/2 is convex in clean runs) is real but attaches to the WITHIN-vehicle
correlation, the last knee, and it is opposed by the cohort channel, which is anti-concentrating
(everyone fails together) and knees first. So: negative through the sweep, dominated by a
mechanism absent from the registration. The third mechanism you asked for is the shared-chain
cohort; the fourth is the quenched limit: once dwells approach the effective mission length
(L(1-p) of order the 600 to 900 live steps; the top of your sweep is approaching it), each
mission samples roughly one channel state and success tends to the p-weighted mixture of a
near-clean mission and a dead-link mission, which at this operating point computes to roughly the
Bernoulli value again. Registered consequence: L1 is NON-monotone, effects growing to mid-L and
fading toward the mixture at the top. If L1 is instead monotone through L = 120, the quenched
reading is wrong and I will say so.

Also register the correct reading of L3 now, before it lands: refund absorption is a CHANNEL
DISCRIMINATOR, not a robustness check. Refund frees console slots; it cannot touch P-waits caused
by link drops. If the L-effect survives refund, it is link-side (drops and cohorts); if refund
absorbs it, it is queue-side (cohort congestion at the console). Either outcome is informative;
neither is a null.

### Q3. Not one timescale, and not a tautology: two composite timescales and one imposter

Push on it as asked: as drafted, "tau is the design parameter" is half tautology and half wrong.
Tautology half: tau is one of only three client timescales in a deliberately small model (P, tau,
rho); its appearing in every formula is bookkeeping, not physics. Wrong half: the fourth formula
(the coherence crossover) should not contain tau alone at all, per Q1: the sampling interval of
the channel by a failed vehicle is Lambda = P + 1 + tau. But fixing that error UNCOVERS the real
unification, which is better than the one you drafted:

- Composite timescale one, the demand cycle Lambda = P + tau + 1. It sets the collapse span
  (n* = c mu Lambda / d: load) and, corrected, the coherence crossover (L* = Lambda/(1-p):
  sampling). One measured quantity, two superficially unrelated thresholds: a capacity limit and
  a channel-modeling-fidelity limit. That is a genuine unification, and it is falsifiable on one
  axis your formula says is inert: sweep P at fixed tau and measure where the burst effect turns
  on. Your tau-form predicts L* does not move with P; the Lambda-form predicts proportionality;
  n* moves with P either way. One run adjudicates the unification AND the Q1 lag correction
  simultaneously. Register it before running.
- Composite timescale two, the retry acceleration Delta = pi (tau - rho). The band width and the
  backoff floor are not two results: width >= one span and floor violated are the SAME inequality
  read in opposite directions. Count them as one or a referee will count them for you.
- The imposter: "whether the radio's burst statistics are worth modeling at all" is NOT set by
  tau or Lambda. The earliest knee is the handshake lag (lat + queue + S, about 11 steps here),
  which is a link-plus-operator timescale, not a client one, and it controls the d(L) mean effect
  that dominates everything (Q1). Burst statistics start mattering at L of about 6 to 14 via
  cohorts and the handshake, long before the client cycle knee at 54.

The Discussion frame that survives: the model has a short ladder of characteristic lags,
handshake (lat + Wq + S), team inter-request spacing (Lambda/n), and client cycle (Lambda), every
one computable from the same constants that set n*; burst structure matters exactly when the
channel's coherence time crosses each lag, in order, and each crossing switches on a different
mechanism (mean delivery, cohort synchronization, within-vehicle repetition). That is a real
organizing principle, it subsumes your knee as the last rung, and it cannot be accused of
symbol-counting because each rung pairs a lag with a distinct, separately testable mechanism.

### Q4. The defense is good; here is the missing decisive test, the scope concession, and your best exhibit

The consultation-rate argument is the right one and it can be upgraded from argument to
measurement: the defining invariance of a physical channel is that its correlation structure in
TIME does not depend on how often it is queried. That is testable inside the simulator in
seconds: measure the autocorrelation of the channel state process (or of message failures) in
sim-time at two offered loads (say n=4 and n=12) under both clocks. The message clock's ACF will
visibly dilate and contract with load; the step clock's will not. That converts "I swapped
conventions" into "one convention violates the defining property of a channel under measurement,
the other satisfies it", which no reviewer can call taste. Run it and put one sentence in the
paper.

Second, concede scope rather than claiming universal correctness: per-message clocking is not
wrong everywhere. It is approximately the right model when losses come from the network's own
slotted contention (state per transmission opportunity), and wrong for fading and jamming, whose
coherence is a property of the propagation environment. The ladder's story is jamming, so the
step clock is right FOR THE LADDER'S CLAIM; a contention channel would be a different model with
its own clock. One limitation sentence, and the "arbitrary convention" objection loses its
footing.

Third, your best exhibit against "kept whichever gave the cleaner story" is already in K1 and the
ledger, and the round-5 message undersells it: under the message clock, the st-bspan sign-flip
bracket was a REGISTERED, CONFIRMED, GATED positive result (K1 msg column: -0.0488 t=-3.23 and
-0.0522 t=-3.82 at exactly the predicted spans 8 and 9). You retracted a confirmed, publishable
effect in favor of a null. The incentive gradient ran opposite to the accusation, and the record
shows it: registration first, confirmation under the old convention, retraction on physical
grounds anyway. Cite the sequence explicitly in the retraction paragraph; it is the strongest
sentence available to it. K2 belongs beside it as the necessary control (the switch acts only
through correlations), with the caveat that K2 is necessary, not sufficient: inertness on a
memoryless channel cannot certify the step clock's correctness, only its containment. The last
honest residue: burst_len is now denominated in ticks whose physical duration is scenario fiat,
so L is a swept axis, not a measured radio property. That is fine, CR-19 treats it as an axis,
but the paper should say it, and the (p, coherence/RTT) surface framing from round 4 remains the
right destination.

### CR-20 expectation: concur, with the reason made quantitative

The old floor's bite is bounded by incidence times (1 - lam): the forced extra transition matters
only where lam is far from 1, i.e. small L, which is exactly where all correlations are near dead
anyway; at large L, where correlations matter, lam is near 1 and one forced transition was nearly
free. The product is second-order everywhere: 0.15 x 0.31 of affected draws decorrelated at L=4
(where nothing downstream cares), 0.15 x 0.01 at L=60 (where something would). No gated effect is
the right expectation, spare-arm treatment is the right disposal, and the fix still matters
because the cohort channel (Q1/Q2) is carried precisely by same-step shared fades: the bug's
cost was never in the cells run so far, it was in the cells CR-19 is about to run.

### Round 5 in one line each

- Q1: e(theta) is third of three channels and mispriced: the registration's fixed-d premise is
  contradicted by your own docstring and by measurement (d 0.642 to 0.776, n* 10.03 to 8.24
  across the sweep), the within-vehicle lag is Lambda = P+tau+1 not tau (L* about 54, the L4
  falsifier lands both-flat), and the earliest real channel is shared-chain cohorts; add the
  d-matched arm or L1 is unattributable.
- Q2: the registered negative will likely verify via mechanisms absent from the registration
  (d(L) mean drift at an interior-optimum operating point, plus cohorts); the convexity counter
  attaches to the last knee and loses; register non-monotonicity toward the quenched mixture at
  the top of the sweep, and read L3 as a link-side/queue-side discriminator.
- Q3: reorganize around two composite timescales (Lambda = P+tau+1 unifying n* and the corrected
  L*, testable by a P-sweep of the knee; Delta = pi(tau-rho) as one inequality, not two results)
  plus the non-client handshake lag that actually decides whether bursts matter; "tau is the
  design parameter" as drafted is the tautology you feared.
- Q4: keep the consultation-rate argument, add the load-invariance ACF measurement (decisive,
  seconds to run), concede the contention-channel scope, and lead with the record: the old clock's
  bracket prediction GATED and was retracted anyway, which is the opposite of story-shopping.
- CR-20: expectation right, bound is incidence times (1-lam), uniformly second-order in the cells
  run so far; its real payload is the cohort channel in the cells about to run.

## Round 7 (2026-08-22, the coordinator's batch 6)

New this round: st-forceratio-9445778 at full tier (held force ratio versus fixed defenders), the
Floyd-Fall framing now in the manuscript, CR-23/CR-24 registered and running, and one datum from
the crossing battery's control (reply pin at n = 6 leaves the burst-times-retry contrast
untouched). Predictions below are blind: I have not read backoff.sh, adaptive.sh, or st-crossing
outputs. Placement facts checked in `scenarios/sc_span_control.json` and `scenario.py`: red scales
by deepening a column (30 m spacing, same anchor, same lane), and mission success is the
`survive_fraction >= 0.5` threshold readout.

Ranked verdicts, most important first: Q4 (do not stop; the fourth account is already registered
and two of its three pin-ladder points are confirmed), Q1 (a result, but a methods result, and
currently over-crowned until one attribution arm runs), CR-23 (falsifier mis-calibrated against
the code's own backoff jitter, and the GE knee locations discriminate my two accounts, so fix the
registration now), Q2 (ship the caution, not the claim), Q3 (structural, and the disanalogy
sharpens it; the papered-over one is signal observability), CR-24 (one predictable failure cell;
pre-commit its interpretation).

### Q4. The pin datum, and when to stop proposing mechanisms

The n = 6 result is not an early warning of a third burned mechanism. It is the second confirmed
point of the account registered in the foundations round (F5 and the r6_crossing probe): the jam
is sustained by good-dwell booking load, and `reply_model="marginal"` pins only the reply leg,
leaving the forward path's conditioning (request legs are lossless inside a good dwell) untouched.
The good-dwell loads at Lambda_r = 25 are:

| n | marginal reply | coherent reply | pin prediction |
| --- | --- | --- | --- |
| 4 | 0.853 | 1.044 | pin kills the effect |
| 5 | 1.067 | 1.305 | pin bites partially |
| 6 | 1.280 | 1.566 | pin does nothing |

Measured so far: n = 6, pin does nothing (co 0.440, mg 0.437, bern 0.493); n = 5, my 128-seed
probe, pin removes about a third (co -0.125, mg -0.086). Two of three points match before the
registered control lands. So when st-crossing refutes H(CR-22b), what dies is the round-trip-d
channel and its falsifier, not the crossing arithmetic: the numerator shortening (43 to 25)
survives, and the denominator's operative d is the conditional forward-path booking rate during
good dwells, not the stationary 0.780.

The decisive arm not yet run is the mirror control: `request_model="marginal"` (draw the up leg at
the stationary rate whatever the chain state, keep the reply coherent). Registered predictions:
the request pin kills at least 80 percent of the DiD at n = 5 and n = 6; the reply pin (existing)
kills roughly none at 6 and at most 40 percent at 5. If BOTH pins leave the contrast standing,
then stop: report an unexplained regularity with the refutation record attached.

The stop rule you asked for, stated generally: stop proposing mechanisms when you can no longer
state, before the run, a cell where the new account and "unexplained regularity" disagree.
Mechanism count is the wrong meter; free-parameter count is the right one. This sequence has added
zero free parameters across four accounts, each successive account contained strictly less
machinery, and every death was on a registered cell. That is refinement. Story-fitting is when the
mechanism space grows faster than the falsifier space, and here the falsifier space has grown
faster (pin arms, jitter arms, rho knees, span ladders). One more discriminating run is earned;
after a double-pin survival, none is.

### Q1. Force ratio: result, but a methods result, and not yet attributed

The finding is real and the U-shape retraction is clean process. But "span of control cannot be
evaluated without declaring what happens to the threat" is currently carrying three channels, and
only one of them is the console:

1. Console congestion: goodput falls with span in both arms, gated. Real.
2. Geometry: held ratio deepens a red column at one chokepoint on one lane (checked: 30 m spacing,
   fixed anchor, no re-laydown, no frontage change). "More red" is "wade through a deeper column,"
   which is a difficulty knob wearing an adversary's clothes. The monotone decline could be partly
   the column, not the console.
3. MOE concentration: success is survive_fraction >= 0.5. At held ratio the Lanchester square law
   makes the mean survivor fraction approximately scale-free while its variance shrinks with
   force size, so once queue degradation pushes the mean fraction below 0.5 (near n* = 6.45 at
   rung 0), concentration converts slightly-below-the-bar into near-certain failure. The -0.440
   cliff at 6 to 9 and the +1.231 DiD are threshold-amplified. The fixed arm is amplified the
   other way (mean above bar, concentration pushes toward 1). This is F4 item 3 doing live damage
   inside your biggest new number.

Attribution costs one cheap battery and one readout: (a) refund at held ratio, n = 9; registered
prediction if the console owns the decline: most of the -0.440 step recovers. A supervisory
held-ratio arm bounds the geometry term (its decline has no console in it). (b) Report mean
survivor fraction and advance distance next to success; if the means move gently while success
cliffs, the text must say threshold-amplified and show both.

Verdict: a result, and worth prominence after attribution, framed as identification: the span
estimand is undefined until the threat-scaling rule is declared; under the two natural rules the
sign reverses; most simulation studies choose silently; the published grid already uses the
conservative rule. Note also that lit-ideas I14 announced this in kind (a static red force is a
structural bias); the quantitative confirmation strengthens the result reading. One scope wrinkle
missed: cross-cell comparisons of effect MAGNITUDES are attrition-confounded even where
within-cell signs are safe, because the demand valve depresses offered load in lethal cells. One
sentence in the paper covers it.

### Q2. The grim reading: ship the caution, not the claim

Two sentences with different fates live in this result. The measurement caution is robust: console
adequacy metrics read from high-attrition trials overstate capacity, because goodput is
demand-endogenous. That transfers regardless of model fidelity; it is a confound statement, and
T&E audiences receive instrumentation cautions as gifts. The operational claim (casualties relieve
the console) is model-contingent and plausibly sign-reversed in the field: real casualty events
spike coordination demand (casevac, reassignment, reporting), and this model's demand is open-loop
with no casualty-triggered surge. Publishing the claim invites the correct rebuttal and taints the
caution standing next to it.

Constructive versions to ship: (1) a demand-normalized goodput (serviced against requests from
surviving requesters, or offered-load-corrected) reported wherever attrition differs across cells,
one line in metrics.py, immunizes every cross-scenario comparison including Q1's; (2) the sizing
rule in its forwardable form: the console's worst day is a bloodless day, so size staffing to
low-attrition operations. Same fact, pointed the useful direction.

### Q3. Floyd-Fall: structural, and the disanalogy sharpens it

Keep the identification. Its invariant is abandonment invisibility: Erlang-A's server sees the
hang-up instantly, so waste is a footnote; Floyd-Fall's upstream router cannot see the downstream
drop, so waste is a regime; the blind console cannot see expired patience, same regime. The policy
triple is a visibility ladder (never, at dequeue, at arrival plus signaled), which is tighter than
an analogy.

Your specific question: responsive-but-abandoning vehicles SHARPEN it. Floyd-Fall need senders
unresponsive on the rate axis. Abandonment is a response on the deadline axis (stop waiting), not
the rate axis (stop offering), and retry converts the deadline response into a rate increase
(cycle 43 to 25). Abandonment-with-retry is anti-responsive: worse per unit of offered load than
Floyd-Fall's senders. The model's addition to their story is exactly this two-axis decomposition
of "responsiveness," and it is why the fix lives on the vehicle.

The second disanalogy you are papering over is signal observability and use. TCP's remedies are
signal-consuming: Jacobson is loss-as-congestion-signal plus RTT estimation plus AIMD. Under blind
and refund your vehicle observes only its own silence, and at rung 3 over a third of round trips
die by link, so silence cannot distinguish link loss from queue death from slow service. Two
consequences. Citation precision: the doubling rule is Metcalfe-Boggs BEB, signal-free by
construction; cite Jacobson only where a signal exists, which is admit. And a falsifiable
completion: your own decomposition says the notification half of admit is worth almost nothing in
published physics, against everything TCP believes about signals, and the resolution is that no
vehicle policy CONSUMES the signal (fallback is identical told or untold). Register the missing
cell: admit plus cadence-AIMD (halve request cadence on refusal, additive recovery on service).
Prediction: the notification share of admit's value grows from single digits to a majority. If it
does not, the observability half of the identification is decorative and should be cut down to the
waste-regime half. An analogy that generates a cell is structural; one that only generates
citations is flattering.

### CR-23. Fix the registration before the data lands

Three problems, all repairable today.

1. The falsifier "the decline is gradual" is mis-calibrated against the implementation. With
   `retry_spread` unset, the effective backoff is cool times rho over tau with cool jittered
   plus-minus 50 percent, so the knee at nominal rho is convolved with a U[rho/2, 3rho/2] kernel.
   At n = 5 that smear is survivable; at n = 8 a knee at 20.6 smears across [10, 31] and is also
   capped near the standing interval, so it will read as gradual whatever the mechanism. Run the
   battery at `retry_spread = 0` (the knob exists for exactly this) or register the knee in
   effective-backoff units.
2. The registered knee locations assume stationary d, and my own F5 numbers share that
   assumption, so one of my two accounts is wrong and this battery arbitrates. Under the
   conditional forward path, the operative booking rate during good dwells is kappa around 0.98,
   not 0.78, and the clean-past-rho point moves right: at n = 5 the damage shoulder runs from
   about rho = 5 (stationary edge, jam persistent across bad dwells) to about rho = 11.6
   (conditional edge, jam dies within good dwells); at n = 6 the shoulder is about 10 to 18; at
   n = 8 the conditional edge is 31, PAST the cap, while Bernoulli clears at 13. Registered
   discriminator, jitter-robust and binary: if n = 8 GE-120 damage never fully clears below the
   cap while n = 8 Bernoulli clears near 13, the conditional account wins and CR-23 doubles as
   the request-pin experiment for free. If GE clears at 20 as your table says, stationary d wins
   and my foundations shoulder was a phantom.
3. The n = 4 falsifier ("gated at any rho refutes") is over-strong at long dwell: the conditional
   forward path gives n = 4 a good-dwell load of 1.044, entry rare but a 1800-step mission crosses
   several dwells, so a small L = 120-only effect at n = 4 is the forward-path term, not a
   refutation. Keep the clean refuter: n = 4 Bernoulli null at every rho (load 0.853, nothing to
   exploit).

### CR-24. One predictable failure cell; pre-commit its reading

The dominance claim should fail, if anywhere, in healthy-but-lossy cells: Bernoulli rung 3 at low
span, where over a third of round trips die by link noise and BEB doubles on silence it cannot
diagnose. Cadence stretches, consultation quality sags a hair, and adaptive lands between fixed-4
and fixed-20 instead of matching fixed-4. That is the classical loss-cause blindness of loss-driven
backoff on lossy links, not a dead rule, and its fix is the Q3 cell (double on refusal under
admit, never on silence). Pre-commit now: a small gated shortfall against fixed-4 confined to
healthy-lossy cells confirms the mechanism reading; treating it as refuting the doubling rule
would be the fourth mis-aimed falsifier this month. Also check the reset semantics before reading
tempo metrics: reset-to-base on service, or the leftover long backoff after a fade drags recovery
and dominance leaks in wait statistics while success holds.

### Scorecard

Mine to own: my F5 jam floor rho*(n, d) used stationary d; the conditional forward-path account,
also mine, moves the GE knees right and at n = 8 past the cap. Both cannot be right. CR-23 with
spread = 0 settles it, and I have committed above to which observation kills which. Also for the
F1 ledger: the attrition demand valve is the fifth instance of the pricing engine producing a
result the queue cannot (dead vehicles file no requests), and it landed at t = 35.8.

### Round 7 addendum (same day): CR-22 retracted, the pump account, Q4a to Q4c

Scorecard first, since the control landed on my registered numbers. The pin ladder held in kind:
pin bites partially at n = 5, none at n = 6, CR-22b fired as predicted. My quantitative bound did
not: I wrote "reply pin kills at most 40 percent at 5" without qualifying the metric, and on
goodput it killed 57 percent (my success-metric probe had shown 31 percent). The split is
metric-dependent and operating-point-dependent, and my bound was sloppy. Consequence for my own
registration: with the reply leg carrying 57 percent on goodput, my "request pin kills at least 80
percent" is wrong under additivity. Revised: request pin retains roughly the reply share (40 to 70
percent), and the DOUBLE pin is the real test: under channel additivity it retains under 15
percent; if it retains more, a third interaction channel exists. Also recorded: the new Fano table
confirms a check my account required (mg and ge share the clustering, 6.48 vs 6.13, because the
pin cannot touch the request-leg synchronizer).

**Q4c first, because it constrains the other two.** Three parts of that Fano rise are separable
and only one is your mechanism. (1) Mechanical on-off thinning: any arrival stream thinned by a
long-dwell channel shows a Fano rise at windows straddling the dwell; ge_off's +1.05 over bern_off
is this, no retry involved. (2) Loop echo: the retry arms add another +2.6 to +3.9, but arrivals
there include retries of the queue's own casualties, so the intermediate variable is endogenous;
clusters are co-produced by console state, and Fano cannot tell echo from cause. (3) Instrument
residue: bern_off at F(300) = 5.4 on a memoryless channel is trend variance (attrition and mission
phase), the same genus of bias as the window bug, smaller. So: the clustering DESCRIPTION is
established; the clustering EXPLANATION is not, yet. And one of your own gated results already
falsifies the clustering-only reading: under refund the same clusters arrive and goodput goes UP
(+0.047 at n = 8). Clusters are not damage; clusters times blind booking is damage. On a
disciplined console the bursty link is BETTER than the steady-loss link at equal average loss,
because fades bunch failures into windows where the queue drains and the post-fade cohort meets an
empty console. The mechanism sentence must therefore carry two clauses with independent switches:
the pump (retry synchronizes re-offers to the recovery edge; switch: backoff/jitter at the dwell
scale) and the valve (blind books the cluster's dead tail; switch: refund, already gated). Written
that way it is a mechanism. Written as "the console gets a cluster it cannot absorb," it
mislocates agency and a reviewer will use your policyburst table against you.

**Q4a.** Measurement plus switch-off is ALMOST enough, and after three failures the bar is
rightly higher: promotion needs (i) every clause of the mechanism sentence to have its own
manipulation (you have the valve switch gated; CR-23/24 and the Q4b battery give the pump switch),
(ii) the intermediate exogenized, because yours is endogenous, and (iii) the instrument validated,
because your last one was silently broken. One battery does all three: synthetic arrivals. Drive
the console with generated request streams (Markov-modulated arrivals), a 2x2x2: {clustered at
the dwell scale, smooth} x {rate matched to ge_retry, rate matched to bern_retry} x {blind,
refund}, with retry and abandonment feedback OFF so the arrival process is exogenous by
construction. Predictions that promote the mechanism: damage appears only in clustered x blind
and grows with rate; refund flips the sign in the same cells; the synthetic rate/clustering split
lands near the observational 57/43 at n = 5 (if it lands far away, the loop echo was doing work
the story credits to the channel). Feeding the Fano probe a known generated stream also calibrates
the instrument on ground truth, which after one broken instrument is not optional. Detrend the
mission-phase and attrition nonstationarity before quoting any long-window Fano in the paper, and
prefer w = dwell over w = 300 (four windows per mission is trend, not statistics).

**Q4b.** The mechanism test is right; the design rule as drafted is wrong twice, and the battery
as drafted has a confound that will produce a false confirmation.

The confound: `retry_spread = s` draws backoff rho + s u with u uniform in [0,1], so the jitter
arm raises the MEAN backoff by s/2. At s comparable to a 120-step dwell that is +60 steps of mean
backoff, which dissolves the effect through the load floor (CR-23's own axis) whether or not any
desynchronization happens. Every jitter arm needs a mean-matched fixed control at rho + s/2, or a
symmetric jitter at fixed mean, or the dissolution confirms nothing about the synchronizer.

The design rule: "scale the backoff to the outage length" is un-fieldable as stated (no vehicle
knows L) and it is also only half the requirement. Two floors bind independently: the load floor
(Lambda_r must cover team demand, n d/(c mu) - (P+1), n-dependent, binds even on clear channels)
and the outage floor (re-entry spread must cover the recovery edge, L-dependent, binds even at
subcritical sustained load because the post-fade spike n d/mu is about 26 booked steps against
P = 20 at n = 5, a transient stall wave per fade). The fieldable rule that satisfies both without
knowing n, d, mu, or L is the one CR-24 is already running: doubling reaches the outage scale
online (by fade end the backoff has doubled up to about L) and its geometric phase history
desynchronizes the cohort as a side effect, which is the classical reason BEB works. So spend the
battery as the mechanism test that also prices the design space, n = 5, rung 3, blind, L in
{40, 120}: A fixed rho = 4 (pump baseline); B rho = 4 with spread s = L PLUS its mean-matched
control at fixed rho = 4 + L/2 (the desync test proper); C fixed rho tuned to L but run at BOTH
dwells (shows any fixed scaling fails off-design); D adaptive doubling; Bernoulli references. Add
one readout: arrival Fano at w = L per arm, so the intermediate collapses under the same
manipulations inside one battery (Q4a's requirement, partially met for free). Registered
expectations: B beats its mean-matched control (desync is real over and above load) or it does
not (pump clause dies, load explains all); D matches the best of B/C at both dwells and pays no
healthy-cell tax. The sponsor sentence that survives every branch: "the backoff must cover the
larger of the team's service demand and the channel's outage scale, and an adaptive doubling
backoff finds both online; under admission control the same bursty link is not a threat but a
scheduling gift." The second half is the policyburst reversal, and it is the most transferable
sentence this project has produced.

**The span shape, one paragraph.** The positive tail at n = 7 to 10 is the link-side demand valve
appearing in a DiD: above the Bernoulli arm's own collapse, fades shed load and the bursty arm
wins. Free registered prediction: the zero crossing tracks the BERNOULLI collapse span (5.86), so
it moves with d and rho by that formula and vanishes under refund. If the crossing instead tracks
the GE arm's threshold, the valve reading is wrong. Costs nothing: the cells exist.

## Round 8 (2026-08-22, the coordinator's batch 7)

### Scorecard first, two deaths of mine

1. The load-threshold account is dead as registered, in both variants. CR-23 v2's falsifier (ii)
   fired on the shape: no knee at any span, smooth decline everywhere, damage gated at n = 4 where
   rho* is negative. I own that; the switch prediction was the account's content and it is gone.
   Two footnotes before burial, neither a rescue: the binary discriminator I registered went the
   conditional account's way (n = 8 GE does not clear by rho = 21), and its other half was not
   reported: does n = 8 BERNOULLI clear near 13? One existing-run readout; if bern also fails to
   clear, the conditional account is fully dead rather than half dead, and I want it buried on the
   full record. Second footnote below, because it is bigger than a footnote.
2. My CR-24 failure-cell prediction was wrong: I named healthy-lossy Bernoulli; the dominance
   claim died on GE goodput at n = 4, 5, 6. The cause was sitting in my own Round 2 lesson, which
   makes the miss worse, not better.

### The cross-cutting catch: goodput's denominator is treatment-inflated in every retry contrast

`operator_goodput = n_serviced / n_request`, and retry is a treatment that manufactures requests:
the failure cycle shortens from about 43 to P + 1 + rho, so in failure-heavy regimes the retry arm
inflates its own denominator by up to 1.7x at rho = 4. Two receipts from CR-23 v2's own table:

- The n = 4 plateau is arithmetic. At n = 4 failures are mostly fade-borne (about 20 percent of
  attempts), so attempt inflation is roughly 0.8 + 0.2 (43/25) = 1.14, which on an off-arm goodput
  near 0.65 predicts about -0.08. Measured plateau: -0.075 to -0.090 across rho = 4 to 14. The
  gated-everywhere row at n = 4 is largely the ratio, not the queue.
- At n = 5, rho = 2, inflation alone predicts roughly -0.23 of the measured -0.51: half
  arithmetic, half real congestion. The table is a mixture at every cell, in proportions that vary
  with rho, which is exactly what a smooth no-knee decline looks like.

What survives cleanly is the rho-insensitive stratum at rho = 21 (-0.032 to -0.056 across spans,
attempts nearly matched there since P + 1 + 21 = 42 against the standing 43). Its candidate is
determinism itself: deterministic holds freeze cohort phases where the jittered standing cycle
diffuses them. That is precisely CR-27's matched-mean fixed-versus-jitter contrast, so the battery
you already registered doubles as the test of this stratum. Convenient, and not designed for it,
which makes it better.

Actions, all cheap: add a `serviced_per_step` export (one line, `op.n_serviced / op.total_steps`)
and re-extract CR-23 v2 and CR-24 on it, or gate on success. Registered predictions for the
re-read: the n = 4 row collapses toward the determinism stratum for rho >= 4; the n = 5 half-point
moves left; CR-24's goodput dominance failure mostly disappears (adaptive tracks fixed20 on
serviced/step). If a knee re-emerges near rho = 10 to 12 at n = 5, the load rule revives on the
metric it was actually derived for (service loss, not the ratio); if the decline is still smooth,
it is dead honestly and I will not raise it again. Do not ledger the half-damage walk (3, 10, 16)
until this re-read; those numbers are mixture statistics. Ledger rule going forward, third
appearance of this lesson (refund/admit ordering in Round 2, the attrition demand valve in Round
7, retry now): any contrast whose treatment changes request cadence gates on treatment-invariant
denominators only.

### Q5. Ship it; bound the residual, do not decompose it further

The identification result (span has no defined effect until the threat-scaling rule is declared)
was licensed by the sign reversal alone and is untouched by any of this. What 75/25 adds is the
stronger sentence: the held-ratio decline is mostly console. The -0.171 gated residual needs one
naming sentence (force-scaling geometry plus the threshold readout), not another battery: the
arrived_frac readout already running splits concentration out of that bundle for free, so the
supervisory-at-fixed-defenders run is not worth its slot unless (c) comes back ambiguous. Report
(b) as the near-miss it is (45 percent against a registered half). And take the free consistency
check sitting in your own table: refund recovers 45 percent of the step while the console owns 75,
and the 30-point gap is the console's non-booking costs, attention dilution (0.95 to 0.825 at
n = 9) and stall time, which the model prices independently. One sentence turns the near-miss
falsifier into a decomposition that hangs together.

### Q6. The registered claim died; the salvage is real but must be labeled salvage

Say plainly: dominance as registered failed on goodput. Then say why that metric was the wrong
gate for this treatment (denominator, above) and that on the mission metric the claim held
(adaptive matches fixed20 everywhere, beats fixed4 by 0.14 to 0.20, gated). Note also that
"fixed20 is indistinguishable from not retrying" is an identity, not a finding: P + 1 + 20 = 42
against the standing 43; it validates the harness cadence arithmetic and nothing else.

The shippable recommendation, in the model's own scope: the reliance loop has no measured upside
and a large measured downside; if a loop must exist for reasons outside the model, exponential
doubling makes it approximately as harmless as not having one, without knowing the channel, the
team size, or rho; fixed-short backoff is the only catastrophic policy in the swept space. That is
"the rule instead of the number" surviving as an insurance claim rather than a performance claim,
and insurance is what a fielded default is. The caveat that keeps it honest: this model prices
unanswered waiting at a flat q_fallback with no exposure escalation, so "close the loop as slowly
as you can" is partly an artifact of guidance being cheap to live without here (F4 item 2). Where
waiting is dangerous, the optimum shifts back toward re-asking, and only the adaptive rule tracks
that shift without retuning. Ship the rule with that sentence attached.

### Q7. Sequence the two moves; pre-commit the order today

The options are not exclusive and the order is the whole answer. Five registered deaths on one
contrast raise the posterior that the CONTRAST is mis-constructed relative to the posterior that a
sixth mechanism exists, and this project's own history votes with that: three of its resolved
mysteries were instrument or metric artifacts (message-clock adjacency, the Fano window, and now
the goodput denominator). So if CR-27's P1 or P2 fails, the correct move is a pre-committed
artifact audit of the contrast itself, in this order, before any conclusion:

1. Denominator re-read (owed already, above).
2. Instrument-on-bench: inject jittered and unjittered retry-like streams into `bench_sim` and
   verify the in-sim `fano_window` would have seen P1's predicted reduction on ground truth.
3. Synchronized-start dependence: stagger initial phases (Round 3 machinery exists); if the
   contrast moves materially, the phenomenon is partly initial-condition sculpture.
4. Dwell-mission quantization: 1800 steps is 15 dwells at L = 120; vary duration and confirm the
   contrast is not a small-multiple artifact of how many fades fit in a mission.

Only after those four: report the regularity, and it is worth being precise about what that report
would say, because it is stronger than "unexplained". The bench already reproduces the damage
ordering with arrivals that cannot hear the console, so the console physics is established
exogenously; the refund reversal is gated, so the valve clause is established; what a CR-27
failure would kill is only the in-sim generative path (retry as the synchronizer). The residue
would be: damage real and portable, valve real, in-sim clustering source unattributed, five
registered refutations attached. That is a publishable negative-space finding, not a failure
report. And name the structural choice a skeptic would reach for, as scope rather than artifact:
the entire phenomenon lives under `blind` booking semantics, which is a modeling bracket for
console software nobody is obliged to field, and the paper has said so since Round 1. The
discipline point for the record: elimination under registered falsifiers is just sequential
testing; the thing to hold fixed now is the survivor's bar, set before this batch. Do not let a
P1/P2 failure move it, and do not let a P1/P2 pass lower it either.

### Bench notes, for the ledger

The bench is clean exactly where the sim was not: offered rate is fixed by construction, so its
goodput carries no denominator artifact, and the clustering effect at matched rate (-0.32 to
-0.43) is the first uncontaminated measurement of the pump's damage. Two sentences belong next to
it. The symmetric ON/OFF geometry (duty 0.5, peak-to-mean 2.0) differs from the channel's 80/20
(peak-to-mean 1.25) even though the Fano is matched, so magnitudes are existence-grade, not
transport-grade. And the corrected apportionment (the reply leg does about twice what a pure rate
step explains, residual unidentified) is the right way to have written it; the observational 57/43
should not reappear anywhere as a rate/clustering split.

## Round 9 (2026-08-22, the coordinator's batch 8)

Scorecard housekeeping first. The Bernoulli ladder completes my kill sheet: n = 8 does not clear
at 13.1 on the memoryless channel either, so both halves of my clearing prediction are dead, and
the rewritten burial (the rule ranks WHICH spans are vulnerable and misses WHERE vulnerability
ends, on both channels) is the correct verdict; I accept it as written. The denominator
quantification matches my receipts (large at n = 4, proportional at n = 5), rate.sh carries my
four predictions verbatim, and the estimator ground-truth tests discharge item (2) of the Q7
audit order. Falsifier (iii) not firing at n = 4 Bernoulli is the load rule's one surviving limb:
ungated at every rho exactly where rho* said nothing should happen.

### The n = 4 cell, read precisely before it becomes a poster

- It is a within-channel DiD (retry minus no-retry per channel), so channel-alone effects are
  already netted. Good construction, worth stating in the ledger.
- The Bernoulli floor (-0.024 at t = -12.8) is REAL and sub-MPE, not zero, and most of it is
  cadence arithmetic: a deterministic 21-step hold gives cycle 42 against the jittered standing
  43, about 2.4 percent more attempts, roughly -0.017 on a 0.688 baseline, before any phase
  effect. Do not let "not gated" become "zero" anywhere. The ladder is also missing its exact
  identity point: rho = 22 makes the cycles equal at 43, and that one cheap cell separates
  cadence arithmetic from determinism proper. Add it to rate.sh.
- The pump-clause quantity at n = 4 is therefore the cross-channel DiD, about -0.028, not the
  -0.052 headline.
- Sustained load is provably off at n = 4; TRANSIENT load is not. The post-fade re-arrival spike
  books about n d / mu = 20.8 steps against P = 20, so the pump at four vehicles lives exactly at
  that coincidence, and the coincidence supplies a free falsifier: at n = 3 the spike is 15.6,
  well under patience, so the pump predicts the n = 3, rho = 21, GE cell is null or much smaller.
  If n = 3 gates at similar size, the spike arithmetic is wrong and the candidate list reopens
  (channel-made clustering times the valve, no pump needed). Register it before running it.

### Q8: keep the battery, slim it, and let the audits ride along

The either/or is mostly false: the two audits cost a fraction of a battery slot (paired cells at
48 to 64 seeds, not 32x64 ladders), so the real decision is what CR-27 spends its arms on.

1. CR-27 keeps its slot and its bar. The n = 4 cell is pass-shaped observational evidence with
   exactly the two alternative explanations you named still live; it cannot carry the pump clause
   alone. The bar was one manipulation per clause, set before this datum existed, and Round 8
   said in both directions that data must not move it. A pass-shaped datum lowering the bar is
   the same sin as a failure raising it.
2. Slim the battery: drop the rho = 34 mean-matched tier. Its effective cycle sits past the
   standing interval, where even the mean predicts nothing; it is the lowest-information arm in
   the set. Keep 10 and 18, the memoryless null, and P3's dose response.
3. Spend the savings on the best P2 cell in the project, which the unplanned result just created:
   GE-120, n = 4, fixed rho = 21 against matched-mean jitter (rho = 10, s = 22). Sustained load
   is off for every d in [0, 1] there, so the mean-shift confound is unavailable IN PRINCIPLE,
   not merely controlled. Registered readings: if jitter at matched mean erases the gated -0.052
   down to the Bernoulli floor, the pump clause is confirmed at a load-free operating point with
   nothing else in the room; if the damage survives jitter, the pump is not phase compression,
   and the determinism stratum inherits the file.
4. The audits ride along at the two poster cells (n = 4 rho = 21, n = 5 rho = 4), both channels:
   staggered start, predicting the n = 4 DiD shrinks by at most about 40 percent and survives
   (the synchronized start is one extra compression event against roughly three fades per
   mission); and duration in {1200, 3600}, predicting per-step damage stable (15 dwells is a
   small multiple, but paired seeds carry most of it). If either audit kills the cell, it was
   initial-condition or quantization sculpture, and the ledger says so before any poster ships.

One more sentence for the ledger when the n = 4 cell is written up: it decides against LOAD, not
for CLUSTERING; the affirmative half still belongs to CR-27's P1/P2, and the write-up should not
borrow tomorrow's conclusion today.
