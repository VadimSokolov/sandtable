# Convoy Baseline (Issues #8 & #10) - Summary of Work

**References**: Army Doctrine ATP 4-11 (Tactical Convoy Operations, App. G & M), ATP 4-16 (Movement Control, App. C), FM 3-90  
**Branches**:  
- Issue #8: `issue-8-convoy-hierarchy` (Merged via [PR #20](https://github.com/VadimSokolov/sandtable/pull/20))  
- Issue #10: `issue-10-convoy-pace-time-gap` -> `convoy-dev`  

---

## Executive Summary

Implemented Phase 1 of the military convoy model in SandTable. Issue #8 established the organizational hierarchy (Columns, Serials, March Units, Sections, and Roles) with march-unit-scoped leader tracking and dynamic command succession on head loss. Issue #10 established the motion and formation mechanics: speed regulation set by the pacesetter vehicle (`speed_cap = pace` in `motion.step`), and dynamic time-distance follower stationing (`station = max(gap, v * time_gap)` in `planning.py`). The implementation is strictly opt-in, preserving 100% byte-identical simulation outcomes when unconfigured, and is validated by a 10-test acceptance suite and interactive HTML tactical replay viewers.

---

## Key Components Implemented

### 1. Convoy Hierarchy & Command Succession (Issue #8)
- **Entities SoA (`src/sandtable/entities.py`)**: Added `march_unit` (int16), `serial` (int16), `section` (int8: `HEAD`, `MAIN`, `TRAIL`), and `convoy_role` (int8: `CONTROL`, `CARGO`, `SECURITY`, `RECOVERY`), defaulting to `-1` in `__post_init__`.
- **Layout Engine (`src/sandtable/convoy.py`)**: `validate_convoy_spec` enforces doctrinal ranges ($1 \le K \le 25$, $2 \le M \le 5$, $1 \le S \le 5$, $6 \le N \le 300$). `build_convoy_layout` assigns contiguous march units and points followers to their march unit head.
- **Scenario Integration (`src/sandtable/scenario.py`)**: Integrates convoy layout into `build_entities` for Blue ground forces when `scn.params["convoy"]` is specified.
- **Command Succession (`src/sandtable/behavior.py`)**: `_update_convoy_succession` automatically promotes the earliest surviving vehicle to Head (`role = 0`, `leader = -1`, `bhv.state = WAYPOINT`) when a march unit head is destroyed.

### 2. Regulated Pace & Dynamic Time Gap (Issue #10)
- **Speed Cap in Kinematics (`src/sandtable/entities.py`, `src/sandtable/motion.py`)**: Added `speed_cap` (float, default `inf`). In `motion.step`, speed is clamped by $v = \min(v_{\text{commanded}}, \text{speed\_cap}, \text{dist} / \Delta t)$. Element heads drive at the declared `pace`, while followers retain their full surge capability (`max_speed`) to close gaps.
- **Doctrinal Bounds & Specification (`src/sandtable/convoy.py`)**: Added validation for `pace` (0 to 50 m/s), `time_gap` (0 to 60 s), and `element_time_gap` (0 to 300 s).
- **Dynamic Time-Gap Stationing (`src/sandtable/planning.py`)**: Updated follower targeting in `_behavior_targets` to $\text{effective\_gap} = \max(\text{gap}, v \times t_{\text{gap}})$. Station expands at speed and compresses to minimum standoff at low speeds/halts.
- **Succession Pace Transfer (`src/sandtable/behavior.py`)**: When a successor vehicle is promoted to Head, it inherits the march unit's pace speed cap to maintain column tempo.
- **Reference Scenario & Replay (`scenarios/uc3_convoy.json`, `tools/make_viz.py`)**: 15-vehicle reference convoy ($1 \times 3 \times 5$, `pace: 10.0`, `time_gap: 4.0`) integrated into interactive HTML viewers (`mission_viewer.html` and `player.html`).

---

## Verification & Acceptance Testing

### Acceptance Suites: 10/10 Tests PASSED

1. **Hierarchy Suite (`tests/test_convoy_hierarchy.py`)**:
   - `test_off_is_byte_identical`: 100% byte-identity across seeds when convoy is off.
   - `test_doctrinal_bounds`: Rejection of out-of-range sizes and unknown roles with `ValueError`.
   - `test_reference_convoy_layout`: Correct 15-vehicle structure (3 heads, 3 trails, 9 cargo).
   - `test_leader_pointers_per_march_unit`: March-unit-scoped leader pointers.
   - `test_head_loss_succession`: Next living vehicle promoted to head upon head loss.

2. **Pace & Time Gap Suite (`tests/test_convoy_pace_time_gap.py`)**:
   - `test_pace_time_gap_off_is_byte_identical`: 100% byte-identity when pace/time_gap are off.
   - `test_doctrinal_bounds_pace_and_gap`: Rejection of invalid pace and time gap ranges.
   - `test_steady_pace_regulation`: Pacesetter speed clamped to declared pace (8.0 m/s) while followers run unconstrained.
   - `test_time_gap_dynamic_expansion`: Follower distance expands with speed and maintains time gap within 1 dt.
   - `test_succession_inherits_pace`: Successor promoted to head inherits the pace speed cap.

### Regression & Linting
- **Core Regression Suite**: 34/34 tests passed in `test_behavior`, `test_entities`, `test_motion`, `test_planning`, `test_sim_repro`, `test_docs_current`.
- **Linter (`ruff check`)**: 0 errors across all modified and new files.
- **Conventions**: No em dashes in code or commits.
