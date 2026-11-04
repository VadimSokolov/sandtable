"""Local application endpoint orchestration through injected domain services."""

from .api import (
    default_config,
    blank_config,
    import_config,
    formation_preview,
    normalize_map,
    compile_config,
    comparison_design,
)
from .studies import read_definition, describe, verify_definition, STUDY_ID


class ViewerApplication:
    def __init__(self, paths, repository, jobs):
        self.paths = paths
        self.repository = repository
        self.jobs = jobs

    def get(self, path):
        if path == "/api/bootstrap":
            return dict(
                default=default_config(),
                blank=blank_config(),
                engine=str(self.paths.repository),
                limits=dict(max_blue=80, max_red=30, max_runs=60),
                mass_unit="kg",
            )
        if path == "/api/jobs":
            return self.repository.list()
        if path == "/api/library":
            return dict(
                study=describe(read_definition(STUDY_ID, library=self.paths.library)),
                jobs=self.repository.study_jobs(STUDY_ID),
            )
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[:2] == ["api", "jobs"]:
            key = parts[2]
            if len(parts) == 3:
                return self.jobs.status(key)
            if len(parts) == 4 and parts[3] == "partial":
                return self.repository.partial(key)
            if len(parts) == 4 and parts[3] in ("result", "request"):
                return self.repository.read(key, parts[3] + ".json")
            if len(parts) == 5 and parts[3] == "runs":
                return self.repository.artifact(key, parts[4])
        raise FileNotFoundError("Unknown API route")

    def post(self, path, body):
        if path == "/api/formation":
            return formation_preview(body["mission"]), 200
        if path == "/api/exposure":
            return dict(roads=normalize_map(body["map"], True)["roads"]), 200
        if path == "/api/import":
            return dict(config=import_config(body["config"])), 200
        if path == "/api/validate":
            c = compile_config(body["config"])
            return {k: c[k] for k in ["config", "summary", "config_hash"]}, 200
        if path == "/api/compare/validate":
            d = comparison_design(body["config"], body["design"])
            return dict(
                total_runs=d["total_runs"],
                arms=[dict(name=a["name"], summary=a["compiled"]["summary"]) for a in d["arms"]],
                warnings=d["warnings"],
            ), 200
        if path == "/api/library/run":
            d = read_definition(STUDY_ID, library=self.paths.library)
            verify_definition(d)
            return self.jobs.submit(
                dict(kind="study", config=d["scenarios"][0]["configuration"], study=d), 240
            ), 202
        if path in ("/api/run", "/api/compare"):
            compiled = compile_config(body["config"])
            kind = "run" if path == "/api/run" else "comparison"
            request = dict(kind=kind, config=compiled["config"])
            total = 1
            if kind == "comparison":
                d = comparison_design(compiled["config"], body["design"])
                request["design"] = body["design"]
                total = d["total_runs"]
            return self.jobs.submit(request, total), 202
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "cancel":
            return self.jobs.cancel(parts[2]), 200
        raise FileNotFoundError("Unknown API route")
