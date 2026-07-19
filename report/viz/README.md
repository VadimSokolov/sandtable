# SandTable viewers

Two self-contained HTML viewers of recorded missions, used to verify simulator behavior.

- **Full console** (`mission_viewer.html`): tactical replay with terrain, telemetry rail,
  detection-coverage sparkline, and per-unit control-quality shading.
- **Simple player** (`player.html`): a minimal map + play/pause + scrubber.

The `.html` files are **generated** (and git-ignored). Regenerate them deterministically:

```bash
PYTHONPATH=src python tools/make_viz.py      # -> mission_viewer.html + _artifact_body.html
PYTHONPATH=src python tools/make_player.py   # -> player.html + _player_body.html
```

Both record representative runs (the seed nearest the multi-seed mean outcome) step-for-step from
`sandtable.replay.record_trace`, which mirrors `sandtable.sim.run_mission` exactly, so a trace is the
real simulated run. The `_*.html` fragments are body-only versions for publishing as web artifacts.
