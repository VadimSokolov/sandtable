"""Slave runner: evaluate() output contract and the inputs.json -> outputs.json CLI."""
from __future__ import annotations

import json

from sandtable import runner


def test_evaluate_returns_output_keys_and_summaries(write_scenario):
    path = write_scenario()
    n_repeats = 3
    res = runner.evaluate(path, params={"route_bias": 1.0}, seed=7, n_repeats=n_repeats)

    for key in runner.OUTPUT_KEYS:
        assert key in res, f"missing averaged KPI {key!r}"
        assert isinstance(res[key], float)

    assert "success_rate" in res
    assert res["success_rate"] == res["success"]   # success_rate is the mean success indicator
    assert "t_obj_success" in res
    assert res["seed"] == 7
    assert res["n_repeats"] == n_repeats
    assert isinstance(res["repeats"], list)
    assert len(res["repeats"]) == n_repeats


def test_evaluate_rejects_nonpositive_repeats(write_scenario):
    path = write_scenario()
    try:
        runner.evaluate(path, params={}, seed=0, n_repeats=0)
    except ValueError:
        pass
    else:
        raise AssertionError("n_repeats < 1 should raise ValueError")


def test_main_reads_inputs_and_writes_outputs(tmp_path, write_scenario):
    scenario_path = write_scenario()
    inputs = tmp_path / "inputs.json"
    outputs = tmp_path / "outputs.json"
    inputs.write_text(
        json.dumps(
            {
                "scenario": scenario_path,
                "params": {"route_bias": 1.0},
                "seed": 1,
                "n_repeats": 2,
            }
        )
    )

    rc = runner.main([str(inputs), str(outputs)])
    assert rc == 0
    assert outputs.exists()

    written = json.loads(outputs.read_text())
    for key in runner.OUTPUT_KEYS:
        assert key in written
    assert written["n_repeats"] == 2
    assert len(written["repeats"]) == 2


def test_main_without_two_args_is_a_usage_error(tmp_path):
    assert runner.main([]) == 2                       # no args
    assert runner.main([str(tmp_path / "only.json")]) == 2   # one arg
