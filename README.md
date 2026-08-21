# sandtable: a mission-level testbed for human-machine teaming

sandtable is a lightweight, pure-Python **mission-design simulator** for autonomy-enabled ground and
air formations. It is a low-fidelity, mission-level counterpart to the Army's Unreal-based
**ProjectGL**: it deliberately drops high-fidelity vehicle dynamics and rendering in favor of
"accurate enough" mission-level models (movement, terrain and mobility, sensing, engagement, command
and control), so it can run thousands of times inside parameter sweeps and Bayesian optimization.

It is the fast inner-loop companion to ProjectGL: the fast tier searches the design space and locates
the decision-relevant regions, and the high-fidelity engine then validates the handful of designs
that matter.

## Project context (VIPR-GS FP6111)

The goal of the wider project is a **human-machine teaming (HMT) virtual prototyping testbed** built
by extending ProjectGL, so the Army can evaluate how warfighters, autonomous ground and air
vehicles, sensors, and cyber/EW elements team up under contested, uncertain mission conditions. The
testbed drives agent-based modeling (ABM), reinforcement learning (RL), deep-learning surrogates, and
human-in-the-loop (HITL) experiments to refine tactics, techniques, and procedures (TTPs),
human-machine interface (HMI) designs, and formation concepts.

- **Program:** VIPR-GS (Virtual Prototyping of Autonomy-Enabled Ground Systems), Focus Area 3:
  Digital Engineering and Virtual Prototyping.
- **Sponsor / prime:** U.S. Army Ground Vehicle Systems Center (GVSC), via the Clemson-led
  Army-Clemson Research Alliance. GMU is a subawardee. Grant FP00006111 / FP6111.
- **Period of performance:** January 2026 through December 2027 (budget covers up to two years; a
  Year 1 demonstration is emphasized).
- **Classification:** all work in this repository is UNCLASSIFIED. Classified mission needs and
  threat models are handled only inside existing Government-accredited enclaves; no classified data
  enters this repository, and no new accreditation is assumed.

### People and roles

| Person | Role | Responsibility |
| --- | --- | --- |
| Jose L. Bricio-Neto | PI (GMU RPRC) | Mission engineering, overall direction |
| Ali Raz | Co-PI (GMU SEOR) | Virtual testbed architecture, system-of-systems |
| Vadim Sokolov | Co-PI (GMU SEOR) | ABM integration, RL algorithm architecture, ML analytics |
| Charles (Chuck) MacDonough | Lead Developer | ProjectGL / CruxGL plugin development |
| Michael Hieb | Contributor | HMI design, multi-domain command |

This repository is the **ABM and learning/surrogate/analytics work** (RL, Bayesian calibration,
deep-learning surrogates with uncertainty quantification, ML pattern-mining) and its integration with
the simulation core. The Unreal/CruxGL simulation core itself is developed elsewhere on the team.

## ProjectGL: what sandtable stands in for

**ProjectGL** (also written "Project GL", where GL stands for *Great Lakes*) is a
Government-furnished, GOTS simulation software framework built on **Unreal Engine**, developed by the
Army's DEVCOM Ground Vehicle Systems Center (GVSC). It ships as a government-managed library of 16
plug-ins (drivable vehicle models, geo-specific terrain, LiDAR, radar sensor models); simulations are
assembled from these plug-ins. It won the U.S. Army 2024 Modeling and Simulation Award. The proposal
and Testbed Design Document (TDD) refer to the **CruxGL simulation core** as its execution core.

The testbed **extends ProjectGL in place** rather than re-platforming it: ground, air, cyber, and EW
models, scenarios, and behaviors are authored as ProjectGL/CruxGL plug-ins and content. Three Unreal
capabilities are load-bearing:

- **Learning Agents:** RL and imitation-learning training and inference for agent behaviors.
- **Mass Entity (ECS):** thousands of concurrent agents at formation scale.
- **Headless / dedicated-server / CLI execution:** large Monte-Carlo design-of-experiments sweeps on
  workstation-class hardware.

Engine note: ProjectGL is built on Unreal Engine, confirmed by *Defense Acquisition* magazine
(Jan-Feb 2026, co-authored by David Gorsich, Chief Scientist at DEVCOM GVSC). An earlier console
mockup that showed Unity is a superseded layout exploration, not the engine; sandtable and the
testbed target Unreal.

## What the testbed answers

Everything traces to **four research objectives** and **five metric families**. When adding
capability, tie it back to these.

**Objectives:** O1 detect success/failure patterns in human-machine collaboration via ML; O2
evaluate HMI designs that optimize cognitive-load distribution; O3 assess direct vs. supervisory
control effectiveness; O4 extend mission-engineering and kill-web analysis.

**Metric families:** TTP Effectiveness (success rate, time to objective, attrition); Coordination
(comm frequency, teamwork graphs, handoff); Human-AI Trust (override rates, trust calibration as
discrimination, not mean trust); Adaptability (re-planning time, recovery); Contested Performance
(impact of EW/cyber on outcomes).

**Design tenets (do not break these):**

- **Engineered ground truth and controllable veridicality.** Every scenario carries a correct answer
  for the trial, and every AI/ABM agent exposes a dial-able error rate, confidence behavior,
  explanation style, and version state. This is what lets ML score detection against *truth* rather
  than mere agreement-with-AI; Objective 1 collapses to correlation-hunting without it.
- **Centerpiece interaction (IV-A x IV-B).** Control modality (direct/mixed/supervisory) crossed with
  comms/EW degradation (a C0-C5 ladder). As comms degrade, the optimum shifts toward on-platform
  autonomy; locating that moving optimum is the single most decision-relevant result.

## Design in one paragraph

The simulator is a **pure function** `run_mission(config, seed) -> metrics`, over
**structure-of-arrays** agent state advanced by a **fixed-timestep** loop (NumPy first, `numba` on
hot spots as needed). Platforms follow the AFSIM-style component model
`Platform{mover, sensors, weapons, processor, comms}`; behaviors are physics-free (cookie-cutter
detection, aspect-sector probability-of-kill, trigger state machines) in the tradition of MANA and
Gaertner (NPS 2013). Optimization is driven by
**[polarisopt](https://github.com/VadimSokolov/polarisopt)** (DOE + BoTorch Bayesian optimization);
the simulator plugs in as a CLI subprocess via the `polarisopt` Simulator/Metric plugin contract (no
fork), mirroring its `taxidemo` example.

### Architecture

sandtable mirrors the full testbed's layered architecture (platform and security, simulation core,
ABM, learning/surrogate/analytics, cyber/EW, mission engineering, HITL/HMI, data and telemetry) in
minimal form. It implements low-fidelity stand-ins for the middle layers; the HITL consoles, the
security and multi-classification regime, and the Unreal simulation core proper live in ProjectGL.
The code maps to the layers as follows.

| Layer | sandtable modules |
| --- | --- |
| Simulation core: fixed-step loop, time, terrain | `sim`, `world`, `scenario`, `seeding` |
| Agent-based modeling: SoA platforms, movement, routing, command | `entities`, `motion`, `planning`, `c2`; optional personality-field movement (`personality`) |
| Sensing and engagement: shared-picture detection, aimed-fire attrition | `sensing`, `engagement`; kill-web state, believed tracks and decoys (`belief`), suppression and finite munitions (`mechanics`), counter-UAS / SHORAD attrition of the recon swarm (`counter_uas`) |
| Cyber / EW: comms degradation, dropped tasking, thinned picture | `comms_ew`; EW-immune command link (fiber / autonomous terminal guidance) via the `ew_immune_link` gate in `c2` |
| Learning, surrogate and analytics: DOE, Bayesian optimization and test-and-evaluation | `runner`, `plugin`, `opt_metrics` (+ polarisopt), Bayesian T&E (`bayes_te`) |
| Data, telemetry and metrics: mission KPIs, cost-weighted exchange, replay traces | `metrics`, `replay` |

### Extensions

Two families of capability sit on top of the core. The **simulation mechanics** are opt-in behind
parameter gates that draw the identical RNG stream when disabled, so the baseline is their degenerate
limit and every prior result is unchanged (proven by an additive-only diff of the generated numbers):

- **Kill web** (`mechanics`, `belief`): suppression, finite munitions, and a believed-track layer
  where fires resolve against a *believed* enemy position that jamming and decoys can corrupt, so
  deception and sustainment become mission effects rather than assumptions.
- **Personality-field movement** (`personality`): ISAAC / EINSTein / MANA-style weighted
  attraction-repulsion movement, where a route emerges from local propensities instead of a scripted
  lane.
- **Drone-war increment** (`counter_uas`, `c2`, `metrics`): an EW-immune command link (`ew_immune_link`,
  standing in for fiber or autonomous terminal guidance) that carries tasking at a fixed latency off
  the C0-C5 ladder, counter-UAS / SHORAD attrition whose per-drone hazard rises with committed swarm
  size (`cuas_rate`, `signature`), and a cost-weighted `cost_exchange` KPI. The first flattens the
  comms-degradation crossover; the second turns the UC-5 swarm response from monotone-in-size into an
  interior optimum, as a mechanism demonstration rather than a modeled air-defense system.

An **analysis layer** reads the mission outcomes without changing them:

- **Bayesian test and evaluation** (`bayes_te`): turns mission success/failure draws into
  Beta-Bernoulli posteriors, decision-chart optimal stopping, and a discounted-prior link that lets
  the fast tier inform the high-fidelity tier's test plan (Ferry's Bayesian Decision Theory
  paradigm for M&S-informed operational testing).

Validation follows a standard verification-and-validation menu (Sargent): reproducibility and
extreme-condition tests, face-validity monotonicity checks, and a Lanchester analytic cross-check as
the aggregate-attrition anchor (still a current benchmark in the combat-modeling literature).

## Scenarios (from TDD Section 11)

1. **Route vs defilade (UC-3)** - a ground formation trades speed against cover on a trafficability
   raster.
2. **Span-of-control x comms degradation (IV-A x IV-B, the centerpiece)** - one operator supervises N
   autonomous assets across control modalities and the C0-C5 comms/EW ladder; as comms degrade, the
   direct-to-supervisory optimum moves.
3. **Sensor swarm under EW (UC-5)** - UAS recon feeds a shared situational-awareness map cueing
   near-blind ground assets under progressive jamming.
4. **Contested belief (UC-7)** - a formation advances against a denser, spoofable, jammed defense
   with the full kill web (suppression, finite munitions, believed tracks, decoys), so deception and
   sustainment become first-order effects rather than assumptions.

## Layout

```
src/sandtable/  simulator package: world, entities, motion, planning, sensing, engagement, c2,
                comms_ew, belief, mechanics, personality, counter_uas, metrics, replay, sim;
                analysis: bayes_te; plus polarisopt runner.py / plugin.py / opt_metrics.py
tools/          make_*_numbers.py produce report/data/*.csv; make_numbers.py / make_figures.py /
                make_diagrams.py turn that CSV into report/gen/*.tex and report/figures/*.pdf
scenarios/      declarative scenario specs (JSON)
studies/        polarisopt study YAMLs (LHS/Morris sweeps + GP/qEI Bayesian optimization)
experiments/    empirical.md lab notebook + results/
tests/          unit + reproducibility + sensitivity tests
report/         academic-paper deliverable (LaTeX, generated figures/tables/numbers)
doc/            proposal, TDD, and console mockup (internal, not tracked)
```

## Environment

```bash
conda activate mgl                # the canonical env for this project (Python 3.12)
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

## Develop

Every command below runs from the repository root, in the `mgl` env. Scripts resolve `report/` and
`scenarios/` relative to the working directory, so running them from a subdirectory silently writes
to the wrong place.

```bash
# full suite: 127 tests, about 2 min
conda run -n mgl python -m pytest tests/ -q
# one file, then one test
conda run -n mgl python -m pytest tests/test_counter_uas.py -q
conda run -n mgl python -m pytest tests/test_counter_uas.py::test_off_is_byte_identical -q
```

Lint config lives in `pyproject.toml` (ruff, line-length 100), but `ruff` is not currently installed
in `mgl`; `pip install ruff` first if you want `ruff check src tests tools` to run.

Regenerating the report is two stages, and the split matters: the producers re-run the simulator and
are slow, the consumers are pure CSV-to-LaTeX and are fast. If you only changed prose or plotting,
run the consumers alone.

```bash
# stage 1, producers: run missions, write report/data/*.csv  (slow; only when the model changed)
conda run -n mgl python tools/make_drone_numbers.py       # drone_fiber_link, drone_cuas_swarm
conda run -n mgl python tools/make_killweb_numbers.py     # suppression_sweep, munitions_sweep, uc7_layers
conda run -n mgl python tools/make_belief_numbers.py      # belief_demo
conda run -n mgl python tools/make_personality_numbers.py # personality_sweep
conda run -n mgl python tools/make_bayes_te_numbers.py    # bayes_te_*
conda run -n mgl python tools/lanchester_check.py         # lanchester (analytic cross-check)

# stage 2, consumers: read report/data/*.csv, write the LaTeX the manuscript \input-s
conda run -n mgl python tools/make_numbers.py    # -> report/gen/numbers.tex, tab_*.tex, results/numbers.txt
conda run -n mgl python tools/make_figures.py    # -> report/figures/*.pdf
conda run -n mgl python tools/make_diagrams.py   # -> architecture, command_model, scenarios figures
```

The centerpiece and UC-3/UC-5 CSVs (`centerpiece_*.csv`, `uc3_frontier.csv`, `uc5_swarm_jam.csv`)
come from the polarisopt studies in `studies/` run on the Hopper cluster, not from a local script.

Compile and pre-flight the manuscript from `report/`:

```bash
cd report
latexmk -pdf -outdir=build -interaction=nonstopmode main.tex   # -> report/build/main.pdf
python3 tools/audit.py                                         # 5 mechanical checks, exit 0 = pass
```

`report/tools/audit.py` checks citation provenance (every `ref.bib` entry carries a `% verified:`
line), AI-writing signs, em-dash absence, that every `\ref{}` in the contribution block resolves, and
a clean compile. Pass `--no-compile` to skip the slow LaTeX check while iterating.

## Conventions

- **No em dashes** in any output (prose, code comments, commit messages). Use commas, parentheses,
  colons, or periods.
- Keep everything in this repository **unclassified**. Never introduce classified content, real
  threat data, or anything that would require accreditation.
- Numbers, figures, and tables in the report are generated by scripts and `\input`-ed, never retyped;
  every reported value traces to a run recorded in `experiments/empirical.md`.
- When engine- or library-specific decisions are still open, surface the choice to the team rather
  than committing silently.

## Doctrine, standards, and references

- **Army doctrine (scenarios trace to these):** FM 3-0, ATP 3-90, JP 3-12.
- **Mission engineering:** MEG 2.0 (Mission Engineering Guide), SysML/LML, kill-web and
  system-of-systems analysis.
- **Background literature:** RAND *One Team, One Fight* (Vols I-II); CRS Robotic Combat Vehicle
  primer; Raz et al. (2024), IEEE Systems Journal, on mission-engineering foundations; Sokolov et al.
  on platoon formation, Bayesian optimization, and deep RL for urban transport.
- **Authoritative internal sources:** the funded proposal and the Testbed Design Document (TDD v0.3),
  both in `doc/`.
