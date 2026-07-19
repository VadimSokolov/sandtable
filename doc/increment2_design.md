# Increment 2 design contract: two-tier C2 + comms/EW (span-of-control centerpiece)

Fixes the interfaces for the new modules BEFORE the parallel build, so subagents
do not diverge (same role Increment 0 played for the ground core). The headline
research finding to reproduce: **the optimal control modality shifts from direct
to supervisory as comms degrade, and the crossover comms level moves earlier as
span-of-control grows.** The "sensitive results" gate for this scenario is that
this crossover is visible and monotone in the sweep, not noise.

## The mechanism (minimal, cheap, layered on the existing spatial sim)

One human operator supervises N autonomous blue agents executing the UC-3-style
advance to an objective. Agents periodically hit **decision events** (a contact or
a route fork). The quality with which each decision is resolved sets the agent's
immediate tempo and exposure, which the existing motion / engagement / metrics
machinery already turns into success / time / losses. Nothing about the spatial
core changes; C2 only sets a per-agent, per-step **control_quality in [0,1]** that
modulates behavior.

### Control modality  (scenario param `control_mode` in {direct, supervisory})

- **direct** (human-in-the-loop): at a decision event the agent issues a request
  and waits for the operator. Operator decisions are high quality
  (`q_operator`, ~0.95). But the operator is a single server (`service_rate`
  decisions/step) shared across all N agents, and the request pays a comms
  round trip (`latency(C)`) and may be dropped (`p_drop(C)`). While waiting the
  agent stalls (tempo penalty); if it waits past `patience` steps it acts
  autonomously at the lower `q_auto`.
- **supervisory** (human-on-the-loop): the agent decides locally and immediately
  at quality `q_auto` (~0.7); no queue, no wait. The operator handles only rare
  exceptions. Comms degradation barely touches this branch, which is the whole
  point.

### Span-of-control

N = number of blue agents served by the single operator (the blue force `count`
in the scenario, or an explicit `agents_per_operator`). Under `direct`, the
shared operator queue lengthens with N and with the decision rate, so wait time
(hence stalls and forced-autonomous fallbacks) grows with N. Under
`supervisory`, N is immaterial to control quality.

### Comms / EW ladder  (scenario param `comms_level` C in 0..5)

`comms_ew` maps C to link quality. Suggested initial ladder (tune in the loop):

| C | latency (steps each way) | p_drop | label |
|---|---|---|---|
| 0 | 0  | 0.00 | uncontested |
| 1 | 1  | 0.05 | nominal |
| 2 | 2  | 0.10 | degraded |
| 3 | 4  | 0.20 | contested |
| 4 | 8  | 0.35 | heavily jammed |
| 5 | 16 | 0.55 | denied |

Under `supervisory`, latency/drop apply only to the rare exception channel, so C
has small effect. Under `direct`, latency + drop directly gate every decision.

## Module interfaces (fixed)

- `sandtable/comms_ew.py`
  - `@dataclass Comms{ level:int; latency:int; p_drop:float; label:str }`
  - `build_comms(scn) -> Comms`  (reads `scn.params["comms_level"]`, applies ladder;
    ladder overridable via `scn.params` for the improve-loop)
  - pure helpers: `delivered(rng, comms) -> bool` (message survives drop),
    `round_trip(comms) -> int` (steps of latency there+back).
- `sandtable/c2.py`
  - `@dataclass Operator{ service_rate:float; q_operator:float; q_auto:float;
    patience:int; queue: (small array / list of pending (agent, ready_step)) }`
  - `build_c2(scn, ent) -> Operator`
  - `step(ent, c2, comms, scn, k, rng) -> None`: advances the queue/latency model
    one tick and writes `ent.control_quality[blue]` in place for step k. Red
    agents unaffected (control_quality left at 1.0 / ignored).
  - Deterministic given (rng, state); no globals.

## New SoA fields on `Entities` (append; keep existing order stable)

- `control_quality: float array`, default 1.0  (C2 writes it for blue each step)
- `await_until: int array`, default -1  (step index a pending request resolves;
  -1 = not waiting)
- `decision_cooldown: float array`, default 0  (steps until the next decision event)

These are additive; existing tests and the ground core are unaffected because
default control_quality 1.0 is a no-op multiplier.

## How control_quality couples into the existing core (the only edits to core)

Small, guarded reads of `ent.control_quality` (all no-ops at quality 1.0):
- `motion.step`: effective tempo multiplier `*= (q_stall + (1-q_stall)*control_quality)`
  so a stalled/awaiting agent (low quality) slows (models the human bottleneck).
- `planning.step`: a low-quality agent biases toward the exposed corridor (poor
  routing) and a high-quality one toward defilade, i.e. `route_bias_effective =
  base_route_bias * control_quality` (well-served agents use cover well).
- `engagement.step`: incoming pk scaled by `(2 - control_quality)` and outgoing pk
  by `control_quality` (well-served agents shoot better and expose less).

All three are behind `getattr(ent, "control_quality", 1.0)`-style safety so the
ground-core scenarios (no C2) are byte-identical. The improve-loop tunes the
coupling strengths; the couplings above are the starting hypothesis.

## Sim loop (sim.py) additions

Insert two steps per tick before motion, only when the scenario declares C2
(`scn.params.get("control_mode")` present):
```
comms = build_comms(scn)            # once, before the loop
c2 = build_c2(scn, ent)             # once
...
for k in range(n_steps):
    if c2 is not None:
        comms_ew  # (comms is static; nothing per-tick unless the ladder is dynamic)
        c2_step(ent, c2, comms, scn, k, rng)   # sets ent.control_quality
    planning.step(...); motion.step(...); sensing.step(...); engagement.step(...)
```

## Scenario: `scenarios/sc_span_control.json`

Reuse the UC-3 world/laydown (advance to objective) with blue as N autonomous
agents. New `params`: `control_mode` (direct|supervisory), `comms_level` (0..5),
`agents_per_operator` (== blue count unless overridden), plus the coupling knobs
(`q_operator`, `q_auto`, `service_rate`, `patience`). The sweep sits on the grid
`control_mode x comms_level x N`.

## Studies

- `studies/sc_sweep.yaml`: full-factorial-ish over `comms_level` (0..5) x
  `agents_per_operator` (e.g. 2,4,6,8) for EACH `control_mode`, via two runs or a
  categorical param. Identity metric storing success / time / losses.
- `studies/sc_bo.yaml`: optional; the interesting output here is the response
  surface / crossover, so the sweep is primary. BO can find the best
  (mode, comms-tolerance) design if we parameterize a continuous autonomy level.

## Sensitivity gate (acceptance)

On `sc_span_control`: at C0, `success(direct) > success(supervisory)`; at C5,
`success(supervisory) > success(direct)`; and the crossover comms level is lower
(earlier) for larger N. Encodes the project's headline finding. Iterate the
ladder and coupling strengths until this holds cleanly (as we did for UC-3's
route_bias monotonicity).

## Increment 3 preview (air/UAS + shared-SA, UC-5) -- not built yet

Adds `domain==AIR` UAS entities as sensing assets feeding a per-side shared-SA
map (organic + relayed detections), with `comms_ew` degrading the relay. UC-5
sweep: swarm size x jam intensity x hand-off policy; gate = detection coverage
falls with jam and rises with swarm size, and shared-SA cueing measurably helps
ground engagement until the relay is jammed. Reuses `comms_ew` from Increment 2.
