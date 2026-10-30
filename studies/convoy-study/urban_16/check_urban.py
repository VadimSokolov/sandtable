"""Verify recorded urban visibility and motion-guard behavior."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('urban_check_study',STUDY/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import numpy as np
from sandtable import behavior,planning,motion
from sandtable.scenario import Scenario,build_entities
from sandtable.seeding import make_rng
from sandtable.world import build_world
from herringbone import Herringbone

data=json.loads((HERE/'results.json').read_text())
traces=json.loads((HERE/'replays.json').read_text())
for row,tr in zip(data['runs'],traces):
    scn=Scenario.from_dict(row['scenario']);world=build_world(scn,make_rng(0,scn.id))
    assert tr['street_graph'] and tr['route']==row['scenario']['params']['route']
    r=row['result'];assert r['cargo_loaded']==sum(r[k] for k in ('cargo_delivered','cargo_lost','cargo_in_transit'))
    for f in tr['frames']:
        ids=np.array([i for i,e in enumerate(tr['entities']) if e['side']==0])
        if world.buildings is not None:
            iy,ix=world._idx(np.array(f['x'])[ids],np.array(f['y'])[ids])
            assert not world.buildings[iy,ix].any()
    assert not any('FORCED' in e['event'] for e in tr['events'])
assert data['runs'][0]['blocked_pairs']==0
assert data['runs'][1]['blocked_pairs']>0
assert data['runs'][0]['scenario']['params']['street_graph']==data['runs'][1]['scenario']['params']['street_graph']

# Deliberately propose an invalid move: the guard must prevent building entry.
scn=Scenario.from_dict(data['runs'][1]['scenario'])
rng=make_rng(0,scn.id);world=build_world(scn,rng);ent=build_entities(scn,rng)
bhv=behavior.build_behavior(scn,ent)
old=(ent.x[0],ent.y[0])
def bad_move(ent,*args,**kwargs):ent.x[0]=2800;ent.y[0]=1800;ent.speed[0]=12
with patch.object(planning,'step',lambda *a,**kw:None),patch.object(motion,'step',bad_move):
    with Herringbone() as adapter:
        planning.step(ent,world,scn,0,bhv=bhv)
        motion.step(ent,world,1.,1.)
        assert (ent.x[0],ent.y[0])==old and ent.speed[0]==0
        assert adapter.blocked_moves==1
print('Graph, LOS contrast, cargo, recorded building avoidance, and forced invalid-move rejection pass.')
