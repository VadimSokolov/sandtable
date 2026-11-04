"""Atomic JSON persistence and confined job-artifact access."""

from pathlib import Path
import json, os, re, time, uuid
from sandtable.map_builder.values import Invalid
from .serialization import clean


class JsonFiles:
    @staticmethod
    def read(path):
        return json.loads(Path(path).read_text())

    @staticmethod
    def write(path, value):
        path = Path(path)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(clean(value), allow_nan=False))
        os.replace(temporary, path)


class JobRepository:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, key):
        if not re.fullmatch("[a-f0-9]{32}", key):
            raise Invalid("Invalid job identifier.")
        folder = self.root / key
        if not folder.is_dir():
            raise FileNotFoundError("Job not found")
        return folder

    def read(self, key, name):
        return JsonFiles.read(self.folder(key) / name)

    def create(self, request, total):
        key = uuid.uuid4().hex
        folder = self.root / key
        folder.mkdir()
        JsonFiles.write(folder / "request.json", request)
        JsonFiles.write(
            folder / "status.json",
            dict(
                id=key,
                kind=request["kind"],
                state="queued",
                fraction=0,
                completed=0,
                total=total,
                message="Starting isolated Python execution",
                started=time.time(),
            ),
        )
        return key

    def list(self, limit=30):
        rows = []
        for path in sorted(
            self.root.glob("*/status.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            row = JsonFiles.read(path)
            request = JsonFiles.read(path.parent / "request.json")
            row["name"] = request["config"]["name"]
            rows.append(row)
            if len(rows) >= limit:
                break
        return rows

    def study_jobs(self, study_id):
        rows = []
        for path in self.root.glob("*/request.json"):
            request = JsonFiles.read(path)
            if request.get("kind") == "study" and request.get("study", {}).get("id") == study_id:
                rows.append(JsonFiles.read(path.parent / "status.json"))
        return sorted(rows, key=lambda r: r.get("started", 0), reverse=True)

    def partial(self, key):
        folder = self.folder(key)
        for filename in ["result.json", "partial.json"]:
            if (folder / filename).exists():
                return JsonFiles.read(folder / filename)
        return dict(kind="study", runs=[], complete=False)

    def artifact(self, key, index):
        if not re.fullmatch(r"\d{1,3}", index):
            raise Invalid("Invalid run index.")
        return self.read(key, f"run-{int(index):03d}.json")
