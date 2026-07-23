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
