"""Curved-route teaching diagnostics; one predetermined seed, no forced kills."""
import copy
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('route_priority_study',STUDY/'red_priority_18/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from sandtable.route import RoutePolyline

waypoints=[[0,1500],[1800,1500],[2400,2100],[3600,2100],[4200,1500],[5750,1500]]
route=RoutePolyline.from_waypoints(waypoints)
base=json.loads((STUDY/'red_priority_18/results.json').read_text())['arms'][1]['scenario']
traces,rows=[],[]
for name in ('no_threat','natural_engagement'):
    cfg=copy.deepcopy(base)
    cfg['params']['route']=waypoints
    cfg['params']['lookahead']=30.
    cfg['params']['study_route_length_m']=route.total_length
    cfg['params']['study_herringbone']['road']='clear polyline; local tangent parking and perpendicular rejoin'
    if name=='no_threat':
        cfg['forces']=[f for f in cfg['forces'] if f['side']==0]
    trace,result,recovery=m.mission(cfg,seed=0)
    assert result['cargo_loaded']==60
    assert len(trace['route'])==len(waypoints)
    max_cross=max(max(f['route_cross']) for f in trace['frames'])
    if name=='no_threat':
        assert result['crew_lost']==0 and result['cargo_lost']==0 and result['crew_steps_at_risk']==0
        assert result['cargo_delivered']==60
    else:
        assert result['convoy_contact_count']>0 and result['study_parked_vehicle_steps']>0
    trace.update(group='#13 — curved route, actual arc-length stationing',
        label=f'{35+len(traces)}. CURVED ROUTE / {name} / full convoy',
        desc='Seed 0; same convoy and route in both new options. Local-tangent experimental Herringbone; perpendicular rejoin; no forced loss. Route is longer and changes exposure geometry, so differences from straight-route runs are not a pure curvature effect.')
    traces.append(trace)
    rows.append(dict(condition=name,scenario=cfg,result=result,max_cross_track_m=max_cross,
                     events=trace['events']))
    print(name,{k:result[k] for k in ('cargo_delivered','cargo_lost','cargo_in_transit','crew_lost','mission_time')},'max cross',max_cross,flush=True)
old=[]
for name in ('baseline_09_14','contact_09_12_14','leader_12_17','console_19','integrated','red_priority_18'):
    old+=json.loads((STUDY/name/'replays.json').read_text())
(HERE/'replays.json').write_text(json.dumps(traces))
(HERE/'results.json').write_text(json.dumps(dict(seed=0,route=waypoints,length_m=route.total_length,runs=rows),indent=2))
m.m.build_viewer(old+traces)
print('36-option viewer generated; route length',route.total_length)
