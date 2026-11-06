# Issue #18 Study Guide: Which Vehicle Does the Enemy Shoot First?

For someone new to this field. Behavior first, code last. Spec: `doc/plans/issue_18_convoy_red_target_priority_ambush_implementation_plan.md`;
reference text: `doc/scenario.md` ("Red target priority and the abstract ambush template").

## 1. What target priority means

Until now every enemy (Red) shooter fired at the nearest vehicle it was allowed to fire at. "Allowed" means: alive,
detected, in weapon range, in line of sight, and the shooter has rounds. #18 adds an optional ordered list, for
example `["ends", "security"]`: fire at the nearest allowed vehicle of the first kind on the list that is available,
and at the nearest allowed vehicle of any kind if none is.

The list never makes a forbidden target allowed. A vehicle Red has not detected, or that is out of range, is never shot
because it is "high priority". And choosing a different target does not make Red any more accurate; it only changes
which vehicle takes the shots.

## 2. What the template adds

An optional abstract ambush (`scenarios/uc3_convoy_ambush.json`): six static Red teams sit 300 m beside the route and hold
fire. When a detected Blue vehicle (security vehicles are ignored by default) reaches a trigger point, they all open up.
After a set time, or after enough ambush-team losses, the ambush teams stop firing, then the support teams, and the
security team stays. Red never moves. All numbers are placeholders, and the scenario is not a reconstruction of any event.

## 3. How it connects to #12, #14 and #17

- **#12**: a halt on contact is triggered when Blue is fired at. Priority changes who is fired at, so it changes who triggers
  that halt. The halt rule itself is untouched.
- **#14**: the autonomous unit puts every human in the control vehicle. A priority on the control vehicle therefore puts
  the crews at risk; `crew_steps_at_risk` reads the same positions as before.
- **#17**: the head of a unit is what the leader-loss policies replace. Targeting heads makes those policies matter more:
  in the sweep, shooting the control vehicle first raised the time units spent leaderless (policy `continue`) by about 370 to
  440 unit-steps.

## 4. One small example

A column of five vehicles drives right; Red is beside the road, all five in range and detected:

```
 Red (beside the road)                    R
                                    . ' ' ' .
   trail                    ...                    head
    [T4]--[T3 sec]--[T2]--[C control]--[H]  --> goal
```

| Rule | Who gets the shots |
|---|---|
| legacy | the nearest to R (here the middle vehicles) |
| `ends` | H and T4, the two ends, if Red has seen them; otherwise the nearest |
| `security` | T3 if Red can tell it is the escort; otherwise the nearest |
| `control` | C if Red can tell it is the control vehicle; otherwise the nearest |

If H is destroyed, the "head" is now the next vehicle (by position) or the promoted leader (by identity), depending on the
setting.

## 5. Glossary

- **Eligible target**: one a shooter is allowed to fire at (section 1).
- **Priority class**: `ends`, `security`, `control`, `armed`, `armored`.
- **Head / trail**: first / last vehicle. `position`: nearest to, and farthest from, the objective. `identity`: the current
  leader of the first unit and the last vehicle of the last unit.
- **Seen vs column basis**: the ends of what Red has detected, or of the whole living column (Red could not know this).
- **Ground truth**: information the simulator has but Red would not (a vehicle's role).
- **Targeted vs destroyed**: aimed at at least once, vs killed. A shot can miss.
- **Hold fire / launch / withdraw**: the ambush stages.
- **Wreck blocking**: a destroyed vehicle physically stopping the road. Not modelled.

## 6. Sourced versus assumed

Sourced (public-release TC 7-100.2, 9 Dec 2011): that an ambush decides at the site whether to fire (3-147); lets security
elements pass and fires when the head of the main force reaches a chosen point (3-148); that hunter-killer teams prefer to trap
urban columns by destroying the first and last vehicles (3-156, 15-61); that security can stay while the others withdraw
(3-161); that a harassment ambush can target a convoy's security element (3-162).

Not sourced, all assumptions: every number (positions, trigger radius, timings, loss fraction), that the ends or the
control vehicle are actually shot first, that Red can recognize roles, and everything about vehicle-targeting order in the
four case studies the work was pointed at (CNA, CTC, AUSA, RAND): not found. The "first and last vehicle" sentence is about
armored vehicles in city streets, not logistics convoys on open routes.

## 7. What the tests prove and what the experiments suggest

**Tests (`tests/test_convoy_red_priority.py`, 54)** use hand-placed vehicles and a rigged random generator that always
kills, so they do not depend on accuracy. They prove: off means byte-identical; an unseen, out-of-range, blocked or
ammunition-less case is never chosen however high its priority; ties go to the lowest index; the next class is used when the
preferred vehicle is gone; head and trail follow position or identity as set; the ambush holds, launches, ignores security,
and withdraws in order; cargo is conserved and crew-by-role sums to the total when everything runs together.

**The sweep (`tools/make_red_priority_arms.py`, 40 seeds, two settings)** only suggests:

- Negative control: with Red on the route axis, `ends` is statistically equivalent to legacy on Blue-loss fraction (margin
  0.06). The ends are already the nearest vehicles there.
- Positive control: with Red beside the route, `ends` destroys more head and trail vehicles (about +0.4 each per run) but
  does not change total Blue losses or delivery in a detectable way.
- Security-first and control-first reduce head losses (trail losses did not change detectably). Control-first raises
  the cumulative time units spend without a head (about +370 to +440 unit-seconds under the `continue` policy, summed over the
  three units): in a hand-placed trace it shoots the three control vehicles, which are the unit heads, and under `continue` a
  unit never gets a head again. `ends` aims at the first and last vehicles of the column, so it reaches a unit head less often.
- No statistically clear difference in delivery or total Blue losses was detected for any policy, in either tested setting, after
  adjusting for multiple comparisons. The intervals are wide, so this does not show the policies are equivalent. The only
  equivalence test run is the negative control (Blue-loss fraction, `ends` versus legacy, Red on the route axis); it passes with
  a margin of 0.06 of the loss fraction and narrowly fails with 0.06 times the legacy level, so it depends on how the margin is read.
- Not tested: the issue's prediction about the control vehicle in the autonomous arm. Without lane blocking (section 8), destroying
  the first and last vehicle does not trap the column.
- Several policies read ground truth, so their effects say what would happen IF Red could recognize roles.

## 8. Later additions: lane blocking, the manifest, and what is still open

**Lane blocking.** A destroyed Blue vehicle can now leave a wreck that holds up the vehicles behind it for `recovery_time_s` seconds
(`lane_blocking`, opt-in). They stop `standoff_m` short and wait; vehicles already past are unaffected. There is no bypass and no rerouting. It is different
from a halt: a halt (#12, #17) is a decision the column makes and can end by its own rule; a wreck is a fact about the road and ends only when its recovery time
runs out. Both can apply at once, and neither clears the other. The recovery time and the stand-off are placeholders. A first experiment (30 seeds, three recovery times, three Red targeting rules) found that blocking did not make delivery worse; in several arms delivery was higher. That is counter-intuitive. A follow-up diagnostic checked whether the template's scripted withdrawal (Red's ambush teams stop firing 120 s after launch) explains it. It does not, by itself: the delivery increase persists with the withdrawal switched off. The cause is still unexplained, and it says nothing about wrecks helping real convoys.

**The manifest.** `tools/manifest_cli.py` freezes a manifest of an experiment before it runs: scenario, arm settings, seeds, comparisons, analysis settings. The
SHA-256 of a canonical form is the registration hash; the git commit is recorded next to it, not inside it. The lane-blocking experiment was frozen first and its run tool
checks the hash. Each frozen manifest also records hashes of the simulation and analysis source (including uncommitted edits) separately from the configuration hash, and the run tool checks them first. The earlier target-priority sweep ran before this existed, so its manifest is marked `post_hoc` and is documentation, not a preregistration; the first lane-blocking manifest froze the configuration but not the code.

**Still open (not test failures).**
- The negative-control margin (A2) is pending clarification: the issue's "0.06 of the contrast spread" is undefined, and one reading passes while two do not.
- The Red halt cost (indirect fire after a halt, devices against responders) has a written proposal and seven open questions
  (`issue_18_red_halt_cost_proposal.md`); nothing is built, because the issue gives the delay but not the effect.
- The registered prediction (control vehicle first by mission-web criticality) is untested until that ranking is supplied or defined. Target role and
  nearest-target rank are not substitutes.
