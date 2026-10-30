"""User sketch: three route alternatives, four declared enemy locations.

Synthetic dimensions, fixed seed-0 displays, descriptive 20-seed comparisons.
No adaptive routing or claim of a generally best route.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('sketch_priority',STUDY/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(STUDY/'urban_16'))
from telemetry import Observe
import numpy as np
from sandtable.street_graph import StreetGraph
from sandtable.scenario import Scenario
from sandtable.world import build_world
from sandtable.seeding import make_rng

nodes=[dict(id=n,x=x,y=y) for n,x,y in [('START',0,1500),('JUNCTION',1800,1500),
    ('JOIN',4800,1500),('GOAL',5750,1500),('UPPER_W',2100,700),('UPPER_E',4500,700),
    ('LOWER_W',1800,2400),('LOWER_E',4500,2400)]]
edges=[dict(u=u,v=v,width=100,speed_mult=1.,exposure=e) for u,v,e in
    [('START','JUNCTION',.2),('JOIN','GOAL',.2),('JUNCTION','JOIN',.7),
     ('JUNCTION','UPPER_W',.25),('UPPER_W','UPPER_E',.25),('UPPER_E','JOIN',.25),
     ('JUNCTION','LOWER_W',.2),('LOWER_W','LOWER_E',.2),('LOWER_E','JOIN',.2)]]
graph=StreetGraph.from_dict(dict(nodes=nodes,edges=edges))
paths={'direct':['START','JUNCTION','JOIN','GOAL'],
       'upper_loop':['START','JUNCTION','UPPER_W','UPPER_E','JOIN','GOAL'],
       'lower_loop':['START','JUNCTION','LOWER_W','LOWER_E','JOIN','GOAL']}
boxes=[[700,900,1600,1350],[700,1700,1600,2200],
       [2300,950,2850,1300],[3900,950,4500,1300],[3100,1700,3650,2200]]
enemy_locations=[[3050,1100],[3550,1100],[2500,1900],[4100,1900]]
base=json.loads((STUDY/'urban_16/results.json').read_text())['runs'][0]['scenario']
seeds=list(range(20))
scores={}
for name,path in paths.items():
    scores[name]={str(b):sum(graph.edge_cost(graph._get_edge_between(u,v),b) for u,v in zip(path,path[1:])) for b in (0.,.75,1.)}
choices={str(b):graph.find_path('START','GOAL',route_bias=b) for b in (0.,.75,1.)}
(HERE/'design.json').write_text(json.dumps(dict(seeds=seeds,display_seed=0,nodes=nodes,edges=edges,
    buildings=boxes,enemy_locations=enemy_locations,paths=paths,planning_scores=scores,planning_choices=choices,
    assumptions='Dimensions and edge exposure values are illustrative, not calibrated or inferred from combat.'),indent=2))
rows,traces=[],[]
for name,path in paths.items():
    route=graph.to_route_polyline(path)
    cfg=copy.deepcopy(base)
    blue=[f for f in cfg['forces'] if f['side']==0]
    red_type=next(f['ptype'] for f in cfg['forces'] if f['side']==1)
    cfg['forces']=blue+[dict(side=1,ptype=red_type,count=1,spawn=loc,spawn_spread=0,formation='column') for loc in enemy_locations]
    cfg['params'].update(study_map='user_sketch',study_urban=True,street_graph=graph.to_dict(),
        buildings=boxes,route=route.waypoints.tolist(),study_street_path=path,
        study_route_length_m=route.total_length,study_route_choice=name,study_candidate_paths=paths)
    scn=Scenario.from_dict(cfg);world=build_world(scn,make_rng(0,scn.id))
    pts=route.waypoints
    assert world.los(pts[:-1,0],pts[:-1,1],pts[1:,0],pts[1:,1]).all()
    all_runs=[]
    for seed in seeds:
        with Observe() as observer:trace,result,recovery=m.mission(cfg,seed)
        all_runs.append(dict(seed=seed,result=result,first_detection=observer.first,
                             blocked_pair_steps=observer.blocked))
        if seed==0:
            for f in trace['frames']:
                iy,ix=world._idx(np.array(f['x'])[:18],np.array(f['y'])[:18])
                assert not world.buildings[iy,ix].any()
            trace.update(group='#16 — user sketch / three route alternatives',
                label=f'{45+len(traces)}. YOUR SKETCH / {name} / 4 enemies',
                desc='Approximation of user drawing, synthetic metre scale. Four diamonds are declared enemy sites. Fixed route, natural combat, seed 0. Edge exposure scores are illustrative priors, not estimated casualty probabilities; no dynamic replanning.')
            traces.append(trace)
    means={k:float(np.mean([r['result'][k] for r in all_runs])) for k in
        ('cargo_delivered','cargo_lost','cargo_in_transit','crew_lost','crew_steps_at_risk','mission_time','success')}
    rows.append(dict(route=name,path=path,length_m=route.total_length,planning_scores=scores[name],
                     scenario=cfg,n=20,means=means,runs=all_runs))
    print(name,'length',round(route.total_length),'mean delivered',means['cargo_delivered'],
          'mean crew lost',means['crew_lost'],flush=True)
old=[]
for n in ('baseline_09_14','contact_09_12_14','leader_12_17','console_19','integrated','red_priority_18','route_13','urban_16','urban_maps'):
    old+=json.loads((STUDY/n/'replays.json').read_text())
(HERE/'replays.json').write_text(json.dumps(traces))
(HERE/'results.json').write_text(json.dumps(dict(seed_display=0,seeds=seeds,planning_choices=choices,routes=rows),indent=2))
m.m.build_viewer(old+traces)
print('47-option viewer generated. Planning choices:',choices)
