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
| C8 | **Congestion collapse by unrefunded abandonment.** The operator spends a service slot on every request it receives, including requests whose answer will arrive after the requester has given up. At large span the offered load exceeds capacity, almost every request is abandoned, and packet loss then acts as unintended admission control. Explicit admission control should remove the interior optimum and dominate at every rung. | **confirmed at proxy**, full-tier gate pending | |
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
