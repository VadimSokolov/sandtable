# Implementation Plan: Convoy Behavior After the Head Is Lost, and a Rule That Releases a Halt (Issue #17)

**Issue**: [#17 Convoy: behavior after the head is lost, and a rule that releases a halt](https://github.com/VadimSokolov/sandtable/issues/17) (part of #7, extends #8 and #12)
**Roadmap**: Phase 4: Autonomy, C2 & Force Protection
**Branch**: `issue-17-convoy-leader-loss-policy` -> `convoy-dev`
**Status**: Proposed plan, 2026-10-28. Based on the issue body (opened Oct 20, label `enhancement`, no comments) and the code of `convoy-dev` at `777568d`.
**Depends on**: #8 (march unit, succession; done), #9 (cargo metrics; done), #12 (contact trigger and halt; done), #14 (crew, `manned_only` succession; done). Feeds #15 (the policy becomes a swept dimension).

---

## 1. What the issue asks for

1. **`leader_loss_policy`** with five values: `legacy` (default), `promote`, `absorb`, `halt`, `continue`.
2. A **handoff latency**, in steps, for `promote` and `absorb`.
3. A **halt release rule**: the halt ends when contact has been clear for N steps, or after holding at most T steps.
4. **One description** of the leader-loss behavior in the code comment, `doc/blue_behavior_design.md` and `doc/scenario.md`. Today they disagree: the code comment says `HALT_ON_LEADER_LOSS` but the code falls back to `WAYPOINT` (`behavior._follow`); the design table says `SENTRY`, then `WAYPOINT`.

**Acceptance criteria**
- Parameter absent: byte-identical output (style of `tests/test_counter_uas.py::test_off_is_byte_identical`, helper `same_run`).
- Killing a march unit head produces the stated behavior in a short run, for each of the four non-legacy values.
- `halt` with no release rule: delivery stops after the last Red shooter dies. With the release rule: delivery resumes within N steps.
- Paired run: `halt` leaves `cargo_in_transit` non-zero and `cargo_lost` equal to the killed head's cargo only; `continue` delivers the followers' cargo.

## 2. What already exists (verified in the code)

| Need | State on `convoy-dev` |
|---|---|
| Succession | `behavior._update_convoy_succession`: promotes the earliest living vehicle of a march unit to head, instantly, with no latency. `succession="manned_only"` (from #14) restricts it to crewed vehicles and leaves the unit headless if none survive. |
| Fallback when no leader | `behavior._follow`: `ref < 0 or not alive[ref]` -> `state = WAYPOINT` (counts `headless_steps` under `manned_only`). This is the effective `continue`. |
| Stale track | `trk_age > track_timeout` hands the follower back to waypoint navigation. |
| Halt | `behavior._update_contact` fills `hold`; `halt_scope` all / non_security; release is only the `timeout` rule (`clear_s`). `release.rule = "leader_policy"` is rejected in `convoy.resolve_contact_reaction` with a message pointing at this issue. |
| Triggers | `lead_lost` (a head went from alive to dead) already exists as a contact trigger. |
| Metrics | `cargo_lost`, `cargo_in_transit`, `delivered_frac` in `metrics._cargo_delivery_metrics`; `headless_steps`; contact metrics (`convoy_halt_steps`, `convoy_contact_steps`). |
| Gaps | No policy parameter. No handoff latency. No hold-time cap (`T`). No policy-driven halt (a halt exists only through a contact reaction). `absorb` has no meaning yet. No metric for the time a unit spent leaderless. |

## 3. Design

### 3.1 Configuration (all optional; absent = today's behavior)

New `convoy` keys (added to `CONVOY_KEYS`, validated in `validate_convoy_spec`, so flat search params resolve too):

- `leader_loss_policy`: `"legacy"` | `"promote"` | `"absorb"` | `"halt"` | `"continue"`. Absent or `legacy` builds no new state.
- `handoff_steps`: non-negative int, default 0. Latency for `promote` and `absorb`. Rejected for other policies when set explicitly.
- `halt_release`: dict, only for `halt`: `{"clear_steps": N, "max_hold_steps": T}`. Either or both; absent = hold indefinitely (the "no release rule" case in the acceptance criteria). Both must be positive ints.

`contact_reaction.release.rule = "leader_policy"` becomes accepted and means: release when the unit's leader-loss policy says so (see 3.4). Until then the existing error stays.

### 3.2 Meaning of each value

| Value | After a head dies |
|---|---|
| `legacy` | Today's code, untouched: instant promotion in `LEADER_FOLLOW`, then `WAYPOINT` fallback. Kept as the default so old results reproduce. |
| `promote` | The earliest eligible living vehicle becomes head after `handoff_steps` steps. During the handoff the followers keep the stale-track rule. Eligibility follows `succession` (`manned_only` excludes uncrewed trucks, so an autonomous unit with no crewed survivor stays headless). |
| `absorb` | The unit stops existing as a unit: surviving vehicles are re-attached to the nearest living march unit's tail (same serial) after `handoff_steps`, taking that unit's head as `leader`. If the whole serial is dead, falls back to `continue`. |
| `halt` | All living vehicles of the unit hold in place (SENTRY-like: speed zero, sensing and engagement continue) from the tick the loss is detected until the release rule fires. |
| `continue` | Followers drop to `WAYPOINT` at once and keep driving the route. This is the current effective fallback made explicit and named. |

The unit is the `march_unit` index (`ent.march_unit`). Loss is detected from the head's `alive` flag, as `lead_lost` already does, with the same one-tick latency.

### 3.3 State and ordering

New `Behavior` fields, created only when a policy other than `legacy` is declared: `ll_policy`, `ll_handoff_left` (int per march unit), `ll_pending_head` (int per unit), `ll_halted` (bool per unit), `ll_hold_steps` (int per unit), `ll_clear_steps` (int per unit), `leaderless_steps` (int, metric).

Per-tick order stays `behavior.step` -> `planning.step`. Inside `behavior.step`: `_update_convoy_succession` is replaced by `_update_leader_loss` when a policy is declared, then `_update_contact`, then the hold mask is merged (policy hold OR contact hold). No random draws in the new code, so RNG streams of paired runs stay aligned. A changed policy changes behavior, not the draw sequence.

### 3.4 Halt release

For a halted unit, per step:
- `clear_steps` N: count consecutive steps with no live Red shooter within weapon range of any living vehicle of the unit (same shooter definition as `crew_steps_at_risk`: alive, `weapon_range > 0`, `pk_base > 0`; no detection or LOS needed). Release when the count reaches N. This is what makes "delivery stops after the last Red shooter dies" true without a release rule, and "resumes within N steps" true with one.
- `max_hold_steps` T: release when the unit has held T steps, whatever the contact state.
- On release the unit resumes: a head is chosen as for `promote` (with zero latency) if the head is dead; vehicles return to their previous behavior.

The contact reaction's own `timeout` rule is separate and unchanged. When both a contact halt and a policy halt hold a unit, the unit is released only when both have released.

### 3.5 Single description of the behavior

- Rename the code comment in `_follow` and the design-table row to `LEADER_LOSS` and describe the five policies once in `doc/blue_behavior_design.md`; point `doc/scenario.md` at that table.
- The design table's "`SENTRY`, then `WAYPOINT`" row becomes the `halt` policy, and the code's current fallback becomes `legacy` / `continue`. The mismatch is resolved by naming, with no behavior change under `legacy`.

### 3.6 Metrics (new, gated on a declared policy)

- `leaderless_steps`: unit-steps with a living vehicle but no living head.
- `ll_halt_steps`: vehicle-steps held by the policy.
- `ll_handoffs`: count of completed promotions or absorptions.
- `first_leader_loss_step`: -1 when none.

The cargo metrics from #9 already carry the acceptance comparison; nothing new is needed for `cargo_lost` and `cargo_in_transit`.

## 4. Open questions for Vadim

1. **`absorb` semantics.** The issue names it without a definition. The plan reads it as joining a neighbouring unit's tail. Confirm, or give the intended meaning.
2. **Default handoff latency.** No public source gives handoff times for autonomous followers (the issue says so). Default 0, swept in #15.
3. **Policy under `manned_only`.** Should `promote` with no crewed survivor behave as `continue` (leaderless but driving) or `halt`? The plan uses `continue` and counts `leaderless_steps`.
4. **Scope of `halt`.** One unit, or the whole convoy? The plan holds the one unit whose head died; other units keep going unless a contact halt holds them.

## 5. Tests (`tests/test_convoy_leader_loss.py`)

1. Off: no key -> `same_run` equal to a baseline, for a plain convoy and for an autonomous-arm convoy; `legacy` explicit equals absent.
2. Validation: unknown policy, negative `handoff_steps`, `handoff_steps` with `halt`, non-positive `clear_steps` or `max_hold_steps`, `halt_release` with a non-halt policy.
3. Head kill, one test per value (`promote`, `absorb`, `halt`, `continue`): force the head dead at a known step and assert the stated behavior (new head index and tick, or held speed, or fallback state).
4. Handoff latency: `promote` with `handoff_steps = 5` has no new head for 5 steps; with `manned_only` and no crewed survivor the unit stays headless.
5. Halt without release: `delivered_frac` stops growing after the last Red shooter dies. Halt with `clear_steps = N`: delivery resumes within N steps of that death.
6. `max_hold_steps`: release at exactly T steps while a shooter is still alive.
7. Paired run (same seed): `halt` -> `cargo_in_transit > 0` and `cargo_lost` equals the head's cargo; `continue` -> followers' cargo delivered.
8. Contact interaction: contact halt plus policy halt release only when both release; `release.rule = "leader_policy"` accepted.
9. No RNG draw from the new code: the random stream state after a run is identical across all policies for a scenario where the head is never killed.

## 6. Work order

1. `convoy.py`: keys, constants, `resolve_leader_loss`, validation, accept `leader_policy` release.
2. `behavior.py`: state, `_update_leader_loss`, hold merge, `_follow` fallback hook.
3. `metrics.py` / `sim.py`: the four metrics, gated.
4. Tests in 5, then the existing convoy test files (`test_convoy_*`, `test_counter_uas.py`) to confirm nothing moved.
5. Docs (3.5) and a sweep tool `tools/make_leader_loss_arms.py` (5 policies x C0..C5, same seeds), writing `report/viz/leader_loss_arms.json` (not committed).
6. Viewer: add a leader-loss scenario to `tools/make_mission_viewer_v2.py` only if asked; the existing "Issue #17" jamming mock uses a different numbering.

## 7. Out of scope

Herringbone `disperse` (#12 Increment B); Red target priority (#18); a console per march unit (#19); route re-planning around the dead vehicle (#16).
