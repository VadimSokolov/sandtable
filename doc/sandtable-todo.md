# SandTable change queue

Change requests against the `sandtable` package, written for the agent doing the implementation.
This file is the queue: nothing here is implemented yet unless its status says so.

Rationale and literature anchors live in `doc/blue_behavior_design.md` and idea I16 of
`doc/lit-ideas.md`. This file carries only what an implementer needs: interfaces, defaults, files
touched, and acceptance tests.

## Framing: what these changes are actually for

Two concepts govern this queue, and every CR is here because it serves one or both. If a proposed
change serves neither, it does not belong in this file.

**Mission design.** The project's title is "Virtual Prototyping of **Mission and Formation
Concepts**," and its first promised outcome is the discovery of novel autonomous formation concepts
that balance human control and autonomy. SandTable's job is to make mission and formation concepts
*designable*: to expose the choices (route, formation geometry, spacing, how the team recovers when
something breaks) as things an analyst or an optimizer can vary, and to score them on resilience,
efficiency and operational feasibility. A parameter that cannot change a mission outcome is not a
design variable, it is decoration. See CR-5 for a live example of that failure.

**Human-machine teaming.** The four SOW objectives are about the *team*, not the vehicle: detecting
patterns of success and failure in human-machine collaboration, distributing cognitive load across
the interface, comparing direct against supervisory control, and measuring collaboration
effectiveness at mission level. The unit of analysis is the operator and the machines together, not
a UGV in isolation. This is why CR-1 matters most: today the modality axis scales a quality gain,
which models *how well the human is helping*, but never *what the division of labor between human
and machine actually is*. Teaming is the division of labor. A model that cannot represent the
division cannot study the teaming.

| CR | Mission design | Human-machine teaming |
| --- | --- | --- |
| CR-1 behavior layer | gives formations a repertoire to be built from | represents the division of labor, not just its quality |
| CR-2 teleop stop | corrects the feasibility cost of a concept | prices keeping the human in the loop |
| CR-3 leader-follower | the fielded formation concept, currently absent | what the team loses when the link degrades |
| CR-4 intervention rate | feasibility, in the Army's own currency | the measured output of teaming |
| CR-5 station keeping | makes formation geometry a real design variable | secondary |
| CR-6 endurance | bounds which formation concepts are feasible at all | secondary |

Keep this table honest. If a CR lands and its column claim turns out to be false, fix the claim.

## Standing conventions

Every change below follows the idiom the package already uses for optional layers
(`personality`, `belief`, `mechanics`, `counter_uas`):

1. **Opt-in, off by default.** A `build_*(scn, ent)` constructor returns `None` unless the scenario
   sets the enabling param. `sim.run_mission` holds the object and skips the call when `None`.
2. **Byte-identical when off.** With the layer off, the same `(scenario, seed)` must produce the
   identical metrics dict, bit for bit. That means no extra RNG draws on the off path. `c2.py` shows
   the technique when a draw is unavoidable: draw the same values on both paths so the stream stays
   aligned.
3. **New `Entities` fields are optional.** Declare as `field: np.ndarray = None` and default it to a
   neutral value in `__post_init__`, with a comment saying why that value is neutral.
4. **Every CR ships an off-path byte-identity test** modelled on
   `tests/test_counter_uas.py::test_off_is_byte_identical`.

Run the suite with `conda run -n mgl python -m pytest tests/ -q` (127 tests, about 2 min).

---

## CR-1 Blue behavior layer core

**Priority:** P1. **Status:** not started. **Blocks:** CR-2, CR-3, CR-4.

### Why

The control-modality axis currently changes a **gain**, not a **behavior**. `c2.py` resolves
modality to a scalar `control_quality`, `motion.py` consumes it as `v * (0.35 + 0.65 * q)`, and
`planning.py` gives every blue ground vehicle the same single script regardless of modality. The
paper's headline axis is a knob on one behavior.

### Interface

New module `src/sandtable/behavior.py`, following `c2.py`'s shape.

```python
# mode codes, int8, stored per entity
TELEOP = 0; WAYPOINT = 1; LEADER_FOLLOW = 2; SENTRY = 3

@dataclass
class Behavior:
    mode: int                 # primary mode for blue ground this scenario
    follow_mode: str          # "link" | "behavior"   (CR-3)
    teleop_stop: bool         # CR-2
    track_timeout: int
    state: np.ndarray         # int8 per entity, current mode
    interventions: np.ndarray # int32 per entity, running count (CR-4)

def build_behavior(scn: Scenario, ent: Entities) -> Behavior | None: ...
def step(ent, bhv, op, comms, scn, k, rng) -> None: ...
```

### Wiring

`behavior.step` runs **after** `c2.step` and **before** `planning.step`, matching the existing
ordering in `sim.run_mission`. Pass the object into planning the way `pers` already is:

```python
planning.step(ent, world, scn, spawn_x, pers=pers, bhv=bhv)
```

`planning.step` keeps its current contract (mutates `ent.tgt_x/tgt_y` in place). When `bhv is None`
it must take exactly today's code path.

### Key implementation note: no change to `motion.py` is required

`motion.step` computes `v = np.minimum(v, dist / dt)` where `dist` is the range to the target.
Setting an entity's target to its own current position therefore yields `v = 0` exactly. Both
`SENTRY` and a halted `TELEOP` agent are expressible purely as a target assignment, so the whole
behavior layer lives in planning-target space. Do not add a speed override to `motion.py`.

### Modes

| Mode | Target rule |
| --- | --- |
| `TELEOP` | Advance on the lane only while the link is up and `await_until < 0`. Otherwise target equals own position. See CR-2. |
| `WAYPOINT` | Today's behavior: independent pure-pursuit carrot along the `route_bias` lane. |
| `LEADER_FOLLOW` | See CR-3. |
| `SENTRY` | Target equals own position. Sensing and engagement continue unchanged. |

### Recovery triggers

Evaluated in this priority order, per living blue ground entity:

| Trigger | Condition | Transition |
| --- | --- | --- |
| `WAIT_FOR_OPERATOR` | `mode == TELEOP` and `ent.await_until[i] >= 0` | hold in place |
| `STOP_ON_LINK_LOSS` | `mode == TELEOP` and link down | hold in place |
| `HALT_ON_LEADER_LOSS` | leader dead, or leader track older than `track_timeout` | `SENTRY`, then `WAYPOINT` if the follower holds the route |
| `FALL_BACK` | wait exceeded `op.patience` | `WAYPOINT` at `q_fallback` |

Reuse `c2.py`'s existing state rather than duplicating it: `ent.await_until` already encodes a
pending request, and `op.patience` already encodes the give-up threshold.

### Modality selects the repertoire

- `control_mode == "direct"` maps to `TELEOP` primary, falling back to `WAYPOINT`.
- `control_mode == "supervisory"` maps to `WAYPOINT` (or `LEADER_FOLLOW`) primary, `SENTRY` on
  trigger, operator by exception only.

`control_quality` is unchanged and still multiplies speed and engagement. It now scales a behavior
instead of standing in for one.

### Params

| Param | Default | Meaning |
| --- | --- | --- |
| `blue_behavior` | `None` | `None` keeps today's path exactly. `"auto"` derives the mode from `control_mode`. A mode name forces it. |
| `track_timeout` | 40 | Steps before a dead-reckoned leader track is stale. |

### Tests

1. `blue_behavior=None` is byte-identical to the pre-change build on the same seed, for at least
   `uc3_route_defilade` and one C2 scenario.
2. `SENTRY` produces exactly zero displacement over a full mission.
3. A scenario with `blue_behavior="auto"` and `control_mode="supervisory"` on a clean link is
   byte-identical to `blue_behavior=None`, because supervisory-with-good-comms reduces to `WAYPOINT`.
   If it is not, the mode mapping is wrong.

---

## CR-2 Teleoperation stop semantics

**Priority:** P1. **Status:** not started. **Depends on:** CR-1.

### Why this is a correctness issue and not a refinement

`c2.py` defaults `q_stall = 0.30`. `motion.py` computes `v * (0.35 + 0.65 * q)`. So a direct-control
vehicle whose operator request was **dropped** keeps driving at `0.35 + 0.65*0.30 = 0.545`, that is
**54.5% of full speed**, for `patience` steps, and then falls back to `q_fallback = 0.50`, that is
**67.5%**. A teleoperated vehicle with a severed link is stopped, not doing 55%.

This biases the model **against the paper's own headline finding**. It softens the cost of direct
control at exactly the ladder rungs where the paper claims that cost is largest. The current numbers
therefore understate the modality crossover rather than exaggerate it, which is the safer direction
to be wrong in, but it is still undocumented and must not stay implicit.

Note the fallback value is separately defensible: an agent that gives up waiting and reverts to
onboard waypoint autonomy legitimately keeps moving. The problem is specifically `q_stall`, the
**awaiting** state.

### Change

Add param `teleop_stop`, default `True`. When true and the agent is in `TELEOP` with a pending or
dropped request, hold in place (target equals own position) instead of applying the `q_stall` speed
multiplier. Setting `teleop_stop=False` reproduces today's behavior exactly, so the old numbers stay
reachable as an ablation.

### Reporting obligation

Whichever way this lands, the paper must state which semantics produced its numbers. If the
published sweep used the 54.5% behavior, say so and characterize the direction of the bias.

### Tests

1. `TELEOP` with the link forced down yields zero displacement across the mission.
2. `teleop_stop=False` is byte-identical to the pre-CR-2 build.
3. Direct-mode mission time is strictly longer with `teleop_stop=True` than `False` at ladder rungs
   C3 and worse.

---

## CR-3 Leader-follower, and the link-versus-behavior contrast

**Priority:** P2. **Status:** not started. **Depends on:** CR-1.

### Why

Two facts about the current package:

- `ent.leader` and `ent.role` are **populated at spawn and never read**. `scenario.py:126-127` sets
  `role = 0` for the first entity of each force group and `leader = i - k` for the rest. Nothing in
  `src/` consumes either field. The formation bookkeeping is already allocated and wired to nothing.
- `planning.py` documents its independence as a feature: every vehicle navigates "independently
  toward the objective ... robust to any vehicle's loss (no dead-leader dependency)." That is the
  most comms-robust arrangement possible, so there is currently **no formation for degraded comms to
  break**. The one design that a degraded link would genuinely punish, and the one fielded Army
  thread (leader-follower resupply), is absent.

### Change

Implement `LEADER_FOLLOW`. Followers (`ent.role == 1`) hold a column station `formation_spread`
behind the vehicle ahead. The leader (`ent.role == 0`) runs `WAYPOINT`.

Two follower variants, selected by param `follow_mode`. **The difference between them is the
experiment**, reproducing Cheung, Rawashdeh and Mohammadi 2022 (`10.3390/app12199863`) at mission
level:

- `follow_mode="link"`: the follower needs the leader's current pose over the comms link. Use the
  existing `comms.delivered(rng)` for message survival. On a dropped or late message it holds a
  stale station, which drifts as the leader moves. This is their "basic delayed follower."
- `follow_mode="behavior"` (default): the follower keeps an on-platform track, last known leader
  pose plus heading and speed, dead-reckoned forward, and continues the column with no live message.
  This is their "Behavior Manager" analogue.

Their published result is a **13.33% to 86.61% reduction in path error** for behavior-based over
delayed-follower, across jammer types and path plans. That is simulation and scores path error, not
mission outcome, so treat a matching **sign** as confirmation and do not expect the magnitude to
carry over. A sign match with a different magnitude is a reportable multi-fidelity finding, not a
failure.

### RNG discipline

`follow_mode="link"` draws from `comms.delivered(rng)`; `"behavior"` does not. Draw the same number
of values on both paths, exactly as `c2.py` does for the EW-immune link, or the two variants will
not be comparable on a shared seed.

### Tests

1. Killing the leader mid-mission drives followers into a recovery state and the mission still
   terminates (no hang, no NaN).
2. As the ladder worsens from C0 to C5, `follow_mode="link"` degrades more than `"behavior"`. Assert
   the **sign** of the difference only.
3. Both variants consume the identical RNG stream on the same seed.

---

## CR-4 Intervention rate KPI

**Priority:** P2. **Status:** not started. **Depends on:** CR-1.

### Why

`doc/scenario.md` already asks for this, because takeover rate is how the Army actually measures
ground autonomy maturity. The behavior layer makes it nearly free: count transitions into
`WAIT_FOR_OPERATOR` and `FALL_BACK`. Reporting it makes SandTable's output commensurable with how
GVSC reports, which is worth more than another internal-only metric.

It also lands a metric family the project promised. `metrics.py` already anticipates this: its
docstring says the five metric families map onto its fields and "more families are added as the C2,
comms/EW, and air layers land."

### Change

Add to the dict returned by `metrics.compute`:

| Key | Meaning |
| --- | --- |
| `interventions` | total recovery-trigger transitions over the mission |
| `intervention_rate` | interventions per blue-ground vehicle-hour |

Both must be `0.0` when the behavior layer is off, so every existing recorded number is unchanged
and no regenerated CSV shifts.

### Required qualifier when reporting

Terrain enters SandTable as a speed raster and a cover tradeoff, never as autonomy difficulty that
forces a takeover. This metric therefore measures **comms and operator-queue contention only**, not
off-road autonomy difficulty. Any table or figure carrying it must say so, or a reader will assume
it is comparable to a field-measured takeover rate. It is not.

---

## CR-5 Station keeping, and `formation_spread` as a design variable

**Priority:** P3. **Status:** not started. **Depends on:** CR-3.

`formation_spread` is exposed to the optimizer as a design variable over `[20, 120]`
(`src/sandtable/plugin.py`), but its only effect is the spawn laydown (`scenario.py:110`), because
`planning.py:62` reads it and immediately discards it (`_ = spread  # reserved for the richer
formation model`).

The initial column depth does partly persist, since each vehicle pursues its own carrot from its own
x. But there is **no station keeping**: nothing restores spacing after terrain-speed variation pulls
the column apart, and no vehicle's behavior depends on any other's. So an optimizer sweeping
`formation_spread` over a 6:1 range is mostly sweeping a starting condition that then drifts.

Once CR-3 lands, `LEADER_FOLLOW` gives `formation_spread` a live meaning as the commanded column gap.
Until then, treat any published sensitivity of an outcome to `formation_spread` with suspicion and
check whether the effect is really an initial-laydown effect.

---

## CR-6 Endurance is allocated and never decremented

**Priority:** P3. **Status:** not started, needs a scope decision.

`ent.fuel` is documented as "seconds of endurance remaining (air)" and populated at spawn from
`pt.endurance` (`scenario.py:129`). Nothing decrements it and nothing reads it. Air platforms
therefore loiter indefinitely.

This matters beyond tidiness: the FP6111 SOW names **power systems** as a cyber-physical element to
model, and `doc/lit-ideas.md` Part 0 lists it as the one promised element with zero literature
coverage in any search round. It also bounds the UAS overwatch concept directly, since
`planning.overwatch_stations` parks the recon swarm on loiter stations with no endurance limit, and
an aerial comms relay is only a comms answer for as long as it can stay up.

Decide before implementing: is endurance in scope for the current paper, or deferred? If deferred,
say so in the limitations rather than leaving an allocated-but-dead field that reads as an
oversight.
