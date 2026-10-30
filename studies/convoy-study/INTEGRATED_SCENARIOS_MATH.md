# Convoy simulator — integrated scenarios, mathematics and vehicle behavior

A study guide to the integrated model for issues #9–#19, prepared on 30 October 2026 from local code and saved results. Extending the jamming model is outside this document's scope.

> **Types of evidence:** A **worked example** uses teaching numbers and does not claim a simulation was run. A **proposed diagnostic** describes an experiment not performed here. A **saved result** comes from an existing run file and is not a general prediction about the real world.
>
> Herringbone movement and console transfer are experimental rules implemented in study adapters. Their presence in the viewer does not establish complete implementation of the corresponding issues in the core engine or field validation.

## 1. What are we simulating?

The integrated convoy has three **march units**. Each unit contains a control vehicle carrying two people, an armed escort carrying three people, and four crewless cargo trucks carrying 5 tonnes each.

| Quantity | One march unit | Entire convoy |
|---|---:|---:|
| Control vehicles | 1 | 3 |
| Armed escorts | 1 | 3 |
| Cargo trucks | 4 | 12 |
| Vehicles | 6 | 18 |
| Crew | 5 | 15 |
| Cargo | 20 t | 60 t |

```text
Control → Escort → Cargo → Cargo → Cargo → Cargo
 2 crew    3 crew    5 t     5 t     5 t     5 t
```

Escorts can engage according to their weapon characteristics and target-eligibility rules. The model does not give them independent human tactical planning.

## 2. Symbols and units

| Symbol | Meaning | Unit |
|---|---|---|
| i, j | Vehicle indices | index |
| r | Enemy index | index |
| c | Console index; distinct from vehicle cargo c_i | index |
| k | Simulation step | step |
| Δt | Step duration; 1 in these scenarios | s |
| p_i=(x_i,y_i) | Vehicle position | m |
| θ_i | Vehicle heading | rad |
| v_i | Actual speed | m/s |
| a_i | Alive=1, destroyed=0 | binary |
| q_i | Control quality | dimensionless |
| n_i | Original vehicle crew count | people |
| c_i | Original vehicle cargo | t |
| D_i | Cargo delivered by the vehicle | t |
| s_i | Distance coordinate along the route | m |
| T_i | Current movement target point | m coordinates |
| R_r | Enemy weapon range | m |

**Control vehicle:** the command/leader vehicle. **Console:** operator service, which may be hosted on the control vehicle. **Halt:** a command to stop. **Promote:** appoint an eligible successor as leader. **LOS:** unobstructed line of sight. **Arm:** one configuration in an experiment. **Seed:** the input used to initialize pseudorandom draws.

## 3. The integrated model: order within each step

```text
Communications update → C2/service → behavior → planning → motion
                                                            ↓
                                                 sensing → engagement
                                                            ↓
                                           exposure and mission accounting
```

Order matters: behavior handles a leader destroyed during engagement in a later update, not retroactively before that shot. Recovery timestamps also depend on the step-numbering convention.

The new state is not the sum of separate issue results:

$$
S_{k+1}=F(S_k,\text{scenario},\text{parameters},U_k).
$$

Here, U_k represents random draws for detection, communications and engagement. The same seed reproduces a run with identical inputs and code. It does not guarantee identical service-request streams between configurations once their trajectories diverge.

## 4. Shared equations

### 4.1 Route and following — #10 and #13

A polyline route consists of points P_0,…,P_m:

$$
L_{route}=\sum_{j=1}^{m}\|P_j-P_{j-1}\|.
$$

The function r(s) converts distance along the route into a position. Under chain following, the reference is the predecessor selected by the behavior layer:

$$
g_i=\max(g_{min},v_{ref}\tau),\qquad s_i^*=s_{ref}-g_i,\qquad T_i=r(s_i^*).
$$

The reference speed v_ref comes from tracked information when setting the target, so it may differ from the instantaneous true speed. The `formation_spread` parameter affects both initial placement and the minimum following-distance floor. Near the destination, followers stop using their following stations after the convergence line so they can enter the delivery area.

### 4.2 Motion — #10 and the motion layer

$$
\theta_i^*=\operatorname{atan2}(T_{iy}-y_i,T_{ix}-x_i)
$$

$$
\theta_i'=\operatorname{wrap}\left[\theta_i+\operatorname{clip}\left(\operatorname{wrap}(\theta_i^*-\theta_i),-\omega_i\Delta t,+\omega_i\Delta t\right)\right].
$$

The wrap operation expresses the heading difference within a single revolution; clip limits the heading change to the permitted turn rate. The maximum turn rate is ω_i.

$$
v_{raw}=v_{max}\,tempo\,traffic(p_i)\,(0.35+0.65q_i)
$$

$$
v_i=\min\left(v_{raw},v_{cap},\frac{\|T_i-p_i\|}{\Delta t}\right),\quad
x_i'=x_i+v_i\cos\theta_i'\Delta t,\quad y_i'=y_i+v_i\sin\theta_i'\Delta t.
$$

A destroyed vehicle has zero speed. The cap v_cap includes applicable speed limits; the commanded convoy `pace` is not always the achieved speed.

The experimental adapter adds slowing near the target, heading alignment before moving along a route, and waiting instead of circling toward a following station already passed. Turning in place is not realistic truck dynamics. The building guard rejects an invalid movement step; it does not find an alternative route or guarantee vehicle collision avoidance.

### 4.3 Detection and engagement — #16 and #18

$$
d_{ir}=\sqrt{(x_i-x_r)^2+(y_i-y_r)^2}.
$$

Ground detection requires a living observer and target on opposing sides, distance within sensor range, and clear LOS. Conditional on those gates:

$$
P_{detect}=1-concealment(p_{target}).
$$

Detections enter a simplified shared ground picture. This study does not simulate an individual message for every detection report.

An eligible firing target must be a living, detected enemy within weapon range and with clear LOS. Control-first priority selects among eligible targets; it does not bypass range or obstruction. The control classification uses role data: promoting a successor does not automatically reclassify it as an original control-role vehicle.

The basic destruction probability for an engagement attempt is:

$$
p_k=clip\{p_{base}(1-cover_{target})q_{shooter}(2-q_{target}),0,1\}.
$$

Additional mechanics factors can multiply this value when enabled. Draw u from U(0,1); the attempt succeeds when u<p_k. These are model probabilities, not calibrated real-weapon performance.

### 4.4 Cargo and success — #9

$$
L=\sum_i c_i,\quad D=\sum_iD_i,\quad X=\sum_i(1-a_i)(c_i-D_i),\quad I=\sum_i a_i(c_i-D_i).
$$

$$
\boxed{L=D+X+I},\qquad f_D=D/L.
$$

L is loaded cargo, D delivered cargo, X cargo lost before delivery, and I cargo on living vehicles that has not yet been delivered. Destroying a vehicle after delivery does not destroy its delivered cargo. Entering the goal area counts as delivery; no unloading duration is modeled here.

$$
\|p_i-p_{goal}\|\le150\text{ m}.
$$

The current study requires f_D≥1 by the 1800-second horizon. Success is a scenario-defined criterion, not a synonym for vehicle survival.

### 4.5 Personnel exposure and losses — #14

$$
z_{i,k}=1[\exists r:\ r\text{ alive},\ R_r>0,\ p_{base,r}>0,\ d_{ir,k}\le R_r]
$$

$$
E=\sum_k\sum_i a_{i,k}n_i z_{i,k},\qquad E_{seconds}=E\Delta t.
$$

Each crew is counted once per step, even when several enemies are in range. **This metric does not require LOS or detection**, unlike firing eligibility. Exposure is therefore not an injury probability or a casualty count.

$$
N_{lost}=\sum_i(1-a_i)n_i.
$$

This abstraction loses the entire crew when a vehicle is destroyed. Partial injuries and evacuation are not modeled. Dividing losses by each arm's own initial crew measures its internal loss fraction. Dividing by a common reference crew measures losses relative to that reference; the denominator must be stated explicitly.

## 5. Scenario A — Movement and delivery without engagement

**Purpose:** isolate #9 and #14 while retaining route and following rules. **Proposed diagnostic, not a newly executed run.**

- Same convoy: 18 vehicles, 60 tonnes, 15 people.
- No Red; pace=10 m/s, time_gap=4 s, spacing=40 m.
- C0, clear route, no forced leader loss.

**Worked example:** a reference vehicle is at s=1000 m, moving at 10 m/s:

$$
g=\max(40,10\times4)=40,\quad s^*=960\text{ m}.
$$

If the follower is at s=950 m, its target is 10 metres ahead along the route. Its speed remains constrained by motion limits and distance to the target.

If all trucks deliver:

$$
L=12\times5=60,\quad D=60,\quad X=0,\quad I=0,\quad f_D=1.
$$

No eligible enemy exists, so z=0 and E=0. Full delivery here is a conditional example; no particular arrival time is assumed without running the scenario.

**Checks:** cargo conservation, arrival of all followers, no circling around stations, and no treating route length divided by pace as a guaranteed mission time.

## 6. Scenario B — Enemy contact and HALT + Herringbone

**Purpose:** connect #12, #16 and #18 to movement. **Worked behavior example.**

The configured trigger is `receive_fire`, the action is `halt`, and the scope is `all`. Incoming fire may trigger the response without a successful hit. The update observes firing effects according to the simulation's step order.

If the latest trigger occurs at t_last, contact remains active according to clear_s=15:

$$
t-t_{last}<15\text{ s}.
$$

Each new trigger resets the timer. This does not mean stopping for only 15 seconds after the first shot while firing continues.

At episode entry, a parking station is fixed for each selected vehicle:

$$
P_i=r(s_i+20)+\sigma_i20\,n(s_i+20),\quad\sigma_i\in\{-1,+1\}.
$$

Here n is the local route normal, and signs alternate among selected living vehicles. The desired parking heading is the local road heading ±45°. Stations do not continuously move with the vehicle. A station inside a building, or with an obstructed approach, is rejected in favor of the vehicle's episode-entry position.

**Example on a road pointing along +x:** a vehicle on the centerline at (1000,1500) has a station at (1020,1520) on one side, or (1020,1480) on the other. Movement is gradual, not teleportation.

After contact clears, the vehicle rejoins the route perpendicularly, then resumes route following and formation. Herringbone has no automatic protection bonus.

**Checks:** trigger time, episode start, time to parking station, continued firing when targets remain eligible, release time, and return to the road.

## 7. Scenario C — Leader loss, leadership recovery and console recovery

**Purpose:** distinguish #17 from #19. **Current rules with a saved timing example.**

```text
leader_loss_policy = promote
succession = manned_only
handoff_steps = 5
console transfer delay = 20 steps after leadership recovery
```

A unit losing its leader enters leader-loss handling. A successor must satisfy eligibility rules. This convoy includes a crewed escort that can become a successor. An eligible successor is a condition, not a guarantee after every loss.

Separate three timestamps:

$$
t_L=\text{leadership recovery time},\quad t_C=\text{console transfer time},\quad t_S=\text{first new accepted service}.
$$

The experimental rule targets transfer at t_L+20 steps if the successor remains alive and crewed. The first service time t_S need not equal t_C because request and service timing also matter.

**From replay 47, seed 0:**

| Event | Time |
|---|---:|
| Leadership restored | 386 s |
| Console transferred | 406 s |
| First new service accepted after loss | 421 s |

$$
406-386=20\text{ s},\qquad421-406=15\text{ s}.
$$

These are recorded events, not an equation guaranteeing a 15-second delay to first service in every run. Queues, reservations and pending replies remain under the study's transfer rule; a previously scheduled reply can arrive after host loss.

**Vehicle behavior:** following a new leader can resume before console service has recovered. Leadership and operator service are separate state variables.

## 8. Scenario D — The same convoy under C0, C2 and C5

**Purpose:** explain the communications pathway through #19 while keeping `follow_mode=behavior`. Local following is not link following.

For each console c:

$$
A_c=\min(1,span\_capacity/N_c),\quad q_c=q_{auto}+(q_{operator}-q_{auto})A_c.
$$

With N_c=4, span_capacity=4, q_auto=0.7 and q_operator=0.95:

$$
A_c=1,\quad q_c=0.95.
$$

This calculates served quality, not every vehicle's q in every state. Waiting, loss and patience determine transitions to fallback states. Exempt crewed vehicles retain q=1 under the current rule. Attention does not itself change service duration; nominal service time here is 1/service_rate=2 s when service_rate=0.5.

| Level | One-way latency | Drop/message | Nominal round trip |
|---|---:|---:|---:|
| C0 | 0 steps | 0% | 0 s |
| C2 | 2 steps | 10% | 4 s |
| C5 | 16 steps | 55% | 32 s |

For the default independent-loss channel, the probability that both request and reply survive transport is:

$$
P_{transport}=(1-p_{drop})^2.
$$

C2: 0.9²=0.81. C5: 0.45²=0.2025. These are not guaranteed service fractions: replies must also meet patience limits, and service, queueing and host availability matter.

At C5, the nominal 32-second round trip exceeds patience=20 s even before service is added. Zero service in the current comparison is understandable under these settings, not a universal statement about every C5 configuration.

**Saved results: 10 seeds, direct route, all other factors held fixed:**

| Arm | Mean accepted-service fraction |
|---|---:|
| Baseline C0 | 0.767 |
| C2 | 0.547 |
| C5 | 0.000 |

The metric counts accepted/scheduled service, not confirmed delivery of every reply. Control quality q also affects speed and engagement, so delivery effects cannot be attributed to waiting alone.

## 9. Scenario E — The user sketch, three routes, seed 0

**Actual saved results** from `sketch_map/results.json`. These are not averages or causal comparisons isolating route length alone. Routes also change visibility, exposure and engagement timing.

| Route / replay | Delivered t | Lost t | In transit t | Crew lost | Exposure crew-steps | Time s | Success |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct / 45 | 0 | 25 | 35 | 15 | 7726 | 1800 | 0 |
| Upper loop / 46 | 60 | 0 | 0 | 5 | 1796 | 1567 | 1 |
| Lower loop / 47 | 50 | 0 | 10 | 2 | 1982 | 1800 | 0 |

Cargo conservation:

$$
Direct:\ 60=0+25+35
$$
$$
Upper:\ 60=60+0+0
$$
$$
Lower:\ 60=50+0+10.
$$

**Why did the lower loop fail?** The requirement is 100% delivery. At the 1800-second horizon, D/L=50/60=83.33%. The last two trucks, V17 and V18, were alive but had not delivered. The goal is at (5750,1500), with a 150-metre radius:

$$
d_{17}=5750-5468.64=281.36\text{ m}>150
$$
$$
d_{18}=5750-5249.25=500.75\text{ m}>150.
$$

Destroying the cargo-free control vehicle lost two people but no cargo tonnage. The delayed trucks carried 10 t in transit, not lost cargo. A low crew-loss count does not by itself satisfy the delivery-success criterion.

This is one seed. It does not establish the upper route as generally best, and failure does not mean the convoy was destroyed.

## 10. Scenario F — Varying one factor across seeds — #15

Everything stays fixed on the direct route except one factor relative to baseline:

| Arm | Pace m/s | Time gap s | Spacing m | Comms |
|---|---:|---:|---:|---|
| baseline | 10 | 4 | 40 | C0 |
| speed_8 | 8 | 4 | 40 | C0 |
| speed_12 | 12 | 4 | 40 | C0 |
| gap_6 | 10 | 6 | 40 | C0 |
| gap_8 | 10 | 8 | 40 | C0 |
| spacing_20 | 10 | 4 | 20 | C0 |
| spacing_60 | 10 | 4 | 60 | C0 |
| comms_C2 | 10 | 4 | 40 | C2 |
| comms_C5 | 10 | 4 | 40 | C5 |

Each arm uses seeds 0,…,9, for 90 runs in total. This is a one-factor-at-a-time (OFAT) design; it does not estimate interactions such as simultaneously changing speed and communications.

$$
\bar Y=\frac1n\sum_sY_s,\quad SD=\sqrt{\frac{\sum_s(Y_s-\bar Y)^2}{n-1}},\quad SE=SD/\sqrt n.
$$

For a paired comparison with baseline:

$$
\delta_s=Y_{arm,s}-Y_{baseline,s},\quad CI_{95\%}=\bar\delta\pm t_{0.975,9}SE(\delta).
$$

Here t≈2.262. The intervals are exploratory and unadjusted for multiple comparisons. An interval containing zero does not establish equivalence.

**Saved cargo-delivery results:**

| Arm | Mean delivered t | SE t | Mean difference t | Paired 95% interval t |
|---|---:|---:|---:|---|
| baseline | 26.5 | 8.53 | 0 | reference |
| speed_8 | 21.0 | 8.75 | −5.5 | [−31.59, 20.59] |
| speed_12 | 28.5 | 9.60 | 2.0 | [−30.62, 34.62] |
| gap_6 | 37.5 | 8.64 | 11.0 | [−18.39, 40.39] |
| gap_8 | 35.5 | 9.67 | 9.0 | [−14.59, 32.59] |
| spacing_20 | 42.0 | 9.17 | 15.5 | [−14.64, 45.64] |
| spacing_60 | 19.5 | 7.47 | −7.0 | [−21.03, 7.03] |
| comms_C2 | 37.0 | 9.17 | 10.5 | [−23.24, 44.24] |
| comms_C5 | 36.0 | 9.80 | 9.5 | [−27.95, 46.95] |

All cargo-difference intervals include zero. These results do not establish a best setting. A higher delivery mean under worse communications does not establish a benefit from jamming: motion, timing and engagement can change through several pathways, and the estimate is inconclusive.

The dashboard's capped completion time equals mission_time on success, otherwise the 1800-second horizon. This is a penalty metric, not the mean arrival time of successful runs. Replays 48–56 all use seed 0; they are not visual averages or selected favorable seeds.

## 11. Short practice exercises

1. A living truck carrying 5 t has not arrived: it contributes 5 to I, not X.
2. A truck delivers 5 t and is then destroyed: the 5 remains in D; it is not counted again as lost.
3. An escort with three people spends 20 measured steps within enemy range: E=3×20=60 crew-steps, provided it remains alive at those measurements.
4. A reference moves at 12 m/s, time_gap=4 s and spacing=40 m: g=max(40,48)=48 m. Do not always assume a 40-metre gap.
5. A building blocks LOS: it can prevent firing while E continues increasing under the current exposure definition.
6. If 50/60 t arrives, success=0 under a 100% requirement and success=1 under an 80% requirement only if the scenario uses that threshold. Changing the threshold changes the question; it should not be changed after results to improve appearances.
7. A new leader exists but the console has not transferred: leadership recovery has occurred; service recovery is not complete.

## 12. Limits of the current environment

- No automatic route adaptation during the mission or wreck bypass is modeled in this environment.
- Lane blocking, the ambush fire-control template and Red halt cost are not connected to this integrated study.
- Detailed jammer frequency/power physics and vehicle-to-vehicle messaging are absent; those extensions are deferred.
- Motion, obstruction, damage and crew models are low-fidelity abstractions, not calibrated operational predictions.
- Herringbone does not guarantee protection or collision avoidance; some rules support an understandable geometric demonstration.
- Console transfer is a study rule. Issue #19 remains incomplete, including its missing comparators and unresolved assumptions.
- Scenario A and B examples are not experiments executed here. The simulation was not rerun to create this document; reported results were read from local saved files.

## 13. Code and result sources

Repository root: `/Users/markfahim/Work/GRA GM/sandtable/`.

| Topic | Source within the repository |
|---|---|
| Step order | src/sandtable/sim.py |
| Following targets and convergence | src/sandtable/planning.py |
| Motion | src/sandtable/motion.py |
| Behavior and leadership | src/sandtable/behavior.py |
| Detection | src/sandtable/sensing.py |
| Communications | src/sandtable/comms_ew.py |
| Consoles and attention | src/sandtable/c2.py; src/sandtable/c2_units.py |
| Cargo and crew | src/sandtable/metrics.py |
| Herringbone study adapter | studies/convoy-study/leader_12_17/herringbone.py |
| Enemy priority used by the study | studies/convoy-study/red_priority_18/branch_sources/engagement.py; target_priority.py |
| Natural console transfer | studies/convoy-study/red_priority_18/run.py |
| Route results, seed 0 | studies/convoy-study/sketch_map/results.json; replays.json |
| Settings comparison | studies/convoy-study/sweep_15/results.json; run.py; design.json |

Result and replay files are generated locally and are not tracked in Git. Open the [comparison dashboard](http://127.0.0.1:8766/convoy_sweep.html) or the [mission viewer](http://127.0.0.1:8766/convoy_study.html) while the local server is running.
