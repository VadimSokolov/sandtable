# Proposal for Professor Sokolov: the Red halt cost (Issue #18, Change item 4)

**Status**: proposal only. **Nothing is implemented**, because the issue does not define the effect, and any effect chosen here
would decide the experimental result.

## 1. What the issue says

> A Red halt cost: indirect fire after a halt (delay 120 to 900 s is a swept placeholder, no public source gives it), and
> secondary devices against responders.

That fixes one thing: a delay between a halt and the start of Red indirect fire, swept over 120 to 900 s as a placeholder. It also names
a second element, "secondary devices against responders".

## 2. What the issue does not say (each needs an answer before anything is coded)

| # | Open point | Why it matters |
|---|---|---|
| 1 | **What counts as "a halt"?** A contact halt (Issue #12), a leader-loss halt (Issue #17), a lane block by a wreck (Issue #18, item 2), or any stop? | The three are different mechanisms; the cost would attach to a different set of runs |
| 2 | **What is Red's indirect fire?** One asset or several; how many rounds; how often | There is no indirect-fire entity in the simulator |
| 3 | **What does one round do?** An area, a radius, a kill probability per vehicle per round | Not sourced; it is the entire effect size |
| 4 | **Must Red observe the halted column?** Or does it fire at a remembered location | An omniscient Red makes the cost independent of detection; the existing `seen` picture is the observable alternative |
| 5 | **When does the fire stop?** Duration, ammunition, or when the column moves | Decides whether a long halt is merely costly or fatal |
| 6 | **What is a "responder"?** The recovery-role vehicles, any vehicle that approaches a wreck, or the escorts | There is a `recovery` role but no responder behavior |
| 7 | **What is a "secondary device"?** Where is it placed, how many, when, what does it do on triggering | No obstacle or device entity exists |

## 3. A concrete proposal (for the answers above)

Everything numerical is an EXPERIMENTAL ASSUMPTION, labelled as such in config and docs, with no public source.

`red_halt_cost` (opt-in; absent = byte-identical):

```
"red_halt_cost": {
  "halt_source": ["contact_halt", "leader_loss_halt", "lane_block"],   # which stops count (question 1)
  "min_vehicles": 3, "min_halt_s": 10,                                  # a halt = this many convoy vehicles stopped this long
  "delay_s": 300,                                                       # swept: 120, 300, 600, 900 (the issue's range)
  "observation": "seen",                                                # Red fires only while it has a seen convoy vehicle (question 4)
  "indirect": {"radius_m": 60, "pk_per_vehicle_per_tick": 0.01, "duration_s": 120},   # PLACEHOLDERS (questions 2, 3, 5)
  "responders": {"roles": ["recovery"], "device_pk": 0.2, "devices": 2, "radius_m": 30}  # PLACEHOLDERS (questions 6, 7)
}
```

Mechanics, in the smallest form that is testable:
1. A halt is detected from the same hold masks and lane-block flags the simulator already has; no new stop mechanism.
2. `delay_s` after the halt is declared, and while Red has at least one seen convoy vehicle, every living Blue vehicle within `radius_m` of the
   halt centroid is hit with probability `pk_per_vehicle_per_tick` each tick, for `duration_s`, or until the column moves on. It would use a
   separate derived random stream so the existing draws are not shifted.
3. Devices are placed, at launch of the ambush, on the wreck sites of the first `devices` Blue vehicles destroyed; a responder within
   `radius_m` of one triggers it once with probability `device_pk`.
4. Metrics: `rhc_halts`, `rhc_fire_ticks`, `rhc_kills_indirect`, `rhc_kills_device`, kept apart from `blue_losses` by cause.

The run design the issue implies: sweep `delay_s` over 120 to 900 s with the same Red set, same seeds, and a frozen manifest
(`doc/manifests/`, `tools/manifest_cli.py`), paired against a run with the cost off.

## 4. What I need from you

- Answers to questions 1 to 7, or "use the proposal above".
- The values for `radius_m`, `pk_per_vehicle_per_tick`, `duration_s`, `devices` and `device_pk`, or agreement that they stay labelled placeholders
  and are swept, never tuned to produce an effect.
- Whether an effect that depends on these placeholders is acceptable as an experiment at all, given that the issue itself says no public source gives the delay.

## 5. Why this was not simply built

A halt cost with invented kill probabilities makes any halt-related policy (the #12 halt, the #17 `halt` policy, a wreck in the lane) look bad or good by
construction. The experiment would then measure the placeholder, not the policy. This was the concern raised for the target-priority work as
well: a mechanism should not be added just to make an effect appear.
