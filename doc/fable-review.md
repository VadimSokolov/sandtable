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
