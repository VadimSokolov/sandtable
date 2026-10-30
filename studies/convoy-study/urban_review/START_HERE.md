# Updated Urban Resupply review page

The updated page keeps the original paper colors, handwritten typography, rounded controls, canvas-plus-notes layout and expandable evidence cards. Its main operation viewer uses actual saved Sandtable Python mission traces. It does not execute Python or pytest in the browser.

## Open or share

- Local server: `http://127.0.0.1:8766/urban_resupply.html`.
- Generated artifact: `report/viz/urban_resupply.html`.
- The generated HTML is a single-file deliverable containing 56 complete replay traces, the 90-run settings study, 44 native MathML equations and an embedded archived original prototype.
- It can be opened as a local file in a modern browser with gzip `DecompressionStream` support. Google Fonts is optional; offline fonts fall back locally. No server or CDN is needed for data, playback or equations.

The original downloaded HTML is preserved byte-for-byte in `original.html` and embedded in a sandboxed, independently running archive. Its inventory, dispatch and repair mechanisms differ from the Python convoy. Its historical text is explicitly labeled as such.

## Build

Use Python with `markdown` and `latex2mathml` installed:

```sh
python studies/convoy-study/urban_review/build.py
```

All eleven study groups listed in `build.py` must already have generated `replays.json`; the settings comparison also needs its `results.json`. The English integrated guide is the source for the expanded mathematical documentation. The builder reads saved outputs and never reruns missions or tests.

Source hashes, recording counts, snapshot revision and presentation-input hashes are written to `source_inventory.json` and embedded in the deliverable. The recorded revision is a snapshot identifier, not proof that every input was committed at that revision.

## Controls

1. Pick a study family or retain all 56 options.
2. Pick a scenario, or use a guided starting point.
3. Play/pause, scrub the timeline, step one recorded frame, or inspect the final frame.
4. Select a vehicle from the inspector or click its map symbol. Zoom and follow it; wheel zoom or drag to pan.
5. Open issue cards and the full integrated mathematical guide.
6. Choose a comparison metric and table row; the replay button opens that arm's seed-0 recording.
7. Open the archived original prototype for its five original scenarios and A/B/C dispatch controls.

Map positions and metrics come from recorded frames. There is no interpolation or new engagement/decision simulation in JavaScript. Missing telemetry is labeled as not recorded, rather than invented. Final totals are separated from live frame values. Explicit forced-loss events receive a diagnostic badge.

## Evidence and validation

The unit-test filenames on the issue cards are verification references, not a claim that this page contains animations exported directly from pytest fixtures. The recordings come from study runners using the actual mission loop. The #18 contact-test reference is supporting coverage, not a dedicated #18 acceptance test.

For this page, static/data verification checked: all 56 final-frame cargo balances against saved Python outcomes; entity/frame array dimensions; explicit forced-loss badges; all 90 experiment results; 44 rendered equations; unique HTML IDs; original prototype preservation; and JavaScript syntax. Browser checks cover scenario filtering, lower-loop failure accounting, C5 comparison, equation rendering, playback controls and the archived prototype. These checks do not validate the underlying model against reality.

Adding presentation Python files changes the broad study-source collection used by the older sweep's frozen source digest. Preserve those historical manifests; this HTML build does not alter or re-register the experiments. Re-running a frozen sweep after source drift requires an explicitly documented new experiment snapshot.

No changes to core simulation mechanics are needed for this presentation. Generated HTML is local output; rebuild it after updating the saved traces or guide.

## Simplified two-mode interface

The default view now starts with Routine delivery and Crewed. Six situation buttons drive a constrained recording selector: Routine delivery; Enemy contact; Leader lost; Console unavailable; Urban route choices; Degraded communications. Choose truck control and the context-specific option, then Run selected recording. Run starts playback, not a new Python simulation. Crewed variants are offered only where a corresponding saved run exists. All 56 original recordings remain inside Advanced.

Logistics prototype is a separate top-level mode. It embeds the original JavaScript simulator with only its operation and comparison sections shown. It retains all five disruption scenarios, A/B/C planning, Crewed/Supervised autonomous and the optional small UGV. Switching away removes the embedded instance; returning starts it again. The unmodified full archive remains available below.

Browser verification checked a crewed Herringbone selection maps to recording 27, and that road closure + Conventional + Supervised autonomous + UGV changes the independent prototype's controls and clock label correctly. No AI training or new mission experiments were run for this interface change. Additional matched urban/crew and recovery experiments are proposed explicitly, not presented as completed.
