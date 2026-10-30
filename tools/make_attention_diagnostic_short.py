#!/usr/bin/env python3
"""Attention diagnostic, short horizon (Issue #19 verification pass, second design).

WHY A SECOND DESIGN. The first attention diagnostic (tools/make_attention_diagnostic.py, 300 s) verified the equation exactly
but its request workload was NOT identical across arms: after about 150 s the convoy enters Blue weapon range of the (disarmed) Red
teams, Blue-on-Red engagement draws begin, tempo depends on quality, and the shared random stream shifts, so waits and served
share differ slightly between arms for a reason that has nothing to do with the attention term. An exploratory check (not
frozen) showed bit-identical workload at 100 s and 140 s. This design therefore uses a 140 s horizon.

STATUS OF THIS DESIGN. It was chosen AFTER the first diagnostic's results were seen, so it is a corrected re-design, not an
independent preregistration. Its own manifest is still frozen before it is run. The first diagnostic and its limitation are kept.

Everything else is as in make_attention_diagnostic.py (same vehicles, crew, route, communications, workload, seeds, spans).
Output: report/viz/attention_diagnostic_short.json (generated; do not commit)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_attention_diagnostic as base  # noqa: E402

base.NAME = "attention_short"
base.BASE = {**base.BASE, "duration": 140.0}
base.OUT = "report/viz/attention_diagnostic_short.json"
base.MANIFEST = "doc/manifests/attention_short.manifest.json"
base.ANALYSIS_FILES = ["tools/make_attention_diagnostic_short.py", "tools/make_attention_diagnostic.py", "tools/local_manifest.py"]

if __name__ == "__main__":
    base.main()
