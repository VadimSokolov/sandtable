"""Three synthetic street maps, each paired open/occluded, predetermined seed 0."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('map_priority_study',STUDY/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(STUDY/'urban_16'))
from telemetry import Observe
import numpy as np
from sandtable.street_graph import StreetGraph
from sandtable.scenario import Scenario
from sandtable.world import build_world
from sandtable.seeding import make_rng

def grid(xs,ys,width,margin):
    nodes=[dict(id=f'{i}:{j}',x=x,y=y) for i,x in enumerate(xs) for j,y in enumerate(ys)]
    nodes += [dict(id='START',x=0,y=1500),dict(id='GOAL',x=5750,y=1500)]
    edges=[]
    def edge(u,v,exposure=.2):edges.append(dict(u=u,v=v,width=width,speed_mult=1,exposure=exposure))
    middle=ys.index(1500)
    edge('START',f'0:{middle}');edge(f'{len(xs)-1}:{middle}','GOAL')
    for i in range(len(xs)):
        for j in range(len(ys)):
            if i+1<len(xs):edge(f'{i}:{j}',f'{i+1}:{j}',.95 if j==middle else .1)
            if j+1<len(ys):edge(f'{i}:{j}',f'{i}:{j+1}',.1)
    boxes=[[x0+margin,y0+margin,x1-margin,y1-margin]
           for x0,x1 in zip(xs,xs[1:]) for y0,y1 in zip(ys,ys[1:])]
    return dict(nodes=nodes,edges=edges),boxes

grid_graph,grid_boxes=grid([1200,2200,3200,4200],[700,1500,2300],80,150)
narrow_graph,narrow_boxes=grid([1400,2100,2800,3500,4200],[1000,1500,2000],40,50)
perimeter=dict(nodes=[dict(id=n,x=x,y=y) for n,x,y in
    [('START',0,1500),('J',1500,1500),('NW',1500,2400),('NE',4400,2400),
     ('E',4400,1500),('GOAL',5750,1500),('SW',1500,600),('SE',4400,600),('CENTER',3000,1500)]],
    edges=[dict(u=u,v=v,width=80,speed_mult=1,exposure=e) for u,v,e in
    [('START','J',.2),('J','NW',.1),('NW','NE',.1),('NE','E',.1),('E','GOAL',.2),
     ('J','SW',.3),('SW','SE',.3),('SE','E',.3),('J','CENTER',.95),('CENTER','E',.95)]])
perimeter_boxes=[[1650,750,2800,1350],[3200,750,4250,1350],
                 [1650,1650,2800,2250],[3200,1650,4250,2250]]
catalog=[('city_grid',grid_graph,grid_boxes),('compact_blocks',narrow_graph,narrow_boxes),
         ('perimeter_and_center',perimeter,perimeter_boxes)]

base=json.loads((STUDY/'urban_16/results.json').read_text())['runs'][0]['scenario']
traces,rows=[],[]
for name,graph_data,boxes in catalog:
    graph=StreetGraph.from_dict(graph_data)
    path=graph.find_path('START','GOAL',route_bias=.5)
    assert len(path)>=2
    route=graph.to_route_polyline(path)
    for arm in ('open','buildings'):
        cfg=copy.deepcopy(base)
        cfg['params'].update(street_graph=graph.to_dict(),route=route.waypoints.tolist(),
            study_street_path=path,study_route_length_m=route.total_length,
            buildings=boxes if arm=='buildings' else [],study_map=name)
        scn=Scenario.from_dict(cfg);world=build_world(scn,make_rng(0,scn.id))
        # Every chosen edge must be clear before running the mission.
        points=route.waypoints
        assert world.los(points[:-1,0],points[:-1,1],points[1:,0],points[1:,1]).all()
        with Observe() as observation:trace,result,recovery=m.mission(cfg,seed=0)
        for frame in trace['frames']:
            if world.buildings is not None:
                ids=np.array([i for i,e in enumerate(trace['entities']) if e['side']==0])
                iy,ix=world._idx(np.array(frame['x'])[ids],np.array(frame['y'])[ids])
                assert not world.buildings[iy,ix].any(),(name,arm,frame['t'])
        if arm=='open':assert observation.blocked==0
        trace.update(group=f'#16 — map collection / {name}',
            label=f'{39+len(traces)}. MAP / {name} / {arm}',
            desc='Synthetic map, seed 0. Fixed Dijkstra route selected before combat, same route within open/buildings pair. No forced deaths, dynamic rerouting, lane-capacity model or calibrated urban tactics.')
        traces.append(trace)
        rows.append(dict(map=name,arm=arm,path=path,scenario=cfg,result=result,
            blocked_pair_steps=observation.blocked,first_red_detection=observation.first))
        print(name,arm,'route',round(route.total_length),'delivered',result['cargo_delivered'],
              'blocked pair-steps',observation.blocked,flush=True)
old=[]
for n in ('baseline_09_14','contact_09_12_14','leader_12_17','console_19','integrated','red_priority_18','route_13','urban_16'):
    old+=json.loads((STUDY/n/'replays.json').read_text())
(HERE/'replays.json').write_text(json.dumps(traces))
(HERE/'results.json').write_text(json.dumps(dict(seed=0,runs=rows),indent=2))
(HERE/'maps.json').write_text(json.dumps([dict(name=n,graph=g,buildings=b) for n,g,b in catalog],indent=2))
m.m.build_viewer(old+traces)
print('44-option viewer saved; all previous options retained.')
