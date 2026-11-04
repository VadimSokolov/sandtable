#!/usr/bin/env python3
"""Repository-local launcher for the packaged map builder and mission viewer."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sandtable.mission_viewer.__main__ import main

if __name__ == "__main__":
    main()
