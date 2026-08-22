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
| CR-7 operator load metrics | scores concepts on operator feasibility | the load half of teaming, objective (2) |
| CR-8 formation robustness score | makes formation quality a computed number | secondary |
| CR-9 budgets and bursty channel | prices the command architectures honestly | how the human's decisions actually reach the team |

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

---

## CR-7 Operator utilization and attention-switching cost as load metrics

**Priority:** P2. **Status:** not started. **Depends on:** nothing. Can land before CR-1.

### Why

Objective (2) is cognitive-load distribution, and the standing objection is that a constructive
simulation has no operator to measure. The literature answers it, and SandTable can compute the
answer almost for free.

Donmez, Nehme and Cummings (`10.1109/TSMCA.2010.2046731`) use operator **utilization** as a real-time
workload surrogate inside a discrete-event multi-vehicle simulation, calibrate the
utilization-to-wait-time relation against 74 participants, and show it predicts accurately for team
structures it was **not** calibrated on. That cross-structure validity is what makes it usable here,
because the project's first promised outcome is *novel* formation concepts.

`c2.py` already holds every piece of state this needs. It models a single shared operator server with
`service_rate`, tracks `operator_free_at`, and per-agent `await_until` and `decision_cooldown`. Nobody
is reading any of it out.

### Change

Accumulate over the mission, inside the existing `c2.step`:

| Quantity | Definition |
| --- | --- |
| `operator_utilization` | fraction of mission steps where `operator_free_at > k`, that is the server is busy |
| `mean_wait` | mean `reply - k` over serviced requests, the attention-switching wait |
| `wait_p95` | 95th percentile of the same, since overload shows in the tail |
| `queue_depth_mean` | mean number of agents with `await_until >= 0` |

Surface all four through `metrics.compute`. All must be `0.0` when `op is None`, so ground-core
scenarios are unchanged and no recorded number moves.

### Mandatory qualifier

Sarno and Wickens (`10.1177/154193129203600105`) put computational workload models at 61 to 77 percent
of variance explained. This is a **ranking instrument and an overload flag, not a NASA-TLX-comparable
score**. Any table or figure carrying it must say so. Do not label the column "workload."

### Related: `span_capacity` rests on an untransferred assumption

`c2.build_c2` defaults `span_capacity = 4.0` and uses it for attention dilution. The fan-out and
span-of-control literature behind that number (D4) is **UAV supervision**. D12 found no workload study
of a single operator supervising a **mixed ground-and-air** formation, and the project's title says
ground and air. This does not require a code change, but the default needs a source comment naming the
assumption, and the paper needs a sentence stating it.

### Tests

1. With no C2 layer, all four keys are exactly `0.0` and the run is byte-identical.
2. `operator_utilization` rises monotonically with blue count at a fixed `service_rate`.
3. `mean_wait` rises monotonically with ladder rung under `direct` and stays flat under
   `supervisory`.

---

## CR-8 Score formations by network robustness, not connectivity alone

**Priority:** P2. **Status:** not started. **Depends on:** CR-3 (needs a formation to score).

### Why

This is the most directly reusable result in the literature review for **mission design**, because it
turns "is this formation any good" into a computed number. See idea I20 in `doc/lit-ideas.md`.

Sundaram and Hadjicostis (`10.1109/TAC.2010.2088690`) prove **2f+1 vertex-disjoint paths suffice to
tolerate f malicious or compromised agents, and 2f provably do not**. Guerrero-Bonilla, Prorok and Kumar
(`10.1109/LRA.2017.2654550`) turn that into a formation-construction algorithm returning feasibility and
the required proximity relationships for a given team size and assumed f. Usevitch and Panagou
(`10.1016/j.automatica.2019.108586`) make network robustness computable from the graph Laplacian by
mixed-integer programming.

**And it corrects an assumption already in the project's literature.** Idea I2 proposes mapping ladder
rungs to algebraic connectivity (the Fiedler eigenvalue). LeBlanc et al. (`10.1109/JSAC.2013.130413`)
state that **connectivity is not adequate** to characterize resilient consensus. A formation tuned for
algebraic connectivity is **not** thereby robust to a compromised agent. The two metrics will disagree,
and that disagreement is a publishable result rather than a bug.

### Change

A pure scoring function, no coupling to the sim loop:

```python
# src/sandtable/formation_metrics.py
def comms_graph(ent, comms, scn) -> np.ndarray      # adjacency from range/link model
def algebraic_connectivity(adj) -> float             # Fiedler value, the I2 metric
def r_robustness(adj) -> int                         # the I20 metric
```

Report both per mission. Expect them to rank formations differently and say so in the paper.

### Scope guard

The theorems are about **consensus** among agents. SandTable's blue agents do not currently run a
consensus protocol; they pursue independent targets. So this scores the **communication topology's**
resilience, not a proven property of the mission outcome. Do not write that the formation "tolerates f
compromised agents" unless and until a consensus step exists. Score the graph, and say it is the graph.

### Tests

1. A fully connected graph returns the known maximal robustness for its size.
2. A path graph returns robustness 1 regardless of length, while its algebraic connectivity falls with
   length. This is the disagreement, and it should appear in a test.
3. Both metrics are `0.0` and skipped when no comms layer exists.

---

## CR-9 Charge both command arms a real budget, and make the channel bursty

**Priority:** P2. **Status:** not started. **Depends on:** nothing for the channel half.

### Why, part one: a serial simulator silently favors bidding

The project promises to compare doctrinal planning against bidding-based decision systems. Kishimoto
and Nagano (`10.1609/icaps.v26i1.13786`) showed severe synchronization overhead in parallel allocation
that **serial evaluation hides entirely**. SandTable evaluates serially. If the bidding arm is added
without charging it for the messages an auction actually needs and the time it takes to clear, the
comparison is rigged before it runs, in favor of bidding.

**Change:** both arms declare an explicit message count and a time cost per allocation decision, paid
through the existing comms model. Report messages-per-decision alongside the outcome. See idea I23.

### Why, part two: the ladder's channel is memoryless, and jamming is not

`comms_ew.py` models message loss as an independent Bernoulli draw per message
(`delivered()` returns `rng.random() >= p_drop`) with a fixed per-level latency. Real jamming is
**bursty**: losses arrive in runs, not independently.

This matters for the centerpiece result rather than being a detail. Under memoryless loss at
`p_drop = 0.35`, a direct-control agent gets intermittent service and mostly keeps moving. Under bursty
loss with the **same mean**, it can stall for a long consecutive run and then be served normally. The
distribution of stall lengths changes even though the mean drop rate does not, and stall length is what
`c2.py` converts into mission effect through `patience` and fallback. **The crossover rung could move.**

Otte, Kuhlman and Sofge (`10.1007/s10514-019-09828-5`) sweep auction mechanisms under **both** Bernoulli
and Gilbert-Elliot channels precisely because the two give different answers, and that is the closest
published work to this project's thesis.

### Change

Add an optional two-state Gilbert-Elliot channel to `comms_ew.Comms`: good and bad states with
transition probabilities and per-state drop rates, calibrated so the **stationary mean drop rate equals
the current ladder value at every rung**. That makes the comparison clean: same mean, different burst
structure, so any change in the result is attributable to burstiness alone.

| Param | Default | Meaning |
| --- | --- | --- |
| `channel` | `"bernoulli"` | `"bernoulli"` keeps today's behavior exactly. `"gilbert_elliot"` enables the bursty channel. |
| `ge_burst_len` | 4 | Mean dwell in the bad state, in messages. The mean drop rate is held to the ladder value. |

**Statefulness warning.** The Gilbert-Elliot channel carries state across draws, so `Comms` stops being
data-only. Keep the state inside the `Comms` instance built per run, never module-level, or
`run_mission` stops being a pure function of `(scenario, seed)`.

### Tests

1. `channel="bernoulli"` is byte-identical to the pre-change build at every rung.
2. Over a long run, the Gilbert-Elliot empirical drop rate matches the ladder value at each rung to
   within Monte Carlo error. Same mean is the whole point.
3. The distribution of consecutive-loss run lengths differs measurably between the two channels.
4. Report whether the modality crossover rung moves between channels. **If it moves, that is a finding
   for the paper, not a bug to tune away.**

---

## CR-10 Operator admission control  (IMPLEMENTED 2026-08-21)

### Why

The published operator works every request it receives. It has no way to notice that the
requester stopped waiting, so a request that arrives when the queue is already deeper than the
requester's patience still costs a full service slot, and the answer is thrown away on arrival.

```python
done = max(op.operator_free_at, k + lat) + 1.0 / op.service_rate
op.operator_free_at = done          # spent here, unconditionally
if done + lat - k <= op.patience: ...serviced...
else: ...the requester gave up, and the slot was spent anyway...
```

At spans above `n* = (patience + decision_interval + 1) * service_rate` this is self-sustaining:
every vehicle abandons, every abandonment still consumes the operator, the queue never drains.
Only 18% of requests get an answer at n=8 on a clean link. Packet loss is then the only thing
shedding load, which is why mission success *rose* with jamming in the published model.

This is the call-center problem with abandonment, and the standard answers apply
(`doc/lit-ideas.md` D4a).

### Change

`params["queue_policy"]`, default `"blind"` so every prior number is unchanged:

| policy | server slot on an abandoned request | requester |
| --- | --- | --- |
| `blind` | spent | waits out `patience` |
| `refund` | freed | waits out `patience` |
| `admit` | freed | told after one round trip (`2*latency`), then drives autonomously |

`refund` isolates the server-side half; `admit` adds the vehicle-side half and is the deployable
recommendation.

### Result

n=8, direct, proxy tier: clean-link success 0.512 (blind) to 0.840 (admit), and the interior
optimum in comms level disappears. Goodput inverts from rising-in-jamming to falling-in-jamming.
Full detail in `doc/autoresearch-conjectures.md`.

### Tests

`tests/test_queue_policy.py`: default byte-identity, request accounting partitions to 1.0,
unknown policy rejected, both fixed policies raise goodput at saturated span, `admit` empties the
waiting room relative to `refund`, and all three agree when the operator is never saturated.

---

## CR-11 Hold durations and the fan-out estimate  (IMPLEMENTED 2026-08-21)

### Why

`intervention_rate` counts *events*. Jamming makes each hold longer, so events per vehicle-hour
**fall** as the burden rises. The first version of the CR-4 test asserted the opposite and failed;
the failure is the finding.

### Change

`behavior.py` accumulates `hold_steps` and `alive_steps` per entity (counts only, no RNG, so the
off path stays byte-identical). `metrics.py` derives:

- `hold_fraction`, the share of live vehicle-steps spent stopped waiting on the operator. This is
  the quantity that tracks burden monotonically.
- `interaction_steps` (IT) and `neglect_steps` (NT), the observed duty cycle.
- `fan_out = 1 + NT/IT`, the Olsen and Wood capacity estimate (`10.1145/985692.985722`).

### What it is for

Fan-out has no queue in it, so it predicts capacity as if every vehicle wanting attention got it on
arrival. Cummings and Mitchell 2008 (`10.1109/TSMCA.2007.914757`) added wait time for exactly that
reason. Comparing SandTable's own fan-out estimate against the span at which measured success
actually peaks is therefore a check on a widely used HMT capacity metric, not a metric to optimize.
Conjecture C9.

### Reporting obligation

`intervention_rate` is never reported without `hold_fraction` beside it.

---

## CR-12 Analytic cross-check: the operator queue solved  (IMPLEMENTED 2026-08-21)

`tools/queue_theory.py`. Closed-form latency cut-off and collapse span, an M/M/1-tail fixed point
for goodput, and `queue_only_sim`, the request-and-abandon rules with the mission stripped out.
The stripped model reproduces the interior optimum on its own, which is what establishes that the
effect belongs to the queue rather than to terrain, sensing, or attrition. Validating the ABM
against a tractable model is the discipline the build plan committed to. Tests in
`tests/test_queue_theory.py`.

---

## CR-13 Staggered decision phase  (IMPLEMENTED 2026-08-21)

`entities.py` starts every agent's `decision_cooldown` at zero, so on step 0 all n blue agents fire
a decision event at once and the single operator opens the mission with a burst of n requests. Real
vehicles are not phase-locked. `params["stagger_decisions"]` draws a uniform starting phase in
`[0, decision_interval)`; off by default and byte-identical when off.

Found by reading the initialization, not by search, which is the argument for auditing state that
the search never varies. Its effect turned out to be small (goodput +0.01 to +0.05 at n=8), so its
value was in ruling out a startup transient as the explanation for CR-10's result rather than in
changing any number. Tests in `tests/test_stagger.py`.

### Known and deliberately unchanged

`build_c2` computes attention dilution from `(ent.side == BLUE).sum()`, which counts dead vehicles,
while the operator queue serves only live ones. So per-decision quality does not improve as the
force takes losses even though the queue drains. That is defensible (an operator's assigned span
does not shrink the instant a vehicle is hit) but it is an asymmetry, and it should be stated
wherever span-of-control results are reported.

---

## CR-15 Terrain-driven operator demand  (IMPLEMENTED 2026-08-21)

### Why

Decision events arrived at a jittered fixed rate, so the load offered to the operator was
*stationary*: every vehicle called for help at the same average rate wherever it was. Real demand
is spatially correlated. A column entering a defile needs help together, so a queue sized for the
average rate meets a burst, and the closed-form collapse threshold, which assumes stationary
arrivals, is optimistic.

This is also the missing link between terrain and the teaming loop. Before this, terrain acted only
on movement and exposure; the HMT layer never saw it.

### Change

`params["terrain_demand"]` (default 0.0, off and byte-identical) scales the inter-decision interval
by local trafficability: `interval / (1 + terrain_demand * (1 - speed_at(x, y)))`. Exactly one
integer is drawn either way, so the on and off paths stay paired on a shared seed.

### Result

At the published span of six, right at the stationary threshold of 6.30, correlated demand pushes
the queue over the edge: goodput 0.751 with stationary demand, 0.281 at `terrain_demand=2`. So the
centerpiece scenario as shipped is *just* stable only because its demand process is unrealistically
smooth. Admission control recovers it to 0.778.

### Reporting obligation, revised

The CR-4 qualifier changes. With `terrain_demand` off, terrain never raises autonomy difficulty and
the intervention rate is not comparable to a field takeover rate at all. With it on, difficult
ground does raise the call rate, which is closer to what a field takeover rate measures, but the
coupling is a modeled scalar rather than a perception stack meeting real terrain, so the comparison
stays qualitative. Both `metrics.py` and `behavior.py` docstrings now say this.

### Tests

`tests/test_terrain_demand.py`: off-path byte-identity, monotone in the coupling strength, pulls
the collapse below the published span, admission control still recovers it, supervisory pays
nothing for the same demand increase.

---

## CR-14 Multiple operator consoles  (IMPLEMENTED 2026-08-21)

### Why

The published model has exactly one operator, which turns "how many assets can a human supervise"
into a fixed ratio. Real command posts staff several consoles, and the closed form from CR-12 says
the collapse span is linear in the console count, `n* = c(P + tau)mu / d`. That makes staffing a
testable prediction rather than a parameter: if the model is right, adding a console should move a
cliff, not lift a curve.

### Change

`Operator` gains `crew_free_at`, an array of per-console next-free times, allocated only when
`n_operators > 1`, so the single-console path keeps its scalar `operator_free_at` and its exact
arithmetic. A request goes to `argmin(crew_free_at)`. With `n_operators = 1` the field is `None`
and every branch reduces to the published code, which is what keeps the off-path byte-identical.
`build_c2` validates `n_operators >= 1` and rejects a non-integer.

### Result

Measured goodput on a clear link (32 blocks x 64 reps, `st-gateB-9437187`):

| assets | 1 console | 1 + admit | 2 consoles | 3 consoles |
|--------|-----------|-----------|------------|------------|
| 6      | 0.759     | 0.905     | 1.000      | 1.000      |
| 8      | 0.170     | 0.734     | 0.990      | 1.000      |
| 12     | 0.015     | 0.449     | 0.810      | 0.991      |
| 16     | 0.007     | 0.300     | 0.045      | 0.972      |

Each column's transition brackets its own prediction: 6.30, 12.60, 18.90. The two levers are not
interchangeable. A second console doubles the span the queue carries and leaves the cliff shape
intact; admission control on one console converts the cliff into a slope. That distinction is the
one the call-center literature draws between staffing and delay announcements (Ibrahim 2018,
`10.1111/poms.12796`, see `doc/lit-ideas.md` D4a).

### Tests

`tests/test_crew.py`: off-path byte-identity at `n_operators = 1`, per-console assignment picks the
earliest free console, two consoles raise goodput at a span where one collapses, invalid counts
rejected.

### Still open

The consoles are interchangeable and the discipline is first-come-first-served. Heterogeneous
operators, handoff, dynamic span reallocation, and a triage rule that serves the request most
likely to still be waited on are all unbuilt. `n*` sizes the bank; it does not tell it how to work.

---

## CR-16 Service order: `queue_discipline`  (IMPLEMENTED 2026-08-22)

### Why the first design was scrapped before it was written

The proposal was "serve the request with the least remaining patience." Reading `c2.py` shows that
rule is a no-op here, and the reason bounds what triage can mean in this model at all. There is no
queue object: a request's whole future is fixed at arrival (`start = max(operator_free_at, k+lat)`,
`done = start + 1/mu`, `reply = done + lat`), and the queue is the scalar reservation horizon
`operator_free_at`. Requests reserve in arrival order and never sit anywhere that could be
reordered later. Every requester carries the same patience `P`, so all requests competing at a
given moment have identical slack, and reordering two feasible requests swaps *which* vehicle is
served without changing *how many* are.

So ordering can only bite through heterogeneity in what the help is worth. The model already has a
source: with `terrain_demand` on, vehicles in difficult ground request more often and therefore
crowd the queue, and because `control_quality` enters motion and engagement multiplicatively, a
quality point buys a different amount depending on the ground the vehicle is standing on.

### Change

`params["queue_discipline"]`, default `fcfs`, validated against `c2.DISCIPLINES`. The order is
computed by the pure helper `c2.service_order(op, blue, difficulty, rng)`, extracted so the sort is
testable without running a mission.

| arm | order | role |
| --- | --- | --- |
| `fcfs` | entity index, untouched | default, byte-identical |
| `random` | `rng.permutation` each step | **null control** for the RNG-reassignment confound: reordering the loop also changes which entity draws which random number, so a priority arm moves two things at once |
| `hard_first` | descending terrain difficulty | treatment |
| `easy_first` | ascending terrain difficulty | **adversarial control**; a real priority effect has to be two-sided |

The priority sorts are stable, so on uniform ground they degenerate to `fcfs` rather than to an
arbitrary permutation. That is what makes a flat result interpretable as "ordering did nothing"
instead of "the order was scrambled." Terrain is read whenever the discipline needs it, which draws
no random numbers, so widening that condition cannot perturb any arm that ignores the result.

### Tests

`tests/test_triage.py` (10): off-path byte-identity; the sort is correct in both directions with
ties in index order; both priority arms degenerate to `fcfs` on uniform ground and with no
difficulty map at all; `random` actually perturbs the run; every discipline runs and keeps its
rates in [0,1]; an unknown discipline is rejected; and the model-level claim that ordering moves
goodput by less than 0.10 across all four arms.

The effect-size question is deliberately **not** a unit test. A first attempt asserted that the two
priority arms bracket the null on 12 seeds; it failed on noise (means of a binary metric over 12
seeds move in steps of 0.083), which is a sample-size artifact rather than a finding. Effect sizes
belong to the gated battery at the full tier; pytest asserts mechanism.

### Battery

`hopper/batteries/triage.sh`: X1 no heterogeneity (all four arms should agree), X2 heterogeneity
across span (band-limited around `n*` if anything), X3 the same contrast with admission control on
(flat if ordering only ever mattered because `blind` wastes slots), X4 coupling strength at the
congested span.

## CR-17 Closed-loop reliance and the fold band  (IMPLEMENTED 2026-08-22)

### Why

Every queue result before this one assumed a vehicle's request cycle is independent of whether its
last request was answered. That assumption is what gives the M/D/1+D model a single threshold, and
it is not obviously true of an operator-reliant vehicle: one left unanswered may ask again sooner
than one that was served. Drop it and offered load becomes a function of the state the queue is
already in, which is the one ingredient the model was missing to be bistable.

### Change

| Param | Default | Meaning |
| --- | --- | --- |
| `retry_prob` | 0.0 | Fraction of abandoned requests that return on the short backoff. 0 draws nothing, so the OFF path is byte-identical. |
| `retry_backoff` | `decision_interval` | Steps to the retry. Equal to the interval means no shortening and no band. |

The coin is drawn at abandonment, not at re-arm, so an outstanding request carries no pending draw.
The retry rescales the jittered interval `_reset_cooldown` already draws rather than replacing it,
so exactly one integer is drawn either way and the arms stay paired on a shared seed.

Also adds `operator_goodput_late` (final quarter only), because whole-mission goodput averages over
the transient and cannot distinguish "the disturbance hurt while it lasted" from "the disturbance
left the team somewhere else".

### Result

Band `(n_c, n_h)` with width `c*mu*pi*(tau-rho)*(1-a_h)/d`, in which `d` cancels at the abandonment
floor. Gated at full tier at exactly one span: +0.313 mission success and +0.572 operator goodput
on the initial condition alone, null at 3, 4, 6 and 8. `refund` and `admit` close the band by 44x
and 20x. Backoff floor `rho >= tau - 1/(c*mu*pi)` = 15.33 confirmed: the band is gated at backoffs
of 4, 8 and 12 and below the MPE at 16 and 20.

### Known and deliberately unchanged

`a_h` is endogenous, so the upper edge is bracketed rather than located. Four vehicles sits inside
the band and shows nothing, which is a basin question we did not map. `pi` and `rho` are declared,
not measured against any crew.

## CR-18 Clock the comms chain in time, not in messages  (IMPLEMENTED 2026-08-22)

### Why this is a correctness issue and not a refinement

The Gilbert-Elliot chain advanced one transition per MESSAGE. `c2.step` drew a request and its
reply back to back, so the model treated them as adjacent in channel time even though the operator's
whole service delay, tens of steps, separates them in mission time. Two requests from the same
vehicle four steps apart were likewise adjacent however many other vehicles asked in between. That
inflates round-trip delivery from `(1-p)^2` to `(1-p)(1-p_gb)` for a coding reason rather than a
physical one, and it manufactured a gated finding: a sign flip in the burstiness effect across span,
reproducible across two rungs, which does not survive the repair.

### Change

| Param | Default | Meaning |
| --- | --- | --- |
| `channel_clock` | `"message"` | `"message"` keeps today's behavior exactly. `"step"` indexes the chain by time. |

Under `step`, `delivered` advances the chain by the steps elapsed since it was last resolved, and
`reply_survives(rng, lag)` prices the reply by its own lag with `1 - p(1 - lam^L)`, which is
`1 - p_gb` at `L = 1` and decays to the marginal `1 - p`. One uniform per call either way. The
marginal drop rate is unchanged at every rung (0.0495 / 0.0995 / 0.2016 / 0.3511 / 0.5494 against
nominal), so the two channels still differ only in structure.

### Reporting obligation

Any result comparing the two channels must name the clock. The two are not variants of one model;
they are different physical assumptions about coherence time against round-trip time, and they
bracket a real surface rather than one being simply correct.

### Result

Realized round-trip delivery collapses onto the Bernoulli value at every rung, so burstiness at a
matched mean does nothing to the queue through `d`. Every published gated cell is unaffected:
Bernoulli has no chain to clock. What survives is an interaction with CR-17's reliance loop, which
is being gated against the completed repair.

## 2026-08-22: foundational audit, prompted by "question everything"

Three findings from auditing the model rather than extending it. The first two are problems with
what the paper CLAIMS, not with what the code DOES; the third is a defence of the code.

### A1. The span sweep varies span and force ratio together, and the paper reads it as span

Rung 0, `blind`, 32 replications a point, `sc_span_control`:

| n_blue | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 10 | 12 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|
| success | .531 | .375 | .500 | .688 | .562 | .375 | .469 | .750 | .906 | **.969** |
| operator goodput | 1.000 | 1.000 | .985 | .962 | .784 | .361 | .195 | .062 | .018 | **.007** |
| blue loss fraction | .641 | .594 | .578 | .400 | .552 | .580 | .512 | .388 | .315 | **.201** |

**Mission success is 97% while the operator answers 0.7% of requests.** Success has a local minimum
at seven, exactly where the queue collapses, and then climbs monotonically as the operator becomes
irrelevant. The blue loss fraction falls the whole way, which is the tell: the defenders are FIXED
at four, so a larger assault force beats them more efficiently. The sweep buys combat power along
with span and the two cannot be separated in the published design.

The manuscript reports spans one-to-two through one-to-eight. That is the dip and nothing else, so
its headline that congestion defeats direct control at high span is measured inside the window
where the confound runs in its favour, and the effect reverses on mission success just outside it.
`st-forceratio-9445778` holds the ratio at the published 6:4 and repeats the sweep.

**This does not touch the queue mechanism**, which is measured on `operator_goodput` and is
monotone, well gated and analytically predicted. It touches what the paper may say about DECISIONS.

If the confound is confirmed, there is a genuine finding underneath it rather than only a
correction: there are two ways to survive operator collapse, stay below it or go far enough past it
that the assets stop needing the operator, and the worst place to stand is on the threshold. That
is a U-shaped design curve with its trough at `n*`, and "if you must exceed n*, exceed it by a
lot" is a sharper recommendation than anything currently in the paper.

### A2. Half the force dies during the mission, so "span of control" is not a constant

`blue_loss_frac` runs 0.64 down to 0.20 across the sweep. At the centerpiece operating point it is
0.55, so a span of six is really a span of six falling to three. Reading `n*` as a staffing number
assumes a population the mission is actively destroying. The measured cliff still brackets `n*`
(between six and eight against a predicted 6.45), so the error is not large here, but the reading
is looser than the paper's presentation implies and belongs in the limitations.

### A3. The agent-based layer is NOT redundant, and the divergence is informative

The queue alone, with no terrain, sensing, or combat, was compared against full SandTable on
`operator_goodput` at sixteen operating points. Mean absolute gap 0.045, max 0.195. Away from the
cliff the two agree to within 0.014; AT and past the cliff the queue-only model over-predicts
collapse badly (rung 0, n=8: SandTable 0.195 against queue-only 0.0004; n=12: 0.018 against
0.0003).

The mission is a **demand valve**. Vehicles die or reach the objective and stop asking, so the
queue never carries the fixed population a queueing model assumes. That is the agent-based layer's
actual contribution to the queue results, it is the reason the closed form is a threshold
prediction rather than a performance prediction, and it should be said out loud in the paper
instead of left as an unexplained gap between two numbers that are presented as agreeing.

### Cleared by the audit
- `fan_out`, `hold_fraction` and `interventions` read zero in the plain `sc_span_control` direct
  configuration, which looked like the manuscript reporting zeros. It is not: the reported values
  come from `st-searchC` C9, where the behaviour layer is active, and they are 3.88 at two assets
  against a 2.15 floor. No error.
