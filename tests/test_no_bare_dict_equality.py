"""No test may compare two metric dicts with a bare `==`.

The reason is a defect this project has already paid for once. `run_mission` returns a flat dict of
floats, and for most of the project's life every one of those floats equalled itself, so `assert a
== b` was a correct byte-identity check and two dozen tests used it. Then a ratio metric became
honestly undefined in the configurations where its denominator is zero, and NaN does not equal
itself: thirteen identity tests began failing on runs that were in fact bit-identical. The tests
were right to be strict and the metric was right to be NaN. What was wrong was the comparison.

`conftest.same_run` is the identity check that survives an undefined entry: same keys, and every
pair either equal or both NaN. This file is the guard that keeps the bare form from coming back,
because the failure mode is silent at write time and only shows up when some later metric goes
undefined in some later configuration.
"""
from __future__ import annotations

import ast
import pathlib

# Calls whose return value is a metric dict. `_run` and `_mission` are the per-file wrappers this
# suite uses around run_mission; `evaluate` is the ensemble form and returns the same key space.
RUN_CALLS = {"run_mission", "evaluate", "_run", "_mission"}

HERE = pathlib.Path(__file__).parent


def _call_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _metric_names(fn: ast.AST) -> set[str]:
    """Local names bound to a metric dict inside one function body."""
    out: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and _call_name(node.value) in RUN_CALLS:
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
    return out


def _offenders(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text())
    bad: list[str] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = _metric_names(fn)
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assert):
                continue
            cmp_ = node.test
            if not (isinstance(cmp_, ast.Compare) and len(cmp_.ops) == 1
                    and isinstance(cmp_.ops[0], ast.Eq)):
                continue
            for side in (cmp_.left, cmp_.comparators[0]):
                is_metric = (_call_name(side) in RUN_CALLS
                             or (isinstance(side, ast.Name) and side.id in names))
                if is_metric:
                    bad.append(f"{path.name}:{node.lineno}")
                    break
    return bad


def test_no_test_compares_two_metric_dicts_with_bare_equality():
    bad: list[str] = []
    for path in sorted(HERE.glob("test_*.py")):
        bad.extend(_offenders(path))
    assert not bad, ("bare `==` on a metric dict (use conftest.same_run, which is NaN-aware): "
                     + ", ".join(bad))


def test_the_detector_fires_on_a_planted_offender(tmp_path):
    """Negative control. A guard that cannot fail is not a guard."""
    p = tmp_path / "test_planted.py"
    p.write_text("def test_x():\n"
                 "    a = run_mission(s, seed=1)\n"
                 "    b = run_mission(s, seed=1)\n"
                 "    assert a == b\n")
    assert _offenders(p) == ["test_planted.py:4"]


def test_the_detector_passes_the_helper_form(tmp_path):
    p = tmp_path / "test_clean.py"
    p.write_text("def test_x():\n"
                 "    a = run_mission(s, seed=1)\n"
                 "    b = run_mission(s, seed=1)\n"
                 "    assert same_run(a, b)\n"
                 "    assert a['served_per_step'] == b['served_per_step']\n")
    assert _offenders(p) == []


def test_same_run_is_nan_aware_and_still_strict():
    from conftest import same_run

    nan = float("nan")
    assert same_run({"a": 1.0, "b": nan}, {"a": 1.0, "b": nan})    # both undefined: identical
    assert not same_run({"a": 1.0, "b": nan}, {"a": 1.0, "b": 0.0})  # one defined: not identical
    assert not same_run({"a": 1.0}, {"a": 1.0, "b": nan})            # key sets must match
    assert not same_run({"a": 1.0, "b": 2.0}, {"a": 1.0, "b": 2.5})  # ordinary difference still caught
