"""Persistence boundaries and real spawned workers for the packaged application."""

from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import json
import pytest
from sandtable.mission_viewer.api import default_config, compile_config
from sandtable.mission_viewer.storage import JobRepository, JsonFiles
from sandtable.mission_viewer.jobs import JobManager
from sandtable.mission_viewer.worker import study_run
from sandtable.map_builder import Invalid


def test_repository_confines_paths_and_retains_existing_results(tmp_path):
    repository = JobRepository(tmp_path)
    for invalid in ["../secret", "a" * 31, "g" * 32, "a" * 32 + "/../"]:
        with pytest.raises(Invalid):
            repository.folder(invalid)
    config = default_config()
    key = repository.create(dict(kind="run", config=config), 1)
    original = dict(answer=42)
    JsonFiles.write(repository.folder(key) / "result.json", original)
    assert repository.partial(key) == original
    with pytest.raises(Invalid):
        repository.artifact(key, "../0")
    JobManager(repository).reconcile()
    assert repository.read(key, "status.json")["state"] == "interrupted"
    assert repository.partial(key) == original


def test_spawned_processes_execute_real_engine_and_keep_seed_identity(tmp_path):
    c = default_config()
    c["map"]["red"] = []
    c["mission"]["duration"] = 10
    arm = dict(name="S1", compiled=compile_config(c))
    with ProcessPoolExecutor(
        max_workers=2, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        futures = [
            pool.submit(study_run, str(tmp_path), arm, seed, i, dict(test=True))
            for i, seed in enumerate([3, 7])
        ]
        rows = [f.result(timeout=30) for f in futures]
    for row, seed in zip(rows, [3, 7]):
        artifact = json.loads((tmp_path / row["file"]).read_text())
        assert artifact["seed"] == artifact["configuration"]["mission"]["seed"] == seed
        assert artifact["frames"][0]["t"] == 0
        assert artifact["frames"][-1]["t"] == 10
        assert artifact["outcome"]["cargo_in_transit"] == 60
