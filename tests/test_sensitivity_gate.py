"""ACCEPTANCE TEST: the UC-3 "sensitive results" milestone.

The covered route (route_bias = 1.0) must be materially safer and more successful than the open
corridor (route_bias = 0.0). This encodes the doctrinally meaningful speed-vs-attrition tradeoff
the whole testbed is built to expose; if it regresses, that is a real modeling failure, not a
flaky test. Thresholds here are intentionally NOT to be weakened to make the suite pass.
"""
from __future__ import annotations

from sandtable.scenario import load_scenario
from sandtable.sim import evaluate

N_REPS = 40      # modest but stable; ~a couple of seconds total
SEED = 0
SUCCESS_MARGIN = 0.3


def test_covered_route_is_safer_and_more_successful(uc3_path):
    scn = load_scenario(uc3_path)

    open_corridor = evaluate(scn, n_reps=N_REPS, seed=SEED, params={"route_bias": 0.0})
    covered_route = evaluate(scn, n_reps=N_REPS, seed=SEED, params={"route_bias": 1.0})

    s_open = open_corridor["success"]
    s_cover = covered_route["success"]
    b_open = open_corridor["blue_losses"]
    b_cover = covered_route["blue_losses"]

    # Success: the covered route wins by a clear margin.
    assert s_cover - s_open >= SUCCESS_MARGIN, (
        f"success gap too small: covered={s_cover:.3f} open={s_open:.3f} "
        f"(need covered - open >= {SUCCESS_MARGIN})"
    )
    # Attrition: the covered route loses fewer blue platforms.
    assert b_cover < b_open, (
        f"covered route not safer: blue_losses covered={b_cover:.3f} open={b_open:.3f}"
    )
