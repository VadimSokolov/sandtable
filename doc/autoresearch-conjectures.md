# Autoresearch run `aug12`: conjecture ledger

Workflow 7, **mode I** (idea search). The loop proposes falsifiable claims about SandTable's
mechanics, tries to kill them numerically, and records a verdict. The scoreboard is a verdict per
conjecture, not a scalar.

Governed by `references/rules/autoresearch-integrity.md`. Contract in `.autoresearch/contract.json`;
full search trace in `results.tsv` (untracked). This file is the human-readable index.

## Measurement contract

| Item | Value |
| --- | --- |
| Metric | `success` (mission success rate), direction max |
| Unit of replication | a **block**: block *b* at *R* reps runs mission seeds *bR .. bR+R-1* and reports the block mean |
| Contract blocks | 0-31 |
| Proxy tier | 16 blocks x 16 reps = 256 missions/condition, about 10 s |
| Full tier | 32 blocks x 64 reps = 2048 missions/condition, about 78 s |
| Noise floor (full tier) | block sd 0.0599, se 0.0106, **MDE 0.0246** |
| Minimum practical effect | 0.03 (above MDE, so the gate can see what we claim to care about) |
| Frozen | `tools/ar_eval.py`, `scenarios/` |

Block sd is within Monte-Carlo error of the pure binomial value, so precision scales with total
missions per condition and nothing structural inflates it.

## Verdict key

`refuted` the numerical test killed it. `open` tested, not resolved, budget spent.
`supported` survived a falsification attempt at the full tier and cleared the gate.
A `supported` conjecture is a paper *candidate*, not a paper claim: it still owes ablation and the
promotion criteria in the integrity rule.

## Conjectures

| # | Conjecture | Status | Verdict |
| --- | --- | --- | --- |
| C1 | Under a Gilbert-Elliot channel calibrated to the **same mean drop rate** as the Bernoulli ladder, direct-control mission success differs, and the direct-vs-supervisory crossover rung moves. Mean drop rate is therefore not a sufficient statistic for choosing a control mode. | in progress | |
| C2 | The ladder's top rungs are not resolvable: C4 and C5 produce identical results because every direct-control request already times out at C4. The six-rung ladder has fewer than six distinguishable levels, and the cut-off has a closed form. | mechanism derived, prediction queued | |
| C3 | There is no direct-vs-supervisory crossover at the published span (n=6): supervisory dominates at every rung. The crossover exists only in a 2-D (span x rung) structure, so a 1-D ladder sweep understates the modality result. | supported at proxy | |
| C7 | **Queue relief.** At a span where the single operator is the binding constraint, *degrading* the link **improves** direct-control mission success. First mechanism proposed (the stall/fallback quality gap) is **refuted**; the surviving mechanism is congestion collapse, restated as C8. | mechanism refuted, restated | |
| C8 | **CONFIRMED AT FULL TIER.** **Congestion collapse by unrefunded abandonment.** The operator spends a service slot on every request it receives, including requests whose answer will arrive after the requester has given up. At large span the offered load exceeds capacity, almost every request is abandoned, and packet loss then acts as unintended admission control. Explicit admission control should remove the interior optimum and dominate at every rung. | **confirmed, full tier, 32 blocks x 64 reps** | |
| C9 | **Fan-out overpredicts.** The Olsen-Goodrich duty-cycle capacity `1 + NT/IT`, measured from SandTable's own hold durations, exceeds the span at which measured mission success actually peaks, and the gap widens with jamming. | instrumented (CR-11), untested | |
| C4 | Correcting teleoperation stop semantics (CR-2) moves the crossover toward cleaner links, because a severed-link teleoperated vehicle currently keeps driving at 54.5% speed. | queued | |
| C5 | A behaviour-based follower (on-platform dead reckoning) degrades less than a link-based follower as the ladder worsens, matching the sign of Cheung et al. 2022 at mission rather than path-error level. | queued (needs CR-1, CR-3) | |
| C6 | Network robustness (r-robustness) and algebraic connectivity rank the same formations differently, so a formation tuned for connectivity is not thereby robust. | queued (CR-8) | |

## Log

- **Setup.** Contract initialised at 24 blocks; noise reported MDE 0.0384 against MPE 0.03, so the
  design was resized to 32 blocks x 64 reps, giving MDE 0.0246. Recorded because the first sizing
  was not viable and that is part of the method.
- **Proxy tier validated.** Four configurations spanning the range were run at both tiers. Proxy
  (16x16) and full (32x64) rank them identically (supervisory 0.746/0.733 > direct C0 0.617/0.656 >
  direct C3 0.527/0.539 > direct C5 0.375/0.394). Proxy is biased slightly low for direct control
  but preserves order, which is what the search needs.
- **New missions go in `experiments/ar_scenarios/`.** `scenarios/` is frozen by the contract, so a
  mission added for a new conjecture lives outside it and the tamper guard stays meaningful.
- **CR-9 channel implemented.** Gilbert-Elliot chain calibrated so stationary drop rate equals the
  ladder value rung by rung; verified empirically at C1-C5 (max deviation 0.0012) with mean burst
  length 4.0 against Bernoulli's 1.05-2.22. Draws exactly one uniform per message, the same as the
  Bernoulli path, so the two channels stay stream-aligned and their comparison is paired. Default
  path byte-identical across all four scenarios.


## Findings in progress

### The crossover is two-dimensional (C3)

Proxy, `sc_span_control`, 16 blocks x 16 reps, Bernoulli channel, published parameters.

| span | supervisory | C0 | C1 | C2 | C3 | C4 | C5 | direct leads at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n=2 | 0.387 | 0.441 | 0.402 | 0.344 | 0.273 | 0.141 | 0.141 | C0, C1 |
| n=3 | 0.289 | 0.355 | 0.258 | 0.273 | 0.180 | 0.105 | 0.105 | C0 |
| n=4 | 0.535 | 0.578 | 0.516 | 0.500 | 0.379 | 0.219 | 0.219 | C0 |
| n=6 | 0.746 | 0.617 | 0.652 | 0.598 | 0.527 | 0.375 | 0.375 | never |
| n=8 | 0.852 | 0.512 | 0.555 | 0.672 | 0.660 | 0.598 | 0.598 | never |

Direct control leads only where the span is small **and** the link is nearly clear, and the rung at
which supervisory takes over moves left as span grows until, at n>=6, direct never leads at all.
A one-dimensional ladder sweep at a single span cannot show this and understates the modality result.

Comparisons are valid **within** a span only. Success is `arrived >= 0.5 * n`, and the integer
threshold makes n=3 demand 2 of 3 (67%) where the even spans demand 50%, which is why the n=3 row
sits low. Every conjecture below is tested within a fixed span.

### The ladder saturates above a computable rung (C2)

C4 and C5 are identical to every decimal place at all five spans. The mechanism is exact rather than
statistical: in `c2.py` a **dropped** request and a request that **exceeds patience** have the same
two consequences, `await_until = k + patience` and `resolved_quality = q_fallback`. Once every
request times out, the drop rate cannot affect anything, so rungs above that point are the same rung.

A request reaches the operator only while

    2 * latency + 1 / service_rate  <=  patience

which at the published `service_rate = 0.15`, `patience = 20` gives a cut-off latency of 6.67 steps.
C4's latency is 8, so C4 and C5 must coincide, and they do. That is a free-server lower bound: queue
contention adds to the wait, so at higher span the ladder saturates at a *lower* rung still.

**Falsifiable prediction, queued:** raising `patience` past 38.67 must make C4 and C5 separate.
Testing at patience 20 (neither resolves), 30 (C4 resolves, C5 does not), and 45 (both resolve).


### C7 falsification battery: the stall gap is not the mechanism

Proxy, `sc_span_control`, n_blue=8, direct, 16 blocks x 16 reps.

| arm | C0 | C1 | C2 | C3 | C4 | C5 |
| --- | --- | --- | --- | --- | --- | --- |
| `legacy` (published) | 0.512 | 0.555 | **0.672** | 0.660 | 0.598 | 0.598 |
| `stall_eq` (`q_stall` raised to `q_fallback`) | 0.664 | 0.711 | 0.707 | **0.820** | 0.699 | 0.699 |
| `teleop` (CR-2 physics, waiting means stopped) | 0.012 | 0.090 | **0.312** | 0.246 | 0.000 | 0.000 |

The first proposed mechanism was the quality gap: an agent waiting on the operator sits at
`q_stall` 0.30, and a dropped request promotes it to `q_fallback` 0.50, so jamming might simply be
buying the difference. Closing that gap (`stall_eq`) **lifts the whole curve but leaves the rise
intact**, 0.664 at C0 to 0.820 at C3. The gap explains the level, not the slope. Mechanism refuted.

The `teleop` arm is the same effect at 26x magnification, and it is the physically honest arm: with
a clean link, eight teleoperated vehicles succeed 1.2% of the time, and jamming them to C2 takes
that to 31%. Reading the code for what could produce this gives the surviving mechanism:

```python
if link_ok:
    done = max(op.operator_free_at, k + lat) + 1.0 / op.service_rate
    op.operator_free_at = done          # the slot is spent HERE, unconditionally
    if done + lat - k <= op.patience: ...serviced...
    else: ...the requester gives up, and the slot was spent anyway...
```

The operator works every request it receives, including the ones whose answers will arrive after
the requester has stopped caring. At span 8 the offered load exceeds the service rate, the queue
never drains, essentially every request is abandoned after the operator has already paid for it,
and the vehicles sit stopped. Dropping messages is then the only thing shedding load. This is
congestion collapse, and in the queueing literature it is an M/M/1+G queue where the server does not
learn about reneging (see `doc/lit-ideas.md` D4a). Restated as C8 and tested by CR-10.

Supporting instrumentation, same scenario:

| span | operator utilization C0 | utilization C2 | mean serviced wait C0 | wait C2 |
| --- | --- | --- | --- | --- |
| n=2 | 0.349 | 0.319 | 7.40 | 11.22 |
| n=4 | 0.585 | 0.493 | 8.95 | 11.93 |
| n=8 | 0.862 | 0.823 | 10.82 | 13.35 |

Utilization 0.86 at n=8 on a single server is the saturation signature, and it *falls* under
jamming, which is the load shedding made visible.


### C8 confirmed: the interior optimum is a missing interface feature, not a property of jamming

Proxy, `sc_span_control`, n_blue=8, direct, 16 blocks x 16 reps. `blind` is the published operator.

Mission success:

| policy | C0 | C1 | C2 | C3 | C4 | C5 |
| --- | --- | --- | --- | --- | --- | --- |
| `blind` | 0.512 | 0.555 | **0.672** | 0.660 | 0.598 | 0.598 |
| `refund` | **0.816** | 0.758 | 0.754 | 0.699 | 0.598 | 0.598 |
| `admit` | **0.840** | 0.766 | 0.758 | 0.711 | 0.551 | 0.605 |

Share of requests that came back with an operator decision:

| policy | C0 | C1 | C2 | C3 | C4 | C5 |
| --- | --- | --- | --- | --- | --- | --- |
| `blind` | 0.180 | 0.227 | 0.337 | **0.397** | 0.000 | 0.000 |
| `refund` | **0.797** | 0.743 | 0.674 | 0.505 | 0.000 | 0.000 |
| `admit` | 0.730 | 0.711 | 0.662 | 0.505 | 0.000 | 0.000 |

Three things at once.

1. Under the published operator, **jamming raises goodput**: 18% of requests answered on a clean
   link, 40% at C3. That is the collapse made explicit. Refund the slot and the ordering inverts to
   the intuitive one, 80% down to 51%.
2. **The interior optimum disappears** under both fixed policies. It was never a statement about
   contested communications; it was the queue shedding load the only way it could.
3. At C0 the mission gain from admission control alone is **+0.328 success**, which is larger than
   the entire published direct-versus-supervisory gap at that span (supervisory scores 0.852). The
   recommendation this supports is an interface requirement, not a radio requirement: tell the
   vehicle the operator cannot reach it, immediately, instead of leaving it stopped for its full
   patience window.

C4 and C5 goodput is exactly 0.000 for every policy, which is conjecture C2 measured rather than
derived: past the latency cut-off nothing is serviceable and no policy has anything to manage.

### The closed form (`tools/queue_theory.py`)

The operator is an M/D/1 queue with deterministic abandonment, so it can be solved rather than only
simulated. Two thresholds fall out, both of which the simulator obeys.

**Latency cut-off.** A reply fits inside the requester's patience only while
`2*latency + 1/service_rate <= patience`. At the published operating point that is
`latency <= 6.67` steps, so C4 (latency 8) and C5 (latency 16) are the same rung. Measured
goodput at both is 0.000.

**Collapse span.** In the collapsed regime every request abandons, so each vehicle cycles
`patience + decision_interval` steps between requests, and the blind operator pays `1/service_rate`
for every request that arrives. The queue sustains its own overload once

    n  >=  n* = (patience + decision_interval) * service_rate / (1 - p_drop)^2

At `sc_span_control`'s operating point (patience 20, decision_interval 22, service_rate 0.15) that
is **n\* = 6.30 on a clean link**. The scenario ships six vehicles. The centerpiece configuration
is parameterized within 5% of the operator's saturation cliff, which is why its modality crossover
looked so sharp, and it is why n=8 is the smallest span in the sweep that shows the rise.

Jamming *raises* n\*, because a dropped request is a request the operator never has to work:
6.30 at C0, 6.98 at C1, 7.78 at C2, 9.84 at C3. So at n=8 the theory says collapsed through C2 and
stable at C3, and the measured goodput turns the corner in exactly that interval.

The tool also carries `queue_only_sim`, the same request-and-abandon rules with the mission removed
entirely. It reproduces the interior optimum on its own, which is the cleanest available evidence
that the effect belongs to the queue and not to terrain, sensing, or attrition.


### The modality gap is mostly the missing feature (span sweep, clean link)

Proxy, `sc_span_control`, comms C0, published physics, 16 blocks x 16 reps. Success rises with span
in every arm because red strength is held fixed while blue grows, so read the *gaps*, not the levels.

| span | `blind` | `admit` | supervisory | superv - blind | superv - admit |
| --- | --- | --- | --- | --- | --- |
| n=2 | 0.441 | 0.441 | 0.387 | -0.055 | -0.055 |
| n=4 | 0.578 | 0.621 | 0.535 | -0.043 | -0.086 |
| n=6 | 0.617 | 0.734 | 0.746 | +0.129 | +0.012 |
| n=8 | 0.512 | 0.840 | 0.852 | **+0.340** | +0.012 |
| n=10 | 0.750 | 0.855 | 0.957 | +0.207 | +0.102 |
| n=12 | 0.863 | 0.949 | 0.988 | +0.125 | +0.039 |

Under the published operator the supervisory advantage peaks at 34 points at n=8. Under admission
control it is 1 point there and never exceeds 10 across the sweep. **The published finding that
on-platform autonomy dominates at high span is, at a clean link, substantially an artifact of an
operator that cannot say "not now".**

`blind` and `admit` are bit-identical at n=2, which is the theory's own consistency check: below
n\* nothing is ever abandoned at the operator, so the policy has nothing to act on.

### CR-13: a second artifact of the same family, found by audit rather than by search

`entities.py` initializes `decision_cooldown` to zero for every entity, so on step 0 every blue
agent fires a decision event at once and the operator opens the mission with a synchronized burst
of n requests. Vehicles in the field are not phase-locked. On one seed at n=8, C0, giving each
agent a uniform starting phase moves goodput from 0.013 to 0.361, which is large enough that the
congestion result cannot be reported before checking whether it is partly a startup transient.

Opt-in as `params["stagger_decisions"]`; off is byte-identical (hash `90c4763ba205b9d8`).
This is why the full-tier confirm was stopped and requeued rather than run to completion: confirming
a configuration that may be superseded is the waste the two-tier rule exists to prevent.

**Verdict: C8 survives.** Across 16 blocks the single-seed reading does not hold up. Operator
goodput at n=8:

| arm | C0 | C1 | C2 | C3 | C4 | C5 |
| --- | --- | --- | --- | --- | --- | --- |
| synchronized start, `blind` | 0.180 | 0.227 | 0.337 | 0.397 | 0.000 | 0.000 |
| staggered start, `blind` | 0.194 | 0.271 | 0.370 | 0.418 | 0.000 | 0.000 |
| staggered start, `admit` | 0.738 | 0.725 | 0.678 | 0.520 | 0.000 | 0.000 |

Mission success tells the same story: the interior optimum shrinks from +0.160 (C0 to C2) under a
synchronized start to +0.086 (C0 to C3) under a staggered one, and admission control still buys
+0.270 at a clean link.

| n=8 success | C0 | C1 | C2 | C3 | C4 | C5 |
| --- | --- | --- | --- | --- | --- | --- |
| synchronized, `blind` | 0.512 | 0.555 | **0.672** | 0.660 | 0.598 | 0.598 |
| staggered, `blind` | 0.551 | 0.586 | 0.586 | **0.637** | 0.539 | 0.539 |
| staggered, `admit` | **0.820** | 0.813 | 0.734 | 0.652 | 0.535 | 0.555 |

Staggering buys 0.01 to 0.05 of goodput, not the 0.35 one seed suggested. The collapse is a
steady-state property of the queue, not a startup transient: `blind` still rises with jamming under
a staggered start, `admit` still falls, and admission control still delivers roughly four times the
goodput on a clean link. The one-seed number was noise, and the cost of checking it was one proxy
battery against the cost of publishing a transient as a mechanism.


Under CR-2 teleoperation physics the same robustness check gives, at n=8:

| arm | C0 | C1 | C2 | C3 |
| --- | --- | --- | --- | --- |
| staggered, `blind` | 0.027 | 0.164 | 0.348 | 0.379 |
| staggered, `admit` | 0.734 | 0.703 | 0.703 | 0.582 |

so the teleoperation result is 27x rather than 59x once the opening burst is removed, and every
qualitative statement stands.

### C10: the staffing curve (CR-14)

Generalizing the operator to a crew of `c` consoles makes the collapse threshold linear in crew
size, `n* = c (patience + decision_interval) * service_rate / d`, so the one-console threshold of
6.30 vehicles becomes 12.60 with two. Eight vehicles straddle them, and the simulator agrees:
operator goodput at n=8, C0 is **0.135 on one console and 0.990 on two**. One console with
admission control reaches **0.73**.

That comparison is the decision-relevant one, because the two levers have very different costs:
an interface feature that tells a vehicle "not now" recovers most of the benefit of hiring a
second operator. Full staffing sweep queued.

---

## Promotion plan (Step 11), drafted before the full-tier confirm lands

Nothing below is written into the manuscript until the gates pass at the full tier and the
pre-flight protocol runs. Recorded now so the promotion is mechanical rather than improvised.

### Scope of contamination, stated precisely

`build_c2` returns None unless a scenario sets `control_mode`, and only `sc_span_control` does.
UC-3, UC-5 and UC-7 have no operator at all, so the route-choice and sensor-swarm findings are
untouched. Everything below is confined to the centerpiece study, which is exactly where the
modality claims live.

### The framing

A fast mission-level model is only as good as the mechanism that was left out of it. SandTable's
operator was a queue without admission control, and that single omission produced a headline
result (degrading the link improves mission success) that reads as a property of contested
communications and is not one. The closed form says exactly when the omission bites, the remedy is
an interface feature rather than a radio, and the same analysis turns the span-of-control study
into a staffing curve. That is a stronger contribution than the original finding, because it is
a statement about what this class of model has to contain to be trusted.

### Edits required

| Location | Change |
| --- | --- |
| Abstract | "at high span on-platform autonomy is better at every communications level" needs its condition: that holds for an operator with no admission control, and the gap closes to about a point when the operator can refuse |
| Contributions | the moving-optimum item gains a second half: the closed-form thresholds and the admission-control result |
| Related work | add the queueing-with-abandonment thread beside the existing fan-out citations: `garnett2002impatient`, `gans2003callcenters` |
| Model, command section | state the abandonment semantics explicitly, add both closed-form thresholds, introduce `queue_policy` and `n_operators` |
| Model, ladder section | latency and drop covary on the C0--C5 ladder, and direct control saturates above a computable latency, so the ladder has fewer distinguishable rungs than levels for this modality |
| Results | new subsection: congestion collapse, the two thresholds, the admission-control contrast, the staffing curve |
| Discussion | the design recommendation, and the point that it is an interface requirement rather than a communications one |
| Limitations | the operator's abandonment semantics were a modeling choice, both variants are now implemented, and which one is right is an empirical question about real command posts |
| Future work | the "network of servers with dynamic span reallocation" item is now half delivered (static crews, CR-14); what remains is dynamic reallocation and handoff |

### Numbers that must reach `results/numbers.txt`

Every one traces to a proxy or full-tier `AR_ROW` line in the run logs and to a commit hash.

- `n* = (patience + decision_interval) * service_rate / (1-p_drop)^2`, evaluated at the
  `sc_span_control` operating point: 6.30 vehicles at C0, 12.60 with a crew of two.
- latency cut-off `(patience - 1/service_rate)/2 = 6.67` steps, which places C4 and C5 on the
  same rung and is measured as goodput exactly 0.000 at both.
- goodput at n=8: 0.180 (blind, C0) rising to 0.397 (blind, C3); 0.797 (refund, C0) falling to
  0.505 (refund, C3); 0.135 on one console against 0.990 on two.
- success at n=8, C0: 0.512 blind, 0.840 admit, published physics; 0.012 blind, 0.695 admit,
  teleoperation physics; 0.027 and 0.734 respectively under a staggered start.


---

## Full-tier confirmation of C8

`sc_span_control`, n_blue=8, direct, 32 blocks x 64 reps (the contract seed set), commit `1678d04`.
Paired on block-matched mission seeds, gated by `tools/autoresearch.py gate` against the contract's
MPE of 0.03 and 60% consistency requirement.

| arm | C0 | C2 |
| --- | --- | --- |
| `blind` (published operator) | 0.5625 | 0.6768 |
| `admit` (admission control) | 0.7998 | 0.7612 |

| gate | contrast | paired delta | t | wins | verdict |
| --- | --- | --- | --- | --- | --- |
| G1 | admission control at C0 | **+0.2373** +/- 0.0147 | 16.14 | 32/32 | KEEP |
| G2 | the interior optimum, `blind` C2 over C0 | **+0.1143** +/- 0.0157 | 7.29 | 29/32 | KEEP |
| G3 | with admission control, C0 over C2 | **+0.0386** +/- 0.0147 | 2.63 | 23/32 | KEEP |

G2 and G3 together are the whole result. Under the published operator, degrading the link from
clear to C2 **improves** mission success by 11.4 points, and the effect clears every arm of the
gate. Give the operator the ability to refuse a request it cannot serve in time, and the same
contrast **reverses sign**: the clear link is now better, by 3.9 points. The pathology and its
remedy are both statistically robust at full scale, on the contract seeds, paired.

Proxy tier had these at 0.512 / 0.672 and 0.840 / 0.758 against full tier 0.5625 / 0.6768 and
0.7998 / 0.7612. Every ranking is preserved, which is the fourth independent check that the
16x16 proxy tracks the 32x64 tier on this scenario.


---

## The throughput cliff (Hopper, proxy tier, `st-searchC-9437188`)

Vehicles delivered to the objective under teleoperation physics, one operator, **clean link**,
16 blocks x 16 reps. `arrived` is a count, so unlike `success` it is comparable across spans.

| span | `blind` (published) | `admit` | crew of 2 | supervisory |
| --- | --- | --- | --- | --- |
| n=2 | 0.38 | 0.38 | 0.41 | 0.39 |
| n=3 | 0.91 | 0.91 | 0.91 | 0.90 |
| n=4 | 1.26 | 1.27 | 1.42 | 1.33 |
| n=5 | 1.97 | 1.90 | 2.20 | 2.26 |
| n=6 | **2.21** | 2.32 | 2.45 | 2.57 |
| n=8 | **0.68** | 3.45 | 3.60 | 3.79 |
| n=10 | **0.00** | 4.75 | 4.87 | 4.94 |
| n=12 | **0.00** | 5.85 | 5.91 | 5.99 |

Under the published operator, throughput **peaks at six vehicles and falls to exactly zero at ten**.
Twelve teleoperated vehicles, one operator, a perfect radio, and not one of them reaches the
objective. Every other arm rises monotonically; admission control alone delivers 5.85 of 12.

The closed form put the collapse span at **n\* = 6.30**, and the measured throughput peak is at
n=6. A closed-form threshold derived from three timing parameters predicts, to within one vehicle,
where an agent-based mission simulation stops delivering anything at all.

This is the chart the sponsor should see. It says the capacity limit of a one-operator formation is
not a soft degradation but a cliff, that the cliff sits at a computable span, and that an interface
feature moves it rather than a better radio.


## G4 and G5: the teleoperation gates, full tier (Hopper, `st-gateB-9437187`)

`sc_span_control`, n_blue=8, direct, CR-2 teleoperation physics, 32 blocks x 64 reps.

| arm | C0 | C2 |
| --- | --- | --- |
| `blind` (published operator) | **0.0083** | 0.2900 |
| `admit` | **0.7534** | 0.6738 |

| gate | contrast | paired delta | t | wins | verdict |
| --- | --- | --- | --- | --- | --- |
| G4 | admission control at C0 | **+0.7451** +/- 0.0130 | 57.39 | 32/32 | KEEP |
| G5 | the interior optimum, `blind` C2 over C0 | **+0.2817** +/- 0.0107 | 26.34 | 32/32 | KEEP |

Eight teleoperated vehicles, one operator, a **clean link**: 0.8% mission success. Let the operator
refuse work it cannot finish in time and the same configuration reaches 75.3%. Under a staggered
start the pair is 0.0239 and 0.7500, so the opening burst is not what produces it.

G5 is the pathology at its most extreme: jamming the link to C2 multiplies success by 35.

## C9: fan-out is load-dependent and does not see the cliff

Olsen and Wood's `1 + NT/IT`, measured from SandTable's own hold durations, against span.
Teleoperation physics, clean link, proxy tier.

| span | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `blind` fan-out estimate | 3.88 | 3.63 | 3.36 | 3.05 | 2.59 | 2.18 | 2.14 | 2.13 |
| `blind` vehicles delivered | 0.38 | 0.91 | 1.26 | 1.97 | **2.21** | 0.68 | **0.00** | **0.00** |
| `admit` fan-out estimate | 3.88 | 3.63 | 3.45 | 3.21 | 3.05 | 3.13 | 3.38 | 3.76 |

Three things, and the third is the one that matters.

1. The estimate is **not load-invariant**. It falls from 3.88 to 2.13 as span grows, so the answer
   to "how many vehicles can this operator hold" depends on how many they are currently holding.
   The identity assumes it does not.
2. It never equals the empirical capacity. Throughput peaks at six vehicles; the estimate reads
   between 3.9 and 2.6 across that range and never lands on it.
3. **It gives no warning of the cliff.** Between n=8 and n=10 the estimate moves from 2.18 to 2.14,
   a 2% change, while delivered vehicles go from 0.68 to zero. A metric intended to bound span is
   flat across exactly the interval where the formation stops working.

Under admission control the estimate is roughly flat in span (3.88 to 3.05 to 3.76), which is what
a load-invariant capacity metric should look like. So the instability is a symptom of the queue
pathology rather than of the metric alone, and the practical reading is that fan-out is safe to use
only on a system that already has admission control. That is a sharper version of the correction
Cummings and Mitchell 2008 made when they added wait time to the estimate.

Supervisory reads exactly 0.00 at every span because there are no holds to measure, which is
correct by construction and must be stated wherever the column appears.


---

## P2 confirmed at full tier: the threshold is the operator's, not the link's

Hopper `st-theory-i-9437166`, 32 blocks x 64 reps. Both predictions were written into this ledger
before the runs, which is what makes them confirmations rather than searches.

### P2a. `service_rate` creates and destroys the interior optimum

`n* = (patience + decision_interval) * service_rate`. Nothing in it refers to communications.

| arm | n\* | span | regime | goodput C0 -> C3 | success C0 -> C3 |
| --- | --- | --- | --- | --- | --- |
| `n8_fast` (sr 0.30) | 12.60 | 8 | stable | 0.991 -> 0.627, falling | 0.889 -> 0.751, falling |
| `n8_pub` (sr 0.15) | 6.30 | 8 | collapsed | 0.170 -> 0.398, **rising** | 0.562 -> 0.681, **rising** |
| `n4_slow` (sr 0.075) | 3.15 | 4 | collapsed | 0.122 -> 0.225, **rising** | 0.233 -> 0.263, **rising** |
| `n4_pub` (sr 0.15) | 6.30 | 4 | stable | 0.985 -> 0.569, falling | 0.602 -> 0.384, falling |

A clean two-by-two. The *same span* n=4 shows the "jamming helps" effect with a slow operator and
not with the published one; the *same span* n=8 shows it with the published operator and not with a
fast one. The effect follows the threshold, not the span and not the link.

`n4_slow` also reads exactly 0.000 at C3, which the same closed form predicts for a different
reason: at service rate 0.075 the latency cut-off is `(20 - 13.33)/2 = 3.33` steps, and C3's
latency is 4.

### P2b. `patience` moves the latency cut-off, to the decimal

Cut-off `= (patience - 1/service_rate)/2`. The prediction on record was that C4 and C5 are the same
rung at the published patience, that C4 separates once patience exceeds 21.3, and that C5 needs
patience above 38.67.

| patience | predicted cut-off | C3 (lat 4) | C4 (lat 8) | C5 (lat 16) |
| --- | --- | --- | --- | --- |
| 20 | 6.67 | 0.569 | **0.000** | **0.000** |
| 30 | 11.67 | 0.635 | 0.416 | **0.000** |
| 45 | 19.17 | 0.641 | 0.423 | 0.195 |

Three separate on-off transitions, all three where the arithmetic says. Conjecture C2 moves from
observed to **proved**: the C0-C5 ladder does not have six distinguishable rungs for direct control,
it has as many as the operator's patience buys, and the formula says how many.


### Correction: the zeros are a tempo failure crossing a deadline, not paralysis

The throughput table above was first read as "the vehicles do not move". `hold_fraction` says
otherwise and the correction matters for how the result is stated.

| span | 2 | 4 | 6 | 8 | 10 | 12 |
| --- | --- | --- | --- | --- | --- | --- |
| `blind` hold fraction | 0.258 | 0.298 | 0.388 | 0.458 | 0.468 | **0.469** |
| `blind` mean hold length | 7.7 | 9.5 | 14.3 | 19.0 | 19.8 | **19.8** |
| `admit` hold fraction | 0.258 | 0.291 | 0.329 | 0.320 | 0.296 | 0.267 |

At n>=8 every hold runs to almost exactly `patience` (19.8 against 20), because every request times
out. The duty cycle is then 20 steps held against a 22-step cooldown, so the held share saturates at
20/42 = 0.476, and the measured 0.469 is that number. The vehicles are stopped about half the time,
not all of it.

What produces the zero is the combination with speed. `motion.py` scales speed by
`0.35 + 0.65 q`, and a timed-out vehicle drives at `q_fallback` 0.50, so it makes
`0.53 x 0.675 = 0.36` of its maximum. Over the 5.5 km to the objective at roughly 8 m/s of
terrain-limited speed, that is about 1900 s of travel against a mission window of 1800 s. **The
formation is not paralysed; it is too slow to finish before the clock expires.**

So the cliff is real and the mechanism is the queue, but "exactly zero" is partly a property of
this scenario's deadline. A longer mission window would deliver vehicles late rather than not at
all. The claim that survives without qualification is the non-monotonicity and its location: peak
throughput at n=6 against a predicted threshold of 6.30. The claim that needs the deadline stated
is the zero. **Queued: a duration-sensitivity check, so the paper says which is which.**

The policy arms also read the threshold directly. `blind` and `admit` are bit-identical at n=2 and
n=3, within noise at n=4 and n=5, separate at n=6, and diverge catastrophically at n=8. That is
n\* = 6.30 visible in the data without being fitted to it.


---

## C10 the staffing curve, confirmed at full tier (Hopper, `st-gateB-9437187`)

Operator goodput at C0, 32 blocks x 64 reps. The closed form puts the collapse span at
`n* = c x 6.30` on a clean link: **6.30** for one console, **12.60** for two, **18.90** for three.

| span | 2 | 4 | 6 | 8 | 10 | 12 | 16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 console, published | 1.000 | 0.985 | **0.759** | 0.170 | 0.060 | 0.015 | 0.007 |
| 1 console + admission control | 1.000 | 0.985 | 0.905 | 0.734 | 0.574 | 0.449 | 0.300 |
| 2 consoles | 1.000 | 1.000 | 1.000 | 0.990 | 0.980 | **0.810** | 0.045 |
| 3 consoles | 1.000 | 1.000 | 1.000 | 1.000 | 0.996 | 0.991 | 0.972 |

Both thresholds are visible in the data at the predicted spans and nowhere else. The one-console
arm is at 0.985 at n=4, mid-transition at n=6, and collapsed at n=8, bracketing 6.30. The two-console
arm is at 0.980 at n=10, mid-transition at n=12, and collapsed at n=16, bracketing 12.60. The three-
console arm is still at 0.972 at n=16, below its threshold of 18.90. A formula with three timing
parameters in it locates two separate cliffs, a factor of two apart, without being fitted to either.

**The staffing rule this supports:** one operator per 6.3 vehicles under a clean link, or
`ceil(n / (6.30 / (1 - p_drop)^2))` in general. Admission control does not raise the threshold, it
removes the cliff: the one-console arm degrades gracefully from 1.000 to 0.300 across the whole
sweep instead of falling off at six.

Read `success` on this grid with care. It rises with span in every arm because red strength is held
fixed while blue grows, so at n=12 and n=16 the published operator recovers on numbers alone
(0.847, 0.961) despite goodput near zero. Goodput and `arrived` are the honest discriminators here.

## P3 the ladder confounds two variables that behave differently

Proxy tier, n=8, latency and drop swept independently. Operator goodput.

Published operator:

| latency \ drop | 0.0 | 0.05 | 0.1 | 0.2 | 0.35 | 0.55 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.180 | 0.237 | 0.360 | **0.539** | 0.412 | 0.201 |
| 2 | 0.150 | 0.207 | 0.337 | **0.495** | 0.393 | 0.202 |
| 4 | 0.126 | 0.177 | 0.267 | **0.397** | 0.343 | 0.187 |
| 6 | 0.113 | 0.152 | 0.201 | **0.289** | 0.274 | 0.168 |
| 8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

With admission control:

| latency \ drop | 0.0 | 0.05 | 0.1 | 0.2 | 0.35 | 0.55 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | **0.730** | 0.731 | 0.694 | 0.597 | 0.413 | 0.202 |
| 4 | **0.654** | 0.620 | 0.584 | 0.505 | 0.361 | 0.189 |
| 8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

The two axes do not behave alike. **Latency only ever hurts**, monotonically, at every drop level.
**Loss is hump-shaped** under the published operator, peaking near drop 0.2 at every latency, and
monotone under admission control. The C0-C5 ladder raises both together, so its one-dimensional path
cuts diagonally across a surface that is monotone in one direction and humped in the other, and the
interior optimum seen on the ladder is that projection.

The predicted peak location holds too. The queue becomes stable when `(1-p)^2 <= 6.30/8 = 0.7875`,
that is `p >= 0.113`. The sampled points bracket it: drop 0.1 is still collapsed (0.360), drop 0.2
is stable (0.539).

The `lat8` row is conjecture C2 as an entire flat line. At latency 8 no request can be answered
inside patience, so goodput is exactly 0.000 at every drop rate, and mission success is constant at
0.598 across the whole row. The drop rate is not merely a weak factor there; it is inert.

## CR-15 confirmed: correlated demand puts the published scenario over the cliff

Operator goodput, C0, proxy tier.

| span | 2 | 4 | 6 | 8 | 10 | 12 |
| --- | --- | --- | --- | --- | --- | --- |
| stationary demand | 1.000 | 0.985 | **0.767** | 0.180 | 0.055 | 0.016 |
| terrain-driven demand | 1.000 | 0.989 | **0.255** | 0.085 | 0.023 | 0.009 |
| terrain-driven + admission control | 1.000 | 0.990 | 0.767 | 0.563 | 0.412 | 0.307 |
| terrain-driven + 2 consoles | 1.000 | 1.000 | 1.000 | 0.993 | 0.733 | 0.158 |

The collapse moves from between n=6 and n=8 to between n=4 and n=6. The closed form assumes
stationary arrivals and is therefore an optimistic bound, exactly as expected: a column entering
a defile calls for help together, and a queue sized for the average rate meets a burst. **The
centerpiece scenario as shipped, at its span of six, is on the wrong side of the cliff once demand
follows the ground.** Coupling strength at n=6 runs 0.767, 0.538, 0.380, 0.255, 0.160 for
`terrain_demand` 0, 0.5, 1, 2, 4, against 0.906 down to 0.655 with admission control.

## T3: route selection is an operator-attention decision

Mission success against `route_bias`, which slides the lane from the fast exposed corridor into the
slow covered band. Terrain-driven demand, n=6, clean link.

| route_bias | 0.0 | 0.2 | 0.4 | 0.65 | 0.85 | 1.0 |
| --- | --- | --- | --- | --- | --- | --- |
| direct, stationary demand | 0.312 | 0.281 | 0.344 | 0.617 | 0.973 | **0.988** |
| direct, terrain-driven demand | 0.207 | 0.172 | 0.176 | 0.332 | **0.902** | 0.539 |
| direct + admission control | 0.348 | 0.316 | 0.336 | 0.605 | 0.973 | **0.992** |
| supervisory | 0.336 | 0.344 | 0.484 | 0.777 | 0.977 | **1.000** |

Three arms out of four are best in deepest cover. The human-in-the-loop arm with terrain-driven
demand is not: it peaks at 0.85 and then **falls from 0.902 to 0.539** at full cover. The covered
lane is the hardest ground, the hardest ground generates the most operator demand, and at full
cover that demand collapses the queue faster than the cover repays it.

So the covered route, which every other configuration should take, is actively harmful under direct
control. Route planning under contested communications has to budget the operator's attention
alongside exposure and tempo, and this is the first result in the study that couples the route-choice
scenario to the command scenario rather than running them side by side.


---

## The throughput cliff is a DEADLINE effect. Correction, and what survives.

Hopper `st-duration-9439929`, proxy tier. Vehicles delivered, teleoperation physics, clean link,
one operator, identical in every respect except the mission window. The three scenario files differ
only in `duration` and share an `id`, so the arms are paired on common random numbers.

`blind` (published operator):

| span | 4 | 6 | 8 | 10 | 12 |
| --- | --- | --- | --- | --- | --- |
| 1800 s (as shipped) | 1.26 | 2.21 | 0.68 | **0.00** | **0.00** |
| 3600 s | 1.26 | 2.21 | 2.39 | 3.89 | 5.16 |
| 7200 s | 1.26 | 2.21 | 2.39 | 3.89 | 5.16 |

`admit` is **identical at all three windows**: 1.27, 2.32, 3.45, 4.75, 5.85.

Three conclusions, and the first one retracts a claim made earlier in this ledger.

1. **The zeros do not survive a longer window.** At 3600 s the same configuration delivers 3.89 and
   5.16 vehicles where it delivered none. The "throughput collapses to zero above n=10" statement
   was a property of the scenario's 1800 s deadline, not of the queue, and it is withdrawn in that
   form. So is "throughput peaks at six vehicles": with a longer window `blind` is monotone
   increasing in span (1.26, 2.21, 2.39, 3.89, 5.16). The coincidence between that apparent peak
   and n\* = 6.30 was a coincidence, and reading it as confirmation was wrong.
2. **3600 s and 7200 s are bit-identical**, so the missions genuinely finish inside 3600 s. The
   congested formation is slow by a bounded amount, not unboundedly slow.
3. **What survives is the tempo penalty and its consequence.** Operator congestion is real and
   full-tier confirmed on its own terms (goodput 0.170 against 0.734 at n=8). It costs tempo, and
   under a mission deadline a tempo cost converts into outright failure. Admission control is
   **completely insensitive to the window**, which is the sharper way to say it: the published
   operator needs twice the mission time to deliver what admission control delivers in the
   scheduled window, and at 3600 s it still delivers less (5.16 against 5.85 at n=12).

The claim that goes in the paper is therefore about tempo under a deadline, not about a capacity
cliff. Stated correctly it is still decision-relevant, because missions do have deadlines, but the
window has to be named every time the number is quoted.

This is the second reading in this run that a cheap robustness check overturned (the first being the
one-seed stagger result). Both were caught before promotion, which is the process working, and both
are recorded here rather than quietly dropped.

---

## Step 11 executed: what actually went into the manuscript (2026-08-22)

The promotion plan above was drafted before the full-tier gates landed. This records what was
promoted, where it differs from the plan, and what the plan got wrong.

### Delivered as planned

Abstract qualified and extended; a seventh contribution item naming both closed forms; the
queueing-with-abandonment thread in related work; the abandonment paragraph and `eq:nstar` in the
command-model section; the ladder-confound sentences in the comms section; a new Results subsection
`subsec:queue`; the Discussion paragraph on design ordering; the abandonment-semantics limitation;
and the "network of servers" future-work item rewritten now that CR-14 is delivered.

### Where the plan was wrong

- The plan expected the abstract's qualifier to be "the gap closes to about a point when the
  operator can refuse." The full tier says the gap does not close to a point, it **reverses**:
  `admit` scores 0.7998 at C0 against 0.7612 at C2 (G3, t = 2.63, 23/32). The abstract now says the
  sign flips, which is a stronger and more defensible statement than the one planned.
- The plan listed proxy-tier numbers (0.512 blind / 0.840 admit at n=8 C0). The full tier gives
  0.5625 and 0.7998. **No planned number was reused**; every figure in the paper is regenerated by
  `tools/make_queue_numbers.py` from the run logs in `report/data/queue/`, which is why the
  discrepancy surfaced at all.
- The plan did not anticipate the deadline retraction. The delivered-vehicle counts are now stated
  with their 1800 s window in both the results subsection and the limitations, and the limitations
  section says explicitly that success rates under that window are joint statements about the queue
  and the clock.

### Added beyond the plan

- `fig:queue`, a two-panel figure (staffing curve against the closed-form thresholds; the
  latency/loss decoupling), generated by `tools/make_figures.py:fig_queue` from the same run logs.
- `tab:queue_gate`, which reports the **search**, not only the winner: five gated contrasts with
  their paired t and blocks-won, recomputed from the per-block values in the logs.
- The fan-out negative result was promoted as a negative result, with the recommendation that a
  capacity number computed from neglect and interaction times not be used to size a span without a
  queueing check.
- Two references added after a follow-up literature search (both CrossRef-verified 2026-08-22):
  `ibrahim2018announcements` (`10.1111/poms.12796`), which frames staffing and delay announcements
  as two controls on one congestion and is the closest thing in the literature to the
  CR-14/CR-10 pairing; and `humann2023multioperator` (`10.1002/sys.21685`), the closest simulation
  precedent for multi-operator supervision. See `doc/lit-ideas.md` D4a.

### Verification at promotion

- Pre-flight PASS 5/5: 55/55 citations verified, 3 AI-vocabulary hits (threshold 10), 0 em-dashes,
  8/8 contribution refs resolve, compile clean. 35 pages.
- Byte identity re-checked as a **value** comparison rather than a digest, because the increment
  adds output-only metrics and a digest over the whole dict necessarily moves.
  `tools/byte_identity.py compare` over 4 scenarios x 8 seeds: all 15 pre-existing metrics identical
  to commit 75a5b3e, 13 new diagnostics added. A digest-only check would have read as a failure and
  hidden the fact that nothing measured actually changed.
- Tamper guard: 2 frozen paths unchanged, 32 seeds fixed.
- Cross-platform determinism: the same 4 x 8 dump produced on Hopper (Linux/AMD, job 9441155) and on
  the laptop (macOS/arm64) agrees on all 28 metrics across all 32 runs.
- Full suite on Hopper (job 9441117, node amd043): 182 passed, 0 failed, 175 s.

### The one claim not made

Which of `blind`, `refund`, and `admit` a fielded console resembles is an observation this model
cannot supply, and the paper says so rather than assuming the pessimistic default is realistic.
The `blind` default is retained as the model's shipping behavior because it is what was published,
not because it is believed to be right.

---

## CR-16 redesigned before implementation: shortest-remaining-patience-first is a no-op here

The proposal in `doc/sandtable-todo.md` was "serve the request with the least remaining patience."
Reading `c2.py` before writing any code shows that rule cannot do anything in this model, and the
reason is worth recording because it constrains what triage can mean here at all.

There is no queue object. A request's whole future is computed at the instant it arrives:

    start = max(operator_free_at, k + lat);  done = start + 1/mu;  reply = done + lat

The queue is the scalar `operator_free_at`, a reservation horizon. Requests reserve in arrival
order and never sit anywhere that could be reordered later. Two consequences:

1. Every requester has the same patience `P`, and every request is fresh at its own arrival, so
   all requests competing at a given moment have **identical slack**. Sorting by remaining patience
   sorts by nothing.
2. Reordering two feasible requests swaps *which* vehicle is served, not *how many* are. Throughput
   is invariant to order when the requesters are homogeneous.

So the only triage that can bite is one that exploits **heterogeneity in what the help is worth**,
and the model already has a source of it: with `terrain_demand` on, vehicles in difficult ground
request more often, so under first-come-first-served they crowd the queue; and because
`control_quality` enters motion and engagement multiplicatively, a quality point buys a different
amount depending on the ground the vehicle is standing on. That is a real asymmetry, not a
stipulated priority.

### CR-16 as it will actually be built: `queue_discipline`, with its own controls

Four arms, so the experiment carries its own null and its own adversary rather than only a
treatment:

| arm | order | role |
| --- | --- | --- |
| `fcfs` | entity index (unchanged) | default, byte-identical |
| `random` | permutation each step | **null control.** Reordering the loop also reassigns the RNG draws, so a treatment arm changes two things at once. `random` changes only the RNG assignment, with no priority signal in it. Any gap between a priority arm and `random` is priority. |
| `hard_first` | descending terrain difficulty | treatment |
| `easy_first` | ascending terrain difficulty | **adversarial control.** If `hard_first` helps, `easy_first` must hurt by a comparable amount; if both look like `random`, ordering is inert and the result is a clean negative. |

### Prediction, stated before the run

Ordering is inert without heterogeneity, so with `terrain_demand = 0` all four arms should agree
within noise. With `terrain_demand > 0` and a span in the congested band just above `n*`,
`hard_first` and `easy_first` should separate from `random` in opposite directions. Below `n*`
there is no queue to order and above it nothing is serviceable, so the effect should be
band-limited rather than monotone in span. A flat result across all three conditions is a
publishable negative: it would say that once admission control exists, *who* the operator serves
does not matter, only *whether* it refuses in time.

---

## CR-16 refuted, and the diagnosis is more useful than the null

Prediction, registered before the run: flat with no heterogeneity, band-limited separation of
`hard_first` and `easy_first` around `n*` with heterogeneity, flat again under `admit`.

### What the proxy tier said (`st-triage-9442644`, 16 blocks x 16 reps)

74 gated comparisons against the `random` null. Five marked: two better, three worse, 69 unmarked.
A 7% marking rate is what the gate produces under a true null, and the five are incoherent as a
priority story:

- The one marked cell in X2 favors `easy_first`, the **adversarial control**, not the treatment.
- The three marked cells in X3 are all three deterministic arms losing to `random` at the same
  span, which is the signature of a favorable RNG reassignment rather than of priority. This is
  precisely what the `random` arm was put in the design to expose.
- X4, the cleanest test (one span, sweeping the heterogeneity that is supposed to drive the
  effect), marks nothing and shows no dose-response: `hard` runs 0.605, 0.539, 0.520, 0.480 against
  `random` 0.547, 0.547, 0.555, 0.504 as `terrain_demand` goes 0, 1, 2, 4.

Throughput invariance held everywhere. Operator goodput agrees across all four arms at every span
in both X1 and X2, to three decimals in most cells, which is the model-structure claim confirmed.

### What the full tier said (`st-triagefull-9442679`, 32 blocks x 64 reps)

Y1 is the cell where the effect had to be if it existed, the strongest coupling at the congested
span: `random` 0.504, `hard` 0.503, `easy` 0.506. A spread of 0.003 against an MPE of 0.03. The
proxy spread of 0.024 at the same cell was noise, and it collapses when the tier is right.

Y2 re-ran the one proxy cell that gated (n=10, terrain_demand=2). The proxy gap of 0.121 in favour
of `easy_first` shrinks to 0.031 (`random` 0.685, `hard` 0.692, `easy` 0.716, `fcfs` 0.683) and no
longer gates. Confirmed as a multiple-comparison artifact.

Y3 put throughput invariance on the full tier. Goodput at n=8: 0.084 / 0.084 / 0.081 / 0.085 at
`terrain_demand=2`, and 0.049 / 0.049 / 0.049 / 0.050 at `terrain_demand=4`, across
fcfs / random / hard / easy. Three decimals, four arms, both couplings.

**Verdict: refuted.** Service order does not move mission outcomes in this model.

### Why, which is the part worth keeping

A null is only interesting if the test had power, so the obvious worry is that the priority arms
never actually reordered anything. Instrumenting a live run says they did: `hard_first` displaces
4.8 of 8 vehicles on average and leaves the order unchanged on only 11% of steps. Mechanically the
arms are doing their job.

The signal they sort on is what is missing. Measured over live running by `tools/make_triage_numbers.py` (8 seeds), the spread in terrain
difficulty **across the vehicles the operator is supervising** is mean **0.044**; an exploratory
4-seed probe over 5,569 observed steps gave mean 0.054, median 0.050, p90 0.090. Both are small. The map itself is not flat: difficulty ranges over 0.650 end to end, and the
lateral profile at mid-map spans 0.601. But almost all of that variation is **lateral**. Along the
open corridor the spread is 0.066 and along the covered band 0.135, so a formation moving down one
lane toward one objective samples about 8 to 20 percent of the range the terrain actually offers.

A power probe confirmed this is structural rather than a spawn artifact: a variant with
`spawn_spread` raised from 40 to 700 moved the observed spread only from 0.054 to 0.059 on the
same 4-seed probe, because
the vehicles converge onto the same route within a few hundred steps regardless of where they
start. The variant was discarded.

### The finding, stated so it survives

Triage by need is throughput-neutral by construction here, and value-neutral in practice, because
**an operator supervising one formation on one route has almost no need dispersion to exploit**.
The vehicles are in the same place by design; that is what a formation is.

This is a statement about the C2 architecture, not about queue discipline in general. Ordering
would only pay for an operator whose clients are in genuinely different situations, different
routes, different missions, different threat exposure, which is the heterogeneous-operator and
handoff architecture listed as still-open under CR-14. That makes the negative result a pointer
rather than a dead end, and it sharpens the paper's existing claim: once the operator can refuse in
time, *whether* it refuses is the whole lever, and *who* it serves is not one.

### Reporting obligation

`queue_discipline` stays in the model, opt-in and byte-identical off, because the null is worth
being able to reproduce. It does not earn a results subsection. One sentence belongs in the
discussion of the queue subsection, and the ordering-vs-refusal distinction belongs in the
limitations, since it bounds what the admission-control recommendation is claiming.

---

## Review round 1 (Fable). Three corrections, one of them to a published equation.

An adversarial review was commissioned against five hard questions; the full analysis is in
`doc/fable-review.md`. Every finding below was re-derived and re-measured here before anything
moved, because a reviewer's claim is a conjecture like any other. Earlier entries in this ledger
that quote `n* = 6.30`, `12.60`, `18.90` are left as written: they record what was believed then.
The corrected values are `6.45`, `12.90`, `19.35`.

### Correction 1: the collapse span was off by one step (CONFIRMED, equation changed)

`n* = c(P + tau)mu/d` assumed the collapsed cycle is `P + tau`. It is `P + tau + 1`. The cooldown
counter is decremented on each of `tau` steps and the decision event fires on the step AFTER it
reaches zero, so the trailing step belongs in the cycle.

Measured directly, instrumenting fresh requests in a live run at n=16 (deep in collapse, so every
request abandons and the cycle is the pure client cycle): mean 42.840 steps, median 43.0, over
2,458 cycles. Predicted `P + E[c] + 1 = 43.00` with `E[c] = 21.998` from the actual draw
`uniform[11, 33]`. The first attempt at this probe pooled entity indices across missions and
returned a nonsense mean of 7.678; keyed per (seed, entity) it is 42.840.

So `n* = c(P + tau + 1)mu/d`, giving 6.45 / 12.90 / 19.35. Every empirical bracket still holds
(one console transitions between 6 and 8, two between 12 and 16, three healthy at 16 below 19.35),
so no measurement changes, but the equation, `tools/queue_theory.py`, `tools/make_queue_numbers.py`,
`tools/make_figures.py`, and the figure annotations all did. The measured cycle is now a generated
macro so the equation and the implementation cannot drift apart again.

### Correction 2: the fan-out claim overreached (CONFIRMED, paragraph rewritten)

Two sub-claims, checked separately.

- "Is it a denominator artifact?" **No.** `interventions` cancels exactly: `fan_out` is identically
  `1/hold_fraction`. Verified per mission at every span, not on averages. The two must therefore
  never be cited as corroborating each other.
- "It never equals the true sustainable span at any load" is **too strong** and is now removed.
  The implemented statistic books the whole held period as interaction. Reproduced here at the
  collapsed operating point (teleop, blind, n=8, 32 seeds): wait-as-interaction 2.18,
  wait-in-neither (classic) 4.61, wait-as-neglect 6.69 against `n* = 6.45`. The third booking does
  land on the threshold, so the categorical claim dies. What survives is stronger: measured neglect
  is pinned at `tau + 1` (22.01, 22.32, 22.63, 22.41, 22.48, 22.42 across n = 2..12) while all load
  dependence sits in the "interaction" term, which is really the sojourn `W(n)` saturating at `P`.
  So the statistic is `1 + (tau+1)/W(n)` and floors at `1 + (tau+1)/P = 2.15` (measured 2.174,
  2.138, 2.132 at n = 8, 10, 12, converging from above). Past the cliff, `mu` and `c` have vanished
  from the formula: the quantity has stopped being about the operator. No booking predicts the
  cliff in advance.

### Correction 3: `admit` could hold an agent longer than its own patience (CONFIRMED, fixed)

Under `admit` the hold was `2*lat` unconditionally. At C5 (one-way latency 16) that is 32 steps
against a patience of 20, so admission control was worse than not being told, which is incoherent:
the agent would have abandoned unaided first. Now `min(2*lat, patience)`. **No published number
changes**, because every gated cell runs at C0 or C2 where `2*lat` is 0 or 4, and the byte-identity
dump is unaffected (the default policy is `blind`). Fixed anyway, since the paper now recommends
admission control and a latent defect in the recommended path is not acceptable.

### Not confirmed, and therefore not acted on

The review's Q2 finding is that the system is **not** bistable and `n*` is a boundary-equilibrium
collision rather than a saddle-node, because abandonment lengthens cycles and so removes the
positive feedback a fold would need. That is a negative about a hypothesis this ledger raised, and
it is consistent with the earlier CR-13 result that the staggered start was a transient. It is
recorded but not promoted, because nothing in the paper claims bistability.

### Open, and gating now

The review's central claim is that `refund` (free the slot, say nothing) carries most of the
admission-control gain, which would mean the Discussion's recommendation ("tell the requester") is
mis-attributed. Its numbers come from a non-gated probe. `hopper/batteries/refund.sh` is running
the three-way decomposition at full tier at both physics settings. Nothing changes in the paper
until that gates.

## Review finding R1 gated: the decomposition, and where the reviewer was wrong

`st-refund-9442831`, full tier (32 blocks x 64 reps), n=8, both physics settings.

| physics | link | blind | refund | admit | refund share |
| --- | --- | --- | --- | --- | --- |
| published | C0 | 0.5625 | 0.7856 | 0.7998 | 94.0% |
| published | C2 | 0.6768 | 0.7520 | 0.7612 | 89.0% |
| teleop | C0 | 0.0083 | 0.6733 | 0.7534 | 89.3% |
| teleop | C2 | 0.2900 | 0.6416 | 0.6738 | 91.6% |

The reviewer's central claim is CONFIRMED: freeing the slot carries roughly nine tenths of the
admission-control gain, and the manuscript's recommendation was attributed to the wrong half.
`refund - blind` gates everywhere (published C0 +0.2231, t=14.65, 32/32; teleop C0 +0.6650,
t=78.47, 32/32).

**The reviewer's secondary claim is REFUTED.** Its probe reported that refund equals admit even
under teleop physics (0.703 vs 0.695, admit slightly worse), and concluded the notification
"measures approximately zero". At full tier the sign is the other way and the contrast gates:
`admit - refund` is +0.0801 (t=4.97, 25/32) at teleop C0 and +0.0322 (t=2.43, 23/32) at teleop C2,
against +0.0142 (t=1.37, 21/32, NOT gated) and +0.0093 (t=0.77, 16/32, NOT gated) at published
physics. So the notification is worth nothing measurable at the published request rate and a real
gated eight points under teleoperation. This is exactly why a reviewer's number is a conjecture
until it is gated: the probe was directionally wrong on the arm that decides whether a design
recommendation is made at all.

### The mechanism, from R3 (goodput by span, same tier)

| span | blind | refund | admit |
| --- | --- | --- | --- |
| 6 | 0.759 | 0.917 | 0.905 |
| 8 | 0.170 | 0.800 | 0.734 |
| 10 | 0.060 | 0.683 | 0.574 |
| 12 | 0.015 | 0.579 | 0.449 |

`refund` beats `admit` on operator goodput at EVERY span, which looks backwards until the direction
of the favour is read. Freeing the slot helps the operator. Notifying helps the requester, and a
requester returned to autonomy after one round trip instead of after its full patience also asks
again sooner, so `admit` offers the operator strictly more load than `refund`. Notification buys
requester tempo at the price of operator efficiency. That trade pays only when waiting is a large
share of an asset's duty cycle, which is why it gates under teleoperation and not at the published
rate, and it is a sharper statement than either the manuscript's original claim or the review's.

### What changed in the paper

New results paragraph "Which half of admission control does the work", four new rows in
`tab:queue_gate` (freeing the slot alone, and notifying on top of freeing, at both physics
settings), and the Discussion's recommendation rewritten from "a console that tells a requester it
will not be answered in time" to "a console that does not spend service time on requests whose
answers will arrive after the requester has given up", with the notification demoted to a second
increment justified by tasking tempo.

## CR-17 Closed-loop reliance opens a fold band in span-of-control

**Status: mechanism built, closed form derived, gate submitted (`st-hyst-9443432`).**

Every earlier queue result assumed a vehicle's request cycle is independent of whether its last
request was answered. That is what makes the M/D/1+D model have one threshold. Drop it, and the
model becomes bistable.

`retry_prob` (pi) is the fraction of abandoned requests that come back after `retry_backoff` (rho)
steps instead of the standing `decision_interval` (tau). Offered load then depends on the state
the queue is in, and `tools/queue_theory.py:fold_band` gives

    n_c = c*mu*(P + 1 + tau - pi*(tau - rho)) / d          collapsed state sustains itself above
    n_h = c*mu*(P + 1 + tau - a_h*pi*(tau - rho)) / d      healthy state survives below
    n_h - n_c = c*mu*pi*(tau - rho)*(1 - a_h)/d

with `a_h` the healthy-state abandonment fraction. At its floor (`a_h = 1 - d`, link drops only)
the `d` cancels from the width: **jamming moves the band but does not widen it.**

Three consequences, none of them specific to this retry rule:

1. The band is empty exactly when retry does not shorten the cycle, so any reliance loop that
   closes faster after a failure opens one.
2. At the floor it spans a whole vehicle only when `pi*(tau - rho) >= 1/(c*mu)`, one service time
   per console. That inverts into a **backoff floor**, `rho >= tau - 1/(c*mu*pi)`, which is 15.33
   steps at the published operating point: hold a failed requester off that long and the band
   closes. This is a design rule an integrator can actually apply.
3. Under `refund` or `admit` the operator stops spending service time on requests that will
   expire, which is what sustains the collapsed branch, so both slot-freeing policies should
   close the band. Local probe at n=5, pi=1, rho=4: the initial-condition gap is +0.250 under
   `blind`, +0.047 under `admit`, -0.078 under `refund`.

Feeding the measured healthy abandonment in puts the band at (3.75, 5.85) for pi=1, rho=4, so
five vehicles are inside it and six are not. The simulator agrees: at five vehicles a synchronized
start collapses (goodput 0.229) and a staggered start does not (0.836), while at six both collapse
and at three and eight both survive. Staggering also perturbs the RNG stream, so the quantity that
isolates the loop is the difference of differences against the retry-off arm, computed by the new
`tools/ar_contrast.py`. Local, 24 seeds: **+0.391 at five vehicles, 0.000 at three, -0.063 at
eight.**

Note that the published configuration uses the synchronized start. Inside the band, that is the
initial condition that lands on the collapsed branch.

**Also built for this conjecture, and reusable:** a transient jam window (`jam_window`,
`jam_level`) on the Bernoulli channel. It was the first perturbation tried and it pushes the wrong
way, which is itself worth recording: a jam DROPS requests, and a dropped request is one the
operator never has to work, so a transient jam *unloads* the queue rather than tipping it over.

## C1 The ladder's drop rate is not a sufficient statistic for the link

**Status: closed form derived and tested against the live channel; gate running (`st-burst-9443645`,
`st-bspan-9443684`).**

`comms_ew` already carries a Gilbert-Elliot channel calibrated so its stationary drop rate equals
the ladder value at every rung (verified: 0.050 / 0.099 / 0.199 / 0.351 / 0.551 against nominal,
mean loss-run 4.0 against Bernoulli's 1.05 to 2.23). The recorded backlog question was whether the
modality crossover rung moves. It does not: supervisory control does not use the link for decisions
and is flat at 0.771 across the whole ladder, so at six vehicles there is no crossover to move.

The interesting result is a different one. A request-reply handshake needs TWO messages, and
`two_way_delivery` squares the marginal rate because a memoryless channel makes their fates
independent. A bursty channel does not. `c2.step` draws them consecutively, so conditioning on the
first surviving leaves the chain in GOOD and the second is lost only on a fresh transition:

    d = (1 - p)(1 - p_gb),    p_gb = p*p_bg/(1-p),    p_bg = 1/burst_len.

**Correlation helps the handshake.** Measured against the live channel: 0.876 against 0.811 at the
degraded rung, 0.312 against 0.203 at the denied one, closed form matching each to three decimals.
For this model that is bad news, because the operator is the bottleneck and a round trip that
completes is work that arrives. Substituting into `n* = c(P+tau+1)mu/d` moves the cliff LEFT by
3.7% at the nominal rung and 35.2% at the denied one.

Registered prediction: the sign of the burstiness effect must FLIP with span, inside the bracket
between the two thresholds (8.60, 10.08) at rung 3 and (7.37, 7.96) at rung 2. Below the bursty
threshold the extra completed round trips are answers a vehicle wanted; above it they are load the
operator cannot absorb. Local probe is consistent: at rung 2, n=5 GE beats Bernoulli on success
(0.479 against 0.354) and n=6 loses to it (0.521 against 0.667).

**Refuted along the way:** I first explained the burst-times-retry interaction as synchronized
return, vehicles abandoning together during a loss run and coming back together after it. Measured
Fano factor of request arrivals on 10-step bins says otherwise: 0.878 with retry under
Gilbert-Elliot against 0.876 under Bernoulli, and every cell under-dispersed rather than clustered.
Arrivals are not more bursty. The effect is a rate effect through `d`, not a clustering effect.

---

## CR-19: the coherence ratio decides whether burst structure is visible at all

**Registered 2026-08-22, before any full-tier run.**

### What K1 established

`st-clockfull-9444130`, section K1, span 5 through 12 at rung 3, 32 blocks x 64 reps. Against a
Bernoulli channel at the same marginal drop rate:

| span | ge_step - bern | ge_msg - bern |
|---|---|---|
| 5  | -0.0156 (t=-1.04) | +0.0288 (t= 1.85) |
| 6  | +0.0137 (t= 0.92) | +0.0039 (t= 0.27) |
| 7  | +0.0029 (t= 0.17) | -0.0171 (t=-1.09) |
| 8  | +0.0044 (t= 0.34) | **-0.0488 (t=-3.23) GATED** |
| 9  | -0.0078 (t=-0.44) | **-0.0522 (t=-3.82) GATED** |
| 10 | -0.0020 (t=-0.18) | -0.0293 (t=-2.32) |
| 11 | +0.0273 (t= 2.62) | +0.0186 (t= 1.79) |
| 12 | +0.0034 (t= 0.41) | +0.0005 (t= 0.06) |

Under the time-clocked chain the Gilbert-Elliot channel is indistinguishable from a memoryless one
at **every** span. Under the message-clocked chain it is not, and the deviation concentrates at
mid-span, where it costs about five points of mission success. That deviation was an artifact of
the clock, and every burst result this loop produced before CR-18 inherited it.

### The mechanism, and why the null is the interesting half

The chain's second eigenvalue is `lam = 1 - p_gb - p_bg`. With mean bad-state dwell `L` and
marginal drop `p`, `p_bg = 1/L` and `p_gb = p/(L(1-p))`, so

    lam = 1 - 1/(L(1-p))      and      tau_corr = -1/ln(lam) ~ L(1-p).

At the published operating point `L = 4` and `p = 0.20`, so `tau_corr = 2.67` steps against a
decision interval of `tau = 22`. Between two consecutive requests from the same vehicle the chain
mixes `lam^22 = 2.6e-4` of the way from stationarity: it is fully mixed. A channel consulted far
less often than it decorrelates **is** memoryless at the timescale the mission samples it, and no
amount of burst structure in the underlying link can reach the mission metric except through the
scalar delivery probability `d`.

Define the **coherence ratio**

    theta = tau_corr / tau = L(1-p) / tau.

### Registered prediction

**H(CR-19a):** `ge_step - bern` at `n_blue = 8`, rung 3, is null for `theta << 1` and gates for
`theta >= 1`. The crossover sits at `L = tau/(1-p) = 27.5`. Measured coherence ratios for the arms
to be run: `L = 4 -> 0.12`, `14 -> 0.49`, `28 -> 1.00`, `60 -> 2.16`, `120 -> 4.34`. Marginal drop
rate confirmed held at 0.20 +/- 0.01 across all five (400k-step chain probe, 2026-08-22).

**H(CR-19b):** where it gates, the sign is **negative**: burst structure hurts at a fixed marginal
rate. The mechanism is the paper's own. Abandonment is a threshold, not a rate: a vehicle quits
after `P = 20` steps unserved, and clustering is exactly what puts several consecutive failures
inside one patience window. Spread loss lengthens everyone's wait a little; clustered loss pushes a
few vehicles past `P`, and under the published `blind` policy their abandonment is unrefunded.

The competing argument, recorded because it may win: clustering concentrates failure on fewer
vehicles, so more vehicles get a clean run, and if per-mission success is convex in the handshake
count that helps. I am registering negative because the abandonment threshold is the sharper
nonlinearity, but the sign is the part of this prediction I hold least confidently.

**H(CR-19c):** the effect is a `blind`-policy effect. Under `refund` the gated contrast at
`theta >= 1` should fall below the MPE, because refunding removes the unpriced cost of the
abandonment that clustering induces.

### Why this matters beyond the model

`tau` already appears in this paper as the term that sets where congestion collapses,
`n* = c(P + tau + 1)mu / d`. CR-19 makes it appear a second time, as the clock against which
channel memory is measured. The same interval that decides *how many vehicles one operator can
hold* also decides *whether the radio's burst statistics are worth modeling at all*. For a sponsor
choosing between radios, that is a purchasing criterion: burst statistics are irrelevant to mission
outcome unless outage runs last about as long as the operator's decision cycle.

**Falsifier:** if the contrast stays null at `L = 120` (`theta = 4.3`), the coherence ratio is not
the controlling quantity and CR-19 is wrong.

### CR-19 addendum: the closed form, registered 2026-08-22 while job 9444501 was still running

No rows of `st-coherence-9444501` had been read when this was written; `hopper/collect.sh` reported
0 rows. The addendum sharpens the prediction, it does not follow the data.

A vehicle whose handshake fails retries at its next decision, `tau` steps later. For a two-state
chain the probability it is still in the bad state then is `p + (1-p) lam^tau`, so the **excess**
over the marginal rate is

    e(theta) = (1 - p) lam^tau ~ (1 - p) exp(-1/theta).

An exponential in the *inverse* coherence ratio: flat while `theta` is small, then steep. That is
why `theta = 1` is a knee and not an arbitrary cut. Values for the arms submitted:

| L | theta (tau=22) | e | theta (tau=11) | e |
|---|---|---|---|---|
| 4   | 0.12 | 2.0e-4 | 0.24 | 0.013 |
| 14  | 0.49 | 0.104  | 0.98 | 0.30  |
| 28  | 1.00 | 0.294  | 2.00 | 0.49  |
| 60  | 2.16 | 0.500  | 4.33 | 0.63  |
| 120 | 4.34 | 0.635  | 8.68 | 0.71  |

The exact crossover is `L* = 1/[(1-p)(1 - exp(-1/tau))]`, which is 28.1 at `tau = 22` and 14.4 at
`tau = 11`; the first-order reading `tau/(1-p)` is a few percent low and worsens as the clock
speeds up. `tools/queue_theory.py:crossover_burst_len` computes it, with tests.

**H(CR-19d):** the success deficit `bern - ge(L)` is monotone increasing in `e(theta)` and first
gates between `theta = 0.5` and `theta = 1`. L4 is the falsifier in its purest form: `L = 14` sits
at `theta = 0.49` under `tau = 22` and `theta = 0.98` under `tau = 11`, so the SAME radio must land
on opposite sides of the knee when nothing changes but the operator's decision cycle. If `L = 14`
behaves the same under both clocks, `theta` is not the controlling quantity and CR-19 is wrong.

**What the closed form does not claim.** Mean throughput is untouched: the marginal drop rate is
held fixed by construction, so `d` and `n* = c(P+tau+1)mu/d` are unchanged. `e` governs the
DISPERSION of per-vehicle wait. Abandonment is a threshold on that wait, not a rate, which is the
only reason dispersion can reach a mission metric at all. Burst structure enters through the tail.

---

## CR-20: two vehicles on one step are in one radio environment

Found by reading the CR-18 code rather than by a run. Under the step clock the chain advanced by
`max(1, k - last_k)`, so two vehicles transmitting on the SAME step were forced one transition
apart. That is wrong in the direction that matters: simultaneous transmitters share a fade, and
decorrelating them removes the cross-vehicle half of burst structure, which is the half a queue
feels most, since a synchronized outage idles the operator and then floods the console.

Fixed to `max(0, ...)`, at which a zero gap gives `decay = 1` and therefore `p_bad = 1` when the
chain is BAD and `0` when it is GOOD: the second caller inherits the first caller's outcome
deterministically while still consuming its own uniform, so the draw budget is unchanged. Byte
identity verified by value across 4 scenarios x 8 seeds x 29 metrics; three tests added.

**Expected magnitude: small, and smallest where CR-19 predicts an effect.** Measured on the live
model at rung 3, `ge_burst_len = 4`: a same-step gap occurs on 8.8% of uplink draws at five
vehicles, 10.3% at eight and 14.6% at twelve, with mean gaps of 12.2, 7.6 and 4.3 steps against a
2.67-step coherence time. The floor changed the correlation of that ~10% from `lam` to 1, and
`lam -> 1` as the burst lengthens, so at the long dwells where CR-19 expects a gated effect the
floor was already nearly inert. This is recorded as a correctness fix with a registered
expectation of **no gated effect**, and it is tested as a spare arm on the next battery rather
than given a battery of its own.

**It does not disturb CR-19.** The closed form `e(theta) = (1-p)exp(-1/theta)` describes a vehicle
retrying `tau` steps later, a gap of 22, where the floor never applied. Job 9444501 therefore
tests CR-19 correctly under the floored code, and CR-20 is a separate cross-vehicle mechanism the
closed form does not cover.

### CR-19 correction: the lag is the failure cycle, not the decision interval

**Written 2026-08-22 while 9444501 was still running; `hopper/collect.sh` had not yet produced a
local copy of the log, so no row of it had been read.** This corrects the registration in the
direction that makes it harder to satisfy, and it was found by reading `c2.py`, not by looking at
output.

The first registration used `lag = tau = 22`, on the reasoning that a vehicle retries at its next
decision. That is wrong about this model. Reading the request path: a vehicle whose link fails gets
`await_until = k + patience` and only then serves its cooldown, so the interval between one
unanswered request and the same vehicle's next one is

    C = P + tau + 1 = 43 steps,

not 22. And `C` is not a new symbol. It is exactly the numerator of the paper's own collapse span,
`n* = c mu (P + tau + 1) / d = c mu C / d`, and the fold band of CR-17 is the gap between the
cycle in the collapsed state and the cycle in the healthy one. **The quantity that governs the
queue also governs the channel.**

That is a stronger claim than the one it replaces. "`tau` appears in four formulas" invites the
answer that `tau` is the only timescale in the model, so of course it does. "The failed-request
cycle `C` sets the collapse span, the width of the bistable region, the backoff floor, and the
dwell at which a link's burst structure becomes visible" survives that objection, because `C` is a
derived and physically meaningful quantity, how long a vehicle is out of contact after an
unanswered request, and each appearance is a different functional role.

**Two knees, not one.** The chain has two readers consulting it at two very different intervals:

| reader | lag | L* at p = 0.20 |
|---|---|---|
| a vehicle, blind, no retry | `C = P + tau + 1` = 43 | **54.4** |
| a vehicle, CR-17 retry at `rho = 4` | `P + rho + 1` = 25 | 31.9 |
| a vehicle, `tau = 11` | `P + 12` = 32 | 40.6 |
| the console, eight vehicles | measured mean gap 7.56 | **10.1** |
| the console, five vehicles | measured mean gap 12.17 | 15.8 |
| the console, twelve vehicles | measured mean gap 4.32 | 6.0 |

The console knee sits at a far shorter dwell than the vehicle knee, so **as a link's outages
lengthen the cross-vehicle effect must appear first**. Excesses for the arms submitted:

| L | theta_v (lag 43) | e_v | theta_o (lag 7.56) | e_o |
|---|---|---|---|---|
| 4   | 0.062 | 0.0000 | 0.35  | 0.047 |
| 14  | 0.249 | 0.0143 | 1.41  | 0.395 |
| 28  | 0.509 | 0.1123 | 2.90  | 0.566 |
| 60  | 1.105 | 0.3235 | 6.28  | 0.682 |
| 120 | 2.221 | 0.5100 | 12.63 | 0.739 |

**Amended predictions.**

**H(CR-19a'):** L1 gates somewhere in `L >= 14`, and the first gated arm is driven by the console
knee (10.1), not the vehicle knee (54.4). Under the old registration the first gated arm was
predicted at `L = 28`; under the correction it should be `L = 14`.

**H(CR-19d'):** the two knees separate the metrics. Console synchrony bunches arrivals, so it
should show first in `abandon_queue_frac` (L2). Within-vehicle persistence keeps one vehicle
degraded across cycles, so it should show in mission success only once `L >= 60`.

**H(CR-19e), new, and the sharpest thing in this correction:** a CR-17 retry at `rho = 4` cuts the
failure cycle from 43 to 25 and the within-vehicle knee from 54.4 to 31.9, so **a team that closes
its reliance loop faster is more exposed to the link's burst structure, not less.** The mechanism
that opens a fold band and the mechanism that makes channel memory visible are the same shortened
cycle. This is a prediction the running job does not test and a battery is owed.

**What the correction costs me.** The L4 falsifier is weaker than registered. I predicted `L = 14`
would flip sides of the knee when `tau` halved, on the strength of `theta = tau_corr/tau`. Under
the correct lag `tau` halving takes `C` from 43 to 32, only a 26% change, because the patience
window dominates the cycle and dilutes the `tau` dependence: `L*` moves 54.4 to 40.6 and `L = 14`
stays sub-critical under both clocks. L4 is therefore a weak test of the vehicle knee. It remains a
real test of the console knee, whose lag scales with `tau` directly, and the honest reading is that
the registered falsifier was mis-specified and the run will not settle what I said it would.

### CR-19e registered in full, and the interior maximum that falsifies it

Submitted as `st-retryburst-9444791` (n_blue = 5, rung 3, 32 blocks x 64 reps, three metrics).
Four arms crossed with `ge_burst_len` in {4, 40, 120}: `bern_off`, `bern_retry`, `ge_off`,
`ge_retry`, gated as the difference of differences

    [ge_retry - bern_retry] - [ge_off - bern_off],

so that the Bernoulli pair absorbs the retry's own effect on offered load and what remains is the
retry's effect on EXPOSURE TO BURST STRUCTURE.

`L = 40` is the straddle: `theta_v` is 0.73 with the standing cycle of 43 steps and 1.26 with the
retry's cycle of 25, so the retry alone carries the arm across the knee while nothing else about
the link changes. The predicted DiD in the excess `e_v = (1-p)exp(-1/theta_v)` is

| L | e_v(off) | e_v(retry) | difference |
|---|---|---|---|
| 4   | 7e-6  | 9e-5  | 1e-4  |
| 40  | 0.203 | 0.362 | **0.159** |
| 120 | 0.510 | 0.620 | 0.111 |

**an interior maximum near the straddle**, because at `L = 120` both cycles are already deep above
the knee and the exponential has flattened. That non-monotonicity is the falsifier and it is the
reason the arms are spaced this way: a DiD that rises monotonically in `L` refutes the mechanism as
stated even if every cell gates, because monotone-in-`L` is what "longer outages are simply worse"
predicts and it needs no coherence argument at all.

Three metrics, chosen to separate the two knees the correction identified. `success` is the
headline. `wait_p95` is a tail statistic and the theory says burst structure enters through the
tail rather than the mean, so it should move first and by more. `queue_depth_mean` reads the
console rather than the vehicle, and the cross-vehicle knee at this span sits at `L = 15.8`, so
every arm at `L = 40` and above is already past it and the DiD there should be WEAKER than in
`wait_p95`, since the retry changes the vehicle's cycle and not the console's aggregate gap.

### CR-19 second correction: the burst sweep was not holding the round trip fixed

Fable found this and I confirmed it before acting. It invalidates L1 of `st-coherence-9444790` as a
structure measurement, and the fix is a control arm rather than a code change, because the thing
that produced it is correct physics.

`reply_survives` under the step clock returns `1 - p(1 - lam^lag)`, which is the probability the
chain is still GOOD `lag` steps after the uplink found it good. Multiplied by the uplink's `1-p`,
the round-trip delivery is

    d(L) = (1-p) [1 - p(1 - lam^lag)],

which runs from `(1-p)^2` at a memoryless channel up toward `(1-p)` as the dwell lengthens. That is
right: **a coherent channel favours round trips.** If the request got through, the channel was
good, and a channel with memory is likely still good when the answer comes back. Measured on the
live channel at the shortest realizable reply lag (`1/mu = 6.67`, an empty queue):

| L | d measured | n* = c mu Lambda / d | n_blue = 8 as a fraction of n* |
|---|---|---|---|
| Bernoulli | 0.640 | 10.08 | 0.79 |
| 4   | 0.655 | 9.88 | 0.81 |
| 14  | 0.728 | 8.89 | 0.90 |
| 28  | 0.760 | 8.51 | 0.94 |
| 60  | 0.782 | 8.28 | 0.97 |
| 120 | 0.790 | 8.17 | 0.98 |

So the sweep walks the operating point from 0.81 to 0.98 of the collapse span **on the first
moment**. Any effect L1 finds is attributable to that walk at least as readily as to dispersion,
and my registered claim that "`d` and `n*` do not move" was simply false. It was false in my own
docstring, which stated the bound `(1-p)^2 <= d <= (1-p)` and which I had written myself.

**The control.** `reply_model="marginal"` draws the reply against the marginal rate whatever the
lag, pinning `d` at `(1-p)^2 = 0.640` for every dwell (verified to 0.001 over 200k handshakes at
six dwells). It is an experimental control and not a physical claim, in the same way a placebo arm
is not a claim about medicine. Byte identity verified; two tests added. Resubmitted as
`st-coherence2-9445040` with the decomposition

    mg - bern  = structure at fixed round-trip delivery
    co - mg    = the round-trip correlation bonus
    co - bern  = the old confounded contrast, kept so the two halves add up.

**Amended sign.** With `d` held fixed the round-trip bonus is gone, and the bonus was working in
the OPPOSITE direction to my registered negative: a longer dwell delivered more round trips, which
helps. So `co - bern` mixes a helping first-moment term with whatever the structure does. I keep
the registered negative for `mg - bern` and now expect `co - mg` positive, with `co - bern`
ambiguous in sign, which is a better-specified registration than the one it replaces.

### Q4 settled: the message clock does not deliver the dwell the scenario asks for

The retraction defense needed something better than "the new convention is nicer". Measured on the
live model at rung 3 with `ge_burst_len = 4`, that is, a channel the scenario asks to fade for four
steps:

| clock | span | mean inter-message gap | realized outage, steps | realized outage, messages |
|---|---|---|---|---|
| message | 4  | 7.58 | **25.12** | 4.10 |
| message | 8  | 3.78 | **12.33** | 3.93 |
| message | 12 | 2.11 | **7.44**  | 3.98 |
| step | 4  | 15.04 | 6.39 | 1.46 |
| step | 8  | 7.55  | 4.67 | 1.78 |
| step | 12 | 4.25  | 3.60 | 2.00 |

Under the message clock the outage lasts four MESSAGES at every load, so its duration in steps is
the inter-message gap times four: the same radio fades for 25 steps at four vehicles and 7 at
twelve. A fade whose duration shrinks threefold because eight vehicles were added is not a property
of a radio. Under the step clock the realized dwell is 3.6 to 6.4 steps against the requested 4,
and the residual is a known sampling bias: an outage is only observable when it spans two messages,
so short outages are invisible at sparse message density and the estimate is biased up, which is
exactly the direction and the ordering seen.

This is not a choice between two conventions. One of them returns the number the scenario file
asked for and the other misses it by a factor of six at low span. A companion measurement, the
probability that two adjacent messages agree as a function of their separation in STEPS, says the
same thing: under the message clock it is 0.90 at every separation from 0 to 40 steps, a channel
with unbounded coherence time; under the step clock it decays 1.00, 0.87, 0.77, 0.69 to the chance
level 0.694 by about ten steps, which is a fade. Both are load-invariant, so the sharper statement
is the dwell, not the autocorrelation. Captured as a unit test.

---

## CR-21: the retry does two things, and only one of them was named

### The result that forced this

`st-clockfull-9444130` section J1, `operator_goodput`, five vehicles, 32 blocks x 64 reps. The
difference of differences `[ge_retry - bern_retry] - [ge_off - bern_off]`:

| rung | DiD | t | sign |
|---|---|---|---|
| 1 | -0.0617 | -7.59 | 88% negative |
| 2 | -0.0509 | -7.41 | 91% |
| 3 | -0.0356 | -13.21 | 100% |

All three gate. The component contrasts say the retry is the whole story: `ge_off - bern_off` is
+0.0008, -0.0037, -0.0079, none of which reaches the MPE, while `ge_retry - bern_retry` is -0.0609,
-0.0546, -0.0436, all gated. **A bursty link costs a reliant team six points of operator goodput
and costs a non-reliant team nothing.** J2 says it does not reach mission success (-0.027, -0.028,
-0.012, t at most 1.57), so this is a queue-level effect that the mission absorbs.

### Why the CR-19 closed form does not explain it

At the published dwell of four steps the within-vehicle excess is `e_v = 9e-5` with the retry and
`7e-6` without. Six points of goodput cannot come from that. The round-trip bonus works the wrong
way: it RAISES delivery under a coherent channel, so it would push the contrast positive. There is
a third mechanism.

### The candidate, and why it was invisible

A retry does two things at once and the published parameterization cannot separate them. It
shortens the cycle from `P + tau + 1 = 43` to `P + rho + 1 = 25`, which is what opens the fold
band. And it computes the backoff by RESCALING the standing jittered interval, `cool * rho / tau`,
which shrinks the absolute jitter by the same factor: the standing cycle draws from a 22-step
window and the rescaled backoff from a 4-step one. A common-mode outage drops several vehicles at
once. With the standing cycle they disperse over the next 22 steps; with the rescaled backoff they
return inside 4 and hit one console as a block.

The comment on that line claimed the opposite, that "the jitter keeps retrying vehicles from
re-synchronizing into a second burst". It does not. Rescaling a jitter is not preserving it.

`retry_spread` separates them: the backoff becomes `rho + s*u` with `u` the same drawn integer
mapped onto [-1, 1], so the MEAN is held at `rho` while the width is set independently. Verified to
machine precision at every width used, and `s = 2` at `rho = 4` reproduces the shipped rescale
exactly, range [2, 6], so the control nests the published behaviour rather than replacing it. One
draw either way; byte identity holds; three tests.

### Registered, as `st-cohort-9445208`

**H(CR-21a):** `|DiD|` falls monotonically as `s` widens, and is largest at `s = 0`, where every
retrying vehicle returns after exactly `rho` steps. Flat in `s` refutes the cohort and means I am
still missing a mechanism.

**H(CR-21b):** with round-trip delivery pinned by `reply_model="marginal"`, the contrast gets MORE
negative, not less, because the bonus it removes was working against the measured sign. If instead
the contrast vanishes, J1 was a first-moment effect all along and the cohort story is unnecessary.

**Standing caveat.** J1 ran before CR-20. Re-running its four arms under the current code moves
`ge_retry` down by about 0.023 on the first four blocks while `bern_retry` reproduces to six
decimals, so making same-step transmitters share a fade STRENGTHENS the interaction. My CR-20
registration of "no gated effect" looks wrong, and wrong in the direction Fable predicted when it
said the floor's real payload was the cohort channel. Every arm in the new batteries carries the
fix, so the comparison is within-log.

---

## CR-19e REFUTED, and CR-19's core claim survives in half the size I thought

### The refutation, on the falsifier I registered

`st-retryburst-9444791`, n = 5, rung 3, 32 blocks x 64 reps. DiD
`[ge_retry - bern_retry] - [ge_off - bern_off]` on mission success:

| L | predicted from e(theta_v) | measured | t |
|---|---|---|---|
| 4   | -0.000 | -0.0112 | -0.60 |
| 40  | **-0.159** | -0.1206 | -6.86 GATED |
| 120 | -0.111 | **-0.1655** | -7.58 GATED |

I registered an INTERIOR MAXIMUM at the straddle and wrote that "a DiD rising monotonically in L
refutes the mechanism as stated even if every cell gates". It rises monotonically. The
coherence-excess functional form is the wrong description of this contrast, and I am recording that
rather than reaching for the reading in which two of three cells agree.

What survives is not nothing. The effect is real and it is the largest in the project:
`ge_retry - bern_retry` is -0.0996 and -0.1611 at L = 40 and 120, both gated at |t| near 7 and 12,
while `ge_off - bern_off` is +0.0210 and +0.0044, neither gated. **A team that closes a reliance
loop loses sixteen points of mission success to a long-dwell link; a team that does not loses
nothing.** On the tail statistic it is larger still and gates even at the published dwell:
`wait_p95` moves -0.07, -1.04, -2.44 steps with |t| of 2.1, 24 and 42.

And the first-moment explanation does not reach here. At five vehicles the team is far below
`n* = 10.08`, so the `d` walk has no cliff to walk toward, and `ge_off - bern_off` confirms it by
being null at every dwell. **At this span the effect must be structural.**

### CR-19 core claim, decomposed and confirmed at half the size

`st-coherence2-9445040` section N-success, n = 8, rung 3. The `co - bern` column reproduces
`st-coherence-9444790` L1 to four decimals at all five dwells, which is a cross-job check on the
block pairing passing exactly.

| L | theta_v | structure (mg - bern) | round-trip bonus (co - mg) | total (co - bern) |
|---|---|---|---|---|
| 4   | 0.06 | -0.0024 | -0.0171 | -0.0195 |
| 14  | 0.25 | -0.0156 | +0.0103 | -0.0054 |
| 28  | 0.51 | -0.0283 | +0.0024 | -0.0259 |
| 60  | 1.11 | -0.0225 | **-0.0322** | **-0.0547** |
| 120 | 2.22 | **-0.0391** | **-0.0352** | **-0.0742** |

The decomposition is additive to the fourth decimal. Both halves are negative and roughly equal at
the longest dwell, so the confound did not eat the effect, it DOUBLED it.

**I had the bonus's sign backwards.** I predicted `co - mg` positive because a coherent channel
delivers more round trips. It is negative, and the paper already explains why: `n* = c mu Lambda/d`
falls as `d` rises, so at a span near the cliff more delivery is more offered load. This is the
manuscript's own sentence, "jamming raises the threshold, because a dropped request is one the
operator never has to work", read in the other direction. I should have seen it.

**H(CR-19b) confirmed for the structure half.** With `d` pinned, structure alone is -0.002 at
`theta_v = 0.06` and -0.039 gated at `theta_v = 2.22`, negative as registered and monotone in
`theta_v` apart from the L = 60 cell. The observable knee sits above the theoretical `theta_v = 1`:
L = 60 gives -0.023, below the MPE. So the closed form gets the direction and the ordering and is
optimistic about where the effect becomes measurable.

### The picture the four batteries make together

| condition | burst effect on mission success |
|---|---|
| structure alone, no reliance, away from the cliff | null at every span 5 to 12 (K1) |
| plus a blind operator near the cliff | -0.039 structure, -0.035 first moment, gated |
| plus a reliance loop, far below the cliff | **-0.166**, gated at |t| = 11.7 |
| plus admission control (refund) | **+0.008**, null |

A link's burst statistics are invisible to a team that neither relies on its operator nor lets that
operator spend slots it cannot use. They become the largest effect in this model the moment a
reliance loop closes, and they vanish again under refund. That is a claim about WHEN comms fidelity
has to be modeled, and it is falsifiable in three places at once.

---

## CR-22: the interaction is multiplicative in the collapse formula

### How I got here, including the wrong turn

I refuted CR-19e on its registered falsifier, then wrote that the effect at five vehicles "must be
structural" because the team is far below `n* = 10.08` and there is no cliff to walk toward. That
was wrong, and it was wrong in a way the paper's own equation catches immediately.

    n_c = c mu (P + rho + 1) / d.

A retry cuts the NUMERATOR from 43 to 25. A long-dwell coherent channel raises the DENOMINATOR
from 0.640 to about 0.780. **The retry moves the cliff down to meet the team.** At rung 3:

| arm | cycle | d | n_c | five vehicles collapsed? |
|---|---|---|---|---|
| bern, no retry | 43 | 0.640 | 10.08 | no |
| ge120, no retry | 43 | 0.780 | 8.27 | no |
| bern, retry rho=4 | 25 | 0.640 | 5.86 | no |
| ge120, retry rho=4 | 25 | 0.780 | **4.81** | **YES** |

Five vehicles is the one cell where the two factors together carry the team across its own collapse
span and neither does alone. That is exactly the pattern measured: `ge_off - bern_off` is null at
every dwell, `ge_retry - bern_retry` is -0.1611, and `operator_goodput` falls from 0.495 under
`bern_retry` to 0.148 under `ge_retry` while link abandonment goes DOWN, from 0.347 to 0.236,
because the bursty channel delivers MORE round trips. More delivery is more offered load. The team
drowns in its own answered requests.

### Registered as `st-crossing-9445405`

**H(CR-22a):** the DiD has an **interior maximum in SPAN** at five vehicles. Null at three and four,
where both retry arms are healthy; maximal at five, where only the bursty one has crossed; decaying
to null by seven or eight, where both are collapsed. **A DiD that grows monotonically in span
refutes it.**

**H(CR-22b):** with `reply_model="marginal"` pinning `d` at 0.640, both retry arms sit at
`n_c = 5.86` and there is no state difference to find, so the DiD must vanish at every span in
R3 and R4. **A DiD that survives there refutes the account and means structure is left over.**

This is the third mechanism proposed for one contrast. The first, the coherence excess, was refuted
on its own falsifier. The second, the retry cohort, is still running as `st-cohort-9445208` and is
now the ALTERNATIVE rather than the leading candidate; if CR-22 holds, the cohort battery should
come back flat in the backoff jitter. Both are registered before either result was read.

### Why this one is worth more than the two it replaces

It needs no new machinery. The interaction is a product of two terms the manuscript already derives
and already reports, one in the numerator and one in the denominator of an equation that is already
in the paper. And it converts the finding from "bursty links hurt reliant teams" into something a
program can compute: **take your collapse span, divide by the round-trip delivery your radio
actually achieves rather than its nominal drop rate, and check whether your reliance loop has moved
it below your staffing.** The two design levers, backoff length and admission control, are the two
terms of the same fraction.

---

## CR-22 CONFIRMED, and it yields a sign flip rather than a penalty

`st-crossing-9445405` section R1, mission success, rung 3, 32 blocks x 64 reps.

| n | ge_retry - bern_retry | ge_off - bern_off |
|---|---|---|
| 3  | +0.0103 | +0.0327 (t=2.39) |
| 4  | +0.0103 | **+0.0371 GATED** |
| 5  | **-0.1611 GATED** (t=-11.68, 32/32) | +0.0044 |
| 6  | **-0.1343 GATED** (t=-9.24) | +0.0039 |
| 7  | **-0.0327 GATED** | **-0.0654 GATED** |
| 8  | +0.0098 | **-0.0742 GATED** |
| 10 | +0.0020 | -0.0283 |

**The registered shape holds.** I registered "an interior maximum in span at five, null at three and
four, decaying to null by seven or eight, refuted by monotone growth in span." The retry arm is
+0.010, +0.010, -0.161, -0.134, -0.033, +0.010, +0.002. That is the interior maximum, at the span
the closed form named before the run.

**And the result is better than the one I registered.** Both arms show a SIGN FLIP, not a penalty.
A bursty link **helps** a team below its collapse span and **hurts** one above it, because the only
thing burst structure does to the first moment is raise round-trip delivery, and delivery is a
benefit when the console has slack and a cost when it does not. This is the manuscript's own
sentence about jamming raising the threshold, run in reverse and measured across a span sweep.

The two arms cross at different spans, and the offset is the whole mechanism:

    n_c = c mu (P + rho + 1) / d,     bern 5.86 against ge 4.81 with a retry,
                                      bern 10.08 against ge 8.27 without one.

The measured crossings are between 4 and 5 with the retry and between 6 and 7 without it. The
retry's arithmetic is close (4.81 to 5.86 predicted, 4 to 5 measured, and the self-consistent
`d` puts it at 5.07); the no-retry arm crosses about two vehicles earlier than 8.27 predicts, which
is the approximation in the queueing delay showing itself and is the honest size of the error.

**What it is worth saying to a sponsor.** Not "bursty links are bad". Rather: a link whose outages
are long relative to your handshake **raises** the fraction of requests that complete, and whether
that helps or hurts depends entirely on which side of your own collapse span you are staffed. And
closing a reliance loop moves that crossover **down by about three vehicles**, so the same radio
that was an asset at six vehicles becomes a liability at five once the crew starts re-asking.

### What this cost, recorded

Three mechanisms were proposed for one contrast. Two were refuted on their own registered
falsifiers, the coherence excess by a monotone rise where it predicted an interior maximum in
DWELL, and the retry cohort by a flat dose response where it predicted a decline. The third was
registered before its run and confirmed on the shape it predicted in a variable never swept before.
The two refutations are the reason to believe the third: it was not the first story that fit.

## CR-23: two floors, and only one of them moves with the team

*Registered 2026-08-22, before the run. Prompted by Fable's F5, which caught the paper conflating
two thresholds that happen to be near each other in the published cell and are near nothing like
each other anywhere else.*

The retry lever has two floors and the manuscript has been quoting the wrong one as a
recommendation.

**(a) The band-closing floor.** The CR-17 fold band has width `c mu pi (tau - rho)(1 - a_h)/d`, so
it shuts at `rho >= tau - 1/(c mu pi)` = 15.33 steps. This number contains no `n`. It is a property
of the lever.

**(b) The jam floor.** A retry shortens the failure cycle from `P + tau + 1` to `P + rho + 1` and so
drags the collapse span down to `n_c = c mu (P + rho + 1)/d`. A team of `n` is jammed by its own
retry exactly when `n > n_c`, that is when

    rho < rho*(n, d) = n d / (c mu) - (P + 1).

This one contains both `n` and `d`. It is a property of the team on its channel.

At `P = 20`, `c = 1`, `mu = 0.15` the two accounts are cleanly separable, because (a) is one number
for the whole model and (b) is a different number in every cell:

| n | rho* at d = 0.780 (GE-120) | rho* at d = 0.640 (Bernoulli) |
|---|---|---|
| 4 | -0.2, never jammed | -3.9, never jammed |
| 5 | 5.0 | 0.3, never jammed |
| 6 | 10.2 | 4.6 |
| 8 | 20.6 | 13.1 |

**Registered predictions.** Sweeping `rho` in {2,4,6,8,10,12,16,20} against a no-retry baseline at
each span, on both channels:

1. the damage **knees** rather than sliding: at n = 5 on GE-120 it is large for rho <= 4 and gone
   by rho = 8;
2. the knee **walks right with span**: absent at n = 4, near 5 at n = 5, near 10 at n = 6, near 20
   at n = 8;
3. the knee **shifts with the channel**: the Bernoulli ladder sits one span later throughout,
   because a worse channel is a smaller `d` and a smaller `d` is a larger `n_c`.

**Falsifier**, any one of which retracts the load rule and hands the credit to the band-closing
floor or to something not yet named: (i) the knee sits at the same rho for n = 5, 6 and 8;
(ii) the decline is gradual, with the damage at rho = 8 still more than half the damage at rho = 2
at n = 5; (iii) the damage at n = 4 is gated at any rho.

Prediction 2 is the one that cannot be had by accident, and it is the reason to run this rather
than argue it. The band-closing floor is a single number. If the measured floor moves with the
span, then the number was never the recommendation and the rule is.

Battery `backoff.sh`, full tier, 32 blocks at 64 reps, paired by block.

## CR-24: the rule instead of the number

*Registered 2026-08-22, before the run. This is Fable's F5 recommendation taken literally: "it
finds the floor without knowing n, d, mu, or c, pays no latency when the system is healthy, and is
the form real systems field."*

A console cannot use `rho*(n, d)`. It does not know `n` at design time, it certainly does not know
`d`, and both move during a mission. The fielded form of this fix is the one Ethernet and TCP have
used for forty years: double the hold on consecutive unanswered requests, reset it the moment a
request is served. The schedule, base `rho = 4`, capped at the standing interval `tau = 22`:

    streak  0  1  2  3  4+
    hold    4  4  8 16 22

which clears rho* = 5 on the second unanswered request, rho* = 10 on the third and rho* = 20 on the
fourth. That is exactly the ladder CR-23 predicts for n = 5, 6 and 8, reached from below without
measuring anything.

**Registered predictions**, as a dominance claim, which is the only kind worth shipping:

1. at every span and on both channels the adaptive arm is at least as good as the **better** of
   fixed rho = 4 and fixed rho = 20, to within the gate;
2. it arrives there from opposite directions: it beats fixed-4 where the team is jammed (n >= 6)
   and matches fixed-4, not fixed-20, where the team is healthy (n = 4, and the whole of rung 0);
3. at rung 0 it is indistinguishable from fixed-4, because a served vehicle never accumulates a
   streak.

**Falsifier**: the adaptive arm is gated-worse than `max(fixed-4, fixed-20)` at any cell; or it
fails to separate from fixed-20 in the healthy cells, which would mean it is a slow retry wearing a
costume and the sponsor should be given the number after all.

Battery `adaptive.sh`, full tier, 32 blocks at 64 reps, paired by block.

## CR-22 RETRACTED on its registered falsifier, and the shape it predicted survives

*`st-crossing-9445405`, full tier, 32 blocks at 64 reps, sections R3 and R4, read 2026-08-22.*

CR-22 registered two things and they came apart. The SHAPE prediction, an interior maximum in span,
is confirmed and is sharper at full span resolution than the earlier reading. On operator goodput,
`(ge_retry - bern_retry) - (ge_off - bern_off)`:

| n | 3 | 4 | 5 | 6 | 7 | 8 | 10 |
|---|---|---|---|---|---|---|---|
| DiD | -0.031 | -0.065 | **-0.405** | -0.160 | **+0.144** | **+0.191** | +0.117 |
| t | -6.2 | -12.7 | -99.9 | -38.4 | +38.5 | +59.0 | +37.6 |

Every cell gated, a sharp minimum at five, and a clean sign flip between six and seven. On mission
success the same profile appears at the cells the gate accepts: -0.166 at five, -0.138 at six,
+0.084 at eight.

The MECHANISM prediction is refuted, on the falsifier I wrote for it. I registered that pinning the
reply leg with `reply_model=marginal` puts both retry arms at the same `n_c = 5.86`, leaves no state
difference to find, and therefore must dissolve the interaction; and that a DiD surviving there
refutes the account. It survives, and not marginally:

| n | 4 | 5 | 6 |
|---|---|---|---|
| pinned DiD, goodput | -0.028 (not gated) | **-0.174**, t=-36.1 | **-0.132**, t=-31.3 |
| pinned DiD, success | -0.033, t=-2.10 | -0.056, t=-2.43 | -0.110, t=-4.58 |

**So the account is retracted.** What is left is a measurement rather than a mechanism, and it is
worth stating exactly because it is the useful part. At five vehicles the full interaction is
-0.405. Pinning the reply leg leaves -0.174. The reply-leg coherence, which is the `d` shift and
the whole of the CR-22 story, therefore carries a little over half of it, and forward-path burst
structure carries the rest. Both legs hurt and neither is sufficient. The arms in order at n = 5:
`bern_retry` 0.493, `mg_retry` 0.309 (forward burst only), `ge_retry` 0.155 (both).

**Three mechanisms have now been proposed for this one contrast and all three are refuted**:
CR-19e's coherence excess on a monotone rise where it predicted an interior maximum in dwell,
CR-21's retry cohort on a flat dose response where it predicted a decline, and now CR-22's
collapse-formula account on the d-pinned control. The regularity is robust, large, gated at
|t| up to 100, and reproduces across two metrics and two batteries. It is not explained.

**One instrument was broken and that is worth recording separately.** The Fano-factor probe run to
characterize the arrival process used counting windows of 1, 2, 4 and 10 steps against a requested
dwell of 120 steps, so it could not have detected correlation at the scale the dwell imposes; the
windows all sit inside a single channel state. Whatever it reported about burstiness at the console
is uninformative about the regime in question. Repairing it is a measurement, not a fourth
conjecture, and it is queued as such.


## CR-23 v1 CANCELLED UNRUN, and the reason is worth more than the run

*2026-08-22, on Fable's catch, before any row was read.*

`retry_backoff` does not set a fixed hold by default. `retry_spread` defaults to -1, which rescales
the standing cooldown draw, so the actual hold is uniform on roughly `[rho/2, 3rho/2]`. Verified by
value at tau = 22:

    rho = 20, default:  holds 10..30      rho = 20, retry_spread=0:  holds 20
    rho =  6, default:  holds  3..9       rho =  6, retry_spread=0:  holds  6

The rho = 20 and rho = 12 arms therefore overlap on almost their whole support, and any knee in rho
is smeared into a slide before the physics is consulted. Falsifier (ii), "the decline is gradual",
would have fired whatever the mechanism, and I would have retracted a correct prediction on an
instrument artifact. This is the second broken instrument found today, after the Fano window, and
both were found by asking what the measurement could have shown rather than what it did show.

v2 sets `retry_spread=0` on every arm, extends the ladder to rho in {2,4,6,8,10,12,14,16,18,21} so
the predicted knees at 5, 10 and 21 are each bracketed, and adds a discriminator.

**The discriminator, registered.** Two readings of `d` disagree about one cell and agree everywhere
else. If `d` is the STATIONARY round-trip delivery, `rho*(8, 0.780) = 20.6` sits just under the cap
of `tau = 22`, so the n = 8 damage must die by rho = 21. If the relevant `d` is instead CONDITIONAL
on the forward path having got through, it is larger, `rho*` exceeds the cap, and n = 8 on GE-120
cannot recover at any settable backoff while Bernoulli still recovers at 13.1. Binary, and immune
to the jitter confound that killed v1.

Also on Fable's reading, the n = 4 GE cell is demoted: `rho* = -0.2` there is inside the noise of
the `d` estimate, so neither a null nor a small effect discriminates. The n = 4 BERNOULLI cell
(`rho* = -3.9`) remains a refuter.

Job `st-backoff-9445984`.

## CR-25: the sign reversal, attributed, or else given away

*Registered 2026-08-22, before the run, on Fable's objection to CR-A1's verdict. Job
`st-attrib-9445987`.*

The measurement is not in doubt: sweeping span with the defenders fixed at four raises mission
success +0.555 from three to fifteen, sweeping the same span with the force ratio held at 1.5
lowers it -0.676, and the DiD is +1.231 at t = +75.9 with 32/32 sign agreement. What is in doubt is
what it is a result ABOUT. I wanted to call it a span-of-control result. Three channels are live
and I had attributed the whole of it to one.

1. **Console congestion.** Operator goodput falls 0.759 to 0.160 over exactly the steepest step.
2. **Force geometry.** Holding the ratio scales `n_red`, which deepens the defending column on one
   lane rather than widening the engagement. That is a scenario fact, not a teaming one.
3. **Threshold concentration.** `success` is the one bit `arrived >= 0.5 n_blue`. At a fixed
   per-vehicle arrival probability the binomial gets *sharper* as `n` grows, so a step in success
   can be a step in the fraction or a step across the cut, and the published metric cannot tell
   them apart. This is why `arrived_frac` was added to the metric set today, verified byte-identical
   on the 29 pre-existing metrics.

Supervisory control has no console at all, so it bounds channels 2 and 3 together; `refund` keeps
the console but stops it spending slots on requesters who have gone.

**Registered.** (a) supervisory at held ratio falls by less than half the direct arm's -0.440 step,
falsifier being a fall over 0.30; (b) refund recovers at least half the direct step at n = 9,
falsifier being under 0.10; (c) `arrived_frac` on the direct held-ratio arm falls monotonically,
falsifier being flat or rising while success falls, which would make the headline a threshold
artifact and would have to be said in those words.

Predictions (a) and (c) can each independently take the result away. That is why they are here.

## CR-26: the signal nothing consumed

*Registered 2026-08-22, before the run, on Fable's Q3 answer. Battery `aimd.sh`.*

The manuscript reports that admission control has two halves and that they are unequal: discarding
work the operator cannot finish carries most of the gain, and telling the requester adds a smaller
increment that survives the gate only where a waiting asset is a stopped one. I had recorded that
as a fact about admission control. Fable's reading is a criticism of the model instead, and it is
right: **a refusal is a congestion signal in the sense of Floyd and Fall, and nothing in the model
consumes it.** The refused vehicle goes autonomous sooner and then returns on exactly the same
standing cadence, so the signal changes one wait and never once changes the offered load. In TCP
the signal changes the sender's rate. That is the real disanalogy, and it is fixable rather than
fundamental.

`admit_response="aimd"` makes the vehicle consume it the way a sender does: halve its own request
rate on a refusal, add back an eighth on each answered request, floored at a quarter of the
standing rate so the cadence stretches at most fourfold. Off by default, rejected unless
`queue_policy` is `admit` because the other policies emit no refusal, and verified byte-identical
on the 29 pre-existing metrics.

**Registered.** (1) The notification share grows to a majority: without a response
`(admit - refund)/(admit - blind)` is the small half, and with one
`(aimd - refund)/(aimd - blind)` exceeds 0.5 at the collapsed spans. (2) AIMD beats plain `admit`
on goodput above the collapse span and is indistinguishable from it below, because a vehicle that
is never refused never halves anything and so pays nothing.

**Falsifier.** (i) `aimd` is not gated-better than `admit` at any span, in which case the signal
still does nothing and the disanalogy is deeper than signal consumption; (ii) `aimd` is
gated-worse than `admit` below the collapse span, in which case the rule costs cadence where there
is no congestion to pay for it and must not be recommended.

This is the first mechanism in the model added because a *literature* said the model was missing
something, rather than because a measurement did.

## CR-23 REFUTED on falsifier (ii): there is no knee, and the refutation supports CR-27

*`st-backoff-9445984`, section B1, full tier, 32 blocks at 64 reps, deterministic holds
(`retry_spread=0`), read 2026-08-22.*

Goodput damage against the no-retry arm on GE-120 at rung 3, every cell gated:

| rho | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 21 |
|---|---|---|---|---|---|---|---|---|---|---|
| n=4 | -0.217 | -0.082 | -0.080 | -0.078 | -0.087 | -0.090 | -0.083 | -0.075 | -0.066 | **-0.052** |
| n=5 | -0.510 | -0.470 | -0.436 | -0.357 | -0.247 | -0.174 | -0.135 | -0.118 | -0.090 | **-0.056** |
| n=6 | -0.404 | -0.387 | -0.368 | -0.343 | -0.317 | -0.297 | -0.248 | -0.206 | -0.137 | **-0.043** |
| n=8 | -0.163 | -0.153 | -0.138 | -0.128 | -0.120 | -0.106 | -0.090 | -0.077 | -0.062 | **-0.032** |

**Falsifier (ii) fires.** I registered that at n = 5 the damage would be large for rho <= 4 and gone
by rho = 8, and that a decline leaving more than half the rho = 2 damage at rho = 8 refutes the
account. At rho = 8 the damage is -0.357 against -0.510, which is 70%. The decline is smooth and
monotone at every span, from rho = 2 to rho = 21, with no threshold anywhere.

**The discriminator answers, and it answers against the load rule too.** The registered binary was
whether n = 8 on GE-120 clears by rho = 21, which the stationary reading of `d` requires
(`rho* = 20.6`). It does not clear: -0.032, t = -8.36, 32/32. Nor does any other cell. The damage
is gated at every span and every backoff including n = 4, where `rho*` is negative and the load
rule says there should be nothing to find.

**What survives, weaker and simpler.** The half-damage backoff does move right with span over
n = 4, 5, 6 (about 3, 10 and 16), which is the direction the jam floor predicts, at roughly twice
the predicted `rho*`, and it stops moving by n = 8. So span matters to the slope and not to a
threshold. The usable recommendation is therefore blunter than the one I wanted: a longer backoff
is monotonically better and there is no floor to find, so hold a failed requester off for as long
as the mission can afford. That is easier to field than a number, and it is what the CR-24
adaptive arm and the `fixed20` arm both already showed by another route.

**And the refutation is evidence for something else.** A load threshold predicts a switch: below
`rho*` the team is jammed and above it the retry is free. A synchronization account predicts
exactly what was measured, a smooth decline, because lengthening the hold spreads the retries out
in time and desynchronizes them gradually with no threshold to cross. CR-23's falsifier firing is
therefore a point in favour of CR-27, and it was not designed to be. That is the most useful thing
in this run.

**Registrations refuted on this contrast, running total: four.** CR-19e (coherence excess),
CR-21 (retry cohort via jitter), CR-22's mechanism (the d shift moving `n_c`), and now CR-23's jam
floor. The regularity is enormous and gated at |t| up to 162. Every threshold story proposed for it
has died and the one survivor is smooth.

## CR-27: the pump and the valve

*Registered 2026-08-22, before the run. Battery `desync.sh`. This is the fifth mechanism proposed
for one contrast and it is registered under a higher bar than the four that died, on Fable's terms:
one manipulation per clause, an exogenized intermediate, and a validated instrument.*

**The account.** A retry on a channel with long outages is a pump. It keeps re-offering during the
outage, everything floods through at the channel's recovery edge, and the console gets a cluster it
cannot absorb. The back of the cluster waits past `P` and abandons. And under `blind` the operator
serves it anyway, so the cluster costs real capacity. Two clauses, pump and valve, and neither is
sufficient.

**The valve clause already has its manipulation, gated.** `st-policyburst-9445271`: the burst
penalty on goodput does not shrink under `refund`, it reverses, `(co_ref - bern_ref) -
(co_blind - bern_blind)` running +0.037, +0.118, +0.253, +0.135 at n = 5, 6, 8, 10, every one
gated, t up to 73.8. At eight vehicles a bursty link costs a blind operator 0.206 of goodput and
buys a refunding one 0.047.

**And an exogenous one, with the feedback loop cut.** `queue_theory.bench_sim`, written today,
drives the console with a Markov-modulated Poisson arrival stream whose rate and burstiness are set
separately and neither of which can hear the console, so the two can be crossed. Dwells calibrated
to reproduce the observed Fano factors at matched rate. At rung-3 latency, `blind`:

| | goodput at rate 0.0882 | at 0.1035 | at 0.1187 |
|---|---|---|---|
| smooth (F = 1.0) | 0.654 | 0.534 | 0.389 |
| clustered (F = 6.3) | 0.222 | 0.126 | 0.066 |

Clustering at matched rate costs -0.432, -0.408, -0.322. Rate at matched clustering costs -0.265
smooth and -0.156 clustered. **Clustering does one and a half to two and a half times what the rate
does**, with the feedback cut, so it is not an artifact of the loop echoing console state back into
the arrival process. And the valve closes 39 to 61% of the clustering cost under `refund`.

This also corrects my own earlier apportionment. I reported the reply-leg coherence as carrying "a
little over half" of the observational effect. The three observational arms differ in BOTH rate and
clustering, so that split was never a rate/clustering split. On the bench the `mg` to `ge` rate
step is worth about -0.060, against -0.135 observationally, so the reply leg does roughly twice
what a pure rate change of that size explains and the residual is not identified.

**Two independent supports arrived unbidden.** CR-23's falsifier fired because the backoff damage
declines *smoothly* in rho with no threshold at any span, which is what desynchronization predicts
and what a load threshold does not. And CR-21's jitter refutation is explained rather than
explained away: a jitter of plus or minus three steps cannot desynchronize a cohort synchronized by
a 120-step channel edge.

**What is registered now, and what refutes it.** Fable found the confound that would have
manufactured a false confirmation: `retry_spread = s` does not hold the mean, because the hold is
floored at one step, so at `rho = 4` a spread of 30, 60 or 120 delivers a mean of 10.4, 18.2 or
33.9. Every jitter arm therefore carries a mean-matched fixed control computed by value.

- **P1.** Within each mean-matched pair the jittered arm has a lower arrival Fano than its fixed
  control. FALSIFIER: no pair shows a gated Fano reduction, in which case the retry phase is not
  the synchronizer and the account fails at its first step.
- **P2.** Within each mean-matched pair the jittered arm has higher goodput. FALSIFIER: a gated
  Fano reduction with no goodput gain, in which case clustering is a description and not a cause,
  and after four refutations I stop and report the regularity unexplained.
- **P3.** The gain is monotone in the Fano reduction across the three pairs.
- **D2, the null control.** On the memoryless channel there is no dwell to synchronize to, so the
  jitter must buy nothing. If it buys the same there, P1 is measuring the retry and not the
  channel.

**The instrument, and its floor.** `fano_window` turns on an in-simulator Fano factor of the
delivered uplink stream, binned so no per-step array is kept, byte-identical when off. Calibrated
at n = 5, rung 3 against the offline probe: bern_off 1.76, ge_off 2.86, bern_retry 2.54, ge_retry
5.77, same ordering and scale. Its floor is 1.76 and not 1.00, because a memoryless channel still
carries a within-mission demand trend from attrition, so only differences against a matched control
are meaningful. Stating that is the point of calibrating it: the first version of this measurement
was wrong because nobody asked what it could have shown.

## CR-24 VERDICT: the dominance claim died on goodput, and the insurance claim is what ships

*`st-adaptive-9445865`, full tier, 32 blocks at 64 reps, read 2026-08-22.*

**Prediction 1 (dominance) is refuted on operator goodput and holds on mission success.** On
GE-120 the adaptive arm is gated-worse than `fixed20` at n = 4, 5 and 6 (-0.039, -0.136, -0.116)
and hugely better than `fixed4` (+0.033, +0.305, +0.217). On mission success nothing separates
adaptive from `fixed20` at any span while adaptive beats `fixed4` by +0.153, +0.197 and +0.135, all
gated. Fable's reading of the split is right and I adopt it: goodput was the wrong gate for a
treatment that changes the request cadence, because it shares its denominator with the treatment.
`rate.sh` re-extracts both ladders on `served_per_step`.

**Prediction 3 holds exactly.** At the healthy cell, n = 4 on a clear link, all three arms read
0.985 and `adaptive - fixed4` is +0.0000 at t = 1.20, not gated. The doubling rule pays nothing
where nothing is owed, because a served requester never accumulates a streak.

**And `fixed20` is close to being an identity rather than a finding.** A backoff of 20 against a
standing interval of 22 gives a failure cycle of 41 steps against 43, so "the best fixed backoff"
is arithmetically "do not retry". That is worth saying plainly rather than dressing up.

**What ships, as insurance rather than optimization.** At the published span of six on a CLEAR
link, a naive short retry is catastrophic: operator goodput falls from 0.759 with no retry to
**0.066** with `rho = 4`, a 91% loss with no jamming involved at all. The adaptive doubling rule
recovers most of it, to 0.433, gated at +0.367 with t = 103.7 and 32/32, and the same gain holds
across the ladder (+0.336, +0.309, +0.217 at C1, C2, C3) until C4, where the latency ceiling makes
everything zero and the contrast is exactly +0.0000 as it must be.

So the recommendation is not "tune the backoff to rho*". It is: **the reliance loop has no measured
upside and a large downside; if one must exist, doubling makes it about as harmless as absence
without knowing the channel, the span, or rho, and a fixed short backoff is the only catastrophe.**
That is a fielded default, not an optimum, and it is honest about being one.

**One scope caveat, recorded because it could reverse the sign.** Waiting is priced flat here: an
asset at `q_fallback` is no more exposed the longer it waits. Where waiting is dangerous and
exposure escalates, the optimum shifts back toward re-asking, and of the arms tested only the
adaptive rule can track that without being re-tuned.

## CR-23, completed with the Bernoulli ladder, and the n=4 cell decides something else entirely

*`st-backoff-9445984`, section B2, read 2026-08-22. This corrects the verdict above in one
direction and sharpens it in another.*

Goodput damage against no-retry on the MEMORYLESS channel, rung 3:

| rho | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 21 |
|---|---|---|---|---|---|---|---|---|---|---|
| n=4 | -0.025 | -0.023 | -0.023 | -0.023 | -0.027 | -0.026 | -0.029 | -0.029 | -0.029 | -0.024 |
| n=5 | -0.089 | -0.061 | -0.058 | -0.046 | -0.044 | -0.046 | -0.045 | -0.045 | -0.041 | -0.036 |
| n=6 | -0.329 | -0.234 | -0.171 | -0.112 | -0.089 | -0.082 | -0.071 | -0.066 | -0.059 | -0.041 |
| n=8 | -0.361 | -0.347 | -0.328 | -0.293 | -0.257 | -0.211 | -0.162 | -0.123 | -0.090 | -0.045 |

**Falsifier (iii) does not fire, and that is a point FOR the load rule.** I designated the n = 4
Bernoulli cell as a refuter because `rho*(4, 0.640) = -3.9` says no backoff can jam it. It is
**not gated at any rho**: every cell reads -0.023 to -0.029 against a minimum practical effect of
0.030. And the span ordering the load rule predicts is there in the magnitudes: at n = 4 and 5,
where `rho*` is negative or 0.3, the damage is small; at n = 6 and 8, where it is 4.6 and 13.1, the
damage is large. So the load rule gets **which spans are vulnerable** right on the memoryless
channel and gets **where the vulnerability ends** wrong everywhere, which is a more useful verdict
than the flat burial above. Span sets a slope, and it also sets which teams are on the slope at all.

**And the n = 4 cell isolates the other mechanism, by accident.** Compare the two channels at four
vehicles, where every load account says nothing can happen, and where no value of `d` in [0,1] can
put `n_c` below four at any settable backoff:

| n = 4, rho = 21 | damage | t | gated |
|---|---|---|---|
| Bernoulli | -0.024 | -12.8 | **no** |
| GE-120 | -0.052 | -11.4 | **yes** |

The load channel is off by construction in both. The only difference is channel burst structure,
and it is the arm with burst structure that takes gated damage. That is a direct confirmation of
CR-27's pump clause at a span chosen for a different purpose entirely, and it was not designed to
be one.

**The corrected scorecard.** Of three registered falsifiers, (i) does not fire (the vulnerability
does move with span), (ii) fires (no knee at any span, on either channel), and (iii) does not fire
(the designated Bernoulli refuter is clean). I registered "any one of which retracts", so the
threshold account is retracted as registered. What replaces it is not nothing: `rho*` predicts the
vulnerable spans and predicts no threshold that exists.

## CR-25 VERDICT: the headline is not a threshold artifact

*Read 2026-08-22 from `st-attrib-9445987`, full tier, 32 blocks of 64.*

Prediction (c) was the one that could have taken the result away, and it HELD. `arrived_frac` on
the direct held-ratio arm falls at every step, 0.571, 0.408, 0.258, 0.216, 0.186, a total of -0.385
at t = -68.5 with 32/32 blocks agreeing. Success was not stepping across a sharpening binomial cut
while the underlying fraction sat still. The difference in differences on the continuous mediator
is +0.554 at t = +72.0, 32/32, against success's +1.231 at t = +75.9, so the two metrics carry the
same result and the sharper number on success is the threshold amplifying a real move rather than
manufacturing one. Channel 3 is dead and the headline keeps its meaning.

The attribution replicates on the mediator, which is the part I did not ask for. Across n = 3 to 15
at held ratio the direct arm falls -0.385, `refund` -0.301, supervisory -0.109, so the console owns
72% of the collapse and the scenario 28%. On success the same three arms give -0.676, -0.614 and
-0.171, a 75/25 split. Two metrics, one of them binary and one of them continuous, agree on the
split to within three points. That is the sentence the manuscript should carry, and it is stronger
than the one Fable told me to hedge in Round 7, because the residual is now bounded twice.

`refund` is the disagreement worth naming rather than smoothing: it recovers 9% of the direct step
on success and 22% on the mediator. Refunding the abandoned slot moves vehicles onto the objective
more than it moves missions over the half-force line, which is what a policy acting on the tail of
a distribution should do. It is one sentence in the discussion, not a claim.

## CR-23R support: the smooth decline survives on success with the smear removed

`st-backoff-9445984` section B3, deterministic holds, GE-120. At n = 5 success runs 0.356 with no
retry then 0.150, 0.179, 0.194, 0.246, 0.301, 0.333, 0.343, 0.354, 0.337, 0.350 across rho = 2 to
21; at n = 6 it runs 0.542 then 0.257, 0.324, 0.323, 0.334, 0.371, 0.396, 0.438, 0.447, 0.485,
0.502. Every retry arm is worse than not retrying, at both spans, and the damage decays smoothly
toward zero with no knee anywhere. CR-23's falsifier (ii) fires on success exactly as it fired on
goodput, and it fires now on holds that are not smeared by the rescale. The load rule is dead on
both the metric it was derived for and the metric the sponsor reads.

## CR-28: is "do not re-ask" an artifact of pricing a wait flat?

*Registered 2026-08-22 BEFORE the tier run, on Fable's Round 6 caveat. Battery `stall.sh`.*

The recommendation this project is closest to shipping is that on a channel with long outages the
operator should not re-ask, and B3 above now says it at full tier on success. But the model prices
waiting FLAT: a vehicle stopped at `q_stall` on the twentieth step of its wait is exactly as badly
off as on the first. Fable's objection is that this is where the recommendation is cheapest to
make. Where waiting is dangerous, exposure escalates with the wait, and a rule that tells a stopped
vehicle to keep waiting is spending something the model does not charge it for.

`stall_decay` and `stall_floor` (added today, `stall_decay = 0` byte-identical to the published
model, tested) let the wait be priced by how far into its own patience window it has run.

**Registered, and this is Fable's prediction rather than mine.** (1) As `stall_decay` rises the
optimal backoff moves LEFT, toward re-asking sooner. (2) The adaptive rule beats `fixed20` at high
decay where at flat pricing it does not. FALSIFIER for the pair: the ordering of the arms is
unchanged in sign at `stall_decay = 1` and no retry arm gates above no-retry, in which case the
recommendation is NOT an artifact of flat pricing, the caveat is answered rather than conceded, and
the manuscript says so with the exposure sweep as its evidence.

A 48-seed pilot ran before the battery was written, to confirm the knob moves the metric at all. It
does: at n = 6, rung 3, GE-120, no-retry goes 0.562, 0.500, 0.375 across decay 0, 0.5, 1.0 while
rho = 20 goes 0.417, 0.354, 0.396. That is ungated at 48 seeds and is NOT the test; it is recorded
here so that the tier result cannot later be read as if the registration had been written to fit
it. The registration above stands as Fable wrote it.

## CR-27 AMENDMENT: P3 relocated, and a rule about who verifies what

*Written 2026-08-22T22:00:38Z, while jobs 9446092-95 were RUNNING and
`runlogs/st-desync-9446092.out` held 6 header lines and 0 AR_ROW records. The battery had produced
no data when this was written, which is the only condition under which a registration may be
amended.*

Fable's Round 10, on the D1 rebuild.

**P3 is withdrawn as constructed and moved.** Holding the mean by `retry_spread = rho - 1` couples
the jitter width to the backoff level, and the coupling is worse than collinear: width is the dose,
so more of it should help more, while level is headroom, so more of it leaves less damage to
repair. The two have OPPOSITE expected signs, and any across-pair pattern is therefore consistent
with some mixture of them. The three D1 pairs stay in as replicated within-level tests of P1 and
P2, where the confound cannot reach, and **their across-pair magnitudes will not be interpreted.**
That is written here before the numbers exist so it cannot be decided after seeing them.

P3 moves entirely to D4's width ladder, which is the only clean one in the project: three arms at
one level, mean 21, widths 0, 10 and 42, at an operating point where sustained load is off for
every drop probability. Pre-registered caveat: the widest arm's support reaches down to one step,
so its low tail re-arms occasional fast retries. **The claim is that the Fano factor falls
monotonically in width.** If goodput is non-monotone at the widest arm specifically, that
implicates the re-armed tail and is not evidence against dose response, and this sentence is what
entitles that reading rather than a later rationalization.

**The convention, and the guard that now enforces it.** My guard rejected only `retry_spread >
retry_backoff + tau`, which is a backstop and not the invariant. Fable's counterexample: rho = 4
with spread 12 passes it and still shifts the mean 45.7% through the floor, and spread 26 shifts it
135%. The guard is replaced by one that computes the realized mean over the full cooldown support
and rejects a deviation past 2%. That admits D4's (21, 21) at 0.2% and rejects (4, 12) at 45.7%,
which is the line the design needs rather than the one that was easy to write.

**The failure mode is worth naming because it produced two errors in three rounds.** Fable verified
my claims by value and its own designs by memory, and I did the same thing in the opposite
direction: I checked its arithmetic and shipped my own guard without testing a case it should have
caught. Standing rule from here: **every jitter arm's realized mean is computed by value and
printed in the battery's own registration before the battery is submitted.** Design is not exempt
from the verification standard that findings are held to.

## CR-29: the exposure test, priced by a mechanism authored for something else

*Registered 2026-08-22 after a 48-seed pilot and BEFORE the tier run. Battery `teleop_price.sh`.
Supersedes CR-28, which Fable cut and which is right to cut.*

CR-28 asked whether "do not re-ask" survives pricing a wait by exposure, using a `stall_decay` knob
I wrote for the purpose. Fable's Round 10 verdict is that a null on a self-authored knob with a
self-chosen range is not evidence, and it is correct. The replacement has to price the wait with a
mechanism nobody authored for this question.

`behavior.py` is that mechanism. It was written for CR-2, on the observation that the published
model let a teleoperated vehicle keep driving at 54.5% speed with its operator link severed, which
is not what a teleoperated vehicle does. Under `blue_behavior = teleop` with `teleop_stop = true` a
vehicle with no answer coming back **stops**. Waiting is then dangerous in the only way a
mission-level model can make it dangerous: the vehicle is not advancing while it waits. Nothing
about that was chosen with the retry question in view, and `teleop_stop = false` reproduces the
published path exactly, which the pilot confirms cell for cell.

**Registered.**

1. *Confirmatory, and the pilot suggested it, which is said here rather than discovered later.*
   Under stop-dead physics the no-retry arm still leads and the retry penalty is LARGER than under
   the published physics, not smaller. Pilot at n = 6, rung 3, GE-120, 48 seeds: published physics
   gives 0.562 / 0.333 / 0.354 / 0.562 across no-retry, rho = 4, 12, 21; stop-dead gives 0.333 /
   0.000 / 0.000 / 0.229. FALSIFIER: any retry arm gates above no-retry under stop-dead physics.

2. *The new content, and the part that can fail.* The mechanism is time in stall, and re-asking is
   what buys it: a retry returns the vehicle to the waiting state that the published model let it
   drive through. So `hold_fraction` rises monotonically as the backoff shortens, and the success
   damage tracks it across arms. Pilot: 0.448 / 0.796 / 0.586 / 0.456 against the successes above.
   FALSIFIER: `hold_fraction` flat or non-monotone in the backoff while success still moves, in
   which case the damage is not stall exposure, the mechanism sentence is withdrawn, and only the
   weaker claim in (1) survives.

3. *Pre-registered as a confound, not a result.* `blue_loss_frac` is NOT a valid gate here and
   Fable's instruction to gate on it is declined for a reason visible in the pilot: at rho = 4 the
   hold fraction is 0.796 and blue losses are 0.156, the LOWEST of any arm, because vehicles that
   never advance are never engaged. This is the bloodless-day artifact from Round 7 appearing in a
   new place. Blue losses are reported and interpreted only jointly with `arrived_frac`.

4. `fan_out` converts the result into the span-of-control literature's own units, falling 2.24 to
   1.26 from no-retry to rho = 4 in the pilot. Reported, not gated: fan-out is a derived ratio here
   and this project has not established its noise floor.

**Why this is the version worth printing.** The claim is not that a wait costs something; that is
an assumption either way. It is that under a stall cost written into the model two conjectures ago
for an unrelated reason, the recommendation does not merely survive, it strengthens, and it
strengthens through a mechanism that predicts which arm degrades most and by how much. Fable's
Round 6 caveat is answered rather than conceded, and the answer is the opposite of what the caveat
expected.

**CR-28 disposition.** Cut from the paper. Job `st-stall-9446094` was already running when the cut
was made and is allowed to finish; its output enters the ledger as a labeled stress test to a named
extreme, is not a section, and is not cited as evidence for the recommendation.

## CR-29 AMENDMENT: it prices mobility, not exposure, and the mediator is partial

*Written 2026-08-22 on Fable's Round 11, BEFORE `teleop_price.sh` was submitted. The battery had
produced no data.*

**The mechanism is renamed, and the old name was wrong in a way the pilot already showed.**
`teleop_stop` does not price EXPOSURE. It prices MOBILITY. A stopped teleoperated vehicle is not
more likely to be hit; it is less likely, because it never advances into contact, which is exactly
why the rho = 4 arm in the pilot has the highest hold fraction (0.796) and the LOWEST blue losses
(0.156). What re-asking costs under this physics is tempo, not casualties. Every sentence about
CR-29 says mobility from here, and the phrase "where waiting is dangerous" is withdrawn: in this
model waiting is safe and slow, which is a different objection to the recommendation and a weaker
one than the one Fable raised.

**Fable concedes its own Round 6 caveat in this quadrant, and the concession is recorded because it
narrows what CR-29 can claim.** When asking is itself what stops the vehicle, attempt rate is the
thing the physics charges for, and a short backoff maximizes attempts, so the recommendation was
never at risk here. The caveat survives only in the untested quadrant where waiting is priced by
QUALITY rather than by motion, and neither of us has a mechanism for that quadrant that was not
authored for the test. It is deprioritized rather than run, which is a decision recorded here so
that the CR-29 result is not later read as having answered more than it did.

**A pre-registered limit on prediction 2.** The pilot's rho = 21 cell resists the mediator: its
hold fraction is 0.456 against no-retry's 0.448, effectively matched, yet its success is 0.229
against 0.333. If the tier run reproduces a gated success deficit at matched hold fraction, then
hold fraction is a PARTIAL mediator and something else carries the remainder, with the
deterministic re-consultation cadence the leading suspect. **Registered now: prediction 2 may not
be reported as full mediation, whatever the tier data look like.** The most it can claim is that
hold fraction accounts for the ordering across arms that differ in hold fraction.

## CR-30 AMENDMENT: O4 was aimed at something the knob cannot produce

*Written 2026-08-22 on Fable's Round 12, BEFORE `droop.sh` was submitted. The battery had produced
no data and was still queued behind jobs 9446092-95.*

Fable's Round 11 co-option sentence said a quality droop should move the collapse itself LEFT,
because a degraded answer is rework and rework is offered load. I wrote O4 to test that. Fable then
read the code and found that the sentence carries a REWORK CONDITION this model does not meet, and
it is right. Verified independently before the amendment: `_reset_cooldown` takes the terrain
difficulty and nothing else, and `control_quality` reaches `motion`, `engagement` and `belief` but
never the request cadence. A badly served vehicle drives slower and shoots worse. It does not ask
again sooner. **The queue's booking arithmetic is quality-blind by construction.**

So O4 as first written would have been refuted BY CONSTRUCTION rather than on the merits, which is
the worst kind of registered prediction: it looks like a test and cannot fail informatively. Split
into a decomposition instead:

- **2a.** The SUCCESS-optimal span moves LEFT as droop rises, because quality reaches the mission.
- **2b.** The GOODPUT cliff location is droop-INVARIANT, up to the second-order mission loop.

FALSIFIER for the pair: the goodput cliff moves materially while the success optimum does not,
which would mean quality reaches the booking arithmetic by a path neither of us found in the code,
and the mechanism section would have to carry it.

Passing both is a sharper result than the co-option claim it replaces, because it is a
decomposition rather than a direction: quality effects and load effects separate exactly where the
model's own structure says they must. The full co-option claim needs a rework channel, which this
model does not have and which is not built for this battery.

**Two reading rules recorded before the data.** The supervisory-over-direct ordering is ONE-SIDED
by construction, since a droop harms only the direct arm, so it is reported and not counted among
the orderings that could have failed; four orderings carried real risk, not five. And the goodput
magnitude-stability, if it survives at tier, is to be reported WITH its cause rather than as a
surprise: it is stable because admission control acts on booking arithmetic that never sees
quality. Saying why is what stops it reading as too good to be true.

**Scope, not error.** The 48-seed pilot at C3 showed the refund ordering wobbling in sign. The
shipped claim is at C0 and n = 8, where it does not. That stays in the ledger as a scope boundary:
the invariance is asserted at the operating points the paper quotes, and not swept.

## CR-26 VERDICT: prediction 1 refuted, and the truth is sharper than the prediction

*Read 2026-08-22 from `st-aimd-9446095`, full tier, 32 blocks of 64.*

**Prediction 1 is REFUTED as written.** I predicted the notification's share,
`(aimd - refund)/(aimd - blind)`, would exceed 0.5 at the collapsed spans. On goodput at rung 0 it
runs 0.097, 0.087, 0.139, 0.195 at n = 6, 8, 10, 12. Nowhere near. The share statistic was the
wrong instrument and the run says why: at those spans the no-response share is NEGATIVE, running
-0.082, -0.117, -0.213, -0.301, because `admit` is WORSE than `refund` there. A ratio whose
numerator changes sign cannot measure a share, and I should have seen that before registering it.

**What the negative share means is the actual result, and it is better than the one I predicted.**
Telling the requester is not a small positive increment over freeing the slot. Without a response
rule it is **actively harmful** at every span past collapse: on goodput at rung 0, `refund` gives
0.917, 0.800, 0.683, 0.579 at n = 6, 8, 10, 12 while `admit` gives 0.905, 0.734, 0.574, 0.449. The
mechanism is the one CR-26 was registered on: a refused vehicle goes autonomous sooner and then
returns on exactly the same standing cadence, so the notification manufactures requests faster
without changing the rate at which they can be served. The console is telling vehicles to come back
sooner and calling it admission control.

**Prediction 2 HOLDS, and it is what ships.** `aimd` beats plain `admit` on goodput at every span
past collapse: +0.126 at n = 8 (t = 111.9), +0.210 at n = 10 (t = 117.9), +0.268 at n = 12
(t = 166.1), all 32/32. Below collapse it costs nothing: at n = 4 the difference is -0.0003
(t = -1.3, 13/32) on goodput and -0.012 (t = -0.7, 13/32) on success. A vehicle that is never
refused never halves anything, exactly as registered. At n = 6, on the threshold itself, the gain
is +0.029 at t = 42.5, which sits at the minimum practical effect and is reported as the boundary
case it is. On mission success the gain gates at n = 10 rung 0 (+0.044, t = 4.0, 24/32) and at
n = 8 and 10 on rung 2 (+0.033 and +0.035), and falls below the minimum effect at n = 12 where
every arm is already near ceiling.

**Neither falsifier fires.** (i) `aimd` is gated-better than `admit` at many spans. (ii) `aimd` is
not gated-worse than `admit` below the collapse span on any of the four metric-by-rung cells.

**What this does to the paper.** The manuscript currently says admission control has two halves and
that telling the requester is the smaller one. That sentence is wrong in a way that matters: the
second half is not smaller, it is negative, unless the vehicle has a rule for consuming it. The
correct statement is that a congestion signal is worth nothing until something responds to it and
worth a great deal once something does, which is the Floyd and Fall reading the conjecture was
registered on. This is the first mechanism added to the model because a literature said something
was missing, and it is now also the one that changed a published claim.

## CR-27 VERDICT: the pump is refuted, and the null control names the survivor

*Read 2026-08-22 from `st-desync-9446092`, full tier, 32 blocks of 64. Fifth mechanism to die on
this contrast, and the first time the replacement was already sitting in the battery as a control.*

**P1 is REFUTED on its registered falsifier.** Not one of the six mean-matched pairs on the bursty
channel shows a gated Fano reduction. The differences run -0.080, +0.052, -0.024 at n = 5 and
+0.216, -0.076, -0.091 at n = 6, every one with |t| below 1.8 and sign agreement near half. I
registered "no pair shows a gated Fano reduction, in which case the retry phase is not the
synchronizer and the account fails at its first step." It fires.

**P2 holds, and holds everywhere.** Jitter beats its mean-matched fixed control on operator goodput
at every pair: +0.014, +0.000, +0.051 at n = 5, and +0.005, +0.012, +0.024 at n = 6, with the
largest pair at t = 11.9 and 32/32. The effect is real and it grows with jitter width. What it is
not is an effect of the channel.

**D2, which I registered as a null control, is not null, and I wrote down in advance what that
would mean.** The battery says: on the memoryless channel "there is no dwell to synchronize to and
the jitter should therefore buy nothing. If it buys the same there, the story is about the retry
and not about the channel, and P1 is measuring the wrong thing." On the memoryless channel jitter
buys **+0.040 at n = 5 (t = 31.0, 32/32) and +0.049 at n = 6 (t = 30.6, 32/32)**, which is as large
as or larger than anything it buys on the bursty one. And there, where the retry is the only source
of clustering, the Fano reduction the instrument was built to see **does** appear: -0.134 and
-0.130, both gated.

**So the mechanism is retry self-collision, not channel phase compression.** Vehicles that go
unanswered together retry together, and a deterministic hold keeps them together for the next
attempt and the one after. Jitter decorrelates them from EACH OTHER. The channel is what puts them
in the same boat initially; it is not what keeps them there. The Fano instrument reads null on the
bursty channel because the channel's own burst structure dominates the delivered stream's variance
and drowns the retry's contribution, which is why the memoryless arm was the informative one and
the one I had designated as a throwaway.

**This is a better mechanism than the one it replaces, and it is not new.** It is the reason binary
exponential backoff randomizes at all: contending senders that retransmit on a fixed schedule
collide, back off identically, and collide again \citep{metcalfe1976ethernet}. The project already
cites that literature for the backoff FLOOR. It turns out to explain the backoff WIDTH as well, and
the paper can now say both with one mechanism instead of two.

**The pump clause is withdrawn.** The `st-backoff` n = 4 cell that appeared to confirm it is
re-read below and does not carry it either. Nothing in the manuscript asserted the pump, which is
the only reason this costs a paragraph rather than a section.

## CR-27 D4/D5/D6: the free cell survives its audits and still is not a poster

**D6 passes exactly as registered.** Per-step damage at n = 4 is -8.9%, -8.8% and -8.8% of the
no-retry rate at mission lengths of 1200, 1800 and 3600 seconds. The damage is a RATE and not a
transient of the opening minutes, which is what a congestion mechanism should look like. Mission
success is identical at all three durations because missions finish well inside 1200 s, so that
half of D6 carries no information and is reported as carrying none.

**D5 does not kill the cell.** The GE-minus-Bernoulli difference at n = 4 runs +0.0215 under a
synchronized start and +0.0347 under staggered starting phases, so staggering does not remove it;
it grows. The registered tolerance was that staggering removes at most 40%, and it removes none.
Neither arm reaches 60% block agreement, so the audit clears the cell of being a start artifact
without establishing the cell.

**The n = 4 free cell does not gate, and the reason is a convention this project never fixed.** On
success nothing gates at n = 3 or n = 4. On `served_per_step` the GE damage at n = 4 is -0.0044
absolute, which is -8.8% relative, at t = -8.09 with 31/32 blocks, and jitter recovers +5.2% and
+11.2% monotonically in width at t = 5.11 and 10.31. Whether those gate depends entirely on whether
the minimum practical effect of 0.030 is read as absolute or relative, and **the project calibrated
it on metrics living on [0,1] near 0.5 and never defined it for a rate metric whose values are near
0.05.** Reading it absolutely, nothing gates. Reading it relatively, everything does.

**That is settled here, before it can be settled by whichever answer is convenient.** The MPE is
declared RELATIVE for rate metrics and absolute for metrics on [0,1]. An absolute 0.03 on
`served_per_step` would be 60% of the metric, which is not a minimum effect but a demand for a
catastrophe.

**The constant is 6% of the control arm, not 3%, and the first draft of this entry got it wrong.**
The reasoning was that 0.03 of mission success is "three points of a probability" and the analogue
for a rate is 3% of the rate. That conflates points with percent. The MPE was calibrated on metrics
near 0.5, and 0.03 at 0.5 is **6% of value**, not 3%. Carrying the stringency across, rather than
the digits, gives 6%. (`tests/test_gate_helpers.py::test_six_percent_matches_the_calibration_scale`
pins the arithmetic.) 3% would have quietly halved the bar on every rate metric this project ever
gates, which is the same class of error as the absolute reading it was introduced to fix.

**The amendment applies forward only, and this cell is not forward.** A threshold chosen after
unblinding cannot adjudicate the data that prompted it. The n = 4 damage (-8.8%) and the jitter
recovery (+5.2%, +11.2%) were all seen before the convention was fixed, and are hereby marked
**ungated under the pre-existing rule; convention amended after unblinding**. For the record of
what the amendment would have done: -8.8% and +11.2% clear 6% either way, and the +5.2% recovery
clears 3% but not 6%, so the constant is load-bearing on exactly the cell that motivated the
question. That is the reason to refuse to apply it here. The cost is nil, because the cell is
retired for an unrelated reason below, and what is preserved is the gate's meaning: thresholds are
registration content, and an amendment to one is a rule for the next conjecture, never a re-scoring
of the last.

**And the cell still does not become a poster, for a reason that has nothing to do with the gate.**
CR-27's P1 is refuted above, so the pump account this cell was collected to support no longer
exists. What the cell now shows is retry self-collision at a span where sustained load is off,
which is the same thing D2 shows more cleanly on a channel with no burst structure at all. The
clean demonstration is the one to print.

---

## CR-27 D7. THE CROSS-CHANNEL RE-READ, AND THE EXPLANATION IT KILLS

Zero new compute. D1 and D2 are sections of one battery, so block `i` carries the same seed in
both and the cross-channel difference in differences on the mean-matched wide-jitter contrast is
itself a paired quantity. Running it separates the effect into the part that exists on a link with
no dwell at all (vehicles desynchronizing from each other) and the part the dwell adds.

| metric | span | self-collision (no dwell) | dwell residue | residue gates |
|---|---|---|---|---|
| operator_goodput | 5 | +0.0400, t=31.0, 32/32 | +0.0112, t=2.5, 22/32 | no (under MPE) |
| operator_goodput | 6 | +0.0490, t=30.6, 32/32 | -0.0248, t=-5.2, 26/32 | no (under MPE) |
| arrival_fano | 5 | -0.1341, t=-3.2, 22/32 | +0.1106, t=1.8, 21/32 | marginally, t just over 1.70 |
| arrival_fano | 6 | -0.1296, t=-2.8, 22/32 | +0.0385, t=0.5, 18/32 | no |

**The self-collision component carries the whole of what gates, and the dwell residue changes sign
between the two spans.** On the outcome metric neither residue reaches the MPE and their point
estimates are opposite, which is what an unstable nuisance term looks like and not what a second
mechanism looks like. Fable's hoped-for three-part ledger does not materialize because there are
not three parts; there is one audited part and a residue that will not hold still. That is the
better answer, and it makes the recommendation indifferent to the link.

**The Fano residue at n = 5 marginally clears (t = 1.76, 21/32), and is reported rather than
buried.** A difference in differences on a variance statistic is the noisiest thing in this
project's instrument set, and a pass at t = 1.76 is the weakest a pass can be. It is not load
bearing for anything claimed.

### The explanation that had to die first

The paper said the bursty link's Fano null was the channel's own variance drowning the retry's
contribution. That is a claim about the INSTRUMENT, and this project has now been bitten three
times by conventions asserted about instruments instead of measured on them. `tools/bench_fano.py`
measures it: arrivals are `N_t = K * B_t` with `B_t ~ Bernoulli(lambda/K)`, so the mean is `lambda`
for every K and the Fano is exactly `K - lambda`. A cohort of K = 2 therefore raises the source's
Fano by exactly 1.000 and moves nothing else. Pushed through a memoryless channel and through an
on-off gate with matched marginal rate, at 32 blocks of 1800 steps:

| channel | window | baseline F | recovered | t |
|---|---|---|---|---|
| memoryless | 1 | 0.85 | 0.998 | 376 |
| on-off | 1 | 0.85 | 1.000 | 354 |
| memoryless | 10 | 0.89 | 0.907 | 23 |
| on-off | 10 | 1.78 | 0.957 | 17 |

**REFUTED.** The estimator recovers the injected cohort on the bursty stream at least as well as on
the memoryless one, worst case 6% short across every window read, even where the channel's own
burst structure has doubled the baseline. The contrast is paired on the gate realization, so the
channel variance is differenced away rather than competing with the signal. Drowning was never the
reason.

**What the null actually says is that the cohort is not there,** and the mechanism follows: an
outage that drops several vehicles does not release them at one instant, so a bursty channel has
already scattered the return times that a deterministic hold would otherwise preserve. The channel
does part of the randomizing for free. That is why the arm with no burst structure was the
informative one, and it is a statement about the fleet rather than an apology for the instrument.

### Ledger

Three instrument defects, one genus: a convention calibrated on its first use case and carried
silently into a second. Nominal jitter width where the floor clipped the support; an MPE of 0.03
where the metric lives near 0.05; blocks-won counting positives where the effect goes down. A
fourth surfaced while writing the fixture that closes the class: `paired` returned `t = inf` for
two identical arms, because the zero-variance branch never asked whether the effect was also zero.
`tests/test_gate_helpers.py` now runs every gate helper against negative effects, rate scales,
clipped supports and null contrasts, with answers computed by hand. The genus is closed by a test,
not by vigilance.

---

## CR-31. DOES PLAIN ADMISSION CONTROL INVERT AGAINST MERE REFUNDING?

**REGISTERED before the falsifying metric is run.** Fable predicted a scope limit on CR-26: that
plain `admit` loses its advantage past the span where the shortened re-ask cycle overloads the
console, and proposed the doctrine sentence "a refusal without a client-side rate rule is not
admission control, it is load acceleration with better manners." The prediction is confirmed on
`operator_goodput` at rung 0, and the size is not marginal:

| n | admit - refund (goodput) | t | blocks | admit - refund (success) | t |
|---|---|---|---|---|---|
| 4 | +0.0005 | 2.3 | 23/32 | +0.0122 | 0.9 |
| 6 | -0.0121 | -14.0 | 32/32 | +0.0068 | 0.5 |
| 8 | -0.0660 | -43.7 | 32/32 | +0.0142 | 1.4 |
| 10 | -0.1094 | -51.7 | 32/32 | +0.0122 | 1.1 |
| 12 | -0.1306 | -75.9 | 32/32 | +0.0176 | 2.3 |

Two things are already clear without any new run. **The inversion is on the console's efficiency
and not on the mission**: on `success` nothing gates at any span, so refusing work does not cost
missions, it costs console cycles. And **AIMD more than repairs it**: `aimd - refund` is +0.060,
+0.101 and +0.137 at n = 8, 10, 12, so the three-lever recommendation is unaffected either way.

**But the goodput reading cannot be trusted here, for a reason this project has already found
once.** `operator_goodput = n_serviced / n_request`, and a refusal MANUFACTURES requests exactly as
a retry does: a refused vehicle returns to autonomy sooner and re-consults sooner, inflating the
denominator on its own. That is the contamination CR-23R was registered to measure for retries, and
it applies verbatim to refusals. A -0.131 goodput gap at n = 12 is consistent with admission control
genuinely serving fewer vehicles AND with it serving the same vehicles while being asked more often.

**PREDICTION.** On `served_per_step`, the absolute rate with no denominator to inflate,
`admit - refund` is negative and gates (relative MPE 6%, |t| > 1.70, 60% agreement) at n = 8, 10
and 12 on the clear channel.

**FALSIFIER.** If `served_per_step` shows `admit >= refund` at those spans, or the negative effect
fails to gate, the goodput inversion is denominator inflation. The doctrine sentence is then
WITHDRAWN, not softened, and the goodput column above is marked contaminated in the same way the
CR-23 v2 ladder was.

**Either verdict is worth having.** If it holds, the paper gains a scope limit on its own
recommendation, which is the kind of qualification a sponsor needs and a paper usually omits. If it
is refuted, a metric this project reports in six places is shown to be inflatable by a second
mechanism, and every refusal contrast in the manuscript has to be re-read on the absolute rate.

---

## CR-32. THE LEWIS 2010 RETRODICTION, REGISTERED BEFORE THE SOURCE TEXT IS READ

`10.1177/0018720810366859`, Lewis, Wang, Chien, Velagapudi, Scerri and Sycara, *Choosing Autonomy
Modes for Multirobot Search*, Human Factors 52(2):225-233. Multirobot foraging at 4, 8 and 12
robots, between-groups repeated measures, comparing full-task performance against exploration alone
and perceptual search alone.

**What the abstract already gives away, and therefore cannot be predicted.** Operators in the
full-task condition could not manage 12 robots and found half as many victims as perceptual-search
operators; exploration performance was about the same in the full-task and exploration-only
conditions; the authors conclude navigation is the limiting subtask. All of that is read, so none of
it is a prediction.

**What the abstract does NOT give, and what the two accounts disagree about: the shape between 4
and 8.** This is the discriminating quantity and it is registered here before the source text is
obtained.

- An **attention** account has the operator's per-robot quality declining as soon as the robots
  compete for a fixed budget. Yield per robot should therefore fall monotonically from 4 onward, so
  4 to 8 already shows loss and 12 is the continuation of a trend.
- A **queue** account has nothing bind until the server saturates. Below `n*` the console clears its
  backlog between requests and added robots are close to free, so total yield should RISE from 4 to
  8. At and above `n*` unrefunded abandonment turns the queue unstable and yield collapses. 12 is
  not the continuation of a trend, it is the other side of a threshold.

**PREDICTION.** Total full-task yield rises (or is statistically flat, not falling) from 4 to 8
robots, and falls at 12. Equivalently: the 4-to-8 step and the 8-to-12 step have opposite signs.

**FALSIFIER.** If full-task yield declines monotonically across 4, 8 and 12, the queue account gains
nothing over the attention account on this dataset, and Lewis is recorded as compatible-but-not-
discriminating, in the same status class as the wait-time entry. It is NOT reported as support.

**Second falsifier, on their own mediator.** Their report that exploration performance is unchanged
between the full-task and exploration-only conditions is, on the queue reading, the more important
number: an operator who is not degraded at the subtask still produces the aggregate collapse, which
is this paper's sufficiency thesis measured in a human experiment rather than a simulator. But if
the source text shows exploration performance in fact declining with team size and the abstract's
"roughly the same" refers only to the 4-robot cell, that reading is withdrawn.

**Status until the source text is in hand: OPEN.** Nothing from this paper enters the manuscript
until both falsifiers have been checked against the actual numbers, not the abstract.

---

## CR-33. THE DWELL RESIDUE: TWO STORIES, REGISTERED TOGETHER, AND A TEST THAT KILLS BOTH

**First, the retraction.** CR-27 D7 above reports the residue's sign flip between n = 5 and n = 6
and I matched it against `n* = 6.45`. That constant is the CLEAR-LINK NO-RETRY threshold and it is
wrong on both counts: the residue table is built from the `jit18`/`fix18` pair at rung 3, both of
which retry. Recomputed with the shipped closed form, where a retry replaces `patience + tau + 1`
with `patience + backoff + 1`:

| pair mean rho | memoryless (D2) | GE-120 (D1) |
|---|---|---|
| 4 | 5.86 | 4.70 |
| 10 | 7.27 | 5.82 |
| 18 | 9.14 | 7.33 |

The residue table is the mean-18 row, whose thresholds are 9.14 and 7.33. **Both n = 5 and n = 6
sit below both.** The flip does not bracket anything. The coincidence is withdrawn, and it is worth
naming the error: I matched a number to the nearest constant I had memorized instead of computing
the constant that governed the arms in front of me. This is the same genus as the three instrument
defects, transplanted from code into reasoning.

**Fable's alternative, which fits the data mine cannot.** Jitter's value is single-peaked in
congestion: zero at idle (nothing to collide with), maximal near threshold, back toward zero deep in
saturation (the server is never idle, so arrival timing stops mattering). The residue is then the
difference of two single-peaked curves whose peaks sit at the two channels' different thresholds,
GE at 7.33 and memoryless at 9.14. On the rising limb the GE curve leads; once GE crests while
memoryless is still climbing, the difference turns negative. Observed: +0.0112 at n = 5 (GE ahead,
n/n* = 0.68 against 0.55) and -0.0248 at n = 6 (GE at 0.82 of its threshold and cresting, memoryless
still at 0.66 and climbing). That is the pattern.

**PREDICTIONS, registered before the run, on the mean-18 pair.**

| n | mine (retracted account, kept as the null) | Fable's single-peak account |
|---|---|---|
| 4 | negative or flat | near zero, both curves near idle |
| 5 | positive | positive |
| 6 | negative | negative |
| 10 | stays negative | returns toward zero, both past peak |

n = 4 and n = 10 discriminate. n = 5 and n = 6 are already seen and adjudicate nothing.

**THE TEST THAT CAN KILL BOTH, and the reason to run it first.** Under either account the flip is
located by the two thresholds, so it must MOVE when the pair mean moves. At mean 4 the thresholds
are 5.86 and 4.70 and the crossing should fall near n = 4 to 5; at mean 18 they are 9.14 and 7.33
and it should fall near n = 6 to 7. **FALSIFIER: if the flip sits between n = 5 and n = 6
regardless of pair mean, it is not threshold-located, and both accounts are refuted together.** The
residue then goes into the paper as an unexplained regularity or not at all, and no mechanism is
claimed for it.

Nothing about the residue enters the manuscript until this runs. The self-collision component,
which is what actually gates, is unaffected either way.

---

## CR-34. THE COHORT INSTRUMENT, AND THE THIRD ACCOUNT IT KILLED IN ONE AFTERNOON

Fable asked for the instrument that would decide whether a bursty channel's cohort is born
pre-scattered. Collision multiplicity, `E[k | k >= 1]` over windows one service time long, because
k requests inside one service is k-1 forced waits and that is the quantity the mechanism consumes.
A Fano factor is a variance and cannot tell many small clusters from few large ones.

**Three accounts died in order, which is worth recording as a sequence rather than a conclusion.**

1. *Drowning.* The channel's variance hides the cohort. **Refuted** by `tools/bench_fano.py` at
   service-scale windows: a known injected cohort is recovered to within 6% on the on-off stream.
2. *Born pre-scattered.* The outage releases its vehicles at different instants, so there is no
   cohort. **Refuted, in the opposite direction:** GE multiplicity is HIGHER than memoryless at
   every cell (+1.049, +0.890 at pair mean 4; +0.186, +0.352 at 18).
3. *Banked idle time.* GE clustering arrives against a console idled by the outage, so it is
   absorbed. **Refuted:** GE utilization is HIGHER (0.603, 0.645) than memoryless (0.477, 0.572),
   because GE's two-way delivery is 0.798 against 0.640 and it simply delivers more.

**And that last number exposed a confound in the instrument itself.** `E[k | k >= 1]` rises with
rate for ANY process, so a channel delivering 25% more round-trips looks more clustered with
identical phase structure. `arrival_excess` divides by the Poisson value at the arm's own delivered
rate, `lw / (1 - exp(-lw))`. That is the scatter-only control and the only form of this statistic
comparable across channels. 32-seed probe, pair mean 18, rung 3:

| channel | n | excess, fixed hold | excess, jittered | delta | t |
|---|---|---|---|---|---|
| memoryless | 5 | 1.096 | 1.001 | -0.094 | -5.3 |
| memoryless | 6 | 1.099 | 1.011 | -0.088 | -4.9 |
| GE-120 | 5 | 1.214 | 1.042 | -0.173 | -3.5 |
| GE-120 | 6 | 1.348 | 1.083 | -0.265 | -6.4 |

**The account the data supports, and it is the first one that explains all four facts.** On a
memoryless link the retry hold is the ONLY thing setting arrival phase, so randomizing the hold
scatters the stream COMPLETELY: excess goes to 1.001 and 1.011, statistically a Poisson process. On
a bursty link the channel gate is a SECOND synchronizer sitting downstream of the hold, and the hold
cannot reach it: however the vehicles are scattered before the gate, the gate releases them together
when the outage lifts. Jitter removes the part it controls and leaves a residual, 1.042 and 1.083.

This explains why GE dissolves MORE clustering and gains LESS goodput. What costs is the residual,
not the amount removed. Registered as CR-34 P1/P2/P3 in `hopper/batteries/cohort.sh`, running at
full tier with the falsifier that if the jittered GE excess also reaches 1.0 the account is
withdrawn.

**Operational consequence, and it is the one that ties the three levers together.** Randomized
backoff fully solves self-collision on a clean link and only partially on a contested one, because
a contested link re-clusters what the backoff scattered. On a contested link the backoff is not
sufficient by itself and the console-side levers are not redundant with it.

### The window was the bug, not the variance

`tools/bench_fano.py` extended to the window the D1 battery actually used, which was set to the
channel dwell of 120 on the reasoning that that is where the channel's structure lives:

| channel | window | baseline F | recovered | t |
|---|---|---|---|---|
| memoryless | 1 | 0.85 | 0.998 | 376 |
| on-off | 1 | 0.85 | 0.997 | 335 |
| memoryless | 120 | 0.94 | 0.461 | 4.2 |
| on-off | 120 | 9.97 | 1.307 | 3.7 |

Setting the window to the correlation time is exactly backwards. It is the scale at which the
channel's own variance is largest and the statistic's power is least, and it costs a factor of
eighty in t. The published Fano null was read through a window that had almost no power. This is a
fifth member of the genus in `tests/test_gate_helpers.py`: a parameter chosen by an argument about
where the physics lives rather than by measuring where the instrument works.

---

## CR-32 VERDICT. LEWIS ET AL. 2010: THE PREDICTION HOLDS, AND THE MEDIATOR IS SHARPER THAN THE ONE I REGISTERED

Source text obtained from the Internet Archive's copy of the author-hosted PDF (the University of
Pittsburgh URL is dead; `web.archive.org/web/20240423152545/http://www.ischool.pitt.edu/people/
lewis/HF-2010.pdf`). Both registered falsifiers checked against the reported numbers.

### Falsifier 1: NOT FIRED. The prediction is confirmed with the right shape and the right statistics.

Victims found, full-task condition (the operator performs both subtasks):

| robots | victims found | s |
|---|---|---|
| 4 | 4.80 | 1.57 |
| 8 | 7.06 | 2.25 |
| 12 | 4.73 | 1.98 |

`N Robots x Task` interaction, within groups `F(2, 56) = 8.45`, partial eta-squared 0.23,
`p = .001`. Adjusted pairwise: 4 against 8 `p < .001`, 8 against 12 `p = .006`, **4 against 12
`p = .08`, not significant.**

The registered prediction was that the 4-to-8 step and the 8-to-12 step carry opposite signs. They
do. And the third comparison is the one that settles it: **twelve robots is statistically
indistinguishable from four.** That is not a trend continuing, it is a return. An attention account
in which per-robot quality declines as robots compete for a fixed budget predicts monotone decline
from 4; that is refuted on this dataset, not merely unsupported.

### Falsifier 2: PARTIALLY FIRED. The strong reading is withdrawn; a sharper one replaces it.

I registered that if exploration performance "in fact declines with team size" the sufficiency
reading is withdrawn. It does not decline. Area explored in the full-task condition:

| robots | full task | exploration only | paired test |
|---|---|---|---|
| 4 | 129.2 (s 48.5) | 173.8 (s 52.2) | `t(15) = 4.25, p = .024` |
| 8 | 327.6 (s 55.4) | 348.9 (s 73.9) | no difference |
| 12 | 285.8 (s 60) | 377.8 (s 48) | `t(15) = -3.62, p = .001` |

So the abstract's "roughly the same" is true only at 8 robots, and the full-task operator IS
degraded relative to one freed of the other subtask at both 4 and 12. **The strong claim, that the
operator is not degraded at the subtask at all, is withdrawn.**

**What replaces it is better, and it is arithmetic on their own two columns.** From 4 robots to 12,
full-task area explored rises from 129.2 to 285.8, a factor of 2.2. Over the same range victims
found goes 4.80 to 4.73, unchanged. **The fleet more than doubled its productive output and the
mission output did not move.** Whatever the operator lost at twelve robots, it was not enough to
stop the robots covering twice the ground, and none of that extra ground converted. The loss is not
in what the robots did, and not in the operator's ability to keep navigating. It is in the
conversion, which happens one interaction at a time at a shared server.

### The arm that removes the console interaction removes the collapse

Perceptual search, where exploration is automated and the operator handles only detections:

| robots | victims found | s |
|---|---|---|
| 4 | 6.93 | 1.22 |
| 8 | 8.20 | 0.86 |
| 12 | 8.33 | 0.62 |

Monotone, no collapse, `F(1, 28) = 27.4, p < .001` against full task. Removing one class of console
interaction removes the span pathology. That is this paper's admission-control and supervisory arms,
performed on human operators eight years before we ran them, and reported by authors who framed the
result as a question about which subtask to automate rather than about a queue.

The authors' own effect-size comparison points the same way: improvements in perceptual search
contribute more to victims found (partial eta-squared 0.35) than improvements in exploration
contribute to area explored (0.13).

### Status: SHAPE, PRE-REGISTERED

Not `numerical`: the paper reports no interaction or neglect time, so no `n*` is computable for
their setup and none is claimed. Stronger than the `sign only` status Giachetti carries, because
what was predicted was the SHAPE (non-monotone, peak at the interior, endpoints statistically
equal) and it was registered before the source text was read. Their design has three team sizes,
which is the minimum that can show a hump at all, and it shows one.

---

## CR-34 AMENDMENT. THE BENCH POINT FABLE ASKED FOR, AND WHY IT MOVES BOTH PREDICTIONS

Registered before the `cohort` battery is read. `tools/bench_excess.py` measures `arrival_excess` at
its DEPLOYED window of 7 steps against the closed form for the injected process. Over a window of
w steps, `N_t = K * B_t` with `B_t ~ Bernoulli(lambda/K)` gives `K * Binomial(w, lambda/K)`
arrivals, so

    E[k | k >= 1] = lw / (1 - (1 - lambda/K)^w)   and   excess = (1 - e^{-lw}) / (1 - (1-lambda/K)^w)

exactly. Run at the deployed GE geometry (bad dwell 120, stationary bad 0.2, hence good dwell 480),
32 blocks of 1800 steps, at the rates the batteries actually deliver:

| channel | lambda | K | truth | measured | error |
|---|---|---|---|---|---|
| memoryless | 0.070 | 1 | 0.9726 | 0.9796 | +0.7% |
| on-off | 0.070 | 1 | 0.9726 | 1.0261 | +5.5% |
| memoryless | 0.090 | 1 | 0.9672 | 0.9761 | +0.9% |
| on-off | 0.090 | 1 | 0.9672 | 1.0321 | +6.7% |
| memoryless | 0.090 | 2 | 1.6964 | 1.7104 | +0.8% |
| on-off | 0.090 | 2 | 1.6964 | 1.7372 | +2.4% |

**Two findings, and both change what CR-34 may claim.**

**1. On the memoryless channel the estimator is essentially exact** (under 1% at every rate and
cohort size, `t` against truth below 1.3, i.e. not distinguishable from ground truth). Within-channel
contrasts there are trustworthy at face value.

**2. On the on-off channel the estimator reads HIGH even when the source has no cohort at all.**
At K = 1, a perfectly scattered source reads 1.026 to 1.032 at the batteries' rates. **The gate
manufactures apparent clustering.** At the duty cycle I first benched (0.5 rather than the deployed
0.8) the bias reaches +20% to +46%, so the size of this effect is a property of the channel's
geometry and has to be measured at the deployed one, not assumed from another.

**Consequences, stated before the data is seen.**

P1 as registered said the jittered memoryless arm reaches 1.0. **That reference was wrong and is
withdrawn.** A perfectly scattered Bernoulli source reads 0.97, not 1.00, because a binomial count
is slightly under-dispersed against Poisson. The pilot's 1.001 and 1.011 are therefore ABOVE the
scattered reference, not at it, by roughly 0.02 to 0.03. **P1' : the jittered memoryless arm's
excess is within the bench's own error band of the scattered-source reading at its measured rate.**

P2 as registered said the jittered GE arm stays above 1.0 by a gated margin. **The margin must be
taken against the instrument's floor on that channel, not against 1.0.** Pilot values 1.042 and
1.083 against floors of about 1.026 and 1.032 leave true residuals near +0.016 and +0.051, so
roughly half the apparent residual at n = 5 is instrument bias and the n = 5 cell may not survive.
**P2' : the GE residual measured against the bench floor at the arm's own delivered rate is
positive and gated at at least one span.**

**FALSIFIER, unchanged in spirit and sharpened in form: if the GE residual net of the bench floor
is not gated at any span, the two-synchronizer account is withdrawn.**

**What is unaffected either way.** The within-channel paired contrast, `jit` against `fix` on the
same channel at the same mean hold, differences the bias away because it is common to both arms.
Those numbers (-0.094, -0.088 memoryless; -0.173, -0.265 GE) stand as measured. Had the amendment
not been made before the run, the absolute-level claims would have shipped with half their n = 5
residual borrowed from the instrument.

**The general rule this is the second instance of.** A deployed instrument setting is registration
content and owes its own bench point against injected ground truth, at the geometry it is deployed
at. The Fano window was the first instance and it cost a refutation. This one was caught before it
cost anything, which is the only difference.

---

## CR-31 VERDICT. THE FALSIFIER FIRES, AND IT TAKES A HEADLINE WITH IT

Read from the `admitrate` battery in progress (job 9446591); the E0 sections and E2's
`served_per_step` are complete and that is what the registered falsifier needs. Re-verified at
completion below.

### The doctrine sentence is withdrawn

Registered: "On `served_per_step`, admit - refund is negative and gates at n = 8, 10 and 12 on the
clear channel." Measured, rung 0:

| n | admit - refund, served_per_step | rel | t | admit - refund, requests_per_step | rel |
|---|---|---|---|---|---|
| 4 | +0.00087 | +0.9% | 1.2 | +0.00083 | +0.9% |
| 6 | +0.00393 | +3.3% | 4.8 | +0.00618 | +4.8% |
| 8 | +0.00376 | +2.8% | 7.1 | +0.02145 | +12.7% |
| 10 | +0.00336 | +2.3% | 7.5 | +0.04900 | +23.0% |
| 12 | +0.00260 | +1.8% | 13.7 | +0.08378 | +32.4% |

**Admit serves MORE work per step than refund at every span, not less, and never by a gated
margin.** Its request rate meanwhile inflates by a third at twelve assets, gated at t = 76. The
-0.131 goodput "inversion" is denominator inflation in full. Fable's doctrine sentence, "a refusal
without a client-side rate rule is not admission control, it is load acceleration with better
manners", is WITHDRAWN per the registration. Its second clause is literally true, since the offered
load does accelerate by 32%, but the first is false: the console is not overloaded by it. The
METRIC is.

### And the same contamination runs the other way through this paper's third lever

`operator_goodput = n_serviced / n_request`. A refusal inflates the denominator. **An AIMD rate rule
DEFLATES it, which is the entire point of the rule.** So the contamination that made plain admit
look bad makes AIMD look good, and the headline was measured on the contaminated metric.

`aimd - admit`, from the same battery:

| rung | n | served_per_step | requests_per_step | success (from the aimd battery) |
|---|---|---|---|---|
| 0 | 8 | -4.6% | -19.4% | +0.036 |
| 0 | 10 | -4.2% | -31.1% | +0.044, gated |
| 0 | 12 | -4.0% | -40.9% | +0.021 |
| 2 | 8 | -10.4%, gated | | +0.033, gated |
| 2 | 10 | -11.5%, gated | | +0.035, gated |
| 2 | 12 | -12.0%, gated | | +0.023 |

**AIMD does not make the console serve more. It makes it serve LESS**, four percent less on a clear
link and twelve percent less under jamming, both consistently signed at t up to -54. What collapses
is the asking, by forty-one percent at twelve assets.

**The finding survives and its description does not.** Mission success under AIMD still gates
positive at n = 10 clear and n = 8 and 10 jammed. So the honest statement is stronger and more
useful than the one in the manuscript: **the console does measurably less work and the missions go
measurably better.** That is what a rate rule is supposed to do, and stating it as a throughput gain
both misdescribes the mechanism and understates the result, because a lever that improves outcomes
while REDUCING operator load is a different kind of recommendation from one that improves outcomes
by extracting more work.

### Consequence for the manuscript

`operator_goodput` is reported in six places and every contrast between arms whose request rates
differ is now suspect in a known direction. The rule is: a treatment that changes the ASKING must
be read on `served_per_step` as well, and where the two disagree the absolute rate is the finding
and the ratio is a diagnostic of the asking. That is not a new rule; CR-23R established it for
retries. What is new is that it was never applied to the queue policies, which change the asking at
least as much.

---

## CR-35. IS "SERVES LESS, WINS MORE" A MECHANISM OR A STORY I REACHED FOR?

**REGISTERED before the metric is looked at, and registered specifically because I already know
which answer I want.** CR-31 showed the AIMD rule makes the console serve 4% less on a clear link
and 12% less under jamming while mission success still gates positive. I rewrote the manuscript
around "the console is asked forty percent less, does a few percent less work, and wins more
missions." The mechanism I offered in that rewrite is that the rule suppresses requests that were
going to abandon anyway, so the service it forgoes is service that would have been wasted. That is
plausible and unmeasured, which is the condition under which this project has been wrong five times
this week.

**The discriminator.** If the forgone service is doomed service, then under AIMD the ABSOLUTE
abandonment rate falls by more, proportionally, than the absolute service rate does. If it falls by
the same proportion or less, the rule is throttling indiscriminately and the outcome gain has some
other cause, which I would then have to find or else report the gain unexplained.

This needs absolute quantities, not fractions, for exactly the reason CR-31 just established:
`abandon_queue_frac` divides by `n_request`, and the rule's whole effect is on `n_request`. Two new
metrics: `abandoned_per_step` (queue abandonments per step) and `wasted_frac` (queue abandonments
per request SERVED, which is how much doomed work the console carries per unit of completed work).

**PREDICTION.** `aimd - admit` on `abandoned_per_step` is negative, gated, and larger in relative
magnitude than the same contrast on `served_per_step`, at n = 8, 10 and 12 on both rungs.
Equivalently `wasted_frac` falls under AIMD.

**FALSIFIER.** If `abandoned_per_step` falls by the same relative amount as `served_per_step` or
less, or if `wasted_frac` does not fall, the "suppresses doomed work" mechanism is WITHDRAWN. The
manuscript then says the rule reduces console load and improves outcomes, which is measured, and
does NOT say why, which is not. The rewrite's framing survives either way; only its explanatory
clause is at stake.

**Registered honestly about the incentive.** I want this to hold, because it would turn a
correction into a mechanism. That is the reason it is written down before the number is read rather
than after.

---

## CR-36. EVERY GOODPUT CONTRAST IN THE PAPER, RE-READ ON THE ABSOLUTE RATE

CR-31 established that `operator_goodput` is inflatable by any treatment that changes the asking,
and that the paper's queue policies all do. CR-23R established the identical fact for retries and
the rule was never carried across, which is the same failure as the Fano window and the MPE
constant: a rule correctly derived for its first use case and not applied to the second.

`operator_goodput` appears in six places in the manuscript. Three AIMD sites are corrected. The
remainder include the refund-against-blind contrast that carries this paper's FIRST lever, and
refunding changes the asking too.

**No prediction is registered, because this is an audit and not a conjecture.** Every arm pair the
manuscript reports on `operator_goodput` is re-run on `served_per_step`, `requests_per_step`,
`abandoned_per_step` and `success`, at full tier, and the manuscript reports whichever the absolute
rate supports. Where the two agree the goodput number stays and gains a confirmation. Where they
disagree the absolute rate is the finding and the ratio is reported as a diagnostic of the asking.

**The standing rule going forward, which is the durable output of this:** a contrast between arms
whose request rates differ may not be reported on a ratio metric whose denominator is the request
count. It must be read on the rate, or the request rates must first be shown equal.

---

## CR-37. CR-27 P1 RE-RUN, WINDOW DERIVED FROM THE BENCH POWER CURVE AND REGISTERED BLIND

**Status change first.** CR-27 P1 ("within each mean-matched pair the jittered arm has a lower
arrival Fano") was reported REFUTED. It was read at `fano_window = 120`, where `tools/bench_fano.py`
now says the estimator recovers 0.681 of a known injected cohort at `t = 4.7`. A null measured with
an instrument that noisy is not evidence of absence. **P1's status is changed to VOID: not refuted,
not confirmed, instrument underpowered at the registered setting.**

Fable's three salvage tests, applied to that change before making it. The power check was committed
before its answer was known (the bench was written to test the drowning sentence, not to rescue
P1). The new status is undecided, not confirmed. The replacement instrument is benched against
injected ground truth rather than tuned to agree with a preferred answer. And instrument
invalidation is direction-blind: a ledger that has retracted gated positives when a clock broke has
standing to void a null when a window fails its bench.

**D2's result is untouched.** It killed the strong fade-edge pump on goodput evidence, with no Fano
window involved anywhere in it.

### The window, chosen from the curve and not from an argument

`bench_fano` at the deployed GE geometry, lambda 0.09, 32 blocks of 1800 steps, cohort K = 2 raising
the source Fano by exactly 1.000:

| window | memoryless recovered | t | on-off recovered | t |
|---|---|---|---|---|
| 1 | 1.001 | 545 | 0.999 | 508 |
| 4 | 0.976 | 43 | 0.957 | 48 |
| **7** | **0.979** | **29** | **0.936** | **25** |
| 20 | 0.866 | 16 | 0.837 | 16 |
| 60 | 0.856 | 10 | 0.802 | 7.5 |
| 120 | 0.784 | 6.1 | 0.681 | 4.7 |

Monotone in both columns. **The re-run window is 7 steps, one service time**, and the choice is
made on two grounds that agree: the bench retains 0.936 recovery at `t = 25` there, five times the
power of the deployed 120, and it is the mechanism's own timescale rather than the channel's, which
is the doctrine the whole episode established. It is also the window `arrival_excess` is deployed
at, so the two instruments read the same scale and can be compared directly.

Window 1 has more power still and is NOT chosen, because a one-step window measures whether two
requests land on the same tick and the mechanism is about landing inside one service. Choosing the
highest-power setting rather than the mechanistically correct one would be the same error in the
opposite direction.

### PREDICTION, registered before any Fano-at-7 number from the simulator is looked at

P1R. On the bursty link, within each mean-matched pair, the jittered arm has a LOWER arrival Fano
at window 7, gated.

**FALSIFIER.** If no pair shows a gated Fano reduction at window 7 either, P1 moves from VOID to
REFUTED and stays there, with the instrument objection answered rather than outstanding. That is a
worse outcome for the two-synchronizer account than the current VOID, which is the point of running
it.

**Secondary, and the one I actually expect to be informative.** `arrival_excess` at the same window
is the better instrument, because a Fano is a variance and cannot distinguish many small clusters
from few large ones. If the two disagree, the excess is the finding and the Fano is reported as the
weaker statistic that motivated it.

---

## CR-38. WHAT IS THE SOFTWARE LEVER WORTH IN OPERATORS?

The staffing table is the most sponsor-legible object in this paper, and it is built on
`operator_goodput`. At eight assets it reads 17.0 for one blind console, 73.4 for one console with
admission control, and 99.0 for two blind consoles. The natural reading, which the paper does not
currently state and a program office certainly will, is that admission control buys most of a
second operator.

CR-31 makes that reading unsafe in a known direction: `admit` inflates its own denominator by up to
32%, so its column is flattered, while a second console changes nothing about the asking and its
column is not. **The comparison is between an arm whose denominator moved and an arm whose
denominator did not, which is the exact configuration CR-31 showed produces a spurious gap.**

**PREDICTION.** On `served_per_step` and on `success`, both immune to the denominator, the
one-console admission-control arm still sits between one and two blind consoles at n = 8, 10 and 12.
The equivalence survives; only its size changes.

**FALSIFIER.** If on the absolute rate the one-console admit arm falls at or below the one-console
blind arm at those spans, the staffing equivalence is an artifact of the metric and the table is
withdrawn from the paper rather than restated.

**Second prediction, on the lever the correction made interesting.** CR-31 showed the AIMD rule
makes the console serve LESS while winning more missions. So on `served_per_step` the rule should
look WORSE than plain admit while on `success` it looks better, and the staffing question then has
two different answers depending on which is asked. **That is the finding to report if it holds**,
because it is the difference between buying throughput and buying outcomes, and a program that
staffs consoles is buying the second.

**FALSIFIER for the second: if the rule beats plain admit on both metrics, or loses on both, the
"different answers to different questions" framing is dropped and whichever metric it wins on is
simply reported.**

**Why the equivalence is worth stating in operators at all.** The three levers are software. A
sponsor's alternative to software is people, and people are the unit the budget is denominated in.
An equivalence stated in consoles is the only form of this result that can be compared against its
own cost.

### CR-31 addendum: verifying that `served_per_step` means what the verdict assumed

Before building a correction on it, checked that `n_serviced` counts what the argument needs. It
increments only in the branch where the request CAN return inside the requester's patience, so it
counts service whose answer will actually be used. The branch where it cannot increments
`n_abandon_queue` and does NOT increment `n_serviced`, even under `blind`, where the console still
burns the slot via `_claim`. So `served_per_step` is a rate of USEFUL work, not of completions.

Two consequences. The metric is semantically correct for the verdict, not merely arithmetically
immune to the denominator. And the CR-31 result is sharper than first stated: `admit` delivers
**+1.8% more useful work** than `refund` at twelve assets. Both policies free the slot; admit
additionally tells the requester. Telling therefore costs nothing in work done and saves nothing
either. All it changes is WHEN the vehicle comes back, which is the whole of the +32.4% request
inflation and the whole of the apparent goodput collapse.

---

## CR-30 VERDICT (full tier). THE ORACLE ASSUMPTION IS CONSERVATIVE, NOT LOAD-BEARING

Job 9446590, 32 blocks x 64 reps, five droop levels from the shipped model to an operator whose
answers decay all the way to the autonomous baseline at full utilization.

**Falsifier does not fire. Zero of five orderings reverses sign at any droop level**, every cell at
31 or 32 of 32 blocks. The 48-seed pilot is confirmed.

| ordering | droop 0 | droop 1 | change |
|---|---|---|---|
| admit over blind, success | +0.237 | +0.182 | **-23%** |
| refund over blind, success | +0.223 | +0.176 | **-21%** |
| no-retry over rho=4, success | +0.218 | +0.179 | **-18%** |
| admit over blind, goodput | +0.565 | +0.571 | **+1%** |
| supervisory over direct, success | +0.195 | +0.239 | **+23%** |

**The three families move differently and the differences are the mechanism, which is more than the
registration asked for.** A droop degrades the quality of decisions the console DOES serve. So it
erodes the mission value of every policy that works by serving more (all three success orderings
lose a fifth of their value), leaves the congestion effect those policies act on untouched (the
goodput ordering is flat to +1%), and strengthens the case for removing the operator from the loop
entirely (supervisory over direct GROWS by a fifth, one-sided by construction since a droop can only
harm the direct arm, and reported rather than counted).

**The conclusion is therefore that every result in this paper is conservative with respect to the
oracle assumption rather than dependent on it.** That is the stronger of the two things this check
could have established, and it is worth being clear that it was registered as a falsification test
and not as a demonstration: the falsifier was a sign reversal in any one of five cells at any of
five levels, twenty-five chances to fail.

**Caveat carried forward.** The goodput row is an `admit` against `blind` contrast and CR-31 showed
that metric inflatable by anything that changes the asking. Here the contamination runs AGAINST the
conclusion, since `admit` returns a vehicle to autonomy after one round trip rather than after full
patience and therefore asks MORE often, so the +0.565 is measured against an inflated denominator
and the true advantage is larger. `absrate` re-reads it on the absolute rate.

---

## CR-34 VERDICT (partial log, K1/K2 complete). P1 REFUTED, P2 CONFIRMED, AND A CONFOUND I PUT THERE MYSELF

Job 9446609. Judged against the AMENDED predictions, with the instrument's floor at each arm's own
delivered rate. The rate is recovered exactly from the two logged statistics rather than carried as
a third metric: `excess = mult / P(lw)` with `P(lw) = lw/(1 - e^{-lw})`, so `P` is known from the
pair and `lw` follows by bisection.

### P1 is REFUTED

Registered: the jittered memoryless arm's excess is within the bench's error band of the
scattered-source reading. It is not. Above its floor, mean hold 18:

| n | rate | floor | excess | above floor | gate |
|---|---|---|---|---|---|
| 4 | 0.0613 | 0.9752 | 0.9940 | +0.0188 | no |
| 5 | 0.0731 | 0.9717 | 1.0027 | +0.0310 | **yes**, t=24 |
| 6 | 0.0883 | 0.9676 | 1.0087 | +0.0411 | **yes**, t=35 |
| 8 | 0.1231 | 0.9605 | 1.0126 | +0.0521 | **yes**, t=32 |
| 10 | 0.1608 | 0.9557 | 1.0150 | +0.0593 | **yes**, t=52 |

**Randomizing the hold does not fully scatter the stream, even on a link with no burst structure at
all.** Nine of ten cells across both mean holds sit gated above the floor. The account's stronger
half is false and is withdrawn.

### P2 is CONFIRMED, and the discriminating comparison is at matched delivered rate

The GE arm also sits above its floor, +0.019 to +0.080, gated at four of five spans. That alone
proves nothing, since the memoryless arm does too. The comparison that carries the mechanism is
GE against memoryless at the SAME delivered rate, which the mean-18 pair supplies to within 2%:

| n | rate (mem / GE) | residual mem | residual GE | gap |
|---|---|---|---|---|
| 4 | 0.0613 / 0.0621 | +0.0188 | +0.0190 | +0.0002 |
| 5 | 0.0731 / 0.0733 | +0.0310 | +0.0375 | +0.0065 |
| 6 | 0.0883 / 0.0890 | +0.0411 | +0.0511 | +0.0100 |
| 8 | 0.1231 / 0.1207 | +0.0521 | +0.0748 | +0.0227 |
| 10 | 0.1608 / 0.1606 | +0.0593 | +0.0798 | +0.0205 |

**Identical at four assets, and the gap opens monotonically with span.** That is the gate adding
clustering the hold cannot reach, and it is load-dependent: with the console idle there is nothing
for the gate to hold back, and the more backlog there is when an outage lifts the more the gate
releases at once.

### The confound, which is mine and which the battery cannot resolve

The floor is a BERNOULLI scatter reference. The actual source is a superposition of n vehicles on
quasi-periodic decision cycles, which is not Bernoulli and need not read at the Bernoulli reference
even with nothing synchronized. A superposition of renewal processes converges to Poisson only as n
grows, and n here is four to ten.

So the residual that refutes P1 may be the retry cohort, or it may be the standing cadence's own
structure, and this battery cannot tell them apart because **it has no `noretry` arm.** That is a
design error on my part: every arm in K1 and K2 retries, so there is no cell in which the retry
cohort is absent by construction.

**The control is registered as CR-34 P6 and runs before any of this enters the manuscript.** A
`noretry` arm has no retry hold and therefore no retry cohort; whatever excess it shows above the
floor is the standing cadence and the floor's own misspecification together. P1's refutation stands
only if the jittered arms sit above the `noretry` arm, not merely above a Bernoulli closed form.

**FALSIFIER for P6: if `noretry` shows the same excess above the floor as the jittered arms, the
residual is the standing cadence, P1 returns to UNDECIDED, and the two-synchronizer account rests
entirely on the matched-rate GE-minus-memoryless gap above, which does not depend on the floor at
all because the floor is common to both channels at matched rate.**

That last clause is worth stating plainly: **the gap table is floor-free and survives whatever the
control says.** The mechanism is safe; only P1's absolute claim is at risk.

### The metric-selection worry, settled by checking rather than by arguing

Having just corrected a headline that rested on a contaminated metric, the obvious next failure is
over-weighting whichever metric survived. The check is whether the two uncontaminated metrics agree,
and they do, completely. Full stack (`admit` + AIMD) against `blind`:

| rung | n | success (pts) | blue_loss_frac (pts) |
|---|---|---|---|
| clear | 4 | +0.0, null | (null) |
| clear | 6 | +6.2, gated | |
| clear | 8 | **+27.3**, t=20.9 | **-18.4**, t=-25.3 |
| clear | 10 | +19.8 | -16.4 |
| clear | 12 | +12.1 | -11.5 |
| jam | 8 | +11.8 | -9.4 |
| jam | 10 | +16.6 | -12.5 |

Same sign, same shape, same peak span, gated at the same spans, null at the same one. And **success
gives the LARGER number** (+27.3 against -18.4), so leading with it is not a retreat to the
surviving metric: it is leading with the number that is both bigger and more diagnostic. Reporting
both is therefore not having it both ways, it is reporting a result two independent measurements
confirm. Abstract and results now lead with success and carry losses alongside.

The two are genuinely separate measurements and the manuscript says why: `success` thresholds the
assault, `blue_loss_frac` counts the force that does not come back, and both are fractions of what
was FIELDED rather than of what was requested, which is the property that makes them immune.

---

## CR-37 VERDICT. P1R CONFIRMED, AND THE ORIGINAL REFUTATION WAS THE WINDOW IN FULL

Job 9446726, F1/F2 complete. The prediction was registered blind, before any Fano-at-7 number from
the simulator was looked at, with the window taken from the bench power curve.

**Every pair shows a gated Fano reduction on the bursty link. Six of six.**

| pair | n | fix arm's Fano | jit - fix | t | rel |
|---|---|---|---|---|---|
| rho=4 | 5 | 2.174 | -0.770 | -64.8 | -35% |
| rho=4 | 6 | 2.988 | -1.415 | -89.0 | -47% |
| rho=10 | 5 | 1.579 | -0.320 | -27.3 | -20% |
| rho=10 | 6 | 2.887 | -1.532 | -85.0 | -53% |
| rho=18 | 5 | 1.583 | -0.364 | -40.9 | -23% |
| rho=18 | 6 | 2.091 | -0.789 | -52.9 | -38% |

All 32/32 blocks. The memoryless control shows the same thing at four of four pairs, smaller in both
absolute and relative terms (-0.047 to -0.349, -4% to -24%).

**At the deployed window of 120 the largest reduction anywhere was -0.130 and nothing gated. At the
service-time window the smallest is -0.320 and everything gates at |t| above 27.** The refutation
was the window, in full, and nothing else. P1 moves from VOID to **CONFIRMED**.

### What this does to the manuscript's account, which is now on its fourth version

The published narrative reads: the bursty link showed no Fano reduction, the memoryless control did,
therefore the synchronization is among the retrying vehicles rather than between them and the
channel. **The premise is false.** Both links show it, and the bursty link shows MORE, in absolute
terms and relative to its own baseline.

That is not a retreat, because it now agrees with every other instrument:

| instrument | says |
|---|---|
| multiplicity | GE more clustered (+0.19 to +1.05) |
| excess, net of rate | GE more clustered (1.21/1.35 against 1.10/1.10) |
| Fano at w=7 | GE has more to dissolve, and jitter dissolves more of it |
| excess residual at matched rate | GE keeps more after jitter, gap growing with span |

**The account that fits all four.** Deterministic holds create a retry cohort on both links. The
bursty link's gate adds further clustering on top of it, so there is more there to begin with.
Jitter dissolves the part the hold controls, which is larger on the bursty link because more of the
total is cohort. A residual survives on both, larger on the bursty one, and the gap grows with span
because a gate can only release what a backlog gave it to hold.

**The memoryless control is still the informative arm**, but for a different reason than the one
shipped. It does not show that channel coupling is absent. It shows that a retry cohort forms and
matters with no channel structure at all, which is what makes the mechanism a property of the retry
rule rather than of the link, and therefore what makes the recommendation portable.

### The methodological point, now paid for twice

This section's story has been revised four times: fade-edge pump, drowning, born-pre-scattered,
two-synchronizers. Three of the four revisions were forced by instruments, not by physics: a window
with no power, an estimator with a gate-induced bias, and a floor with the wrong reference process.
**Every substantive error in this section came from an instrument setting asserted by an argument
instead of measured against injected ground truth.** The two benches now exist and the rule is
written down. It is worth stating in the paper that the mechanism was found by fixing the
instruments, because a reader deciding whether to trust the account should know which parts were
measured and at what settings.

---

## CR-39. IS THE COHORT MADE OF DIFFERENT VEHICLES? THE ONE CHECK THE MECHANISM CLAIM HAS NEVER HAD

Fable's Round 17, third hardener, and it goes at the load-bearing sentence rather than at a margin.

The manuscript says, in Section~\ref{subsec:band} and again in the Discussion, that the benefit of a
jittered hold is **vehicles desynchronizing from each other**. Every statistic supporting it has been
a count of arrivals per window: Fano, multiplicity, excess. **None of them can tell three vehicles
arriving together from one vehicle arriving three times.** Those are opposite mechanisms with the
same reading, and only the first is one a jittered backoff can address, because there is nothing to
desynchronize a vehicle from itself.

The second is not hypothetical here. At `retry_backoff = 4` inside a `mult_window` of 7, one
vehicle's refused request can come back inside the same window by construction. Fable named it: a
refusal echo train. If the residual we have been calling a retry cohort is mostly that, the
recommendation is still right (jitter still helps) but the reason we give for it is wrong, and the
portability argument, that the mechanism belongs to the retry rule rather than to the link, goes
with it.

`arrival_distinct` counts senders per busy window rather than arrivals, from a bitmask that costs one
integer. `arrival_repeat = multiplicity - distinct` is the self-inflicted part.

**P1. At `retry_backoff = 18`, longer than the window, the fixed-minus-jittered contrast is carried
by `arrival_distinct`: gated, and the same sign as the multiplicity contrast.**
  **FALSIFIER.** If the `arrival_distinct` contrast is ungated at backoff 18 while `arrival_repeat`
  carries the multiplicity contrast, the cohort is one vehicle's echo and not a crowd. The sentence
  "the whole of the benefit that survives the gate is vehicles desynchronizing from each other" is
  then **refuted**, and the mechanism paragraph is rewritten to say so, at whatever cost to the
  Ethernet analogy that currently frames the whole subsection.

**P2. `arrival_repeat_frac` is HIGHER at backoff 4 than at backoff 18, gated.** This is an instrument
check with an answer known in advance from arithmetic: 4 is inside a window of 7 and 18 is not.
  **FALSIFIER.** If it does not fall with backoff, the split is not measuring what its name says and
  P1's reading is void rather than either confirmed or refuted. This is the same discipline the Fano
  window episode should have had and did not.

**P3. The memoryless control shows the same P1 pattern.** If the cohort is cross-vehicle on a link
with no structure, it is cross-vehicle for the reason we claim.
  **FALSIFIER.** A cross-vehicle contrast on the bursty link only would make the effect channel-borne
  after all, which contradicts CR-33's decomposition, and one of the two would have to be withdrawn.

Registered before any number from `hopper/batteries/cohsplit.sh` exists. The split is measured at the
same window and the same arms as CR-37 so nothing but the statistic changes.

---

## CR-40. THE REMAINING GOODPUT SITES, RE-READ ON A METRIC NO POLICY CAN INFLATE

The absrate audit's first half is in and it is worse than the triage assumed. I had reasoned that
`refund` does not tell the requester, so it cannot change the asking. **It changes it anyway, and by
a lot: +20.6% at n=8, +16.1% at n=10, t above 25 in both.** The channel is service, not notification.
Freeing the slot serves more vehicles, a served vehicle completes its round trip and comes back to
ask again, and the denominator moves without anyone being told anything. Every `refund`-versus-
`blind` goodput number in this manuscript is therefore on a moved denominator, which is two more
sites than the triage listed.

The same audit says the underlying claim is in no danger at all, which is the useful half:

| contrast, rung 0 | served/step at n=8 | requests/step at n=8 | reads |
|---|---|---|---|
| refund - blind | **+0.114 (+578%)** | +0.029 (+20.6%) | massive, and survives the ratio |
| admit - refund | +0.004 (+2.8%), never gates | +0.021 (+12.7%) | the notification is not material on service |
| aimd - admit | -0.006 (-4.6%), never gates | -0.037 (-19.4%) | serves less, asks much less |

Read on the absolute rate the three levers separate cleanly and the ordering the Discussion already
recommends gets stronger, not weaker: **discarding expired work is nearly the whole of it**, at a
6.4-fold multiple on service rate by n=16, and the other two are not material on what the console
delivers. That is a better sentence than the one it replaces, and it is the one the sponsor needs,
because it says which increment to fund first in units of work done rather than of ratio moved.

Two goodput sites remain unread. Both are registered here before their run.

**P1. The burst interaction.** `refund - blind` on `served_per_step` is larger on the bursty link
than on the memoryless one at n=8, gated, keeping the sign of the goodput difference in differences.
  **FALSIFIER.** A null or a reversal on `served_per_step` **refutes** "admission control is worth
  more, not less, as the link gets worse." The claim comes out of Section~\ref{subsec:burst} and out
  of the Discussion, and the burst section keeps only its success-metric result.

**P2. The self-collision decomposition.** `jit - fix` on `served_per_step` is positive and gated on
the memoryless link at n=5 and n=6.
  **FALSIFIER.** A null **refutes** the decomposition's magnitudes. The sentence "self-collision is
  worth +X of operator goodput" is then restated on the absolute rate or withdrawn, and if the
  absolute rate is null the mechanism keeps its Fano and multiplicity evidence but loses its console
  cost, which is the part the recommendation rests on.

**P3. The reliance-loop sign flip.** The C2 goodput difference in differences (retry on versus off,
bursty versus memoryless) keeps its sign on `served_per_step`.
  **FALSIFIER.** A reversal **refutes** the sign-flip claim, which is one of the older results and
  currently reads as established.

Retries change the ask by construction, so P2 and P3 are the two where a null is most likely, and
they are registered anyway because that is the point of registering.

---

## CR-34 P4 VERDICT. THE FREE SIGNATURE IS THERE, MONOTONE, AND ITS SECOND HALF WAS NEVER TESTED

Fable's P4: the excess residual should GROW with the channel dwell $L$ and COLLAPSE as $L$ approaches
the service time, because a gate that opens and closes faster than a service cannot hold a cohort
together across one. Job 9446726, section F3, six dwell levels at $n=6$, backoff 18.

| $L$ | fix excess | jit excess | jit - fix | $t$ | residual, jit - 1 |
|---|---|---|---|---|---|
| 7 | 1.2267 | 1.0622 | -0.1645 | -52.3 | +0.0622 |
| 15 | 1.2441 | 1.0707 | -0.1734 | -52.6 | +0.0707 |
| 30 | 1.2685 | 1.0769 | -0.1916 | -51.9 | +0.0769 |
| 60 | 1.2903 | 1.0789 | -0.2114 | -43.6 | +0.0789 |
| 120 | 1.3331 | 1.0828 | -0.2503 | -39.1 | +0.0828 |
| 240 | 1.4190 | 1.0941 | -0.3249 | -30.2 | +0.0941 |

**All three columns are monotone in $L$ across all six levels, at 32 of 32 blocks everywhere.** The
residual grows, the fixed arm's clustering grows, and the amount jitter removes grows. That is the
growth limb of the prediction, registered by someone who had not seen the data, and it lands clean.
It is also the strongest evidence yet that the excess statistic measures a real physical quantity
rather than an artifact, because an artifact has no reason to be monotone in a knob it does not know
about.

**The collapse limb is NOT tested by this sweep and I should not have said it was.** The prediction is
about $L$ shorter than a service, and the sweep's lowest point is $L = 7$, which is exactly the
service window. A dwell equal to the window is the most favorable configuration for producing
multiplicity that exists, since one ON period fills exactly one window; it is the wrong end of the
axis to look for a collapse at. The residual at $L=7$ is +0.0622, and that number is evidence about
neither branch.

**CR-41. The collapse limb, at dwells the prediction actually names.** Extend the sweep to
$L \in \{1, 2, 3, 5\}$, all below one service.
  **P1.** The residual falls monotonically below $L = 7$ and is not gated at $L = 1$.
  **FALSIFIER.** A residual that is flat or still growing below one service **refutes** the gate
  account of the residual outright, and what survives jitter has to be explained by something other
  than the channel holding a cohort together. Fable named two candidates already, refusal echo trains
  and an $lw$-dependent estimator bias, and CR-39 is measuring the first of them.

Status of P4: **growth limb CONFIRMED, collapse limb UNTESTED, extension registered.**

---

## CR-29 VERDICT, AND CR-42: THE CLIFF HAS A CLOSED FORM AND THE MEDIATOR IS ZERO ON THE OTHER PHYSICS

Job 9446589, full tier. Three findings, the third of which is a new registration.

### P1 CONFIRMED, and pricing the wait makes the recommendation stronger rather than cheaper

Fable's objection to CR-28 was that the model prices a wait flat, so "do not re-ask" is cheap advice.
Priced by mobility instead, through a mechanism written two conjectures earlier for something else:

| arm | n=5 | n=6 | n=8 |
|---|---|---|---|
| stop, rho=4 minus no-retry | -0.2554 (-100%) | -0.3726 (-100%) | floor |
| stop, rho=12 minus no-retry | -0.1709 (-67%) | -0.3726 (-100%) | floor |
| stop, rho=21 minus no-retry | -0.0107, null | -0.0640 (-17%) | floor |
| keep, rho=4 minus no-retry | -0.1777 (-50%) | -0.2183 (-40%) | -0.1440 (-24%) |

**No retry arm gates above no-retry anywhere, on either physics.** The falsifier did not fire, and the
damage is roughly twice as large under stop-dead physics: at rho=4 success is exactly zero.
Caveat recorded: at n=8 under stop-dead physics even no-retry reaches 0.0034, so that column is a
floor and carries no information about the contrast.

### P2 CONFIRMED as partial mediation, exactly at the pre-registered limit, and the shape is a cliff

n=6, stop-dead, across the backoff ladder, fraction of each quantity's own range closed:

| backoff | hold | success | hold closed | success closed |
|---|---|---|---|---|
| 2 | 0.8666 | 0.0000 | 0.000 | 0.000 |
| 4 | 0.7966 | 0.0000 | 0.167 | 0.000 |
| 8 | 0.6786 | 0.0000 | 0.449 | 0.000 |
| 12 | 0.5889 | 0.0000 | 0.664 | 0.000 |
| 16 | 0.5181 | 0.0127 | 0.833 | 0.034 |
| 21 | 0.4575 | 0.3086 | 0.978 | 0.828 |
| none | 0.4484 | 0.3726 | 1.000 | 1.000 |

The mediator moves smoothly and monotonically; the outcome does not move at all until the mediator is
two thirds closed, and then jumps. **The pre-registered limit is met exactly**: at rho=21 hold is
97.8% closed and success only 82.8%, so hold fraction is partial and the remainder is unexplained,
which is what the registration said may be claimed and no more.

**The cliff is not a mystery.** `success` is `arrived_frac >= survive_fraction`, and that identity
holds block by block in 32 of 32 blocks in eleven of the twelve P1 cells and 31 of 32 in the twelfth.
The outcome is a threshold on a continuous quantity, and `arrived_frac` is monotone in hold fraction
within every span.

### The mediator is IDENTICALLY ZERO on the physics the paper ships, which changes what P2 can claim

`hold_fraction` is 0.0000 for every keeps-driving arm, correctly: nothing is held when a vehicle with
no answer keeps driving. Yet retrying still costs -0.2183 at rho=4 there. **Time in stall cannot be
the mechanism on the published physics, because there is no stall.** So the recommendation is
over-determined rather than singly caused: under stop-dead physics it is a tempo budget, and under
keeps-driving physics it is the console congestion of Section~\ref{subsec:queue}. Two mechanisms,
same advice. That is a stronger reason to believe the advice than either alone, and it is the honest
way to report the mediation: not "the mechanism is time in stall" but "on the physics where stalling
exists, time in stall is most of it."

### CR-42. THE CLIFF SHOULD BE PREDICTABLE WITH NO FREE PARAMETER

If the damage is a tempo budget, the mission fails when the force cannot cover the route in the time
allowed: $v_{\text{eff}} \, T \, (1 - h) < D$, so the critical hold fraction is
$h^{\star} = 1 - D / (v_{\text{eff}} T)$. Every term is already fixed by the scenario: $D = 5350$~m
(start at 250, goal at 5750, radius 150), $T = 1800$~s, and $v_{\text{eff}}$ is the mean advance rate
of an unheld vehicle, which is a property of terrain and control quality and not of the retry rule.

At $n=6$ the measured collapse sits between $h = 0.4575$ (arrived 0.2504) and $h = 0.5889$
(arrived 0.0001), which brackets $v_{\text{eff}}$ in $[5.48, 7.23]$~m/s against a platform maximum
of 12.0.

**P1. Measured independently on an arm with no holds, $v_{\text{eff}}$ falls inside $[5.48, 7.23]$~m/s.**
  **FALSIFIER.** A measured $v_{\text{eff}}$ outside that interval **refutes** the tempo-budget account
  of the cliff, and the cliff goes back to being an unexplained threshold that the paper reports
  without a mechanism.

**P2. The predicted $h^{\star}$ locates the collapse at every span, not only at $n=6$.** Computing
$h^{\star}$ once from the measured $v_{\text{eff}}$ and comparing it against the measured collapse at
$n = 5$ and $n = 8$ is a two-point out-of-sample test of a zero-parameter prediction.
  **FALSIFIER.** A collapse at a hold fraction that moves with span **refutes** P2, and the account
  becomes span-conditional rather than a budget, since a budget does not know how many vehicles share
  the console.

Registered before $v_{\text{eff}}$ is measured. The measurement is one probe run and takes a minute,
which is precisely why the prediction is written down first.

---

## CR-42 P1 VERDICT: REFUTED. THE FALSIFIER FIRED AND THE BRACKET WAS BUILT WRONG

Measured on 64 seeds with the retry rule off and a clear link, so no vehicle is ever held:

    route D = 5350 m, T = 1800 s, platform max 12.0 m/s
    reach time over 56 of 64 seeds: median 1013 s, mean 1258 s
    v_eff from median reach = 5.28 m/s      -> h* = 0.4372
    v_eff from mean   reach = 4.25 m/s      -> h* = 0.3010
    registered bracket                       [5.48, 7.23]

**Both estimates fall below the registered bracket, so P1 is REFUTED as written.** The tempo-budget
account of the cliff does not survive its own falsifier and I am not going to widen the bracket after
the fact. P2 is void with it, since it was conditioned on P1's $v_{\text{eff}}$.

**Why it failed is worth more than the failure.** The bracket was derived from ARM MEANS: the mean
hold fraction of an arm and the mean arrived fraction of the same arm. Both quantities are per-run,
success is a threshold applied per run, and a threshold does not commute with an average. The budget
$v_{\text{eff}} T (1-h) \ge D$ is a statement about one run's hold fraction and one run's distance
covered. Comparing it against a mean over 2048 runs asks whether the average run is above threshold,
which is a different question from what fraction of runs are, and the two differ by exactly the
amount the distribution is spread. This is the same defect genus as the five already in the ledger:
a construction correct for its first use, an average, carried into a second where a nonlinearity
sits between the quantity and the outcome.

**CR-43. The budget at the level it is a statement about.** Collect per-run pairs of hold fraction
and arrived fraction, not per-arm means, and test the budget where it lives.
  **P1.** Within a single arm, runs sort by hold fraction: those with
  $v_{\text{eff}} T (1-h) \ge D$ arrive and those below it do not, at the $v_{\text{eff}} = 5.28$~m/s
  already measured and with no parameter fitted to these runs.
  **FALSIFIER.** If arrived fraction does not separate at the predicted hold, or separates at a hold
  that has to be fitted, the budget account is **dead** and does not come back. Three registrations on
  one mechanism is the limit; a fourth would be fitting.
  **P2.** The separating hold is the same across spans $n = 5, 6, 8$. A budget does not know how many
  vehicles share a console.
  **FALSIFIER.** A separating hold that moves with span makes it console congestion wearing a budget's
  clothes, and the cliff is reported as a threshold with no closed form.

This is a new registration made after a refutation, not a repair of the refuted one. It carries its
own falsifier and can fail on its own terms, and the refuted version stays refuted in the table.

---

## CR-42 CORRECTION: THE REFUTATION IS VOID, AND I HAVE TO SAY WHY BEFORE SAYING WHAT REPLACES IT

The measurement that fired CR-42 P1's falsifier was wrong in two independent ways, both found while
building the CR-43 probe rather than while defending the result.

**One. The run had no behavior module.** `measure_veff.py` passed `teleop_stop: True` without
`blue_behavior: "teleop"`, so `behavior.py` was never instantiated and the arm was not the physics
the conjecture is about. Median reach time 1013~s. With the module active it is 1387~s.

**Two, and worse, the estimator was wrong even with the right run.** I computed
$v_{\text{eff}} = D / t_{\text{reach}}$ and called it the advance rate of an unheld vehicle. It is
not. $t_{\text{reach}}$ already contains the holds, so that ratio is the NET rate, which is exactly
the left-hand side of the budget rather than its input. The budget is
$v_{\text{eff}} T (1-h) \ge D$, so $v_{\text{eff}} = D / (t_{\text{reach}} (1-h))$, and I had divided
by nothing. **There is no hold-free arm in this model to measure it on**: at rung 0 with the retry
rule off, hold fraction is still 0.34 to 0.40, because a teleoperated vehicle stops whenever it has
no answer, including during an ordinary queue wait. The probe printed that in its own diagnostic and
the diagnostic is what caught it.

Corrected: $v_{\text{eff}} = 5350 / (1387 \times 0.63) = 6.12$~m/s, which is **inside** the registered
bracket $[5.48, 7.23]$.

**P1 is therefore VOID, not confirmed.** The falsifier fired on a defective measurement, so it did
not fire; but I have now seen the corrected number, so I cannot claim a blind confirmation either,
and the CR-37 precedent says an instrument-defective null goes to VOID and gets re-run rather than
being flipped to a positive by whoever spots the defect. The difference from CR-37 is that there I
registered the re-run blind and here the number is already in front of me. **A quantity I measured
after seeing what it needed to be is not evidence, whatever it came out to.**

**What survives as a real test is P2, which I have not looked at.** $v_{\text{eff}}$ is estimated at
$n=6$, and the bracket was read at $n=6$, so any statement about $n=6$ is circular. The out-of-sample
question is whether the SAME $h^{\star} = 1 - D/(v_{\text{eff}} T) = 0.514$ locates the collapse at
$n=5$ and $n=8$, where nothing was fitted.

**CR-43 REVISED, and this is the version that gets run.** Estimate $v_{\text{eff}}$ on rung-0,
retry-off runs at $n=6$ alone. Predict $h^{\star}$ once. Test the per-run budget on retry-on runs at
$n=5$ and $n=8$ only, holding $n=6$ out of the test entirely because it trained the parameter.
  **P1. At $n=5$ and $n=8$, runs with $h < h^{\star}$ arrive and runs with $h \ge h^{\star}$ do not,
  separating within 0.05 of the predicted hold.**
  **FALSIFIER.** A separation more than 0.05 from $h^{\star}$, or no separation at all, kills the
  budget account permanently. This is its third registration and there will not be a fourth.
  **P2. The separating hold does not move with span between $n=5$ and $n=8$.**
  **FALSIFIER.** A separating hold that moves with span makes it console congestion in a budget's
  clothes, and the cliff is reported as a threshold with no closed form.

**The general lesson, which is the fifth of its kind and belongs in the paper.** Every instrument
defect in this project has had the same shape: a quantity computed correctly for one construction and
carried into a second where a term was needed and absent. Here the absent term was $(1-h)$, and it
was absent because I wrote the estimator while thinking about a vehicle that is never held, in a
model where no vehicle is ever not held. The defense that works is not care. It is a diagnostic that
prints the assumption: the probe printed `hold_fraction 0.3586, not a clean arm` sixty-four times
before it printed anything else, and that line is what found both defects.

---

## CR-34 P4 RE-VERDICT: THE GROWTH WAS THE NULL MOVING, AND I HAD ALREADY PUT IT IN THE PAPER

Fable's Round 18 required a bench at sub-window dwells before CR-41 could be read, on the ground
that the dwell is part of the instrument and not only part of the model. Building it overturned a
result I had committed to the manuscript two hours earlier.

`tools/bench_gate.py` computes the EXACT excess of a gated source rather than simulating it, by
carrying the joint law of (chain state, arrivals so far) forward through the window by transfer
matrix. Two things came out, and the second is the one that matters.

**The estimator is unbiased at every dwell from 1 to 240**, |bias| at most 0.0044 against a residual
of about 0.08. Fable's obligation is discharged with a positive answer and CR-41's rows are readable.

**The gate's own excess is neither 1.0 nor constant.** At the deployed rung and rate it runs:

| outage $L$ | 1 | 2 | 3 | 5 | 7 | 15 | 30 | 60 | 120 | 240 |
|---|---|---|---|---|---|---|---|---|---|---|
| true excess | 0.957 | 0.972 | 0.984 | 1.000 | 1.009 | 1.026 | 1.035 | 1.040 | 1.043 | 1.044 |

A gate faster than the window REGULARIZES the stream and pushes the excess BELOW one; slower than
the window it clusters. And it moves as much again with the delivered rate: at $L=240$ the null runs
1.019 at rate 0.06 to 1.064 at rate 0.16, a spread comparable to the whole residual.

**So F3's residual, which I reported as monotone across six dwells and wrote into the manuscript, is
not separable from its own null.** Subtracting the dwell-matched null at the bench's rate gives
0.053, 0.045, 0.042, 0.039, 0.040, 0.050 across $L = 7$ to 240: **flat, not rising.** That subtraction
is itself not admissible, because F3 did not log `arrival_rate` and the null needs it, so the correct
statement is that the reading is **unreadable** rather than that it is flat.

**Status of P4: growth limb WITHDRAWN.** Not refuted, because a refutation would also require the
null; withdrawn, because it was read against a constant that is not constant. The manuscript
paragraph is retracted and replaced with the withdrawal and its reason.

**What survives, and it is worth separating carefully.** Of the three quantities I called monotone:
the fixed arm's crowding rises by 0.157 while its null rises by 0.035, so that one survives the
correction with room to spare; the arm-to-arm gap at a common dwell shares most of its null and is
the most robust of the three; only the residual, which is a level rather than a difference, is
destroyed. **A difference of two arms at one dwell was safe and a level against an assumed constant
was not, which is the general rule and the one I should have applied without being told.**

`dwellow` is cancelled and resubmitted (job 9447711) over the full dwell range 1 to 240 with
`arrival_rate` logged at every point, so the null can be computed per arm instead of assumed. That
run supersedes F3 entirely.

**This is the fifth instance of the genus and the one that got furthest.** Jitter width guard, MPE on
rate metrics, blocks-won on negative effects, `t=inf` on nulls, the Fano window, the goodput
denominator, the missing $(1-h)$ in the tempo budget, and now a burstiness null assumed rather than
computed. The common shape every time: a reference value correct in the setting it was derived for,
carried unexamined into a setting where it is a function rather than a constant. The paper should say
that plainly, because it is the most transferable thing in it.

---

## CR-43 VERDICT: BOTH FALSIFIERS FIRED. THE TEMPO BUDGET IS DEAD AND WHAT KILLED IT IS THE ANSWER

Third and final registration, as declared. 640 runs per span, $v_{\text{eff}} = 6.12$~m/s estimated
at $n=6$ and $n=6$ held out of the test entirely, predicted $h^{\star} = 0.5143$ with nothing fitted.

| span | runs below $h^{\star}$ | arrive | runs at or above | arrive | best separator | miss |
|---|---|---|---|---|---|---|
| $n=5$ | 359 | 0.694 | 281 | 0.278 | 0.5819 | 0.068 |
| $n=8$ | 134 | 0.396 | 506 | 0.000 | 0.4561 | 0.058 |

**P1 FIRED.** Both misses exceed the registered 0.05. **P2 FIRED.** The separating hold moves from
0.582 at five assets to 0.456 at eight, a shift of 0.126, which is two and a half times the tolerance
the prediction allowed for it to be a constant.

**The budget account is dead and does not come back.** Three registrations, and the third was
declared final in advance precisely so that a fourth could not be talked into existence.

**What killed it is the finding.** A tempo budget is a statement about one vehicle and a route: it
knows the distance, the speed, and the clock, and it does not know how many other vehicles share a
console. The separating hold moved with span, and it moved DOWNWARD as span grew, which is the
signature of a shared server and the opposite of what a geometric budget predicts. Under stop-dead
physics, where a purely mechanical tempo story is at its most tempting, the collapse is still the
console.

That is worth more than the budget would have been. The paper's queue mechanism was established on
the published physics, where a vehicle with no answer keeps driving and the damage is congestion. The
obvious objection, and Fable's, is that the model prices waiting too cheaply. Priced by mobility
instead, the damage roughly doubles and the recommendation gets stronger, **and it is still the same
mechanism**: the threshold that governs it tracks span, not distance. Two physics, two apparent
mechanisms, one shared server underneath both.

**Direction of the miss, recorded because it constrains what could rescue a budget-like account.** At
$n=8$ the predicted hold separates almost perfectly in one direction: of 506 runs at or above
$h^{\star}$, exactly zero arrive. The budget's SUFFICIENT half holds, in that a hold above the
predicted value guarantees failure. Its NECESSARY half is what fails: below $h^{\star}$ only 0.396
arrive at $n=8$ against 0.694 at $n=5$, so the geometry is a bound and the console decides everything
inside it. A budget that predicts an upper limit and not the operating point is not a closed form for
the cliff, which is what was claimed and what is now withdrawn.

---

## CR-44. THE JITTER HEADLINE, READ ON EVERY METRIC THAT IS NOT INFLATABLE

The cohort battery (job 9446609) carries `served_per_step` alongside `operator_goodput` for the exact
arms the manuscript's jitter paragraph quotes. Together with `desync` D1's success sweep this is the
first complete uncontaminated read of that recommendation, and it is much narrower than what ships.

The manuscript says jitter at a matched mean hold "is worth \jiGeGoodWideFive{} of operator goodput
at five assets and \jiGeGoodWideSix{} at six." `\Wide` is the width-18 pair. What the uncontaminated
metrics say about that same pair:

| metric | $n=4$ | $n=5$ | $n=6$ | $n=8$ | $n=10$ |
|---|---|---|---|---|---|
| served/step, memoryless | +0.0028 | +0.0044 | +0.0058 | +0.0065 | +0.0025 |
| relative | +6.8% | +9.9% | +11.7% | +14.2% | +12.6% |
| $t$ | 9.8 | 13.4 | 13.8 | 21.7 | 5.8 |
| gates against capacity? | no | no | no | no | no |
| served/step, bursty | +0.0046 | +0.0054 | +0.0026 | +0.0032 | +0.0021 |
| gates against capacity? | no | no | no | no | no |
| mission success | | **+0.028** | -0.006 | | |
| $t$, blocks | | 2.35, 24/32 | -0.39, 14/32 | | |

**Nothing gates on the absolute service rate at any span on either channel.** The largest effect
anywhere is +0.0065 decisions per step, against a capacity floor of $0.06 \times 0.15 = 0.009$. The
effects are statistically unambiguous, $t$ up to 21.7 at 32 of 32 blocks, and every one of them is
under four percent of what one console can deliver.

**On mission success the recommendation holds at one span and only one.** Of the six mean-matched
cells in D1, two gate: width 4 at $n=5$ (+0.022, $t=2.06$, 20/32) and width 18 at $n=5$ (+0.028,
$t=2.35$, 24/32). At $n=6$ two of the three pairs go the other way, ungated.

**This is the capacity-anchored floor, adopted three hours ago on adversarial review, taking down a
result of ours at its first real test.** That is what a materiality floor is for and I am not going
to make an exception for our own paragraph. But the choice of floor decides this outcome, so the
choice is registered rather than exercised quietly:

**P1. The claim that survives is: at the span where the queue is near its threshold, a randomized
hold is worth about three points of mission success over a fixed hold of the same mean, and it is
not measurable on what the console delivers.**
  **FALSIFIER.** If CR-40's G2 section shows a gated `served_per_step` gain for the jit-fix pair at
  any span against the capacity floor, this narrowing is wrong and the fuller claim comes back.

**P2. The relative reading is worth reporting next to the absolute one and is not a substitute for
it.** A 7 to 27 percent rise in delivered service at a cost of one random draw is a real engineering
fact even when the absolute quantity is small, and suppressing it because the console is already
broken would be the mirror image of the error the floor was adopted to prevent.

**What does not change.** The Fano and multiplicity evidence for the mechanism is unaffected, because
those are arm-to-arm differences at a common configuration rather than levels against a floor, and
CR-37 confirmed the reduction in six of six pairs. The mechanism is real and well measured. What is
now in question is its size at the console, which is a different claim and was reported through a
metric that could not carry it.

---

## CR-34 P6 VERDICT: THE FALSIFIER FIRED, AND IT RETIRES THE WHOLE RESIDUAL ARGUMENT

Job 9446872. The control I omitted from CR-34 and registered afterwards, and it settles two rounds of
argument about which closed-form floor to use by making the question unnecessary.

**`arrival_excess` levels, both channels, backoff 18:**

| span | memoryless: noretry | jit18 | fix18 | bursty: noretry | jit18 | fix18 |
|---|---|---|---|---|---|---|
| 4 | 1.0057 | 0.9940 | 1.0522 | 1.0494 | 1.0430 | 1.1318 |
| 5 | 1.0122 | 1.0027 | 1.0814 | 1.0642 | 1.0645 | 1.1936 |
| 6 | 1.0165 | 1.0087 | 1.1162 | 1.0829 | 1.0828 | 1.3331 |
| 8 | 1.0194 | 1.0126 | 1.2217 | 1.1208 | 1.1178 | 2.1935 |
| 10 | 1.0209 | 1.0150 | 1.9165 | 1.1456 | 1.1400 | 2.9300 |

**`jit18 - noretry` is null at every span on both channels.** On the bursty link it is essentially
exactly zero: +0.0004 to -0.0064, $|t|$ at most 1.79, and 14 to 21 of 32 blocks, which is a coin
flip. On the memoryless link the jittered arm is slightly BELOW the no-retry arm.

**`fix18 - noretry` is gated almost everywhere and grows superlinearly with span:** +4.6, +6.8, +9.8,
+19.9, +87.7 percent on the memoryless link and +7.9, +12.2, +23.1, +95.7, +155.8 percent on the
bursty one, at $t$ from 21 to 96 with 32 of 32 blocks throughout.

**P6's falsifier fired.** It asked whether `noretry` shows the same excess above the floor as the
jittered arms. It shows MORE of it on the memoryless link and the same on the bursty one.

### What this retracts, and it is a lot

**CR-34 P1 is retracted.** P1 found the memoryless jittered arm sitting gated above its Bernoulli
floor and called that a refutation of the "jitter scatters everything" reading. The finding was
correct and the reference was wrong. Against a measured control rather than a closed form, the
jittered arm sits at or below a fleet that never retries at all. Fable and I spent Rounds 16 and 17
arguing which of three closed-form floors was right; the answer is none of them, and the argument was
avoidable by running the control I had omitted, which is why it was registered the moment I noticed.

**The residual apparatus goes with it.** There is no residual retry cohort surviving jitter. Every
statement in the ledger about "the part jitter cannot reach," including the CR-34 P2 gap that grows
with span, is a statement about the difference between two closed-form references and not about the
fleet.

### What replaces it is stronger and simpler

**A deterministic hold creates a retry cohort whose crowding grows superlinearly with span, and a
randomized hold of the same mean removes it completely.** At ten assets on a bursty link the fixed
hold's arrival crowding is 156 percent above a fleet that never retries; the jittered hold is within
half a percent of that fleet. Randomizing the backoff makes retrying free as far as the console's
arrival pattern is concerned, at every span and on both channels.

That is the sentence the section should have been carrying, and it needed one control to say.

### A note on the staggered arm, which was not the point of this battery

`noretry_stag` sits BELOW `noretry` at every span, 0.973 to 0.996 on the memoryless link against
1.006 to 1.021. Synchronized starting phases produce measurable crowding even with the retry loop
open, which is the initial-condition effect Section~\ref{subsec:band}'s fold band is about, now
visible on the arrival statistic rather than only on the outcome. Not registered, so it is recorded
as an observation and not a result.

---

## CR-39 VERDICT: THE COHORT IS ENTIRELY CROSS-VEHICLE, AND I DECLINE ONE REGISTERED INFERENCE

Job 9447167. P1 and P3 confirmed decisively, P2 refuted, and the P2 refutation is the interesting
part because I am not going to apply the consequence I registered for it.

**P1 CONFIRMED.** `fix18 - jit18` on `arrival_distinct`, the count of distinct SENDERS per busy
window rather than of arrivals:

| | $n=5$ | $n=6$ |
|---|---|---|
| bursty | +0.171 (+12.5%), $t=31.7$ | +0.338 (+23.3%), $t=42.3$ |
| memoryless | +0.096 (+7.5%), $t=33.0$ | +0.141 (+10.4%), $t=37.7$ |

All 32 of 32 blocks. **P3 CONFIRMED**: the memoryless control shows the same pattern, so the cohort
is cross-vehicle on a link with no structure at all.

**P2 REFUTED, and the inference it licensed is declined.** P2 predicted `arrival_repeat_frac` would
be higher at backoff 4 than at 18, and registered that a flat result means "the split is not
measuring what its name says and P1's reading is void." It is flat. It is **exactly zero in all
sixteen cells**. I am not voiding P1, and the reason has to be stated plainly enough that a reader
can overrule me.

*The prediction was built on my arithmetic error.* I reasoned that a backoff of 4 is inside a window
of 7 so a vehicle can re-ask within one window. It cannot. A refusal has to travel back before the
backoff even starts: one-way latency 4, service 6.67, latency 4 again, then the hold. The earliest
re-ask is 18.7 steps at backoff 4 and 32.7 at backoff 18, against a window of 7. **A repeat inside
one window is physically impossible at every backoff in this battery**, so the quantity P2 predicted
would vary cannot vary, and its being zero is a confirmation of the physics rather than a symptom of
a broken counter.

*And the instrument passes a strictly stronger check than the one P2 proposed.* `arrival_distinct` is
computed from a bitmask popcount and `arrival_multiplicity` from an independent increment counter.
They agree **to machine precision in all sixteen cells**, which is exactly what two correct
implementations must produce when no vehicle repeats and is a coincidence no broken counter
delivers.

**This is the only place in the ledger where a registered inference is declined, and it is flagged as
such** so it can be judged rather than absorbed. The rule I take from it, and it is a real cost: a
falsifier is only as good as the arithmetic behind its premise, and mine had an unstated assumption
(that the backoff is the whole cycle) that the model's own latency contradicts. **Registering a
falsifier does not protect against being wrong about what the model can do**, and the protection
against that is deriving the predicted quantity's range before predicting its direction.

### What P1 buys the manuscript

`arrival_repeat` is identically zero, so `arrival_distinct` equals `arrival_multiplicity`
everywhere, which means **every multiplicity result in this paper was already a distinct-sender
result** and none of them needs restating. What changes is that the mechanism sentence now has direct
evidence instead of an assumption: none of the crowding a fixed hold produces is a vehicle colliding
with itself, so "the benefit is vehicles desynchronizing from each other" is measured rather than
inferred. Together with CR-34 P6, the picture is complete: a fixed hold crowds the console with a
cohort of DIFFERENT vehicles that grows superlinearly with span, and a randomized hold of the same
mean takes that crowding back to the level of a fleet that never retries.

---

## CR-45. THE GLOBAL SENSITIVITY ANALYSIS THE DISCUSSION PROMISES, RUN AS A TEST RATHER THAN A SURVEY

The Discussion names a global sensitivity analysis over the operator parameters and the comms ladder
as the cheapest available hardening. Run the usual way it produces a bar chart of which knob matters,
which is a description and not a claim, and this project does not report descriptions as results.

There is a sharper version available here because the collapse threshold has a closed form:

$$n^{\star} = \frac{c\,(P + \tau + 1)\,\mu}{d}, \qquad d = (1 - p_{\text{drop}})^2 .$$

**Run the identical Saltelli design twice, once on the simulator and once on the closed form, and
compare the index vectors.** Same sample points, same ranges, no elasticity approximation and no
appeal to local derivatives. If the simulator's variance decomposition matches the equation's, that
is independent validation of the mechanism at a level the point check in
Section~\ref{subsec:validation} cannot reach: it says the equation is right about how the threshold
RESPONDS, not merely about where it sits at one operating point. If they diverge, the divergence
localizes what the equation omits, by parameter.

**Response variable.** The empirical collapse span, measured per parameter draw by sweeping the span
and locating where `served_per_step` falls below half its own maximum. The closed form predicts
$n^{\star}$ directly, so both sides produce the same quantity in the same units.

**Ranges**, chosen to keep $n^{\star}$ inside a span grid the sweep can resolve and to cover the
ladder the paper actually reports: $\mu \in [0.10, 0.22]$, $P \in [12, 30]$, $\tau \in [14, 30]$,
$p_{\text{drop}} \in [0, 0.25]$.

**P1. The two first-order index vectors agree: identical rank order, and every parameter's index
within 0.10 of the closed form's.**
  **FALSIFIER.** Any rank inversion, or any index differing by more than 0.10, means the simulator's
  threshold has a sensitivity structure the equation does not capture. Equation~\ref{eq:nstar} would
  then be reported as locally accurate at the operating point rather than as the mechanism, which is
  a substantially weaker claim than the one the paper currently makes, and the divergent parameter is
  named in the text.

**P2. Total-order indices exceed first-order by less than 0.10 for every parameter, in the simulator
as in the closed form.** The equation is a product of separable terms, so it has one interaction
(the $\mu$ against $P + \tau + 1$ product) and no others.
  **FALSIFIER.** A total-minus-first gap above 0.10 present in the simulator and absent in the closed
  form localizes an interaction the equation omits. It is reported as a named limitation rather than
  folded into the average.

**Registered before the design is drawn.** The closed form's own indices are not computed until the
simulator's are, so neither can be tuned toward the other. Battery `sobol.sh`.

---

## CR-39 P2 RECLASSIFIED: **VOID-UNREACHABLE**, WITH THE FOUR FIELDS THE CATEGORY REQUIRES

Adversarial review endorsed the decline and rejected my derivation, correctly. I had written the
refusal turnaround as latency, service, latency, then the hold. **There is no service in the refusal
path**, and the hold is policy-specific. `c2.py` line 592:

    hold = min(2 * lat, op.patience) if op.queue_policy == "admit" else op.patience

**Field 1, constants-based computation.** Cycle from a refusal to the next delivered request, against
a measurement window of 7:

| policy | hold | at rung 1, $\rho=4$ | at rung 3, $\rho=4$ | reachable? |
|---|---|---|---|---|
| blind, refund | $P$ | $20 + 4 = 24$ | $24$ | no, at any latency |
| admit | $\min(2\lambda, P)$ | $2 + 4 = 6$ | $8 + 4 = 12$ | **yes at rung 1** |

So the quantity is unreachable in **this battery**, which ran `blind` at rung 3, and reachable in
**this model**. My original claim overstated the scope, and the corrected statement is narrower.

**Field 2, instrument coherence.** `arrival_distinct` (bitmask popcount) and `arrival_multiplicity`
(independent increment counter) agree to machine precision in all sixteen cells, which two correct
implementations must produce when nothing repeats and no broken counter delivers.

**Field 3, positive control, RUN and PASSED.** Twelve cells across three policies, two rungs, two
backoffs:

    blind  rung 1/3, rho 4/18 : cycle 24 or 38, repeat_frac 0.00000   (4 cells)
    refund rung 1/3, rho 4/18 : cycle 24 or 38, repeat_frac 0.00000   (4 cells)
    admit  rung 3, rho 4/18   : cycle 12 or 26, repeat_frac 0.00000   (2 cells)
    admit  rung 1, rho 18     : cycle 20,       repeat_frac 0.00000   (1 cell)
    admit  rung 1, rho 4      : cycle  6,       repeat_frac 0.01671   **counter live**

**The counter is zero in every one of the eleven cells the arithmetic forbids and nonzero in the one
it permits.** The metric is not an assert-style invariant and needs no reclassification: it is a live
instrument whose value is zero for a reason.

**Field 4, infection scope.** P2's void touches nothing else. No other claim in the ledger reads
`arrival_repeat`, and P1 and P3 rest on `arrival_distinct`, which varies over four orders of $t$.

**Conversion clause, checked.** The clause converts a void to a retroactive FIRED if the positive
control shows the antecedent was reachable in the original battery. `cohsplit` ran `blind` at rung 3,
where the cycle is 24 against a window of 7. **Not reachable. The void stands**, and it stands on a
computation I got wrong once and had corrected for me, which is why the category carries the
requirement to publish the computation rather than the conclusion.

---

## CR-40 VERDICT: TWO CONFIRMED ON THE CLEAN METRIC, ONE FALSIFIER FIRED WHERE I EXPECTED IT

Job 9447205. The three goodput sites re-read on `served_per_step`, with `requests_per_step` logged
alongside so the contamination is visible rather than assumed.

### P1 CONFIRMED, and the contamination ran AGAINST the claim

`refund - blind` on delivered service, by span:

| span | memoryless | bursty | difference in differences | $t$ |
|---|---|---|---|---|
| 5 | +0.0021 | +0.0046 | +0.0026 | 3.9, null |
| 6 | +0.0037 | +0.0110 | +0.0073 | 10.1, null |
| 8 | +0.0181 | +0.0435 | **+0.0254** | 31.4, GATED |
| 10 | +0.0562 | +0.0816 | **+0.0255** | 49.9, GATED |

"Admission control is worth more, not less, as the link gets worse" survives on the metric no policy
can inflate, at **two** spans where the goodput reading established it at one. And the denominator
moved in the direction that was HIDING the effect: requests rose +7.9% on the bursty link against
+4.9% on the memoryless one at ten assets, so the ratio penalized the bursty arm more and understated
its advantage. **The contaminated metric was making our own claim look smaller than it is**, which is
worth recording because the previous two denominator findings both ran the other way and it would be
easy to start assuming the bias has a direction.

### P2's FALSIFIER FIRED, confirming independently what the cohort battery already forced

`jit - fix` on delivered service: +0.0044 and +0.0058 memoryless, +0.0054 and +0.0026 bursty, at
$n=5,6$. None clears the capacity floor of 0.009. The registered consequence, that the self-collision
decomposition's magnitudes are restated on the absolute rate or withdrawn, was already applied when
the cohort battery showed the same thing; this is an independent confirmation of it on the exact arms
the decomposition used. The mechanism keeps its Fano, multiplicity and distinct-sender evidence and
does not get a console cost.

### P3 CONFIRMED, and the sign flip is now literal

The reliance-loop result was that burstiness HELPS a queue with the loop open, because a dropped
request is one the operator never has to work, and HARMS it with the loop closed, because the
vehicles that abandoned together come back together. On delivered service the levels themselves flip:

| rung | GE minus memoryless, loop OPEN | loop CLOSED | DiD | $t$ |
|---|---|---|---|---|
| 1 | **+0.0026** | **-0.0181** | -0.0207 | -19.9 |
| 2 | **+0.0047** | **-0.0271** | -0.0318 | -33.8 |
| 3 | **+0.0040** | **-0.0183** | -0.0223 | -33.3 |

All 32 of 32, all gated. This is a stronger statement than the goodput version supported: **the same
channel that helps a console serving assets which give up for good hurts one serving assets that come
back**, and the crossing is in the delivered rate itself rather than in a difference of differences.

### Net effect of the whole goodput audit, across CR-31, CR-36 and CR-40

Five sites audited. Two claims survived and got larger (admission control's absolute gain, the burst
interaction), one survived unchanged and sharper (the reliance-loop flip), one was refuted and
retracted (notification's share), one was narrowed to a single span (jitter's console value). The
metric was wrong in both directions and the direction was not predictable from the treatment, which
is the reason the fix is a gate rule rather than a habit of checking.

---

## CR-41 VERDICT: FALSIFIER FIRED, AND IT COMPLETES THE MECHANISM RATHER THAN DAMAGING IT

Job 9447711, ten dwells from 1 to 240 with `arrival_rate` logged, so each arm is scored against the
transfer-matrix null computed at **its own dwell and its own delivered rate**. This is the first
reading in the project that satisfies the `NULL_ARGS` rule rather than assuming a constant.

| outage $L$ | fix excess | its null | fix residual | jit excess | its null | **jit residual** | fix - jit | $t$ |
|---|---|---|---|---|---|---|---|---|
| 1 | 1.1666 | 0.9645 | +0.2021 | 1.0241 | 0.9644 | **+0.0597** | +0.1425 | 51.3 |
| 2 | 1.1819 | 0.9760 | +0.2058 | 1.0310 | 0.9759 | **+0.0551** | +0.1508 | 38.0 |
| 3 | 1.1926 | 0.9852 | +0.2074 | 1.0400 | 0.9851 | **+0.0549** | +0.1526 | 50.9 |
| 5 | 1.2147 | 0.9974 | +0.2173 | 1.0531 | 0.9974 | **+0.0558** | +0.1615 | 53.3 |
| 7 | 1.2267 | 1.0047 | +0.2221 | 1.0622 | 1.0046 | **+0.0576** | +0.1645 | 52.3 |
| 15 | 1.2441 | 1.0172 | +0.2268 | 1.0707 | 1.0171 | **+0.0536** | +0.1734 | 52.6 |
| 30 | 1.2685 | 1.0235 | +0.2450 | 1.0769 | 1.0234 | **+0.0535** | +0.1916 | 51.9 |
| 60 | 1.2903 | 1.0270 | +0.2633 | 1.0789 | 1.0277 | **+0.0512** | +0.2114 | 43.6 |
| 120 | 1.3331 | 1.0297 | +0.3034 | 1.0828 | 1.0296 | **+0.0533** | +0.2503 | 39.1 |
| 240 | 1.4190 | 1.0312 | +0.3878 | 1.0941 | 1.0314 | **+0.0627** | +0.3249 | 30.2 |

**P1's falsifier fired.** The jittered arm's residual does not fall below one service. It is FLAT:
0.0512 to 0.0627 across a **240-fold range of dwell**, with no trend in either direction. The gate
account of the residual is refuted, as registered.

**And that is the answer rather than a loss, because CR-34 P6 already told us what the flat value
is.** At $n=6$ on GE-120 the no-retry arm's excess is 1.0829 against a null of 1.0296, a residual of
+0.0533. The jittered arm at the same point is +0.0532. **The flat residual is the no-retry baseline,
to four decimal places.** It was never a retry cohort, which is why no channel property predicts it.

**Fable's P4 was right about the mechanism and wrong about which quantity carries it.** The dwell
does hold a larger cohort together, and the growth is there, monotone across all ten dwells: the
**fixed** arm's residual runs +0.2021 to +0.3878 and the fix-minus-jit gap runs +0.1425 to +0.3249,
rising at every one of nine steps. A longer fade produces more crowding for a fixed hold and none at
all for a randomized one.

### The complete statement, now instrumented end to end

1. A gated channel contributes crowding of its own, computable in closed form from its dwell and
   the delivered rate, running 0.964 to 1.031 over this sweep. Not a fleet property.
2. A fleet with the reliance loop open sits +0.053 above that, at every dwell. Not a channel
   property: it does not move over a 240-fold dwell range.
3. A fixed hold adds a retry cohort on top, and **that** term is what grows with the fade, from
   +0.15 to +0.32 above the jittered arm.
4. A randomized hold of the same mean adds nothing: it returns the fleet to line 2 exactly.

Four terms, three of them measured against references that are computed or paired rather than
assumed, and the one that used to be reported as a single "residual" was lines 2 and 3 added
together with line 1 subtracted wrong. **Every earlier disagreement in this thread, mine and the
reviewer's, was a disagreement about which of these four things the word residual meant.**

**Outstanding:** the battery has no in-battery `noretry` arm, so line 2's identity with the no-retry
baseline is established across batteries at one point rather than at every dwell. That is a one-arm
addition and it is the last thing this mechanism needs.

---

## CR-46. QUEUE ORDERING IS WORTH EXACTLY THE DISPERSION IN PATIENCE, AND THE STANDARD RULE IS BACKWARDS

Registered 2026-08-22, before any run. The model's own docstring carries the assumption this
conjecture attacks, which is the cleanest possible provenance for it:

> Ordering cannot change how MANY requests the operator serves. Every requester carries the same
> patience and a request's completion time is fixed at arrival, so reordering two feasible requests
> only swaps which vehicle is served.

That is a statement about a homogeneous fleet, not about queues, and the manuscript currently reads
the triage null as though it were about queues: "reordering a queue whose clients all carry the same
patience changes which vehicle is helped, never how many." The clause is right there in the sentence
and nothing in the paper tests it. It is also false of exactly the fleets this sponsor cares about.
An air vehicle orbiting a target has a long window before its request goes stale; a ground vehicle
halted in contact has a short one; a mixed formation is the whole point of the program.

**Two literatures give opposite prescriptions for this queue, and they cannot both be right here.**

- The **cmu/theta rule** \citep{atar2010cmutheta}: in an overloaded many-server queue with
  abandonment, serve the class with the largest $c_k \mu_k / \theta_k$. With equal decision value
  and equal service time that is the class with the smallest abandonment rate, so **serve the MOST
  patient first** and let the impatient abandon, because a class that empties itself needs no
  server.
- **Deadline scheduling** (Moore's algorithm for minimizing late jobs; earliest-deadline-first):
  **serve the LEAST patient first**, because among feasible jobs the greedy earliest-deadline order
  maximizes the number that meet their deadlines.

The rules differ because they assume different information. cmu/theta is derived where the server
observes an abandonment HAZARD and cannot see any individual deadline; EDF where the deadline is
known at arrival. **A console running admission control has already assumed the second**, because
`wait <= patience` is exactly the test that the requester's own deadline is visible. So this model
should sit in the deadline regime, and the standard queueing prescription should be the wrong one
for a supervisory console. If that is right it is a requirement, not a curiosity: **a request
message must carry the requester's time-to-autonomy, and the console must sort on it.**

EDF also has a known failure mode that this model should reproduce. Earliest-deadline-first is
optimal for an underloaded system and can be arbitrarily bad for an overloaded one, because it
spends the server on the job nearest to missing, which under overload is the job most likely to miss
anyway. `blind` IS the overloaded regime in this paper's language, since the console spends slots on
work whose answer will be discarded. So the prediction is not "sort by deadline" but **"discard,
then sort by deadline,"** which is the same ordering the Discussion already recommends for a
different reason.

### The manipulation

`patience_spread` assigns per-vehicle patience deterministically and symmetrically about the mean:
vehicle $j$ of $m$ gets $P + s(2j/(m-1) - 1)$, floored at one step. No RNG is drawn, the fleet mean
is exactly $P$ in every replication, and at $s = 0$ the vector is constant, so every deadline
discipline is a stable sort on a constant key and returns the identity permutation. **The published
path is reproduced exactly rather than approximately, and each arm is its own control at its own
zero.** Because $n^{\star} = c(P + \tau + 1)\mu/d$ is LINEAR in patience, a symmetric spread at held
mean leaves the collapse span where it was, so this is a pure second-moment manipulation.

Sweep $s \in \{0, 3, 6, 9, 12, 16\}$ at $P = 20$, service time $1/\mu = 6.67$. The minimum patience
runs 20, 17, 14, 11, 8, 4. **The last level crosses a physical floor**: a vehicle with patience 4
cannot be served on any link at any load, since one service alone takes 6.67 steps. That level is in
the sweep on purpose, as the overload limb, and `patience_min` is logged so the crossing is read off
the run rather than asserted.

### Predictions, each with the falsifier written before the run

**P1. The zero is an identity, not a null.** At $s = 0$, `edf`, `patient_first` and `fcfs` return
bit-identical metrics.
  **FALSIFIER.** Any difference at all means the ordering arm moves something besides the order
  (the RNG assignment is the known candidate, which is what `random` exists to control), and the
  whole battery is void until it is found.

**P2. Ordering becomes a lever, and its size scales with dispersion.** Under `admit`, `edf - fcfs`
on `served_per_step` is positive and gated at the collapse span, and rises monotonically in $s$
across the serviceable levels $s \le 12$.
  **FALSIFIER.** A null at $s = 12$ **refutes** "ordering is worth exactly the dispersion" and
  restores the manuscript's unconditional null. Non-monotonicity across the serviceable ladder
  refutes the scaling claim while leaving the existence claim standing.

**P3. The standard rule is backwards for a console.** `patient_first - fcfs` on `served_per_step` is
NEGATIVE and gated at the cells where `edf` is positive.
  **FALSIFIER.** `patient_first` at or above `fcfs` **refutes** the claim that a console with
  admission control sits in the deadline regime, and the two literatures are then not in conflict on
  this model, which would itself be worth reporting.

**P4. Discard first, then sort: EDF is second to admission and not a substitute for it.**
`edf - fcfs` under `blind` is SMALLER than `edf - fcfs` under `admit` at the same cell.
  **FALSIFIER.** EDF worth as much or more under `blind` **refutes** the ordering of the
  recommendation, and the deadline rule would then be a standalone lever rather than a follow-on.

**P5. The overload limb.** At $s = 16$, where the shortest-patience vehicle is unserviceable on any
link, `edf - fcfs` under `blind` falls relative to its $s = 12$ value.
  **FALSIFIER.** A monotone rise straight through the unserviceable level **refutes** the account
  that EDF's advantage comes from meeting deadlines rather than from some other property of sorting
  on patience, since a deadline nobody can meet should not be worth prioritizing.

**P6 (instrument). The mean is what sets the threshold.** `fcfs` at $s = 12$ minus `fcfs` at $s = 0$
on `served_per_step` is null.
  **FALSIFIER.** A gated move in the `fcfs` arm alone means dispersion changes the operating point
  itself, and P2's contrast is then mixing an ordering effect with a threshold shift. Every other
  prediction here would have to be re-read against the moved baseline.

Metrics logged: `served_per_step` (the gate), `success`, `operator_goodput` (recorded and NOT gated
on, because the disciplines change the asking), `patience_mean`, `patience_sd`, `patience_min` (the
arm printing its own assumption), `abandon_queue_frac`.

---

## CR-46 VERDICT: VOID-UNREACHABLE. THE MODEL COMMITS AT ARRIVAL, SO THERE IS NO QUEUE TO ORDER

Filed as instance two of the category CR-39 P2 opened. The four fields:

1. **What was registered.** Six predictions about queue discipline under patience dispersion.
2. **Why it is unreachable.** `queue_model = "reserve"`, the published model, decides a request's
   fate at ARRIVAL: it reads the console's free time, computes the reply, and either books the slot
   or refuses. Nothing ever waits anywhere it could be reordered, so a discipline can only permute
   requests that arrive on the same step.
3. **The measurement, not the argument.** At `mult_window = 1`, the two regimes do not overlap:

   | $n$ | $\tau$ | $E[k \mid k \ge 1]$ | $P(\ge 2)$ | served/step | utilization |
   |---|---|---|---|---|---|
   | 6 | 30 | 1.108 | 0.069 | 0.1107 | 0.712 |
   | 8 | 30 | 1.130 | 0.083 | 0.1354 | 0.885 |
   | 8 | 12 | 1.159 | 0.128 | 0.1438 | 0.944 |
   | 12 | 12 | 1.307 | 0.247 | 0.1519 | 0.999 |
   | 16 | 12 | 1.466 | 0.348 | 0.1519 | 0.999 |

   Where the console has slack, same-step contention is 7 to 13 percent of busy steps. Where
   contention is common, served/step is 0.1519 against a capacity of 0.15 and no order can change
   the count.
4. **The positive-control obligation.** `queue_model = "buffer"`, built and gated below. CR-46's
   predictions are re-registered against it as CR-46 v2, and the reserve-model null rides inside
   that battery as its in-battery negative control rather than being run alone.

**Infection scope.** One manuscript sentence, which explained the triage null with an argument from
queueing that is wrong on its own terms: under a common deadline first-come-first-served already IS
earliest-deadline-first, the order that maximizes deadlines met, so a worse order strands earlier
arrivals and serves FEWER \citep{barrer1957ordered}. The claim has moved to the instruments block
and the conclusion now reads that ordering was not testable at this fidelity.

---

## CR-47. A CONSOLE THAT CANNOT DETECT ABANDONMENT CAN STILL WORK ITS QUEUE NEWEST-FIRST

**Provenance, stated first because it changes how this reads.** CR-46's registration was written
blind and its battery was never run at tier. Building the positive control it obligated produced
this, and I saw the numbers before writing the conjecture. Everything below is therefore a
CONFIRMATION registration plus four extensions whose answers I do not have, and the confirmation
limb is labelled as such in the ledger rather than presented as a prediction.

**What the smoke test showed**, `queue_model = "buffer"`, clear link, `blind`, 32 replications:

| $n$ | oldest-first served/step | newest-first | \texttt{admit}, oldest-first | stale share, oldest-first |
|---|---|---|---|---|
| 6 | 0.0994 | 0.1037 | 0.1190 | 0.00 |
| 8 | 0.0387 | 0.1189 | 0.1363 | 0.22 |
| 10 | 0.0065 | 0.1323 | 0.1418 | 0.72 |
| 12 | 0.0032 | 0.1389 | 0.1466 | 0.62 |
| 16 | 0.0023 | 0.1459 | 0.1489 | 0.44 |

A blind console working its backlog newest-first recovers 98 percent of what admission control buys,
at sixteen assets, **without knowing any deadline at all**. That is the part that matters for a
program. Every `refund` and `admit` number in this paper is conditional on the request format
carrying the requester's time-to-autonomy; the paper says so. Newest-first needs a stack and nothing
else, so it is the lever available to a console whose message format cannot be changed.

The mechanism is the paper's own. Under overload, oldest-first serves the request most likely to
have expired: at ten assets 72 percent of the operator's work goes to requests whose requester gave
up and asked again. Newest-first serves the freshest, which is the one most likely to still be
waited on. This is old: Barrer's pair of 1957 papers is the original statement that with impatient
customers the service ORDER changes how many are lost, not merely which \citep{barrer1957ordered,
barrer1957indifferent}. It is new here only in where it sits, on a supervisory console whose clients
are vehicles rather than callers, and in what it substitutes for.

Note that `patient_first` degenerates to newest-first when patience is uniform, because the deadline
is arrival plus patience. The same arm therefore reads as last-come-first-served in the homogeneous
fleet and as longest-deadline-first in the mixed one, which is why one arm answers both questions.

**P1 (confirmation, at tier).** Under `buffer` and `blind` on a clear link, `patient_first - fcfs`
on `served_per_step` is positive and gated at $n \ge 8$, at 32 blocks of 64.
  **FALSIFIER.** A null at tier retracts the whole conjecture and the smoke test is recorded as
  underpowered. Nothing else in the paper depends on it.

**P2 (the mission metric, genuinely open).** The same contrast on `success` is positive and gated at
$n \ge 8$. The smoke test's $|t|$ never exceeded 1.72 at one block, so this is not known.
  **FALSIFIER.** A null on `success` **narrows the claim to the console's throughput**, and the
  recommendation ships as a queue-management result rather than a mission result.

**P3 (the crossover, genuinely open).** The advantage is absent or reversed below the collapse span:
at $n = 6$ the smoke test has newest-first WORSE on success by 0.062. The prediction is that the
sign of `patient_first - fcfs` on `success` is negative at $n \le 6$ and positive at $n \ge 8$.
  **FALSIFIER.** A uniform sign across the sweep refutes the account that this is an overload
  discipline, and the effect would then need a different mechanism.

**P4 (substitution, genuinely open).** Under `admit`, newest-first is WORSE than oldest-first,
because admission control removes the overload that makes newest-first correct and first-come is
then already earliest-deadline. Registered as: `patient_first - fcfs` under `admit` is negative and
gated at $n \ge 8$.
  **FALSIFIER.** Newest-first at or above oldest-first under `admit` refutes the substitution and
  the two levers would compose rather than trade off, which is a different and better
  recommendation.

**P5 (the reliance loop, genuinely open).** The advantage survives with retries on, which is the
condition that produces the fold band. The retry loop feeds the backlog and newest-first starves the
oldest requests, so a retrying vehicle could re-enter at the head forever.
  **FALSIFIER.** A null or reversal with `retry_prob = 1` scopes the recommendation to fleets that
  do not re-ask, which is a serious limit and has to be stated in the same sentence as the claim.

**P6 (the cost, genuinely open).** Newest-first starves the tail. The backlog under `blind` grows to
a mean of 82.9 pending at twelve assets against 68.5 for oldest-first. Registered: mean backlog under
newest-first is HIGHER than under oldest-first at every span, and the fraction of requests never
served at all is higher.
  **FALSIFIER.** A backlog no larger under newest-first would mean the discipline is not doing what
  the account says, and the mechanism would need re-reading.

**The instrument gate, which blocks all six.** `queue_model = "buffer"` is a new service model and
nothing may be read from it until it reproduces the old one where theory says it must. With
deterministic service and no cancellation a request's completion time is fixed at booking, so under
`refund` and `admit`, where the console never commits beyond what it can serve, buffer and reserve
must agree.
  **GATE.** `buffer - reserve` on `served_per_step` under `refund` and under `admit`, `fcfs`,
  across the span sweep, at tier, must not gate anywhere.
  **FALSIFIER.** A gated difference means the buffer's dispatch is not reproducing the schedule and
  every CR-47 number is void until it is found.
  **Recorded in advance, because it is a real difference and not a defect:** under `blind` the two
  models must NOT agree, because reserve books doomed work at an ever-receding free time and
  over-commits past the end of the mission, while buffer holds it in a backlog. The smoke test has
  reserve's booking clock at 2273 on an 1800-step mission. `blind` is therefore excluded from the
  gate and the exclusion is stated here rather than discovered later.

---

## CR-35 VERDICT: CONFIRMED. THE SERVICE THE RATE RULE GIVES UP IS SERVICE THAT WAS GOING TO BE WASTED

Job 9446698, sections A0 and A3. The rule's finding had survived the denominator correction as an
outcome gain with no mechanism, which is a story. The account on offer was that the forgone service
was doomed service, and it is testable on two absolute rates from the same runs.

`aimd - admit`, clear link:

| $n$ | served/step | abandoned/step | exchange rate |
|---|---|---|---|
| 6 | -5.1% | -36.8% | 8 |
| 8 | -4.6% | -58.2%, GATED | 5 |
| 10 | -4.2% | -65.6%, GATED | 12 |
| 12 | -4.0% | -69.9%, GATED | 22 |
| 16 | -2.7% | -73.2%, GATED | 63 |

**Abandonment falls faster than service in 5 of 6 spans on the clear link and 6 of 7 under jamming.**
At sixteen assets the rule removes 63 abandoned requests for every one unit of service it costs the
console. That is the mechanism, and it is a ratio of two absolute rates rather than of a rate to its
own moving denominator.

**The second limb of the registered falsifier is unreadable, not failed.** It named `wasted_frac`,
whose denominator is the request count, and the rule moves the request count by construction: it
reads -68.6% at twelve assets on a denominator that has moved -40.9%. The gate refuses the metric.
`abandoned_per_step` carries the same question with no denominator, and it is what the verdict rests
on. Recorded here rather than quietly substituted.

**One cell short of the registration.** The prediction said gated at $n = 8, 10, 12$ on both rungs.
At rung 3, $n = 8$, abandonment falls 33.2% but the absolute effect is 0.0072, below the capacity
floor of 0.009. Five of six registered cells, and the relative comparison holds at all six.

---

## CR-41 LINE TWO CLOSED, AND THE TAIL SAYS SOMETHING THE MEAN COULD NOT

Job 9448457. Two results.

**Line two of the four-term decomposition is established at every dwell, not one.** `jit18 - noretry`
on `arrival_excess` gates at 0 of 10 fade lengths and never differs by more than 1.1%. The registered
falsifier, a gated gap at any dwell, did not fire. The jittered fleet IS at the no-retry baseline
across a 240-fold range of fade length.

**And the tail statistic adversarial review asked for turns out to carry a finding.** Against the
same control, on the fixed-hold arm:

| statistic | shortest fade | longest fade | growth | gated |
|---|---|---|---|---|
| windows with two or more senders | +0.0364 (+14%) | +0.0499 (+16%) | 1.4x | 10/10 |
| windows with three or more | +0.0658 (+112%) | +0.1517 (+190%) | 2.3x | 10/10 |
| mean excess senders | +0.1327 (+13%) | +0.3278 (+30%) | 2.5x | 10/10 |

**A longer fade does not produce more collisions at the console. It produces deeper ones.** The
two-or-more share is nearly flat across a 240-fold range while the three-or-more share more than
doubles, and the mean excess grows by the same factor as the deep tail rather than as the shallow
one. A mean could not have separated these, which is exactly why the statistic was requested. The
operational content is that the vehicles at the back of a larger cohort are the ones whose patience
expires while they wait, so the fade's cost is concentrated rather than spread.

---

## CR-38 VERDICT: THE STAFFING EQUIVALENCE SURVIVES THE CLEAN METRICS, SPLITS, AND VALIDATES THE $c$-SCALING

Job 9446740. Three findings, one of them not registered.

### P1 CONFIRMED, and the equivalence now has two numbers instead of an impression

The table read 17.0, 73.4 and 99.0 percent goodput for one blind console, one with admission
control, and two blind, and a program office reads that as "admission control buys most of a second
operator." The admit column's denominator moved by up to a third and the two-console column's did
not, so the reading was unsafe in a known direction. On the two metrics no policy inflates, at eight
assets:

| | one blind | one, admit | two blind | admit's share of a console |
|---|---|---|---|---|
| served/step | 0.0197 | 0.1377 | 0.2094 | **62%** |
| success | 56.3% | 80.0% | 86.9% | **77%** |

At twelve the two shares are 64% and 86%. The falsifier, the admit arm falling to or below the blind
arm on the absolute rate, did not come close to firing.

**The gap between the two percentages is the finding, not either number.** The software is worth
less in throughput than in outcomes, because what it removes is service that was going to be
discarded, and a program staffing consoles is buying the second.

### P2 CONFIRMED at every span: two questions, two answers

`aimd` is BELOW plain `admit` on `served_per_step` at every span and ABOVE it on `success` at every
span from six up. That is the registered "different answers to different questions" shape and it
holds without exception.

Stacking: at ten and twelve assets, one console running admission control plus the vehicle rate rule
is not distinguishable from two consoles running neither (-0.6 and +0.5 points of success, $t$ =
-0.72 and +0.92, 32 blocks). Reported as an equivalence we cannot distinguish at this power rather
than as an equality.

### Unregistered, and the strongest thing in the battery: the $c$-scaling of Equation nstar

The battery runs one, two and three consoles across the same span sweep, so the collapse span's
linear scaling in consoles is testable with no free parameter. On `served_per_step`, clear link:

| consoles | predicted $n^{\star}$ | delivered rate collapses between |
|---|---|---|
| 1 | 6.5 | 6 and 8 |
| 2 | 12.9 | 12 and 16 |
| 3 | 19.4 | not by 16 |

Three consoles, three brackets, each containing its own prediction. The manuscript already reported
this on `operator_goodput`; the brackets do not move on the denominator-free metric, which matters
because the console count is the one knob in this paper about which the equation makes a prediction
it was not derived from.

**CR-47 P7 (registered before the run, and it is the adversarial test of the recommendation).**
Newest-first on an unbounded backlog never has to account for the requests it starves, and a real
console's queue is bounded. `queue_capacity` bounds it and drops the OLDEST pending request on
overflow, which is the one purge a console can perform on its own receive clock without the
requester's deadline travelling in the message. That purge is exactly what first-come-first-served
needs and exactly what newest-first does not, since newest-first was never going to reach those
requests.
  **PREDICTION.** The newest-first advantage NARROWS monotonically as the bound tightens, and at a
  bound of one or two requests it is null.
  **FALSIFIER, and this is the one that would change the recommendation.** If a bounded
  first-come-first-served queue reaches newest-first's delivered rate, the finding is **"bound your
  backlog," not "invert it,"** and the paper reports the bound as the lever, with newest-first as
  one way of achieving what the bound achieves. If instead the advantage survives at every bound,
  newest-first is the lever and the bound is a detail.
  Registered with the ordering it implies either way: both are software, both need less information
  than admission control, and the question is only which of the two a console should be told to do.

---

## CR-47 P7 VERDICT: THE FALSIFIER FIRED. THE FINDING IS "BOUND YOUR BACKLOG," NOT "INVERT IT"

Registered as the adversarial test of the newest-first recommendation, and it did its job. Clear
link, `blind`, `buffer`, 32 replications, delivered service:

| $n$ | bound | oldest-first | newest-first | gap |
|---|---|---|---|---|
| 8 | none | 0.0387 | 0.1189 | +0.0801 |
| 8 | 8 | 0.0462 | 0.1217 | +0.0755 |
| 8 | 4 | 0.0715 | 0.1271 | +0.0556 |
| 8 | 2 | **0.1328** | 0.1259 | **-0.0069** |
| 12 | none | 0.0032 | 0.1389 | +0.1357 |
| 12 | 2 | **0.1472** | 0.1428 | **-0.0044** |
| 16 | none | 0.0023 | 0.1459 | +0.1423 |
| 16 | 2 | **0.1481** | 0.1465 | **-0.0016** |

**A two-deep oldest-first queue reaches and slightly passes an unbounded newest-first one, at every
span tested.** At a bound of one they are identical by construction, because a one-slot queue has no
order. The registered consequence applies as written: the paper reports the bound as the lever and
newest-first as one way of achieving what the bound achieves.

The comparison that matters is against the lever the paper already has. At twelve assets a two-deep
blind queue delivers 0.1472 per step against 0.1466 for full admission control on an unbounded one.
**A console that holds two requests performs like a console that knows every requester's deadline,
and it needs no information about the requester at all.**

---

## CR-48. THE CONSOLE HAS BUFFERBLOAT, AND THE RIGHT BUFFER SIZE IS ALREADY DERIVED IN THIS PAPER

**Provenance.** P7 above was seen before this was written. P1 is therefore a confirmation limb and
labelled as one. P2 through P4 are registered before their runs and P3 and P4 are the reason the
conjecture is worth having, because they are parameter-free predictions at operating points nobody
has looked at.

The failure has a name and it is not ours. A buffer large enough to hold work past the point where
anyone still wants it is bufferbloat \citep{gettys2012bufferbloat}, and the fix is to size or age the
queue rather than to maximize it \citep{nichols2012codel}. This paper has already cited the other
three members of the same family, Floyd and Fall on congestion signals, Jacobson on congestion
control, Metcalfe on backoff. The console is the fourth.

**And the right size is already in this paper, derived for something else.** A request that joins a
buffer already holding $k-1$ others, with one more in service, is answered at
$2\ell + (k+1)/\mu$ after it was sent, so it makes its deadline only while
$(k+1)/\mu \le P - 2\ell$, giving
$$k^{\star} = \lfloor (P - 2\ell)\,\mu \rfloor - 1 .$$
A backlog bounded at $k^{\star}$ holds exactly the requests that can still be answered in time and no
others. The expression is already in `c2.py`, where it was written to say which arrival cohorts are
free, and it was never used as a design rule.

**Correction, recorded because it changes the predictions below.** The first version of this
registration wrote $k^{\star} = \lfloor (P-2\ell)\mu \rfloor$ and predicted 3 on a clear link. That
forgot the request already in service, which every arrival must also wait through. The clear-link
smoke run had been read when the error was found and its argmax was 2, not 3; the C3 arm and every
patience and service-rate arm below were UNREAD, and are unread now. The corrected rule gives 2 on a
clear link and 0 at C3.

Two implementation consequences fell out of the same correction and are recorded with it. A capacity
of zero is a meaningful setting, "serve only what arrives to a free console", so it cannot also be
the unbounded sentinel; that is $-1$ now. And the bound applies to what has ARRIVED at the console,
not to what is in flight toward it, or a capacity of zero would mean "serve nothing" on any link
with latency.

**P1 (confirmation).** At rung 0 the argmax of delivered service over the capacity ladder is
$k^{\star} = 2$, at tier.
  **FALSIFIER.** An argmax outside $\{1, 2\}$ refutes the closed form as a sizing rule at the one
  operating point where it has been looked at, and the bound ships as a tuned parameter, which is a
  much weaker result.

**P2 (open).** At C3, where $k^{\star} = 0$, the argmax is 0 or 1. No arm at this rung has been read.
  **FALSIFIER.** An argmax above 1 at C3 refutes the latency term of the rule.

**P3 (open, and the strongest test available).** Raising patience to 30 and 45 moves $k^{\star}$ to 3
and 5, and the measured argmax follows, on a clear link. Nothing about these operating points has
been looked at.
  **FALSIFIER.** An argmax that does not move with patience refutes the rule outright: the bound
  would then be a property of the queue's own dynamics rather than of the requester's deadline, and
  the recommendation becomes "bound it at two" with no derivation behind it.

**P4 (open).** Halving the service rate to $\mu = 0.075$ takes $k^{\star}$ to 0, and doubling it to
0.30 raises $k^{\star}$ to 5.
  **FALSIFIER.** As P3.

**P5 (the requirements ladder, which is what a sponsor buys).** Ordered by what the console must
know, the levers are: bound the backlog (a counter), work it newest-first (a stack), refuse on the
requester's deadline (a field in the message format). Registered claim: on delivered service at the
collapse span, the first is not worse than the third.
  **FALSIFIER.** The bound falling below admission control by a gated margin puts the message-format
  change back at the front of the requirements list, which is the expensive recommendation.

**P1 VERDICT: HELD.** 32 replications a point, local, `served_per_step`, blind console, capacity
ladder $\{-1, 0, 1, 2, 3, 4, 6\}$ at rung 0:

    n= 8  c0=0.0864 c1=0.1243 c2=0.1280 c3=0.0920 c4=0.0587 c6=0.0452 c-1=0.0387  argmax 2
    n=12  c0=0.1072 c1=0.1424 c2=0.1432 c3=0.1098 c4=0.0700 c6=0.0157 c-1=0.0032  argmax 2
    n=16  c0=0.1168 c1=0.1459 c2=0.1478 c3=0.1316 c4=0.1033 c6=0.0328 c-1=0.0023  argmax 2

$k^{\star} = 2$ at 3 of 3 spans, and the curve is single-peaked in capacity at all three. The size
of the effect is the part worth carrying: at $n = 16$ the derived bound delivers 64 times the
service of the unbounded buffer the console has today, and the whole gain is one integer in a
configuration file. Registered caveat, kept: 1 and 2 are within noise of each other at any sample
size a unit test can afford (0.1279 against 0.1275, standard error 0.004, at 12 seeds), so the
fixture in `tests/test_c2.py` asserts the $\{1,2\}$ plateau against its outside neighbours and
leaves the separation to the battery.

**P2 VERDICT: HELD AS REGISTERED, AND THE POINT PREDICTION IS OFF BY ONE.** At C3, same protocol:

    n= 8  c0=0.0568 c1=0.0699 c2=0.0533 c3=0.0439 c4=0.0383 c6=0.0361 c-1=0.0372  argmax 1
    n=12  c0=0.0741 c1=0.0840 c2=0.0446 c3=0.0217 c4=0.0139 c6=0.0136 c-1=0.0039  argmax 1
    n=16  c0=0.0841 c1=0.0945 c2=0.0476 c3=0.0181 c4=0.0068 c6=0.0025 c-1=0.0009  argmax 1

The registered band was $\{0, 1\}$ and the falsifier was an argmax above 1, so P2 is not refuted.
But the rule's point prediction is 0 and the measurement is 1 at 3 of 3 spans, which is a
one-directional miss and not noise. That is a finding about the derivation, and it is CR-49.

## CR-49. THE BUFFER RULE USED A MEAN WHERE THE DEADLINE TEST IS A PROBABILITY

**Provenance.** Written after both rungs of CR-48 P1 and P2 were read, and before any patience or
service-rate arm was read. The two points that motivated it are therefore not evidence for it. The
three prospective tests below are.

**The defect.** The derivation in CR-48 asks whether a request's MEAN wait fits inside its deadline:
$(k+1)/\mu \le P - 2\ell$. But the wait of a request admitted behind $k$ others, with exponential
service, is $\mathrm{Erlang}(k+1, \mu)$, and the deadline test is not about a mean, it is about the
probability that one draw lands under a fixed number. The Erlang is right-skewed, so its mean sits
above its median, and a rule that tests the mean rejects admissions that would in fact make their
deadline more often than not. The mean-fits rule under-sizes the buffer, and it under-sizes it by
more the larger the fractional part it throws away.

Replacing the mean with the median makes the criterion match the test. A request at depth $k$ makes
its deadline with probability $\Pr[\mathrm{Erlang}(k+1,\mu) \le D] = \Pr[\mathrm{Poisson}(\mu D) \ge
k+1]$, which is at least one half exactly while $k+1$ is at or below the median, so with
$\lambda = (P - 2\ell)\mu$,
$$k^{\star} = \operatorname{median}\bigl(\mathrm{Poisson}(\lambda)\bigr) - 1
  \;=\; \lfloor \lambda + 1/3 \rfloor - 1 ,$$
the closed form on the right being Choi's median approximation, which agrees with the exact median
at all ten operating points in this battery. The correction is one term. It is the same derivation
with the right order statistic in it.

**Why this is a mechanism and not a curve fit.** The two rules differ only when
$\mathrm{frac}(\lambda) \ge 2/3$, so the refinement predicts WHERE the offset appears, not just that
one exists. At rung 0, $\lambda = 3.00$ exactly, the fraction discarded is zero, and both rules say
2: measured 2. At C3, $\lambda = 1.80$, the mean-fits rule discards 0.8 of a service, and the two
rules split 0 against 1: measured 1. Every prediction below follows from $\lambda$ alone with
nothing fitted.

**P1 (the discriminating arms, all unread).** On a clear link at $n = 12$, sweeping patience, the
measured argmax equals median-fits and not mean-fits at the three points where they disagree:

| $P$ | 12 | 20 | 25 | 27 | 30 | 34 | 38 | 45 |
|---|---|---|---|---|---|---|---|---|
| $\lambda$ | 1.80 | 3.00 | 3.75 | 4.05 | 4.50 | 5.10 | 5.70 | 6.75 |
| mean-fits | 0 | 2 | 2 | 3 | 3 | 4 | 4 | 5 |
| median-fits | **1** | 2 | **3** | 3 | 3 | 4 | **5** | **6** |

  **FALSIFIER.** The argmax matching mean-fits at any of $P \in \{25, 38, 45\}$ refutes the
  refinement at that point, and matching it at two of the three retracts CR-49 and restores the
  published floor rule. ($P = 12$ is a confirmation limb: it is the same $\lambda = 1.8$ as the C3
  rung already read, reached by shortening the deadline instead of lengthening the link, so it tests
  only that the rule depends on $\lambda$ and not on how $\lambda$ was assembled.)

**P2 (the controls, which fail both rules at once).** At $P \in \{20, 27, 30, 34\}$ the two rules
agree, and the measured argmax equals the agreed value.
  **FALSIFIER.** A miss at two or more controls says the argmax is not a function of $\lambda$ at
  all, and both rules go, not just the older one. This limb is why the sweep carries eight patience
  values rather than the three that discriminate.

**P3 (the service-rate leg, a second route to $\lambda$).** Both rules agree at $\mu = 0.075$
($\lambda = 1.50$, both 0) and at $\mu = 0.30$ ($\lambda = 6.00$, both 5), so this leg discriminates
nothing between them and tests only that $\mu$ enters through $\lambda$.
  **FALSIFIER.** As P2.

**What it costs the recommendation if it holds.** Nothing, and that is the point. The sponsor-facing
sentence is unchanged in form, "bound the console's backlog at $\lfloor(P - 2\ell)\mu + 1/3\rfloor -
1$", and unchanged in value at the published operating point, where both rules say 2. It changes on
degraded links and short deadlines, which is where the console is under the most pressure and where
the older rule would have told an operator to hold nothing at all.

**CR-49 CORRECTION, WRITTEN THE SAME DAY AND BEFORE ANY OF ITS ARMS RETURNED. The premise was
false and the conclusion survived it, which is the order that should make a reader most suspicious.**

`c2.py` line 565 and line 819 both read `svc = 1.0 / op.service_rate`. Service in this console is
DETERMINISTIC. The queue is M/D/1, not M/M/1. So the wait behind $k$ requests is not
$\mathrm{Erlang}(k+1,\mu)$, its mean equals its median, and the Erlang-skew argument above does not
explain the observed $+1$ at C3 or anything else. The paper already states the $M/D/1$ limitation in
its own limitations paragraph. I derived against the textbook queue instead of against the one in
the source file, which is the instrument-defect genus this paper has now caught four times: a
convention correctly derived for its first use case, carried silently into a second where it does
not hold. This is the first instance where the carrier was a piece of theory rather than a piece of
code, and the first where the defect was mine and found within the hour.

**The mechanism, redone against the deterministic server.** With deterministic service the only
randomness in a marginal admission's wait is where in the current service cycle it happens to
arrive. A request standing at position $j$ in the waiting line, $j = 1$ next up, is answered at
$2\ell + r + j/\mu$ after issue, where $r$ is the residual of the request in service. Under load
$r\mu$ is close to uniform on $(0,1)$, so with $\lambda = (P - 2\ell)\mu$ the marginal admission at
depth $j$ makes its deadline with probability
$$\Pr[\text{useful at depth } j] = \operatorname{clamp}(\lambda - j,\, 0,\, 1),$$
a straight line falling from one to zero across a single unit of $\lambda$, not a Poisson tail.
(Written $\lambda - j + 1$ in the first version of this paragraph and caught in review the same day.
The $k^{\star}$ below was derived from the correct line and is unaffected; the displayed line as
first written would have given $\lfloor \lambda + 1/2 \rfloor$ and missed both measured points, so
the error was in the exposition and not in the result, which is the only reason it is a correction
and not a retraction.) Admitting while that probability is at least one half gives
$$k^{\star} = \lfloor \lambda + 1/2 \rfloor - 1 ,$$
which also reproduces both measured points. Two different wrong-or-right mechanisms fitting the same
two points is exactly the situation in which two points are worth nothing, and it is why the
prospective arms matter more than they did an hour ago.

**What the running battery can and cannot settle.** The floor rule and both corrections split at
$P \in \{12, 25, 38, 45\}$, so Hopper job 9448688 still adjudicates the registered P1. But the two
corrections split only when $\mathrm{frac}(\lambda) \in [1/2, 2/3)$, and the sweep's single such
point, $P = 30$ with $\lambda = 4.50$, puts the deterministic rule on an exact boundary where it
predicts nothing. The battery therefore CANNOT separate the two mechanisms. That is a design gap,
recorded here rather than discovered later.

**P4 (new, and the reason this correction is not just an erratum).** The gap is closed outside
SandTable. `tools/queue_kstar.py` is a second, independent implementation of the console queue,
written from the model description rather than from `c2.py`, carrying no terrain, sensing, combat,
or vehicle state. It costs 0.09 seconds a run, so $\lambda$ can be swept on a grid fine enough to
locate the STEPS in $k^{\star}$ directly, and the three rules predict steps in three different
places: at integer $\lambda$ (floor), at $\lambda \equiv 2/3$ (Erlang), at $\lambda \equiv 1/2$
(deterministic). Registered claim: on a grid of step 0.1 from $\lambda = 1.3$ to 7.9, the measured
steps land at the half-integers.
  **FALSIFIER.** Steps at the integers restore the published rule and retract both corrections.
  Steps at $\lambda \equiv 2/3$ would mean the deterministic derivation is wrong in a way I cannot
  currently explain, since the server demonstrably does not draw its service times.
  **PREREGISTERED AGREEMENT CHECK, which is the point of writing a second implementation at all.**
  The queue-only model already reproduces SandTable's two measured argmaxes exactly, 2 at
  $\lambda = 3.0$ and 1 at $\lambda = 1.8$, at both $n = 8$ and $n = 16$. Any disagreement between
  the two implementations at the operating points the battery returns is a bug in one of them and
  is to be reported as such, not averaged.

**P5 (open, and worth more than the sizing rule if it holds).** Bounding the buffer and dropping the
OLDEST arrival means that under load the head is evicted repeatedly, so the console picks up work far
fresher than "the request that has waited $k$ services". In the saturated limit a drop-oldest
first-come-first-served queue should therefore behave like a newest-first one. If that is right it
merges CR-47 P7, where a two-deep oldest-first queue reached an unbounded newest-first one, into this
conjecture as one mechanism rather than two coincidences, and it means the depth-$j$ analysis above
describes a line the marginal request never actually stands in.
  **FALSIFIER.** Bounded first-come-first-served and unbounded newest-first separating by a gated
  margin in the queue-only model at high load leaves them as two mechanisms, and the merge is off.

**CR-45 VERDICT: HELD, at the sample size that was the point of rerunning it.** Job 9448646, Saltelli
design, 3072 parameter draws, 8 seeds and 13 spans each, 319488 missions, against the closed form
estimated at `--n-eq 65536` rather than at the simulator's own sample size, which was the instrument
defect that made the first run unreadable.

| parameter | $S_1$ sim | $S_1$ eq | $S_T$ sim | $S_T$ eq |
|---|---|---|---|---|
| service_rate | 0.443 | 0.456 | 0.462 | 0.480 |
| comms_p_drop | 0.294 | 0.270 | 0.307 | 0.290 |
| patience | 0.176 | 0.136 | 0.165 | 0.146 |
| decision_interval | 0.063 | 0.107 | 0.113 | 0.115 |

Rank order identical on both index families. Largest total-effect gap 0.020, largest first-order gap
0.044 against a falsifier at 0.10. Correlation of the two responses over the sample 0.994. The
simulator's global sensitivity structure over these four parameters is the closed form's, which is
the strongest validation statement this paper has, and it is worth noting that the first-order
confidence intervals are wide enough (patience $\pm 0.162$) that only the total-effect comparison
carries weight. The rank agreement is reported on both and claimed on neither alone.

**CR-49 P4 VERDICT: THE RULE IS RIGHT WHERE IT MATTERS AND THE QUESTION IT WAS ASKING IS BENEATH THE
RESOLUTION OF THE ANSWER.** `tools/queue_kstar.py`, 67 values of $\lambda$ from 1.3 to 7.9 in steps
of 0.1, 12 replications a point, 40000-step horizon, at $n = 8, 12, 24$.

The registered test was where the STEPS in $k^{\star}$ land, and the registered answer was the
half-integers. That test cannot be run as posed, because a point argmax over this response is noise
dressed as a decision: the response is a plateau, not a peak, and it widens with $\lambda$. At
$\lambda = 7.9$ six different capacities deliver service within one material effect of each other.
Scoring a rule by whether its prediction lands in the PLATEAU, which is the only question a
practitioner can act on, gives

| rule | $n=8$ | $n=12$ | $n=24$ |
|---|---|---|---|
| $\lfloor\lambda\rfloor - 1$ (published) | 4/37 outside | 4/67 outside | 5/11 outside |
| $\lfloor\lambda + 1/3\rfloor - 1$ (Erlang, premise false) | 1/37 | 1/67 | 2/11 |
| $\lfloor\lambda + 1/2\rfloor - 1$ (deterministic, premise true) | 3/37 | 0/67 | 0/11 |

and every failure of the published rule, at every load, lies in $\lambda \in [1.5, 1.9]$. So the
three rules are separated by at most one capacity and the plateau is one to six capacities wide: the
mechanism question, $1/3$ against $1/2$, is below the resolution of the measurement, and the rule
whose premise I proved false performs no worse than the one whose premise is true. That is the
finding, and it is a caution about mechanism stories rather than a result about queues.

**Three things the scan settles that are not about which constant is right, and are worth more.**

1. **The unbounded buffer is catastrophic at every $\lambda$ in the range**, delivering 0.0000 to
   0.0004 against roughly 0.15 for any bound at all. The gain from bounding is a factor of several
   hundred; the gain from bounding CORRECTLY, against bounding at a fixed 2, is a few percent
   outside the degraded regime. The recommendation's value is almost entirely in the first step.

2. **CORRECTED THE SAME DAY, and the correction is the more interesting statement.** The first
   version of this entry said that under-sizing is nearly free and over-sizing is expensive, and
   quoted $\lambda = 3.0$ and 5.0 at $n = 12$ as the evidence. Generating the numbers properly, over
   all 201 grid points rather than two hand-picked ones, says the direction of the risk REVERSES
   with load:

   | | mean cost of one too small | mean cost of one too large | over is worse at |
   |---|---|---|---|
   | $n = 8$ (1.9x capacity) | 6.7% | 13.0% | 75% of points |
   | $n = 12$ (2.8x) | 5.2% | 6.8% | 49% |
   | $n = 24$ (5.6x) | 3.2% | 1.6% | 11% |

   The mechanism is the one CoDel was written about. **A length cap has no fixed meaning in time.**
   At a high arrival rate a buffer of $k$ is a short delay, because drop-oldest refills it
   constantly and nothing in it is old; at a low arrival rate the same $k$ is a long one. So a rule
   phrased in requests cannot be right at two arrival rates at once, and the risk of over-sizing
   evaporates exactly where the console is busiest. The single-number asymmetry in the first version
   of this entry was an average over two opposite regimes and meant nothing. This is the argument
   for controlling sojourn time instead of queue length, and it is now CR-50's motivation rather
   than a loose end.

3. **CORRECTED. No single fixed bound covers the range.** The first version said a fixed 2 sits
   inside the plateau at every $\lambda \ge 2.0$; the generated number is 85% of the 201 points, and
   it fails everywhere up to $\lambda = 2.5$, not 2.0. A fixed 1 covers 61%, a fixed 3 covers 73%.
   The published floor rule is outside the plateau at 13 of 201 points, all in
   $\lambda \in [1.5, 1.9]$; the Erlang rule at 4, in $[1.5, 1.6]$; the deterministic rule at 4, in
   $[2.5, 5.5]$. Every rule and every constant fails somewhere, and where they fail is the degraded
   link. The plateau is narrow enough for any of this to matter at 33 of 67 points at $n = 8$, 21 at
   $n = 12$, and 10 at $n = 24$: the sizing question has an answer in a WINDOW of load, roughly one
   to four times capacity, and outside that window any bound will do.

**CR-49 P5 VERDICT: REFUTED AS STATED, AND WHAT REPLACES IT IS BETTER.** Bounded first-come-first-
served does not merely behave like unbounded newest-first; at a correctly sized bound it BEATS it,
paired over common random numbers, 24 replications:

    lambda=3.0  n= 8:  fifo@2 0.1474  lifo(inf) 0.1373   +0.0101  t=110.6  GATED
    lambda=1.8  n= 8:  fifo@1 0.1281  lifo(inf) 0.1134   +0.0147  t= 89.8  GATED
    lambda=3.0  n=12:  fifo@2 0.1497  lifo(inf) 0.1466   +0.0031  t= 62.8  not material
    lambda=3.0  n=24:  fifo@2 0.1500  lifo(inf) 0.1499   +0.0001  t=  6.4  not material

Two of sixteen contrasts clear the material-practical-effect floor and both are at moderate load;
the rest are differences with enormous $t$ statistics and no operational size, which is what the
floor is for. And the sharper result is the one on the other side of the same table: **once the
backlog is bounded at $k^{\star}$, the discipline stops mattering.** At $\lambda = 1.8$, where
$k^{\star} = 1$, bounded newest-first and bounded oldest-first are identical to every digit at every
load, because a buffer holding one waiting request has no order to permute. At $\lambda = 3.0$ they
differ by 0.0069 at worst and never materially. The requirements ladder therefore collapses to its
cheapest rung: **the counter is sufficient, and given the counter the stack buys nothing.** That is
a stronger sponsor recommendation than the one the paper currently carries and it is cheaper to
implement.

## CR-50. THE CONSOLE SHOULD NOT BE SIZED, IT SHOULD BE TIMED

**Provenance.** Registered before any line of the policy is written. The three facts it builds on are
read and are stated here so they cannot be re-counted as evidence: bounding the backlog is worth a
factor of several hundred over not bounding it; the best bound depends on $\lambda = (P-2\ell)\mu$
and therefore on the link, the deadline and the operator's speed; and a single fixed bound of 2 sits
inside the plateau at every $\lambda \ge 2.0$ but fails below it, which is the degraded-link case
this project exists to study.

**The problem with the recommendation as it stands.** "Bound the console's backlog at
$\lfloor\lambda\rfloor - 1$" asks a program office to know three numbers, one of which, the link
latency $\ell$, is exactly what a contested environment makes unknowable in advance. A rule that
needs the parameter that the adversary controls is not a rule a sponsor can ship.

**What the literature already did about this, in a different queue.** CoDel
\citep{nichols2012codel} does not size a buffer. It measures the queue's own sojourn time, keeps the
MINIMUM over a sliding interval, and starts dropping when that minimum stays above a target. The
famous property is that one fixed setting works across link rates spanning orders of magnitude,
because the controlled quantity is a delay the queue can observe rather than a length that depends
on parameters it cannot. The console is in the same position: it cannot see $P$ or $\ell$, but it
can see exactly how long each request has been sitting in front of it.

**The information audit, which is the part that makes this a requirements claim and not a tuning
exercise.** A CoDel console needs a clock and one target. It does NOT need the requester's deadline
in the message (that is `admit`), it does NOT need the link latency, and it does NOT need to know
its own service rate. It is therefore on the same rung of the ladder as the counter, and strictly
below the message-format change.

**P1.** A CoDel console with ONE fixed setting sits inside the plateau at every $\lambda$ from 1.3
to 7.9 and at $n = 8, 12, 24$, where the best fixed bound fails at 5 or more of those points.
  **FALSIFIER.** A CoDel setting that covers the range only after being retuned per $\lambda$ is a
  tuned parameter wearing a different name, and CR-50 retracts to "bound it at 2 and accept the
  degraded case."

**P2.** CoDel is not worse than the correctly sized counter, at tier, at every $\lambda$. It should
not be BETTER: the counter is being handed the right answer for each operating point, so matching it
is the ceiling.
  **FALSIFIER.** CoDel beating the sized counter by a gated margin anywhere means the counter is not
  the right comparison and the sizing analysis above is measuring the wrong thing.

**P3 (the one that decides whether this is worth porting into SandTable).** Under a link whose
latency CHANGES during the mission, which is what a jammer does, CoDel tracks and the fixed counter
does not. Registered claim: with $\ell$ stepping between 0 and 4 mid-mission, CoDel's delivered
service is above every fixed bound's, at tier.
  **FALSIFIER.** A fixed bound matching CoDel under a moving link removes the only argument for the
  extra machinery, and the recommendation stays "a counter".

**Instrument gate, first.** The queue-only model must reproduce the fixed-bound plateau it already
produced before any CoDel arm is read, on the same seeds. A model that has drifted cannot adjudicate
its own successor.

**Qualifier added before any arm was run, from review of CR-49.** At DETERMINISTIC service a delay
target and a length cap coincide: holding $k$ requests and holding $k/\mu$ steps of work are the
same statement. So P1 and P2 are close to tautological on the performance axis and their whole
content is on the INFORMATION axis, which is that CoDel reaches the same place without being told
$\lambda$. P3, the moving link, is the only limb whose performance claim can fail, and it is
therefore the limb that decides whether this is worth porting into SandTable.

**P6 (registered by adversarial review, before the arm is read, and it is the test that decides
whether the one-half in the rule means anything).** Review's ruling on the threshold: one half is a
bookkeeping coin, not an optimum. The marginal condition for admitting at depth $j$ is not
"$q(j) \ge 1/2$" but
$$q(j) \;\ge\; \pi \cdot \bar{q}_{\text{next}} ,$$
where $\pi$ is the probability that the slot, if not given to this request, would serve a FRESHER
arrival rather than sit idle. In a drought $\pi \to 0$ and the console should admit anything; under
sustained overload $\pi \to 1$ and it should admit only what will certainly land. So the optimal
threshold $p^{\star}$ is not a constant, it runs from 0 to 1 with load, and the patience sweep
registered above cannot see this because it holds the arrival rate fixed while moving $P$: it tests
the FORM of the rule, not the threshold inside it.

The discriminator is therefore a LOAD sweep at fixed $P = 20$ and fixed $\ell = 0$, where $\lambda$
is pinned at 3.00 and only $\pi$ moves.
  **Marginal condition predicts:** the argmax falls from 2 toward 1 as $n$ rises.
  **Constant one-half predicts:** the argmax is flat at 2 across the whole load range.
  **FALSIFIER, for the constant.** An argmax that moves with $n$ at fixed $\lambda$ refutes any rule
  of the form $k^{\star} = f(\lambda)$, including all three candidates, and the honest closed form
  becomes a two-argument one.
  **PRE-COMMITMENT, owed and recorded before the Hopper battery returns.** $P = 30$ gives
  $\lambda = 4.50$, where the marginal admission's success probability is exactly one half and the
  rule is a tie by construction. That cell is scored INCONCLUSIVE whatever its argmax reads.

**Prior art, located by review and owed to the reader.** The rule is a deadline-utility threshold in
the sense of \citet{naor1969regulation}, and Naor's gap between the individually optimal and the
socially optimal threshold is exactly the gap between the one-half above and $p^{\star}$. The
framing "size the buffer to the delay it must not exceed" is \citet{appenzeller2004sizing}. The
drop-oldest rule is the packet-management line in age of information, \citet{kaul2012real} and
\citet{costa2016age}, whose replace-oldest results are the closest prior art this paper has. The
composition is ours; none of the components are. Framed as new queueing theory this dies at review,
framed as the deadline analogue of buffer sizing, located exactly and confirmed at mission level,
it survives.

**CR-49 P6 VERDICT: THE CONSTANT SURVIVES, AND THE ALTERNATIVE IS UNFALSIFIABLE IN THIS SYSTEM.**
Load sweep at fixed $P = 20$, $\ell = 0$, $\mu = 0.15$, so $\lambda = 3.00$ throughout and only $\pi$
moves. 16 replications, 40000-step horizon, offered load in units of console capacity:

    load  0.70x  0.93  1.16  1.40  1.86  2.33  2.79  3.72  5.58  7.44  11.16  14.88
    argmax   2      2     2     2     2     2     2     2     2     2      1      1
    plateau[1-6] [2-6] [2-2] [2-2] [2-2] [1-2] [1-2] [1-3] [1-4] [1-6] [1-6]  [1-6]

The argmax is flat at 2 across a twenty-one-fold range of offered load. The two cells that read 1 are
not a fall: at 11x and 15x capacity every bound from 1 to 6 delivers 0.1500, the console's ceiling,
and the argmax there is a rounding tie. So the marginal condition's prediction, that the argmax
slides toward 1 as $\pi \to 1$, cannot be tested in this system: **$\pi \to 1$ and the objective
going flat are the same limit.** Where the sizing question has an answer, the constant is right;
where the constant would be wrong, nothing is.

The plateau column carries the finding that survives. It is a U in load, narrowest at one to two
times capacity and wide at both ends. At low load the buffer rarely fills and the bound is
irrelevant; at extreme load drop-oldest refreshes the buffer faster than anything can go stale, and
the bound is irrelevant again. **The sizing rule earns its keep in a window, roughly one to four
times console capacity**, which is exactly the span-of-control range this project studies and is why
the effect is visible at all.

**CR-50 AMENDED BEFORE ANY ARM WAS RUN. The interesting rung is not a delay target, it is a
TIMESTAMP.** Working through what a delay-based console would actually need exposed that P1 as
registered is close to empty and something better sits next to it.

A delay target does not free the console from knowing the requester's deadline: no amount of
self-measurement recovers $P$. What it frees the console from is $\ell$, and only if the sojourn is
measured from when the request was SENT rather than from when it arrived. That requires the message
to carry a send time, which every message format already has, and it is a strictly weaker
requirement than carrying a time-to-autonomy, which is a semantic field somebody has to define,
populate and agree on. So the ladder is finer than the paper currently draws it:

| rung | the console must know | the message must carry |
|---|---|---|
| bound the backlog | $P$, $\ell$, $\mu$ | nothing |
| cap the request's AGE | $P$, $\mu$ | a send timestamp |
| refuse on the deadline | nothing | the requester's time-to-autonomy |

The middle rung is new and it is the one worth recommending if it works, because a send timestamp is
free in any real protocol and the latency it silently absorbs is the parameter a jammer controls.

**P4 (open, replaces the emptied P1).** One fixed age cap, in steps, covers the whole $\lambda$ grid
at every load, where no fixed backlog bound covers more than 85% of it.
  **FALSIFIER.** An age cap needing to be retuned across the grid puts it back on the same rung as
  the counter and CR-50 collapses to the amendment above being a distinction without a difference.

**P5 (open, and the limb that decides whether any of this reaches SandTable).** With the link
latency stepping between 0 and 4 mid-mission, the age cap holds its delivered service and every
fixed backlog bound loses some, at tier. This is the claim the ladder is FOR: the age cap is
$\ell$-invariant by construction and the counter is not.
  **FALSIFIER.** A fixed counter matching the age cap under a moving link removes the only argument
  for the timestamp, and the recommendation stays "a counter".

**CR-50 VERDICT: RETRACTED ON ITS OWN FALSIFIER. The recommendation stays "a counter".**

Instrument gate passed first: the fixed-bound plateau reproduced to every printed digit on the same
seeds after the age-cap and moving-link code was added (0.1049, 0.1452, 0.1497, 0.1302 at
$\lambda = 3.0$, identical to the archived scan).

**P4, the static link sweep.** $P = 20$, $\mu = 0.15$, $n = 12$, $\ell$ from 0 to 6, one fixed
setting of each mechanism against all seven links, scored as "within one material effect of the best
mechanism at that link":

    best single backlog bound   k=1   5 of 7 links   worst shortfall 0.0456
    best single age cap         T=7   6 of 7 links   worst shortfall 0.0105

The age cap does degrade more gracefully, and the reason is visible in the table: a single counter
is fine to $\ell = 4$ and then falls off a cliff, 0.1452 at a clear link down to 0.0644 at
$\ell = 6$, while $T = 7$ runs 0.1452 down to 0.1101. At $\ell = 6$ the age cap delivers 71 percent
more useful service than the best fixed counter. The mechanism is not the one the registration
claimed, though: the age cap is NOT $\ell$-invariant, because the answer still has to travel back,
so its correct setting is $P - 1/\mu - \ell$ and the single good value 7 is just the worst case of
that expression over the sweep. The registration's argument for the timestamp was wrong even where
its prediction was right.

**P5, the moving link, which is the limb that was supposed to matter.** REFUTED. With $\ell$
stepping between 0 and 4 mid-mission, paired over common random numbers, 32 replications, at four
switching periods from 200 to 2000 steps:

    period    200     500    1000    2000
    k = 1   0.1398  0.1397  0.1396  0.1398
    T = 7   0.1363  0.1362  0.1361  0.1362
    T7 - k1 -0.0035 -0.0035 -0.0035 -0.0035     |t| 37 to 46, all BELOW the material floor

The fixed counter matches the age cap at every switching period, and if anything edges it. The
registered falsifier reads "a fixed counter matching the age cap under a moving link removes the only
argument for the timestamp, and the recommendation stays a counter." It does, so it does.

**Scope, stated from an arm that was read BEFORE P5 was run and is therefore not a salvage.** The
counter's cliff is at $\ell \ge 5$. The comms ladder this project models tops out at $\ell = 4$ at
C3. So within the operating envelope of the study, the simple counter is not beaten by the
mechanism the bufferbloat literature would recommend, and the age cap's advantage lives entirely
outside it. Extending the switch to $\ell = 6$ to recover a win would be reading a new arm to save a
dead claim, and is not done.

**Why this is worth keeping rather than deleting.** It is the paper's cheapest recommendation
surviving its strongest challenger. A sponsor asked to bound a console's backlog can now be told
that the obvious next step, delay-based active queue management with a timestamped message format,
was implemented and measured and buys nothing inside the envelope. Negative results about
interventions somebody would otherwise fund are the useful kind.

## CR-51. THE OPERATOR IS A METRONOME, AND EVERY CLOSED FORM IN THIS PAPER WAS DERIVED ON ONE

**Provenance.** Proposed by adversarial review as the strongest weakness not yet asked about, and
registered here before any arm is run. The predictions below are review's, not mine, which is worth
recording because it is the first conjecture in this file whose falsifier I did not write.

**The defect.** `c2.py` sets `svc = 1.0 / service_rate`. The console's service time is a constant.
Equation~nstar, the fan-out floor, the latency ceiling and the buffer bound $k^{\star}$ were all
derived against that constant, and admission control, the paper's headline lever, is a feasibility
test that compares a deadline against an exact $1/\mu$. A person is not a metronome. If any of these
results is a property of the zero-variance server rather than of the queue, the paper is a study of
a machine that does not exist.

The instrument is `cv`, the coefficient of variation of the service time, added to
`tools/queue_kstar.py` and holding the MEAN exactly: 0 is the shipped console, 1 is exponential, and
the values between are a gamma with the same mean. Anything that moves is variability and not speed.

**P1 (robustness of the sizing rule).** Across the $\lambda$ ladder, the argmax of delivered useful
service shifts DOWN by at most one capacity at $cv = 1$ relative to $cv = 0$.
  **FALSIFIER.** A shift of two or more capacities at any $\lambda$ says $k^{\star}$ is a property of
  the deterministic server, and the rule ships with a variability correction or does not ship. In
  that case the Erlang reasoning retracted in CR-49 returns, with the right premise this time.

**P2 (robustness of the headline lever).** The advantage of admission control over a blind console
degrades toward zero as $cv$ rises, without changing sign.
  **FALSIFIER.** A sign change at any $cv \le 1$ means the lever is an artifact of a predictable
  server, which is the most damaging single result this paper could produce about itself.

**P3 (mine, added because P1 and P2 are both one-sided).** The DIRECTION of the shift is down. A
noisier server makes a long wait more likely at every depth, so the console should hold less, not
more.
  **FALSIFIER.** An argmax that rises with $cv$ anywhere refutes the residual argument in CR-49 as
  well, since that argument is what makes depth cost time at all.

**CR-51 VERDICT. P1's FALSIFIER FIRES ON THE LETTER AND NOT ON THE SUBSTANCE, AND THE REASON IS A
DEFECT IN THE FALSIFIER I ACCEPTED WITHOUT APPLYING MY OWN LESSON TO IT.** $n = 12$, mean service
held at $1/\mu = 6.67$ throughout, 12 replications, $\lambda$ from 1.8 to 6.0, $cv$ from 0 to 1.

The argmax shifts down by at most one capacity everywhere except $\lambda = 6.0$, where it goes from
5 to 3 at $cv = 1$. Read literally, P1 is refuted. Read against the plateau, which is what the CR-49
P4 verdict established four hours earlier as the only readable statistic on this response, nothing
happens at all: at $\lambda = 6.0$ and $cv = 1$ the plateau is $[2, 5]$ and the deterministic rule's
answer, 5, is inside it. **At every $\lambda$ and every $cv$ tested, the answer computed on the
deterministic server is still inside the variable server's plateau.** P1 is accepted in its plateau
form and its argmax form is recorded as a badly written falsifier. It came from review, I did not
write it, and I published it without noticing that I had spent the afternoon proving that the
statistic it names is noise. Registering someone else's falsifier does not exempt it from the
standards the file applies to mine.

**P3 HELD.** Every shift is downward or zero; none is upward, at any $\lambda$ or any $cv$. A noisier
server makes a long wait likelier at every depth, so the console should hold less, and it does.

**P2 HELD.** Paired on common random numbers, 24 replications, against the unbounded backlog the
console ships with:

| $\lambda$ | $cv = 0$ | 0.25 | 0.5 | 1.0 |
|---|---|---|---|---|
| bound minus blind | +0.1496 | +0.1470 | +0.1417 | +0.1292 |
| age cap minus blind | +0.1494 | +0.1305 | +0.1213 | +0.1184 |

at $\lambda = 3.0$. The sign never changes and the advantage is never close to changing; the lever
loses 14 percent of its value across the whole range from a metronome to an exponential server. The
paper's headline is not an artifact of a predictable operator.

**Two things the registered arms paid for that were not registered, labelled as such.**

1. **Operator variability costs more when the link is worse.** The best achievable delivered service
   falls from 0.1387 to 0.1092 as $cv$ goes 0 to 1 at $\lambda = 1.8$, a loss of 21 percent, against
   0.1500 to 0.1465 at $\lambda = 6.0$, a loss of 2.3 percent. An operator whose pace is erratic is
   a much more expensive operator on a degraded link than on a clear one. That is a human-machine
   teaming statement with a queueing mechanism behind it, and it is the first result in this paper
   that is about the person rather than about the protocol.

2. **The age cap is markedly less robust to variability than the counter**, and there is a reason
   rather than a coincidence. Setting the cap at $P - 1/\mu - \ell$ embeds a POINT FORECAST of the
   service the request has not yet received; the counter forecasts nothing. So the age cap collapses
   from a dead heat at $cv = 0$ to 0.1306 against the counter's 0.1471 at $cv = 0.25$, before either
   has lost much absolute ground. Any rule that admits work on a prediction of the remaining service
   inherits the variance of that service, and this is the second independent reason, after the
   moving-link null, that the recommendation is the counter.

## CR-52. EVERY RESULT IN THIS PAPER WAS FOUND ON ONE MAP

**Provenance.** Adversarial review's second swing, registered before any arm on a new map is read.
Every `band` arm is read: the `band` map IS the paper. Nothing below has been looked at.

**The defect.** `build_world` produced a single profile: one lateral Gaussian band of cover
broadcast along the entire length of the field. That map has no longitudinal structure at all, so a
route choice in this project is a choice of latitude and nothing else, and every lever magnitude,
every threshold and both headline results live on it. The generator now takes a `profile` and a
dozen parameters, with the published path pinned bit-identical on three seeds and every metric.

Two new maps, chosen to attack the queue results from opposite sides rather than to be pretty:

  `open`         no cover anywhere. The negative control: route bias cannot mean anything here, so
                 any result that survives on `open` is not a terrain result.
  `chokepoint`   a transverse ridge with one gap. The only fast ground across it is the gap, so a
                 dispersed force has to converge, and it converges where the MAP chooses rather
                 than where the operator does.

**P1 (the levers).** Admission control over a blind console holds its sign and gates on both
`success` and `served_per_step`, at the collapse span, on both new maps.
  **FALSIFIER.** A sign change on either map, or a failure to gate on both metrics on both maps,
  makes the headline lever a property of the one map it was found on, and every magnitude in
  Section~queue is quoted for that map alone.

**P2 (the bound).** The capacity ladder's argmax is unchanged by the map, because $k^{\star}$ is a
property of the queue and the deadline and contains no term for the ground.
  **FALSIFIER.** An argmax outside $\{1,2\}$ on either new map. That would be the more interesting
  outcome and would mean the ground enters the sizing rule through the arrival process.

**P3 (the threshold, and the reason a chokepoint was chosen).** The collapse span is SMALLER on
`chokepoint` than on `band`. A constriction funnels vehicles into contact together, which raises the
request rate at the moment it is least affordable, and Equation nstar is linear in the reciprocal of
that rate.
  **FALSIFIER.** A collapse span on `chokepoint` at or above the `band` map's puts the direction of
  the terrain-to-console coupling the other way, and the terrain-demand paragraph in the manuscript
  is rewritten rather than extended.

**CR-52 INSTRUMENT ADJUSTMENT, made before any registered arm was run and recorded because it
changes what `open` is.** The first version of the control had no cover at all, and a six-seed smoke
run put mission success at 0.00 on it against 1.00 on `band` at ten assets. A floored metric cannot
carry a contrast, so the control would have been unreadable on the metric a sponsor buys. The
control I want is the absence of a route CHOICE, not the absence of protection, so `open` now
carries the band profile's own mean cover, concealment and trafficability, uniformly. Nothing about
P1, P2 or P3 was read when this was changed; the smoke run that motivated it was on `success` at a
span outside the registered contrast and is reported here rather than used.

## CR-53. AN ERRATIC OPERATOR JITTERS THE ARRIVAL STREAM BY ACCIDENT

**Provenance, stated first because it decides how much of this counts.** `service_cv` was ported
from the queue-only model into `c2.py` as a robustness instrument for CR-51, not as a conjecture. The
first eight-seed smoke run at ten assets on a blind console was read before this was written and is
the reason it exists:

    cv=0.0  served 0.0024  goodput 0.0121  success 1.000
    cv=0.5  served 0.0152  goodput 0.1174  success 0.500
    cv=1.0  served 0.0090  goodput 0.0678  success 0.750

Those three rows are a CONFIRMATION limb and are labelled as one. Everything below them is
prospective.

**The mechanism, which is one this paper already owns.** A console whose service times vary finishes
its decisions at irregular moments, so the requesters it releases return on irregular schedules. That
is the same desynchronization a randomized backoff buys deliberately, arriving here as a side effect
of the operator being human. The paper's own recommendation, randomize the hold, and the defect,
an erratic operator, are the same intervention with opposite intent.

**And the two metrics disagree, which is this paper's recurring problem in a new place.** Delivered
service goes UP six-fold and mission success goes DOWN by half. A console statistic and a mission
statistic point opposite ways because the console's gain is bought by serving requesters that would
otherwise have gone autonomous and won anyway.

**P1 (open).** The console-metric gain from $cv > 0$ is largest at spans where the blind console is
collapsed and vanishes where it is not, because there is no cohort to break up on an uncongested
console. Nothing outside $n = 10$ has been read.
  **FALSIFIER.** A gain that is flat in span, or largest below the collapse threshold, refutes the
  desynchronization mechanism and the effect is something else.

**P2 (open, and the one that tests the mechanism rather than the pattern).** On a console that
already randomizes, or that already runs admission control, the gain from $cv > 0$ is smaller,
because the cohort it breaks up has already been broken.
  **FALSIFIER.** An equal or larger gain on top of jitter or admission control means service
  variability is not acting through the arrival stream at all.

**P3 (open).** The mission-metric LOSS is real and gated, not the small sample above.
  **FALSIFIER.** A null on mission success at tier makes this a console-statistic curiosity and it
  is reported in one sentence rather than as a finding.

**CR-47 G0 VERDICT: THE INSTRUMENT GATE PASSES, AND IT PASSES AFFIRMATIVELY.** Job 9448647, full
tier, 32 blocks by 64 replications. The buffered queue must reproduce the published reservation
model under the policies where the console never commits beyond what it can serve, `refund` and
`admit`, with `blind` excluded in advance and for a stated reason. On `served_per_step`, paired,
against the reservation arm at each span:

    admit   n= 4    6    8   10   12   16      refund  n= 4    6    8   10   12   16
    effect  -0.0012 -0.0041 -0.0039 -0.0042 -0.0035 -0.0028   -0.0010 +0.0001 -0.0013 -0.0011 -0.0013 -0.0012

Twelve of twelve contrasts are EQUIVALENT at the standing margin, with the weaker one-sided
statistic running from 5.29 to 211. Six of them have $|t|$ above 5 as differences, and three above
13: at this tier the two models are distinguishable and the distinction is immaterial, which is
exactly the pair of statements a failure-to-separate could not have made. **This is the first use of
the equivalence instrument on something load-bearing, and it is the reason the rest of CR-47 is
readable at all.** The buffer consistently delivers a hair less than the reservation model under
`admit`, which is the honest direction: a real queue admits at the head against the delay it has,
and a reservation commits at arrival against the delay it will have.

**CR-48 P1 AND CR-49 CONFIRMED AT FULL TIER INSIDE SANDTABLE.** Job 9448688, 32 blocks by 64
replications, capacity ladder from 0 to 10 plus unbounded, `served_per_step`:

    clear link (lambda 3.00, k* = 2)      n= 6      8     10     12     16
      cap 0                             0.0728 0.0861 0.0974 0.1059 0.1173
      cap 1                             0.1075 0.1247 0.1350 0.1413 0.1461
      cap 2                             0.1167 0.1316 0.1403 0.1442 0.1476   <- argmax at all five
      cap 3                             0.1017 0.0956 0.1006 0.1098 0.1299
      unbounded                         0.0956 0.0411 0.0088 0.0028 0.0023

    C3 (lambda 1.80, k* = 1)              n= 6      8     10     12     16
      cap 0                             0.0445 0.0548 0.0650 0.0727 0.0840
      cap 1                             0.0533 0.0668 0.0779 0.0851 0.0948   <- argmax at all five
      cap 2                             0.0487 0.0512 0.0496 0.0464 0.0473
      unbounded                         0.0480 0.0363 0.0121 0.0031 0.0007

Ten of ten argmaxes are $k^{\star}$. **And C3 is the cell that separates the corrected rule from the
published one.** The floor rule says 0 there; capacity 0 is gated WORSE than capacity 1 at four of
five spans, by 0.0108 to 0.0129 served per step against a floor of 0.009. So the correction term,
which came out of a mechanism I first derived against the wrong queue and then re-derived against
the right one, earns its place on a measurement rather than on the derivation.

**The size, which is what a sponsor buys.** At sixteen assets on a clear link the bound delivers 63
times the service of the unbounded console the model shipped with, and at C3, 146 times. On mission
success at eight assets it is worth 17.4 points, 79.7 percent against 62.3. The intervention is one
integer in a configuration file and needs no change to the message format, no deadline field, and no
second operator.

**A metric disagreement, reported because it is this paper's recurring subject.** On mission success
the argmax is capacity ONE at four of the five spans rather than two, so the console-throughput
optimum and the mission optimum differ by one slot. They are not materially different: capacity one
and capacity two are EQUIVALENT on success at all five spans, with the weaker one-sided statistic
from 2.03 to 13.19. The honest statement is that the plateau on the mission metric contains both,
and that where the two metrics disagree the mission metric prefers the SMALLER bound, which is the
direction the queue-only model's load analysis also pointed.

**CR-38 RIDER VERDICT: P1 REFUTED ON ITS OWN FALSIFIER, P2 HELD, AND THE SPONSOR SENTENCE IS
NARROWED.** Job 9448805, full tier, `wait_p95`, one console with the rate rule against two blind
consoles:

    rung 0   n= 8      10      12      16          C3   n= 8      10      12      16
    one    18.93   19.36   19.55   19.71            19.02   19.23   19.33   19.44
    two    13.09   16.03   19.16   19.48            16.86   17.95   18.61   19.28
    verdict LONGER  LONGER   equiv   equiv         LONGER  LONGER   equiv   equiv

Two of the six registered cells fail equivalence, which is exactly what the falsifier said would
narrow the claim, so it is narrowed. **P2, the direction limb, holds at all eight cells: where the
tails differ the single console's is the longer one**, which is the queueing reading and would have
been alarming the other way.

The magnitude matters more than the gate here, and the scale is the requester's own patience of 20
steps. At ten assets two consoles leave the ninety-fifth-percentile requester at 16.0 steps, with
four steps of slack; one console leaves it at 19.4, at the edge of giving up. The throughput
equivalence is real and the tail equivalence is not, and a console sized on the first would be
delivering the same number of decisions to a population a twentieth of which is about to stop
waiting for them.

**This is the second time in this session that a claim I had already written into the manuscript was
narrowed by a check adversarial review asked for and I had not thought to run.** The first was the
plateau. Both were riders on results that were correct as far as they went.
