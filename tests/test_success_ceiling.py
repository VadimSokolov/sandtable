"""CR-69: `success` is a censored instrument above twelve assets on the centerpiece scenario.

Guards the claim the instrument ledger makes. Two things have to stay true for that row to be
honest: success really is pinned at exactly one from the saturation span up, and something else
really is still moving there. If either stopped holding, the row would be describing a scenario
this simulator no longer runs.
"""
from __future__ import annotations

import pytest

from sandtable.scenario import load_scenario
from sandtable.sim import evaluate

SAT = 16          # the saturation span reported in the ledger and in `gen/ceiling_numbers.tex`


@pytest.fixture(scope="module")
def sweep():
    scn = load_scenario("scenarios/sc_span_control.json")
    return {n: evaluate(scn, n_reps=12, seed=0, params={"n_blue": n})
            for n in (8, 12, SAT, 24, 32)}


def test_success_is_pinned_at_one_from_the_saturation_span_up(sweep):
    for n in (SAT, 24, 32):
        assert sweep[n]["success"] == pytest.approx(1.0, abs=1e-12), \
            f"success {sweep[n]['success']:.4f} at {n}: the ceiling moved"


def test_success_still_has_room_where_the_paper_reads_it(sweep):
    """Every success contrast in the manuscript is read at eight assets or fewer. If success
    saturated there too, the centerpiece would be unreadable and this is the test that would say
    so."""
    assert sweep[8]["success"] < 0.95, f"success {sweep[8]['success']:.4f} at eight is at ceiling"
    assert sweep[12]["success"] < 1.0                    # twelve is the last span with any room


def test_the_fleet_is_still_paying_different_prices_where_success_cannot_say_so(sweep):
    """The half that makes the censoring a defect rather than a fact about the mission. If loss
    flattened alongside success, the honest reading would be that the mission really is over."""
    lo, hi = sweep[32]["blue_loss_frac"], sweep[SAT]["blue_loss_frac"]
    assert hi > 2.0 * lo, f"loss {hi:.4f} -> {lo:.4f} across the saturated range is not a spread"
    for a, b in ((SAT, 24), (24, 32)):
        assert sweep[b]["blue_loss_frac"] < sweep[a]["blue_loss_frac"]      # and monotone
