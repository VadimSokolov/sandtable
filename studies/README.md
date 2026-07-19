# polarisopt studies

Optimization / sensitivity studies for `sandtable`, driven by
[polarisopt](https://github.com/VadimSokolov/polarisopt). Each study wires the
`mission` simulator (registered by `sandtable.plugin`) to a scenario and runs a DOE or
Bayesian-optimization phase. Run every command **from the repo root** so the
relative `scenario:` path resolves.

## Setup (once)

```bash
pip install -e '.[opt]'      # registers simulator type "mission" + metric "mission_score"
pip install 'polarisopt[bo]' # adds torch/gpytorch/botorch, needed only for the BO study
```

## The studies

| File | Phase | What it does |
|------|-------|--------------|
| `uc3_sweep.yaml`  | static LHS (48 x 20) | Response surface of the KPIs over `route_bias`, `formation_spread`, `tempo`. Stores raw KPIs per sample (identity metric). |
| `uc3_morris.yaml` | static Morris (40 x 20) | Elementary-effects screening: ranks the three knobs by influence (mu*) on the scalar `mission_score`. |
| `uc3_bo.yaml`     | sequential GP + q-EI | Minimizes `mission_score` (failure + tempo + attrition). LHS warm-up 12, batch 4, plateau/max-iter stop. |

```bash
polarisopt validate studies/uc3_sweep.yaml
polarisopt run      studies/uc3_sweep.yaml
polarisopt status   studies/uc3_sweep.yaml
polarisopt best     studies/uc3_bo.yaml      # BO winner
```

Analysis scripts (read the per-sample workspaces under `~/sandtable-runs/<study>/`):
`experiments/analysis/analyze_sweep.py`, `experiments/analysis/analyze_morris.py`.

## Objective: `mission_score`

```
J = w_fail*(1 - success_rate) + w_time*(time_to_objective / time_scale) + w_loss*blue_loss_frac
```

Defaults `w_fail=1.0, w_time=0.3, w_loss=0.5, time_scale=1800`. Lower is better.
Every term is on a 0..1 scale, so the weights express doctrine (how a commander
trades tempo against attrition against outright failure), not units. For a pure
descriptive sweep, use polarisopt's built-in `identity` metric with `keys: [...]`
instead (as `uc3_sweep.yaml` does).

## Scaling to GMU Hopper (HPC)

The same study runs on Hopper by swapping only the runner block: change
`runner.type` from `local` to `slurm` and add Hopper specifics
(`partition`, `--time`, `--mem`, `setup_commands` to activate the `sandtable` env)
under `runner.options`. polarisopt submits one `sbatch` per sample, checkpoints
to SQLite, and resumes after a master restart (`polarisopt resume`). The
simulator is CPU-bound NumPy, so use a CPU partition. Nothing in the simulator,
scenario, parameters, or metric block changes.
