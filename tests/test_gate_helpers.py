"""Fixtures for the statistical helpers that decide what this project keeps.

Three instrument defects in this project shared one shape: a convention calibrated on the
first use case, then silently carried into a second where it did not hold.

  1. A jitter-width guard written for one arm's support, applied to an arm whose floor
     clipped it, so two arms differed in mean by 45.7% while the guard called them matched.
  2. An MPE of 0.03, calibrated on [0,1] metrics near 0.5, applied to a rate metric whose
     values sit near 0.05, where the same absolute constant demands a 60% effect.
  3. `paired`'s blocks-won counting `x > 0`, which is agreement only for a positive effect
     and reports the DISAGREEING blocks on a contrast that goes down.

None of the three was caught by a test, because each helper was only ever tested (if at
all) on the case it was written for. This file tests each helper on the case it was NOT
written for: negative effects, rate scales, and clipped supports, against answers computed
by hand. It is the regression barrier for the class, not for the three instances.
"""
from __future__ import annotations

import math
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from ar_table import paired as gate            # noqa: E402  the keep/discard marker
from make_queue_numbers import paired as report  # noqa: E402  the reporting helper
from sandtable.c2 import Operator, backoff_mean  # noqa: E402  the mean-match guard


def blocks(vals: list[float]) -> dict:
    return {"vals": vals}


# --- The sign class: a real effect that goes DOWN ------------------------------------------
#
# Both helpers must treat a -0.20 effect exactly as they treat a +0.20 one. Before the fix,
# `report` returned 0 of 8 for the descending arm, which reads as "no block agreed" when
# every block agreed.

DOWN_HI = [0.10, 0.12, 0.09, 0.11, 0.13, 0.08, 0.10, 0.12]
DOWN_LO = [0.30, 0.32, 0.29, 0.31, 0.33, 0.28, 0.30, 0.32]


def test_report_counts_agreement_not_positives_on_a_negative_effect():
    eff, t, w, n = report(blocks(DOWN_HI), blocks(DOWN_LO))
    assert eff == pytest.approx(-0.20)
    assert t < 0
    assert (w, n) == (8, 8), "every block moved with the effect; the count must say so"


def test_report_is_sign_symmetric():
    """Flipping which arm is `hi` must flip the effect and leave agreement alone."""
    down = report(blocks(DOWN_HI), blocks(DOWN_LO))
    up = report(blocks(DOWN_LO), blocks(DOWN_HI))
    assert down[0] == pytest.approx(-up[0])
    assert down[1] == pytest.approx(-up[1])
    assert down[2] == up[2] == 8


def test_report_counts_a_genuine_disagreement():
    """Three of eight blocks move against a positive effect: the count is five, not eight."""
    hi = [0.30, 0.32, 0.29, 0.31, 0.05, 0.04, 0.06, 0.33]
    lo = [0.10, 0.12, 0.09, 0.11, 0.13, 0.08, 0.10, 0.12]
    _, _, w, n = report(blocks(hi), blocks(lo))
    assert (w, n) == (5, 8)


def test_gate_marks_a_real_decrease_as_a_decrease():
    """The contract's gate has always been two-sided; this pins it so it stays that way."""
    assert gate(DOWN_HI, DOWN_LO, mpe=0.03) == "--"
    assert gate(DOWN_LO, DOWN_HI, mpe=0.03) == "**"


# --- The scale class: an MPE constant carried onto a rate metric ----------------------------
#
# `served_per_step` lives near 0.05. A 20% real effect on it is 0.01 in absolute terms, well
# inside an MPE of 0.03, so the absolute constant silently discards it. This is not a bug in
# `gate`, which does what it is told; it is a bug in telling it 0.03. The fixture pins the
# arithmetic so the convention cannot be misapplied again without a red test.

RATE_HI = [0.060, 0.061, 0.059, 0.062, 0.060, 0.058, 0.061, 0.060]
RATE_LO = [0.050, 0.051, 0.049, 0.052, 0.050, 0.048, 0.051, 0.050]


def test_absolute_mpe_discards_a_large_relative_effect_on_a_rate():
    eff = sum(a - b for a, b in zip(RATE_HI, RATE_LO)) / len(RATE_HI)
    assert eff == pytest.approx(0.010, abs=1e-9)
    assert eff / (sum(RATE_LO) / len(RATE_LO)) == pytest.approx(0.20, abs=0.01)
    assert gate(RATE_HI, RATE_LO, mpe=0.03) == "~", "a 20% effect vanishes under the [0,1] MPE"


def test_relative_mpe_keeps_it():
    """6% of the control arm, the convention adopted after the scale error was found."""
    ref = sum(RATE_LO) / len(RATE_LO)
    assert gate(RATE_HI, RATE_LO, mpe=0.06 * ref) == "**"


def test_the_relative_mpe_still_discards_a_small_relative_effect():
    """The amended convention must not be a rubber stamp: 3% of value stays inside it."""
    near = [b * 1.03 for b in RATE_LO]
    ref = sum(RATE_LO) / len(RATE_LO)
    assert gate(near, RATE_LO, mpe=0.06 * ref) == "~"


def test_six_percent_matches_the_calibration_scale():
    """Where the 0.03 constant was calibrated, [0,1] metrics near 0.5, the two agree.

    This is the arithmetic that fixes the constant at six rather than three: 0.03 of value
    at 0.5 is 6% of it, and `0.03 absolute` and `6% relative` are then the same gate.
    """
    assert 0.03 / 0.5 == pytest.approx(0.06)


# --- The support class: a guard that a floor can defeat ------------------------------------
#
# The jitter arms must differ in spread and not in mean. The first guard compared nominal
# widths, which is only the mean if the arm's support is not clipped. Here the realized mean
# is computed over the actual support, so a clipped arm fails the guard instead of passing.

def arm(interval: int, spread: int) -> float:
    """The realized mean hold of a jitter arm, straight out of the shipped helper.

    Deliberately not a reimplementation. The original defect was a guard that modelled the
    draw instead of asking it, so a fixture that models the draw again would reproduce the
    defect rather than catch it.
    """
    op = Operator.__new__(Operator)
    op.decision_interval = interval
    op.retry_backoff = interval
    op.retry_spread = spread
    op.retry_mode = "fixed"
    return backoff_mean(op)


def test_a_clipped_arm_fails_the_realized_mean_guard():
    """rho = 4, s = 30: the floor bites across the support and drags the mean off its nominal."""
    assert abs(arm(4, 30) - arm(4, 0)) / arm(4, 0) > 0.02


def test_an_unclipped_arm_passes():
    """s = rho - 1 never reaches the floor, which is why the rebuilt design uses it."""
    for rho in (10, 22, 40):
        assert abs(arm(rho, rho - 1) - arm(rho, 0)) / arm(rho, 0) <= 0.02, f"rho={rho}"


def test_the_guard_is_what_rejected_the_original_design():
    """The arms the first jitter battery shipped with, and the shift the width guard missed."""
    shift = abs(arm(4, 30) - arm(4, 0)) / arm(4, 0)
    assert shift > 0.40, f"the rejected arm was off by {100 * shift:.1f}%"


# --- Degenerate inputs the helpers will meet on real logs ----------------------------------

def test_gate_returns_empty_on_ragged_or_missing_arms():
    assert gate([], [1.0], mpe=0.03) == ""
    assert gate([1.0, 2.0], [1.0], mpe=0.03) == ""


def test_zero_variance_is_infinite_t_not_a_zero_division():
    eff, t, w, n = report(blocks([0.5] * 8), blocks([0.2] * 8))
    assert eff == pytest.approx(0.3) and math.isinf(t) and (w, n) == (8, 8)


def test_a_null_contrast_is_neither_significant_nor_agreeing():
    flat = [0.5] * 8
    assert gate(flat, flat, mpe=0.03) == "~"
    _, t, w, _ = report(blocks(flat), blocks(flat))
    assert t == 0.0 and w == 0


# ---------------------------------------------------------------------------
# The denominator rule, made mechanical. `operator_goodput` is serviced over requested, and every
# queue policy worth recommending moves the request count. The rule was known and written down for
# a month before a generator quietly broke it, so it is enforced by the gate rather than by memory.
# ---------------------------------------------------------------------------
import pytest  # noqa: E402

from tools.ar_gate import DenominatorUnchecked
from tools.ar_gate import gate as ar_gate  # noqa: E402


def test_an_inflatable_ratio_cannot_be_gated_without_its_denominator():
    with pytest.raises(DenominatorUnchecked):
        ar_gate("operator_goodput", eff=0.30, t=40.0, won=32, n=32, base=0.50)


def test_a_moved_denominator_makes_the_ratio_unreadable():
    # The real case: admit asks 32 percent more often than refund at twelve assets. Whatever the
    # ratio does, it cannot be read, and the gate says null rather than reporting a smaller effect.
    assert ar_gate("operator_goodput", eff=0.30, t=40.0, won=32, n=32, base=0.50,
                denom=(0.324, 1.0)) is False


def test_a_held_denominator_lets_the_ratio_through():
    assert ar_gate("operator_goodput", eff=0.30, t=40.0, won=32, n=32, base=0.50,
                denom=(0.01, 1.0)) is True


def test_the_rule_is_sign_blind_on_the_denominator():
    # A rate rule suppresses requests and flatters itself by the same arithmetic in reverse.
    assert ar_gate("operator_goodput", eff=0.30, t=40.0, won=32, n=32, base=0.50,
                denom=(-0.324, 1.0)) is False


def test_a_non_ratio_metric_needs_no_denominator():
    assert ar_gate("success", eff=0.30, t=40.0, won=32, n=32, base=0.50) is True


def test_the_three_original_parts_still_bind_on_an_inflatable_metric():
    # A held denominator does not excuse a failing t, block count, or effect size.
    held = {"denom": (0.0, 1.0)}
    assert ar_gate("operator_goodput", 0.30, 1.0, 32, 32, 0.50, **held) is False
    assert ar_gate("operator_goodput", 0.30, 40.0, 15, 32, 0.50, **held) is False
    assert ar_gate("operator_goodput", 0.001, 40.0, 32, 32, 0.50, **held) is False
