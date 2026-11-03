"""Exploratory one-factor-at-a-time study; fixed map, ten matched seeds."""
import copy
import hashlib
import importlib.util
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from scipy.stats import t
HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
METRICS=('cargo_delivered','cargo_lost','cargo_in_transit','crew_lost','crew_steps_at_risk','blue_losses','success','c2u_serviced_frac','capped_completion_s')

def clean(obj):
    """Undefined auxiliary diagnostics are JSON null, never a zero observation."""
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [clean(v) for v in obj]
    if isinstance(obj,float) and not math.isfinite(obj):return None
    return obj

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def source_hashes():
    files=list((ROOT/'src/sandtable').glob('*.py'))+list(STUDY.rglob('*.py'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}

def design():
    cfg=json.loads((STUDY/'sketch_map/results.json').read_text())['routes'][0]['scenario']
    arms=[]
    for name,key,value in [('baseline',None,None),('speed_8','pace',8.),('speed_12','pace',12.),
            ('gap_6','time_gap',6.),('gap_8','time_gap',8.),('spacing_20','formation_spread',20.),
            ('spacing_60','formation_spread',60.),('comms_C2','comms_level',2),('comms_C5','comms_level',5)]:
        c=copy.deepcopy(cfg)
        if key in ('pace','time_gap'):c['params']['convoy'][key]=value
        elif key:c['params'][key]=value
        arms.append(dict(name=name,changed_parameter=key,value=value,scenario=c))
    return dict(seeds=list(range(10)),display_seed=0,arms=arms,sources=source_hashes(),
        analysis=dict(metrics=METRICS,interval='paired t, 95%, unadjusted exploratory',
            capped_completion_s='mission_time if success else scenario duration',
            scope='OFAT, not interactions; matched seeds do not ensure matched request streams after divergence'),
        chronology='Frozen before this sweep; chosen after earlier exploratory scenario studies, not a blinded preregistration.')

def worker(task):
    arm,seed=task
    spec=importlib.util.spec_from_file_location('sweep_priority',STUDY/'red_priority_18/run.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    sys.path.insert(0,str(STUDY/'urban_16'))
    from telemetry import Observe
    with Observe():trace,result,_=m.mission(arm['scenario'],seed,capture=seed==0)
    assert abs(result['cargo_loaded']-sum(result[k] for k in ('cargo_delivered','cargo_lost','cargo_in_transit')))<1e-8
    result['capped_completion_s']=result['mission_time'] if result['success'] else arm['scenario']['duration']
    for key in METRICS:assert math.isfinite(result[key]),('undefined primary metric',key)
    if seed==0:
        trace.update(group='#15 — settings / 10-seed comparison',label=f"{48+arm['index']}. SETTINGS / {arm['name']} / seed 0",
            desc='One run, seed 0. Compare ten-seed means and uncertainty in the Settings comparison page. Fixed direct route; other factors held at baseline.')
    return dict(arm=arm['name'],seed=seed,result=result),trace if seed==0 else None

def stats(values):
    a=np.asarray(values,dtype=float)
    return dict(mean=float(a.mean()),se=float(a.std(ddof=1)/np.sqrt(len(a))),n=len(a))

def dashboard(data):
    out=ROOT/'report/viz/convoy_sweep.html';out.parent.mkdir(parents=True,exist_ok=True)
    page='''<!doctype html><meta charset="utf-8"><title>#15 Settings comparison</title>
<style>body{background:#101824;color:#e5edf6;font:16px system-ui;margin:32px;max-width:1300px}a{color:#74d8ee}select{padding:10px}table{border-collapse:collapse;width:100%;margin-top:24px}th,td{text-align:left;border-bottom:1px solid #405063;padding:12px}th{color:#8ee0ee}small{color:#b2bdcf}.bar{background:#3c899b;height:8px;margin-top:6px}p{line-height:1.6}</style>
<a href="convoy_study.html">← Mission viewer: all previous options retained</a><h1>#15 — Settings comparison</h1>
<p>9 settings × 10 seeds (0–9). Fixed user-sketch map, direct route, same convoy and enemy layout. Change one factor at a time. Replay options 48–56 show seed 0; the table summarizes all ten runs.</p>
<label>Metric <select id="metric"></select></label><table><thead><tr><th>Setting</th><th>Speed m/s</th><th>Gap s</th><th>Spacing m</th><th>Comms</th><th>Mean ± SE</th><th>Difference vs baseline<br><small>95% paired t interval</small></th></tr></thead><tbody id="rows"></tbody></table>
<p><b>Interpretation:</b> intervals are exploratory and unadjusted for multiple comparisons. No winner is selected. Shared seeds do not ensure identical request streams after trajectories diverge. This design does not estimate interactions.</p>
<p>Spacing changes initial laydown and the following-distance floor. Communications affects C2 requests in this behavior-following scenario. C5 has 16 s one-way latency and 55% drop probability; its nominal 32 s round trip exceeds the configured 20 s patience. These are model settings, not a calibrated human workload model.</p>
<p>Capped completion time uses mission time only on success, and 1800 s on failure. It is a penalty metric, not average arrival time. Exposure is crew-steps (dt = 1 s); no detection or line-of-sight condition is required by that metric.</p><small id="hash"></small>
<script>const D=__DATA__;const labels={cargo_delivered:'Cargo delivered (t)',cargo_lost:'Cargo lost (t)',cargo_in_transit:'Cargo in transit (t)',crew_lost:'Crew lost',crew_steps_at_risk:'Personnel exposure (crew-steps)',blue_losses:'Vehicles lost',success:'Success fraction',c2u_serviced_frac:'C2 accepted service fraction',capped_completion_s:'Capped completion time (s)'};
const select=document.getElementById('metric');for(const k of Object.keys(labels)){let o=document.createElement('option');o.value=k;o.textContent=labels[k];select.append(o)}
function render(){let k=select.value;document.getElementById('rows').innerHTML=D.arms.map(a=>{let p=a.scenario.params,s=D.summary[a.name][k],d=s.paired;return `<tr><td>${a.name}</td><td>${p.convoy.pace}</td><td>${p.convoy.time_gap}</td><td>${p.formation_spread}</td><td>C${p.comms_level}</td><td>${s.mean.toFixed(3)} ± ${s.se.toFixed(3)}</td><td>${d.mean.toFixed(3)} [${d.low.toFixed(3)}, ${d.high.toFixed(3)}]</td></tr>`}).join('')};select.onchange=render;render();document.getElementById('hash').textContent='Design SHA256: '+D.design_hash;</script>'''
    payload=dict(arms=data['arms'],summary=data['summary'],design_hash=data['design_hash'])
    out.write_text(page.replace('__DATA__',json.dumps(payload).replace('</','<\\/')))
    return out

def main():
    candidate=design();path=HERE/'design.json'
    if path.exists():
        frozen=json.loads(path.read_text());assert frozen['hash']==digest(candidate),'Frozen design/source drift; preserve original design and explicitly create a new study.'
    else:
        frozen=dict(hash=digest(candidate),design=candidate);path.write_text(json.dumps(frozen,indent=2))
    arms=candidate['arms']
    for i,a in enumerate(arms):a['index']=i
    # Confirm recording is observational, using the baseline seed before the sweep.
    a=copy.deepcopy(arms[0]);a['index']=0
    r0,_=worker((a,0))
    spec=importlib.util.spec_from_file_location('capture_check',STUDY/'red_priority_18/run.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    sys.path.insert(0,str(STUDY/'urban_16'));from telemetry import Observe
    with Observe():_,r1,_=m.mission(a['scenario'],0,capture=False)
    for key in METRICS[:-1]:assert r0['result'][key]==r1[key],('recording changes result',key)
    runs=[];traces=[]
    (HERE/'progress.jsonl').write_text('')
    with ProcessPoolExecutor(max_workers=2) as pool:
        for row,tr in pool.map(worker,[(a,s) for a in arms for s in candidate['seeds']]):
            runs.append(row)
            with (HERE/'progress.jsonl').open('a') as log:log.write(json.dumps(clean(row),allow_nan=False)+'\n')
            if tr is not None:traces.append(tr)
            if len(runs)%10==0:print(row['arm'],len(runs),'/90',flush=True)
    baseline={r['seed']:r['result'] for r in runs if r['arm']=='baseline'}
    summary={}
    for a in arms:
        rr=[r for r in runs if r['arm']==a['name']];summary[a['name']]={}
        for key in METRICS:
            ss=stats([r['result'][key] for r in rr]);dd=stats([r['result'][key]-baseline[r['seed']][key] for r in rr]);radius=float(t.ppf(.975,9))*dd['se']
            ss['paired']=dict(mean=dd['mean'],low=dd['mean']-radius,high=dd['mean']+radius)
            summary[a['name']][key]=ss
    data=dict(design_hash=frozen['hash'],arms=arms,seeds=candidate['seeds'],summary=summary,runs=runs)
    (HERE/'results.json').write_text(json.dumps(clean(data),indent=2,allow_nan=False))
    (HERE/'replays.json').write_text(json.dumps(clean(traces),allow_nan=False))
    print(dashboard(data),flush=True)

if __name__=='__main__':main()
