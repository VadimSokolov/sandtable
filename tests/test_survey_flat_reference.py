"""The guard the ledger promises for instrument defect 15.

A contrast against a reference the treatment cannot move is a level wearing a difference. The
three-price comparison in the `trust` battery was exactly that: an operator checking every answer
catches every wrong one by construction, so its automation error rate and its harm channel were both
inert and its cells came back byte-identical. Nothing in the numbers said so. These tests make
`ar_survey` say so, and make sure it stays quiet when the reference genuinely moves.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from ar_survey import survey  # noqa: E402

SEC = "T1 a reference that cannot move"


def _log(tmp_path, ref_vals, arm_vals) -> pathlib.Path:
    """One section, two arms, two sweep points, written in the battery's own line format."""
    lines = [f"### {SEC} (success)"]
    for pt in ("4", "8"):
        lines.append(f"AR_ROW arm=ref n_blue={pt} mean=0.5 vals={','.join(ref_vals[pt])}")
        lines.append(f"AR_ROW arm=trt n_blue={pt} mean=0.5 vals={','.join(arm_vals[pt])}")
    lines.append("AR_META scenario=x metric=success blocks=4 reps=8")
    p = tmp_path / "st-fake-1.out"
    p.write_text("\n".join(lines) + "\n")
    return p


def test_a_reference_identical_across_the_sweep_is_announced(tmp_path, capsys):
    flat = {"4": ["0.50", "0.60", "0.40", "0.50"], "8": ["0.50", "0.60", "0.40", "0.50"]}
    moves = {"4": ["0.70", "0.80", "0.60", "0.70"], "8": ["0.30", "0.40", "0.20", "0.30"]}
    survey(str(_log(tmp_path, flat, moves)), SEC, "success", ref="ref")
    assert "FLAT REFERENCE" in capsys.readouterr().out


def test_a_reference_that_moves_is_not_announced(tmp_path, capsys):
    moves_a = {"4": ["0.50", "0.60", "0.40", "0.50"], "8": ["0.51", "0.60", "0.40", "0.50"]}
    moves_b = {"4": ["0.70", "0.80", "0.60", "0.70"], "8": ["0.30", "0.40", "0.20", "0.30"]}
    survey(str(_log(tmp_path, moves_a, moves_b)), SEC, "success", ref="ref")
    assert "FLAT REFERENCE" not in capsys.readouterr().out


def test_the_warning_reaches_stderr_when_the_caller_asked_for_quiet(tmp_path, capsys):
    """The number scripts all run quiet, so a warning that only prints on stdout is a warning that
    never fires where it is most needed."""
    flat = {"4": ["0.50", "0.60", "0.40", "0.50"], "8": ["0.50", "0.60", "0.40", "0.50"]}
    moves = {"4": ["0.70", "0.80", "0.60", "0.70"], "8": ["0.30", "0.40", "0.20", "0.30"]}
    survey(str(_log(tmp_path, flat, moves)), SEC, "success", ref="ref", quiet=True)
    cap = capsys.readouterr()
    assert "FLAT REFERENCE" in cap.err and cap.out == ""


def test_a_single_point_sweep_cannot_be_judged_and_says_nothing(tmp_path, capsys):
    """One sweep point is not evidence of flatness, and a guard that cries wolf gets switched off."""
    p = tmp_path / "st-fake-2.out"
    p.write_text(f"### {SEC} (success)\n"
                 "AR_ROW arm=ref n_blue=8 mean=0.5 vals=0.5,0.6,0.4,0.5\n"
                 "AR_ROW arm=trt n_blue=8 mean=0.7 vals=0.7,0.8,0.6,0.7\n")
    survey(str(p), SEC, "success", ref="ref")
    assert "FLAT REFERENCE" not in capsys.readouterr().out


def test_the_real_battery_that_motivated_the_guard_still_trips_it():
    """Regression against the landed log, so the guard cannot be silently narrowed later."""
    log = pathlib.Path(__file__).resolve().parent.parent / "report/data/queue/st-trust-9450073.out"
    if not log.exists():
        pytest.skip("battery log not present in this checkout")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        survey("st-trust-9450073.out", "S5 three prices for a wrong answer, one grid",
               "success", ref="reflR100")
    assert "FLAT REFERENCE" in buf.getvalue()


def test_a_cell_containing_an_undefined_value_is_refused_rather_than_scored(tmp_path, capsys):
    """NaN compares false against every threshold, so a censored cell would quietly come back
    "inconclusive", which is a verdict rather than a refusal."""
    p = tmp_path / "st-fake-3.out"
    p.write_text(f"### {SEC} (answer_step_ratio)\n"
                 "AR_ROW arm=ref n_blue=4 mean=0.5 vals=0.5,0.6,0.4,0.5\n"
                 "AR_ROW arm=ref n_blue=8 mean=0.5 vals=0.6,0.6,0.4,0.5\n"
                 "AR_ROW arm=trt n_blue=4 mean=0.7 vals=0.7,0.8,0.6,0.7\n"
                 "AR_ROW arm=trt n_blue=8 mean=nan vals=0.7,nan,0.6,0.7\n")
    survey(str(p), SEC, "answer_step_ratio", ref="ref")
    out = capsys.readouterr().out
    assert "CENSORED" in out and "trt@8" in out


def test_no_censoring_warning_when_every_cell_is_defined(tmp_path, capsys):
    p = tmp_path / "st-fake-4.out"
    p.write_text(f"### {SEC} (answer_step_ratio)\n"
                 "AR_ROW arm=ref n_blue=4 mean=0.5 vals=0.5,0.6,0.4,0.5\n"
                 "AR_ROW arm=trt n_blue=4 mean=0.7 vals=0.7,0.8,0.6,0.7\n")
    survey(str(p), SEC, "answer_step_ratio", ref="ref")
    assert "CENSORED" not in capsys.readouterr().out


def test_a_reference_at_exactly_zero_is_announced(tmp_path, capsys):
    """The mirror image of the flat reference. For any metric outside RATE_METRICS the margin is a
    fraction of the reference level, so a reference of zero makes every difference material by
    construction and no equivalence declarable."""
    p = tmp_path / "st-fake-5.out"
    p.write_text(f"### {SEC} (starved_frac)\n"
                 "AR_ROW arm=ref n_blue=4 mean=0.0 vals=0.0,0.0,0.0,0.0\n"
                 "AR_ROW arm=ref n_blue=8 mean=0.1 vals=0.1,0.1,0.1,0.1\n"
                 "AR_ROW arm=trt n_blue=4 mean=0.2 vals=0.2,0.3,0.1,0.2\n"
                 "AR_ROW arm=trt n_blue=8 mean=0.3 vals=0.3,0.4,0.2,0.3\n")
    survey(str(p), SEC, "starved_frac", ref="ref")
    out = capsys.readouterr().out
    assert "ZERO-BASE REFERENCE" in out and "4" in out


def test_a_rate_metric_is_exempt_because_its_margin_is_absolute(tmp_path, capsys):
    p = tmp_path / "st-fake-6.out"
    p.write_text(f"### {SEC} (served_per_step)\n"
                 "AR_ROW arm=ref n_blue=4 mean=0.0 vals=0.0,0.0,0.0,0.0\n"
                 "AR_ROW arm=ref n_blue=8 mean=0.1 vals=0.1,0.1,0.1,0.1\n"
                 "AR_ROW arm=trt n_blue=4 mean=0.2 vals=0.2,0.3,0.1,0.2\n"
                 "AR_ROW arm=trt n_blue=8 mean=0.3 vals=0.3,0.4,0.2,0.3\n")
    survey(str(p), SEC, "served_per_step", ref="ref")
    assert "ZERO-BASE REFERENCE" not in capsys.readouterr().out
