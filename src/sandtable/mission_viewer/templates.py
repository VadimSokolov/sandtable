"""Fresh copies of packaged editor templates; no machine-specific paths."""

import json
from pathlib import Path


def default_config():
    return json.loads((Path(__file__).parent / "static/templates/your-sketch.json").read_text())


def blank_config():
    c = default_config()
    c["name"] = "Blank map"
    c["map"].update(
        nodes=[],
        roads=[],
        buildings=[],
        red=[],
        start=[100, 1500],
        goal=[5750, 1500],
        route_mode="auto",
        manual_path=[],
    )
    return c
