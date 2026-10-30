"""Paired seed-0 street-network mission, without and with building occlusion."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('urban_priority_study',STUDY/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import numpy as np
from sandtable import behavior,sensing
from sandtable.street_graph import StreetGraph
from sandtable.scenario import Scenario
from sandtable.world import build_world
from sandtable.seeding import make_rng

nodes=[dict(id=k,x=x,y=y) for k,x,y in [('A',0,1500),('B',1800,1500),
    ('C',1800,2100),('D',3600,2100),('E',3600,1500),('F',5750,1500),
    ('G',1800,900),('H',3600,900)]]
edges=[dict(u=u,v=v,width=80,speed_mult=1.,exposure=e) for u,v,e in
    [('A','B',.5),('B','C',.2),('C','D',.2),('D','E',.2),('E','F',.5),
     ('B','G',.8),('G','H',.8),('H','E',.8)]]
graph=StreetGraph.from_dict(dict(nodes=nodes,edges=edges))
path=graph.find_path('A','F',route_bias=.5)
route=graph.to_route_polyline(path)
boxes=[[2250,1600,3350,2000],[1950,1000,2600,1400],[2750,1000,3450,1400],
       [600,1650,1550,2000],[3800,1650,4700,2000]]

class Observe:
    def __init__(self):self.bhv=None;self.k=0;self.total_pairs=0;self.blocked=0;self.first=None;self.seen_steps=0
    def __enter__(self):
        original_behavior,original_sensing=behavior.step,sensing.step
        def step(ent,bhv,*args,**kwargs):
            self.bhv=bhv
            bhv.study_urban_telemetry=dict(sensor_pairs=0,blocked_pairs=0,red_detected=0,first_red_detection=self.first)
            return original_behavior(ent,bhv,*args,**kwargs)
        def sense(ent,world,rng,comms=None):
            original_sensing(ent,world,rng,comms)
            distance=np.hypot(ent.x[:,None]-ent.x[None,:],ent.y[:,None]-ent.y[None,:])
            pairs=ent.alive[:,None]&ent.alive[None,:]&(ent.side[:,None]!=ent.side[None,:])&(distance<=ent.sensor_range[:,None])
            clear=world.los(ent.x[:,None],ent.y[:,None],ent.x[None,:],ent.y[None,:])
            blocked=int((pairs&~clear).sum());total=int(pairs.sum())
            seen=int((ent.seen&ent.alive&(ent.side==1)).sum())
            if seen and self.first is None:self.first=self.k+1
            self.total_pairs+=total;self.blocked+=blocked;self.seen_steps+=int(seen>0)
            self.bhv.study_urban_telemetry=dict(sensor_pairs=total,blocked_pairs=blocked,red_detected=seen,first_red_detection=self.first)
            self.k+=1
        self.bp=patch.object(behavior,'step',step);self.sp=patch.object(sensing,'step',sense)
        self.bp.__enter__();self.sp.__enter__();return self
    def __exit__(self,*args):self.sp.__exit__(*args);self.bp.__exit__(*args)

base=json.loads((STUDY/'route_13/results.json').read_text())['runs'][1]['scenario']
traces,rows=[],[]
for arm in ('open_streets','buildings_occlude'):
    cfg=copy.deepcopy(base)
    cfg['params'].update(study_urban=True,street_graph=graph.to_dict(),study_street_path=path,
        route=route.waypoints.tolist(),study_route_length_m=route.total_length,
        buildings=boxes if arm=='buildings_occlude' else [])
    cfg['params']['study_herringbone']['road']='street polyline with building-safe parking / movement guard'
    # Direct, deterministic geometry checks: identical road and sensor conditions.
    scn=Scenario.from_dict(cfg);world=build_world(scn,make_rng(0,scn.id))
    assert bool(world.los(2800.,2100.,2800.,1500.))==(arm=='open_streets')
    assert bool(world.los(2400.,2100.,3300.,2100.))
    with Observe() as observation:
        trace,result,recovery=m.mission(cfg,seed=0)
    if arm=='buildings_occlude':assert observation.blocked>0
    else:assert observation.blocked==0
    for f in trace['frames']:
        ids=[i for i,e in enumerate(trace['entities']) if e['side']==0]
        if world.buildings is not None:
            iy,ix=world._idx(np.array(f['x'])[ids],np.array(f['y'])[ids])
            assert not world.buildings[iy,ix].any(),('vehicle entered building',f['t'])
    trace.update(group='#16 — streets, intersections and building visibility',
        label=f'{37+len(traces)}. URBAN / {arm} / same street route',
        desc='Seed 0, fixed graph path A–B–C–D–E–F. Same convoy, enemies and route. Buildings only differ; core raster LOS gates sensing and engagement. Experimental building-safe Herringbone; no rerouting or collision avoidance.')
    traces.append(trace)
    rows.append(dict(arm=arm,scenario=cfg,result=result,first_red_detection=observation.first,
        sensor_pairs=observation.total_pairs,blocked_pairs=observation.blocked,
        red_seen_steps=observation.seen_steps,events=trace['events']))
    print(arm,'first detection',observation.first,'blocked pairs',observation.blocked,
          {k:result[k] for k in ('cargo_delivered','crew_lost','tp_shots','mission_time')},flush=True)
old=[]
for name in ('baseline_09_14','contact_09_12_14','leader_12_17','console_19','integrated','red_priority_18','route_13'):
    old+=json.loads((STUDY/name/'replays.json').read_text())
(HERE/'replays.json').write_text(json.dumps(traces))
(HERE/'results.json').write_text(json.dumps(dict(seed=0,path=path,length_m=route.total_length,runs=rows),indent=2))
m.m.build_viewer(old+traces)
print('Saved 38-option viewer; graph path:',path)
