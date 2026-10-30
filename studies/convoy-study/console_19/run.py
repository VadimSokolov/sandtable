"""Learning adapter: leadership recovery versus console-service recovery.

Only promote is covered. No absorb ownership policy or production C2 changes.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
sys.path.insert(0,str(STUDY/'leader_12_17'))
from run import record,build_viewer
from sandtable import c2

class ConsoleTransfer:
    def __init__(self,rule,kill=True,delay=20,kill_step=150):
        self.rule,self.kill,self.delay=rule,kill,delay
        self.op=None
        self.leader_restored=self.console_restored=self.first_new_service=None
        self.events=[]
        self.loss_services=None
        self.initial_host=None
        self.kill_step=kill_step
    def after_behavior(self,k,ent,bhv):
        if self.kill and self.kill_step is not None and k>=self.kill_step and self.leader_restored is None and bhv.ll_head[0]>=0:
            self.leader_restored=k
            self.events.append(dict(t=k,event='LEADER_RESTORED',host=int(bhv.ll_head[0])))
    def snapshot(self,ent):
        if self.op is None:
            return dict(rule=self.rule,hosts=[],available=[],serviced=[],abandon=[],leader_restored=None,
                        console_restored=None,first_new_service=None)
        u=self.op.units
        return dict(rule=self.rule,hosts=u.host.tolist(),available=ent.alive[u.host].tolist(),
            serviced=u.serviced.tolist(),abandon=u.abandon_console.tolist(),
            leader_restored=self.leader_restored,console_restored=self.console_restored,
            first_new_service=self.first_new_service)
    def __enter__(self):
        original=c2.step
        def step(ent,op,comms,scn,k,rng,world=None,bhv=None):
            self.op=op;u=op.units
            if self.initial_host is None:self.initial_host=int(u.host[0])
            if self.kill and self.kill_step is None and bhv.in_contact:
                self.kill_step=k+10
                self.events.append(dict(t=k,event='DIAGNOSTIC_LOSS_SCHEDULED',at=self.kill_step))
            if self.kill and self.kill_step is not None and k==self.kill_step:
                h=self.initial_host
                assert ent.alive[h] and ent.convoy_role[h]==0 and ent.cargo[h]==0
                ent.alive[h]=False;ent.hp[h]=0
                self.loss_services=int(u.serviced[0])
                self.events.append(dict(t=k,event='HOST_AND_LEADER_LOST',host=h))
            if (self.rule=='transfer_successor' and self.leader_restored is not None
                and self.console_restored is None and k>=self.leader_restored+self.delay):
                h=int(bhv.ll_head[0])
                if h>=0 and ent.alive[h] and ent.crew[h]>0:
                    u.host[0]=h
                    # Preserve reservations, pending fallback/replies, assignment,
                    # attention denominator and console capacity; no extra server.
                    op.crew_free_at[0]=max(float(k),op.crew_free_at[0])
                    self.console_restored=k
                    self.events.append(dict(t=k,event='CONSOLE_TRANSFERRED',host=h))
            before=int(u.serviced[0])
            original(ent,op,comms,scn,k,rng,world,bhv)
            if self.kill and self.kill_step is not None and k>=self.kill_step and u.serviced[0]>before and self.first_new_service is None:
                self.first_new_service=k
                self.events.append(dict(t=k,event='FIRST_NEW_SERVICE_ACCEPTED'))
        self.patch=patch.object(c2,'step',step);self.patch.__enter__();return self
    def __exit__(self,*args):return self.patch.__exit__(*args)

def main():
    base=json.loads((STUDY/'leader_12_17/results.json').read_text())
    cfg=copy.deepcopy(base['scenarios']['No loss control / reduced_crew'])
    cfg['params'].update(control_mode='direct',console_per_march_unit=dict(attention_basis='assigned',exceptions=False),
        queue_model='reserve',n_operators=1,span_capacity=4,service_rate=.5,decision_interval=30,
        patience=20,q_operator=.95,q_auto=.7,q_fallback=.5,q_stall=.3,comms_level=0)
    cfg['params']['convoy'].update(leader_loss_policy='promote',handoff_steps=5)
    cfg['params']['convoy'].pop('contact_reaction',None)
    old=[]
    for n in ('baseline_09_14','contact_09_12_14','leader_12_17'):
        old+=json.loads((STUDY/n/'replays.json').read_text())
    traces,rows=[],[]
    for rule,kill in [('no_loss_control',False),('fixed_console',True),('transfer_successor',True)]:
        c=copy.deepcopy(cfg)
        c['params']['study_console_transfer']=dict(rule=rule,delay_s=20,kill_time_s=150 if kill else None)
        bridge=ConsoleTransfer(rule,kill=kill)
        tr,result=record(c,c2_bridge=bridge)
        assert result['crew_total']==15 and result['cargo_loaded']==60
        if kill:
            assert bridge.leader_restored==155
            assert result['crew_lost']==2 and result['ll_handoffs']==1
        if rule=='fixed_console':
            assert bridge.console_restored is None and bridge.first_new_service is None
            assert bridge.op.units.serviced[0]==bridge.loss_services
            assert bridge.op.units.abandon_console[0]>0
        if rule=='transfer_successor':
            assert bridge.console_restored==175
            assert bridge.first_new_service is not None and bridge.first_new_service>=175
            assert bridge.op.units.host[0]!=bridge.initial_host
        if not kill:assert result['crew_lost']==0 and result['ll_handoffs']==0
        tr.update(group='#19 — leadership vs console recovery (study rules)',
            label=f'{len(old)+len(traces)+1}. Console / {rule} / reduced crew',
            desc='Seed 0, no enemy, 18 vehicles / 15 crew / 60 tons. Promote latency 5 s. Study console-transfer delay 20 s. Service counts mean accepted/scheduled requests, not confirmed reply delivery.',
            events=tr['events']+bridge.events)
        traces.append(tr)
        rows.append(dict(rule=rule,leader_restored=bridge.leader_restored,console_restored=bridge.console_restored,
            first_new_service=bridge.first_new_service,events=bridge.events,scenario=c,result=result))
        print(rule,'leader',bridge.leader_restored,'console',bridge.console_restored,'new service',bridge.first_new_service,flush=True)
    (HERE/'replays.json').write_text(json.dumps(traces))
    (HERE/'results.json').write_text(json.dumps(dict(seed=0,
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),runs=rows),indent=2))
    build_viewer(old+traces)
    text=['# Issue #19 — leadership vs console recovery','','One seed (0), no enemy; teaching diagnostics, not a policy ranking.','',
          '| Rule | Leadership restored | Console available | First new service accepted |',
          '|---|---:|---:|---:|']
    for r in rows:text.append('| '+r['rule']+' | '+' | '.join('—' if r[k] is None else str(r[k])+' s' for k in ('leader_restored','console_restored','first_new_service'))+' |')
    text+=['','Rules: promote after 5 steps; fixed original console vs transfer to living crewed successor 20 steps after leadership recovery. Console assignments and number of servers remain unchanged.',
        'Existing pending replies/fallback waits and reserved slots retain existing engine semantics; no cancellation, requeue or resurrected-job rule is added. A pre-loss scheduled reply may still arrive after host destruction.',
        'Transfer assumes compatible console equipment/operator capability at the successor escort. This is an explicit study assumption, not a production feature or personnel task model.',
        'Quality affects movement and combat through the current engine. No enemy is present here. Service counters count scheduling/acceptance, not completed answer delivery.',
        'No absorb reassignment, exceptions experiment, remote/off-loop comparator, workload calibration, registered neglect inequality or full-suite validation is claimed.',
        'Original 28 options retained. New 29–31 use local study adapter; production source unchanged.']
    (HERE/'RESULTS.md').write_text('\n'.join(text)+'\n')
    print('Viewer has',len(old)+len(traces),'options')

if __name__=='__main__':main()
