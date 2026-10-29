# Issue #17 Study Guide: What Happens When a Convoy Loses Its Lead Vehicle

For someone new to this field. Behavior first, code last. The full spec is in
`doc/plans/issue_17_convoy_leader_loss_halt_release_implementation_plan.md` and the reference text in
`doc/scenario.md` ("Leader-loss policy and halt release").

## 1. The problem

A convoy drives in small groups. In the autonomous version, only the front vehicle has people in it and the
trucks behind it follow it. If the front vehicle is destroyed, the followers have lost the thing they
follow. What should they do?

Before #17 the simulator had one answer, built in and not named: the followers hand control to the next
vehicle or drive the route on their own. Nobody could change it or study it. #17 turns that answer into a
setting with five values, and adds a rule for when a stopped convoy may start moving again.

How it extends earlier work:

| Issue | What it added | What #17 uses from it |
|---|---|---|
| #8 | Convoy structure: march units, serials, roles, and promotion of a new head | The head, the unit, and the old "promote the next vehicle" rule (now called `legacy`) |
| #12 | Escort vehicles, and a "halt on contact" reaction with a timeout release | The halt mechanism, and a new release rule `leader_policy` |
| #14 | Crew counts, an autonomous unit (one crewed head, four unmanned trucks), `manned_only` succession | Who may become head (only crewed vehicles under `manned_only`), and the crew exposure metric |

These are simulation policies for comparison. They are not documented capabilities of any fielded system
(ATV-S included); no public source gives a loss-of-leader procedure for autonomous followers.

## 2. Glossary

- **March unit**: a small group of vehicles that moves together (here five: one head, four trucks).
- **Serial**: a few march units that travel together.
- **Head / leader**: the front vehicle the others follow.
- **Follower**: a vehicle that holds its place relative to the one it follows.
- **Head loss**: the head is destroyed. The simulator notices on the same or next tick.
- **Succession**: choosing a new head. `manned_only` means only a vehicle with people in it may be chosen.
- **Handoff latency** (`handoff_steps`): how many ticks pass between the loss and the new arrangement
  taking effect. 0 is an idealized best case, not a measured value.
- **Halt**: the unit stops in place but keeps sensing and engaging.
- **Release rule**: what ends a halt. Two options, and either one ends it: `clear_steps` (no armed enemy in
  weapon range of the unit for N ticks in a row) and `max_hold_steps` (the halt has lasted T ticks).
- **Shooter**: an enemy that is alive, has a weapon range, and a non-zero kill probability.
- **Cargo in transit / delivered / lost**: payload still being carried, handed over at the objective, or
  destroyed with its vehicle.
- **Byte-identical when off**: with the setting absent, every output is exactly what it was before #17.

## 3. One small example

One march unit: head **H** (crewed control vehicle, no cargo) and trucks **T1 T2 T3 T4** (each carrying
cargo, unmanned). Another unit, **U2**, is ahead in the same serial. An enemy destroys **H**.

| Policy | What the four trucks do next |
|---|---|
| `legacy` | The old behavior: the next vehicle is promoted straight away (or they drive the route alone if no one can lead). Kept so old results reproduce. |
| `continue` | Each truck becomes its own leader and drives the route alone, immediately. The unit stays leaderless to the end of the run. |
| `promote` | After `handoff_steps` ticks, T1 becomes head and T2 to T4 follow it. Under `manned_only` no truck is crewed, so nobody is eligible and the unit behaves as `continue`. |
| `absorb` | After `handoff_steps` ticks, the trucks join the tail of the nearest unit in the same serial that has a living head (U2). Experimental; see section 7. If none exists, as `continue`. |
| `halt` | All four trucks stop where they are. When the release rule fires, T1 becomes head and they resume. Other units keep going. |

## 4. Halt and release

```
head destroyed
      |
      v
 unit halts  ---- every tick: count ticks held, and ticks in a row with no armed enemy in range ----
      |
      +-- clear_steps reached? (enemy gone for N ticks in a row) --+
      |                                                            |--> RELEASE
      +-- max_hold_steps reached? (halted T ticks)  ---------------+
      |
      +-- neither set --> keep holding (only the end of the mission ends it)
                                                     |
                                                     v
                              earliest eligible survivor becomes head, no further delay, unit resumes
                              (nobody eligible: unit drives on as `continue`)
```

`clear_steps` looks at the true positions of enemies, not at what the convoy has detected. So it assumes the
convoy somehow knows the shooting has stopped.

## 5. What changes in the numbers

- **Cargo.** Losing a vehicle loses only that vehicle's undelivered payload. In the test convoy the head is
  the control vehicle and carries nothing, so losing it loses no cargo under any policy. `halt` without a
  release leaves the unit's cargo in transit for the rest of the run, and in the sweep this is what drops
  delivery sharply. A halt with a release delays the unit's delivery while it holds; the sweep does not isolate by how much.
- **Leaderless metrics.** `leaderless_steps` counts unit-ticks with survivors and no head: zero for an
  instant `promote`, equal to the handoff delay for a delayed one, and growing every tick under `continue`.
  `ll_halt_steps` counts vehicle-ticks held. `ll_handoffs` counts completed promotions or attachments.
  `first_leader_loss_step` is the tick of the first loss, -1 if none.
- **Crew exposure.** A halted unit sits where it was. If that is inside enemy range, the crews in it stay at
  risk longer, so `crew_steps_at_risk` should rise with long halts. This has not been measured: the sweep
  declares no crew.

## 6. How it is built, briefly

The code is in `src/sandtable/behavior.py` (`_update_leader_loss`, one pass per march unit each tick),
settings are validated in `src/sandtable/convoy.py`, and the metrics are in `src/sandtable/metrics.py`. The
new code draws no random numbers. A declared policy turns on leader-following automatically.

## 7. Assumptions and limitations

- **Idealized baseline**: `handoff_steps = 0`. Other delays are swept values with no source.
- **`absorb` is a modelling device.** It reassigns the trucks on paper to the nearest living head in the same
  serial. Under `manned_only` that head must be crewed. There is no doctrine for escorts or wreckers taking
  over other units' followers, and none is claimed.
- **`clear_steps` uses ground truth** (see section 4).
- **`halt` holds one unit.** Other units are not stopped unless a contact reaction stops them.
- **Fallbacks are permanent**: once a unit drops to `continue`, it does not get a head again.
- **One scenario (UC-3), one convoy layout, 20 seeds.**
- **A baseline test failure and an unfinished test** are unrelated to #17 (see the plan, section 8).

## 8. What the tests prove and what the experiments suggest

**Tests (`tests/test_convoy_leader_loss.py`, 44 tests) prove the code does what the spec says.** They force
the kill at a chosen tick and, in the halt tests, remove the enemy at a chosen tick, so the results do not
depend on enemy aim. They show: off means byte-identical; each policy's behavior after a head kill; handoff
delay; halt with and without each release condition; a loaded cargo truck killed loses exactly its payload;
a head kill loses no cargo; `absorb` skips an uncrewed receiving head under `manned_only`. They say nothing
about which policy is better.

**The sweep (`tools/make_leader_loss_arms.py`) is exploration.** 12 arms, seeds 0-19, a forced head kill and
a real-engagement experiment, each arm paired by seed with `legacy`.

- `halt` with no release is clearly worse than `legacy` for delivery, as expected.
- `absorb` is higher than `legacy` in both experiments, but the cause is unknown and may be an artifact of
  the reassignment.
- Everything else has intervals that include zero. That means the data cannot tell it apart from `legacy`,
  not that it is the same.
- Differences are against `legacy` only, so two other arms are not compared with each other. About 110
  comparisons were made, so a few will look significant by chance.
- A head was lost in 20 of 20 seeds (forced) and 19 of 20 (engagement).
