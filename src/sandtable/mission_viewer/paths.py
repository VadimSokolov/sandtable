"""Locate repository inputs and runtime output without an external checkout."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class ViewerPaths:
    repository: Path
    home: Path
    assets: Path

    @property
    def data(self):
        return self.home / "data"

    @property
    def library(self):
        return self.home / "scenario_library"

    @classmethod
    def discover(cls, home=None):
        module = Path(__file__).resolve()
        repository = next(
            (p for p in module.parents if (p / "pyproject.toml").exists()), Path.cwd()
        )
        default = repository / "studies/convoy-study/mission-viewer-v3"
        home = Path(home or os.environ.get("SANDTABLE_VIEWER_HOME", default)).resolve()
        return cls(repository, home, module.parent / "static")
