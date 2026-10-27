# Implementation Plan - Issue #9: Convoy Cargo and Delivery Metrics

**Parent Roadmap**: Phase 2: Cargo & Logistics Delivery Metrics  
**Target Issue**: [Issue #9: Convoy: cargo and delivery metrics](https://github.com/VadimSokolov/sandtable/issues/9)  
**Parent Epic**: [Issue #7: Convoy baseline: eight capabilities for simulating a doctrinal Army convoy](https://github.com/VadimSokolov/sandtable/issues/7)  
**Branch**: `issue-9-convoy-cargo-delivery` -> `convoy-dev`  
**Doctrinal References**: FM 4-0 (Sustainment Operations, March 2026, Section "Logistics in Contested Environments"), ATP 4-11 (Army Motor Transport Operations, March 2026, App. G & M), `doc/contested_logistics_one_pager.md`  

---

## 1. Doctrinal Motivation and Problem Statement

### The Foundational Purpose of a Convoy
In military operations research and Army doctrine (**FM 4-0, Sustainment Operations**):
> *"A convoy exists for a single operational purpose: to deliver sustainment payload to supported combat forces in the field."*

Survivability is a constraint, but **delivery is the objective**.

### The Current Simulator Limitation
Currently in SandTable:
1. `sim.run_mission` terminates when `metrics.blue_at_goal` satisfies:
   $$\text{blue\_at\_goal} \ge \text{survive\_fraction} \times \text{assault0}$$
2. The simulation carries no payload state. A vehicle is simply a geometric point with domain (`GROUND`) and health (`alive`).
3. **The Escort Paradox**: 
   - A convoy where all cargo trucks are destroyed by an enemy ambush, but all armed escorts (`ROLE_SECURITY`) survive and reach the objective, scores as a **100% mission success**.
   - Conversely, a convoy that delivers 100% of its critical ammunition/fuel but loses half its gun trucks in a defensive rear-guard action is penalized as a partial failure.

In contested logistics (FM 4-0 and `doc/contested_logistics_one_pager.md`), cargo must become an explicit state variable and delivery must become the true mission success condition.

---

## 2. Mathematical Specification and Conservation Laws

### A. Per-Vehicle Cargo Representation
In `Entities`:
- `cargo: np.ndarray` (float64, tons/payload units): Quantity of cargo loaded at departure.
- `cargo_delivered: np.ndarray` (float64, tons): Quantity of cargo successfully delivered at the objective.

### B. Role-Based Payload Assignment
In accordance with Issue #8 and Issue #15:
- **Cargo Trucks** (`convoy_role == ROLE_CARGO`): Assigned payload capacity $C_{\text{veh}}$ (e.g., 5.0 metric tons for standard MTV/FMTV/PLS, or specified in `PlatformType.cargo_capacity` / `convoy.cargo_per_vehicle`).
- **Command & Control** (`convoy_role == ROLE_CONTROL`): $C = 0.0$ tons.
- **Armed Escort / Gun Trucks** (`convoy_role == ROLE_SECURITY`): $C = 0.0$ tons.
- **Recovery / Maintenance** (`convoy_role == ROLE_RECOVERY`): $C = 0.0$ tons.

Total Convoy Cargo Loaded:
$$C_{\text{total}} = \sum_{i \in \text{BLUE}} \text{cargo}[i] = N_{\text{cargo}} \times C_{\text{veh}}$$

### C. The Fundamental Conservation Invariant
At every simulation timestep $t \ge 0$, the universe of cargo must strictly satisfy the conservation law:
$$C_{\text{loaded}} = C_{\text{delivered}}(t) + C_{\text{lost}}(t) + C_{\text{in\_transit}}(t)$$

Where:
- **Delivered Cargo ($C_{\text{delivered}}$)**:
  $$C_{\text{delivered}}(t) = \sum_{i \in \text{BLUE}} \text{cargo\_delivered}_i(t)$$
  A living vehicle delivers its full cargo upon reaching the objective radius:
  $$\text{if } \text{alive}_i(t) == 1 \text{ and } \|\mathbf{x}_i(t) - \mathbf{x}_{\text{goal}}\| \le r_{\text{goal}} \implies \text{cargo\_delivered}_i(t) = \text{cargo}_i$$
- **Lost Cargo ($C_{\text{lost}}$)**:
  Cargo on vehicles destroyed prior to reaching the objective:
  $$C_{\text{lost}}(t) = \sum_{i \in \text{BLUE}, \text{alive}_i(t) == 0} (\text{cargo}_i - \text{cargo\_delivered}_i(t))$$
- **In-Transit Cargo ($C_{\text{in\_transit}}$)**:
  Cargo on living vehicles still advancing toward the objective:
  $$C_{\text{in\_transit}}(t) = \sum_{i \in \text{BLUE}, \text{alive}_i(t) == 1} (\text{cargo}_i - \text{cargo\_delivered}_i(t))$$

---

## 3. Mission Termination and Success Criteria

When cargo is active ($C_{\text{total}} > 0$):
1. **Delivered Fraction ($\phi_{\text{del}}$)**:
   $$\phi_{\text{del}}(t) = \frac{C_{\text{delivered}}(t)}{C_{\text{total}}}$$
2. **Delivery Success Threshold**:
   A declared target share $\phi_{\text{req}}$ (defined by `delivery_fraction` or defaulting to `survive_fraction`, typically $0.70$):
   $$\text{success} = 1.0 \iff \phi_{\text{del}} \ge \phi_{\text{req}}$$
3. **Dynamic Stopping Condition in `sim.run_mission`**:
   The simulation terminates early if:
   - **Success Condition**: $\phi_{\text{del}}(t) \ge \phi_{\text{req}}$ (Required payload delivered; record $t_{\text{reached}} = t$).
   - **Terminal Exhaustion**: $C_{\text{in\_transit}}(t) == 0.0$ (All cargo has either arrived or been destroyed; no further delivery is possible).
   - **Blue Annihilation**: No living Blue entities remain.

When cargo is NOT active ($C_{\text{total}} == 0$):
- Retains exact legacy stopping test: `blue_at_goal.sum() >= survive_fraction * assault0`.
- Ensures 100% byte-identical simulation outcomes for non-cargo scenarios.

---

## 4. Key Metrics Produced (`metrics.py`)

When cargo mechanics are active, `metrics.compute` outputs:
- `cargo_loaded`: Total tons dispatched at start of mission ($C_{\text{total}}$).
- `cargo_delivered`: Total tons successfully delivered at the objective.
- `cargo_lost`: Total tons destroyed in transit by enemy action.
- `delivered_frac`: Continuous efficiency ratio $\phi_{\text{del}} \in [0.0, 1.0]$.
- `cargo_throughput`: Average delivery throughput ($\text{kg/s}$ or $\text{tons/hr}$):
  $$\text{throughput} = \frac{C_{\text{delivered}}}{t_{\text{elapsed}}}$$
- `time_to_delivery`: Time $t$ when required delivery fraction was achieved.

---

## 5. Implementation Tasks

### Task 1: Entities State Extension (`src/sandtable/entities.py`)
- Add `cargo: np.ndarray = None` (float64) and `cargo_delivered: np.ndarray = None` (float64) to `Entities`.
- Initialize in `__post_init__` to `np.zeros(n, np.float64)` so non-cargo scenarios default to 0.0 neutrally.
- Update `Entities.allocate(n)` to allocate both zeroed float arrays.

### Task 2: PlatformType & Scenario Specification (`src/sandtable/scenario.py`)
- Add `cargo_capacity: float = 0.0` (tons) to `PlatformType` with non-negative validation.
- Add optional `delivery_fraction: float | None = None` to `Objective` (defaulting to `survive_fraction` if not specified).
- In `build_entities`, assign `cargo[i] = pt.cargo_capacity` for vehicles with `convoy_role == ROLE_CARGO`.

### Task 3: Convoy Role & Capacity Configuration (`src/sandtable/convoy.py`)
- Support optional `cargo_per_vehicle: float` in `convoy_spec` (e.g. 5.0 tons) defaulting to platform capacity or 5.0 tons for `ROLE_CARGO`.
- Ensure non-cargo roles (`ROLE_CONTROL`, `ROLE_SECURITY`, `ROLE_RECOVERY`) receive `cargo = 0.0`.
- Expose `cargo_per_vehicle` in `resolve_convoy_spec`.

### Task 4: Dynamic Delivery & Stopping Logic (`src/sandtable/sim.py`)
- In `run_mission`:
  - Detect whether cargo is active: `cargo_active = bool(ent.cargo.sum() > 0)`.
  - At each timestep:
    - For living blue entities inside `goal_radius`:
      `new_delivery = ent.cargo[at_goal] - ent.cargo_delivered[at_goal]`
      `ent.cargo_delivered[at_goal] = ent.cargo[at_goal]`
    - Check stopping test:
      - If `cargo_active`:
        - If `delivered_frac >= req_del`: record `t_reached = t`; break.
        - If `cargo_in_transit == 0`: break.
      - Else: execute existing `survive_fraction * assault0` test.

### Task 5: Delivery Metrics in `metrics.py`
- Add `_cargo_delivery_metrics(scn, ent, t_reached, t_elapsed)`:
  - Calculates `cargo_loaded`, `cargo_delivered`, `cargo_lost`, `delivered_frac`, `cargo_throughput`, `time_to_delivery`.
  - Asserts conservation invariant: `abs(cargo_loaded - (cargo_delivered + cargo_lost + cargo_in_transit)) < 1e-6`.
  - Merges into `metrics.compute` when cargo is active.

### Task 6: Mission Score Multi-Objective Integration (`src/sandtable/opt_metrics.py`)
- Update `MissionScoreMetric`:
  - When cargo is active, replace raw survival indicator with `delivered_frac`:
    $$J = w_{\text{fail}}(1 - \phi_{\text{del}}) + w_{\text{time}}\frac{T}{T_{\text{scale}}} + w_{\text{loss}}\text{loss\_frac} + w_{\text{road}}\frac{RS}{RS_{\text{scale}}}$$
  - Captures the doctrinal optimization tradeoff: Gun trucks (`ROLE_SECURITY`) carry 0 payload, but sacrificing cargo capacity for escort gun trucks preserves overall payload delivered!

### Task 7: Acceptance Test Suite (`tests/test_convoy_cargo_delivery.py`)
Write 6 dedicated tests:
1. `test_cargo_off_is_byte_identical`: Verifies 100% byte-identity across seeds when cargo is off.
2. `test_cargo_conservation_invariant`: Verifies $C_{\text{loaded}} = C_{\text{delivered}} + C_{\text{lost}} + C_{\text{in\_transit}}$ at every step.
3. `test_non_cargo_attrition_preserves_cargo`: Killing 100% of gun trucks/control results in zero cargo lost and 100% delivered fraction.
4. `test_cargo_loss_proportional_to_truck_attrition`: Killing cargo trucks reduces delivered payload tonnage accurately.
5. `test_delivery_threshold_stops_mission`: Early stopping triggers exactly when required delivery fraction is met.
6. `test_mission_score_reflects_cargo_delivery`: Verifies `MissionScoreMetric` penalizes lost cargo.

---

## 6. Acceptance Criteria

- **Byte-Identity**: Scenarios without cargo declared produce 100% byte-identical simulation logs and KPIs across all seeds.
- **Conservation**: Cargo loaded equals delivered plus lost plus in-transit at every simulation timestep without floating point leak.
- **Doctrinal Alignment**: Cargo is carried exclusively on cargo vehicles (`ROLE_CARGO`), and mission success is governed by delivered tonnage.
- **Linting & Code Quality**: 0 errors with `ruff check`, clean type annotations, and no em dashes in code or documentation.
