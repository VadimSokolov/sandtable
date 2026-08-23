"""Guard for instrument defect 12: `arrived_frac` is censored above `survive_fraction`.

`sim.run_mission` breaks the step loop as soon as enough vehicles are at the objective, so a mission
that succeeds records `arrived_frac` AT the threshold and never above it. The metric is a continuous
mediator on the failing side only. These tests pin that, so the manuscript cannot quote it as a
two-sided mediator without a test failing first.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import evaluate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
EASY = dict(control_mode="supervisory", comms_level=0, n_blue=16, q_auto=0.95)


@pytest.mark.parametrize("survive_fraction", [0.3, 0.5, 0.7])
def test_arrived_frac_is_pinned_at_the_threshold_when_the_mission_succeeds(survive_fraction):
    scn = load_scenario(str(ROOT / "scenarios" / "sc_span_control.json"))
    scn.objective.survive_fraction = survive_fraction
    out = evaluate(scn, n_reps=8, seed=5, params=EASY)
    assert out["success"] == pytest.approx(1.0)
    # Pinned to within one vehicle of the threshold: the loop breaks on the step it is crossed.
    assert out["arrived_frac"] == pytest.approx(survive_fraction, abs=1.0 / EASY["n_blue"] + 1e-9)
