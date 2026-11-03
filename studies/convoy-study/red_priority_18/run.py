"""Natural combat: nearest vs control-first, with leadership/console recovery.

Frozen 20 seeds (0..19), identical scenario inputs, no forced deaths or kill draws.
Exact priority and engagement sources copied from the existing local #18 branch.
Only the two seed-0 missions are displayed. No seed search or scenario tuning.
"""
import copy
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('study_consoles',STUDY/'console_19/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from sandtable import c2,engagement

spec=importlib.util.spec_from_file_location('study_target_priority',HERE/'branch_sources/target_priority.py')
tp=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tp;spec.loader.exec_module(tp)
branch_eng=types.ModuleType('study_branch_engagement')
branch_eng.target_priority=tp
source=(HERE/'branch_sources/engagement.py').read_text()
# Import shim only; the mechanics/eligibility/kill calculation remain unchanged.
source=source.replace('from sandtable import mechanics, target_priority','from sandtable import mechanics')
exec(compile(source,str(HERE/'branch_sources/engagement.py'),'exec'),branch_eng.__dict__)

class NaturalRecovery:
    """Transfers the existing console to a crewed successor after 20 steps.

    Tracks all three consoles and repeated host losses; never kills an entity.
    Existing queue reservations, pending answers and fallback waits are retained.
    """
    def __init__(self):
        self.op=None;self.events=[];self.episodes={};self.tick=0
        self.leader_restored=self.console_restored=self.first_new_service=None
    def after_behavior(self,k,ent,bhv):
        for c,e in self.episodes.items():
            if e['leader'] is None:
                h=int(bhv.ll_head[c])
                if h>=0 and ent.alive[h] and ent.crew[h]>0:
                    e['leader']=k
                    self.events.append(dict(t=k,event='LEADER_RESTORED',console=c,host=h))
                    if c==0:self.leader_restored=k
    def snapshot(self,ent):
        if self.op is None:
            return dict(rule='natural / transfer_all_successors',hosts=[],available=[],serviced=[],abandon=[],
                leader_restored=None,console_restored=None,first_new_service=None)
        u=self.op.units
        return dict(rule='natural / transfer_all_successors',hosts=u.host.tolist(),available=ent.alive[u.host].tolist(),
            serviced=u.serviced.tolist(),abandon=u.abandon_console.tolist(),
            leader_restored=self.leader_restored,console_restored=self.console_restored,
            first_new_service=self.first_new_service)
    def __enter__(self):
        original=c2.step
        def step(ent,op,comms,scn,k,rng,world=None,bhv=None):
            self.op=op;self.tick=k;u=op.units
            for c,h in enumerate(u.host):
                episode=self.episodes.get(c)
                if not ent.alive[h] and (episode is None or episode['host']!=int(h) or episode['transfer'] is not None):
                    episode=dict(host=int(h),loss=k,leader=None,transfer=None,first_service=None)
                    self.episodes[c]=episode
                    self.events.append(dict(t=k,event='NATURAL_CONSOLE_HOST_LOSS_OBSERVED',console=c,host=int(h)))
                    if c==0:self.leader_restored=self.console_restored=self.first_new_service=None
                if episode and episode['leader'] is not None and episode['transfer'] is None and k>=episode['leader']+20:
                    successor=int(bhv.ll_head[c])
                    if successor>=0 and ent.alive[successor] and ent.crew[successor]>0:
                        u.host[c]=successor;op.crew_free_at[c]=max(float(k),op.crew_free_at[c])
                        episode['transfer']=k;episode['host']=successor
                        self.events.append(dict(t=k,event='CONSOLE_TRANSFERRED',console=c,host=successor))
                        if c==0:self.console_restored=k
            before=u.serviced.copy()
            original(ent,op,comms,scn,k,rng,world,bhv)
            for c,e in self.episodes.items():
                if e['transfer'] is not None and e['first_service'] is None and u.serviced[c]>before[c]:
                    e['first_service']=k
                    self.events.append(dict(t=k,event='FIRST_NEW_SERVICE_ACCEPTED',console=c))
                    if c==0:self.first_new_service=k
        self.patch=patch.object(c2,'step',step);self.patch.__enter__();return self
    def __exit__(self,*args):return self.patch.__exit__(*args)

class Priority:
    def __init__(self,cfg):self.cfg=cfg;self.prio=None;self.tick=0;self.events=[];self.deaths=set()
    def __enter__(self):
        def step(ent,world,dt,rng,**kwargs):
            if self.prio is None:
                from sandtable.scenario import Scenario
                self.prio=tp.build_target_priority(Scenario.from_dict(self.cfg),ent)
            alive=ent.alive.copy()
            tp.begin_step(ent,self.prio,self.tick)
            branch_eng.step(ent,world,dt,rng,prio=self.prio,**kwargs)
            tp.end_step(ent,self.prio)
            for i in (alive & ~ent.alive).nonzero()[0]:
                if ent.side[i]==0:self.deaths.add(int(i))
                self.events.append(dict(t=self.tick,event='NATURAL_COMBAT_DESTRUCTION',entity=int(i),
                    side=int(ent.side[i]),role=int(ent.convoy_role[i])))
            self.tick+=1
        self.patch=patch.object(engagement,'step',step);self.patch.__enter__();return self
    def __exit__(self,*args):return self.patch.__exit__(*args)

def mission(cfg,seed,priority=True,capture=True):
    recovery=NaturalRecovery()
    if priority:
        p=Priority(cfg)
        with p:trace,result=m.record(cfg,seed=seed,herringbone=True,c2_bridge=recovery,capture=capture)
        assert result['blue_losses']==len(p.deaths), 'A Blue death was not recorded in combat'
        result.update(tp.metrics(p.prio))
        trace['events']+=p.events
    else:trace,result=m.record(cfg,seed=seed,herringbone=True,c2_bridge=recovery,capture=capture)
    trace['events']=sorted(trace['events']+recovery.events,key=lambda e:e['t'])
    assert not any('FORCED' in e['event'] or 'DIAGNOSTIC_LOSS' in e['event'] for e in trace['events'])
    assert result['cargo_loaded']==60 and result['crew_total']==15
    return trace,result,recovery

def main():
    cfg=copy.deepcopy(json.loads((STUDY/'integrated/results.json').read_text())['scenario'])
    cfg['params']['study_console_transfer']=dict(rule='transfer_all_successors',delay_s=20,forced_loss=False)
    seeds=list(range(20))
    # Write design before experiments; no ranking, tuning or representative-seed search.
    (HERE/'design.json').write_text(json.dumps(dict(seeds=seeds,scenario=cfg,arms=['nearest','control_first'],
        display_seed=0,scope='priority only; no ambush fire-control template or lane blocking'),indent=2))
    rows,traces=[],[]
    for arm,order in [('nearest',[]),('control_first',['control'])]:
        c=copy.deepcopy(cfg);c['params']['target_priority']=dict(order=order)
        runs=[]
        for seed in seeds:
            tr,r,rec=mission(c,seed)
            runs.append(dict(seed=seed,result=r,events=tr['events']))
            if seed==0:
                if arm=='nearest':
                    _,original,_=mission(c,seed,priority=False)
                    for key in ('cargo_delivered','cargo_lost','crew_lost','crew_steps_at_risk','blue_losses','red_losses'):
                        assert original[key]==r[key],('off-path mismatch',key)
                tr.update(group='#18 — natural engagement, no forced leader loss',
                    label=f'{33+len(traces)}. NATURAL / {arm} / full integrated mission',
                    desc='Seed 0, selected before runs. No forced deaths. Control class uses ground-truth role among detected, in-range, LOS-eligible targets; fallback nearest. No wreck blocking or ambush-template timing. Console transfer applies to all groups, with 20-step delay.')
                tr['outcome']=r
                traces.append(tr)
        loss_runs=sum(any(e['event']=='NATURAL_CONSOLE_HOST_LOSS_OBSERVED' for e in r['events']) for r in runs)
        transferred=sum(any(e['event']=='CONSOLE_TRANSFERRED' for e in r['events']) for r in runs)
        summary={k:statistics.mean(r['result'][k] for r in runs) for k in
            ('cargo_delivered','cargo_lost','cargo_in_transit','crew_lost','crew_steps_at_risk','blue_losses','tp_shots','tp_priority_shots')}
        rows.append(dict(arm=arm,scenario=c,n=20,host_loss_runs=loss_runs,transfer_runs=transferred,means=summary,runs=runs))
        print(arm,'host-loss runs',loss_runs,'transfers',transferred,'mean delivered',summary['cargo_delivered'],flush=True)
    old=[]
    for name in ('baseline_09_14','contact_09_12_14','leader_12_17','console_19','integrated'):
        old+=json.loads((STUDY/name/'replays.json').read_text())
    (HERE/'replays.json').write_text(json.dumps(traces))
    provenance={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'branch_sources').glob('*.py')}
    revision=json.loads((HERE/'branch_sources/provenance.json').read_text())['revision']
    (HERE/'results.json').write_text(json.dumps(dict(seeds=seeds,branch_revision=revision,branch_source_sha256=provenance,arms=rows),indent=2))
    m.build_viewer(old+traces)
    print('Saved 34-option viewer. Seed-0 events:')
    for tr in traces:
        print(tr['label'],[e for e in tr['events'] if e['event'] in ('NATURAL_CONSOLE_HOST_LOSS_OBSERVED','LEADER_RESTORED','CONSOLE_TRANSFERRED','FIRST_NEW_SERVICE_ACCEPTED')])

if __name__=='__main__':main()
