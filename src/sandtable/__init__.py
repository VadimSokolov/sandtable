"""sandtable: Mission-level GL.

A lightweight, pure-Python mission-design simulator for autonomy-enabled ground/air formations
(project FP6111 / VIPR-GS). Low-fidelity, mission-level counterpart to the Unreal-based ProjectGL.

Public entry points:
    run_mission(scenario, seed) -> dict     one deterministic mission (sandtable.sim)
    evaluate(scenario, n_reps, seed) -> dict Monte-Carlo ensemble aggregate (sandtable.sim)
    load_scenario(path) -> Scenario          (sandtable.scenario)
"""
from __future__ import annotations

__version__ = "0.1.0"

from sandtable.scenario import Scenario, load_scenario
from sandtable.sim import evaluate, run_mission

__all__ = ["Scenario", "load_scenario", "run_mission", "evaluate", "__version__"]
