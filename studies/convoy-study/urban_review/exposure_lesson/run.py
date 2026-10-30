"""Two real 100-step mission runs with exact, RNG-free exposure accounting.

A huge weapon range and almost-zero positive lethality isolate exposure arithmetic.
These are constructed diagnostics, not representative combat conditions.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
HERE=Path(__file__).resolve().parent
STUDY=HERE.parents[1]
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(STUDY/'leader_12_17'))
spec=importlib.util.spec_from_file_location('exposure_record',STUDY/'leader_12_17/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from sandtable import metrics

def main():
    source=json.loads((STUDY/'leader_12_17/results.json').read_text())['scenarios'];traces=[];rows=[]
    for arm,name,total in [('manned','manned',39),('auto','reduced_crew',15)]:
        cfg=copy.deepcopy(source['Escorts / '+name+' / contact CONTINUE']);cfg['duration']=100.;cfg['params']['convoy'].pop('contact_reaction',None)
        cfg['forces']=[f for f in cfg['forces'] if f['side']==0]+[dict(side=1,ptype='at_team',count=1,spawn=[3000,1500],spawn_spread=0,formation='column')]
        cfg['platform_types']['at_team']['weapon_range']=1e6;cfg['platform_types']['at_team']['pk_base']=1e-15
        ledger=[];original=metrics.accumulate_crew_at_risk
        def audit(ent,acc):
            before=float(acc.sum());original(ent,acc)
            ids=np.flatnonzero(ent.side==0);reds=np.flatnonzero(ent.alive&(ent.side==1)&(ent.weapon_range>0)&(ent.pk_base>0))
            d=np.hypot(ent.x[ids,None]-ent.x[reds][None,:],ent.y[ids,None]-ent.y[reds][None,:])
            z=(d<=ent.weapon_range[reds][None,:]).any(axis=1) if len(reds) else np.zeros(len(ids),bool)
            values=ent.alive[ids].astype(int)*ent.crew[ids]*z
            assert float(values.sum())==float(acc.sum())-before
            ledger.append(dict(step=len(ledger)+1,ids=ids.tolist(),alive=ent.alive[ids].astype(int).tolist(),crew=ent.crew[ids].tolist(),z=z.astype(int).tolist(),contribution=values.tolist(),distance_to_red=d[:,0].tolist(),range_m=1e6,step_total=int(values.sum()),cumulative=float(acc.sum())))
        with patch.object(metrics,'accumulate_crew_at_risk',audit):trace,out=m.record(cfg,seed=0)
        assert len(ledger)==100 and out['crew_steps_at_risk']==total*100 and out['crew_lost']==0
        for f in trace['frames']:f['exposure_audit']=ledger[int(f['t'])-1] if f['t']>=1 else None
        trace.update(group='#14 — exact exposure arithmetic / constructed diagnostic',label=str(57+len(traces))+'. EXPOSURE LESSON / '+arm+' / 100 seconds',seed=0,
            desc='Actual Python mission, seed 0. Deliberately huge Red weapon range (1,000,000 m), pk=1e-15 and 100 s horizon isolate arithmetic. This is not representative combat. Exact per-vehicle exposure contributions are audited against the engine at each step.',source_file=str((HERE/'replays.json').relative_to(ROOT)),study_folder='exposure_lesson',forced_diagnostic=False)
        traces.append(trace);rows.append(dict(arm=arm,result=out,scenario=cfg))
        print(arm,total,'crew × 100 steps =',out['crew_steps_at_risk'],flush=True)
    (HERE/'replays.json').write_text(json.dumps(traces));(HERE/'results.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':main()
