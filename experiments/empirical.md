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
