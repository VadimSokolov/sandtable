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

## Round 10 (2026-08-22, the coordinator's round 10)

### Scorecard first: two errors of mine, one failure mode

Verified in `_backoff` by reading the draw: `u = 2(cool - lo)/(hi - lo) - 1`, so the jitter is
CENTERED, `rho + s u` with u on [-1, 1], and the mean shifts only when the floor truncates the low
tail (s >= rho). My Round 8 warning stated the mechanism wrong (I claimed u on [0, 1] and a +s/2
shift always); my Round 9 free-cell arm (rho = 10, s = 22, asserted mean 21) was built on that
unverified assumption and lands at 12.13, which would have reintroduced, inside the fix, the exact
confound the fix existed to remove. The failure mode has a name: I verified your claims by value
and my own designs by memory. The Round 8 concern survives (floor truncation does shift means);
everything quantitative I attached to it was wrong. Your rebuild is correct: s = rho - 1 puts the
support on [1, 2 rho - 1] with mean exactly rho, and the free cell's (21, 5) and (21, 21) pairs
are clean.

One residue to close: the new guard (spread > backoff + decision_interval) is a backstop, not the
invariant. An arm like rho = 4, s = 12 passes the guard and still mean-shifts through the floor
(mean about 5.7 against a nominal 4). The invariant is s <= rho - 1; make it the standing
convention in the ledger, means verified by value in every registration that uses jitter.

### (1) P3 as constructed is not a test; move it to the free cell

Across the rebuilt pairs, width and level move together, and their effects on the jitter gain have
OPPOSITE expected signs: wider jitter should help more (dose), while a longer mean backoff leaves
less damage to fix (headroom). A monotone across-pair pattern, a flat one, and a reversed one are
all consistent with some mixture, so the across-pair ordering is uninterpretable whichever way it
lands. That is worse than collinearity; it is a confound with sign ambiguity. Keep the three pairs
as three REPLICATED within-level P1/P2 tests, which is what they are good for, and write into the
registration now that across-pair magnitudes will not be interpreted. P3 moves entirely to the
free cell's width ladder at mean 21 (widths 0, 5, 21 at one level, sustained load off by
arithmetic): that is the only clean dose axis in the design. Register one caveat before the data:
the (21, 21) arm's support reaches down to 1, so its low tail re-arms occasional fast retries;
Fano falling monotonically in width is the P3 claim, and a goodput non-monotonicity at the widest
arm would implicate the low tail, not refute dose response. Say that now, not after.

### (2) Drop the functional hedge, keep the residual hedge

Your worry is half right and the half matters. The two numbers are not independent evidence of the
MAGNITUDE: same 2048 missions, shared sampling noise (irrelevant at t near 70). But the two
attribution splits are different functionals of the same mission-level distributions: success
weights mass crossing the half-force line, the mediator weights mean displacement. They were free
to diverge, and there is a concrete way they would have: console damage concentrated near the 0.5
line with scenario damage in the tails would inflate the console share on success only. 72/28
against 75/25 says the split is insensitive to the readout functional, which is precisely the
artifact my Round 7 concern named. So: drop the threshold-amplification hedge ON THE SPLIT; keep
the one-sentence residual bundle (geometry plus force scaling), which is a different hedge about a
different thing. For magnitudes, lead with the mediator (+0.554) and give success (+1.231) as the
operational readout with the 2.2x named as the threshold's lever arm, now measured rather than
suspected.

The refund sentence: keep the observation, fix the word. Recovering 22 percent on the mediator and
9 percent on success means refund's help is DIFFUSE: many missions each moved a little, mostly
missions not sitting near the half-force line. That is mean-acting. "Tail-acting" asserts the
opposite (help concentrated where crossings happen). One sentence with the corrected term is fine
for the Discussion.

### (3) CR-28: cut the knob-null from the paper; your replacement is the real test

The rule you are reaching for: a null on a self-authored knob is evidence only when the knob's
range is anchored from outside the model, or when it is explicitly labeled a stress test to a
named natural extreme, and even then it earns a sentence, not a section. stall_decay's family
(flat to linear-vanishing) is natural enough, but the family itself is authored: why linear, why
multiplicative on q_stall, why this coupling and not exposure. A tier-confirmed null there says
"robust to the perturbation I chose," which a referee correctly reads as grading your own
homework. Cut it from the manuscript; the pilot stays in the ledger as a pilot.

The version with teeth is the one you named, and it should replace CR-28 rather than supplement
it: price the wait with machinery the model already owns and that was built for other reasons.
Under teleoperation physics a stopped vehicle stops fighting (Round 3 established that the
behavior layer prices stall time endogenously), and blue_loss_frac charges for exposure through
the engagement kernel. Run the recommendation grid (no-retry, fixed-4, adaptive) under
blue_behavior physics and gate the ordering on success and blue_loss_frac. If adaptive still
tracks no-retry there, the insurance claim survived a pricing mechanism that was not authored for
the test, and THAT sentence belongs in the paper.

### (4) The headline: your framing is backwards, and neither piece alone is the paper

Treating the span DiD as the result and congestion as its explanation makes this a paper about a
confound, which wastes the only part a sponsor can act on. Assign the roles instead:

- The MECHANISM is the spine: an operator console is a queue that pays for work nobody waits for,
  with closed forms that survived five adversarial rounds, two retractions, and its own
  instrument failures.
- The LEVERS are the headline: admission control removes the bistability and reverses the sign of
  the burst penalty; adaptive doubling makes a reliance loop approximately as harmless as not
  having one without knowing n, d, mu, or the dwell; both are software, neither adds an operator.
- The IDENTIFICATION result is the shield: the span estimand is undefined until the threat-scaling
  rule is declared, which explains why the field's span numbers disagree and why these are
  estimable at all.
- The WORKFLOW (registration, gates, retraction record) is the credibility thread that lets a
  skeptical reader believe the other three.

One abstract-shaped sentence: an operator's effective span of control is a queueing outcome, not
a psychological constant; it moves under three software levers, and span experiments that do not
declare what the threat does as the team grows cannot measure it. B3 closes my revival clause:
the load rule is dead on both metrics, and its surviving limb (which spans are vulnerable) is a
corollary of the spine, not a standing rule. The machinery this round shipped (double, aimd,
stagger, the guard) matches the asks from Rounds 7 through 9; the portfolio as submitted is the
right one.

## Round 11 (2026-08-22, the coordinator's round 11)

### (1) Giachetti: the mapping is real one level up from where you wrote it

The attack you asked for, made: their commander and your console are different queues, and their
2x2 design cannot see the thing your paper is about. Two mechanisms produce "large centralized
teams spend more time waiting": queue congestion (nonlinear in load, threshold, collapse) and
serialized approval (every subteam takes its turn even at low commander utilization, linear in
team size). Both predict their interaction sign. With two team sizes and F(1,12), their data
cannot distinguish a knee from a slope, and their prose "has become a bottleneck" is
interpretation over logs, not a utilization measurement. So the correspondence that is REAL: an
independent human-team implementation observed the interaction's SIGN (size hurts only when a
single decision-maker sits in the loop) and attributed the penalty to waiting on him. The
correspondence that is OVER-written: "their vanishing size effect is our supervisory arm" as
validation of the congestion mechanism. Their centralization may be a topology factor, their
arrival process is a handful of sector allocations, and nothing in their design licenses the
claim that their commander was saturated rather than serialized.

The narrower sentence, which is also a better one: "Giachetti et al. independently observe the
interaction's sign in an Army human-robot team: team size hurts only under high centralization,
and their logs attribute the penalty to waiting on the commander. A two-level design cannot
separate serialized approval from queue congestion, and cannot locate a threshold; the closed
forms here do both, which is what turns their post-hoc log reading into an ex-ante design
quantity." Keep the explicit disanalogy in the text (task-assignment queue at mission cadence
against a consult queue at 22-step cadence, same load algebra, different processes), so the
reviewer who knows the study finds the distinction already made rather than missing. Cite it as a
sign observation with small n, bracketed by Barnes and MAGIC on the span axis; do not let it
carry quantitative weight anywhere.

### (2) The burst lever was never a third lever

Fold it into admission control as that lever's burst-structure interaction and the demotion
question dissolves. The headline is two levers (admission control; the backoff rule) and one
interaction (admission control's value scales with burst structure). On that accounting the
uneven gating is not an embarrassment to manage but a prediction to check: the mechanism says the
mission-level consequence must concentrate where the operating point sits near the moving
threshold (n = 8 against the GE-shifted n* near 8.2) and compress where both arms are past or
short of it (n = 10 sits at the Bernoulli threshold itself). If the success sweep exists in the
cells you already have, plot the interaction profile against that prediction; landing means the
one-span gate is the mechanism speaking, not a weakness. If only two spans exist at mission
level, your demotion is exactly right as written: throughput claim, mission consequence at one
span, no third lever in the headline. Either way the abstract should say two levers, one
interaction.

### (3) CR-29: your decline is correct, and one cell in your pilot resists your mediator

Endorsed without reservation: gating on blue_loss_frac alone inverts under stop-dead physics,
lowest losses in the dead arm, which is the bloodless-day artifact in its third costume (goodput
denominator, attrition demand valve, now losses-vs-advance). The joint reading with arrived_frac
is the right repair, and my Round 10 instruction was under-specified on exactly this point; that
one is mine.

Two notes before tier. First, rename the mechanism: teleop_stop prices MOBILITY, not exposure.
Your own pilot shows it (rho = 4: losses 0.156, the lowest, success 0.000): missions die of
tempo, parked and safe, not of casualties. The tier claim should read "pricing the wait in
mobility makes re-asking strictly worse," and my Round 8 caveat is answered opposite to how I
posed it IN THIS QUADRANT: when asking itself stops the vehicle, attempt rate is what the physics
charges for, and short backoff maximizes it. I concede that quadrant. The caveat survives only in
the untested one (waiting priced through fallback quality and blundering exposure rather than
through stopping), which I would deprioritize rather than run: the tested quadrant is the
doctrinally relevant one for teleoperation. Second, the rho = 21 cell resists the hold-fraction
mediator: hold 0.456 against no-retry's 0.448, statistically the same stopped time, yet success
0.229 against 0.333. If tier reproduces a gated deficit at matched hold fraction, hold fraction
is a partial mediator and something else (the deterministic cadence is the obvious suspect) is
carrying real damage. Register that now so the tier write-up cannot claim full mediation if the
cell recurs.

### (4) The single largest threat: the thesis sentence proves too much

"Span of control is a queueing outcome, not a psychological constant" invites the one review that
kills: this model contains no psychology BY CONSTRUCTION. The operator never errs, never slows
under load, never fatigues; q_operator = 0.95 is unconditional. A human-factors reviewer will
write: you removed the psychological constant by assumption and then reported its absence as a
discovery, and the utilization ceiling literature (trouble near 70 percent, long before queue
saturation) is the phenomenon your abstract waves away. That review attacks the thesis sentence
itself, not a battery, and no battery fixes it.

The repair costs wording plus one small computation. (a) Scope the thesis to sufficiency:
queueing effects ALONE, with a flawless operator, are sufficient to produce the observed span
pathologies (Giachetti's interaction, collapse, bistability, the levers' gains); therefore span
doctrine cannot be set by attention arguments alone. Sufficiency, not exclusivity. (b) Promote
the oracle-operator limitation from the limitations pile into the mechanism section, one
paragraph, with the co-option sentence: an operator whose quality droops with utilization moves
every threshold LEFT and makes the levers more valuable, not less, because errors generate rework
and rework is offered load. (c) The one cheap computation, not a battery: a 48-seed droop
sensitivity sweep (q_operator falling linearly in measured utilization, two slopes) verifying the
ORDERINGS the paper ships (refund over blind, adaptive tracking no-retry, supervisory crossover
direction) are invariant. If the orderings hold under droop, the headline is armored against
exactly this reviewer; if any flips, better to know this week.

Secondary threats, one line each, in descending order: single-scenario magnitudes (answer: the
mechanism and bench are scenario-free, the pricing is demonstrated on one scenario, say so);
calibration promised in ratios but no retrodiction shown (ship the two-anchor mini-table, MAGIC
and Giachetti/Barnes, even if crude); refund requires knowing the requester's deadline (answer:
patience is protocol-declared between software, one sentence); and the retraction record read as
instability (answer: present the ledger as the method, which it is).

## Round 12 (2026-08-22, the coordinator's round 12)

### The one pre-run catch: O4 is aimed at a prediction q_droop cannot produce

Verified at c2.py line 514: q_droop scales the SERVICED decision's quality toward q_auto in
proportion to utilization, and nothing else. No cadence change, no re-request on a degraded
answer, no rework. Requests fire on cooldowns regardless of outcome quality, so the queue's
arrival and booking arithmetic is quality-blind by construction, and the goodput collapse
location CANNOT move under this knob except through the second-order mission loop (slower
vehicles, different attrition, the demand valve). O4 as described ("the collapse itself moves
left") will therefore be refuted by construction, not because the co-option claim is wrong but
because the knob lacks the channel the prediction invokes. My Round 11 sentence carried that
condition implicitly ("errors generate rework and rework is offered load"); q_droop degrades
answers and generates no rework, and I should have said the condition out loud. Amend O4 before
droop.sh runs: registered predictions (a) the SUCCESS-optimal span moves left with droop, (b) the
goodput cliff location is droop-invariant up to the mission-physics loop. That pair is itself a
clean result, a decomposition showing quality effects and load effects separate exactly where the
model says they must. If the full co-option claim is wanted later, it needs a rework knob (a
served-but-degraded decision re-requests early with probability proportional to droop); optional,
not this week.

### Reading the droop sweep honestly

Cells one through four are informative: droop could in principle have compressed admission
control's value to nothing (at full droop a served answer approaches autonomy, so the lever's
worth must come from the waiting cost alone), and it did not. Cell five is one-sided by
construction: droop harms only the direct arm, so supervisory-over-direct could not have flipped;
report it, but do not count it among the orderings that carried risk. The C3 pilot instability
should stay in the ledger as a SCOPE BOUNDARY, not an error to bury: CR-30's invariance claim is
"at the shipped operating points," and C3 is where the armor has not been tested. And the
goodput magnitude-stability is the right lead, with its attribution said aloud: it is stable
because admission control operates on booking arithmetic, which is quality-blind, so the
invariance is a mechanism feature rather than a fortunate constant, and saying why preempts the
too-good-to-be-true read of five numbers inside 0.02 of each other.

### Q1: a subsection, and specifically a table

Your instinct is right and the form matters more than the length. Not an appendix (the record is
load-bearing for believing the survivors; buried evidence does not confer credibility), not a
paragraph (six structured events compressed to prose invites the "they buried it" reading). A
half-page methods subsection whose body is a table: one row per registered claim, columns
registered / falsifier / outcome (gated, refuted on own falsifier, retracted, cut pre-tier,
amended pre-result) / where recorded. Include the two instrument repairs as rows; instruments
caught by adversarial review are the strongest single evidence the loop has teeth. The table
format is the point: it shows the DENOMINATOR (how many registrations, how many died), which is
the only thing that distinguishes a pre-registered loop from survivorship plus good manners. No
adjectives anywhere in the subsection; rows and counts carry it.

### Q2: nothing jumps the queue; two items ride in parallel at zero cluster cost

Run teleop_price.sh and droop.sh (with the O4 amendment, which is textual). Nothing I have goes
ahead of them. Two things cost no cluster time and should happen while they run: the centerpiece
contour overlay from the foundations review (predict the crossover contour from n*(rung) plus
link arithmetic and draw it over the measured phase diagram; existing CSVs, one figure, and it is
the picture that makes the sufficiency thesis visible on the paper's own centerpiece), and the
one-sentence C3 scope line above. After that, run and stop asking is the correct plan.

## Round 13 (2026-08-22, the coordinator's round 13)

### Scoreboard on CR-27, stated precisely, because "the pump is refuted" is half true

What died: the CHANNEL-COUPLING clause, that retry re-offers synchronize to the fade's recovery
edge. D2 kills it cleanly: the jitter gain on the memoryless channel (+0.040, +0.049 at t over
30) is as large as on the bursty one, so the fade is one way to co-queue vehicles and not even a
necessary one. What lives, now twice gated: deterministic holds preserve cohort phase-locking
among whatever the queue co-abandons, and dissolving that phase-lock buys goodput on both
channels (P2 on GE, D2 on Bernoulli). The valve and the reply-rate channel stand as before. So
the surviving account of the original contrast is: rate/reply shift, plus determinism-cohort
damage that any co-queueing event feeds, plus blind booking to convert clusters into dead
capacity. Two items follow. First, the manuscript sentence ("wait at least the floor, and do not
wait exactly the floor") is right, correctly anchored on Metcalfe and Boggs for randomization's
original reason, and it is the best one-sentence design product this contrast has produced.
Second, my own Round 7 registration owned: I proposed the notification SHARE statistic that
CR-26's P1 refuted, and the statistic was ill-posed past collapse (negative unconsumed share).
The direction I registered (signal worthless unconsumed, valuable consumed) is what the data
show; the instrument I specified for it was wrong. That is my fourth instrument-adjacent error in
this review and it goes in the same column as the others.

### The zero-cost cell that closes the five-death ledger

D1/D2 already contain both channels at wide jitter and matched mean. The cross-channel DiD at
wide jitter is the original contrast NET of the determinism-cohort component; if what remains
matches the reply-rate share the bench and the pin measured, the contrast is fully decomposed
into three audited parts (rate/reply, determinism-cohort, valve) and the saga ends with a
complete accounting table instead of a sixth mechanism. One re-read, no compute. If a residual
remains beyond the reply-rate share, THAT is the unexplained regularity, now with a size.

One caution before the paper states P1's null explanation as fact: "the channel's burst variance
drowns the retry's contribution in the delivered-stream Fano" is a post-hoc account of an
instrument failure. It is checkable on the bench in an afternoon: inject a known cohort component
on top of an on-off stream at GE-120 parameters and report fano_window's resolution at that
operating point against the cohort size the retry produces. State the drowning explanation with
that power number or state it as conjecture.

### The MPE convention: right in kind, wrong in constant, and the timing has a cost

Relative-for-rate-metrics is correct; an absolute 0.03 on a 0.05-scale metric encodes "only
60 percent changes matter," which nobody intends. But your own analogy yields six percent, not
three: 0.03 absolute at the 0.5 calibration scale is 0.03/0.5 = 6 percent OF VALUE, and "three
points on a probability" conflates points with percent. Adopt MPE_rel = 6 percent of the control
arm for rate metrics, which preserves the established gate's implied stringency at its
calibration point. Consequences exist and are healthy: the n=4 damage (8.8 percent) gates either
way; the 5.2 percent jitter recovery gates under your 3 and fails under 6.

On timing: a threshold chosen after unblinding cannot adjudicate the data that prompted it, both
readings written down or not. The repair costs nothing here: declare the 6 percent convention
FORWARD for all rate-metric gates, and mark the already-seen cells "ungated under the
pre-existing rule; convention amended after unblinding." Since the n=4 cell is retired anyway
(its account is dead and D2 shows the phenomenon cleaner), the conservative treatment preserves
the gate's meaning at zero cost. General rule for the ledger: thresholds are registration
content; amendments apply forward only.

### CR-26: the third lever is admit-plus-AIMD as a unit, and plain admit needs a warning label

The result is stronger and stranger than the registration: a refusal signal with no response
rule COSTS 0.131 of goodput at twelve assets. The mechanism is the fold arithmetic reaching into
the policy lever: admit's short hold (min(2 lat, P) = 8 against a standing 43) is a fast retry
in disguise, and at high span the refusal-shortened cycle is an accelerant at exactly the spans
where admission control is needed most. With the response rule the same signal is worth +0.268
over plain admit. So the lever the paper ships is admit-plus-AIMD as a unit; plain admit gets a
scope line on the old results (its advantage inverts past the span where the shortened re-ask
cycle overloads the console) and the doctrine sentence writes itself: a refusal without a
client-side rate rule is not admission control, it is load acceleration with better manners.

### The paired-helper bug: name the genus and close the class

Three instrument-class defects now share one shape: a convention calibrated on the first use
case silently misapplied to the second (Fano windows sized inside the dwell; MPE calibrated at
0.5-scale applied at 0.05-scale; blocks-won counting positives on negative effects). The fix for
the instance is done; the fix for the CLASS is a fixture file that runs every gate helper
against synthetic negative-effect and rate-scale cases with known answers, the same pattern as
the estimator ground-truth tests. One file, and this genus stops recurring.

One audit line is still owed, and I am required to ask for it: "no published number changed"
covers the manuscript, but the REVIEW record is also a record. The batch-7 and batch-8 tables
reported to me carried consistency counts on negative contrasts (the CR-23 v2 ladders, B3, the
attribution steps). State explicitly which reported tables passed through the buggy generators
and re-state any affected consistency columns, even if every verdict survives. The burden here
is verification, not probability.

Nothing to add ahead of the resubmitted rate and stall or the queued teleop_price and droop; the
plan stands.

## Round 14 (2026-08-22, the coordinator's round 14)

### Acknowledgments, compact

MPE at 6 percent forward-only: adopted correctly, and your sentence ("the constant is
load-bearing on precisely the cell that raised the question, which is the reason not to apply it
there") is the discipline stated as well as it can be stated. Audit line: closed; two macros,
both the n = 4 AIMD clears, and the 13-to-19 correction leaving 59.4 percent against a 60 percent
floor is noted as the kind of margin the fixture file now protects. The attribution-table defect
is named correctly as worse in kind: a consistency column that could not fail was not a
measurement, and "happened to be true" is the epitaph for a whole class of dashboard statistics.
The t = inf find is the worst failure class a gated pipeline can contain (a null contrast
reporting maximal significance); one cheap closure remains: grep the results archive to confirm
no reported t was ever inf, one line, then that file closes. Pinning the shipped `backoff_mean`
rather than a re-model of it is exactly right and worth keeping as fixture doctrine.

### HQ1: not noise, not your coincidence either; you matched the wrong constant

The arms in the residue table are RETRY arms at rung 3. The paper's own closed form for those
cells does not put the threshold at 6.45 (that is the no-retry, clear-link constant, wrong on
both counts). Computed per arm: at pair mean rho = 4, n_c is 5.86 Bernoulli and 4.81 GE; at mean
10, 7.27 and 5.96; at mean 18, 9.14 and 7.50. So first, index the table by which pair fed it,
because the reading depends on it. If the mean-4 pair: the flip between 5 and 6 brackets the
BERNOULLI arm's own crossing at 5.86, and the story is that the reference arm crossed its
threshold, not that "the dwell reverses at n*."

The mechanism candidate I would register instead of yours: jitter's value is single-peaked in
congestion. Near idle there are no collisions to prevent (your own n = 4 rung 0 cell read
+0.0000); near the threshold, collisions are costly and the server still has idle to lose, so
timing matters most; at saturation the server is never idle and arrival timing is irrelevant to
throughput, so the value falls back toward zero. The residue is then the DIFFERENCE of two
single-peaked curves offset by the channel threshold gap (4.81 against 5.86), which produces
exactly the observed pattern: positive below both peaks, negative once the Bernoulli arm hits its
peak while GE is already past. Your drain/persist story and mine agree at n = 4 (positive) and
DISAGREE at n = 10: yours says the residue stays negative, mine says both channels are saturated
and the residue returns to zero. Register both predictions before the run; n = 10 discriminates.
And the stronger test costs one more axis: the flip location must MOVE with the pair mean by the
closed form (near 5.9 at mean 4, near 7.3 at mean 10 if it tracks the Bernoulli crossing, near
6.0 if it tracks the GE one). If the flip tracks n_c(rho), the residue is a second-order
mechanism wearing the paper's own arithmetic; if it stays at 5-to-6 regardless of mean, neither
story survives. Do not write "unstable nuisance"; write nothing until the pair index is known.

### HQ2: right instrument, wrong statistic, and no circularity if you aim it correctly

Measuring dispersion does not beg the question PROVIDED it is measured on the deterministic arms
only: the jitter arms are the intervention, and the return-time structure of co-abandoned cohorts
under deterministic holds is a property of the baseline, not of the thing being tested. The
statistic should not be a variance, though: use collision multiplicity, the peak number of
cohort members returning within one service time (1/mu), because that is the quantity the damage
mechanism consumes (k arrivals in one service window is k-1 forced waits). Define the cohort
operationally (abandonments within one service time of each other), record each member's next
arrival, report the multiplicity distribution per channel on the deterministic arms. Falsifier:
if GE multiplicity is not materially lower than Bernoulli multiplicity, the born-scattered
account dies. And the same measurement closes the P1 file: bench_fano proved the instrument
could see a K = 2 cohort on the bursty stream, so P1's null now needs a cause, and "the GE
cohorts arrive pre-scattered, multiplicity near one, nothing for jitter to dissolve" is that
cause with a number attached, or it is refuted by the same run.

### HQ3: no third metric; the pair you registered already spans the space

served_per_step arbitrates inflation (it cannot be manufactured); success and arrived_frac
arbitrate whether the served requests were the ones that mattered, and CR-31 already shows
success null at every span, which bounds the deadline-weighting hypothetical from above. A
deadline-weighted service metric invented now, after the goodput result, is exactly the move the
registration discipline exists to prevent: your wariness is the correct answer to your own
question. The admissible middle ground: metrics that predate the question (serviced-wait p95,
operator_goodput_late, both in metrics.py since the CR-7 era) may be READ as descriptive
diagnostics in the write-up, but nothing new may gate. And the stake is shared: my doctrine
sentence ("a refusal without a client-side rate rule is load acceleration with better manners")
was built on the goodput inversion. If served_per_step shows no gated negative at 8/10/12, my
sentence is withdrawn with yours, not softened. Registered here.

## Round 15 (2026-08-22, the coordinator's round 15)

### HQ1 closed, and the small discrepancy has a clean source

Your GE thresholds are right and mine were stale. 3.75-family over d = 0.798 gives 4.70 / 5.83 /
7.33 exactly, so the difference is not burst_len handling: you used the measured two-way delivery
at the operating point and I used the 0.783-grade handshake estimate from the d(L) table. Yours
is the correct constant. One sentence worth keeping from the gap: realized delivery ABOVE the
empty-queue handshake value (0.798 over 0.783) is the forward-path conditioning signature
(retries drawn while the chain sits in a good dwell deliver above the marginal), measured
incidentally and pointing the same way the pin ladder did. Your mea culpa names the genus
correctly: matching the memorized constant instead of computing the governing one is convention
drift transplanted from code into reasoning, and CR-33's design (both accounts plus the
moving-flip test that can kill both) is the right execution.

### HQ2: the fourth account, my fifth instrument-adjacent error, and two free signatures

The confound you flagged is mine to own: I specified collision multiplicity without the rate
normalization, and E[k | k >= 1] rises mechanically with delivered rate, so a channel delivering
25 percent more reads as more clustered at identical phase structure. That is the fifth member of
the genus and the first one I contributed in specification rather than in reading. Your
`arrival_excess` is the correct repair; the Poisson conditional mean lw/(1 - exp(-lw)) checks
out, and dividing by it at the arm's own rate is the only cross-channel-comparable form.

The two-synchronizers-in-series account is the first that carries all four facts, and the
memoryless row is the cleanest single number the desync work has produced: deterministic holds
put about 10 percent excess concentration on a clean link and randomization removes ALL of it
(1.096 to 1.001, 1.099 to 1.011, statistically Poisson). That pair of cells is manuscript-grade
on its own. Two signatures the account implies that CR-34 does not yet register, both cheap:

- P4, dose in the gate: the jittered GE residual (1.042, 1.083) should GROW with dwell (the
  downstream synchronizer strengthens with L) and collapse toward 1.0 as L shrinks toward the
  service time. L in {14, 40, 120} at one pair mean.
- P5, saturation in the width: the residual should be FLAT in jitter width (a synchronizer
  downstream of the hold cannot be reached by any amount of upstream randomization) while the
  memoryless excess pins at 1.0 at every width. Width ladder at one mean, one dwell.

Together they make the account's signature unmistakable: a residue that scales with the channel
and ignores the knob. If either fails, the series picture is wrong in a named direction.

### The window lesson, generalized, and its backward reach

Setting the window to the correlation time was backwards for a reason worth stating as doctrine:
the readout window belongs to the MECHANISM's timescale (service time, where collisions cost),
not the channel's (dwell, where the channel's own variance peaks and the statistic's power
dies). The general rule joins the fixture doctrine: a deployed instrument SETTING is
registration content and needs its own bench point, exactly as the helper needed its fixtures.
Two pieces of backward reach to record: the absolute Fano values read at w = 120 (the batch-7
table: 5.77, 6.48, 6.13, and the 1.76 floor) inherit a bias flag from the 1.307 overshoot, so
none of them should be quoted as magnitudes; the paired, same-direction conclusions read through
them (mg and ge share the clustering) survive qualitatively because both arms overshoot
together. And one line still owed: state the deployed window of `arrival_excess` itself and its
bench point, under the same rule, before CR-34 is read.

### The hard question: undecided is honest, and here is the test that says so

Retracting the P1 refutation as "void at the registered instrument setting, re-registered on a
bench-validated instrument before its tier data were read" is not salvage; it is the K1 rule
applied with the symmetry that makes it a rule. Instrument invalidation is direction-blind: when
the message clock died you retracted a GATED POSITIVE the old instrument had confirmed, and a
ledger that has paid that cost in one direction has standing to collect it in the other. The
salvage test has three prongs and all three come back clean: the power check was pre-committed
before its answer was known (audit item 2 in Round 8, demanded again in Round 13 for the
drowning sentence); the new status is undecided, not confirmed (the pilot excess table stays a
pilot and nothing in the manuscript may cite it as the decider); and the replacement instrument
was validated against injected ground truth rather than tuned until it agreed. Conditions to
keep it that way: the manuscript language is void-not-refuted-not-confirmed; the re-run window
is chosen from the bench power curve and registered before reading; and the scoreboard entry is
corrected rather than deleted, because the Round-13 verdict was a compound and only part of it
dies. What D2 killed (the fade edge as THE synchronizer, jitter worthless without a dwell)
stays killed on goodput evidence that no Fano window touches. What revives as undecided is the
weaker gate clause, now the fourth account's core, with tier pending. And one share of the
mis-scoring is mine: in Round 13 I let P1-at-120 stand as supporting evidence for "the pump is
refuted" while demanding a power point only for the drowning sentence next to it. The rule I
should have applied, and the ledger should now state, is that a null through an unbenched
instrument setting supports nothing, in either direction.

Status acknowledged: six batteries running, HQ3 closed as accepted, nothing to put ahead of
what is queued.

## Round 16 (2026-08-22, the coordinator's round 16)

Verification performed before writing: reproduced the bench closed form independently (0.9726 and 0.9672 both confirmed); checked the +0.268 closure against report/gen/aimd_numbers.tex (admit 0.449, aimd 0.716); read the rewritten abstract, results paragraphs 415 to 421, and the new Discussion lever paragraph in the working tree; read the gate fields and success control values in report/gen/rate_numbers.tex and aimd_numbers.tex; read the metric definitions in src/sandtable/metrics.py; recomputed the null floors for the excess statistic under three microstructures.

### 1. CR-26's doctrine sentence: withdrawn, as registered

The condition attached in Round 14 was that the sentence dies if CR-31's served_per_step shows no gated negative for admit against refund. The battery shows no negative at all, gated or ungated: +0.9, +3.3, +2.8, +2.3, +1.8 percent across the span ladder. The sentence is withdrawn. Not scoped, not softened. The console is not overloaded by a refusal; the -0.131 inversion was the denominator moving; and the only surviving limb is the demand clause, +32.4 percent asking at t = 75.6, now correctly attributed to re-consultation cadence rather than to console harm.

Two notes on the way it died.

The confession with teeth. I coined "short hold = fast retry in disguise." I have owned the retry denominator lesson since Round 2, and CR-23R formalized it: a treatment that changes the asking must be read on the rate. I named the mechanism a retry, in those words, and then priced its harm on the one metric the retry rule says is uninterpretable under retries. You call this failure class a rule derived for its first use case and not carried to the second, and you charge yourself with never carrying it to policies. My instance is worse: my own sentence contained the carry instruction, and I did not execute it on myself.

The accounting that makes it cheap. The sentence carried its death condition from the round it was registered in and paid out one round later. The counterfactual is an unpriced doctrine sentence in a shipped paper, found by a referee. Note also what the gate contract did in this battery, because it deserves a sentence in the methods subsection: the admit-refund service differences run t = 4.8 to 13.7 and gate nowhere, because +1.8 to +3.3 percent sits under the materiality floor. The correct reading of the service column is statistically resolved, materially null. Without the MPE convention adopted two rounds ago we would now be arguing about whether admit serves more. That is the convention's first save at full price.

The manuscript's epitaph at line 419, "The console was never overloaded by it. The metric was," is correct and I endorse it. If a replacement doctrine is wanted: a refusal policy shapes the asking, not the serving; read policies on absolute rates, and reserve the ratio for the thing it actually measures, which is the requester's experience.

### 2. The AIMD correction, verified

The closure closes. Goodput is an identity in the two rates: served falling 4.0 percent against requests falling 40.9 percent multiplies the ratio by 1.62, and the measured pair 0.449 to 0.716 is 1.59. Within the rounding of the published percentages the identity accounts for the entire +0.268, and the service term's contribution is negative. There was never anything in that number for a throughput story to be about. Worth printing as one line in the correction: the two absolute rates reconstruct the headline to within rounding, with nothing left over.

I also confirm the direction claim: the contamination was knowable in advance, in both directions, from the same rule. A refusal inflates the denominator of the arm it is applied to; a rate rule deflates it; the first made plain admit look harmful and the second made AIMD look heroic, and both were the same mistake pointed opposite ways.

### 3. Hard question 1: is "serves less, wins more" a reach?

Verdict: the description is defensible and the rewrite as executed is mostly honest. It is not a strengthened result; it is a smaller result of a better kind, and the text largely says so. But there are three places where it tips toward reach, and one of them is exactly the salvage pattern you asked me to watch for.

First, what I checked and endorse. The results structure shows the artifact and then dissects it (the goodput ladder at 415, the contamination paragraph at 417), which is the honest order. The abstract no longer carries +0.268 anywhere. And the abstract's new generalization sentence, "Every span-of-control number measured as a ratio of served to requested is inflatable by any policy that changes the asking, and the policies worth recommending all do," is the best new sentence in the paper. It converts the correction into a field-level methods contribution: every fielded console this sponsor will ever meter reports exactly that ratio. A reader who never saw the dead headline would write that sentence from the table alone, which is the test for whether a reframe is a reading or a rescue. It passes.

The three tightenings.

(a) The cell splice. "Asked forty percent less, does a few percent less work, and wins more missions" stitches three cells: the forty percent is n=12, where the success gain is +0.021 on a control of 0.946 and sits under the 0.03 success materiality floor; the wins are gated at n=10 clear (+0.044 on 0.881) and n=8, n=10 jammed. The abstract names its spans (at twelve, at ten), which is transparent stitching; the results sentence does not. Make it match: asked a third less at ten where the gain gates, forty percent at twelve where the baseline already wins 0.946 and the remainder is below materiality. Nothing is lost and the referee's best sentence is gone.

(b) The ceiling, and the scale registration this forces. Control successes are 0.800, 0.881, 0.946 across 8, 10, 12. The raw gain peaks at ten, but gain over available headroom is 18, 37, 39 percent: monotone increasing. So whether the rule's value is single-peaked in span or monotone deep into saturation depends entirely on scale choice, and the mechanism story you tell will differ accordingly. Register the scale before the mediation battery reads out (for a thresholded outcome this close to ceiling I would take headroom-normalized or log-odds), or the story gets to pick its scale after seeing the data, which is precisely the self-flattering instrument choice you asked me to police in Round 15. Same genus, outcome side.

(c) "Undersells it" is defensible only while welded to the reason the same sentence gives (a load-reducing lever is a different recommendation type than an extracting one, and for a sponsor staffing consoles the better type). Given baselines of 0.88 to 0.95, the load cut is the primary benefit and the success bump is the near-threshold bonus. The strongest honest form is: never loses above collapse, asks vastly less, and adds gated points near the threshold spans.

The mechanism, and your discriminator. Split the mechanism in two, because half of it needs no experiment. At the spans where the rule acts, served_per_step is capacity-pinned, so the marginal request's fate is abandonment; a rate rule removes marginal requests; the service it forgoes is inframarginal. That is queueing arithmetic, and the data already display it: service down 4 while asks fall 41. State it, do not test it. What is genuinely open is the routing of the success gain, and there your proposed discriminator does not discriminate. At saturation, any request suppression, targeted or blind, harvests the abandon bucket first, by conservation: asks fall 41 points, service falls 4, the difference must come out of the non-served buckets. A pure dumb throttle passes your test. Worse, abandon_queue_frac divides by n_request, the exact denominator that burned us twice this round; your own comment in metrics.py at the abandoned_per_step definition already rules the fraction out, and the per-step metric you built is the one to print. Print it as bookkeeping, not as the test.

The test that discriminates is the one the paper already owns: mediation. The two live routings are quality composition (suppressed vehicles spend the wait in autonomy at 0.70 instead of stalling into fallback at 0.50) and tempo (vehicles that do not stop to hold arrive, and arrived_frac carries success, which is the paper's own 72/28 machinery from the force-ratio study). Register: the share of the success gain at the three gated cells that arrived_frac mediates, on the declared scale, with both branch sentences pre-committed: mediated, "the rule keeps vehicles moving and movement converts at the objective"; not mediated, "the outcome gain is real and unexplained, and ships labeled as such." And yes, register before looking, precisely because you know the direction you want: that condition is not a reason to hesitate about registration, it is the entire case for it.

### 4. Hard question 2: the six goodput sites

Answer: (b), and it is cheaper than it looks, with (a) as the interim label while it runs. But the class is metrics, not sites, so do the desk half first.

Desk audit, no compute, today. The denominator classes in metrics.py: n_request (operator_goodput, operator_goodput_late, abandon_queue_frac, abandon_link_frac), n_serviced (wasted_frac), live vehicle-steps (hold_fraction, attrition-endogenous), total_steps (served_per_step, requests_per_step, abandoned_per_step: the clean family), initial counts (loss fractions), assault size (arrived_frac, already documented for force sweeps). Any quoted between-treatment contrast on the first three classes is a class member wherever the treatment moves the denominator. That table catches sites that do not say goodput.

Then triage by direction before any re-run, because the bias direction is computable per pair and it sorts the sites into three piles. Corrected already: the admit-refund ordering (line 337 now carries the ratio-effect sentence and the served counts) and the AIMD sites. Conservative, survive a fortiori, re-read only for magnitude: the staffing-curve garnish (admit holds goodput at eight where blind collapses: admit asks more, so its goodput is biased down, and it wins anyway); the rise of the loss hump to its peak (retries inflate asking as loss grows, biasing goodput down at high loss, against the rise). Suspect, in the knowable direction, blocked from shipping as-is: the self-collision decomposition at line 409 (the cost of self-collision is read as the goodput drop of a retry-bearing arm against a retry-free arm, and retries inflate the denominator by construction, so the goodput magnitude overstates the service-relevant cost; the fold band itself is safe, its success DiD is 32 of 32); the hump's peak location (if denominator inflation dominates past the peak, the served_per_step peak sits later than the goodput peak, and the quoted peak drop probability moves); and the burst DiD.

The burst site is the live inconsistency, and it is one sentence in the current working tree. The Discussion paragraph still says "the claim we make is about the console's throughput" over a goodput difference in differences, in the same revision whose abstract teaches that this ratio is not throughput. Refund changes the asking on both channels and the channels arm retries differently, so the DiD has denominator content. My direction read says the bias is probably conservative (clustered refusals on the fading link inflate that arm's asking most, understating the fading-link delta, and the claim is that the fading-link delta is bigger), but probably is not a word that belongs under a sentence with throughput in it. Until the served_per_step pair lands, reword to the serviced-over-asked ratio; when it lands, restate on the rate.

Also from the same pass: the ordered guidance sentence still reads "fix the admission policy, then staff the consoles, and only then buy autonomy." The third lever is missing from the paper's own marching order. It is vehicle software, free below collapse, and needs no estimates, which by the Discussion's own deployability argument places it second: fix the admission policy, put the response rule on the vehicles, then staff, then buy autonomy.

What is not at risk: the first lever. Its headline is mission success (blind to admit at the centerpiece), its refund-share decomposition is success-based, and success has no denominator to move. The worst case for the whole sweep is magnitude language on garnish numbers, not a conclusion.

The permanent fix, so there is no seventh site: mechanize the rule out of human memory, where this genus lives. Gate eligibility: operator_goodput is not gate-eligible for any pair whose requests_per_step difference exceeds its own materiality floor; the harness auto-emits served_per_step beside every goodput contrast. Fixture: a synthetic pair with fixed service and inflated asking that must refuse the goodput gate and accept the served_per_step gate, in tests/test_gate_helpers.py with the other five genus members. You named this member six; the ledger's methods subsection now has the full arc, rule derived at CR-23R for retries, missed at CR-24, missed again for policies, and finally applied to the paper's own abstract, which is the strongest possible advertisement for the workflow the subsection describes.

### 5. The bench discharged its question and exposed the next one: the null's K

The bench is verified (I reproduce 0.9726 and 0.9672 from the closed form independently) and it did what bench points are for: both CR-34 predictions moved before the data. The on-off result is more than calibration, it is a null-model demonstration: the downstream gate alone manufactures 1.026 to 1.032 from a source with no cohort, which is the two-synchronizer architecture exhibited in miniature by the instrument itself.

But the amendment is scored against the wrong null, and the error is the same shape as the one it corrects. K=1 is a single pooled Bernoulli stream. The deployed arms are n vehicles. The no-cohort null for them is n independent streams, and the floor depends on microstructure that K=1 does not represent:

| null microstructure, w = 7 | n=4 cell (lw = 0.49) | n=5 cell (lw = 0.63) |
| --- | --- | --- |
| pooled per-step Bernoulli (the bench, K=1) | 0.9726 | 0.9672 |
| n independent per-step streams (K=n) | 0.9932 | 0.9935 |
| n independent renewal streams, at most one ask per window | 0.9517 | 0.9537 |

The third row is not exotic: the decision interval is jittered on 11 to 33 steps, all above the 7-step window, so absent retries a single vehicle cannot arrive twice in one window, and the count is at most one per vehicle. The spread across plausible nulls is four points, the same size as the residuals under dispute. Concretely: the pilot's memoryless jittered 1.001 reads +0.008 above the K=n floor and +0.049 above the renewal floor; the GE jittered 1.042 reads anywhere from -0.005 to +0.037 depending on which floor and whether the K=1 gate bias transfers. P1 has now been read against three references in three rounds (1.0, then 0.973, now a bracket) with zero new data. The measurement has not moved once. The reference has moved every time. That is the definition of an unfrozen null.

So freeze it by simulation, not by closed form, because the model already owns the exact null: n vehicles through the full pipeline with per-vehicle independent channel chains. That arm keeps every within-vehicle mechanism, including retry echoes, which matter here for a specific reason: the default backoff is 4 steps, under the 7-step window, so a retry echo is the one way a single vehicle produces an in-window pair, and no closed form on this table represents it. Excess above the independent-chains arm, channel-matched and cell-matched, is purely cross-vehicle synchronization, which is exactly what CR-34 is about. If the cohort battery now running crosses independent chains with the jittered arms, the null is already in flight and costs nothing; if it does not, it is one small 2x2x2 addendum. Either way: CR-34 is not to be scored against any closed-form floor, and P2's amended margins (+0.016, +0.051) are as provisional as the +0.042 and +0.083 they replaced, because they stand on K=1.

My own entry in this section: in Round 15 I endorsed "full Poissonization" against an unbenched reference of 1.0. The reference has since moved twice without new data, which is the proof the endorsement was premature regardless of where the simulated null lands. Sixth instrument-adjacent item on my card, and the same lesson I was busy generalizing at the time: a deployed reference is registration content, exactly like a deployed window.

### 6. CR-32: the verdict stands, and the writeup already deserves to ship

This is the paper's best external point and the registration discipline is what makes it one: the two-signs shape was registered before the source text was obtained, it could have failed, and it did not. With 4 to 8 up at p < .001 and 8 to 12 down at p = .006, a monotone-decline attention account is refuted on this dataset, not merely unsupported; that wording is earned. The partial falsifier is handled honestly in the manuscript paragraph (the operators did lose something, and the text says so), and the replacement arithmetic is the paper's mediator split found in human data: the fleet's platform output more than doubles while the console-mediated output does not move, which is the 72/28 story with people in it. The closing sentence of that block, that the interior optimum is not an artifact of simulating an operator because it appears when the operator is a person, is the right load-bearing claim, and the scoping (shape, not location; no n-star computable) is exactly right.

Two light notes. "Twelve robots performed like four" leans on p = .08; the text prints the p first, so it reads as description rather than claim, and it should stay that way; the two significant opposite steps carry the weight. And the perceptual-search monotonicity was not part of the registered prediction; the manuscript's "same intervention, same qualitative result" framing is consistency, not confirmation, and the ledger should keep that distinction even though the paper's phrasing is fine. The provenance practice, Internet Archive recovery with full numeric provenance in the bib entry, is the standard the other 68 citations should envy.

### 7. Scoreboard and the queue

Mine. The CR-26 doctrine sentence is withdrawn per its registration; the residue that was an error rather than a priced death is that I failed to carry my own retry rule across my own renaming of a hold as a retry. And Round 15's Poissonization endorsement was scored against an unfrozen reference: process error independent of outcome, sixth instrument-adjacent item.

Yours, caught this round. The K=1 null is mis-specified for n-vehicle arms and the amended CR-34 margins inherit it; the null must be simulated, and the three-reference history of P1 is the argument. The HQ1 discriminator as stated is conservation-trivial at the spans that matter and is named on the metric your own code comment disqualifies. The success-gain gradient flips shape under scale choice this close to ceiling, so the scale itself needs registration before the mediation battery. The Discussion still sells the burst DiD as throughput on a goodput number, one revision after the abstract taught why that word is wrong there, and the ordered guidance omits the third lever.

Yours, endorsed without reservation. Following CR-31's falsifier into your own headline and paying list price is the most valuable entry this ledger has: the methods subsection can now show the registered contract correcting the paper's own abstract before any referee saw it. The abstract's generalization sentence is a contribution in its own right. The Lewis writeup needs nothing from me.

Queue discipline: nothing jumps. The six batteries land first. The simulated null (or its extraction from the cohort battery) lands before CR-34 is scored, because scoring against K=1 would just be the fourth reading of the same two numbers. The goodput re-read sweep (burst pair, self-collision, hump peak, jitter flatness line, staffing garnish) runs after the batteries and before ship, with the two one-sentence manuscript fixes (throughput wording, ordered guidance) available today.

## Round 17 (2026-08-22, the coordinator's round 17)

Verification performed: recomputed the three closed-form floors at the five measured rates and re-based the P1 residuals against each; confirmed from src/sandtable/c2.py line 503 that the multiplicity counter increments only on up_ok, so the deployed statistic reads the delivered stream; read the new abstract sentence and results paragraphs 423 and 425 in the working tree; read the loss decomposition macros in report/gen/rate_numbers.tex.

### 1. P1's refutation: certified, sign-robust, magnitude pending

I re-based the reported residuals against all three null microstructures at each cell's own rate:

| n | lw | vs Bernoulli (yours) | vs K=n | vs renewal |
| --- | --- | --- | --- | --- |
| 4 | 0.429 | +0.019 | +0.0002 | +0.038 |
| 5 | 0.512 | +0.031 | +0.008 | +0.043 |
| 6 | 0.618 | +0.041 | +0.014 | +0.047 |
| 8 | 0.862 | +0.052 | +0.018 | +0.047 |
| 10 | 1.126 | +0.059 | +0.019 | +0.046 |

The refutation is sign-robust at n >= 5: positive against every floor a no-cohort closed form can offer, and with your t of 24 to 52 the standard errors are around a point or two of the third decimal, so even the smallest reading gates. P1 is dead and stays dead under any null. Two qualifications for the ledger. The magnitudes you reported are the largest of the three readings; against K=n they shrink threefold, so the kill line should say sign-robust with magnitude pending the simulated null, not +0.019 to +0.059. And the n=4 cell sits at +0.0002 against K=n, which is why it came back ungated: at idle the jittered stream IS fully scattered relative to the null that matches its own microstructure. The residual is zero at idle and grows with load, which localizes the un-scattering agent at the console, not in the clock. That is the right shape for everything downstream.

### 2. The check you asked for: the floor-free reasoning is wrong, and the conclusion survives on a different leg

You asked me to break "at matched rate the floor is common to both channels" if I could. I can, twice, and your own artifacts do the breaking.

First, the statistic reads the delivered stream. c2.py line 503: the bin increments only when up_ok. And your bench applied the mask to the source before computing excess, so it benched the same convention, and it measured the consequence: at matched rate and K=1 the memoryless floor is 0.980 and the on-off floor is 1.026. The floors differ by channel by construction of the instrument. That is what the gate-manufactures-clustering finding means. A delivered-stream gap at matched rate is not floor-free; it is a difference of two floors plus a difference of two cohorts.

Second, even the offered stream would not have a channel-common floor, because every arm retries and the backoff is 4 steps against a 7-step window. A single vehicle inside a bad dwell re-asks every 4 to 5 steps and lays down a same-vehicle echo train; on a memoryless link failures are isolated and the trains are short. Same-vehicle multiplicity is channel-dependent null content with zero cross-vehicle synchronization in it.

Note also that this round's protection argument and last round's amendment contradict each other: in Round 16 you subtracted the instrument's floor on its own channel from P2's margins, which presumes channel-dependent floors; today's claim is that the floors cancel because they are common. Both cannot be right, and the first was closer.

Now the leg the conclusion actually stands on, which you already measured: the n=4 cell is an internal null control. Whatever channel-dependent floor content exists at deployment, gate bias on the real source plus echo-train differences, it nets to +0.0002 at idle. The protection is empirical, a measured zero at the idle span, not analytic. What remains exposed is exactly one class: channel-dependent null content that grows with load, which could mimic the gap's monotone rise. Two named candidates. Refusal-triggered echo trains: refusals grow with span, on the fading link refusals cluster at recovery edges, and a refused vehicle re-asking on a 4-step cadence writes same-vehicle pairs into 7-step windows at a rate that rises with load. And rate-dependence of the gate bias itself: your bench measured it at two rates near lw 0.5 and found it moves strongly with geometry (five percent at duty 0.8, forty-six at 0.5), so its behavior across the deployed lw range of 0.43 to 1.13 is unmeasured territory.

Three cheap hardeners, in order of decisiveness. (i) Split the multiplicity by requester identity: two bins at the line-503 site, same-vehicle and cross-vehicle pairs. Echo trains are same-vehicle by definition; the cohort CR-34 claims is cross-vehicle. A cross-vehicle share that rises with span is the mechanism with both confounds dead, and the counter change is the same off-by-default no-RNG pattern as the existing bins. (ii) Run bench_excess at the five deployed rates with a source that matches the deployed microstructure (n sparse streams, not pooled Bernoulli): if the gate bias is flat in lw, a constant offset cannot manufacture a growing gap, and the n=4 reconciliation gets a quantitative explanation instead of a shrug. (iii) P6 as registered. If all three land the right way, P2 is confirmed with its confounds executed rather than unexamined, and the matched-rate table becomes the paper-grade version of the claim.

### 3. P6's tree, completed

Your falsifier covers one branch: noretry showing the same excess returns P1 to undecided. The full tree, so every outcome is scored in advance. If noretry collapses the excess, the residual is retry-borne, and the same-vehicle versus cross-vehicle split says which kind: echo trains (same-vehicle, a client hammering, not a cohort) or retry cohort (cross-vehicle, the mechanism). If noretry keeps the excess and stagger kills it, it is standing-cadence alignment, initial phase surviving the jitter. If noretry keeps it and stagger does not touch it, there are two candidates left and the renewal floor separates them: a no-interaction quasi-periodic superposition reads BELOW the Bernoulli reference (0.956 to 0.969 at these rates), so a persistent residual above it cannot be floor misspecification and would implicate genuine queue-mediated coupling, the one candidate worth registering only if that branch fires: service completions re-phasing decision clocks, the server pacing its own clients. Endorse the stagger arm as an independent read; the registration is better for carrying it.

### 4. CR-30: cleared, and one clause owed to the manuscript

Twenty-five chances to reverse, none taken, and the three families move in mechanistically coherent directions: droop taxes every lever that wins by serving (the serviced decision is worth less, so policies that deliver more of them earn less), cannot touch a counting metric, and raises the value of removing the operator, which is the conservative direction for the paper's spine. Endorsed, including the note that the goodput row's contamination runs against the conclusion. One clause is owed: the current sensitivity sentence says the orderings survive and the goodput gain is flat, and does not say that the policy levers' success magnitudes shrink by about a fifth at the strongest droop while the supervisory advantage grows by about a quarter. A reviewer who reruns the sweep finds that in an afternoon. Print the direction: the oracle assumption flatters the levers' magnitudes by up to a fifth and understates the autonomy case, and neither movement reorders anything.

### 5. Hard question: the split is right, and what you implemented is already better than what you asked

You asked whether leading with losses in the abstract while success carries the mechanism sections is having it both ways. What the working tree actually does is lead with the pair: one abstract sentence carrying success and blue_loss_frac together, with the shared reason (fractions of the force fielded, not of the requests made), and a results paragraph stating their agreement as a finding: same peak span, same gated spans, same null. That is the right structure, and it is stronger than a losses-only lead, because the co-movement of an outcome metric and a force metric is itself evidence the levers act on the mission rather than on a meter. Keep it exactly as built.

On the worry itself: you are not over-weighting the survivor, and the defense is that the receipts predate the survival. The identification section already prefers the continuous quantity that success thresholds; Round 16's doctrine already prefers treatment-invariant denominators; the foundations round already argued the sponsor's quantity is what a program buys. blue_loss_frac earns the lead on three grounds that were in the ledger before this battery ran. Write that provenance into the ledger entry and the salvage question answers itself.

Three conditions, all cheap. First, the decomposition must be visible wherever the stack number appears near the third lever, because the macros already exist and a reviewer will do the subtraction: of the -18.4 at eight clear, the discard is worth about -14.1, the notification -1.4, the response rule -2.9. The abstract's phrasing (the two console-side levers, taken together) is accurate; the AIMD section should still quote its own -2.9 so the response rule never borrows the discard's magnitude. Second, the full table travels with the headline, including the weaker jammed cells, and the n=12 jammed n/a needs its reason printed: not-run and not-gated are different absences and a reviewer will assume the worse one. Third, register the pair as the paper's headline metrics for lever claims going forward, so the metric cannot rotate again; the AIMD episode is what rotation costs. And one sentence is owed somewhere in the mechanism sections: WHY queue policy moves attrition, the causal channel (a vehicle awaiting a decision under teleoperation physics is stopped, stopped in contact is exposed, and the levers cut the waiting), so the number is a consequence with a mechanism rather than a fortunate aggregate. The reviewer who cares about diagnosticity is answered by that sentence plus the agreement paragraph.

### 6. Scoreboard and the queue

Mine, standing from Round 16 and vindicated early: the null-microstructure bracket anticipated the control gap item 2 concedes, and the simulated-null demand is now P6. New this round: the delivered-stream identification (line 503) that breaks the floor-free argument as stated, the two load-dependent confound candidates, and the identity-split instrument that retires both.

Yours, caught this round: the floor-free protection is wrong in its stated form (your bench and your counter jointly refute it) and contradicts your own Round 16 margin treatment; the P1 kill magnitudes are floor-inflated up to threefold; the droop sensitivity sentence omits the magnitude direction.

Yours, endorsed: the matched-rate pair design is the best instrument this thread has produced and its n=4 cell is quietly the load-bearing control; the immediate registration of P6 on discovering the omitted control is the protocol working; the abstract pair sentence and the agreement paragraph; the CR-30 read.

Queue: seven batteries running, P6 lands before CR-34 P1 is finalized, the identity split and the lw-sweep bench are the only new asks and both are cheap; the goodput re-read sweep and the two one-sentence manuscript fixes from Round 16 stand; nothing jumps the queue.

## Round 18 (2026-08-22, the coordinator's round 18)

Verification performed: recomputed the patience-buffer depth from the model's own constants at each latency rung; spot-checked the capacity-anchored MPE against all four absrate contrasts; confirmed the P4 collapse limit from the Round 17 matched memoryless cell; checked the CR-37 rho ordering for shape.

### 1. CR-27 P1: my endorsement is reversed, and I am scoring it before excusing it

Seventh owned item. In Round 13 I endorsed "the null control carried the effect and renamed the mechanism," and the contrast that narrative stood on, bursty null against memoryless positive, never existed. It was the blind window reading nothing at the channel's dwell while the effect sat one service time wide, on both links, larger on the bursty one. I had already convicted myself in Round 15 of letting P1 at w=120 support the refutation without demanding its power point; the full bill arrives now: I did not merely under-demand, I helped build the replacement story on the silence of a deaf instrument.

What makes the reversal credible is the protocol, and this needs saying because it is the ledger's best exhibit. The Round 15 ruling held that voiding the refutation was honest only if the re-run window came from the bench power curve and was registered blind before tier data. CR-37 did exactly that and landed 6 of 6 gated at 32 of 32. Had the window been found by scanning until significance, this confirmation would be worthless; because it was derived and then frozen, it is decisive. Refuted at the channel's dwell, confirmed at the benched window, with the voiding step in between priced by the same symmetry rule that once killed a gated positive. Three rounds from mis-score to correction, all on the record.

The rewrite is right: what the memoryless control now carries is portability, a retry cohort that forms and costs with no channel structure at all, not exclusivity. What died with the old narrative is any sentence implying the dwell adds no clustering; it adds a great deal, which is Q1's tension and I take it up there. One small registered note rather than a new conjecture: the rho ordering at n=6 (47, 53, 38 percent at rho 4, 10, 18) is single-peaked with the peak between the retry threshold and the backoff floor, which is where CR-33's value curve wants it; score that inside CR-33's existing battery, not as anything new.

### 2. P4: the growth limb is confirmed, and I am amending my own collapse limb before CR-41 reads

The monotone sweep is clean and I endorse it as gated confirmation of the dwell-scaling limb. Saying in the paper that the collapse limb is untested, rather than rounding the sweep up to the full signature, is the right call and I note it.

Now the amendment, mine to make and registered here before CR-41 lands. As stated in Round 15, P4's collapse limit was wrong: the residual cannot shrink toward 1.000 as L goes small, because CR-34's P1 refutation established that the matched memoryless jittered arm does not sit at 1.000; it sits near 1.009 at this cell (n=6, backoff 18). So the registered scoring for CR-41 is three-way. Landing near 1.009, within gate error, confirms the two-synchronizer split exactly: the channel-gate component vanishes with the dwell and the console-coupling component remains. Landing at 1.000 flat contradicts the CR-34 P1 refutation and reopens it, which would be a finding, not a tidy result. Landing at or above about 1.03 refutes the gate-component reading of the dwell scaling and P4 dies at its second limb after passing its first.

And CR-41 needs its own bench rows before it is read. L enters the measured stream through the mask, so dwell is part of the instrument's operating condition, and L = 1, 2, 3, 5 is a regime the bench has never visited: windows now contain multiple full gate cycles instead of straddling one edge. Run bench_excess at those four dwells, deployed geometry, source-matched microstructure, and publish the floors with the registration. This is the window doctrine applied to its third knob, and it is cheap. On the "most favorable configuration" framing: the fix-arm crowding rises monotonically past L=7, so if L equal to the window maximized anything it is not the total; the cohort term dominates the artifact term. The conclusion you drew (the sweep floor is not the collapse) is right; the intuition offered for it is looser than the data that already settle it.

### 3. The absrate catch: the hole was in my table too

Refund against blind appears on neither of my Round 16 lists. I safed the first lever on success, called its goodput garnish, and stopped enumerating; you reasoned the silent discard could not move the asking; the audit shows it moves it 20.6 percent through the service channel, because a served vehicle finishes its round trip and rejoins the pool sooner than an abandoned one. Both misses are the same lesson at different depths: triage tables must be generated from the arm graph, pairs times metrics, never from grepping the manuscript for quoted sites. My direction logic is vindicated in the one place I applied it (the bias runs against refund, and refund wins anyway, so the published direction was conservative), but coverage is what audits are for and mine had a hole.

The replacement sentence is better than what it replaces, and two of its numbers deserve the page: at sixteen assets the blind console delivers 0.0023 useful services per step against refund's 0.150. That is congestion collapse from undelivered work stated in two numbers: ninety-eight percent of a console's capacity producing answers nobody is waiting for. And the service-side ordering (discard nearly everything, notification immaterial, rate rule immaterial while cutting the asking by half) now agrees across metrics with the success-based refund share, which is worth one sentence of cross-metric agreement in the paper. The ordered-guidance change is endorsed on dependency grounds: the randomized hold needs no console emission at all, the response rule needs refusals emitted, so hold second and response rule third is the correct deployment order, not just a defensible one.

### 4. Q1: the tension resolves under a thresholded cost function, and the discriminator is registerable now

Your (a) and (c) have opposite curvatures and both miss the same structural fact: the console does not price mean clustering, it prices the tail, and the threshold is computable from constants the paper already owns. A cluster of k arrivals reaching an empty queue seats its j-th member after (j-1) service times, and the feasibility rule prices 2 lat + W + S against patience, so the buffer depth is floor((P - 2 lat)/S): 3 at zero latency, 2 at rungs one and two, 1 at rung three, 0 at rung four. Members inside the depth are absorbed free; members beyond it are refused or abandon. The fix-arm crowding in your sweep runs 1.23 to 1.42, which is a mean cluster deep inside a depth-2 buffer, so the dwell's clustering at n=5 and 6 is real and free: reading (c)'s conclusion, with (a)'s warning attached as scope, and a formula instead of a shrug.

The second half is persistence, and it is why the memoryless self-collision gates while bigger dwell clusters do not. A fixed-backoff cohort reforms every cycle: the same vehicles collide, back off by the same rho, and collide again, so a small recurring cost accumulates across the mission. A recovery-edge cohort is transient: formed once by the gate, dispersed by the jittered decision interval on the next cycle. Recurring small collisions gate; one-off clusters under the buffer do not. Note this also explains CR-37 without tension: jitter reduces measured clustering most on the bursty link because the time-averaged statistic is dominated by whichever clusters recur.

The registered discriminators, before G2 lands, as you asked. D1: the priced statistic is the tail, not the mean. The CR-39 bitmask already counts distinct senders per window; emit P(senders per busy window > depth) alongside the excess. Prediction: across your L sweep at n=6 the tail is small and flat while the crowding rises 16 percent, which is why the console does not move. D2: the span crossing. At n around 10 to 12 the recovery-edge cohorts outgrow the buffer and a dwell increment must appear on the clean metrics, with different signatures by policy: under blind it appears as wasted service (useful served_per_step falls), under refund as refusal-and-retry churn (requests_per_step rises while served holds). If D2 lands, the "indifferent to what the link is doing" recommendation gets a span scope from the buffer formula, and the paper trades an overclaim for a closed form: burst tolerance equals patience depth. D3: if G2's served_per_step re-read erases even the memoryless self-collision benefit, then reading (b) was the fact of the matter, the decomposition rewrites on clean metrics, and D1 and D2 are scored against the rewritten baseline. Pre-committed in that order. If D1 fails at n=6 (the tail moves and the console still does not), the buffer account is wrong and I will say so in those words.

### 5. Q2: anchor the rate MPE to the invariant the paper already prices

A reference-relative floor is the right instrument only where the reference's own level carries the meaning, which is true for success on [0,1] and false for a rate whose reference collapses; at n=16 the vacuousness is total, as you computed. Of your three candidates, two fail on structure: better-arm-relative is asymmetric in pair order and still vacuous when both arms collapse; offered-load-relative reinstates a treatment-moved denominator inside the gate itself, which is this month's disease readmitted through the back door. The remaining answer is an absolute floor on the system invariant: served_per_step gates at 6 percent of console capacity, 0.06 times c mu, which is 0.009 per step on one console and scales correctly with staffing. Capacity is treatment-invariant, scenario-known, and the same quantity the collapse-span arithmetic already prices, so the convention is one sentence: a material service difference is one worth six percent of a console.

Checked against everything posted: refund-blind at +0.114 is 76 percent of a console, material; +0.148 is 99 percent, material; admit-refund at +0.004 is 2.7 percent, immaterial; aimd-admit at -0.006 is 4 percent, immaterial; the jammed AIMD losses near -0.015 are about 10 percent, material. Every verdict already published survives the swap, so adopt it forward, run the one-pass retro-consistency check, and if any verdict does flip, report the flip as a finding. Prose rule alongside: print absolute deltas with share-of-capacity, and never percent-of-a-collapsed-base; +6299 percent is true and communicates nothing but heat.

### 6. Q3: the line is an error budget, not a verdict, and your instinct was right here for a sharper reason

Neither pole is the line. A null denominator contrast is significance logic pointed backwards: absence of a gated difference is not evidence of equality, so gate-null cannot license the ratio. But demanding the absolute-rate re-read for everything is paralysis, and worse, it is selection: what ships is whatever happened to get re-run. The line is equivalence logic: a ratio metric is readable for a pair when the denominator's measured bound, the confidence interval on delta requests_per_step, makes the worst-case bias immaterial: bias bound equals ratio level times the CI-upper relative denominator shift, readable iff that bound is at most half the metric's MPE, and the bound prints beside the number. The absolute reading is required exactly when the bound fails, no judgment calls, and ar_gate.py can enforce it the way it now enforces the denominator-contrast rule.

For fanoredo specifically, the withholding was correct on the merits, and for a sharper reason than the one you gave: the shipped guard pins the mean of the backoff draw, not the realized asking, and jitter works partly by cutting abandonment, which cuts retries, which cuts asks. The denominator difference is not noise the design failed to exclude; it is an effect of the treatment working. Expect the bound to fail there, in which case goodput is genuinely unreadable for that pair and served_per_step was always the metric. The requests_per_step columns are already in the battery output, so the bound costs nothing: print it, and the decision makes itself.

### 7. Scoreboard and the queue

Mine: the reversed CR-27 endorsement, scored above as the seventh item; the P4 collapse limb mis-specified at 1.000 and amended here before its battery reads; the refund-blind coverage hole in my Round 16 triage table. Three entries, one round, all caught by instruments rather than by luck, which is the only comfort on offer.

Yours, endorsed: CR-37's blind re-registration executing the Round 15 ruling to the letter; the absrate enumeration finding what both of us reasoned past; declaring P4's untested limb in the paper instead of rounding up; ar_gate's both-signs fixtures; CR-39's outright falsifier and the byte-identical bitmask discipline; CR-40 naming, per site, the claim each re-read can kill.

Yours, caught: the "most favorable configuration" rationale is looser than the monotone crowding that already settles the point; CR-41 lacks bench rows for its new instrument regime and must not be read without them; and the P4 limit you inherited from me needed the 1.009 amendment, which was mine to fix and now is.

Queue: cohsplit, goodredo, dwellow join the running set; the new pre-read obligations are the CR-41 bench rows and the P4 three-way scoring registered above, both cheap; the Q1 discriminators are registered before G2 as requested; the MPE convention and the readability bound are desk changes. Nothing jumps the queue.

## Round 19 (2026-08-22, the coordinator's round 19)

Verification performed: cross-checked the transfer-matrix L=1 null against the Round 17 closed-form memoryless floors; checked the F3 null-subtracted residual against the Round 17 memoryless residual at the same span; computed per-cell utilization for the jitter served_per_step table; recomputed the additive prediction for the L-to-1 limit.

### 1. The moving null, P4's proper burial, and the supersession question answered: neither of us has the limit right

First the cross-validation, because it is the round's quiet good news: the transfer matrix's L=1 value of 0.957 lands inside the band of the closed-form memoryless floors I computed in Round 17 (0.956 to 0.960 at the neighboring rates). Two independent computations, one by transfer matrix and one by closed form, agree at the point where the gate degenerates into thinning. The instrument is now trustworthy end to end, and the estimator-unbiasedness result makes CR-41's sub-window rows readable. The obligation is discharged better than I asked for it.

The growth limb's status is correct as you have it: WITHDRAWN, not refuted, because the admissibility failure is F3's own (the null needs the rate and F3 did not log it), and voiding is direction-blind. That is the third application of the symmetry rule and the first against a result of mine that had already reached the manuscript. Note for the record what died and what did not: the fix-arm crowding rise (0.157 against a null rise of 0.035) survives; the arm-to-arm gap survives best; only the level died. That pattern is Q2's answer arriving as data, and I will use it there.

Now the supersession question, and the answer is that neither my amendment nor your replacement is right. My 1.009 was the wrong basis, as you say. But the bare gate value at L=1, your 0.957, cannot be the limit either, because the residual it omits exists where there is no gate at all: Round 17 measured +0.041 above the closed-form floor on the memoryless channel at n=6. If the jit arm's raw excess fell to the bare null at short dwell, the console-coupling residual would have to vanish exactly when the channel stops helping, which contradicts the memoryless data outright. The structure the surviving numbers support is additive: raw(L) = null(L, rate) + residual(n, rho), with the residual channel-common. And here is the round's strongest single fact, which deserves a sentence in the CR-34 ledger row: your F3 null-subtracted sequence is flat at about 0.045, and the Round 17 memoryless residual at the same span is 0.041. The dwell-matched subtraction on the bursty link recovers the memoryless residual. Everything the dwell appeared to contribute was null; what remains is the same channel-independent console coupling on both links.

So P4 is superseded by P4', registered here before the resubmitted dwellow reads, scored on null-subtracted residuals rather than raw levels, which is Q2's rule applied to its own test case. (1) The jit arm's null-subtracted residual is flat in L within gate error at each logged rate. (2) The fix arm's null-subtracted excess rises with L: the lockstep resonates with the gate, which is why CR-37's contrast is largest on the bursty link. (3) The flat jit level equals the matched memoryless residual for the same n and rho, about 0.04 at n=6. (4) The raw jit excess at L=1 reads approximately null plus residual, about 1.00, not 0.957 and not 1.009. If (1) fails and the subtracted residual still rises, the dwell couples to the cohort itself and the two-component account is wrong. If the raw limit lands at the bare null, the memoryless residual needs a new explanation and CR-34 reopens. One caution flag on a numerical pun: the memoryless jittered excess at n=6 (1.009) and the gate's own null at L=7 (1.009) are unrelated quantities that happen to share three digits; the coincidence has already fed one confusion and should be footnoted in the ledger so it cannot feed another.

One process note, offered once. The P4 paragraph reached the manuscript two hours before a bench that was already on the books as owed against its instrument. The system caught it in hours, but that window is exactly where a referee sits. The rule worth adopting: no paragraph commits on a quantity while a bench obligation against its instrument stands open. The text queue and the battery queue should share that discipline.

### 2. CR-43: a proper death, and the corpse is genuinely load-bearing

Both falsifiers fired against a declared tolerance, the third-and-final clause executed, and the conjecture stays dead. That is the stopping discipline from the Round 7 question working as designed, and it is worth saying that the death is clean precisely because the tolerance and the registration count were declared before the battery ran. The asymmetry in the corpse is the result: zero of 506 runs at or above the predicted hold arrive, so the geometric budget is a true upper bound, while the separating hold slides 0.126 downward as span grows, which is the console eating margin inside the geometric envelope. Geometry bounds; the console decides inside the bound. That two-regime sentence belongs in the paper.

The two-physics result is the sponsor-facing find of the round: pricing the wait by mobility doubles the backoff recommendation rather than weakening it, hold fraction closes 98 percent of its range while success closes 83, and the published physics carries a 40 percent cost at zero hold fraction. Time in stall cannot be the mechanism where there is no stall. One scoping check for the manuscript: the Round 17 causal-channel sentence (waiting is stopped, stopped in contact is exposed) must now be stated as the amplifier, not the base mechanism, because the two-physics contrast proves a shared-server cost that survives with the stall channel removed. If that sentence currently reads as the whole channel, it overclaims by exactly the 40 points the published physics retains.

### 3. Q1 ruled: the floor stands, what it killed was a metric mismatch, and the relative reading survives demoted

The regime is the key fact neither framing in your question states. At these cells the fix arm serves 0.020 to 0.050 per step against a capacity of 0.15: the console is running 13 to 33 percent utilization. It is not a broken console being nudged to a smaller failure; it is a slack console whose demand is being throttled upstream by the link, the patience, and the backoff economics. In that regime, served_per_step was never the jitter lever's claim surface. The lever's claim surface is outcomes, and the outcome data agree with the floor's verdict rather than fighting it: success gates at exactly the band span (n=5, both widths) and nowhere else, with signs flipping ungated at n=6. The service increments are real, unambiguous, and sub-material; the missions they buy are concentrated where the fold band lives. So the honest replacement sentence you drafted is endorsed as written: about three points of success at one span, and not measurable on what the console delivers.

On the sponsor's free 14 percent: the deployment recommendation survives on cost grounds, not on throughput grounds. One random draw, no console change, no gated negative anywhere on any metric: deploy because it is free and it closes the band, decisive at the band span, hygiene elsewhere. That is a different and honest sales pitch, and it is the one the evidence signs.

Over-correction check, ruled as asked: adopting a floor and losing a headline to it within the week is the floor doing work. Over-correction would look like inventing a second floor after the fact to kill the relative reading too, and I decline to do that. The relative reading survives, demoted: gates live on absolute numbers only; a relative figure may appear in prose only with its absolute and its base printed beside it, and never standalone in the abstract or discussion. Reporting it that way does not re-admit what the floor excluded, because what the floor excludes is gate status, not description. Add one column to the served tables: utilization of the reference arm, so every reader sees which regime a verdict lives in. And keep exactly one floor: capacity. A per-vehicle floor is capacity rescaled by a constant, and an offered-load floor was rejected for cause in Round 18.

### 4. Q2 argued: the rule is right with one amendment, and it can be enforced by construction

The genus, named precisely: a null that is a function, treated as a constant. Four instances, four missed arguments: the goodput null is a function of the denominator the treatment moves; the Fano null is a function of the window; the excess null is a function of dwell and rate; the tempo budget's null is a function of the hold fraction it was built to predict. Per-case benches caught all four, but always after the fact and always on demand, because the null's arguments were discovered lazily.

Your proposed rule, a level may never be gated, over-forbids by one category, and the category matters. The paper contains level claims of the good kind: the delivery governor pinned at 0.750 against a measured 0.761, and the half-goodput contour drawn from closed forms against the measured crossover. Both are levels gated (or correlated) against COMPUTED nulls, functions evaluated at the deployed configuration with every argument known. Forbidding those would discard the paper's closed-form spine, which is its distinction. The rule you want is one notch more precise:

A level may be gated only against a computed null, and a computed null is admissible only if every argument of the null function is logged in the same run that produced the level. Otherwise ship a difference of arms sharing every nuisance (with the mismatch bounded per the Round 18 equivalence rule, since sharing must be demonstrated, not assumed), or ship description without gate typography.

The admissibility clause is the enforcement mechanism, and it is mechanizable the way the denominator rule was: every metric in metrics.py declares its null signature at creation, difference-only or null(args), and ar_gate refuses gate marks on any level whose declared arguments are missing from the run's logged set. Under that check, F3's failure is impossible by construction: the sweep could not have been scored because arrival_rate was not in the log. The registry's first four entries are the four instances above, and the audit of current text costs an afternoon because the last three weeks already forced the paper into compliance case by case: the contour is a correlation with a computed null, the governor logs its arguments, the staffing brackets are cross-span differences, the abstract's levels are description. Nothing shipped violates the rule today; the rule exists so that nothing future can.

The umbrella sentence, if the methods subsection wants one line: no number in this paper is evidence except against a reference that is either cancelled by pairing or computed from logged arguments.

### 5. Scoreboard and the queue

Mine: the 1.009 amendment is superseded and its numerical nearness to the structural prediction is luck, not foresight; owned above with the pun flagged. P4 was my signature and its growth limb died of a null I should have demanded benched one round earlier than I did; the obligation I did impose is what caught it, which is the difference between a wound and a loss.

Yours, endorsed: the transfer-matrix bench, built better than asked; the withdrawn-not-refuted status and the honest replacement paragraph; CR-43's death executed exactly as registered, corpse read correctly; the two-physics design, which is the strongest sponsor-facing result since the staffing curve.

Yours, caught: the bare-null supersession (0.957 as the limit) would contradict your own Round 17 memoryless residuals; the two-hour premature commit, for which the text-queue rule above; and the L=7 numerical pun, flagged before it bites.

Queue: absrate, goodredo, cohsplit, dwellow, staffeq, noretry; the resubmitted dwellow supersedes F3 and is scored against P4' as registered here; the null registry and the utilization column are desk work. Nothing jumps the queue.

## Round 20 (2026-08-22, the coordinator's round 20)

Verification performed: recomputed the same-vehicle re-ask turnaround per policy from model constants (the table below); checked the jit-noretry sign pattern across all ten cells; re-derived what survives of the Round 19 additive structure against the P6 table.

### 1. P6: the control beats the residual, and I pay first

The table is decisive and I state my losses before interpreting it. Round 19's structure was raw = null(L, rate) + residual(n, rho), with the residual attributed to console-retry coupling. The decomposition survives; the attribution is dead. jit18 minus noretry gates nowhere on either channel, so the retry term under a randomized hold is zero, and the 0.041 I spent two rounds explaining is the open-loop fleet's own arrival structure, present with the reliance loop removed. Eighth owned item, and it has a process half that is worse than the arithmetic half: I prescribed exactly this control in Round 16 (simulate the null, the model owns it), and when it sat queued I did not wait for it; I spent Rounds 17 through 19 doing closed-form floor arithmetic on a level the registered control was about to delete. That is the reviewer-side twin of the premature manuscript commit: answering a question that a pending instrument was already assigned. The rule I proposed for your text queue applies to my analysis queue: no level gets explained while a control against it stands registered and unrun.

What the table establishes, cleanly: the fixed backoff is the cohort (fix18 minus noretry, 5 of 5 gated, rising to +155.8 percent), and the randomized hold does not reduce the retry cohort but removes it, to within a coin flip, at every span on both channels. Two scope notes before that sentence ships in the abstract. First, removal is demonstrated at backoff 18; CR-37 showed the jit-fix contrast is rho-dependent, so read jit4 minus noretry from the same battery family before the abstract sentence goes out unscoped, or scope it to the measured backoff. Second, the noretry baseline's own structure (1.006 to 1.021 memoryless, 1.049 to 1.146 bursty, rising with span) now sits in exactly the chair the 0.041 sat in. It is not to be explained by anyone, me included, until it is floored with logged rates through the NULL_ARGS machinery. The service-pacing candidate from Round 18's tree is the natural registrant if a floored level survives; register nothing before the subtraction. We have one demonstration already of what explaining an unfloored level costs.

One ungated observation, one clause only: jit sits below noretry in all five memoryless cells, 5 of 5 same sign with every cell a coin flip individually. If real, jittered retries act as decorrelated fill-in that dilutes the fleet's own structure toward Poisson. dwellow may firm or erase it; it is not registered and should not be.

P4' is amended to P4'' for dwellow's scoring, and the amendment is the round's lesson applied: the null for the jit arm is the in-battery noretry arm at matched dwell and rate, with the transfer matrix as cross-check only. Predictions: jit minus noretry flat at zero across the full dwell range; fix minus noretry rising with dwell; the noretry arm's own transfer-matrix-floored level reported as data, unexplained.

### 2. CR-39: the cohort is cross-vehicle, as the mechanism sentence needs

fix minus jit on distinct senders per window, gated at 32 of 32 with t up to 42: the lockstep is multiple vehicles landing together, not one vehicle hammering. The noun in "vehicles desynchronizing from each other" is now instrumented. Endorsed; the D1 tail read waits for a battery that carries the ge2/ge3/ge4 counters, next round.

### 3. The ruling you asked for: the decline is endorsed, your derivation is not, and the difference is the obligation it creates

First the verdict, then the corrections, because the corrections are what make the verdict safe to give.

The decline stands. The registered falsifier was built to detect an instrument that does not measure repeats; what the battery produced is machine-precision agreement between two counters that must diverge on any true repeat, sixteen cells of exact zero, and an arithmetic reason the configuration cannot produce a repeat. Firing P2's consequence would void P1 for a failure the evidence positively rules out. But the reasoning you gave has an error that changes what you owe next.

Your turnaround inserted service into the refusal path. The model's discovery paths, from its own constants: under refund and blind the requester is never told, so the earliest same-vehicle re-ask is patience plus backoff, at least 21 steps, unreachable inside a 7-step window at any latency and any backoff. Under admit the refusal notification is one round trip with NO service in it, 2 lat + rho: 12 steps at your latency 4, still unreachable, but 6 steps at lat 1 with rho 4, and 4 steps at lat 1 with rho 2. So the quantity P2 named is not unreachable in the model; it is unreachable in this battery's policy and latency cell. Your zero is structural for the right conclusion and the wrong formula, and the distinction matters because the formula is what the VOID declaration cites.

Question (a), answered: the physics derivation is necessary and not sufficient. Sufficient is three legs. The corrected derivation, from constants, naming the battery's policy and latency. The instrument-coherence evidence you have: the identity proves no repeats occurred, but it cannot prove the repeat-detection path would fire if one did, because that code path has never seen a repeat. And therefore the positive control: one cell where the fast path dips under the window, admit at lat 0 or 1 with backoff at most 4, predicted to move arrival_repeat_frac off zero. If no legal configuration reaches it, then the metric is a model invariant, and the honest handling is to reclassify it as an assertion (nonzero equals bug), because an invariant wearing a metric's name will eventually be read as a measurement again. The turnaround table says the cell exists, so run it.

Question (b), answered: yes, the category should exist, named VOID-UNREACHABLE, and it is kept from becoming an escape hatch by making the declaration itself a registered claim. Four mandatory fields. One: the unreachability computation from model constants, policy-specific, not a narrative. Two: independent instrument-coherence evidence. Three: the positive-control obligation, run or scheduled, or the invariant reclassification when provably unreachable everywhere. Four: infection scope: everything that cited the voided prediction as support is re-scored without it. And the conversion clause that gives the category teeth: if the positive control later shows the antecedent was reachable in the original battery after all, the VOID converts to FIRED retroactively and the decline is scored as an error by name. Declaring void must stake new falsifiable content, not retire old content quietly. P2 becomes the first instance, and its row should carry your corrected turnaround table, not the served-path formula, as field one.

Flagging the decline and asking for the ruling instead of burying it is the protocol working; endorsed as conduct regardless of the derivation error.

### 4. Implementation notes, one catch

NULL_ARGS for arrival_excess lists ge_burst_len and arrival_rate. The null is also a function of the stationary drop rate and of the window itself: the transfer matrix moved with rate at fixed geometry, and it will move with duty at fixed dwell (your own bench showed 46 percent at duty 0.5 against 5 at 0.8), and a future change to mult_window silently invalidates every stored floor. Today those are shared constants across batteries; the genus we are burying is precisely constants that are secretly arguments. Add both to the declaration now, while it costs one line. operator_goodput registered as no-admissible-level is exactly right, and the check_level construction (F3's failure now raises) closes the loop the way Round 19 asked.

### 5. Scoreboard and the queue

Mine: the Round 19 residual attribution, dead by control; the process error underneath it, arguing floors while the prescribed control was queued, which is the item I will be repeating to myself; P4' superseded by P4'' above.

Yours, endorsed: running the omitted control and letting it delete two rounds of both our arithmetic without flinching; the manuscript and ledger updates landing with it; CR-39's instrumented confirmation; flagging the declined inference for external ruling.

Yours, caught: the turnaround derivation prices the served path and calls it the refusal path, which mislocates WHERE repeats are unreachable (this battery, not this model); the removal claim needs its backoff scope or the rho=4 read; NULL_ARGS is two arguments short.

Queue: absrate, goodredo, staffeq, dwellow running, dwellow scored against P4'' as amended above. New obligations, all cheap: the positive-control cell (admit, low latency, small backoff), the jit4-noretry read before the abstract sentence unscopes, the noretry baseline floored before anyone explains it. Nothing jumps the queue.

## Round 21 (2026-08-22, the coordinator's round 21)

Verification performed: read the booking block at c2.py lines 623 to 630 and confirmed the forecast is computed before the policy branch; searched c2.py for any cancellation or reclaim of a booked slot and found none; confirmed queue_discipline and service_order exist with no pending buffer behind them; re-read the manuscript triage sentence at line 635; checked the anti-FIFO stranding argument for homogeneous patience by construction.

### 1. Q1, taken as hard as you asked: the headline is safe, and the proof is structural rather than reassuring

Two independent arguments, either sufficient alone.

The differencing argument. The booking block computes start, done, and reply BEFORE the policy branch: blind and refund hold the identical forecast and differ only in the action taken on it. An information rent requires an information DIFFERENCE between the arms being contrasted, and there is none; the +578 percent is a pure action contrast on a shared information set. Whatever one thinks of the oracle, both arms own it, so it differences out of every refund-minus-blind number in the paper. Clairvoyance cannot be a confound of a contrast between two clairvoyants.

The vacuity theorem. In this model, admit-at-arrival and admit-at-head are the same test. Service is deterministic (done = start + 1/mu exactly), the ledger is append-only FIFO, and nothing cancels a booked slot (verified: neither death nor abandonment reclaims one). So a job's completion time is fixed at booking and can neither improve nor degrade afterward: feasibility evaluated at arrival and feasibility evaluated when the server frees are the same inequality applied to the same deterministic quantities at different clock times. Your proposed head-of-line control would return zero BY THEOREM, and that vacuity is the proof of innocence you were reaching for: the rent you fear is a forecast-error rent, and this model has no forecast error to collect. So the control is not wrong, it is one model early; register it where it can fail, which is the buffer model with service-time variance, with the pre-registered zero point at spread 0 supplied by this theorem.

What the headline DOES owe is an external-validity sentence, and this is the real finding of your question. The refusal test is exact because service is deterministic: the D in M/D/1 is doing load-bearing work in the +578 percent. A real console's same rule pays a forecast-error tax in both directions, refusing work that would have made it and admitting work that will not, so the published gain is the exact-forecast ceiling of the discard lever. That sentence belongs in the parameters-are-set-not-measured paragraph. And the one component that genuinely can collect an early-decision rent, the notification returning the requester in one round trip instead of at the head, is already measured separately and is the small half of the decomposition, so the rent is bounded by a number the paper already prints.

### 2. Q2: build it, and here is the shape with the equivalence proved rather than trusted

Yes to the buffer, with your sketch amended in one place. Add admission_point: "arrival" | "head" under buffer, rather than making head-drop implicit. With admission_point=arrival, fcfs, and deterministic service, all three policies under buffer must reproduce reserve exactly on served_per_step and success, zero tolerance, and that is the build's acceptance gate: by the theorem above a mismatch is a bug by definition. Without the flag you cannot run that gate for admit, because your sketch's head-drop notifies later than reserve's arrival refusal, and the acceptance test would fail for a physics reason rather than a bug. The flag also makes the arrival-versus-head contrast a measured experiment instead of an unexamined choice, which is exactly what you asked the buffer to buy.

Your patience worry, answered with the proof this time. Reserve prices the reply deadline: reply minus k against P. Your head-drop test prices t + 1/mu + lat against arrival + patience, which is the same inequality evaluated later with the same deterministic values, so the semantics are identical PROVIDED two things your sketch already half-contains: the drop test keeps the reply deadline form (it does; do not let it degrade to a service-start deadline), and late replies to requesters who left at k + P stay wasted through the existing keep/waste logic, unchanged. The requester's own clock never moves. The two formulations diverge exactly when service_spread > 0, and that divergence is not a semantics bug, it is the clairvoyance experiment.

Design notes, then the slate. No RNG in pending-list operations: deterministic sort keys, ties broken by arrival then id, so arms stay seed-comparable. Disciplines fcfs, edf, patient_first, plus random, kept for continuity with the triage study's randomized-order control. The patience_spread construction is endorsed as designed: the balanced multiset with the exact mean in every replication is the Round 9 mean-pinning lesson institutionalized at design time, and the rng.spawn isolation is house-rule correct. Nothing else in v1: no preemption, no priority classes. The registration slate that justifies the build: (A) the equivalence gate; (B) CR-46 v2 as framed, the cmu-theta and EDF literatures against each other is a good registration and survives the move; (C) the rent curve, admit-at-arrival minus admit-at-head over a service_spread sweep, zero registered at spread 0; (D) the triage re-run, because a manuscript sentence hangs on it. A blocks the rest.

Why the buffer changes the answer, in one sentence for the ledger: in reserve, ordering value needs same-tick coincidence AND slack, and load manufactures the first only by destroying the second, so the window is closed by construction; a pending list turns contention from a same-tick coincidence into a stock accumulated over residence time, and the window opens.

### 3. Q3: option (b), executed through the category Round 20 built

CR-46 v1 is the second instance of VOID-UNREACHABLE, and the machinery fits without stretching. Field one, the unreachability computation: your contention table plus the c2.step reading, which together show the antecedent (the server has choices) is reachable only as same-tick coincidence, and the slack and contention regimes do not overlap. Field two, instrument coherence: the smoke test's under-floor unstable signs are exactly what the theorem predicts. Field three, the positive control: the buffer build itself, scheduled. Field four, infection: the triage-null claim, handled below. Do not run reserve at tier standalone; option (a) buys a number we already know and cannot interpret, and your contention measurement is sufficient to justify skipping it NOW. But the negative control still runs LATER, inside the buffer battery, same blocks, same seeds, at the battery's own tier, because a negative control's job is to anchor the difference against the treatment arms it travels with, not to exist in isolation. So: the measurement suffices to skip the standalone run; it does not discharge the in-battery control.

### 4. The triage sentence migrates, and you were right to ask rather than talk yourself into it

Ruling: move it. The manuscript sentence, "reordering a queue whose clients all carry the same patience changes which vehicle is helped, never how many are," is true in this model for a structural reason (there is no queue to reorder; completion times are fixed at booking) and FALSE as a general statement about queues, including homogeneous ones. With identical relative patience, deadlines are ordered by arrival, so FIFO coincides with EDF and maximizes the feasible served set, and a bad order can serve a late arrival first and strand an earlier request past its deadline: ordering changes HOW MANY, downward, whenever the discipline is bad enough. The cmu-theta and deadline-scheduling literatures your registration cites exist precisely because order changes counts. A queueing-literate referee kills the current sentence on sight.

So: the docstring states a model property as a queueing theorem, the manuscript inherited it, and the claim moves from the claims block to the instruments block with status supported-by-artifact, pending the buffer re-run. What survives in the Discussion is real and worth keeping: the dispersion argument (a single formation presents almost no priority signal to exploit) is a scenario fact independent of the queue model, and the honest form of the conclusion is "refusal is the lever; ordering was not testable at this fidelity," not "ordering is not." Fix the docstring at the source in the same pass, since the manuscript repeated it once already and will again.

My share: I read that paragraph in at least three rounds, audited its prose, endorsed its placement, and never once asked whether the model could reorder anything. The sentence sat on top of a booking block I had read line by line for other reasons. Ninth owned item, shared: you wrote it, I passed it repeatedly, and the register caught it because you audited your own docstring as if it were a claim, which is the discipline working one level deeper than I was applying it.

### 5. The landed items, briefly

CR-40: the burst interaction surviving AND growing on the clean metric, with the contamination running against the claim this time, is the best possible outcome for that site. One wording catch in the amendment: "the bias is not signed" is true across pairs but loses the useful half. The sign varies by pair AND is computable per pair from which arm asks more; the manuscript should say "computable per contrast, constant in neither size nor sign," because the computability is what makes the rule a method rather than a warning. P3's levels-flip paragraph: endorsed, that is the band mechanism on clean metrics and it was the missing exhibit. CR-41's four-term decomposition: endorsed as the publishable form of three weeks of instrument work, and note with approval that the no-retry fleet term (+0.056, flat across a 240-fold dwell range) is REPORTED and not explained, which is exactly the Round 20 guard holding.

### 6. Scoreboard and the queue

Mine: the triage paragraph passed three times without the structural question, owned above. Nothing else new; the Q1 theorem is the round's work product.

Yours, endorsed: registering CR-46 off your own docstring, which is source-code-as-claims auditing and is the deepest the discipline has reached; the contention table, which is the right way to show an experiment is unrunnable rather than merely null; the patience_spread construction craft.

Yours, caught: the head-of-line control is vacuous in the current model and its vacuity is itself the exoneration, so aim it at the buffer with the registered zero; buffer-admit needs the admission_point flag or the acceptance gate cannot pass for a non-bug reason; the "not signed" amendment needs the computability clause restored.

Queue: staffeq, absrate, sobol, dwellnr running and untouched by any of this. The buffer is code-and-desk work that does not enter the battery queue until its acceptance gate passes. Available today: the triage sentence rewrite, the docstring fix, the computability clause, the limitations sentence on deterministic service. CR-46 v1 files as VOID-UNREACHABLE instance two. Nothing jumps the queue.

## Round 22 (2026-08-22, the coordinator's round 22, answered after the same-hour correction)

Verification performed before the correction arrived: confirmed service is deterministic at c2.py lines 565 and 819; derived the deterministic-residual admission rule independently and computed its full table against the registered sweep; computed the Poisson tails at the three registered discriminating cells; checked the buffer implementation (queue_model, queue_capacity, drop-oldest on overflow, pending list) in the shipped source. The correction and my check converged: the rule I derived, floor(lambda - 1/2), is identical to the corrected floor(lambda + 1/2) - 1. What follows answers the corrected question and is on the record before Hopper 9448688 or the queue-only model reads out.

### 1. One defect to fix before the derivation ships: the survival line is off by one

As displayed, Pr[useful at depth j] = clamp(lambda - j + 1, 0, 1) contradicts the k* beneath it. A request at position j (j = 1 next up) is answered at 2L + r + j/mu; useful iff r mu <= lambda - j; so Pr = clamp(lambda - j, 0, 1). Admitting while that is at least 1/2 gives j <= lambda - 1/2, k* = floor(lambda - 1/2) = floor(lambda + 1/2) - 1, which is the k* line as written. So the final rule is right and the displayed survival curve is one unit generous; with the displayed curve the same threshold would give floor(lambda + 1/2) and miss both measured points. Fix the line, keep the rule.

### 2. (a) The threshold: 1/2 is a bookkeeping coin, not an optimum, and here is the marginal condition

The admission decision at position j trades this request's success against the slot's opportunity cost. Admit iff

    q(j) >= pi * qbar_next

where q(j) = clamp(lambda - j, 0, 1), pi is the probability that the service slot this request will consume would otherwise have gone to a fresher arrival rather than to idleness, and qbar_next is that fresher arrival's own success probability. Two limits pin the range. Drought-dominated arrivals: pi -> 0, the alternative is an idle server worth zero, so admit anything with q > 0 and p* -> 0. Sustained overload: pi -> 1 and qbar_next -> 1, so p* -> 1 and the console should be maximally impatient. The threshold 1/2 is not the optimizer of anything; it is the break-even coin for the marginal occupant considered in isolation (more likely useful than wasted). It coincides with the throughput optimum only when pi qbar_next is approximately 1/2, that is, when the marginal slot's alternative use is itself a coin flip.

Why does a constant-1/2 rule nevertheless fit your ladder? Because your registered sweep varies P at FIXED fleet and cadence, so Lambda/mu, and with it pi and qbar_next, are approximately constant across all eight cells. Any constant-p rule with p in a broad band fits such a sweep; you are measuring the form, not the threshold. The paper-safe sentence: k* = floor(lambda - 1/2) is the largest buffer whose marginal slot is more often useful than wasted; it upper-bounds the throughput-optimal buffer under sustained overload and lower-bounds it under drought-dominated arrivals; at this fleet's operating load the three coincide to the integer.

The registered discriminator for the threshold, stated before anyone's data: sweep LOAD at fixed P. At P = 20 (lambda = 3.00), raise n from 8 toward 20. The constant-1/2 rule predicts the argmax stays 2 at every span. The marginal condition predicts it falls toward 1 as overload deepens, because pi rises. That is the experiment in which p* is identifiable; P = 45 is not, and within the current sweep no cell moves for p anywhere in roughly (0.35, 0.65) except P = 30, which is a tie by construction.

On the design gap you flagged: it is real and it is moot. The Erlang rule is not a live competitor awaiting data; it is refuted by the source code (deterministic service), and no battery should be asked to adjudicate between a wrong-physics formula and a right-physics one that happen to agree numerically. Score the sweep as det-versus-mean-fits only. And note something that died with the Erlang premise: under the Poisson-tail model your three discriminating cells sat on 0.516, 0.505, and 0.512 coins, and I had prepared the attack that your falsifier could fire on noise at flat-topped cells. Under the live deterministic model the same three cells have marginal-slot success 0.75, 0.70, and 0.75: fat margins, well-powered against mean-fits. The fragility was an artifact of the dead model; the design is better than you feared, with one exception: pre-commit P = 30 as scored inconclusive. At lambda = 4.50 the marginal position sits at exactly q = 1/2, the objective is flat between capacities 3 and 4, and neither rule may claim that cell whatever the argmax reads.

### 3. (b) Drop-oldest and LIFO: equivalent at the bottom, not at the top, and the measured curve already says so

Exact statement. At c = 1, drop-oldest FIFO IS serve-newest: the single slot always holds the freshest arrival. At small c under sustained overflow, the served request is the oldest SURVIVOR, whose age is the time to traverse c - 1 departures (services plus evictions, total rate Lambda) plus the race at the head: age approximately (c-1)/Lambda + O(1/(Lambda + mu)). So a two-deep drop-oldest FIFO is newest-first with an age offset of 1/Lambda, about half a service time at your loads, which is why CR-47 P7 found them indistinguishable: the merge is real, and the merged sentence is worth more than either finding, as you suspected: the bound is not a length policy, it is a FRESHNESS cap denominated in service times, and k* = floor(lambda - 1/2) is the patience's bandwidth-delay product. Serve-fresh has two implementations, a tiny drop-oldest buffer and newest-first service, and they are one mechanism.

But the equivalence FAILS at large c, and your own curve exhibits the failure: the served item's age grows linearly, (c-1)/Lambda, because FIFO still serves the oldest survivor even while eviction keeps the buffer's content fresh. At C3, n = 12, Lambda is roughly 0.33 per step, so c = 6 serves requests aged about 15 steps before the round trip, against a net deadline of 12: mostly useless, and measured c6 = 0.0136 against the c1 peak of 0.0840. So do not write "saturated drop-oldest equals LIFO" unqualified; write "equals LIFO at the small-c end, with the divergence growing as (c-1)/Lambda, which is why the bound must be small rather than merely finite." Your depth-j line is therefore half-real: under sustained overflow the marginal request never stands in it (eviction), but during drought-refill episodes eviction pauses and the line exists in full, and the mixed regime is where the fitted rule lives. Three one-column diagnostics settle the regime per rung: age-at-service distribution, eviction rate, idle fraction.

For the queue-only model, registered expectations, not to be adjusted: (i) on a fine lambda grid the measured argmax deviates from floor(lambda - 1/2) by at most one, with deviations toward SMALLER c where the overflow rate is high (the marginal condition's pi rising); (ii) the right-tail collapse above k* is arrival-law-robust (the traversal age mechanism needs only overflow, not burstiness), so Poisson arrivals will reproduce it qualitatively; (iii) what Poisson will understate is the left side and the peak: bursty, retry-cohort arrivals deepen the c0-to-c1 gain and sharpen the optimum, because the buffer's drought-insurance value is a burstiness phenomenon. If the queue-only model on Poisson arrivals fails to match SandTable's peak sharpness, that is the arrival law, not a bug, and I am saying so now so nobody opens a defect investigation later.

### 4. (c) The referee's bookshelf: every component has a name, the composition is yours

The neighborhood the paper must cite or a referee will cite it first. Naor 1969 for threshold admission to an observable queue (your rule is a deadline-utility Naor threshold, and Naor's individual-versus-social gap IS the 1/2-versus-p* gap of section 2: the coin rule is the individual criterion, the social optimum admits less under load). Appenzeller et al 2004 for buffer sizing as a bandwidth-delay product: k* is the BDP of the patience. Nichols and Jacobson's CoDel for bufferbloat: their insight is to target DELAY not LENGTH, and the referee-proof sentence is that at deterministic service the two coincide, so the length cap inherits the delay-target's virtue and admits a closed-form location. The age-of-information packet-management line, Kaul-Yates-Gruteser 2012 and Costa-Codreanu-Ephremides 2016 (the M/M/1/2* replace-oldest results, keep-a-tiny-buffer-and-discard-stale), plus LCFS-freshness results (Yates), for serve-fresh with small pushout buffers: this is the closest prior art to the drop-oldest half and the place a referee would look for "already solved." It is not solved there in your form: AoI optimizes average age, you optimize deadline hit-rate at deterministic service, and the closed-form argmax with in-sim confirmation is a legitimate composition. Barrer stays for deadline reneging; add a line for M/D/1 finite-buffer classical results (Crommelin transforms) so the queueing referee sees the family acknowledged. Framed as "the deadline analogue of buffer sizing, located exactly and confirmed at mission level," it is neither trivial nor re-derived badly; framed as new queueing theory it would be killed.

### 5. Q2: TOST, yes, and the margin is already chosen for you

Do the TOST, margin = the standing MPE, 0.009 served/step, alpha 0.05 (equivalently the 90 percent CI inside plus-minus 0.009). The margin is defensible precisely because it was NOT chosen for this test: it is the paper's pre-existing materiality floor, so there is no margin-shopping to accuse. The reason TOST beats "ran to margin X and could not separate," given that you control the sample size: failure-to-separate is a claim that WEAKENS as reps grow (any fixed nonzero difference eventually separates, so a null that survives your choice of n is only as strong as your restraint), while equivalence-within-margin STRENGTHENS with reps. Since the console-substitution claim is sponsor-facing (one bounded console buys the second console's throughput), it deserves the form that survives more data. Two riders: run the same TOST logic on wait_p95 before selling console parity, because two consoles can dominate tails at equal throughput and a staffing recommendation that ignores tails will be caught; and apply the same instrument to the other null-as-claim rows (the n = 4 costs-nothing cells), which are currently gate-nulls wearing claim clothing, the exact gap Round 18's equivalence-bound rule was built for.

### 6. Q3: the spine

The paper is about one discovery: supervisory span collapses by congestion, not attention; the collapse point is located by closed forms and moved by software. Keep: (A) the queue mechanism and its closed forms, the sufficiency result, the staffing curve, the latency-loss decoupling, and the identification shield (force-ratio DiD, arrived_frac mediation, console share); (B) the lever suite on clean metrics: discard-plus-bound as ONE lever family closing with k* = floor(lambda - 1/2) as its sizing corollary and the 0.0023-versus-0.150 collapse exhibit, the randomized hold as the free band-closer, the vehicle-side rate rule as asked-less-wins-more, with the two-lever stack on success and blue losses; (C) one tight methods subsection carrying the registration ledger, the denominator and null-registry doctrine, the CR-31 and CR-37 arcs, plus the external anchors (Lewis's interior optimum, MAGIC burstiness) and the limitations block. Cut to a second paper about Y = arrival-process microphysics and instrument validity in mission-level simulation: the entire cohort apparatus (CR-34, 37, 39, 41, the four-term decomposition, transfer-matrix nulls, dwell sweeps, the two-synchronizer analysis), the fold-band forensics beyond band-plus-floor-plus-doubling, P3's fine structure; droop compresses to its one-clause sensitivity sentence, triage to the instruments-block limitation pending the buffer, and the failed registrations stay in the main paper as one table because the ledger is load-bearing for credibility and costs a quarter page. That is twelve claims kept, the cohort family and fine structure out, which is your third.

### 7. Scoreboard and the queue

Yours, endorsed at full price: catching the exponential-service premise by reading your own source within the hour, recording it as genus instance five rather than patching silently, and rebuilding the mechanism on the model's actual physics. The corrected rule is the one I had derived in parallel before your message arrived; the convergence is on the record in the tool log, and the queue-only model completes the triangle: theory here, measurement there, compare.

Yours, caught this round: the survival line's off-by-one (the k* line is right and internally implies the fix); "saturated drop-oldest equals LIFO" needs its large-c qualifier or the c6 cell contradicts the paper's own sentence; and P = 30 must be pre-committed inconclusive before the battery reads.

Mine, recorded: the knife-edge attack I had built against the discriminating cells was correct against the Erlang model and died with it; it survives only as the P = 30 tie note. Filed as an attack that its target outran.

Queue: Hopper 9448688 reads against the corrected rule with P = 30 inconclusive by pre-commitment; the load sweep at fixed P = 20 is the registered threshold discriminator when a slot opens; the three regime diagnostics ride along free. Nothing jumps the queue.

## Round 23 (2026-08-23, the coordinator's round 23)

Verification performed: checked T = P - 1/mu - ell over the sweep (13.33 down to 7.33, worst case 7.33, matching the single good age cap of 7); derived the saturated served-age law for drop-oldest under Poisson arrivals and checked the two-mode reading against all twelve entries of the measured plateau table; confirmed the crossover arithmetic in the 201-point reversal.

### 1. My score first: the load sweep was my discriminator, and the constant rule won it

Round 22 registered my prediction: at fixed lambda, rising load pulls the argmax from 2 toward 1. Measured: 2 at every load from 0.70x to 7.44x, then a rounding tie on a flat ceiling. The constant-1/2 rule predicted no motion and was right; my p*-motion prediction is refuted in the only observable I attached it to. Owned, and the failure has a structure I should have derived in Round 22 rather than after: under drop-oldest at saturation, the queue holds the k most recent arrivals, so the served request is the k-th most recent, whose age under Poisson arrivals is exactly Erlang(k, Lambda) with mean k/Lambda. As Lambda grows, every bound serves fresh: the eviction discipline IMPLEMENTS maximal impatience at every k, the policy space collapses, and pi -> 1 arrives as objective-flatness rather than as argmax motion. The marginal condition was not wrong about the physics; it was wrong to expect the argmax to express it, because drop-oldest expresses it first.

### 2. (a) ruled: a legitimate property claim, under three conditions, and the observable that would break the coincidence exists

Claiming "unfalsifiable here as a property of the system" is legitimate and correct, not an excuse, provided it ships in this form. First, state the mechanism, not the failure: the threshold becomes unidentifiable because eviction self-freshening equalizes all bounds exactly where the threshold would move; that is a derivation, not a shrug. Second, scope it: the property holds for console-side metrics under SILENT eviction. There is a system observable for which pi -> 1 does not coincide with flatness: notified eviction. The age at which a bounced requester learns its fate rises with k (a k=1 console bounces you young, a k=6 console strings you along), so with an evict-notification the bound prices requester tempo, and at high load mission success would separate bounds that served_per_step cannot. That is one optional knob if anyone ever needs p* testable; this paper does not. Third, reframe the whole thing as what it actually is: a robustness result. Mis-sizing is dangerous only in the one-to-four-times-capacity window; outside it any bound works. The plateau table is a mis-sizing risk map, and that is a sponsor-legible sentence, not a confession.

### 3. (b) attacked and then completed: the sentence is right about one mode, and the reversal needs two

Your mechanism sentence is true of the overflow mode and does not explain the reversal by itself, because the overflow mode is precisely the one in which the deadline never binds. The full structure is two modes. Drain mode: the buffer fills in a burst and drains without eviction; the bound-j occupant waits j services; age approximately j/mu, LOAD-FREE. This mode prices the right edge, which is why k* = floor(lambda - 1/2) never moved across a twenty-fold load range and why the constant rule won my discriminator: the binding arithmetic was load-free all along. Overflow mode: sustained eviction; the served request is the k-th most recent arrival; age Erlang(k, Lambda), mean k/Lambda; always fresh at high load, so this mode prices nothing. The load reversal of over-versus-under-sizing is the shifting MIXTURE WEIGHT between modes, not a shifting meaning of k inside the binding mode: under-size cost is drought idleness, proportional to the probability the queue empties; over-size cost is stale drain-mode services, proportional to drain frequency; both fall with load at different rates, crossing near your measured 2.8x.

The formula you asked for: age of the served request at bound k is the mixture A = Erlang(k, Lambda) with weight w(k, Lambda) (residence spent under sustained overflow) and A approximately j/mu + residual with weight 1 - w (drain passes), j the admission position. Everything in your paragraph follows: the two-mode reading reproduces your entire plateau sequence including the left-edge non-monotonicity ([1-6] to [2-6] to [2-2] to [1-2] to [1-3] to [1-6]) that the one-sentence version cannot: the left edge binds only while droughts matter (load below roughly 2.2x), the right edge sits at floor(lambda - 1/2) while drains still occur (below roughly 4x), and both edges release at the ends. The window's width is derivable in form: left edge from P(empty) in M/D/1/k, right edge from the drain weight; exact constants via the classical finite-buffer occupancy transforms (Crommelin) or your queue model on a grid, and numerical constants are acceptable there because the EDGES' formulas, not their third decimals, are the claim.

### 4. CR-50: the retraction is exemplary, and one survivor sentence is owed to the companion

Declining to extend the switch envelope to ell=6 to rescue a 71 percent advantage is the anti-salvage rule executed in the tempting direction, and the record should say so plainly. The corrected mechanism is right and better than the registered one: an age cap reads the half of the round trip that has already happened from the timestamp and must still FORECAST the return leg, so its correct setting is P - 1/mu - ell and your single good value 7 is that expression's worst case over the sweep (13.33 down to 7.33). Two notes. The scoped survivor sentence belongs in the companion, not the main paper: inside the modelled envelope the two mechanisms coincide (your moving-link null at |t| = 45 below the material floor is another statistically-resolved-materially-null exhibit for the MPE doctrine); beyond it, a worst-case-tuned age cap extends coverage at the price of one worst-case assumption about the return leg. And the off-by-one being fixed at source with the error on the record closes that item.

### 5. (c) decided, as asked, both decisions final

One: the cut material goes to a SEPARATE FILE marked as the second paper. Not an appendix: an appendix invites this submission's referees to re-litigate the entire instrument war, which is the one fight the spine does not need. Not git-history-only: the companion is real work with a real audience (the four-term decomposition, the transfer-matrix nulls, the window doctrine are publishable methods material). Move the cut LaTeX into a companion skeleton with the ledger rows it carries, and leave the main text one non-promissory line that the arrival-process instrumentation is developed separately.

Two: the instrument-defect list STAYS, merged with the failed-claims table as one table with a type column (claim failed, instrument defect, convention carried past its case), under one criterion that is the entire difference between honest and self-indulgent: every defect row ships with the mechanized guard that now makes its recurrence impossible (the ar_gate fixture, NULL_ARGS, check_level, the TOST margin, the gate-eligibility rule). A defect list with guards is an engineering credibility exhibit: the reader trusts the numbers BECAUSE the failure modes are enumerated and closed by construction. A defect list without guards is confession as decoration. Any row that cannot name its guard gets cut, and the who-erred attribution stays in this ledger file and out of the paper: the paper documents the system, not the theater.

### 6. (d) the free swing: your operator is a human modeled with zero service-time variance

The strongest remaining weakness you have not asked about: every closed form in the paper (n*, the backoff floor, and now k*) and both headline levers were derived and confirmed at service CV = 0. The feasibility test that IS admission control compares against an exact 1/mu; a real operator's decision times have CV near 1, and under service variance the refusal rule acquires a forecast-error channel in both directions, admitting work that overruns and refusing work that would have made it. Round 21 flagged this as a limitations sentence; k* becoming a headline design rule upgrades it to a robustness obligation, because the referee sentence writes itself: "a buffer-sizing rule for human operators, derived and tested only at deterministic service."

Actionable tonight, in the queue-only model, no cluster slot needed: sweep service CV over {0, 0.25, 0.5, 1.0} across the lambda ladder, registered before reading: variance eats deadline slack, so the argmax shifts DOWN, by at most one slot at CV = 1 if the rule is robust; and the admission lever's gain over blind degrades toward blind as CV grows, without changing sign. If k* moves by at most one across the CV row, the rule ships with that row as its robustness evidence; if it moves more, the paper needs the CV-corrected rule (median-type reasoning returns, this time with the right premise, since service variance is what Erlang tails are FOR). Second swing if a battery slot opens: replicate the two headline levers once on the UC3 route geometry, because every lever magnitude currently lives on one map.

### 7. Scoreboard and the queue

Mine: the p*-motion prediction, refuted by the discriminator I designed; the Erlang(k, Lambda) age law I should have produced in Round 22 arrived one round late. Both owned above.

Yours, endorsed: the CR-50 retraction with the rescue declined; catching your own two claims within three hours (the 201-grid reversal, the FULL_MPE-as-absolute instance) and filing them in the genus rather than patching quietly; the TOST implementation with the margin fixed before the contrasts ran, which is exactly why it is defensible.

One rider repeated once, because the sentence is about to ship: before "one console equals two" goes to the sponsor, run the same TOST on wait_p95. Two consoles can dominate tails at equal throughput, and a staffing substitution claim that ignored tails would be the one line in this paper a practitioner catches. Note also that at n=16 the claim is not equivalence but weak dominance (single console ahead by 4.0), which is stronger and should be stated as what it is.

Queue: the CV sweep is queue-only work and can run tonight; the companion split and the merged table are desk work; Hopper 9448688 and the standing batteries read as registered. Nothing jumps the queue.

## Round 24 (2026-08-23, the coordinator's round 24)

Verdicts first. Q1: the identity as registered is neither tautology nor finding, it is an incomplete partition, two consuming bins short, and its own falsifier will likely fire for an instrument reason rather than a physics one; the retry defense of non-tautology is algebraically empty. Q2: drop the word "dominates" entirely: at n=16 the top three arms sit within one MPE of each other, so the ladder is a price ladder among throughput-equivalents, and the pricing inverts on variable links by his own CR-50 table; P3 and k* are separable formulas and P3's miss is the paper's documented one-span-optimistic bias recurring. Q3: the one experiment is the first cross-tier confirmation of the discard rule in ProjectGL, one operating point, five to ten missions per arm, and effect size is why it is the only experiment that CAN be run at tier 2.

### 1. Q1(a): the tautology ruling, and where his defense fails

The retry defense fails by cancellation. stale_frac * requests_per_step = (n_stale/n_request) * (n_request/total_steps) = n_stale/total_steps. n_request cancels exactly, retries and all. Whatever inflates the denominator inflates the numerator's normalizer identically; the product never sees a retry. So the registered identity is, in counters:

  n_serviced/steps + n_stale/steps = mu * busy_steps/steps

which asks: do useful completions and stale completions exhaust busy time? In this codebase the answer is NO, and I can point at the lines. The buffer service path (c2.py 643-668) claims the slot at line 643 ("the slot is spent from here on, always") and then exits through FOUR bins, not two:

  bin 1  n_serviced (line 663): worked, delivered, in time.
  bin 2  n_stale (645): worked, requester already re-asked (seq bumped).
  bin 3  n_abandon_link (648): worked, reply died on the down-link.
  bin 4  n_abandon_queue (653): worked, delivered, too late; the requester gave up but has not yet re-asked, so the seq test at 642 does not catch it. "blind always; an admitting console only when it admitted on the mean and the draw overran" per the comment at 651.

Bins 3 and 4 consume a full service each and appear in NEITHER term of the registered identity. So:

- For admit on a clear link at cv=0, bins 3 and 4 are empty by construction (feasibility test at 631, deterministic service, reply_survives ~ 1), and the identity IS a tautology there, modulo the end effect: at most one in-progress service per mission end, (1/mu)/1800 = 0.37 percent of busy time, at most 0.00056 served/step, sixteen times under the 0.009 MPE.
- For blind arms it is a falsifiable claim and probably FALSE at mid spans. Registered prediction, before 9448883 reads: the two-bin residual equals bin 4 (bin 3 is ~0 on the clear rung), it is rank-ordered fifo ~ rand > lifo > admit ~ 0, and it PEAKS at n = 6-10, where drain-mode delays are comparable to P plus the re-ask lag, then shrinks toward n=16, where the 880-step waits (backlog 132 times 6.67) mean the requester re-asked long before service and nearly all dead work converts to bin 2. The fifo row at n=16 already nearly closes for exactly this reason: 0.0023 + 0.4380 * requests_per_step = 0.15 at requests_per_step = 0.337, which is about right for 16 vehicles with retries. lifo at n=16 leaves ~0.0036 unexplained if util = 1 (served 0.1464, stale ~ 0), which is bin 4: newest-first serves near-boundary requests. Under one MPE, so the falsifier may squeak through at n=16 and fire at n=8.

His falsifier says "residuals not rank-ordered by arm". If my prediction is right, the falsifier FIRES, and the correct response is not to junk the accounting but to log that the identity was registered two bins short. That is the convention-drift genus again, seventh instance: "completions = useful + stale" is a constant-shaped sentence that is secretly a function of the arm, because two of the four exit bins were folded into counters that also increment on non-consuming paths.

Which is the instrumentation defect to fix now, cheaply, before CR-54 reads: n_abandon_queue increments on THREE paths (drop-oldest at 554-555, head refusal at 634, post-claim late reply at 653) of which only the third consumes service; n_abandon_link increments on the up-link path (847, 933) and the post-work down-link path (648), of which only the second consumes service. As logged, the four-bin identity CANNOT be audited from the counters. Split them: n_abandon_queue_worked and n_abandon_link_down, two ints, no behavior change. Then the four-bin identity closes by construction, and its closure is an invariant audit in the Round 20 sense, with the rank-order clause as the audit's teeth.

Corpse sub-bin, for completeness: req_seq bumps only at request generation (840), and requests are generated only by live vehicles (726), so a requester that dies mid-wait can never render its request stale. Worked late, it lands in bin 4; worked in time, it lands in n_serviced, a reply delivered to a corpse counted as useful. Bound: blue deaths times (svc + lat)/mission window each, well under MPE everywhere we run. One scope sentence, no counter.

### 2. Q1(b): his three candidate leaks are one right, two category errors

In-progress at mission end: real, bounded above at 0.00056 served/step, ignorable. n_dropped: consumes ZERO service; the drop path (553-555) pops the pending entry without _claim. Head-refusal n_abandon_queue: zero service, "no service time is claimed, so the next request is considered on the same step" (635). Those two are bins of the REQUEST-FATE ledger, not the console-time ledger, and the identity is a time ledger. Keeping the two ledgers distinct is the actual content here:

- Console-time ledger (busy steps): served + stale + late + lost-reply + end effect. Policy owns stale and late (they are what discipline and admission move), the radio owns lost-reply, physics owns the end effect, capacity owns the total.
- Request-fate ledger (n_request): served, stale, late, dropped, refused, up-link lost, down-link lost, pending at end. Sums to n_request by construction; useful as an audit, not as an objective.

The program-office sentence falls out of the ownership column, and it is better than the one-degree-of-freedom version because it names whose lever each bin is: on a clear link the console's dead work is entirely the software's to remove; on a jammed link a second bin opens that no console policy can touch.

### 3. Q1(c): the strongest honest statement

His draft ("every policy question about this console reduces to minimising dead work") overclaims on three fronts, each with an in-repo counterexample:

1. Distribution. The identity is blind to WHO gets served. lifo and the bound both sit at stale ~ 0 (0.0002 and ~0), and they differ enormously in tail behavior. Two policies with equal dead work are identical to the identity and need not be identical to the mission.
2. Requester side. The ledger counts console time only. Waiting vehicles are exposed (the Round 17 attrition channel), rate rules change the asking, and the codebase's own comment at 183-184 notes that a costly mission relieves the console by destroying its own demand. None of that is in the identity.
3. Value composition. q_droop (157) and admit_foresight already price decisions unequally; the identity counts a service as a service.

The defensible statement, envelope attached: "For a single console at saturation, homogeneous request value, clear link: useful throughput equals mu minus the dead-work rate, so every THROUGHPUT question about discipline and admission reduces to minimizing the console's dead work; the four CR-47 arms are one lever because each is a dead-work rate and nothing else." Below saturation the theorem degenerates and the arms tie, which his own n=4-5 columns show (spread 0.088-0.105, about 1.5 MPE): the left edge of the table is the degenerate case, worth one sentence. And report operator_utilization per arm (it is already logged, metrics.py 150): if all four arms sit at util ~ 1 for n >= 8, the paper buys the sentence "policies do not change how much the console works, only what it works on; the 65-fold served spread at n=16 is composition, not effort" for free, and THAT, not the identity's closure, is the finding.

The rand arm deserves its sentence sharpened, because it is the round's best construction: random order recovers 5.2 percent of what admission recovers ((0.0100-0.0023)/(0.1490-0.0023)). Random sampling of a 130-deep backlog samples the backlog's age distribution; newest-first takes its youngest order statistic. At that depth the age distribution IS the problem, so "breaking rigid order" was never the mechanism, age selection was. One arm, one dead hypothesis, cheap.

### 4. Q2: the recommendation, pressed

First the verb. At n=16: admit 0.1490, bound 0.1476, lifo 0.1464, MPE 0.009. Admit minus bound is 0.0014, bound minus lifo 0.0012, admit minus lifo 0.0026: ALL THREE gaps are under one MPE. Nothing at the top of that table dominates anything else on throughput, and the bound's 0.1476 is from a separate battery besides (different seeds; a same-battery TOST is owed before any equivalence sentence ships). The honest structure is: three throughput-EQUIVALENT policies, one price ladder. Recommend the bound as the cheapest of the equivalents, not as the winner. The word "dominates" hands a reviewer the MPE table.

(i) P3 versus k*. Separable, and the separation is in the formulas: n* = c mu (P + tau + 1)/d is cycle arithmetic, it needs the decision interval and the delivery rate; k* = floor(lambda + 1/2) - 1 with lambda = (P - 2 ell) mu is deadline arithmetic, no tau, no d. They share only the measured constants P and mu. P3's miss is an overprediction (crossing bracketed 5-6, predicted 6.45, 0.5-1.5 spans optimistic), which is the SAME direction and SAME size as the bias the paper already documents for n* in the phase-contour section ("keeps direct control viable about one span higher than the measurement"). Score P3 failed on its letter, the registered number was the number, but write the ledger row as known-bias recurrence, and have the paper cite its own phase section rather than minting a new explanation. k* showed no analogous bias where it was exposed, which brings us to:

(ii) "10 of 10 argmaxes" is inflated, and the deflator is computable. A hit on a width-6 plateau is not a test: the argmax inside a flat plateau is noise-chosen, so hitting it is luck. Correct scoring: per cell, report plateau width w; cells with w <= 2 are sharp tests (the rule must hit), cells with w > 2 test only membership. From the Round 23 plateau table the sharp cells are the 1.16-1.86x loads and the band edges. Demand the count m of sharp cells in the qcap read-out and report "m of m sharp hits plus 10 of 10 membership". If m < 3 the k* sentence in the paper weakens to "consistent with" and the sizing corollary loses its exclamation point. This costs one column in a table he already has.

(iii) Starvation units. Mean backlog is the wrong unit twice over. lifo's 146 entries are mostly zombies (requesters that re-asked or moved on; the seq test guarantees they will be counted stale IF worked, but under lifo they are simply never worked), so backlog length measures memory consumption, not harm. And the harm that exists is requester-visible TIME, but note the twist: lifo starves REQUESTS, not vehicles, because every re-ask lands on top of the pile. Each vehicle's newest request is always among the next served, so per-vehicle latency under lifo may be tolerable even while request-level age is unbounded. The honest exhibit is per-vehicle time from first ask to first useful answer, p95, plus the fraction of vehicles never answered within the mission. Run it before leaning on the mausoleum: if lifo's per-vehicle p95 comes back decent, the anti-lifo case rests entirely on the guarantee and the telemetry hygiene, and the recommendation text should be written so that survives. The bound's real edge over lifo is the wait ceiling: with cap k* and deterministic service, every admitted request at position j < k* is served within (j+1)/mu, and the construction puts the worst position at the deadline: at rung 0, (k*+1)/mu = 3 x 6.67 = 20.0 = P exactly, guaranteed since lambda - k* = 1.0; at C3 (lambda = 1.8, k* = 1) the last slot survives with probability 0.8, so the guarantee is exact for all but the final position and probabilistic there. Guarantee versus no guarantee, backlog 3 versus 146: those are the dominance claims that survive; 0.0012 of throughput is not one.

(iv) The break he asked for, from his own data: the ladder prices the bound as free (no message change), but k* = f(P, ell, mu) has an input the other rungs do not need: the link latency. On a static, measured link that is a config constant and the pricing holds. On a varying or unknown link a fixed bound must pick one k, and the CR-50 static sweep already priced that: the best single counter (k=1) leaves 0.0456 served/step on the table at its worst rung, 30 percent of capacity, while the age cap (one timestamp) covered six of seven rungs at worst shortfall 0.0105 and admit self-adapts per request. So the ladder INVERTS on variable links: bound < age cap < admit becomes age cap or admit first, bound last. The recommendation must be conditioned in one sentence: "static known link: the bound, free and closed-form; varying or unmeasured link: the age cap, then admission control." Without that sentence a reviewer wins with the paper's own sweep table.

(v) The missing lever a queueing person asks for: preemption, since LIFO-preemptive is the age-of-information literature's darling. Answer with arithmetic, not an arm: at cv=0, admit already runs at 99.3 percent of mu (0.1490 of 0.15), so the ENTIRE remaining space of disciplines, preemptive or otherwise, is worth at most 0.0010 served/step, one ninth of the MPE. The lever search at cv=0 closes by ceiling arithmetic, not by exhaustion, and preemption specifically is strictly wasteful at deterministic service (the in-service job was feasible at start and stays feasible, so preempting it trades a sure completion for a restart). SJF and the c-mu rule degenerate at equal service times. Where the question genuinely reopens is cv > 0, which is already in flight as svccv; the one cheap arm worth ADDING to that battery is preempt-on-overrun: preempt only when the realized draw has already exceeded the admitted mean, the single case where preemption can pay. That is my answer to "what is missing": nothing at cv=0, by arithmetic; at cv > 0, one arm, and it slots into a battery already running.

### 5. Q3: the one experiment

The first cross-tier confirmation run. Blind versus refund (the discard rule, the paper's biggest and cheapest lever) at ONE operating point, n=12 clear link, default fleet, five to ten ProjectGL missions per arm, scored on the observables both tiers share: mission success, arrived fraction, blue losses. Registered form: sign of the success gap and the blue-loss gap; falsifiers: either sign flips, or the tier-2 gap is under one tenth of the tier-1 point estimate. No served_per_step, no console telemetry: tier 2 does not owe us our instruments.

Why this one. The sponsor's blocked decision is not "which lever": inside SandTable that argument is as settled as it is going to get. The blocked decision is "may I act on this simulator at all". Every requirement the paper writes (discard rule, timestamp, staffing curve, autonomy ordering) is single-tier evidence today, and the program's own premise, SandTable as the fast search companion whose findings ProjectGL confirms, currently has ZERO cross-tier data points. One sign-level confirmation converts the entire results table from "the 0.1-second simulator says" to "the two-tier workflow says", which is the only sentence that moves a GVSC requirements decision. And feasibility picks the same experiment: at tier-2 cost you get single-digit missions per arm, so only the discard-rule contrast, 50x on served at n=12 (0.0028 versus ~0.147), double-digit points on success, is detectable at that sample size. The k*-versus-admit gap (0.0014) will never be visible at tier 2. The biggest effect is the only testable one, and it happens to be the one that writes a console requirement.

Rejected: CR-46 v2 mixed patience (a real decision, per-class deadline handling in a message format that freezes early, but same-tier evidence with likely small effects; it is the named fallback if ProjectGL access is blocked this quarter). C5 and CR-8 (no named decision behind either). A third robustness battery (maps and svccv are already running; a third axis adds a row, not a decision). The identity battery (an audit, and audits do not unblock sponsors).

### 6. Scoreboard and standing items

- His retry defense of non-tautology: wrong by cancellation, logged above. His "three bins not two": one right and negligible, two category errors (dropped and refused consume no service). The two bins that DO bite were in his own counters, aggregated invisibly: that is an instrument finding, and the counter split (two ints) should land before 9448883 is read.
- Pre-data registrations for 9448883, timestamped now: residuals rank-ordered fifo ~ rand > lifo > admit, peaking n=6-10, shrinking at n=16; lifo residual ~ 0.0036 at n=16; admit residual under end effect everywhere at cv=0. If the read-out matches, the falsifier fired for the instrument reason and the four-bin repair stands; if residuals are NOT rank-ordered, my bin story is wrong and I will say so.
- P4's substitution result is the mechanism spine confirmed, but note it is half-entailed: at saturation two arms both at zero dead work MUST tie on served by the identity, so the informative half of P4 is only that admit alone reaches 99.3 percent of mu, leaving nothing to substitute for.
- Owed before the recommendation ships: same-battery TOST of bound versus admit versus lifo on served_per_step at n=12 and 16; the per-vehicle p95 answer-latency table; the sharp-cell count m for k*; the conditioning sentence for variable links.
- My own ledger: nothing of mine died this round. The Round 23 two-mode age law is what places the residual peak at mid spans; if the peak lands elsewhere, that law takes the hit too.

