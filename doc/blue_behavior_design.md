# Thickened blue behavior layer: design

Status: design, not implemented. Companion to idea I16 in `doc/lit-ideas.md`.

## The problem

SandTable's control-modality axis currently changes a **gain**, not a **behavior**.

`src/sandtable/c2.py` resolves modality into a per-agent scalar `control_quality` in [0, 1].
`src/sandtable/motion.py` reads it as a speed multiplier (`v * (0.35 + 0.65 * q)`) and the
engagement kernel reads it similarly. `src/sandtable/planning.py` then gives every blue ground
vehicle the same single script: an independent pure-pursuit carrot along a lane chosen by
`route_bias`, documented as having "no dead-leader dependency," with `formation_spread` accepted and
immediately discarded (`_ = spread  # reserved for the richer formation model`).

Two consequences, both bad for the centerpiece claim:

1. **A teleoperated vehicle that loses its link does not stop.** It runs at
   `0.35 + 0.65 * 0.30 = 0.545`, that is 55% speed, while nominally awaiting an operator who is not
   answering. Real teleoperation with a severed link is stopped. The model currently understates the
   cost of direct control precisely where the paper claims that cost is largest.
2. **There is no formation, so there is nothing for comms degradation to break.** Independent
   navigation is the most comms-robust possible arrangement. The design that would suffer most from
   a degraded link, leader-follower, is the one fielded Army thread and it is absent.

## What the literature says the target should be

| Anchor | What it licenses |
| --- | --- |
| Urmson et al. 2008, `10.1002/rob.20255` | The three-layer mission / behavioral / motion decomposition, stated in the abstract. The behavioral layer "determines when to change lanes and precedence at intersections and performs error recovery maneuvers." SandTable has layer 1 and a stub of layer 3, and no layer 2. |
| June 2026 Army RFI (grey, see `doc/scenario.md`) | The current fielded baseline modes: teleoperation, waypoint navigation, leader-follower, sentry. |
| Pirozzo et al. 2019, `10.4271/2024-01-3821` | GVSC consolidated AMAS into the government-owned Robotic Technology Kernel. The Army's own direction is a behavior library, not a learned policy. Cite as **2019**; the `2024` in the DOI is SAE numbering. |
| Brendle and Jaczkowski 2002, `10.1117/12.474441` | Leader-follower is the long-running near-term autonomy hedge (Robotic Follower ATD). Abstract announces a program, not a result: lineage only. |
| Cheung, Rawashdeh, Mohammadi 2022, `10.3390/app12199863` | Behavior-based on-platform following beat a basic delayed-follower controller under jamming by **13.33% to 86.61% path-error reduction**. The one quantified argument for moving competence onto the platform. Simulation, path error not mission outcome. |

## Scope boundary, to be stated in the paper

Thickening scripts approaches how an Army UGV is **tasked and commanded**. It does not approach how
an off-road stack **drives**. SandTable has no LiDAR, no vehicle dynamics, no slope or belly
clearance. The Army measures off-road autonomy by soldier takeover rate, and SandTable does not vary
autonomy difficulty by terrain at all. This layer is not a digital twin of a driving stack and the
paper must say so in those words.

## Design

### New module: `src/sandtable/behavior.py`

Runs between `c2.step` and `planning.step`. Owns a per-entity behavior state and may override the
movement target that `planning.step` would otherwise set.

```
BEHAVIORS = TELEOP | WAYPOINT | LEADER_FOLLOW | SENTRY
```

| Mode | Movement rule | Comms dependence |
| --- | --- | --- |
| `TELEOP` | Advances only while the operator link is up and the agent is not awaiting. Link down or awaiting means **speed zero**, not degraded speed. | Total. |
| `WAYPOINT` | Today's behavior: independent pure-pursuit along the `route_bias` lane. | None. |
| `LEADER_FOLLOW` | Followers hold a column station at `formation_spread` behind the vehicle ahead. Two variants below. | Variant-dependent. |
| `SENTRY` | Hold position, keep sensing and engaging. Used for overwatch, screening, and as a recovery state. | None. |

### The Cheung contrast, made a switchable parameter

`LEADER_FOLLOW` gets two follower implementations, and the difference between them is the
experiment:

- `follow_mode="link"`: the follower needs the leader's current state over the comms link. On a
  dropped or late message it holds a stale station, which drifts as the leader moves. This is the
  "basic delayed follower."
- `follow_mode="behavior"`: the follower keeps an on-platform track (last known leader pose plus
  heading and speed, dead-reckoned forward) and continues the column without a live message. This is
  the "Behavior Manager" analogue.

Running the same convoy under both, across the C0 to C5 ladder, reproduces the Cheung comparison at
mission level rather than path-error level. If the sign of the effect matches and the magnitude does
not, that is a reportable multi-fidelity finding, not a failure.

### Recovery triggers

The RTK direction is explicit that current work is refining **behavior requirements for when the
vehicle should stop or hand back to a human**. Model these as guarded transitions, evaluated in
priority order:

| Trigger | Condition | Transition |
| --- | --- | --- |
| `WAIT_FOR_OPERATOR` | decision pending, `TELEOP` | hold in place (speed zero) |
| `STOP_ON_LINK_LOSS` | link down, `TELEOP` | hold in place |
| `HALT_ON_LEADER_LOSS` | leader dead or track older than `track_timeout` | `SENTRY`, then `WAYPOINT` if the follower holds the route |
| `FALL_BACK` | wait exceeded `patience` | `WAYPOINT` at `q_fallback` |

### Modality selects the repertoire, not just the gain

This is the change that makes the centerpiece axis mean something mechanical:

- `direct` maps to `TELEOP` primary, falling back to `WAYPOINT` on link loss or exhausted patience.
  That matches what `doc/scenario.md` already identifies as the realistic near-term contrast:
  teleoperation versus assisted or waypoint autonomy with frequent takeover.
- `supervisory` maps to `WAYPOINT` or `LEADER_FOLLOW` primary, with `SENTRY` on trigger and the
  operator consulted only by exception.

`control_quality` survives unchanged as the quality gain. It now multiplies a behavior instead of
standing in for one.

### New metric: intervention rate

`doc/scenario.md` asks for this because it is how the Army actually measures autonomy, and the
behavior layer makes it computable for free: count transitions into `WAIT_FOR_OPERATOR` and
`FALL_BACK` per vehicle-hour. Report alongside mission success. This makes SandTable's output
commensurable with how GVSC reports UGV maturity, which is worth more than another internal metric.

## Parameters

| Param | Default | Meaning |
| --- | --- | --- |
| `blue_behavior` | `None` | `None` keeps the current single-script path exactly. Otherwise the mode name or `"auto"` to derive from `control_mode`. |
| `follow_mode` | `"behavior"` | `"link"` or `"behavior"`. Only read under `LEADER_FOLLOW`. |
| `formation_spread` | 30.0 | Finally consumed: column gap in metres. |
| `track_timeout` | 40 | Steps before a dead-reckoned leader track is declared stale. |
| `teleop_stop` | `True` | Whether a `TELEOP` agent with no link stops. `False` reproduces today's 55%-speed behavior for an ablation. |

## Implementation discipline

Follow the existing opt-in idiom exactly. `personality.py` is the precedent: `pers=None` leaves the
baseline path byte-identical, and `c2.py` shows the RNG rule ("Both link types draw the same two
Bernoulli message-survival values, so the RNG stream stays aligned and the OFF path is
byte-identical"). Any draw the behavior layer needs must either come from a separate stream or be
drawn identically on both paths.

Required tests, mirroring `tests/test_counter_uas.py::test_off_is_byte_identical`:

1. `blue_behavior=None` is byte-identical to the current build, same seed, same metrics.
2. `TELEOP` with the link forced down produces zero displacement.
3. `LEADER_FOLLOW` with `follow_mode="link"` degrades more than `"behavior"` as the ladder worsens,
   sign only, magnitude unconstrained.
4. Killing the leader drives followers to a recovery state and the mission still terminates.
5. Intervention rate is zero under `supervisory` with a clean link and rises monotonically with
   ladder rung under `direct`.

## What this does not fix

Off-road autonomy difficulty. Terrain enters SandTable as a speed raster and a cover or route
tradeoff, never as autonomy difficulty that forces a takeover. Until terrain can raise the
intervention rate directly, the intervention metric measures comms and queue contention only, and
must be reported with that qualifier.
