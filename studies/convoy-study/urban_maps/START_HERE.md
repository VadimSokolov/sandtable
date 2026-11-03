# More street and urban maps

Six new replay options keep the original1–38 intact. All use the same18-vehicle convoy,15 initial crew,60-ton load, natural Red control-first engagement, experimental Herringbone, succession and console-transfer rules. Each map uses seed0, with no forced deaths or seed search.

| Options | Map | Character | Chosen route length |
|---|---|---|---:|
|39 open /40 buildings|city_grid|Rectangular grid,12 internal intersections, alternative street rows|7350m|
|41 open /42 buildings|compact_blocks|Smaller blocks,15 internal intersections, tighter building setbacks|6750m|
|43 open /44 buildings|perimeter_and_center|Upper/lower perimeter roads and a central alternative|7550m|

The route is selected by Dijkstra with `route_bias=0.5` before combat. It is identical within each map's open/buildings pair. No live rerouting occurs. Graph edge widths are descriptive; there is no lane-capacity or full-size vehicle clearance model. The compact map's smaller footprint setbacks affect LOS and available parking space, not a separate traffic simulation.

## What to watch

1. Start with39 then40: same route with and without buildings. The full graph includes unused alternatives and labelled intersections.
2. Compare41 and42 for tighter blocks. Watch blocked sensor pairs and contact holds near corners.
3. Compare43 and44 for perimeter routes around larger blocks.
4. Select a vehicle under Follow vehicle and zoom in. Building-safe parking may reject a side station; the movement guard prevents entering a building but cannot find a detour.

## Saved seed-0 outcome

| Map | Open delivered | Buildings delivered |
|---|---:|---:|
|city_grid|60t|60t|
|compact_blocks|60t|0t|
|perimeter_and_center|60t|25t|

These are demonstrations, not general rankings or uncertainty estimates. Route lengths, road geometry, threat relationships, and building footprints vary between maps. Only open vs buildings within a map holds that map's route and setup fixed. First detection need not change just because later rays are blocked. #14 exposure still ignores LOS.

`maps.json` stores the editable synthetic graph and footprint catalog. `results.json` records exact resolved scenarios, paths, metrics and seed. `replays.json` contains generated traces. None are real city maps or calibrated conflict scenarios.

```bash
python studies/convoy-study/urban_maps/run.py
python studies/convoy-study/urban_maps/check_maps.py
python tools/convoy_study.py build
```

The optional full `python tools/convoy_study.py run-all` pipeline includes these maps after the earlier urban comparison. Generated traces/results remain ignored by Git; code, documentation and the map catalog are versioned.
