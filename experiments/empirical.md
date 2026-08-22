# Empirical notebook: SandTable (mission-level GL)

Lab notebook for the FP6111 lightweight ProjectGL reimplementation. Every run
(including failures) is recorded with exact parameters, commands, and outputs so
reported numbers trace back to a reproducible step. Dates are absolute.

> **2026-07-17 - Package renamed `mgl` -> `sandtable` (tool named "SandTable").**
> Entries dated on or before 2026-07-16 predate the rename: their module paths
> (`mgl.*`, `src/mgl/`), conda env `mgl`, and run stores `~/mgl-runs/` (Hopper:
> `/scratch/vsokolov/mgl-runs/`) reflect the pre-rename identity and are left
> verbatim so those numbers stay traceable to the data actually on disk. Code now
> imports `sandtable`; study YAMLs and analysis scripts now default to
> `~/sandtable-runs/`, and production studies for the paper will be re-run there.

Environment, unless noted otherwise:
- Host: local (Darwin, Apple Silicon), conda env `mgl`, Python 3.12.
- numpy 2.4.6, scipy, numba, networkx, matplotlib; polarisopt 0.17.2 with the
  `[bo]` extra (torch/gpytorch/botorch) installed editable from
  `/Users/vsokolov/Dropbox/prj/polarisopt`.
- `mgl` installed editable (`pip install -e .`), entry points registered:
  `polarisopt.simulators -> mission = mgl.plugin`,
  `polarisopt.metrics -> mission_kpi = mgl.opt_metrics`.
- Reproducibility contract: `run_mission(scenario, seed)` is a pure function
  (no global RNG, no wall-clock, no hidden state). Per-run RNG is
  `mgl.seeding.make_rng(seed, scn.id)`. polarisopt hands each sample a disjoint
  seed block `base_seed + n_repeats * sample.id`; the runner uses seeds
  `seed, seed+1, ..., seed+n_repeats-1`.

--------------------------------------------------------------------------------

## 2026-07-16  polarisopt packaging fix (dependency of this project)

polarisopt failed to `pip install` (hatchling `ValueError`: duplicate
`examples/__init__.py`) due to a redundant
`[tool.hatch.build.targets.wheel.force-include]` mapping
`src/polarisopt/examples` onto `polarisopt/examples`. Removed the force-include.
Verified the wheel builds and retains all four example study YAMLs. Pushed as
branch `fix/wheel-force-include-duplicate`, PR #2. Interim editable install
worked before the fix; regular install works after.

## 2026-07-16  UC-3 improve-loop (the "sensitive results" iteration)

Goal (user step 6): iterate the model until the mission KPI responds with real,
expected structure to the design parameters, on the UC-3 route-vs-defilade
scenario. Ad-hoc local sweeps over `route_bias` (0 = fast exposed corridor,
1 = slow covered route) drove the following fixes:

1. Leader-death stall: followers chased a dead leader's frozen position and the
   sim stalled. Fix: every blue vehicle navigates independently toward the
   objective (no dead-leader dependency) in `planning.py`.
2. Over-lethal engagement: a per-second Pk of ~0.30 annihilated both sides. Fix:
   Pk placed on a hazard-per-second scale (`at_team` pk_base 0.008, `ugv`
   0.002) and detection made per-step (non-sticky) so concealment protects
   continuously along a covered route.
3. Weak attrition tradeoff (covered route not actually safer). Three root causes
   fixed: (a) linear convergence dragged the covered route back through the
   exposed zone -> late convergence (`converge_dist`); (b) blue approached the
   far goal at a shallow angle and never reached the covered lane before the
   threat -> pure-pursuit carrot `tx = min(x + lookahead, gx)` so blue climb
   onto the lane fast; (c) the red footprint was too wide -> tightened `at_team`
   to a column, weapon_range 1000 m, pk_base 0.008.

Final ad-hoc verification sweep (in-process loop, n_reps=200):

```
route_bias  success       blue_loss(of 8)  red_loss  t_obj|success
0.00        0.18 +/-0.03  6.28 +/-0.14     1.79      468 s
0.25        0.27 +/-0.03  5.88 +/-0.15     2.05      506 s
0.50        0.45 +/-0.04  4.95 +/-0.15     2.73      628 s
0.75        0.90 +/-0.02  2.31 +/-0.12     4.19      859 s
1.00        1.00 +/-0.00  0.72 +/-0.06     4.71     1082 s
```

Monotone, doctrinally meaningful speed-vs-attrition tradeoff. "Sensitive
results" criterion MET for UC-3.

## 2026-07-16  polarisopt integration (studies run through the orchestrator)

Built the master/slave adapter mirroring polarisopt's `taxidemo/`:
- `src/mgl/runner.py`: slave CLI `python -m mgl.runner inputs.json outputs.json`
  (loads scenario, runs n_repeats seeded replications, writes averaged KPIs).
- `src/mgl/plugin.py`: `MissionSimulator` (`prepare` writes inputs.json +
  returns JobSpec; `collect_output` reads outputs.json). Registered type
  `mission`.
- `src/mgl/opt_metrics.py`: `MissionScoreMetric` (registered `mission_score`),
  scalar cost `J = w_fail*(1-success_rate) + w_time*(time/time_scale)
  + w_loss*blue_loss_frac`, weights (1.0, 0.3, 0.5), time_scale 1800.
- Studies: `studies/uc3_sweep.yaml` (LHS), `uc3_morris.yaml` (Morris),
  `uc3_bo.yaml` (GP + q-EI BO). All `runner: local`; all validate.

Slave smoke test (route_bias 0.75, 10 reps, seed 100): success 0.90,
blue_losses 2.6, t_obj|success 861 s. Consistent with the ad-hoc sweep.

### Run 1 -- LHS sweep  (`studies/uc3_sweep.yaml`)

```
polarisopt run studies/uc3_sweep.yaml     # from repo root
```
48 designs x 20 reps. 48/48 samples, 0 failed, 29 s wall (573% CPU).
Store: `~/mgl-runs/uc3-sweep/polarisopt.db`; workspaces
`~/mgl-runs/uc3-sweep/experiments/sim-0000NN/`.

Response surface (analysis: `scratchpad/analyze_sweep.py`):
- corr(route_bias, success)      = +0.908
- corr(route_bias, blue_losses)  = -0.930
- corr(route_bias, red_losses)   = +0.904
- corr(route_bias, t_obj|success)= +0.631

route_bias terciles:
```
low  [0.00-0.33]  n=16  success 0.17  blue_losses 6.72  t_obj|S 780 s
mid  (0.33-0.66]  n=16  success 0.33  blue_losses 5.48  t_obj|S 895 s
high (0.66-1.00]  n=16  success 0.90  blue_losses 1.92  t_obj|S 1341 s
```

### Run 2 -- Morris screening  (`studies/uc3_morris.yaml`)

```
polarisopt run studies/uc3_morris.yaml
```
10 trajectories x (3 params + 1) = 40 evals x 20 reps. 40/40, 0 failed, 24 s.
Analysis: `scratchpad/analyze_morris.py` (SALib `morris.analyze`, num_levels 4,
samples read in sim-id == SALib trajectory order), objective `mission_score`:
```
param             mu*     mu*_conf  sigma
route_bias        1.2618  0.3737    0.6272   <- dominant
tempo             0.4213  0.2965    0.5790
formation_spread  0.1541  0.1123    0.2062   <- negligible
```
route_bias is ~3x tempo and ~8x formation_spread. Confirms allocating the BO
budget primarily to route_bias.

### Run 3 -- Bayesian optimization  (`studies/uc3_bo.yaml`)

```
polarisopt run  studies/uc3_bo.yaml
polarisopt best studies/uc3_bo.yaml
```
Minimize `mission_score`. LHS warm-up 12 + sequential GP + q-EI (mc_samples 256),
batch_size 4. 32/32 samples, 0 failed. Plateau stop fired at iteration 5
(n=32, best=0.209675).
Best sample (id 15): route_bias 0.980, formation_spread 20.0, tempo 1.0,
mission_score 0.2097. BO drove to the covered route at max tempo, the
doctrinally correct optimum. Store: `~/mgl-runs/uc3-bo/polarisopt.db`.

### Run 4 -- Lanchester analytic cross-check  (`experiments/analysis/lanchester_check.py`)

```
conda run -n mgl python experiments/analysis/lanchester_check.py
```
Exercises the real `mgl.engagement.step` kernel in a controlled aimed-fire duel
(two facing ranks of 30, every pair in weapon range, zero cover, all mutually
detected) and compares the MC-mean trajectories (600 reps) to the continuous
Lanchester square-law ODE `dB/dt=-a R, dR/dt=-b B` (a=pk_red=0.03, b=pk_blue=0.02).
Result: RMSE(sim vs ODE) B = 0.87, R = 0.12 over the pre-depletion window;
Lanchester invariant `b*B^2 - a*R^2` drifts only 7.2%. The stronger red side
wins decisively (red holds ~17 of 30 as blue is eliminated), matching the square
law's sqrt-advantage prediction. The bounded late-tail deviation (sim retains a
few more blue than the ODE once ranks thin) is the classic ABM fire-concentration
effect (survivors share a nearest target -> overkill), expected and quantified,
not hidden. Verdict PASS: the low-fidelity attrition kernel is analytically
defensible (method after Gaertner 2013).

## 2026-07-16  Increment 2: span-of-control x comms centerpiece

New modules `comms_ew.py` (C0-C5 latency/drop ladder) and `c2.py` (one operator,
single-server queue + comms round trip, supervising N agents). Each blue agent hits
decision events; the resolved control_quality in [0,1] modulates motion tempo and
engagement (guarded no-ops at 1.0, so the 55 ground-core tests stay green). Two
control modalities: `direct` (human-in-the-loop: high quality q_operator but pays
queue + comms round trip, falls back to a poor q_fallback on timeout/drop) and
`supervisory` (steady autonomous q_auto, comms-independent). Scenario
`scenarios/sc_span_control.json`; blue count is the swept span `n_blue` (via a new
`ForceSpec.count_param`).

Improve-loop (the span axis was the hard part). Iterations:
1. First cut (red=6, pk 0.008, service_rate 0.5): crossover present but success
   floored (too lethal) and N=4 gave no signal.
2. Weakened red (count 4, pk 0.005) + route_bias 0.65: mission winnable, clean
   comms crossover, but the span effect was masked because a fixed threat makes a
   larger force trivially meet the survive-fraction (force-size confound), and a
   saturated direct agent fell back to the same q_auto as supervisory.
3. Added `q_fallback` (0.50 < q_auto) so a direct-mode agent forced autonomous is
   worse than a supervisory one, and slowed the operator (service_rate 0.15) so it
   saturates at large N: the span effect appeared (N=8 supervisory dominates).
4. Added operator **attention dilution** (`span_capacity` 4: one operator fully
   attends up to 4 agents, per-decision quality decays toward q_auto beyond that),
   separating the span effect (quality) from the comms effect (latency). Final.

Fixed a plugin bug: `type: int` sweep params arrive as numpy int64 and broke
`json.dumps`; added a `_to_native` default in `mgl/plugin.py`.

Studies `studies/sc_sweep_{direct,supervisory}.yaml`: full-factorial manual grid
comms_level {0..5} x n_blue {2,4,6,8} = 24 designs x 150 reps each, control_mode
pinned per study via simulator options. 24/24 each, 0 failed, ~90 s each.
Analysis `experiments/analysis/analyze_span_control.py` (surface ->
`experiments/results/sc_surface.json`).

Result: (direct - supervisory) success advantage falls monotonically on BOTH axes.
```
advantage vs comms (mean over N):  C0:-0.11  C1:-0.09  C2:-0.13  C3:-0.19  C4:-0.32  C5:-0.34
advantage vs span  (mean over C):  N2:-0.12  N4:-0.18  N6:-0.20  N8:-0.28
```
Direct control is preferred only in the small-team, good-comms corner (best cell
C0/N2: direct 0.46 vs supervisory 0.40, +0.06); the advantage goes strongly
negative as comms degrade (jamming favors autonomy) or as span grows (one operator
saturates), and both compound. This is the proposal's headline HMT finding and the
UC-3-style "sensitive results" gate for scenario 2 is MET. Residual per-cell noise
remains (the direct mode is bimodal under queue saturation), so the marginal trends
and the advantage surface, not individual cell winners, are the reported evidence.

## 2026-07-16  Increment-2 unit tests + full suite

25 new tests (`tests/test_comms_ew.py` 9, `tests/test_c2.py` 11,
`tests/test_span_scenario.py` 5). Full suite now 80 passing (55 ground-core, all
still green, + 25 Increment-2), ~16 s. No bugs found in c2/comms_ew. The C2
sensitivity gate (C5 jamming, n_blue=6, 30 reps, seed 0): supervisory success 0.733
vs direct 0.400, margin 0.333 (>= 0.15 required). Re-run:
`conda run -n mgl python -m pytest tests/ -q`.

## 2026-07-16  Hopper HPC: parallel studies via the polarisopt SLURM runner

SSH alias `hopper` (hopper.orc.gmu.edu, user vsokolov). Setup:
- rsync `src/scenarios/studies/pyproject` to `/scratch/vsokolov/projectgl-lite`
  and the fixed polarisopt clone to `/scratch/vsokolov/polarisopt` (both editable).
- Reused the existing `pol` conda env (Python 3.11, already had torch 2.11+cpu);
  `pip install -e '/scratch/vsokolov/polarisopt[bo]'` then
  `pip install -e /scratch/vsokolov/projectgl-lite`. Verified mgl + polarisopt +
  torch import; the `mission` simulator and `mission_score` metric register.
- CPU partition `normal` (92 nodes, thousands of idle cores); conda activated in
  the sbatch `setup_commands`. Study `studies/uc3_sweep_hopper.yaml` (identical
  science to `uc3_sweep.yaml`, only runner + workspace differ).

Run: `polarisopt run studies/uc3_sweep_hopper.yaml` (master backgrounded with
nohup on the login node; it submits one sbatch per sample, polls squeue/sacct,
checkpoints to SQLite). 48 designs x 40 reps: 48 jobs submitted to `normal`,
48/48 completed, 0 failed. Store `/scratch/vsokolov/mgl-runs/uc3-sweep-hopper`.

Cross-runner reproducibility: the Hopper response surface matches the laptop run,
corr(route_bias, success) +0.923 (local +0.908), corr(route_bias, blue_losses)
-0.925 (local -0.930), terciles low 0.16/6.68 vs high 0.88/1.87. The same YAML
runs on both the `local` and `slurm` runners with only the runner block changed,
confirming the file+subprocess contract. Hopper is ready for the large final
production studies.

Status: scenarios 1 (UC-3, route vs defilade) and 2 (span-of-control x comms) both
complete end-to-end through polarisopt with sensitive results and a full test suite
(80 passing); UC-3 additionally has the Lanchester analytic cross-check; the Hopper
SLURM path is validated. Next: Increment 3 (air/UAS + shared-SA fusion, UC-5 sensor
swarm under EW), then the final production studies on Hopper, then the report.

## 2026-07-17/18  Production studies on Hopper (300 reps each), sandtable

All studies re-run under the renamed package at `/scratch/vsokolov/sandtable`
(polarisopt `slurm` runner, partition `normal`, conda env `pol`, base_seed 42,
n_repeats 300). Results collected with `experiments/analysis/collect_results.py`
into `report/data/*.csv` (one row per design). Workspaces under
`/scratch/vsokolov/sandtable-runs/<study>`:

- `centerpiece_direct_hopper.yaml`  -> centerpiece-direct  (36 designs = comms{0-5}
  x span{2,3,4,5,6,8}, control_mode=direct). 36/36 completed.
- `centerpiece_supervisory_hopper.yaml` -> centerpiece-supervisory (same grid,
  control_mode=supervisory). Matched seed blocks give common random numbers for the
  paired direct-vs-supervisory delta. 36/36 completed.
- `uc3_frontier_hopper.yaml` -> uc3-frontier (21 designs, route_bias 0.0..1.0 step
  0.05). 21/21 completed.

Headline reads (300 reps): centerpiece supervisory is comms-invariant (span 1:2
71-78% across C0-C5); direct degrades with comms (span 1:2 81%->56%) and with span
(1:8 floored at 4% at C0). Moving optimum: crossover C* falls from ~C1 at span 1:2
to C0 at span 1:8; supervisory advantage up to +34 pp. UC-3: fast corridor 22%
success / 6.1 losses / 468 s vs defilade 99% / 0.7 / 1082 s (2.3x slower). Clean,
monotone, sensitive surfaces on all three axes.

## 2026-07-19  UC-5 sensor-swarm iteration + rerun; Lanchester; paper

UC-5 needed model + scenario work to become insightful (the earlier scattered-threat
laydown gave a flat swarm axis: coverage saturated at 1 UAS). Two changes:
- `planning.overwatch_stations` gained an `aspect` knob (read from param
  `overwatch_aspect`, default 1.0 = old square lattice): with aspect>1 the swarm
  spreads ALONG the assault/threat axis (x) first, matching a defense in depth. UC-5
  sets `overwatch_aspect=3.0`. `scenario.ForceSpec` gained an optional `spacing`
  field so the red AT belt is laid out in depth (spawn [4700,1500], column, spacing
  550 -> threats span x=1950..4700). UGV kept near-blind (sensor 350 m) but long-
  ranged (weapon 1400) so recon cueing is load-bearing. Non-air scenarios unchanged
  (aspect defaults to 1.0; spacing defaults to formation_spread).
- Local probes (`scratchpad/probe_uc5b.py`, 40 reps): the elongation removed the
  n_uas=2 coverage dip and produced a clean monotone rise with a threshold at ~5 UAS
  (blanket the belt), plus a strong EW collapse.

Rerun on Hopper: `studies/uc5_swarm_jam_hopper.yaml` (now n_uas{0..8} x comms{0-5} =
54 designs x 300 reps), workspace `/scratch/vsokolov/sandtable-runs/uc5-swarm-jam`.
All 54 outputs.json valid (the polarisopt master logged 10 "failed" from a
collection race where slow SLURM jobs wrote outputs.json after the master polled;
verified on disk that all 54 are present and parse, then collected directly with
`collect_results.py`). Reads: no recon 2% success (coverage 0.01); 8-UAS swarm 80%
(coverage 0.79) in the clear, collapsing to 52% (coverage 0.39) under severe EW; a
3-UAS swarm 56%->28%. Sensor size and link resilience are complements.

Lanchester cross-check (`tools/lanchester_check.py`, 600 reps/duel, pk=0.01): the
aimed-fire kernel matches the square law sqrt(B0^2-R0^2) to within 9.1% (most 3-6%),
biased slightly low from simultaneous discrete-time fire + nearest-target overkill
(both conservative). Table in `report/gen/tab_lanchester.tex`.

Paper: `report/main.tex` (12 pp) written under the academic-paper skill. Numbers and
all four result tables generated by `tools/make_numbers.py` from `report/data/*.csv`
(audit trail `report/results/numbers.txt`); figures by `tools/make_figures.py`.
Citations (14) verified against CrossRef/arXiv on 2026-07-19, each with a `% verified:`
line in `report/ref.bib`; ProjectGL cited via SAE 2025-01-0469 (Stanko et al.),
superseding the unverifiable trade-magazine URL. Pre-flight audit (`tools/audit.py`)
PASSES all five checks: citation provenance 14/14, AI-writing signs 2 (<10),
zero em-dashes, contribution pointers resolve, compile clean. Single-core throughput
~0.1 s/mission (7-11 runs/s); total study volume 147 designs x 300 reps = 44,100
replications.

Status: all three scenarios complete with sensitive, insightful 300-rep results;
Lanchester validated; paper drafted and passing pre-flight. Next: optional Bayesian-
optimization studies (search rather than grid) and high-fidelity confirmation in
ProjectGL of the flagged designs.

## 2026-07-19  Self-audit (academic-paper Workflow 4), all ten phases

Ran the full self-audit: pre-flight (5 checks) + Phases 2-8 as parallel read-only
subagents (math/notation, claims, citations, consistency, limitations, structure/style,
figures/tables) + Phase 9 (code) + Phase 10 (compile). Fixes applied (all numbers still
trace to code; figures/tables regenerated from make_numbers.py + make_figures.py):
- Citations: corrected `raz2024mission` title (CrossRef: "...with System of Systems
  Interdependence", not the invented subtitle) and given name (Marco, not Mara); added
  "and others" to Stanko et al. (21 authors); added the primary `lanchester1916aircraft`
  (OpenAlex W1550662062) for the square law, keeping Kress 2020 as the modern treatment.
- Claims: removed the unverifiable "2024 M&S award" clause and the "built on Unreal
  Engine" specific (not supported by the cited SAE paper); softened "severs/breaks/
  collapse toward baseline" to match the data (UC-5 severe stays well above the no-recon
  baseline: 52% vs 2%).
- Accuracy: fixed the +34 pp attribution (that maximum is at span 1:6 under heavy EW;
  at 1:8 in the clear it is +27, macro cpDeltaHiSpanClear); reconciled the supervisory
  spread (71 to 78 = 7 pp, not 6.3) by rounding endpoints in make_numbers.py.
- Limitations: added static (non-maneuvering) red, invulnerable UAS (no air defense, so
  swarm size has no survivability cost = UC-5 upside is an upper bound), and hand-set pk
  and C0-C5 ladder values; noted single-operator, no-RL, three-scenario scope.
- Style: converted the four Related-Work `\paragraph{}` headers and the Contributions
  header to prose leads; added orienting sentences after Sections 2, 3, 5 (no bare
  heading stacks); split one 62-word sentence; pinned q_auto/q_operator/kappa values and
  fixed the n/kappa notation.
- Figures/tables: recolored UC-3 to a colorblind-safe blue/amber pair with distinct
  markers; added C0-C5 tick labels to the centerpiece curves; fixed the UC-3 caption
  ("bands" -> markers/lines), UC-5 table caption (selected levels), and UC-3 table loss
  units (of 8 / of 6). Added a Section-4 note on the coverage/success truncation coupling.
Result: pre-flight PASSES all five checks (15/15 citations verified, 2 AI-vocab hits,
zero em-dashes, contributions resolve, compile clean); 12 pages.

### 2026-07-19 - Abstract rewrite, AI-writing pass, figure cleanup (commit 7d7725b)
- Abstract rewritten to describe the simulator core (SoA state, fixed-step pipeline, comms/EW
  ladder, operator-as-shared-server command model, pure run_mission contract) before the results.
- AI-writing pass beyond the vocab grep: removed both "robust" hits (comms-robust -> nearly
  comms-invariant; "robust claim" -> "what the study establishes") and one redundant
  negative-parallelism. audit.py check 2 now reports 0 vocabulary hits.
- centerpiece_phase.pdf: draw only the longest delta=0 contour (suppress the single-cell
  Monte-Carlo-noise island); opaque label boxes; "direct control wins" moved clear of the crossover.

### 2026-07-19 - Paper extended with simulator diagrams and scenario detail
- New tools/make_diagrams.py generates, from the source and scenario JSONs (so they cannot drift):
  architecture.pdf (layered modules + the fixed-step run_mission pipeline + pure-function wrapper),
  command_model.pdf (direct vs supervisory operator model, the moving-optimum mechanism),
  scenarios.pdf (data-driven 3-panel schematic: UC-3 routes/cover, centerpiece operator-over-link,
  UC-5 near-blind UGVs + UAS overwatch vs defense-in-depth), plus tab_ladder.tex (C0-C5 ladder) and
  tab_platforms.tex (per-scenario platform params). All figures are matplotlib (uniform pipeline).
- main.tex: added the three figures + two tables; expanded Section 3 (movement/sensing/engagement
  now carry the actual v and p_k equations; command model gains the queue/service/patience/fallback
  detail and its figure; comms ladder gains its table) and Section 4 (scenario schematic + per-scenario
  laydown/exercise detail + platform table).
- Bug fixed: raw "at_team" underscore broke the compile (math-mode subscript in text); escaped in
  the table generator.
Result: pre-flight PASSES all five checks (0 AI-vocab hits, zero em-dashes, compile clean); 17 pages.

### 2026-07-19 - Richer single-run replay in the mission console
- engagement.step gains an optional `events` list that records (shooter, target) kill pairs; it is
  None on the hot path (sim.run_mission), so the optimizer's RNG stream and outcomes are unchanged
  (verified: same seed -> identical KPIs; 79 tests pass, 1 skipped).
- replay.record_trace attaches per-frame `kills` to each snapshot.
- tools/make_viz.py (full console) now draws: weapon-range rings on threats + sensor rings on ground
  units (toggle "rings", default on), sensor-to-shooter cue lines derived from the shared picture
  (a ground shooter engaging a detected enemy it cannot see itself, linked through the covering UAS),
  and kill tracers (shooter -> victim with an impact burst). Console defaults to the UC-5 swarm view.
- Verified geometry with a matplotlib preview of two UC-5 combat frames (cue chain + kill tracer both
  correct) and node --check on the emitted JS. The .html viewers remain generated + git-ignored.

### 2026-07-20 - Diagram cleanup + Extensions subsection
- Figures: fixed the last overflow/overlap in tools/make_diagrams.py. Architecture: widened the
  build-world, state, and KPI boxes so labels fit inside their borders; dropped a stray backslash so
  control_quality renders with a plain underscore (matplotlib figure text is not LaTeX). Command
  model: fanned the four agent-to-comms arrows to distinct endpoints. Verified overflow-free at
  200-400 DPI.
- main.tex: added a Discussion subsection "Extensions" (three paragraphs), grounded in the
  Limitations and the program objectives: (1) hardening the findings -- global sensitivity (Morris/
  Sobol) reporting the crossover as a band, plus human-subject calibration of the command model and
  Bayesian calibration of the lethality/link parameters against ProjectGL; (2) richer mechanisms --
  probabilistic terrain-masked sensing, reactive red + air defense, multi-operator command; (3)
  learning/analytics -- RL/imitation policies, a DL surrogate with UQ inside the BO loop, and the
  deception/trust use cases for trust calibration and pattern-mining. Only reuses already-verified
  citations (cummings2007capacity, chen2011supervisory, hocraffer2017meta, stanko2025projectgl,
  balandat2020botorch); no new references introduced.
- Result: pre-flight PASSES all five checks (15/15 citations verified, 0 AI-vocab hits, zero
  em-dashes, contribution refs resolve, compile clean); still 17 pages.

### 2026-07-21 - Response to Joe's kill-web / AFSIM review: t+dt diagram + belief-layer prototype

Prompted by Joe's email (attrition-vs-kill-web, rich entity state, belief-based fires, "do you have a
t+dt state machine?", study AFSIM basal behaviors).

- AFSIM research (sourced note in scratchpad/afsim_research.md): "basal behaviors" is not AFSIM's
  term; the construct is RIPR behaviors (precondition + execute) in a 5-node behavior tree, driven by
  WSF_SCRIPT / WSF_TASK / WSF_QUANTUM_TASKER processors and WSF_PERCEPTION_PROCESSOR. Confirmed:
  tracks = imperfect perception, fires/tasking run against tracks not truth, EW = false-target /
  track-corruption effects (first-order on belief). Munitions/fuel/command-chain are first-class;
  suppression/fatigue/posture are NOT in AFSIM (ground-ABM lineage). AFSIM is ITAR / Distribution F
  and ALL its output is export-controlled, so keep sandtable clean-room to preserve the
  unclassified/publishable posture.
- tools/make_diagrams.py: new fig_tick_cycle -> report/figures/tick_cycle.pdf. Shows the fixed-order
  t->t+dt pipeline (C2->planning->motion->sensing->engagement, dt=1s, no per-agent FSM) with
  per-stage read/write, and entity state today vs proposed AFSIM-aligned belief/track layer. Verified
  overlap/overflow-free at 200-210 DPI.
- src/sandtable/belief.py (new, opt-in) + sim.py wiring: per-side persistent tracks (believed x,y,
  age/staleness, confidence) refreshed from detections, going stale when detection lapses; fires
  resolve vs believed position * confidence, not truth; plus false/decoy tracks. Enabled only when
  params["belief"]["model"]=="tracks"; None otherwise, so the baseline path and every existing number
  are byte-identical (full suite: 85 passed / 1 skipped; the 79 baseline tests unchanged).
- tests/test_belief.py (6 tests): opt-in gating, determinism, track staleness/drop, and decoys +
  jamming as first-order effects.
- Demonstration (UC-3, mean blue_losses over 24 seeds): baseline 6.3; belief clear 6.4; +decoys 3.8
  (spoofing pulls fire off real targets); jammed C5 5.2 (stale tracks miss). EW/deception are now
  first-order, not Pk modifiers.

### 2026-07-21 - Full kill-web pass: suppression + munitions mechanics, UC-7 contested-belief scenario

Follow-up to the belief prototype, addressing Joe's kill-web review in full: each entity now carries
suppression and a finite basic load, and a new contested-belief scenario integrates all layers. Every
mechanic is opt-in and byte-identical when off (baseline is the degenerate limit).

- src/sandtable/mechanics.py (new): Mech config + suppression/munitions helpers. Suppression is a
  decaying [0,1] state raised on targets by incoming fire; it scales down a suppressed shooter's Pk
  (read from a pre-step snapshot so both sides use pre-step values, no shooter-order bias). Munitions
  = finite rounds per shooter (arm sets ammo_load on pk_base>0 entities), decremented on fire, gates
  engagement at zero. build_mech returns None unless params["mech"] sets suppression or munitions.
- Wired into engagement.step, belief.engage (shared semantics), and sim.py (build + arm + per-step
  decay). When mech is None the engagement draws the identical RNG stream -> byte-identical.
- Byte-identical PROOF: regenerated report/gen/numbers.tex and every existing report/data/*.csv;
  `git diff` shows only ADDED macros, zero changes to the 34 prior macros or the 6 existing study
  CSVs (centerpiece, uc3, uc5, lanchester, belief_demo). Full suite: 102 passed (92 baseline + 10
  new mechanics tests, tests/test_mechanics.py).
- scenarios/uc7_spoofed_advance.json (new, id=7): 8 UGV advance vs 8 static AT teams; params bake in
  the full contested config (comms C3, belief tracks + 6 decoys, suppression + munitions ammo 120).
- tools/make_killweb_numbers.py (new) -> three CSVs (N=48 seeded reps each):
  - suppression_sweep.csv (UC-3): supp_fire 0.0->1.0. blue losses 6.2->5.0, success 23%->44%.
    supp_fire=0 reproduces the baseline exactly (6.2). Base-of-fire effect: the 8 attackers out-gun
    the 6 defenders, so suppressing them lets the maneuver force cross cheaper.
  - munitions_sweep.csv (UC-3): defender ammo_load 2..1000. blue losses rise MONOTONICALLY
    0.0->6.2, converging exactly on the fixed-Pk baseline (6.2) as ammo->inf; success 100%->23%.
    Sanity: ammo=2 -> 6 teams x 2 shots x pk 0.008 ~= 0.10 blue losses (matches). The fixed-Pk model
    is the infinite-magazine limit.
  - uc7_layers.csv (UC-7): peel from truth baseline. blue losses / success%:
    truth 7.4/6; +belief 7.5/2; +jam 7.3/6; +decoys 4.3/56; +suppress 3.8/65; +full(munitions) 3.0/79.
    Decoys are the dominant single first-order layer (spoofing breaks the engagement); belief and
    jamming alone are near-neutral here with fresh tracks.
- Figures/tables: tools/make_figures.py fig_killweb_sweeps -> report/figures/killweb_sweeps.pdf
  (a: suppression, b: munitions with dashed fixed-Pk baseline). tools/make_numbers.py killweb() ->
  new macros (supp*, muni*, ucSeven*, killwebNRep) + report/gen/tab_killweb.tex. Diagram
  fig_tick_cycle updated: belief/suppression/munitions tagged [built], C2 graph/sustainment [future].
- Paper: new Results subsection 5.5 "Kill-web mechanics" (subsec:killweb) with the moved tick_cycle
  figure, suppression + munitions studies (Fig killweb_sweeps), and the UC-7 layered table; belief
  prototype promoted from Discussion into this Results subsection; 5th contribution added; Extensions
  and Conclusion updated (suppression/munitions/belief moved from future-work to done). Pre-flight
  PASSES 5/5; 20 pages.

### 2026-07-21 - Related-work expansion + personality-movement demonstration (emergent maneuver)

Addressing a review ask: research existing low-fidelity combat-simulation approaches (AFSIM and the
combat-distillation lineage), cite them as background, and where useful implement + demonstrate one.
Two parts.

(1) Reference expansion. Grew report/ref.bib from 15 to ~37 verified entries (all pass
tools/bibverify.py; every entry carries a `% verified:` provenance line). New background threads with
DOI/OpenAlex-verified cites: HMT/levels-of-automation (parasuraman2000types, olsen2004fanout,
lewis2013human, savla2012queue, kaber2004effects, parasuraman1997humans); combat-distillation ABM
(ilachinski2000isaac, ilachinski2004artificial, lauren2002mana, luke2005mason); data farming + DOE +
sim-opt (horne2004datafarming, cioppa2007nolh, kleijnen2015doe, amaran2016simulation, barton2006metamodel,
law2015simulation); Lanchester/attrition validation (deitchman1962guerrilla, bonder1967attrition,
washburn2009combat); DEVS + AFSIM engagement framework (zeigler2019theory, tryhorn2021afsim,
rainey2024afsim). Integrated into Related Work (HMT, agent-based combat sim, DOE paragraphs), the
validation subsection, the kill-web subsection (AFSIM fires-vs-tracks), and the state-and-time
subsection (DEVS discrete-event executive -> our fixed-step reduction). Removed taylor1983lanchester
(bibverify FAIL, no locatable source; redundant with other Lanchester cites). NOTE: clean-room wrt
AFSIM - no AFSIM code/data/output ingested (ITAR/Distribution F); best practices adopted from the
open literature only.

(2) Personality-movement mode, implemented + demonstrated (the "implement if useful" half).
- src/sandtable/personality.py (new): ISAAC/EINSTein/MANA weighted attraction-repulsion movement.
  aim() sets each blue-ground vehicle's target = w_goal*(unit to objective) + enemy repulsion (over
  DETECTED enemies within radius, inverse-distance falloff) + w_cover*(cover gradient, finite-diff of
  world.cover_at) + w_sep*(formation separation). No RNG. build_personality returns None unless
  params["movement"]=="personality"; None -> planning uses the scripted lane, byte-identical.
- Wired into planning.step (pers=None param + override block after the scripted lane) and sim.py
  (build pers, pass to planning.step). Byte-identical PROOF: full suite 102 -> 106 passed (4 new),
  and `git diff report/gen/numbers.tex` shows ONLY added pers* macros, zero changes to the 53 prior
  macros; all existing study CSVs unchanged.
- tests/test_personality.py (4 tests): opt-in gating; movement="scripted" == baseline (byte-identical);
  determinism; and emergent enemy-repulsion lowers mean blue_losses vs w_enemy=0.
- tools/make_personality_numbers.py (new) -> report/data/personality_sweep.csv (N=48 seeded reps).
  Time-to-objective conditioned on SUCCESS (matches the UC-3 frontier convention; not censored at
  duration by failed runs). blue_losses / success% / t_obj(s):
    scripted fast corridor (route_bias 0):  6.2 / 23  / 469   (fast, exposed)
    scripted covered route (route_bias 1):  0.9 / 100 / 1082  (safe, slow) -- best scripted
    personality w_e=0:                       6.2 / 23  / 469   (pure goal-seek -> recovers fast corridor)
    personality w_e=0.5:                     3.6 / 67  / 756
    personality w_e=1:                       0.0 / 100 / 781   (EMERGENT MANEUVER)
    personality w_e=2:                       0.0 / 100 / 838   (emergent over-caution, slower)
  Headline: the scripted planner traces a speed-survivability frontier (fast+deadly <-> slow+safe);
  emergent enemy-repulsion at w_e=1 finds a point OFF that frontier -- as survivable as the covered
  route (0 losses, 100%) but ~28% faster (781 vs 1082 s), because it skirts each threat locally
  instead of committing to a fixed lane. w_e=0 recovers the fast corridor exactly (reduction check);
  w_e=2 shows the propensity can be over-weighted into emergent over-caution. The route is chosen by
  the model, not scripted by route_bias.
- Paper: new Results subsection "Emergent maneuver: personality-movement propensities"
  (subsec:personality) delivering the Related-Work forward-reference; macros pers*/personalityNRep +
  report/gen/tab_personality.tex. Framed honestly as one demonstration on one scenario, not a general
  planner-dominance claim.

### 2026-07-22 - Verification & validation reframe (Sargent framework; modern Lanchester + V&V citations)

Response to a review concern that the validation rests only on Lanchester (a 1916 model with old
citations). No numbers change; this is a framing + citation strengthening of subsec:validation.
- Confirmed Lanchester is still current: paper already cited kress2020lanchester (2020); added
  hausken2025modeling (Annals of Operations Research 2025, heterogeneous-force Lanchester) and
  lucas2004fitting (Lanchester fit to Kursk/Ardennes real battle data). Firecrawl research also found
  a 2022-2025 wave of Lanchester attrition analyses (Ukraine FPV/Shahed drone economics).
- Reframed subsec:validation "Validation against Lanchester's square law" -> "Verification and
  validation": opens with Sargent's VV&A menu (sargent2013verification) and explicitly claims the
  FOUR legs SandTable already has: (1) verification/reproducibility (pure-function determinism +
  CRN); (2) extreme-condition/degenerate-limit tests (the byte-identical off-states: suppression->0
  recovers baseline, ammo->inf converges to fixed-Pk, baseline = degenerate kill web; cross-ref
  subsec:killweb); (3) face validity / expected-direction monotonicity (the sensitive-results
  criterion); (4) analytic cross-check (the existing Lanchester square-law match, kept verbatim as
  the analytic leg). The point: the model had a 4-technique validation story reported as a
  1-technique story.
- Discussion/limitations: named the stronger validation forms left open for future work: docking vs
  an independent model (axtell1996aligning), pattern-oriented validation (grimm2005pattern), and
  empirical comparison against exercise / high-fidelity ProjectGL traces.
- Citations: ref.bib 37 -> 42 verified entries (sargent2013verification, grimm2005pattern,
  axtell1996aligning, lucas2004fitting, hausken2025modeling; all carry % verified: provenance;
  lucas WARN is year 2003-online vs 2004-print, benign). Pre-flight PASS 5/5, 24 pages.

### 2026-07-22 - Bayesian test & evaluation (Ferry / DOT&E paradigm) demonstrated on SandTable

Researched James P. Ferry's (Metron, DOT&E-funded) Bayesian Decision Theory paradigm for T&E
(DATAWorks 2023 talk; ITEA J. 44-3 2023, 45-3 2024 "Dynamo"; FUSION 2024) and demonstrated it on the
centerpiece scenario. The mapping is 1:1: Ferry's hit/miss outcome = our per-replication binary
mission success; context = params; "likelihood is a simulator" = run_mission. No sim mechanic added;
this is post-hoc analysis of evaluate() output.

- src/sandtable/bayes_te.py (new): conjugate Beta-Bernoulli posterior + credible interval +
  P(p>=cut) compliance prob; Wald/Wilson (for contrast); decision_chart() = Bayesian Decision Theory
  SDP backward recursion over a compliance utility + per-trial cost -> Accept/Reject/Test grid;
  optimal_stop(); contrast() (posterior on p_B - p_A); discounted_prior() (M&S as a down-weighted
  prior, effective sample lam*n_sim) + expected_runs_to_confidence(). Pure functions, scipy.stats.
- tests/test_bayes_te.py (9 tests, all pass): conjugate symmetry, monotone P(>=cut), Wald degeneracy
  at extremes, chart terminal actions, continue-region shrinks with cost, stopping at extremes,
  contrast separation, discounted-prior effective sample size, and M&S prior saves runs. Full suite
  106 -> 115 passed. bayes_te is analysis-only, so run_mission is byte-identical (numbers.tex diff is
  +33 lines, all bte* macros, zero prior-macro changes).
- tools/make_bayes_te_numbers.py (new) -> report/data/bayes_te_{intervals,stopping,paths,contrast,
  prior,prior_curve}.csv. Fair fight (n_red=n_blue), N=300/design, gate p>=0.60. Findings:
  A. direct C0 span1:2, 248/300: Beta 95% CrI [0.78,0.87], P(success>=0.8)=0.88. Small n=8 (7 succ):
     Wald upper 1.10 (past 1.0) vs Beta 0.99. Bayesian gives a probability, not a broken interval.
  B. decision chart + optimal stopping: accept the compliant design in 7 reps, reject a failing one
     in 4, spend the most (12) on the design nearest the gate, vs the 300-rep fixed budget. Cost up
     -> continue-test region 279 -> 193 states -> stop sooner.
  C. paired contrast direct vs supervisory (C4, span1:8): P(super>direct)=1.00, advantage +0.27
     [0.21,0.33]. HONEST FINDING: CRN gives ~0 variance reduction (paired corr 0.03), because the
     single per-run RNG stream aligns initial conditions but desyncs once trajectories diverge;
     realizing CRN would need per-purpose substreams. Reported as-is, not overclaimed.
  D. FLAGSHIP - SandTable as a discounted Bayesian prior updated by sparse emulated high-fidelity
     runs (M&S-informed OT). Compliant design's M&S estimate, discounted to lam=0.10 (~30 eff obs),
     vs an emulated (bias-perturbed) high-fidelity truth 0.78: the informed test reaches a confident
     accept in ~0 expensive runs vs ~12 from scratch (~12 saved). Guardrail: if truth is actually
     0.40 (prior wrong), overturning to a confident reject takes ~65 HF runs at lam=0.10 but ~41 at
     lam=0.05 -> trusting M&S less overturns a bad prior sooner. This is the quantitative "fast tier
     feeds, not replaces, the slow tier" claim.
    NOTE: first D attempt backfired (runs_saved=-16.8) because the M&S source design (rate 0.58) sat
    on the opposite side of the 0.60 gate from the truth (0.68); fixed by sourcing the prior from a
    design where M&S and truth agree, and by capping the M&S effective sample via a heavy discount.
- Figure: tools/make_figures.py fig_bayes_te -> report/figures/bayes_te.pdf (a: decision chart +
  three evidence walks stopping at their verdict; b: CrI width vs HF runs, informed vs HF-only).
  Macros/table: make_numbers.py bayes_te() -> bte* macros + tab_bayes_te.tex.
- Citations: ref.bib 42 -> 45 (ferry2024paradigm FUSION 2024 doi 10.23919/FUSION59988.2024.10706400;
  ferry2023edou ITEA 44-3 doi 10.61278/itea.44.3.1007; ferry2024adaptive ITEA 45-3 doi
  10.61278/itea.45.3.1002; all verified). Naval Engineers J. 2024 has no exposed DOI -> not cited.
- Paper: new Results subsection subsec:bayeste (Fig fig:bayeste, Tab tab:bayeste). Pre-flight PASS
  5/5, 26 pages.

### 2026-07-22 - Drone-war increment: EW-immune link (M1), counter-UAS/SHORAD (M2), cost-exchange (M3)

Integrated three Russo-Ukrainian-war lessons as opt-in, byte-identical-off mechanics, each grounded in
verified literature and demonstrated driver -> CSV -> generated numbers/figure. Motivation: drones
central but effect contingent ("depends on the game", Kunertova 2023); air defense keeps pace in a
hider-finder competition (Calcara et al. 2022); fiber/terminal autonomy immune to EW (Bondar CSIS 2025;
Kunertova "Drones have boots" 2023). Grok/user framing honored: "consistent with", not "validates".

M1 - EW-immune command link (src/sandtable/c2.py, built earlier this session):
- Operator gains ew_immune + immune_latency. Direct-control branch draws the SAME two delivered()
  values, then link_ok = ew_immune or (up and down); lat = immune_latency if immune else comms.latency.
  RNG-aligned so the off-path is byte-identical. tests/test_ew_immune.py (4) + test_c2 field-set fix.
- Result (drone_fiber_link.csv, N=200, sc_span_control direct, n_blue=4 n_red=4): jammable success
  0.54(C0) 0.50 0.505 0.37 0.215(C4) 0.215(C5); immune FLAT 0.605 across the whole ladder (comms enters
  only via the C2 link here, which the immune link bypasses). C0 gap (+0.065) within MC noise (+/-0.069
  at N=200); heavy-jam gain ~+0.39 (C4). Consistent-with Bondar 10-20%->70-80% (directional support).

M2 - counter-UAS/SHORAD (src/sandtable/counter_uas.py, NEW; sim.py hook after engagement):
- build_counter_uas(scn, ent) -> None unless cuas_rate>0 (opt-in; byte-identical off: zero RNG when
  off). Captures committed swarm size n0. step(): draws rng.random(n_live_uas); p_kill=min(1,rate*
  n0**sig); a UAS within cuas_reach (2500 m) of a living red defender dies if draw<p_kill. Hazard keys
  on COMMITTED n0 (not live count), so it does not self-limit as the swarm thins.
- WHY interior peak: measured exposure window E ~ mission length (n=1,3 run full 1800 steps; n=6 wins by
  step ~609). Constant hazard => expected survivors n0*(1-p)^E ~ n0*exp(-rate*E*n0^sig), interior-peaked.
  Linear sig=1 => broad plateau (coverage saturates high for big swarms, redundancy). Superlinear sig=2
  steepens the tail: a massed swarm is gutted BEFORE the ground force reaches the red zone (~step 500).
  Probes (scratchpad/probe_cuas.py): sig=1 rate2.5e-4 tail too flat; sig=1.5 rate1.4e-4 peak-tail 0.05
  (noise); sig=2.0 rate6e-5 CLEAN peak (chosen; default cuas_signature=2.0). First (wrong) design used
  per-step LIVE-count hazard -> too lethal (even a lone UAS wiped, uniform failure); fixed by tiny rate
  + initial-size key + superlinear exponent.
- Result (drone_cuas_swarm.csv, N=200, UC-5): OFF success climbs+saturates 0.14 0.305 0.515 0.525 0.61
  0.72 0.70 (n=1..8), no interior penalty. ON success 0.17 0.355 0.505 0.435 0.415 0.33 0.29 -> CLEAN
  interior peak at n=3 (0.505), tail 0.29 at n=8 (drop 21 pp vs peak; small n=1 0.17). Coverage tracks
  it. air_losses at n=8 ON = 7.5 of 8.
- Acceptance test PASSES (tests/test_counter_uas.py, 6): baseline monotone (large>small+0.15); under
  C-UAS mid(3)>small(1)+0.10 AND mid(3)>large(8)+0.10 at NREP=60; + byte-identical-off (8 seeds),
  gating, n0 capture, attrition (air_losses up, coverage down vs off).

M3 - cost-exchange KPI (src/sandtable/metrics.py, output-only, byte-identical):
- compute() gains air0 (from sim.py) + blue_air_losses, blue_ground_losses, blue_cost_lost, cost_exchange.
  Unit costs default 1.0 => per-run cost_exchange == loss_exchange exactly (benign default; prior numbers
  unchanged). test_metrics EXPECTED_KEYS +4, +2 tests (defaults-to-loss_exchange; domain weights).
- Study cost-exchange is the RATIO OF MEANS (mean red value destroyed / mean blue cost lost), computed in
  the driver, NOT the mean of per-run ratios (which is dominated by near-zero-loss denominators; the
  per-run metric gave a misleading 7.9 at n=3). Stipulated relative costs uas=1, ugv=20, red=15. Result
  (ON): 0.47 0.81 1.10 0.99 0.98 0.75 0.58 (n=1..8) -> interior peak at n=3 (1.10, ~break-even),
  collapses to 0.58 at n=8. Oversized swarm bleeds 7.5 drones AND fails the assault (expensive UGVs lost).
- Full suite: 127 passed / 0 skipped in the canonical mgl env (was 115): +6 counter_uas, +2
  metrics-cost, +4 M1 earlier. All prior byte-identical tests still pass => M2+M3 perturb no
  existing scenario. (Count is env-dependent: a leaner env without the polarisopt/torch extras
  skips the integration tests and reports ~120 passed / 1 skipped; the 127 figure is the full mgl run.)

- tools/make_drone_numbers.py (NEW, N=200) -> drone_fiber_link.csv, drone_cuas_swarm.csv.
- tools/make_figures.py fig_drone -> report/figures/drone.pdf (a: fiber crossover-flattening; b: swarm
  interior peak + cost-exchange twin axis). make_numbers.py drone() -> fiber*/cuas* macros + tab_drone.tex
  (gain/drop macros computed from rounded endpoints for prose self-consistency).
- ref.bib 45 -> 49: calcara2022drones (10.1162/isec_a_00431), kunertova2023depends
  (10.1080/00963402.2023.2178180), kunertova2023boots (10.1080/13523260.2023.2262792), all CrossRef-
  verified 2026-07-22; bondar2025autonomy (CSIS, WebFetch 2026-07-22, manual provenance).
- Paper: new Results subsec:drone (Fig fig:drone, Tab tab:drone). Discussion limitation reframed (UC-5
  "no air defense / upper bound" now addressed by the opt-in C-UAS layer); contributions para extended;
  Extensions: SHORAD marked delivered + GNSS-denial roadmap added.
- Pre-flight: PASS 5/5 (49/49 citations verified, 1 AI-vocab hit, 0 em-dashes, 7/7 contribution refs
  resolve incl. new item 6, compile clean). 28 pages (was 26). Cost-exchange reported as ratio of means
  (mean red value / mean blue cost), not the per-run mean-of-ratios (which gave a misleading 7.9 at n=3).

## Autoresearch increment: the operator queue (`aug12` run, CR-10 through CR-15)

Workflow 7, Mode I, unattended. Ledger of conjectures and verdicts: `doc/autoresearch-conjectures.md`.
Experiment ledger: `results.tsv` (26 rows, exp 1--26). Contract: `.autoresearch/contract.json`, frozen
scoring surface, `guard` run at the head of every job. Two tiers: proxy 16 blocks x 16 reps, full
32 x 64 (noise floor MDE 0.0246 < MPE 0.03, exp 4). A "seed" is a BLOCK: block b at R reps runs
mission seeds bR..bR+R-1, which turns the binary per-mission `success` into a continuous paired value
and makes the gate a seed-matched paired test.

### The mechanism (C8, the central finding)

- Under the model as first published, an asset that waits past its patience P stops waiting, but the
  operator does not find out. It works every request it receives, including requests whose answer
  arrives after the requester has gone autonomous. The slot is spent either way, the queue lengthens,
  the next answer is later still, and past a threshold the queue sustains its own overload.
- CR-10 added `queue_policy` in {`blind` (published default), `refund` (frees the slot), `admit`
  (frees the slot AND tells the requester after 2*lat)}. Opt-in: `blind` reproduces code hash
  `90c4763ba205b9d8` byte-for-byte, verified on both laptop and Hopper.
- Closed forms (`tools/queue_theory.py`, cross-checked against a standalone exact queue sim):
  latency cut-off l* = (P - 1/mu)/2 = 6.67 steps; collapse span n* = c(P + tau)mu/d with
  d = (1-p_drop)^2, giving 6.30 on one console and 12.60 on two at the published operating point.
  The link enters ONLY through d, so jamming RAISES the threshold.

### Gates that passed at full tier (32 x 64, seed-matched paired)

| id | contrast | effect | t | blocks won |
|----|----------|--------|---|-----------|
| G1 | admit vs blind, n=8, C0, published physics | +0.2373 | 16.14 | 32/32 |
| G2 | blind C2 vs C0 (jamming helps) | +0.1143 | 7.29 | 29/32 |
| G3 | admit C0 vs C2 (sign reversal) | +0.0386 | 2.63 | 23/32 |
| G4 | admit vs blind, teleop physics, n=8, C0 | +0.7451 | 57.39 | 32/32 |
| G5 | teleop blind C2 vs C0 | +0.2817 | 26.34 | 32/32 |

All five recomputed from the per-block `vals=` in the run logs by `tools/make_queue_numbers.py`, which
emits `report/gen/tab_queue_gate.tex`, so the paper's statistics are generated, not transcribed.

### Supporting results

- P2a (2x2, full tier): `service_rate` creates and destroys the interior optimum exactly at n*. The
  same span n=4 shows it with a slow operator and not the published one; n=8 shows it with the
  published operator and not a fast one.
- P2b (full tier): `patience` moves l* through three transitions. pat20 -> C4 and C5 both dead
  (goodput 0.000); pat30 -> C4 resolves (0.416), C5 still dead; pat45 -> both resolve (C5 0.195).
- C10 staffing curve (CR-14, multi-console, `st-gateB-9437187`): 1 console mid-transition at n=6
  (goodput 0.759) and floored at n=8 (0.170), bracketing 6.30; 2 consoles 0.810 at n=12 and 0.045 at
  n=16, bracketing 12.60; 3 consoles still 0.972 at n=16, below 18.90. Adding a console moves a
  cliff rather than raising goodput uniformly. -> `report/gen/tab_staffing.tex`.
- C9 fan-out (`st-searchC-9437188`): 1 + NT/IT is load-dependent (3.88 at n=2 to 2.13 at n=12), never
  equals the true sustainable span at any load, and is nearly flat (2.18 -> 2.14) across the interval
  where delivery fails. NEGATIVE result, promoted as such.
- P3 latency/loss decoupling: latency monotone harmful (goodput 0.180 at lat0 -> 0.113 at lat6 ->
  0.000 at lat8, all drops); loss hump-shaped, peaking at p_drop = 0.2 (0.539) and falling to 0.201
  at 0.55. The C0--C5 ladder raises both together and therefore confounds two effects of opposite
  sign. The `lat8` row is exactly 0.000 across every drop, which is l* = 6.67 being obeyed.
- CR-15 terrain-correlated demand: coupling request rate to trafficability moves the collapse from
  n=8 to n=6 (goodput 0.767 -> 0.255 at n=6). T3 route choice: direct control + terrain demand peaks
  at route_bias 0.85 (0.902) and FALLS to 0.539 at full cover, while dir_flat (0.988), sup_terr
  (1.000) and adm_terr (0.992) all still peak at 1.0. The interior optimum needs both halves of the
  coupling; it is an artifact of the human in the loop, not of the ground.

### Two readings retracted before promotion (both caught by cheap robustness checks)

- CR-13. One seed suggested the collapse was a startup transient (goodput 0.013 -> 0.361 under a
  staggered start). Sixteen blocks showed only +0.01--0.05. Refuted, exp 10.
- The "throughput cliff." At the published 1800 s window, blind delivers 2.21 vehicles at n=6, 0.68
  at n=8, and 0.00 at n>=10, which read as a capacity cliff peaking at the predicted n*=6.30. The
  duration battery (`st-duration-9439929`, scenario variants at 3600 s and 7200 s sharing `id` so
  common random numbers still pair) shows 3.89 at n=10 and 5.16 at n=12, and blind becomes monotone
  increasing in span. Refuted, exp 26. What survives is a TEMPO penalty that a deadline converts into
  failure, plus the fact that `admit` is byte-identical at all three windows. The window must be
  named whenever the delivered-vehicle numbers are quoted; the paper does so in both the results
  subsection and the limitations.

### Infrastructure and artifacts

- Compute moved to GMU Hopper (conda env `pol`) after the laptop overheated. `hopper/` holds
  `sync.sh`, `ar_job.sbatch` (runs `guard`, stamps host/code-hash/tier), `submit.sh`, `watch.sh`,
  `collect.sh`, `poll.sh`, and `batteries/*.sh`. Fairshare priority, not job size, was the queue
  constraint (32-core/6h estimated next-day, 16-core/2h barely better); the fix was the `interactive`
  partition with batteries chained per allocation. Job IDs: 9437166 (theory), 9437187 (gateB),
  9437188 (searchC), 9439929 (duration).
- Run logs staged for the paper at `report/data/queue/*.out`; the Hopper originals stay in
  `runlogs/hopper/`.
- `tools/queue_theory.py` (closed forms + exact standalone queue sim + `--scenario`),
  `tools/ar_table.py` (renders AR_ROW logs as arm x sweep tables with paired gating markers),
  `tools/make_queue_numbers.py` (54 macros -> `report/gen/queue_numbers.tex`, plus
  `tab_queue_gate.tex` and `tab_staffing.tex`, plus an appended block in
  `report/results/numbers.txt`), `tools/make_figures.py:fig_queue` -> `report/figures/queue.pdf`,
  and `tools/byte_identity.py`. No queue number in the paper is typed by hand; the gate table's
  paired t and blocks-won are recomputed from the per-block values, and the figure reads the same
  logs, so text, table, and figure cannot drift apart.
- New tests: `test_queue_policy.py`, `test_stagger.py`, `test_crew.py`, `test_terrain_demand.py`,
  `test_queue_theory.py`. One pre-existing test asserted that `intervention_rate` RISES with jamming
  under direct control; it falls, because jamming removes requests. The failing assertion was the
  finding, and it is now asserted in the correct direction with `hold_fraction`.
- `duration` is a Scenario field, not a `params` entry, and `tools/ar_eval.py` is frozen by the
  contract, so the duration battery uses scenario variant files
  (`experiments/ar_scenarios/sc_span_control_d{3600,7200}.json`) that deliberately keep `id` unchanged
  so `make_rng(seed, scn.id)` still pairs across variants.

### Verification at promotion

- Full suite on Hopper (job 9441155's sibling 9441117, node amd043, 4 cores): **182 passed, 0
  failed** in 175 s. Tamper guard OK, 2 frozen paths unchanged.
- Byte identity is checked as a VALUE comparison, not a digest (`tools/byte_identity.py compare`
  over 4 scenarios x 8 seeds). A digest over the whole metric dict necessarily moves when an
  increment adds output-only diagnostics, and would have read as a failure while hiding the fact
  that nothing measured changed. Against commit 75a5b3e: **all 15 pre-existing metrics identical,
  13 new diagnostics added**.
- Cross-platform determinism (laptop macOS/arm64 vs Hopper Linux/AMD, job 9441155): **all 28
  metrics identical across 32 runs**.

### Paper changes

New Results subsection `subsec:queue` (Figure `fig:queue`, Tables `tab:queue_gate`, `tab:staffing`); a closed-form
paragraph with `eq:nstar` and l* added to `subsec:command`; the ladder-confound sentences added to
`subsec:comms`; abstract extended with the mechanism and the admission-control numbers; a seventh
contribution item; a queueing-with-abandonment passage in related work
(`garnett2002impatient`, `gans2003callcenters`, `cummings2008predicting`, and two added after a
follow-up search: `ibrahim2018announcements` on staffing versus delay announcements as two controls
on one congestion, and `humann2023multioperator` as the closest multi-operator simulation precedent); a Discussion paragraph on
what the mechanism changes for design guidance; two limitations (abandonment semantics are a modeling
choice; the 1800 s window is part of the claim); and the Extensions "network of servers" item rewritten
now that multi-console is delivered. Pre-flight: PASS 5/5 (55/55 citations verified, 3 AI-vocabulary
hits, 0 em-dashes, 8/8 contribution refs resolve, compile clean). 35 pages (was 28).

## CR-16, service order: a null, and why the null is the useful part

Workflow 7 continued. Ledger entries 28-30 in `results.tsv`; full write-up in
`doc/autoresearch-conjectures.md`.

### The design was scrapped before it was written

The proposal was "serve the request with the least remaining patience." Reading `c2.py` first
showed that rule is a no-op here. There is no queue object: a request's whole future is fixed at
arrival (`start = max(operator_free_at, k+lat)`, `done = start + 1/mu`, `reply = done + lat`), and
the queue is the scalar reservation horizon. Every requester carries the same patience `P`, so all
requests competing at a given moment have identical slack, and reordering two feasible requests
swaps WHICH vehicle is served, never HOW MANY. Ordering can therefore only bite through
heterogeneity in what the help is worth.

### What was built

`params["queue_discipline"]` (default `fcfs`, byte-identical off) with the order computed by the
pure helper `c2.service_order`. Four arms, two of which are controls rather than treatments:

| arm | role |
|-----|------|
| `fcfs` | default |
| `random` | NULL CONTROL. Reordering the loop also reassigns which entity draws which random number, so a priority arm moves two things at once; this moves only the RNG assignment |
| `hard_first` | treatment (descending terrain difficulty) |
| `easy_first` | ADVERSARIAL CONTROL. A real priority effect has to be two-sided |

Priority sorts are stable, so on uniform ground they degenerate to `fcfs` rather than to an
arbitrary permutation, which is what makes a flat result mean "ordering did nothing."

### Result

Proxy (`st-triage-9442644`, 16x16, 74 gated comparisons against `random`): 5 marked, 69 unmarked,
a ~7% marking rate consistent with the gate's own false-positive rate. The five are incoherent as a
priority story: the one X2 marker favors the ADVERSARIAL arm, and the three X3 markers are all
three deterministic arms losing to `random` at one span, which is the RNG-reassignment signature
the `random` control exists to expose. X4 (one span, sweeping the driving heterogeneity) marks
nothing and shows no dose-response.

Full tier (`st-triagefull-9442679`, 32x64), run because a 16x16 null only rules out an effect
larger than its MDE of roughly 0.05-0.06 against an MPE of 0.03:

- Y1, the cell where the effect had to be (strongest coupling, congested span): `random` 0.504,
  `hard` 0.503, `easy` 0.506. Spread 0.003.
- Y2, the one proxy cell that gated: the 0.121 gap shrinks to 0.031 and no longer gates.
  Multiple-comparison artifact.
- Y3, throughput invariance: goodput 0.084/0.084/0.081/0.085 at `terrain_demand=2` and
  0.049/0.049/0.049/0.050 at 4, across fcfs/random/hard/easy.

### Why, which is what makes it publishable

The obvious worry about a null is that the arms never reordered. Instrumenting a live run says they
did: `hard_first` displaces 4.8 of 8 vehicles on average and leaves the order unchanged on only 11%
of steps. What is missing is the signal. The difficulty spread ACROSS THE SUPERVISED VEHICLES is
0.044 on average (`tools/make_triage_numbers.py`, 8 seeds), against 0.650 available across the map.
The terrain is not flat; its variation is almost entirely LATERAL (0.601 across the lateral profile
at mid-map, against 0.066 along the open corridor and 0.135 along the covered band), and a
formation heading down one lane to one objective samples 8-20% of the range.

A power probe confirmed this is structural: raising `spawn_spread` from 40 to 700 moved the
observed spread only 0.054 -> 0.059, because the vehicles converge onto the same route within a few
hundred steps. The variant was discarded rather than kept.

So: triage by need is throughput-neutral by construction and value-neutral in practice, because an
operator supervising one formation on one route has almost no need dispersion to exploit. That is a
statement about the command architecture, not about queue discipline in general, and it points at
the heterogeneous-operator/handoff work still open under CR-14.

### A test failure worth recording

The first `tests/test_triage.py` asserted that the two priority arms bracket the null on 12 seeds.
It failed. The cause was sample size, not mechanism: a binary metric over 12 seeds moves in steps
of 0.083, so the "effect" was 1-3 seeds. Rewritten as deterministic mechanism checks on the
extracted helper; effect sizes belong to the gated battery, pytest asserts mechanism.

### Paper

No results subsection. `queue_discipline` stays in the model because the null should be
reproducible. Two additions only: a passage in the Discussion (ordering is not on the list of
fixes, with the \qTriageSpread{} number and the structural reason) and a Limitations paragraph
bounding what the admission-control recommendation claims, with \qTriageSeen{} against
\qTriageMap{}. The Discussion's earlier phrase "fix the queue discipline" was changed to "fix the
admission policy" to avoid colliding with the new parameter name. Numbers generated by
`tools/make_triage_numbers.py` -> `report/gen/triage_numbers.tex`.

Pre-flight: PASS 5/5 (55/55 citations, 3 AI-vocabulary hits, 0 em-dashes, 8/8 contribution refs,
compile clean). Full suite on Hopper (job 9442696): 192 passed, 0 failed (was 182; +10 triage).
Byte identity re-verified after the `service_order` extraction: 28/28 metrics unchanged.

## 2026-08-22 R3 mechanism: notification and the price of waiting

**Local probe (32 seeds, sc_span_control, published physics, direct/C0).** Served useful
decisions per step = `operator_utilization * service_rate`. Neither `refund` nor `admit` ever
claims a console for a request it cannot finish, so for those two arms utilization counts only
work that reaches someone.

| n_blue | policy | goodput | utilization | served/step |
|---|---|---|---|---|
| 6 | refund | 0.9201 | 0.7378 | 0.11068 |
| 6 | admit | 0.9089 | 0.7789 | 0.11683 |
| 8 | refund | 0.8029 | 0.8635 | 0.12953 |
| 8 | admit | 0.7378 | 0.8856 | 0.13285 |
| 10 | refund | 0.6851 | 0.9400 | 0.14100 |
| 10 | admit | 0.5948 | 0.9491 | 0.14236 |
| 12 | refund | 0.5987 | 0.9695 | 0.14543 |
| 12 | admit | 0.4509 | 0.9923 | 0.14885 |

`admit` completes MORE useful decisions per step at every span while its goodput is lower at
every span. R3's goodput ordering is therefore a ratio effect (notification raises the request
rate, so the denominator moves more than the numerator), not a throughput loss. The manuscript
clause "notification buys requester tempo at the price of operator efficiency" was wrong and is
replaced; the n=8 pair is now generated as `\qServedAdmit` / `\qServedRefund` by
`tools/make_queue_numbers.py:served_per_step`.

**Decisive cell submitted: `st-waitcost-9443162`** (full tier, 32 blocks x 64 reps, interactive
partition, 3h). `q_stall` (quality while awaiting a decision, default 0.30) swept over
0.10 / 0.30 / 0.50 against `q_fallback` = 0.50, arms blind/refund/admit, at published physics
(W1) and teleoperation physics (W2), n=8, C0. Waiting is free at q_stall = 0.50. Competing
predictions registered BEFORE the run: if notification's only job is ending a wait, the
admit-refund increment falls monotonically in q_stall and vanishes at 0.50, at both physics
settings; if the teleop-only increment is instead an artifact of that physics, the increment is
flat in q_stall. `blind` rides along as the control against the whole queue effect scaling with
q_stall.

### st-waitcost-9443162 (full tier, 32 blocks x 64 reps, interactive, complete)

`q_stall` swept 0.10 / 0.30 / 0.50 against `q_fallback` = 0.50, n=8, C0, blind/refund/admit.

| contrast | physics | q_stall=0.10 | 0.30 | 0.50 |
|---|---|---|---|---|
| admit - refund | published | +0.0161 (t=1.37) | +0.0142 (t=1.37) | +0.0093 (t=0.89) |
| admit - refund | teleop | **+0.0913 (t=5.59)** | **+0.0801 (t=4.97)** | **+0.0459 (t=3.72)** |
| refund - blind | published | **+0.3062 (t=20.05)** | **+0.2231 (t=14.65)** | **+0.1768 (t=14.01)** |
| refund - blind | teleop | **+0.5962 (t=73.93)** | **+0.6650 (t=78.47)** | **+0.7495 (t=105.02)** |

Bold = gated. Registered predictions were a monotone decline to zero (wait-cost reading) or a flat
profile (artifact reading). **Neither.** The notification increment declines monotonically and
stays gated: it halves from 0.0913 to 0.0459 as waiting becomes free, so the cost of waiting
carries about half of it. Under published physics it is not gated at any wait cost, which retires
the question of whether the earlier non-gate at q_stall=0.30 was an underpowered miss.

Decomposition of the teleop increment at the published q_stall (0.0801): quality-of-waiting
0.034 (the 0.30-to-0.50 drop), stopped motion 0.037 (the teleop-minus-published gap at matched
q_stall=0.50), residual 0.0093. The middle term is inferred from a cross-physics difference at
matched q_stall rather than gated directly.

Unexplained and flagged: `refund - blind` rises with q_stall under teleop and falls under published
physics. Opposite signs on the same sweep.

Note the q_stall=0.30 published cell reproduces the earlier st-refund-9442831 value (+0.0142,
t=1.37) to four decimals, which confirms the harness is pairing on the same block seeds.

### st-hyst-9443432 (full tier, submitted)

CR-17 fold band. H1/H2 sweep n_blue = 3,4,5,6,8 across {burst, staggered} x {retry, no retry} on
`success` and `operator_goodput`; H3 asks whether refund and admit close the band at n=5; H4 sweeps
`retry_backoff` = 4,8,12,16,20 against the predicted floor of 15.33. Gated by difference of
differences (`tools/ar_contrast.py --did`), because staggering perturbs the RNG stream and has a
direct effect of its own. Predictions registered in `doc/autoresearch-conjectures.md` under CR-17.

**The `refund - blind` sign reversal, resolved (local probe, 32 seeds, n=8, C0).** It is a floor
effect plus a missing channel, not a queue puzzle.

| physics | policy | q_stall=0.10 | 0.30 | 0.50 | hold fraction |
|---|---|---|---|---|---|
| teleop | blind | 0.031 | 0.031 | 0.031 | 0.46 |
| teleop | refund | 0.719 | 0.844 | 0.906 | 0.39 |
| published | blind | 0.375 | 0.469 | 0.656 | 0.00 |
| published | refund | 0.750 | 0.781 | 1.000 | 0.00 |

Under teleoperation the blind arm is pinned at 0.031 for every value of `q_stall`. It cannot
benefit from cheaper waiting because its vehicles are stopped 46% of the mission and `q_stall`
is a control-quality parameter: it prices what a waiting vehicle can do, and a stopped vehicle
does nothing regardless. Only `refund` has room to move, so the gap widens. Under published
physics nothing is stopped, `q_stall` acts through the speed multiplier `0.35 + 0.65*q_stall` on
both arms, and the arm with more waiting (blind, +0.281) gains slightly more than the arm with
less (refund, +0.250), so the gap narrows. Note also that refund's goodput is flat across the
sweep (0.801 / 0.797 / 0.792) while its success rises by 0.19: `q_stall` prices the consequence
of waiting, not the amount of it.

**Correction (same day).** The three-way split of the notification increment (quality of waiting
0.034, stopped motion 0.037, residual 0.0093) was published to the manuscript and then withdrawn
from it. Review found it is not gateable as built: the stopped-motion term subtracts the
published-physics arm from the teleoperation arm at matched `q_stall`, but those arms differ in
two things at once (the behavior layer is absent under published physics AND `teleop_stop` is
off), so the difference crosses two response surfaces and isolates neither factor. The residual
was ungated noise reported as a 12% component. The manuscript now reports the sweep and the
conditional it supports, and no decomposition.

The clean design is a 2x2 factorial inside the teleoperation stack (`teleop_stop` x `q_stall`,
with `blue_behavior="auto"` throughout), submitted as `st-stopf-9443653`. Registered predictions,
from the reviewer, before the run: base +0.009, quality main +0.005, stop main +0.037, interaction
+0.029, the substantive claim being that the interaction is the largest single term, so the channel
is quality-of-waiting-while-stopped rather than quality of waiting.

### st-stopf-9443653 (full tier, complete): the factorial that replaced the withdrawn split

`teleop_stop` x `q_stall`, both inside the teleoperation stack (`blue_behavior="auto"`
throughout), n=8, C0, admit against refund.

| | q_stall = 0.30 | q_stall = 0.50 |
|---|---|---|
| stopped while waiting | **+0.0801 (t=4.97, 78%)** | **+0.0459 (t=3.72, 69%)** |
| still driving | +0.0142 (t=1.37, 66%) | +0.0093 (t=0.89, 53%) |

Bold = gated. **The gate accepts the contrast in exactly the two cells where the waiting asset is
stopped**, which states the conditional cell by cell with no subtraction between surfaces.

Two things fell out that were not the point of the run.

First, the `teleop_stop=False` cells reproduce the published-physics arm to four decimals
(+0.0142/t=1.37 and +0.0093/t=0.89 against W1's +0.0142/t=1.37 and +0.0093/t=0.89). The behavior
layer with the stop semantics off is the pre-CR-2 path, so the confound that motivated this run
has zero magnitude. The reviewer's objection was sound in principle and void in fact, which is
worth recording because the run that established it also produced the better presentation.

Second, the reviewer's registered predictions for the four factorial terms were confirmed to three
decimals: base +0.009 (measured +0.0093), quality main +0.005 (+0.0049), stopped-motion main
+0.037 (+0.0366), interaction +0.029 (+0.0293). **But none of the four terms passes the contract.**
The quality main effect is six times below the MPE of 0.03; the stopped-motion main effect clears
|t| and the MPE but fails sign consistency at 53%; the interaction fails on both. Only the total
in the stopped cell is gated. So the decomposition is right in its ordering and unreportable under
this contract, and the manuscript gives the cells instead. A higher tier would not rescue the
quality term: it sits below the smallest effect this contract will report by construction, which
is itself the finding that the standalone quality-of-waiting channel is practically zero.

### st-hyst-9443432 (full tier): CR-17 gated

**H1 (mission success) and H2 (operator goodput)**, difference of differences against the retry-off
control, which absorbs the initial condition's own direct effect:

| n_blue | H1 success | H2 goodput |
|---|---|---|
| 3 | -0.0020 (t=-1.68) | -0.0000 (t=-1.07) |
| 4 | -0.0078 (t=-0.50) | -0.0002 (t=-0.74) |
| **5** | **+0.3130 (t=18.22, 32/32)** | **+0.5722 (t=61.12, 32/32)** |
| 6 | +0.0010 (t=0.05) | -0.0232 (t=-6.78) |
| 8 | +0.0044 (t=0.24) | -0.0133 (t=-3.23) |

One span carries the whole effect, on both the mechanism and the outcome. Four vehicles is inside
the predicted band (3.75, 5.85) and shows nothing, which is a basin question rather than a
stability one: the collapsed branch is stable there, but a synchronized start is not a large enough
disturbance to reach it. The n=6 and n=8 cells are statistically distinguishable from zero and far
below the MPE, which is what a null looks like at 2048 missions per cell.

**H3, five vehicles, retry on, staggered start minus synchronized start:**

| policy | gap | t | gated |
|---|---|---|---|
| blind | +0.5900 | 63.01 | yes |
| refund | +0.0133 | 34.21 | no, below MPE |
| admit | +0.0301 | 68.65 | marginal |

Both slot-freeing policies collapse the band, by 44x for `refund` and 20x for `admit`. Discarding
work the operator cannot finish removes the bistability, not just the mean loss, which is the
strongest operational statement the queue thread has produced.

That `admit` closes the band slightly LESS completely than `refund` is not noise and has a reading:
notification returns a requester to service sooner, so it raises the request rate, which is the
same thing the retry loop does. Admission control's second half is itself a small reliance loop.

### st-burst-9443645 C1 (full tier): burstiness does not move the crossover, and does nothing at n=6

| rung | direct: GE - Bernoulli | supervisory |
|---|---|---|
| 0 | +0.0000 | +0.0000 |
| 1 | -0.0156 (t=-0.98) | +0.0000 |
| 2 | -0.0078 (t=-0.42) | +0.0000 |
| 3 | +0.0039 (t=0.27) | +0.0000 |
| 4 | +0.0000 | +0.0000 |
| 5 | +0.0000 | +0.0000 |

Nothing gates. Supervisory is exactly zero at every rung, which is the correctness check: it does
not use the link for decisions, so a channel change must not touch it.

**This retires a local probe that misled me.** At 48 seeds the same cell read 0.667 for Bernoulli
against 0.521 for Gilbert-Elliot at rung 2, which I took as a real effect. At 2048 missions per
cell it is -0.0078. The lesson is the one the contract exists to enforce: a 48-seed probe on a
binary outcome is a hypothesis generator, never evidence.

The null is consistent with the closed form rather than against it. Six vehicles sits well below
both predicted thresholds at every rung (7.96 Bernoulli against 7.37 bursty at rung 2), so the
queue has slack and the extra completed round trips are absorbed. The theory localizes the effect
near the threshold, which is what `st-bspan-9443684` sweeps span to find.

### st-bspan-9443684 S1 (full tier, rung 3): the registered sign flip, confirmed in shape

`ge - bern` on mission success, span sweep at a matched mean drop rate of 0.20:

| n_blue | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|
| effect | +0.0288 | +0.0039 | -0.0171 | **-0.0488** | **-0.0522** | -0.0293 | +0.0186 | +0.0005 |
| t | 1.85 | 0.27 | -1.09 | **-3.23** | **-3.82** | -2.32 | 1.79 | 0.06 |

Bold = gated. The registered profile holds: burstiness HELPS at small span, where the extra
completed round trips are answers a vehicle wanted; crosses zero; HARMS at intermediate span,
where they are load the operator cannot absorb; and converges once both arms are collapsed.

The placement is off. The registered bracket was (8.60, 10.08), the two predicted thresholds. The
harm is gated at 8 and 9, just below the bursty threshold rather than between the two, and the zero
crossing sits near 6.5 rather than 8.60. The closed form locates the span at which the collapsed
state becomes self-sustaining, not the span at which queueing starts to bite, and the second is
about one and a half vehicles to the left of the first. The mechanism is confirmed and the
quantitative placement is not; both belong in the report.

### CR-18: the burstiness result was an artifact of clocking the channel in messages

Review (round 4) found the defect and it is real. The Gilbert-Elliot chain advances one transition
per MESSAGE, and `c2.step` drew the request and the reply back to back, so the model treated the
two as adjacent in channel time even though the operator's service delay separates them by tens of
steps in mission time. That inflates round-trip delivery from `(1-p)^2` to `(1-p)(1-p_gb)` for a
coding reason rather than a physical one.

The repair prices the reply at the moment it is actually sent. For a chain with second eigenvalue
`lam = 1 - p_gb - p_bg`, a message sent `L` steps after a delivered one survives with probability
`1 - p(1 - lam^L)`, which is `1 - p_gb` at `L = 1` and decays to the marginal `1 - p`. One uniform
either way, so the stream is unmoved; `channel_clock="message"` remains the default and is
byte-identical across 29 metrics and 32 runs.

Realized round-trip delivery, n=8, direct, 32 seeds:

| rung | Bernoulli | GE message-clocked | GE step-clocked |
|---|---|---|---|
| 1 | 0.9057 | 0.9352 | 0.8945 |
| 2 | 0.8180 | 0.8703 | 0.8210 |
| 3 | 0.6348 | 0.7598 | 0.6478 |
| 4 | 0.4172 | 0.5593 | 0.4199 |

**Step clocking returns the handshake to independence at every rung.** The service delay outruns
the channel's coherence, so the whole effect disappears, and with it the closed-form threshold
shift and the gated S1 sign flip. The honest conclusion inverts the one I recorded earlier: at a
matched mean drop rate, burst structure does nothing to this operator queue, and the ladder's
`p_drop` IS a sufficient statistic for it.

Two things survive. The closed form is the correct description of the adjacent limit, which is the
right physics for a jammer whose sweep is slow against the round trip, so the two clocks bracket a
real (p, coherence/RTT) surface rather than one being simply wrong. And every published gated cell
is unaffected: Bernoulli has no chain to clock, so `reply_survives` reduces to `delivered` and the
result is identical, which `st-clock-9443902` K2 checks rather than assumes.

`st-bspan-9443684`'s S1 rows are retained as the measurement of the artifact's size, not as a
finding. `st-clock-9443902` K1 re-runs the same span sweep under both clocks; registered
prediction is that the flip vanishes under step clocking.

### The defile demo is a mixture shift, not a slowdown (48-seed histograms)

Per-seed `operator_goodput`, n=5, staggered (healthy) start:

| terrain_demand | retry on: fraction below 0.3 | above 0.7 | retry off: below 0.3 |
|---|---|---|---|
| 0.25 | 0.10 | 0.54 | 0.00 |
| 0.50 | 0.40 | 0.29 | 0.00 |
| 0.75 | 0.42 | 0.12 | 0.00 |
| 1.00 | 0.60 | 0.00 | 0.00 |

With the loop closed the distribution is bimodal (at demand 0.25, 23 of 48 seeds above 0.9 and 11
near 0.35 with a hollow middle) and terrain moves the MIXING FRACTION between the two branches. With
the loop open it is unimodal at every terrain setting, 48 of 48 seeds above 0.9 at demand 0.25 and
none below 0.7 even at 1.0. So the mean moving smoothly is the average of a fraction migrating
between two branches, not each mission degrading. That is the tipping evidence, and it is stronger
than the mean contrast that motivated it.

### st-hyst-9443432 H4: the backoff floor confirmed as a measured design rule

Initial-condition gap at five vehicles, retry on, sweeping the backoff:

| retry_backoff | 4 | 8 | 12 | 16 | 20 |
|---|---|---|---|---|---|
| gap | **+0.5900** | **+0.2644** | **+0.0413** | +0.0251 | +0.0186 |
| t | 63.01 | 36.49 | 32.30 | 42.21 | 34.87 |

Bold = gated (the last two fall below the MPE). The band stays reportable through a backoff of
twelve and stops being reportable by sixteen, and **the predicted floor of 15.33 falls inside that
interval.** The reviewer registered "open at 4/8/12 and closed at 16/20" before the run, which is
exactly what happened. This is the one place in the queue thread where a closed form yields an
actionable setting rather than a description, so its confirmation matters more than its size.

### st-burst-9443645 C2: gated, and quarantined pending the clock check

The difference of differences (bursty minus memoryless, with the reliance loop minus without) is
-0.2009 / -0.2869 / -0.2114 on operator goodput at rungs 1 / 2 / 3, all gated at 32 of 32 blocks.

**Not reported as a finding.** These are message-clocked runs, and CR-18 shows that clocking
inflates round-trip delivery, which is extra offered load, which is exactly what pushes five
vehicles across the fold band. The interaction may be entirely the artifact acting through the
band that H1 established. `st-bclock-9443926` re-runs it under `channel_clock="step"`; registered
prediction is a null at every rung. If it survives, burst structure has a channel into this model
that is not the scalar `d`, and the Fano evidence says it should not.

### st-defile-9443710 D4: the backoff floor cuts the cost of difficult ground by 85%

Hard ground minus flat, five vehicles, staggered start, retry on, sweeping the backoff:

| retry_backoff | 4 | 8 | 12 | 16 | 20 |
|---|---|---|---|---|---|
| terrain penalty | -0.5189 | -0.5113 | -0.3439 | -0.1474 | -0.0755 |
| t | -87.67 | -107.40 | -80.41 | -51.07 | -60.50 |

All gated: difficult ground always costs something. But the cost falls sevenfold as the backoff
crosses the predicted floor, from -0.52 at a backoff of four steps to -0.076 at twenty. The residual
is the part terrain imposes directly by shortening the decision interval, which no backoff rule can
touch. This is the design rule working on the case that matters operationally rather than on the
synthetic initial-condition contrast that established it.

### st-bspan-9443684 S2: the artifact replicates one rung down

`ge - bern` on mission success at rung 2 (mean drop 0.10):

| n_blue | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|
| effect | **+0.0391** | -0.0078 | **-0.0815** | **-0.0659** | -0.0220 | +0.0103 | +0.0000 | -0.0059 |

Same shape as S1 and shifted one vehicle left, as the lower rung's lower thresholds require: harm
peaks at 7 and 8 here against 8 and 9 at rung 3. The message-clocked artifact is therefore
reproducible and structured, not noise, which is what makes `st-clock-9443902` a real test: a
pattern this consistent across two rungs either survives physical clocking or it was never about
the channel.

### st-burst-9443645 C3: the interaction on mission outcome, quarantined with C2

-0.0630 / -0.1572 / -0.1191 at rungs 1 / 2 / 3, all gated. Held back for the same reason as C2.

### CR-18 completed: the request draw was still message-clocked

The first repair priced only the reply by its lag. `delivered` still advanced the chain one
transition per MESSAGE, so two requests from the same vehicle four steps apart were adjacent in
chain time no matter how much simulated time separated them. The completed repair indexes the chain
by TIME: `delivered` advances it by the steps elapsed since it was last resolved, so a chain
consulted rarely has decayed toward stationarity by the time it is consulted. Marginal drop rate is
unchanged (0.0495 / 0.0995 / 0.2016 / 0.3511 / 0.5494 against nominal), so the two channels still
differ only in structure, and the default clock is byte-identical across 29 metrics and 32 runs.

**`st-bclock-9443926` J1 refuted the null I registered**, and it ran the half repair. Interaction
(bursty minus memoryless, with the loop minus without), operator goodput at five vehicles:

| rung | message clock (C2) | half repair (J1) | full repair, 64-seed probe |
|---|---|---|---|
| 1 | -0.2009 | **-0.0793** | +0.0131 |
| 2 | -0.2869 | **-0.0960** | -0.0863 |
| 3 | -0.2114 | **-0.0560** | -0.0319 |

Bold = gated at full tier. Under the half repair, burstiness alone does nothing (-0.0011 / -0.0074 /
-0.0136, none gated) while burstiness with the reliance loop is gated at every rung. So burst
structure does reach this model through something other than the scalar `d`, and it only reaches it
when reliance closes the loop, which is what the reviewer registered as the one route back.

The 64-seed full-repair column is a probe and nothing more; the C1 lesson applies. `st-clock-9443902`
and `st-bclock-9443926` were cancelled and superseded by `st-clockfull-9444130`, which runs K1, K2,
J1 and J2 against the completed model. Registration this time, having been refuted once: the
interaction SURVIVES at rung 2 and is null at rung 1.

### st-defile2-9443773 E1: my registered interpretation says this is a moved cliff, not a drag

Difference of differences on operator goodput, five vehicles, sweeping terrain demand:

| terrain_demand | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|---|---|
| effect | +0.5722 | +0.4752 | +0.3682 | +0.2369 | +0.1627 | +0.1015 | +0.0765 |

All gated at 32 of 32. The profile is **monotone decreasing**, and the registration said: "a
single-peaked profile is the signature of a band being dragged past a fixed span; a monotone
profile would mean I am watching a moved cliff and not a band." So by my own criterion, terrain
does not tip a bistable team across a basin boundary. It removes the healthy branch.

The reading that survives. On flat ground the band already contains five vehicles, at (3.75, 5.80),
so there was never a band sitting above the operating point waiting to be dragged onto it. Adding
terrain demand shortens the decision interval, which lowers both edges, and the upper edge falls
below five first. Past that point only the collapsed state exists and the initial condition stops
mattering, which is exactly a monotone decline to zero. Terrain destroys the bistability by
removing the good state rather than creating it.

**The "defile tips the team" framing is therefore dropped.** It was never shipped to the
manuscript, which claims only what D4 gates: a longer backoff cuts the terrain penalty sevenfold.
That result now has its mechanism, and it is the same one: lengthening the backoff shortens the
cycle less, which raises both band edges, which puts the healthy branch back above five vehicles
even on difficult ground. The design rule works by restoring the good state, not by widening a basin.

Consistency check worth recording: E1 at terrain_demand = 0 reads +0.5722, which reproduces H2's
five-vehicle cell to four decimals from an independent job. The block pairing is doing what it
claims across submissions.

### A second, physical reliance loop exists in the model and is too weak to matter

`motion` reads `control_quality` as a speed multiplier and `terrain_demand` shortens the decision
interval on difficult ground, so a vehicle that gets poor control moves slower, lingers in the
defile, and asks for help more often. That is a closed loop with no retry in it at all. Reading the
retry-OFF arms of E1 asks whether it is strong enough to produce two states on its own:

| terrain_demand | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|---|---|
| stag - burst, retry off | +0.0178 | +0.0164 | +0.0175 | +0.0168 | +0.0163 | +0.0170 | +0.0102 |

Flat, and below the MPE at every setting. The initial condition buys the same +0.017 whether the
terrain coupling is off or at its strongest, which is the direct effect of desynchronizing the
first decision events and nothing more. So the physical loop exists and its gain around the loop is
below one; the behavioural loop's is above it.

That sharpens CR-17 rather than merely controlling for it. The finding is not that feedback between
failure and demand creates bistability, since this model contains such feedback already and it does
not. The finding is that a loop closing on the DECISION timescale (a retry four steps after an
abandonment) has enough gain and a loop closing on the MOVEMENT timescale does not.

### st-defile2-9443773 E2: the same monotone decline on mission outcome

| terrain_demand | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|---|---|
| effect | **+0.3130** | **+0.2163** | **+0.0879** | +0.0376 | -0.0034 | -0.0059 | -0.0229 |

Bold = gated. Bistability is gone by a terrain coupling of 0.75 and the profile is monotone on the
outcome metric as it was on the queue metric, so the moved-cliff reading holds on both. The zero
terrain cell reads +0.3130, reproducing H1's five-vehicle cell exactly from an independent job, as
E1 did for H2.

**Process note.** I first read this log at 28 of its 56 rows and got an empty E2 section, because
`hopper/collect.sh` rsyncs on a schedule and can copy a file a job is still writing. A partial log
is indistinguishable from a complete one by inspection: a half-written section just has fewer rows.
`tools/ar_contrast.py` now warns when a log lacks the runner's completion marker.
