"""Check each new map pair's graph, route, accounting and building avoidance."""
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('check_map_priority',HERE.parent/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import numpy as np
from sandtable.scenario import Scenario
from sandtable.street_graph import StreetGraph
from sandtable.world import build_world
from sandtable.seeding import make_rng

rows=json.loads((HERE/'results.json').read_text())['runs']
traces=json.loads((HERE/'replays.json').read_text())
assert len(rows)==len(traces)==6
for start in (0,2,4):
    a,b=rows[start:start+2]
    assert a['map']==b['map'] and a['path']==b['path']
    ca,cb=a['scenario']['params'],b['scenario']['params']
    assert ca['route']==cb['route'] and ca['street_graph']==cb['street_graph']
    assert not ca['buildings'] and cb['buildings']
for row,tr in zip(rows,traces):
    scn=Scenario.from_dict(row['scenario']);world=build_world(scn,make_rng(0,scn.id))
    graph=StreetGraph.from_dict(scn.params['street_graph'])
    assert graph.find_path('START','GOAL',route_bias=.5)==row['path']
    r=row['result']
    assert r['cargo_loaded']==60 and r['crew_total']==15
    assert r['cargo_loaded']==sum(r[k] for k in ('cargo_delivered','cargo_lost','cargo_in_transit'))
    for f in tr['frames']:
        if world.buildings is not None:
            iy,ix=world._idx(np.array(f['x'])[:18],np.array(f['y'])[:18])
            assert not world.buildings[iy,ix].any()
    assert not any('FORCED' in e['event'] for e in tr['events'])
print('6 replays verified: matched pairs, graph paths, cargo/crew, no building entry and no forced loss.')
