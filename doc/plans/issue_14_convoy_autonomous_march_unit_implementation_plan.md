# Implementation Plan: Convoy Autonomous March Unit and Personnel Exposure (Issue #14)

**Issue**: [#14 Convoy: autonomous march unit and personnel exposure](https://github.com/VadimSokolov/sandtable/issues/14) (part of #7)
**Roadmap**: Phase 4: Autonomy, C2 & Force Protection
**Branch**: `issue-14-convoy-autonomous-march-unit` -> `convoy-dev`
**Status**: Proposed plan, 2026-10-28. Based on the issue body and the author's Oct 20 source-review comment, and on the code of `convoy-dev` at `9253308`.
**Implementation status (2026-10-28)**: implemented with the simplest assumptions. Not implemented, pending Vadim's decisions: equal-cargo escort layout (3.5), `follow_mode="human"` for the manned arm (3.4), `leader_loss_policy` `halt` (the existing waypoint fallback is used). Everything else in sections 3.1 to 3.3 and 3.6 is in, with tests in `tests/test_convoy_autonomous_unit.py`.
**Depends on**: #8 (march unit, roles; done), #9 (cargo and delivery metrics; done), #12 (security vehicles; done). Related, not blocking: #17 (leader-loss policy), #18 (Red target priority), #19 (one console per march unit).

---

## 1. What the issue asks for

1. An optional per-vehicle **crew count** in `Entities`. Defaults (Oct 20 comment, ATP 4-11 2-56): manned truck 2, autonomous march unit's control vehicle 2, security vehicle 3, autonomous truck 0.
2. A **`crew_steps_at_risk`** metric: per step, the sum of the crew of every living Blue vehicle within weapon range of at least one living Red shooter, summed over steps. Detection is not required, so it does not depend on Red's sensing. It is not `blue_exposure`, which counts every living Blue entity regardless of crew or range.
3. The **autonomous march unit** as a `convoy` configuration: one manned control vehicle leading four autonomous trucks on `LEADER_FOLLOW`.
4. Also from the comment: report `crew_steps_at_risk` **by role** (parts sum to the total) and add **`crew_lost`**.

**Acceptance criteria**
- All vehicles manned and metric not requested: existing metrics unchanged, byte-identical (style of `tests/test_counter_uas.py::test_off_is_byte_identical`).
- On one seed, changing only crew counts leaves every non-crew metric unchanged.
- `crew_steps_at_risk` is 0 if no Red shooter is ever in range. It equals crew x steps alive if every living vehicle is in range throughout.
- By-role split sums to the total.
- Both arms read against #9 (delivery rate, time to delivery, cargo lost) at each comms rung C0 to C5 (`comms_level`).

## 2. What already exists (verified in the code)

| Need | State on `convoy-dev` |
|---|---|
| Roles, march-unit layout | `convoy.py`: `roles` list or `security_ratio`; `march_unit_size` 5 with `["control","cargo","cargo","cargo","cargo"]` is expressible today. Spec requires `march_units_per_serial` >= 2 and total >= 6, so the smallest autonomous arm is 2 units (10 vehicles). |
| Leader-follower | `behavior.py`: `LEADER_FOLLOW`, `follow_mode` (`link`/`behavior`), `follow_topology`, track age and timeout. Active only when `blue_behavior` is set. `ent.leader` already points each follower at its unit head. |
| Delivery metrics | `metrics._cargo_delivery_metrics`: `delivered_frac`, `time_to_delivery`, `cargo_lost`, `cargo_success`, `cargo_throughput`. Only `ROLE_CARGO` carries payload. |
| Comms ladder | `comms_ew.build_comms` reads `params["comms_level"]` 0..5. |
| Crew / people | **None.** No `Entities` field. `c2.py` "crew" means operator consoles, not vehicle occupants; do not reuse the name. |
| Exposure | `sim.py`: `blue_exposure` counts living Blue entities per step (vehicle-steps), accumulated just before the goal/termination checks. |
| Succession | `behavior._update_convoy_succession` promotes the earliest living vehicle of a march unit to head when the head dies. Runs only in `LEADER_FOLLOW`. |
| Escorts | Done in #12 (`security_ratio`, `security_ptype`). |

## 3. Design

### 3.1 Configuration (all optional; absent = today's behaviour)

New `convoy` keys (flat params also resolve, via `CONVOY_KEYS`), validated in `validate_convoy_spec`:

- `autonomy_arm`: `null` | `"manned"` | `"autonomous_march_unit"`.
  - `"manned"`: crew from the role table below; behaviour unchanged (every truck has a driver and navigates on its own mode; no follower link/sensor dependence).
  - `"autonomous_march_unit"`: `march_unit_size` is forced to 5 and roles to `control` + 4 `cargo` unless `roles` is given explicitly; crew table below; `blue_behavior` defaults to `"leader_follow"` (an explicit `blue_behavior` or `follow_mode` in params wins). The control vehicle is the head; the four trucks are unmanned followers.
- `crew`: optional override, a dict role -> int (`{"control": 2, "cargo": 0, "security": 3, "recovery": 2}`) so the isolation test and sweeps can change crew only. Values are non-negative ints, validated.
- `leader_loss_policy`: `"continue"` (default, existing waypoint fallback) | `"halt"`; only used by the autonomous arm.
- `crew_metrics`: bool, default false. Turns the metrics on without an arm. Implied true when `autonomy_arm` or `crew` is declared.

**Default crew table** (the issue's numbers; sources checked 2026-10-28, see `doc/plans/issue_14_open_questions_ar.md`):

| Role | manned arm | autonomous arm | Source |
|---|---|---|---|
| control | 2 | 2 | driver + march unit commander (ATP 4-11 M-5, p. 81; verified in the publication) |
| cargo | 2 | 0 | driver + assistant driver (ATP 4-11 2-56, p. 15; verified) / unmanned (M-1: full autonomy removes drivers and vehicle commanders) |
| security | 3 | 3 | driver, vehicle commander, gunner: CPP concept (Army Sustainment 2021) and CALL 18-10; secondary sources, an assumption for the exact manifest |
| recovery | 2 | 2 | **assumption**: M984 cab is 2, M88A2 is 3; variant-dependent, no directive found |

### 3.2 Data model

`Entities.crew: np.ndarray` (int16), defaulted in `__post_init__` to zeros, and assigned in `scenario.build_entities` from the convoy role and the table/override when the metrics are on. Zeros when off means nothing downstream can read a nonzero crew by accident. **Crew never feeds dynamics** (no change to movement, engagement, sensing, c2 or behaviour); that is what makes the isolation test true by construction.

### 3.3 `crew_steps_at_risk` (in `sim.py`, only when `crew_metrics`)

After the engagement and cuas steps and next to the `blue_exposure` accumulation (so "steps alive" has one definition across the codebase):

```
shooters = alive & (side == RED) & (weapon_range > 0)      # definition below
blue     = alive & (side == BLUE) & (crew > 0)
d        = hypot(x[blue,None] - x[None,shooters], y[blue,None] - y[None,shooters])
at_risk  = (d <= weapon_range[None,shooters]).any(axis=1)
crew_at_risk_steps += crew[blue][at_risk]        # per role via a (n_roles,) bincount
```

- "Red shooter" = living Red entity with `weapon_range > 0` **and `pk_base > 0`** (an entity that cannot kill is not a shooter). Not conditioned on `seen`, line of sight or ammo, matching the issue's "detection is not required" and keeping the metric independent of Red sensing.
- Each crew member counts **once per step** however many shooters cover the vehicle (not once per shooter-vehicle pair). Both rules are model definitions: no standard military metric matching this one was found in public sources, so the docs must call it a model-defined geometric exposure, not casualty risk. Mines, indirect fire and air-delivered weapons are outside the metric.
- Range only; no line-of-sight term. With the #16 street graph, buildings reduce true exposure, so this metric is an upper bound there. A separate `crew_steps_at_risk_los` variant is out of scope.
- Cost O(N_blue_crewed x N_red) per step; only runs when requested.
- Integer arithmetic (crew is int, counts are int), so the by-role parts sum to the total exactly, not to a tolerance.

Output keys (only when requested): `crew_steps_at_risk`, `crew_steps_at_risk_control`, `_cargo`, `_security`, `_recovery`, `crew_total` (initial crew), `crew_lost`, and `crew_lost_<role>`.

`crew_lost` = initial crew minus crew of vehicles alive at the end. A killed vehicle kills its whole crew (the model has binary vehicle hp, so no partial casualties); stated in the docs.

### 3.4 The autonomous arm's behaviour

The arms differ in who rides and what followers depend on:
- **manned**: followers are driven by people who keep route, pace, order and gap (ATP 4-11 G-11; ATP 4-16 App. C). So manned vehicles hold station on the vehicle ahead with human perception: no link or sensor-lock dependence and no track loss. This needs a small new follow variant in `behavior.py` (`follow_mode="human"`: station on the predecessor from ground truth within a sensing range, never losing the track). Independent waypoint navigation was rejected because it would compare crew and column discipline at the same time.
- **autonomous**: followers run `LEADER_FOLLOW`. `follow_mode="link"` loses the track under jamming; `follow_mode="behavior"` dead-reckons. Both are existing mechanics (#8, CR-3). The sweep reads each at C0 to C5.

**Head loss in the autonomous arm** is the one place this issue must not silently inherit existing behaviour. Today succession promotes any living vehicle to head, and with `HALT_ON_LEADER_LOSS` the code falls back to independent waypoint navigation. A promoted unmanned truck would become the "commander" of a unit with no human in it. Plan: a spec key `succession`: `"any"` (default, existing) | `"manned_only"`, and `autonomy_arm="autonomous_march_unit"` defaults it to `"manned_only"`. With `manned_only` and no manned survivor in the unit, the unit has no head. Public sources give no rule for this: ATP 4-11 does not say, ADP 6-0 covers human succession of command only, and no ATV-S documentation was found. So the behaviour is a parameter, not a claim: `leader_loss_policy` = `"continue"` (existing waypoint fallback) | `"halt"` (followers hold). Results that depend on head loss are reported under both values. A counter `autonomous_headless_steps` (follower-ticks with no manned head) makes the situation visible. The policy itself, and any rule for a manned escort or wrecker to take over, belong to #17.

### 3.5 Escorts and the reference convoy

ATP 4-11 G-7 counts every vehicle assigned to a march unit (up to 25) in its size, and G-8 adds command and support vehicles on top of the task vehicles; G-10 and G-13 leave the security ratio to theater policy. So security vehicles are inside the unit total but additional to the cargo count. Plan: the arms are compared at **equal cargo (task) vehicle count**, and `march_unit_size` grows by the number of escorts. For the 15-cargo-vehicle reference with 3 escorts: manned crew = 15x2 + 3x3 = 39, autonomous = 3x2 + 3x3 = 15 (ratio 2.6, matching the issue comment); with 5 escorts 45 and 21 (2.14). This needs `build_convoy_layout` to size the unit from a cargo count plus an escort count when `autonomy_arm` is declared; existing `march_unit_size` specs are untouched.

### 3.6 Sweep tool

`tools/make_autonomy_arms.py` (patterned on `tools/make_contact_arms.py`): arms `manned` and `autonomous` (x `follow_mode` link and behavior) at `comms_level` 0..5, N seeds, writing a labeled JSON with the #9 delivery keys, `crew_steps_at_risk` (total and by role), `crew_lost`, and `escort_vehicle_steps`. Arm labels are written into each row. Optional escorts via #12 `security_ptype`.

## 4. Files

| File | Change |
|---|---|
| `src/sandtable/convoy.py` | New keys, validation, role -> crew table, autonomous-arm layout expansion, `succession` |
| `src/sandtable/entities.py` | `crew` array, neutral default |
| `src/sandtable/scenario.py` | Assign crew per role when enabled |
| `src/sandtable/behavior.py` | `manned_only` succession, `autonomous_headless_steps` |
| `src/sandtable/sim.py` | `crew_steps_at_risk` accumulation, `crew_lost`, output keys (gated) |
| `src/sandtable/metrics.py` | Helper to assemble the crew metric dict |
| `tools/make_autonomy_arms.py` | New sweep |
| `tests/test_convoy_autonomous_unit.py` | New |
| `doc/scenario.md` | Document keys, defaults, definitions, limitations |

## 5. Tests (`tests/test_convoy_autonomous_unit.py`)

1. `test_off_is_byte_identical`: no arm, no crew, no `crew_metrics` vs explicit `null`/`false`, several seeds on `uc3_convoy.json`, using `same_run`. Output has none of the new keys.
2. `test_crew_changes_nothing_else`: on one seed, two different `crew` overrides give identical results on every non-crew key.
3. `test_zero_when_no_shooter_in_range`: Red placed beyond every Blue vehicle's reach for the whole run (or Red `weapon_range` 0): `crew_steps_at_risk == 0`.
4. `test_full_range_equals_crew_times_steps_alive`: Red with very large `weapon_range` and `pk_base` 0 (no losses): metric equals `sum(crew) * steps`. Plus a variant with one vehicle killed at a known step, checking the alive-step accounting.
5. `test_by_role_sums_to_total`: exact equality across several seeds and both arms.
6. `test_crew_defaults_per_role_and_arm`: the table above, both arms; reference convoy: manned 15 vehicles (all 2) = 30 crew, autonomous 3 control = 6 crew (ratio 5.0).
7. `test_crew_lost`: killed vehicles remove exactly their crew; by-role parts sum.
8. `test_autonomous_arm_layout`: one control + four cargo per unit plus the escorts, `LEADER_FOLLOW` on the followers, `blue_behavior` default honoured and overridable; equal cargo count across arms, and the reference crew totals (39/15 with 3 escorts, 45/21 with 5).
9. `test_succession_manned_only`: head killed in the autonomous arm, no unmanned follower is promoted (a manned escort in the same unit may be), `autonomous_headless_steps` counts, and `leader_loss_policy` `halt` vs `continue` differ as specified; with `succession="any"` the existing promotion is unchanged.
10b. `test_manned_arm_holds_station`: manned followers never lose their track under C5 (`follow_mode="human"`), while autonomous `follow_mode="link"` does.
10c. `test_shooter_definition`: a Red entity with `pk_base == 0` does not add exposure; two shooters covering one vehicle count its crew once.
10. `test_spec_validation`: unknown arm, negative or non-int crew, unknown role keys, `succession` values.
11. `test_arms_vs_comms_ladder_smoke`: both arms run at C0 and C5 and produce the #9 delivery keys (no result claim asserted).

## 6. Risks and limitations

- **No partial casualties.** Vehicle kill = whole crew lost. Overstates crew loss for hits that would not kill everyone; state it wherever `crew_lost` is reported.
- **Range-only exposure.** Overstates exposure behind buildings (#16). Upper bound.
- **Control vehicle concentration.** In the autonomous arm the control vehicle carries every human, and Red reportedly targets it (Oct 20 comment: Defense News 2024, TC 7-100.2). Red's current rule is nearest-target, so this issue under-represents that risk. Target priority is #18; the by-role split makes the concentration visible meanwhile. Do not report autonomous-arm exposure advantages without that caveat.
- **Console model unchanged.** `c2.py` attention divides `span_capacity` by all Blue vehicles (about lines 380 to 383) and ignores operator count, which penalises a 15-vehicle convoy (attention 0.27, quality 0.767 per the comment). One console per march unit is #19. Any C0 to C5 comparison here that uses `control_mode` carries that bias; the plan does not change `c2.py`.
- **Headless unit.** No public rule exists for follower behaviour after control-vehicle loss; it is a swept parameter (`leader_loss_policy`), not a result. The takeover rule is #17.
- **Public-source gaps.** ATP 4-01.45 and TC 4-11.46 are restricted and were not read; security crews (3), recovery crew (2) and escort ratios come from secondary sources and are labeled assumptions.

## 7. Increments

Single increment is reasonable: crew array and metrics (3.1 to 3.3) are small and independent of the arm; the arm and succession (3.4) is the larger piece. If review prefers, split into A (crew, metrics, tests 1 to 7, 10) and B (arm, succession, sweep, tests 8, 9, 11).

## 8. Decisions taken from the source review (to confirm with the issue author)

Evidence is in `doc/plans/issue_14_open_questions_ar.md` (ATP 4-11 read directly; other sources via a ChatGPT literature pass, partly unverified).

1. **Escorts:** inside the unit total, additional to the cargo count; arms compared at equal cargo count (section 3.5).
2. **Recovery crew:** 2, labeled assumption (M984 cab 2, M88A2 3).
3. **Shooter:** living Red with `weapon_range > 0` and `pk_base > 0`; each crew member counted once per step; model-defined metric.
4. **Manned arm:** holds station on the vehicle ahead with human perception (`follow_mode="human"`), not independent waypoint navigation.
5. **Head loss:** `succession="manned_only"`; the follower response is a swept parameter `leader_loss_policy` (`continue` | `halt`), reported under both until #17.

Still needed from the issue author: confirm 1 (equal cargo count) and 4 (manned following), the two that change the layout and add a behaviour variant.
