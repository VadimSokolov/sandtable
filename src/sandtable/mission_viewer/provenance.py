"""Physical source and runtime identity recorded alongside new execution results."""

import hashlib, platform, subprocess
import numpy as np
from .paths import ViewerPaths
from .identity import digest


def provenance():
    paths = ViewerPaths.discover()
    source = paths.repository / "src/sandtable"
    files = sorted(source.rglob("*.py")) + [
        p for p in sorted(paths.assets.rglob("*")) if p.is_file()
    ]
    hashes = {
        str(p.relative_to(paths.repository)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files
    }
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=paths.repository, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=paths.repository, text=True
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = "unavailable", None
    return dict(
        repository=str(paths.repository),
        revision=revision,
        working_tree_dirty=dirty,
        source_files=hashes,
        source_digest=digest(hashes),
        python=platform.python_version(),
        numpy=np.__version__,
        adapters=[
            "Deterministic declared formation placement",
            "Flat terrain/road trafficability raster with building LOS",
            "Steering-aware arrival, route rejoin, boundary/building guard",
            "Herringbone only when explicitly selected",
            "Console successor transfer only when explicitly selected",
            "Preserved #18 target selector only when explicitly selected",
        ],
    )
