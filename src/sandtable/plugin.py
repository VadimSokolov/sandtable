"""polarisopt simulator plugin: registers the ``mission`` simulator type.

Discovered automatically through the ``polarisopt.simulators`` entry point
declared in this package's ``pyproject.toml`` -- ``pip install`` the package and
``simulator: {type: mission}`` becomes available in any study YAML.

Example study snippet::

    simulator:
      type: mission
      options:
        scenario: scenarios/uc3_route_defilade.json   # the mission to evaluate
        n_repeats: 20        # average this many seeded runs per sample
        base_seed: 42

    parameters:
      inline:
        - { name: route_bias,       file: inputs.json, min: 0.0, max: 1.0 }
        - { name: formation_spread, file: inputs.json, min: 20.0, max: 120.0 }
        - { name: tempo,            file: inputs.json, min: 0.5, max: 1.0 }

The scenario path is resolved to an absolute path in the master's working
directory (run ``polarisopt`` from the repo root), then written into each
sample's ``inputs.json`` so the slave subprocess (``python -m sandtable.runner``) needs
no CWD assumptions. This mirrors the master/slave pattern of a real ProjectGL run,
so the same study works under both the local and the Slurm runner.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any

import numpy as np

from polarisopt.parameters import ParameterSpace
from polarisopt.runners.base import JobSpec
from polarisopt.samples.sample import Sample
from polarisopt.simulator.base import Simulator, SimulatorError, simulator_registry


def _to_native(o: Any) -> Any:
    """json default: coerce numpy scalars (e.g. int64 from `type: int` params) to Python."""
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(f"not JSON serializable: {type(o)!r}")


@simulator_registry.register("mission")
class MissionSimulator(Simulator):
    """Evaluate the sandtable mission simulator for one design sample.

    Options
    -------
    scenario : str
        Path to the scenario JSON (relative to the master's working directory or
        absolute; ``~`` is expanded). Resolved to an absolute path at construction.
    n_repeats : int
        Seeded Monte-Carlo replications averaged per sample (the sim is stochastic;
        averaging tames the noise the surrogate must model).
    base_seed : int
        Per-sample seeds derive deterministically from this and the sample id, so a
        retried sample reproduces exactly and samples never share seed blocks.
    python_executable : str or None
        Interpreter for the slave subprocess. Defaults to :data:`sys.executable`;
        on a cluster point it at the environment that has ``sandtable`` installed (or
        activate that environment via the runner's ``setup_commands``).
    **fixed
        Any design parameter to pin for the whole study (e.g. ``tempo: 1.0``).
        A parameter cannot be both pinned here and searched via ``parameters``.
    """

    INPUT_FILE = "inputs.json"
    OUTPUT_FILE = "outputs.json"

    def __init__(
        self,
        *,
        scenario: str,
        n_repeats: int = 1,
        base_seed: int = 42,
        python_executable: str | None = None,
        **fixed: float,
    ) -> None:
        if n_repeats < 1:
            raise SimulatorError(f"n_repeats must be >= 1, got {n_repeats}")
        scenario_path = Path(scenario).expanduser().resolve()
        if not scenario_path.exists():
            raise SimulatorError(f"scenario file not found: {scenario_path}")
        self.scenario = str(scenario_path)
        self.n_repeats = int(n_repeats)
        self.base_seed = int(base_seed)
        self.python_executable = python_executable or sys.executable
        self.fixed = dict(fixed)

    def prepare(self, sample: Sample, space: ParameterSpace, workspace: Path) -> JobSpec:
        overlap = set(space.names) & set(self.fixed)
        if overlap:
            raise SimulatorError(
                f"parameter(s) {sorted(overlap)} are both searched and pinned in simulator options"
            )
        # Searched values override pinned defaults are forbidden above; merge is safe.
        params = {**self.fixed, **space.values_dict(sample.inputs)}
        # One distinct, reproducible seed block per sample.
        seed = self.base_seed + self.n_repeats * (sample.id or 0)

        workspace.mkdir(parents=True, exist_ok=True)
        input_path = workspace / self.INPUT_FILE
        output_path = workspace / self.OUTPUT_FILE
        input_path.write_text(
            json.dumps(
                {
                    "scenario": self.scenario,
                    "params": params,
                    "seed": seed,
                    "n_repeats": self.n_repeats,
                },
                indent=2,
                default=_to_native,
            )
        )
        cmd = " ".join(
            [
                shlex.quote(self.python_executable),
                "-m",
                "sandtable.runner",
                shlex.quote(str(input_path)),
                shlex.quote(str(output_path)),
            ]
        )
        return JobSpec(
            name=f"mission-sample-{sample.id or 'unsaved'}",
            command=cmd,
            cwd=workspace,
            stdout=workspace / "stdout.log",
            stderr=workspace / "stderr.log",
        )

    def collect_output(self, sample: Sample) -> dict[str, Any]:
        if sample.folder is None:
            raise SimulatorError(f"sample {sample.id} has no folder set")
        output_path = sample.folder / self.OUTPUT_FILE
        if not output_path.exists():
            raise SimulatorError(f"output file missing: {output_path}")
        return dict(json.loads(output_path.read_text()))
