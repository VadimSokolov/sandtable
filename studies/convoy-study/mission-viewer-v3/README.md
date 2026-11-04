# Mission Viewer V3 — inside Sandtable

The map builder, routing, simulation adapters and viewer now run from this repository.
The earlier standalone `convoy-study/mission-viewer-v3` directory is an archive, not a
runtime dependency.

From the Sandtable repository root:

```bash
PYTHONPATH=src .venv/bin/python -m sandtable.mission_viewer --port 8767
```

Open <http://127.0.0.1:8767/>. Alternatively, double-click `run.command` in this
directory. With the package installed, `sandtable-viewer --port 8767` is also available.
The server binds only to the local machine.

The four working tabs remain Build map, Configure mission, Run & inspect, and Compare
runs. Saved scenarios is the existing 12-scenario study, with individual recorded
missions selectable by scenario and seed. A new Run always executes Python; it does
not select an old recording.

## Where things live

| Responsibility | Repository path |
| --- | --- |
| Search strategies and edge costs | `src/sandtable/routing/` |
| Automatic road exposure from declared Red sites | `src/sandtable/routing/exposure.py` |
| Map validation, topology and planning | `src/sandtable/map_builder/` |
| Configuration, simulation and job services | `src/sandtable/mission_viewer/` |
| Browser interface | `src/sandtable/mission_viewer/static/` |
| Saved inputs | This directory's `examples/` and `scenario_library/` |
| Local results, recordings and logs | This directory's ignored `data/` |

See [ARCHITECTURE.md](ARCHITECTURE.md) for interfaces, equations, compatibility and
the explicit experimental simulation adapters.

## Import earlier recordings

From the repository root, run:

```bash
.venv/bin/python tools/import_mission_viewer_v3.py /absolute/path/to/old/mission-viewer-v3
```

This copies only saved inputs/results, checks every file's SHA-256 and refuses
conflicting destination files. It never imports or executes the old Python files.
Historical manifests and result provenance remain unchanged. The generated
`archive-import.json` is a local copy audit; neither it nor `data/` is committed.

Use `--home /absolute/path` when starting the viewer to choose another runtime data
directory. A custom home needs a copy of `scenario_library/` to use Saved scenarios.

## Verification

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_routing_policies.py tests/viewer
```

The routing tests compare both algorithms with exhaustive solutions on small graphs.
Viewer tests include map geometry, exposure overrides, configuration/formation,
physical placement, Herringbone, console transfer, study identities, persistence and
real spawned Python missions. Existing `tests/test_convoy_street_graph.py` continues
to cover the legacy graph interface.
