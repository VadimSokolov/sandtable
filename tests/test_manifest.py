"""Reproducibility manifest and registration hash (Issue #18, Change item 5)."""
from __future__ import annotations

import json

import numpy as np
import pytest

from sandtable import manifest as mf

REG = mf.build_registration(
    "t", {"s": "scenarios/uc3_convoy.json"}, {"a": {"params": {"x": 1.0, "y": [1, 2]}}}, {"f": 1},
    [0, 1, 2], [{"metric": "m", "arm": "a", "reference": "b"}], {"alpha": 0.05})


def test_canonical_form_is_independent_of_key_order_and_numpy_types():
    a = {"b": 1, "a": [1.5, (2, 3)], "c": np.float64(0.1), "d": np.arange(2)}
    b = {"d": [0, 1], "c": 0.1, "a": [1.5, [2, 3]], "b": np.int64(1)}
    assert mf.canonical(a) == mf.canonical(b)
    assert mf.canonical({"a": 1}) == '{"a":1}'


def test_nan_is_rejected():
    with pytest.raises(ValueError):
        mf.canonical({"x": float("nan")})


def test_hash_is_stable_and_changes_with_every_registered_part():
    h = mf.registration_hash(REG)
    assert h == mf.registration_hash(json.loads(json.dumps(REG)))
    for path, value in ((("seeds",), [0, 1]), (("fixed", "f"), 2), (("analysis", "alpha"), 0.1),
                        (("arms", "a", "params", "x"), 2.0), (("comparisons", 0, "metric"), "n"),
                        (("scenarios", "s", "content", "name"), "other")):
        other = json.loads(json.dumps(REG))
        node = other
        for p in path[:-1]:
            node = node[p]
        node[path[-1]] = value
        assert mf.registration_hash(other) != h, path


def test_scenario_formatting_does_not_change_the_hash(tmp_path):
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    p1.write_text('{"x": 1, "y": [1, 2]}')
    p2.write_text('{\n  "y": [1,\n 2],\n"x": 1\n}')
    assert mf.scenario_input(p1)["content"] == mf.scenario_input(p2)["content"]


def test_provenance_status_and_note_are_not_hashed():
    a = mf.make_manifest(REG, "frozen_before_run", "one")
    b = mf.make_manifest(REG, "post_hoc", "two")
    assert a["registration_hash"] == b["registration_hash"]
    assert "source_revision" in a["provenance"] and "registration_hash" not in a["registration"]


def test_status_must_be_known():
    with pytest.raises(ValueError):
        mf.make_manifest(REG, "preregistered")


def test_verify_detects_changed_definitions_and_hand_edits():
    man = mf.make_manifest(REG, "frozen_before_run")
    assert mf.verify_manifest(man, REG)[0]
    changed = json.loads(json.dumps(REG))
    changed["seeds"] = [0, 1]
    ok, why = mf.verify_manifest(man, changed)
    assert not ok and "current definitions" in why
    edited = json.loads(json.dumps(man))
    edited["registration"]["seeds"] = [9]
    ok, why = mf.verify_manifest(edited, REG)
    assert not ok and "hand" in why


def test_the_committed_manifests_match_their_definitions():
    import importlib
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    for name, modname in (("lane_block", "make_lane_block_arms"), ("red_priority", "make_red_priority_arms")):
        mod = importlib.import_module(modname)
        man = json.loads(Path(mod.MANIFEST).read_text())
        ok, why = mf.verify_manifest(man, mod.registration())
        assert ok, (name, why)
    lane = json.loads(Path("doc/manifests/lane_block.manifest.json").read_text())
    post = json.loads(Path("doc/manifests/red_priority.manifest.json").read_text())
    assert lane["status"] == "frozen_before_run" and post["status"] == "post_hoc"


# ---- source hashes (provenance, separate from the configuration hash) ------------

def test_source_hashes_cover_the_simulation_and_listed_analysis_files_only(tmp_path):
    (tmp_path / "src" / "sandtable").mkdir(parents=True)
    (tmp_path / "src" / "sandtable" / "a.py").write_text("x = 1\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "t.py").write_text("y = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("z = 1\n")
    h = mf.source_hashes(["tools/t.py"], tmp_path)
    assert set(h["simulation"]["files"]) == {"src/sandtable/a.py"}            # tests are not covered
    assert set(h["analysis"]["files"]) == {"tools/t.py"}
    assert {"python", "numpy", "scipy"} <= set(h["environment"])
    (tmp_path / "tests" / "test_a.py").write_text("z = 2\n")
    assert mf.source_hashes(["tools/t.py"], tmp_path)["simulation"]["digest"] == h["simulation"]["digest"]


def test_source_verification_sees_uncommitted_edits_and_missing_records(tmp_path):
    (tmp_path / "src" / "sandtable").mkdir(parents=True)
    (tmp_path / "src" / "sandtable" / "a.py").write_text("x = 1\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "t.py").write_text("y = 1\n")
    man = mf.make_manifest(REG, "frozen_before_run", repo=tmp_path, analysis_files=["tools/t.py"])
    assert mf.verify_source(man, ["tools/t.py"], tmp_path)[0] is True
    (tmp_path / "tools" / "t.py").write_text("y = 2\n")                       # analysis edited after freezing
    ok, why, _ = mf.verify_source(man, ["tools/t.py"], tmp_path)
    assert ok is False and "analysis" in why and "tools/t.py" in why
    (tmp_path / "tools" / "t.py").write_text("y = 1\n")
    (tmp_path / "src" / "sandtable" / "a.py").write_text("x = 2\n")           # simulation edited
    ok, why, _ = mf.verify_source(man, ["tools/t.py"], tmp_path)
    assert ok is False and "simulation" in why
    old = mf.make_manifest(REG, "frozen_before_run", repo=tmp_path)           # frozen without source hashes
    assert mf.verify_source(old, ["tools/t.py"], tmp_path)[0] is None


def test_source_hashes_do_not_enter_the_registration_hash(tmp_path):
    (tmp_path / "src" / "sandtable").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "t.py").write_text("y = 1\n")
    a = mf.make_manifest(REG, "frozen_before_run", repo=tmp_path, analysis_files=["tools/t.py"])
    (tmp_path / "tools" / "t.py").write_text("y = 2\n")
    b = mf.make_manifest(REG, "frozen_before_run", repo=tmp_path, analysis_files=["tools/t.py"])
    assert a["registration_hash"] == b["registration_hash"]
    assert a["provenance"]["source_hashes"]["analysis"]["digest"] != b["provenance"]["source_hashes"]["analysis"]["digest"]
