# Decision brief for Professor Sokolov: Issue #18 (Red target priority and an ambush template)

**State**: a reviewable checkpoint, not a finished issue. Target priority, the ambush template, lane blocking (route-only) and the manifest/registration hash exist and are tested.
This brief lists what cannot be closed without a decision. Required decisions come first; optional realism is separate and does not block acceptance.

## What the checkpoint does and does not claim

- Priority only reorders targets Red is already allowed to fire at. It adds no kill probability and no obstacle.
- Lane blocking holds the column behind a wreck for a swept placeholder time. It is route-only: no rerouting, queueing or street-graph traffic.
- In the lane-blocking experiment, delivered fraction was often **higher** with blocking than without. A diagnostic tested one explanation, the template's scripted withdrawal, and **it did not account for the
  increase** (the increase persists with the withdrawal disabled). **The cause is unresolved.** It is not evidence that wrecks help convoys, and not evidence about any real engagement.
- Tests: the latest changes passed 240 affected tests (convoy suites and counter-UAS). The broader 641-pass run predates the timing-metric changes and includes one pre-existing failure
  (`test_no_bare_dict_equality`, already on `convoy-dev`). Not run: `test_plugin_metric.py`, `test_sobol.py` (missing dependencies) and `test_search_bench.py` (undiagnosed stall).

## A. Required decisions (they decide whether #18 can be accepted)

### A1. Negative-control margin

1. **Issue wording**: "Negative control: with Red head-on and no vehicle ahead of the head, `target_priority` on and off are equivalent by `ar_gate.tost` on blue losses, with margin 0.06 of the contrast spread (the project's minimum practical effect) over at least 30 paired blocks."
2. **Current implementation**: 40 paired blocks, Blue-loss fraction, `ends` versus legacy. Three readings of the margin, all kept: absolute 0.06 of the loss fraction (fixed before results; **passes**, TOST statistic 4.22 against 1.70); `ar_gate.margin`, 0.06 times the legacy level = 0.0245 (added after results; **fails narrowly**, 1.65); 0.06 times the SD of the paired contrast = 0.0052 (added after results; **fails**, 0.26).
3. **Decision needed**: which quantity "the contrast spread" is, and so which margin applies.
4. **Effect**: the negative control, an acceptance criterion, passes under the first reading and fails under the other two. Nothing is tuned to make it pass.

### A2. Red halt cost

1. **Issue wording**: "A Red halt cost: indirect fire after a halt (delay 120 to 900 s is a swept placeholder, no public source gives it), and secondary devices against responders."
2. **Current implementation**: none. A concrete proposal is in `doc/plans/issue_18_red_halt_cost_proposal.md`: a halt is detected from existing hold masks and lane-block flags; after `delay_s` Red indirect fire hits halted vehicles with a placeholder per-tick probability; devices at early wreck sites hit responders. Every effect number is a placeholder.
3. **Decision needed**: the seven open points: what counts as a halt, what Red's indirect fire is, what a round does, whether Red must observe the column, when the fire stops, what a responder is, what a secondary device is.
4. **Effect**: the issue gives the delay but not the effect, so any choice sets the result. Without a decision the item stays unimplemented and #18 cannot be called complete. If implemented, the halt-cost numbers must stay labelled placeholders and be swept.

### A3. Lane blocking: does route-only satisfy "needs the street graph"?

1. **Issue wording**: "A lane-blocking rule for a destroyed vehicle with a `recovery_time` (needs the street graph)."
2. **Current implementation**: a wreck blocks the road at its along-track position (route arc length, or the line to the objective) for `recovery_time_s`; vehicles behind stop at a stand-off point; no bypass, no rerouting; the street graph is never read (a test enforces this).
3. **Decision needed**: whether "needs the street graph" means the route (which a graph may have produced) is enough, or the blocked edge must be removed from a graph the column routes over.
4. **Effect**: if route-only is enough, this item is complete (see B1 for realism beyond it). If a graph edge must be blocked, the item is incomplete.

### A4. Registration hash: what "one hash across both arms" covers

1. **Issue wording**: "Register the Red set before any Blue variation run, label each parameter sourced, bounded or placeholder, use one hash across both arms, and call the paired automated runs simulation-based analysis, not wargames."
2. **Current implementation**: a manifest records the whole experiment (scenario inputs, resolved arms, fixed parameters, seeds, comparisons, analysis settings) under one configuration hash, with simulation and analysis source hashes beside it. The lane-blocking and withdrawal manifests were frozen before running; the target-priority sweep's is `post_hoc`. No experiment currently compares the manned and autonomous arms.
3. **Decision needed**: whether the hash should cover the Red set only (so the same hash appears in both Blue arms) or the whole configuration; and whether "both arms" means the manned and autonomous Blue arms.
4. **Effect**: only a frozen manifest may be called a registration. If the Red-set-only reading is meant, the manifest needs a Red-set sub-hash and the target-priority work has not been registered before its Blue variation.

### A5. The registered prediction

1. **Issue wording**: "Prediction to test: ranked by mission-web criticality, the control vehicle comes first in the autonomous arm and no vehicle dominates in the manned arm. Falsified if the ranking is flat in the autonomous arm." Acceptance: "Registered prediction, not an acceptance test: the arm difference changes sign or size between the static Red and the ambush template, which the ticket expects; it is reported either way."
2. **Current implementation**: none, and untested on purpose. A first look at manned versus autonomous in these scenarios gave identical delivery and losses (same roles and behavior; only crew counts differ), so it was dropped as uninformative. Target role and nearest-target rank are not used as substitutes.
3. **Decision needed**: the definition or source of "mission-web criticality" (the issue cites Raz et al. 2024 and `doc/lit-ideas.md`, which were not verified here).
4. **Effect**: the prediction is not an acceptance test, but the issue expects the arm difference to be reported either way, which is not done.

## B. Optional extensions and interpretation choices (they do not block acceptance)

| # | Item | Current | Effect of choosing differently |
|---|---|---|---|
| B1 | Rerouting or bypass around a wreck | none | More realism; needs runtime path replanning. Only matters if A3 requires it |
| B2 | Per-role or per-vehicle recovery times; recovery tied to the convoy's recovery vehicles | one swept constant | Changes who is held and for how long |
| B3 | Replay path support for lane blocking | not wired | Replays would not show the blocking |
| B4 | Which end definition is intended (`position` default, or `identity`) | both exist | Changes which vehicles count as head and trail |
| B5 | Whether the `security` and `control` classes may read ground truth | allowed and labelled | An observable-only policy would drop them |
| B6 | The security-role team never withdraws (TC 7-100.2 3-161, "may remain to provide warning and to delay") | as written | If it should withdraw too, Red falls fully silent after the order |
| B7 | Scripted withdrawal timed from ambush activation | from the launch tick | From mission start would change when Red stops firing |
| B8 | Why delivery rises with blocking | unexplained | Finding it needs an agreed hypothesis; the withdrawal was ruled out as the main cause |

## C. What can be said now

The simulator supports configurable Red target selection and an abstract ambush template, tested under controlled fixtures. In the tested settings no statistically clear difference in delivery or total Blue losses was detected between priority policies;
that is not evidence of equivalence. The negative control passes under one margin reading and fails under two. The halt cost, the criticality-ranked prediction and a street-graph reading of lane blocking are open.
