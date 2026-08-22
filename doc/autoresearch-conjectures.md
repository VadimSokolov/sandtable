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
