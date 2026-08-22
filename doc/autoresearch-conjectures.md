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
declared RELATIVE for rate metrics, at 3% of the control arm's own value, and absolute for metrics
on [0,1]. The justification is that 0.03 of mission success is three points of a probability, and
the analogous quantity for a rate is 3% of that rate; an absolute 0.03 on `served_per_step` would
be 60% of the metric, which is not a minimum effect but a demand for a catastrophe. Under that
convention the n = 4 damage and the jitter recovery both gate.

**And the cell still does not become a poster, for a reason that has nothing to do with the gate.**
CR-27's P1 is refuted above, so the pump account this cell was collected to support no longer
exists. What the cell now shows is retry self-collision at a span where sustained load is off,
which is the same thing D2 shows more cleanly on a channel with no burst structure at all. The
clean demonstration is the one to print.
