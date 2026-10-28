# Implementation Plan: Convoy Security Vehicles and a Contact Reaction (Issue #12)

**Issue**: [#12 Convoy: security vehicles and a contact reaction](https://github.com/VadimSokolov/sandtable/issues/12) (part of #7)
**Branch**: `issue-12-convoy-security-contact-reaction` -> `convoy-dev`
**Status**: Revised plan (v2), 2026-10-28. Supersedes the first draft, which built a five-state herringbone drill that the issue does not ask for.
**Depends on**: #8 (`convoy_role`, done), #15 (`security_ratio`, done). The release rule that ends a halt depends on #17 (leader-loss policy, not started).

---

## 1. What the issue asks for

1. A **security platform type** with its own `weapon_range` and `pk_base`, filled into the convoy at a declared ratio, at positions set by the `convoy` entry from #8.
2. **One generic reaction state** in `behavior.py` (continue, halt, or disperse on contact), declared as a single rule together with its contact trigger.
3. Metric `escort_vehicle_steps`, and a labeled zero-escort counterfactual arm.
4. Contact types `receive_fire`, `lead_lost`, `detect_range` now. `ied_event` and `obstacle` later (no generator exists; see #14/#18).

**Acceptance criteria (from the issue)**
- With no security vehicles and no reaction state, output is byte-identical (style of `test_off_is_byte_identical` in `tests/test_counter_uas.py`).
- The reaction state draws no random numbers when absent.
- With a ratio declared, the security count equals ratio x vehicle count under a stated rounding rule, at the declared positions.

**Review comment (Oct 20) constraints**: ratio sweep range 0 to 1:3, 1:5 placeholder (inference, not doctrine); Blue may not see Red first; Red's response to a halt is not modeled, so a test that the best reaction depends on that cost is required before claiming the model tests the reaction.

## 2. What already exists (verified in the code, 2026-10-28)

| Need | State on `convoy-dev` |
|---|---|
| `ROLE_SECURITY`, `security_ratio` allocation | Done in `convoy.py` `build_convoy_layout` (#8, #15). Allocates `round(n_middle * ratio)` security among the `march_size-2` middle slots; explicit `roles` list overrides. |
| Per-entity `weapon_range`, `pk_base` | Exist as `Entities` columns, but `scenario.build_entities` gives the whole convoy force one `ptype`, so security vehicles are identical to cargo trucks. **This is the gap for item 1.** |
| Hold mechanism | `bhv.holding` -> `planning.step` freezes held targets at current position (`planning.py` end of step). A "halt" reaction can reuse it with no new motion code. |
| Detection | `ent.seen[j]` = Red entity j is on Blue's shared SA map. This is the `detect_range` input. |
| Incoming-fire signal | **Missing.** `engagement._side_damage` knows shooter/target pairs but records only kills (and only when `events` is passed). Hits are binary (`hp = 1`), so "hp dropped" is the same as "dead" and cannot trigger a reaction before the loss. |
| Leader loss | `behavior._update_convoy_succession` only runs in LEADER_FOLLOW mode; head loss is otherwise not observable as an event. |
| RNG | Order per tick in `sim.py`: behavior -> planning -> ... -> engagement. `_follow` draws `comms.delivered` per follower. The reaction must add no draws. |

## 3. Design

### 3.1 Configuration (all optional; absence = today's behaviour)

New keys in `CONVOY_KEYS`, validated in `validate_convoy_spec`:

- `security_ptype`: name in `scenario.platform_types`. Security-role vehicles take `weapon_range`, `pk_base`, `sensor_range`, `max_speed`, `hp` from it. Absent: unchanged.
- `contact_reaction`: `null` | `"none"` | `{ "action": "halt" | "continue" | "disperse", "triggers": [...], "release": {...} }`.
  - `triggers`: list from `receive_fire`, `lead_lost`, `detect_range` (the last takes `range_m`, default 800).
  - `release`: `{"rule": "timeout", "clear_s": 15}` now; `{"rule": "leader_policy"}` reserved and rejected until #17 lands (raise `ValueError`, do not silently ignore).
  - `disperse` is accepted by validation but implemented in Increment B. Until then it raises `NotImplementedError` at build time rather than behaving like `halt`.

`null`/`"none"` and a missing key must produce an identical resolved spec (`None`), so no new array or code path is built.

### 3.2 Ratio and rounding rule (stated, as the issue requires)

Keep the #15 rule so no existing result moves: `n_security = min(n_middle, max(0, round(n_middle * security_ratio)))` per march unit, Python `round` (half to even), where `n_middle = march_unit_size - 2` (head and recovery excluded). The test pins this for several sizes. Positions come from the `roles` list when given; otherwise from the existing allocation (security at the tail of the middle slots). **Open question for the issue author** (section 8): the issue says "ratio times the vehicle count"; this plan's rule applies the ratio to the middle slots only.

### 3.3 Incoming-fire signal (no RNG)

`engagement._side_damage` gets one optional argument, `fired_at: np.ndarray | None = None`. When given, set `fired_at[target_idx] = True` for every target that a shooter selected, after `target_idx` is computed and before `rng.random`. It reads state only, so the RNG stream is unchanged either way, and the hot path passes `None` as with `events`. `engagement.step` gains the same optional arg. `sim.run_mission` allocates and passes it only when a contact reaction is configured, and `behavior.step` consumes the previous tick's array (one-tick latency, documented).

Semantics: `receive_fire` means "a Red shooter selected this Blue vehicle as its target this tick", which is the earliest observable that precedes a kill given binary hp.

### 3.4 Reaction state machine (single rule)

In `behavior.py` add a `contact` block to `Behavior` (arrays only when configured) and `_update_contact(ent, bhv, ...)`, called at the end of `step` before `bhv.holding = hold`:

1. **Trigger** (per convoy, not per vehicle, so one contact event broadcasts to the whole convoy; broadcast is instantaneous in this increment, comms effects are #19/#17 territory): any of
   - `receive_fire`: any living Blue convoy vehicle has `fired_at` set.
   - `lead_lost`: the head of any march unit became dead this tick.
   - `detect_range`: any living Red ground entity with `ent.seen` within `range_m` of any living Blue convoy vehicle (straight-line, plus `world.los` when buildings exist, matching `_follow`).
2. **Action** while in contact:
   - `halt`: all living Blue convoy vehicles are added to `hold` (non-security only if `halt_scope: "non_security"`; default all). Security vehicles keep firing, since engagement is independent of movement.
   - `continue`: state recorded, metrics counted, no motion change (the control arm).
3. **Release** (`timeout`): when no trigger has fired for `clear_s` seconds, `contact` clears and `hold` stops. The clock restarts on every trigger.
4. Record the rising edge in `bhv.interventions` consistently with existing holds, plus the new contact counters.

No `rng` argument is read in `_update_contact`.

### 3.5 Metrics (in `metrics.py` / `convoy_metrics.py`, emitted only when configured)

- `escort_vehicle_steps`: sum over ticks of living `ROLE_SECURITY` vehicles (the cost of the ratio). Computed whenever the convoy has any security vehicles, since it is a pure count with no behavior effect.
- `convoy_contact_count`, `convoy_contact_steps`, `convoy_first_contact_step`.
- `convoy_halt_steps`: vehicle-ticks held by the reaction (separate from tasking-mode holds).
- Existing delivery metrics (#9) give the benefit side. New keys must not appear in output when the reaction is off, so existing golden outputs and `test_docs_current.py` stay valid.

### 3.6 Counterfactual arm

A sweep helper (extend `tools/make_convoy_sweep.py`) with arms labeled in the output: `no_escort_no_reaction` (the zero-escort autonomous counterfactual), `escort_no_reaction`, `escort_continue`, `escort_halt`. The label is written into the result, not just the filename.

## 4. Increments

**Increment A (this issue, required for acceptance)**: 3.1 to 3.6, `halt` and `continue` only.

**Increment B (separate commit, only after A is green and reviewed)**: `disperse` posture, i.e. the herringbone from the first draft. Corrections to carry forward from the draft:
- Heading sign: with normal `n` pointing left and `sigma = +1` meaning right shoulder, an outward-facing herringbone vehicle on the right shoulder points right of the road tangent: `theta* = theta - sigma * theta_h`, not `+`. The first draft had it inverted.
- Station comes from `ent.progress` (valid only on routed scenarios, NaN otherwise); on unrouted scenarios fall back to `halt`. Centerline/tangent from `RoutePolyline.point_at(s)`; lateral clamp from street-graph width/`world` building boxes (#16).
- The 25% deflection bonus in `engagement.py` is an invented constant with no source. Make it a declared parameter defaulting to 0 (neutral), swept rather than assumed.
- Re-forming in echelon (head first) to avoid bunching.

## 5. Out of scope

IED/obstacle contact types (no generator; #14/#18), Red target-priority and ambush template (#18), console/attention (#19), leader-loss release rule (#17), Red indirect fire on a halted column, comms-delayed broadcast, dismounts. Doctrine citations from the first draft (ATP 4-11 section/appendix numbers, edition dates) were unverified and are removed; cite only after checking the source text. The 1:3 and 1:5 ratios are inference, labeled as such in code comments and docs.

## 6. Files

| File | Change |
|---|---|
| `src/sandtable/convoy.py` | New keys, validation for `security_ptype`, `contact_reaction` (rejects `leader_policy` release and, until B, `disperse`) |
| `src/sandtable/scenario.py` | Apply `security_ptype` columns to `ROLE_SECURITY` entities |
| `src/sandtable/engagement.py` | Optional `fired_at` out-array, set before the RNG draw |
| `src/sandtable/behavior.py` | `_update_contact`, contact arrays, counters |
| `src/sandtable/sim.py` | Allocate/pass `fired_at` only when configured |
| `src/sandtable/metrics.py`, `convoy_metrics.py` | New metrics, gated |
| `src/sandtable/replay.py` | Record contact flag per frame (gated) |
| `tools/make_convoy_sweep.py`, `tools/make_mission_viewer_v2.py` | Counterfactual arms; viewer banner for contact/halt |
| `tests/test_convoy_contact_reaction.py` | New |
| `doc/scenario.md` | Document keys, trigger semantics, one-tick latency, caveat below |

## 7. Tests (`tests/test_convoy_contact_reaction.py`)

1. `test_off_is_byte_identical`: no `contact_reaction`, no `security_ptype` vs explicit `"none"`/`null`, 8 seeds on `uc3_convoy.json`, using the `same_run` pattern from `test_counter_uas.py`. Plus engagement called with and without `fired_at` yields identical state and RNG state.
2. `test_reaction_draws_no_rng`: with the reaction configured but never triggered (Red absent or out of range), the generator state after the run equals the no-reaction run's.
3. `test_security_ratio_count_and_positions`: counts for several `march_unit_size` and ratios (including a half case such as 2.5 to pin half-even rounding), positions equal the `roles` list when given.
4. `test_security_ptype_columns`: security entities carry the declared `weapon_range`/`pk_base`; others unchanged.
5. `test_spec_validation`: unknown action/trigger, `release.rule = leader_policy`, `disperse` pre-B, bad ranges raise `ValueError` with a descriptive message.
6. `test_receive_fire_trigger`: a Red shooter in range sets `fired_at` and the convoy enters contact within one tick, before any kill.
7. `test_lead_lost_trigger` and `test_detect_range_trigger` (including a building-occluded negative case).
8. `test_halt_holds_and_release_timeout`: vehicles stop, security still fires, hold ends `clear_s` after the last trigger.
9. `test_continue_is_control_arm`: `continue` changes counters only, trajectories equal the no-reaction run.
10. `test_escort_vehicle_steps`: equals alive-security-count x ticks on a no-loss run.
11. `test_reaction_is_not_dominated_by_construction` (the review comment's concern): over a seed batch, `halt` is better than `continue` on one outcome and worse on another (or on a halt-cost parameter once added), so the best reaction is not fixed independent of cost. If it is dominated, the test fails and the finding is reported, not hidden.

## 8. Open questions for the issue author

1. **Ratio denominator.** Apply the ratio to the middle slots (current, #15, byte-stable) or to the whole march unit as the acceptance wording suggests? Changing it moves #15 results.
2. **Ratio notation.** "1:3" as odds (security : others = 0.25 of total) or as a fraction (0.33)? The plan treats the key as a fraction.
3. **Halt cost.** Add a Red response to a halted column in this issue (a halted-target pk multiplier, parameterized), or leave it to #18 and ship the caveat? Test 11 is weaker without it.
4. **Release rule.** Is a timeout acceptable until #17, or should halt be left unreleased?

## 9. Risks

- **Byte identity**: all new state and metric keys are gated on configuration; the single shared-code edit is the optional `fired_at` write, which reads before the RNG draw. Test 1 guards it.
- **Halt-induced stall**: a halted column with no release hangs until timeout; the timeout is mandatory in validation.
- **Validity of the reaction comparison**: documented limitation (Red does not exploit a halt); do not report "halt vs continue" results as findings without question 3 resolved.
