# sandtable: Mission-level GL

A lightweight, pure-Python **mission-design simulator** for autonomy-enabled ground and air
formations. It is a low-fidelity, mission-level counterpart to the Army's Unreal-based
**ProjectGL**: it deliberately drops high-fidelity vehicle dynamics and rendering in favor of
"accurate enough" mission-level models (movement, terrain/mobility, sensing, engagement, C2), so it
can run thousands of times inside parameter sweeps and Bayesian optimization.

Built for project **FP6111 / VIPR-GS** (US Army GVSC via Clemson). See `CLAUDE.md` for project
context and `doc/` for the proposal and Testbed Design Document (TDD).

## Design in one paragraph

The simulator is a **pure function** `run_mission(config, seed) -> metrics`, over
**structure-of-arrays** agent state advanced by a **fixed-timestep** loop (NumPy first, `numba` on
hot spots as needed). Platforms follow the AFSIM-style component model
`Platform{mover, sensors, weapons, processor, comms}`; behaviors are physics-free (cookie-cutter
detection, aspect-sector probability-of-kill, trigger state machines) in the tradition of MANA and
Gaertner (NPS 2013). Optimization is driven by **[polarisopt](https://github.com/VadimSokolov/polarisopt)**
(DOE + BoTorch Bayesian optimization); the simulator plugs in as a CLI subprocess via the
`polarisopt` Simulator/Metric plugin contract (no fork), mirroring its `taxidemo` example.

## Scenarios (from TDD Section 11)

1. **Route vs defilade (UC-3)** - ground formation trades speed vs cover.
2. **Span-of-control x comms degradation (IV-A x IV-B)** - one operator supervises N autonomous
   assets across control modalities and the C0-C5 comms/EW ladder.
3. **Sensor swarm under EW (UC-5)** - UAS recon feeds a shared SA map cueing ground assets under
   jamming.

## Layout

```
src/sandtable/        simulator package (world, entities, motion, planning, sensing, engagement, c2,
                comms_ew, metrics, sim; plus polarisopt runner.py / plugin.py / opt_metrics.py)
scenarios/      declarative scenario specs
studies/        polarisopt study YAMLs (LHS/Morris sweeps + GP/qEI Bayesian optimization)
experiments/    empirical.md lab notebook + results/
tests/          unit + reproducibility + sensitivity tests
report/         academic-paper deliverable
```

## Environment

```bash
conda activate sandtable          # Python 3.12 env for this project
pip install -e '.[dev,graph,viz]'
# optimization driver (git only; add [bo] for the Bayesian-optimization backend = torch):
pip install 'polarisopt @ git+https://github.com/VadimSokolov/polarisopt.git'
```

## Run

```bash
# single mission, deterministic given the seed
python -m sandtable.runner scenarios/uc3_route_defilade.json /tmp/out.json   # slave CLI (polarisopt contract)
# or from Python:
python -c "from sandtable.sim import run_mission; from sandtable.scenario import load_scenario; \
           print(run_mission(load_scenario('scenarios/uc3_route_defilade.json'), seed=0))"
```
