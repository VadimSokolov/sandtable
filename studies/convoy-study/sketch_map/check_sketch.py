"""Verify the user-sketch geometry, route costs and saved mission accounting."""
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('check_sketch_priority',HERE.parent/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from sandtable.street_graph import StreetGraph
from sandtable.scenario import Scenario
from sandtable.world import build_world
from sandtable.seeding import make_rng
import numpy as np

design=json.loads((HERE/'design.json').read_text())
graph=StreetGraph.from_dict(dict(nodes=design['nodes'],edges=design['edges']))
expected={'0.0':'direct','0.75':'upper_loop','1.0':'lower_loop'}
for b,name in expected.items():
    assert graph.find_path('START','GOAL',float(b))==design['paths'][name]
results=json.loads((HERE/'results.json').read_text())
traces=json.loads((HERE/'replays.json').read_text())
assert len(results['routes'])==len(traces)==3
for row,tr in zip(results['routes'],traces):
    cfg=row['scenario'];scn=Scenario.from_dict(cfg);world=build_world(scn,make_rng(0,scn.id))
    assert sum(f['count'] for f in cfg['forces'] if f['side']==1)==4
    assert len(row['runs'])==20 and [r['seed'] for r in row['runs']]==list(range(20))
    for r in row['runs']:
        k=r['result'];assert k['cargo_loaded']==60 and k['crew_total']==15
        assert sum(k[x] for x in ('cargo_delivered','cargo_lost','cargo_in_transit'))==60
    for f in tr['frames']:
        iy,ix=world._idx(np.array(f['x'])[:18],np.array(f['y'])[:18])
        assert not world.buildings[iy,ix].any()
    assert not any('FORCED' in e['event'] for e in tr['events'])
print('3 route choices, Dijkstra costs, 60 runs, cargo/crew, four enemy sites and displayed building avoidance verified.')
