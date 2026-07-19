# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: VIPR-GS FP6111 (Human-Machine Teaming Virtual Prototyping Testbed)

This repository holds the George Mason University (GMU) portion of a U.S. Army research
project. The goal is to build a **human-machine teaming (HMT) virtual prototyping testbed**
by extending **ProjectGL** (a Government-furnished simulation framework) so the Army can
evaluate how warfighters, autonomous ground/air vehicles, sensors, and cyber/EW elements
team up under contested, uncertain mission conditions. The testbed drives agent-based
modeling (ABM), reinforcement learning (RL), deep-learning surrogates, and human-in-the-loop
(HITL) experiments to refine tactics, techniques, and procedures (TTPs), human-machine
interface (HMI) designs, and formation concepts.

- **Program:** VIPR-GS (Virtual Prototyping of Autonomy-Enabled Ground Systems), Focus Area 3: Digital Engineering and Virtual Prototyping.
- **Sponsor / prime:** U.S. Army Ground Vehicle Systems Center (GVSC), via the Clemson-led Army-Clemson Research Alliance. GMU is a subawardee. Grant FP00006111 / FP6111.
- **Period of performance:** begins January 2026 (budget covers up to two years, through Dec 2027; the narrative emphasizes a Year 1 demonstration).
- **GMU budget:** $303,886 total.
- **Classification:** all work in this repo is UNCLASSIFIED. Classified mission needs and threat models are handled only inside existing Government-accredited enclaves; no classified data enters this repository, and no new accreditation is assumed.

### People and roles

| Person | Role | Responsibility |
| --- | --- | --- |
| Jose L. Bricio-Neto | PI (GMU RPRC) | Mission engineering, overall direction |
| Ali Raz | Co-PI (GMU SEOR) | Virtual testbed architecture, system-of-systems |
| **Vadim Sokolov** | **Co-PI (GMU SEOR)** | **ABM integration, RL algorithm architecture, ML analytics** |
| Charles (Chuck) MacDonough | Lead Developer | ProjectGL / CruxGL plugin development |
| Michael Hieb | Contributor | HMI design, multi-domain command |

Vadim Sokolov owns this working copy. When prioritizing, his scope is the **ABM layer, the
learning/surrogate/analytics layer (RL, Bayesian calibration, deep-learning surrogates with
uncertainty quantification, ML pattern-mining), and their integration with the simulation
core**. The Unreal/CruxGL simulation core itself is primarily Chuck MacDonough's domain.

## Current repository state (read this first)

This is a **greenfield repository**: it currently contains only planning documents under
`doc/`, no source code, and no build system. Do not expect (or fabricate) build, lint, or
test commands yet. When code lands, update this file with the real commands.

`doc/` contents:

- `Proposal_FP6111_Bricio_Clemson_Army_11-20-2025.pdf`: the funded proposal (objectives, SOW, metrics, schedule, budget, BOM). The authoritative statement of *what* and *why*.
- `TDD_FP6111_HMT_Virtual_Prototyping_Testbed_ProjectGL_v0.3.docx`: Testbed Design Document (v0.3, from collaborators). The authoritative statement of the *architecture, workflows, and outputs*. Section 11 defines the use-case library, experiment manipulations, and measures.
- `mission_eng_console_7.html`: a single-file UI mockup of the Mission Engineering & Experiment Control console (from a collaborator). Useful for the intended console layout and the MEG 2.0 / SysML mission-engineering flow.

> **Simulation engine: Unreal Engine (resolved).** ProjectGL is built on Unreal Engine. This
> is confirmed by an authoritative DoD source: *Defense Acquisition* magazine (Jan-Feb 2026),
> co-authored by David Gorsich, Chief Scientist at DEVCOM GVSC. It states "Project GL is a
> simulation software framework built on top of Unreal Engine" and describes a
> government-managed library of 16 plug-ins (drivable vehicle models, geo-specific terrain,
> LiDAR, radar). This matches the proposal and TDD v0.3 (CruxGL core, Mass Entity ECS, UMG
> consoles, Unreal Learning Agents). The `mission_eng_console_7.html` mockup shows **Unity**
> (DOTS/ECS, Netcode, AFSIM), which contradicts the authoritative sources; treat that mockup
> as a **superseded exploration for layout only**, not for the engine. Do not write Unity code.
> Source: https://www.waru.edu/library/damag/january-febuary2026/engineering-initiatives

## Authoritative technical direction

**ProjectGL** (also written "Project GL", where GL stands for *Great Lakes*) is a
Government-furnished, GOTS simulation software framework built on **Unreal Engine**, developed
by the Army's DEVCOM Ground Vehicle Systems Center (GVSC). It is architected for modularity,
supportability, cost effectiveness, and scalability, and ships as a government-managed library
of 16 plug-ins (for example: drivable vehicle models, geo-specific terrain, LiDAR, and radar
sensor models). Simulations are assembled from these plug-ins. Documented use cases include
crew-station development, virtual experimentation, autonomous simulation, and immersive
visualization. It won the U.S. Army 2024 Modeling & Simulation Award. The proposal and TDD
refer to the **CruxGL simulation core** as the execution core within ProjectGL.

The testbed **extends ProjectGL in place** rather than re-platforming it: ground, air, cyber,
and EW models, scenarios, and agent behaviors are authored as ProjectGL/CruxGL plug-ins and
content, and Government-furnished ProjectGL data and scenarios are reused directly. Three
Unreal capabilities are load-bearing:

- **Learning Agents**: RL and imitation-learning training/inference for agent behaviors.
- **Mass Entity (ECS)**: thousands of concurrent agents at formation scale.
- **Headless / dedicated-server / CLI execution**: large Monte-Carlo design-of-experiments sweeps on workstation-class hardware.

### Layered architecture (from TDD Section 3)

Inputs enter at the bottom; outputs flow up to analysts and stakeholders. Each layer maps to
derived functional requirements (FR-1..FR-12).

| Layer | Role | FRs |
| --- | --- | --- |
| Platform, Security & Multi-Classification | RBAC, audit, two regimes (unclassified dev vs. accredited enclave) | FR-12 |
| Simulation Core (ProjectGL / CruxGL on Unreal) | Physics, vehicle dynamics, sensing/RF, synthetic environments, ECS scheduling, time sync | FR-1, FR-3, FR-11 |
| Agent-Based Modeling (ABM) | Squads, UAS teams, sensor/comm nodes; behavior trees for doctrine + learned policies; logged decisions | FR-1, FR-2 |
| Learning, Surrogate & Analytics | RL + Bayesian policies, deep-learning surrogates with uncertainty, ML/data-mining over logs | FR-2, FR-7, FR-9 |
| Cyber / EW / Information Operations | Emulated C2 network; inject spoofing, jamming, malware to degrade comms/sensing | FR-5 |
| Mission-Engineering & Experiment-Control | SysML/LML scenarios in Innoslate, doctrine traceability, kill-web/SoS, DOE run manager | FR-6, FR-7, FR-11 |
| Human-in-the-Loop (HITL) / HMI | UMG C2 consoles, HOTAS, direct vs. supervisory control, cognitive-load capture | FR-4 |
| Data, Telemetry & Logging | Time-stamped event bus, reproducibility metadata, replay store, metric/feature stores | FR-8, FR-10 |

## What the testbed is trying to answer

Everything traces to **four research objectives** and **five metric families**. When adding
capability, tie it back to these.

**Objectives:** O1 detect success/failure patterns in human-machine collaboration via ML;
O2 evaluate HMI designs that optimize cognitive-load distribution; O3 assess direct vs.
supervisory control effectiveness; O4 extend mission-engineering and kill-web analysis.

**Metric families:** TTP Effectiveness (success rate, time to objective, attrition);
Coordination (comm frequency, teamwork graphs, handoff); Human-AI Trust (override rates,
**trust calibration** as discrimination, not mean trust); Adaptability (re-planning time,
recovery); Contested Performance (impact of EW/cyber on outcomes).

### Load-bearing design tenets (do not break these)

- **Engineered ground truth + controllable veridicality.** Every scenario carries a correct answer for the trial, and every AI/ABM agent exposes a dial-able error rate, confidence behavior, explanation style, and version/patch state. This is what lets ML score detection against *truth* rather than mere agreement-with-AI. Objective 1 collapses to correlation-hunting without it.
- **Centerpiece interaction (IV-A x IV-B).** Control modality (direct/mixed/supervisory) crossed with comms/EW degradation (a C0..C5 ladder). As comms degrade, the optimum shifts toward on-platform autonomy; locating that moving optimum is the single most decision-relevant result. See TDD Section 11 for the failure-mode taxonomy (F0..F5) and the 10-scenario use-case library (UC-1..UC-10).

### Experiment lifecycle (workflows WF-1..WF-8)

Prepare (1-3): scenario/mission definition -> agent/behavior config -> experiment design (DOE).
Execute (4-6): headless batch/Monte-Carlo -> HITL session -> cyber/EW effects injection.
Analyze (7-8): data collection/metrics/ML pattern-mining -> after-action review, design
patterns, TTP/doctrine recommendations. Findings feed back into WF-1/WF-2.

## Implementation stack

No code exists yet. Engine and the core of Vadim's stack are decided; the rest is intended
direction inferred from the proposal and TDD (verify before relying on it):

- **Simulation core & consoles (decided):** Unreal Engine (C++/Blueprints), ProjectGL/CruxGL plug-ins, UMG for HITL UI.
- **RL / imitation learning (decided):** **Unreal Learning Agents** with a **Python bridge** for training; **PyTorch** as the training framework.
- **ABM, surrogates, ML analytics (Vadim's scope, decided):** **Python + PyTorch** (deep-learning surrogates with uncertainty quantification, RL, ML pattern-mining). Bayesian calibration/optimization tooling to be picked, consistent with the team's prior work.
- **Mission engineering:** Innoslate for SysML/LML models with doctrine traceability.
- **Dashboards / console:** web-based (see the HTML mockup for layout only, not the engine).

## Doctrine, standards, and external references

- **Army doctrine (scenarios trace to these):** FM 3-0, ATP 3-90, JP 3-12.
- **Mission engineering:** MEG 2.0 (Mission Engineering Guide), SysML/LML, kill-web / system-of-systems analysis; ME DMM (data meta-model) and M-An viewpoint appear in the console mockup.
- **Background literature (proposal references):** RAND *One Team, One Fight* (Vols I-II); CRS Robotic Combat Vehicle primer; Raz et al. (2024) IEEE Systems Journal on mission-engineering foundations; Sokolov et al. on platoon formation, Bayesian optimization, and deep RL for urban transport.

## Reading the source documents

The design lives in a `.docx` and a `.pdf`. To read the TDD as text:

```bash
textutil -convert txt -stdout "doc/TDD_FP6111_HMT_Virtual_Prototyping_Testbed_ProjectGL_v0.3.docx"
```

Read the proposal PDF with the Read tool's `pages` parameter (it is 18 pages, image-based).
The HTML mockup is a self-contained file; open it in a browser or grep its `layerbar` /
`card` structure to see the console layout.

## Conventions

- **No em dashes** in any output (prose, code comments, commit messages). Use commas, parentheses, colons, or periods. (This is a standing user preference; note the source documents themselves use em dashes freely, so do not copy their punctuation.)
- Keep everything in this repo unclassified. Never introduce classified content, real threat data, or anything that would require accreditation.
- When engine- or library-specific decisions are still open (see the Unity/Unreal discrepancy), surface the choice to the team instead of committing silently.
