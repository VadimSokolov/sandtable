# Cross-tier confirmation protocol (CR-71)

**Status: tier-1 side registered and submitted (Hopper job 9460874). Tier-2 side BLOCKED on
ProjectGL access, which this repository does not have.** Everything below is written so that the
confirmation run is an afternoon of harness work on the day ProjectGL is available, and so that the
comparison is against numbers registered before any tier-2 data existed.

## Why this experiment and not a different one

Every requirement this paper writes (the discard rule, request timestamps, the staffing curve, the
ordering of autonomy in the guidance) is single-tier evidence. The program's premise is that
SandTable searches the design space fast and ProjectGL confirms what it finds, and there are
currently zero cross-tier data points. The blocked sponsor decision is not "which lever"; inside
SandTable that argument is as settled as it is going to get. The blocked decision is **may I act on
this simulator at all.**

One sign-level agreement converts the results table from "the tenth-of-a-second simulator says" to
"the two-tier workflow says". One disagreement locates the abstraction boundary, which is the most
valuable single result this project could produce and is worth more than any further tier-1 battery.

Feasibility picks the same experiment. Tier-2 missions cost enough that a confirmation run is
single-digit missions per arm, so only the largest effect is detectable at that sample size. The
discard rule is the largest effect in the paper (published mission success 56.2% blind against 78.6%
refund and 80.0% admit, a 23.8-point gap), and it is also the effect that writes a console
requirement. The smaller contrasts this paper reports, for instance the bounded-versus-admitting gap
of 0.0014 served per step, will never be visible at tier 2 and are not proposed for it.

## The operating point, fixed now

| | |
|---|---|
| scenario | `sc_span_control`, published physics, default fleet |
| span | `n_blue = 8` |
| link | C0 (clear); C2 registered as an alternate for a team that cannot reproduce a clear link |
| arms | `blind` (works every request), `refund` (drops work it cannot finish, says nothing), `admit` (drops it and tells the requester) |
| missions per arm | 5 to 10 |

**Why eight assets.** It is the paper's published operating point for this contrast, and CR-69
found that mission success on this scenario is pinned at exactly 1.0 from sixteen assets up. At
eight, success is 0.5000 at baseline and has full range. The censoring pre-flight therefore passes
by construction rather than by luck.

## Shared observables, and what tier 2 does not owe us

Score on what a high-fidelity tier can be expected to report:

- `success` (mission accomplished, boolean per mission)
- `arrived_frac` (fraction of the blue force that reached the objective)
- `blue_losses` (absolute count)
- `mission_time`

**Not** `served_per_step`, `busy_dead`, `starved_frac`, or any other console telemetry. Tier 2 does
not owe us our instruments, and a protocol that demanded them would be unrunnable.

## Registered form and falsifiers, declared before tier-2 data exists

The registration is on **sign and order of magnitude**, not on value. Two tiers that agreed to four
decimals would be evidence of a bug, not of validity.

1. **Sign.** The tier-2 success gap `refund - blind` is positive, and the tier-2 blue-loss gap
   `refund - blind` is negative.
2. **Magnitude.** The tier-2 success gap is at least one tenth of the tier-1 point estimate.

**Falsifiers.** Either sign flips, or the tier-2 gap is under one tenth of the tier-1 point
estimate. Either fires and the bridge is reported as failed, with the abstraction boundary it
locates named. A failed bridge is a publishable result and is not to be re-run at a different
operating point in search of a better one.

**Pre-flight on the tier-2 side, mandatory.** Before scoring, run the tier-2 baseline across
whatever span range the confirmation uses and check that `success` is not saturated at either bound
there. If it is, score on `blue_losses` instead, by the Round 36 axis rule: an axis is admissible
only where the reference arm sits off its bounds, the diagnosis is computed from the reference arm
alone, and both axes are reported with only primacy switching. Applying that rule after seeing the
result is exactly the failure the rule exists to prevent, so the pre-flight is run and recorded
first.

## What tier 2 has to deliver

One CSV, one row per mission, four columns plus the arm:

```
arm,mission,success,arrived_frac,blue_losses,mission_time
blind,1,0,0.50,4,612
blind,2,1,0.75,2,588
refund,1,1,0.88,1,540
...
```

`tools/score_bridge.py` reads it, reads the registered tier-1 predictions from the `crosstier`
battery log, and prints the verdict against the falsifiers above. It refuses to score a file whose
arms do not match the registration, and it refuses to score fewer than five missions per arm.

## What is blocked and what is not

Blocked: the tier-2 run. ProjectGL is Government-furnished GOTS software built on Unreal Engine and
is not in this repository. Obtaining it, and the plug-in work to instrument the four shared
observables, is sponsor-side and is on the critical path for the manuscript's strongest possible
claim.

Not blocked, and done: the operating point is fixed, the tier-1 predictions are registered and
running, the falsifiers are written, the censoring pre-flight is specified, the delivery format is
defined, and the scorer exists. On the day ProjectGL is available the remaining work is running
missions and typing a file path.
