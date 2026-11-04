"""Process lifecycle, concurrency limits, cancellation and restart reconciliation."""

import os, subprocess, sys, threading
from sandtable.map_builder.values import Invalid
from .storage import JsonFiles


class JobManager:
    def __init__(self, repository, max_jobs=2):
        self.repository = repository
        self.max_jobs = max_jobs
        self.processes = {}
        self.lock = threading.Lock()

    def submit(self, request, total=1):
        with self.lock:
            if request["kind"] == "study":
                for key, process in self.processes.items():
                    if (
                        process.poll() is None
                        and self.repository.read(key, "request.json")["kind"] == "study"
                    ):
                        return dict(id=key, state="running", reused=True)
            if sum(p.poll() is None for p in self.processes.values()) >= self.max_jobs:
                raise Invalid("Two local jobs are running; wait or cancel one first.")
            key = self.repository.create(request, total)
            folder = self.repository.folder(key)
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            with (folder / "worker.log").open("w") as log:
                self.processes[key] = subprocess.Popen(
                    [sys.executable, "-B", "-m", "sandtable.mission_viewer.worker", str(folder)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
            return dict(id=key, state="queued")

    def status(self, key):
        state = self.repository.read(key, "status.json")
        process = self.processes.get(key)
        if (
            state["state"] in ("queued", "running")
            and process is not None
            and process.poll() is not None
        ):
            state = self.repository.read(key, "status.json")
            if state["state"] in ("queued", "running"):
                state.update(
                    state="failed",
                    message="Worker exited before writing final status; inspect worker.log.",
                )
                JsonFiles.write(self.repository.folder(key) / "status.json", state)
        return state

    def cancel(self, key):
        state = self.status(key)
        if state["state"] in ("queued", "running"):
            (self.repository.folder(key) / "cancel").touch()
        return dict(id=key, state=state["state"], message="Cancellation requested")

    def reconcile(self):
        for path in self.repository.root.glob("*/status.json"):
            state = JsonFiles.read(path)
            if state["state"] in ("queued", "running"):
                state.update(
                    state="interrupted",
                    message="Server restarted during this job. Restore inputs and rerun explicitly.",
                )
                JsonFiles.write(path, state)

    def close(self):
        for key, process in self.processes.items():
            if process.poll() is None:
                self.cancel(key)
