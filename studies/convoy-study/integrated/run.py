"""One mission combining cargo, crew, contact, leader recovery and console transfer."""
import importlib.util
import json
import copy
from pathlib import Path

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('console_study',STUDY/'console_19/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=json.loads((STUDY/'console_19/results.json').read_text())
cfg=copy.deepcopy(base['runs'][2]['scenario'])
threat=json.loads((STUDY/'baseline_09_14/results.json').read_text())['scenarios']['threat']
cfg['forces']=copy.deepcopy(threat['forces'])
cfg['params']['convoy']['contact_reaction']=dict(action='halt',triggers=['receive_fire'],
    halt_scope='all',release=dict(rule='timeout',clear_s=15.))
cfg['params']['study_herringbone']=dict(experimental=True,offset_m=20.,road='straight clear only')
cfg['params']['study_console_transfer']=dict(rule='transfer_successor',delay_s=20,
    kill_trigger='10 steps after first observed contact; diagnostic forced loss')
bridge=m.ConsoleTransfer('transfer_successor',kill_step=None)
trace,result=m.record(cfg,herringbone=True,c2_bridge=bridge)
assert bridge.kill_step is not None
assert bridge.leader_restored==bridge.kill_step+5
assert bridge.console_restored==bridge.leader_restored+20
assert bridge.first_new_service is not None
assert result['convoy_contact_count']>0 and result['study_parked_vehicle_steps']>0
assert result['cargo_loaded']==60 and result['crew_total']==15
assert result['ll_handoffs']>=1
assert result['crew_lost']>=2
trace.update(group='ALL TOGETHER — #9 + #14 + #12 + #17 + #19',
    label='32. INTEGRATED — cargo + autonomy + escorts + HALT/Herringbone + leader/console recovery',
    desc='Single seed 0. Real engagement plus explicitly forced first-control loss 10 steps after first contact. Experimental Herringbone and successor-console transfer; not a calibrated model.',
    events=sorted(trace['events']+bridge.events,key=lambda e:e['t']))
old=[]
for name in ('baseline_09_14','contact_09_12_14','leader_12_17','console_19'):
    old+=json.loads((STUDY/name/'replays.json').read_text())
(HERE/'replays.json').write_text(json.dumps([trace]))
(HERE/'results.json').write_text(json.dumps(dict(seed=0,scenario=cfg,result=result,events=trace['events'],
    loss=bridge.kill_step,leader_restored=bridge.leader_restored,console_restored=bridge.console_restored,
    first_new_service=bridge.first_new_service),indent=2))
m.build_viewer(old+[trace])
print({k:result[k] for k in ('cargo_delivered','cargo_lost','cargo_in_transit','crew_lost','crew_steps_at_risk')})
print('loss',bridge.kill_step,'leader',bridge.leader_restored,'console',bridge.console_restored,'service',bridge.first_new_service)
