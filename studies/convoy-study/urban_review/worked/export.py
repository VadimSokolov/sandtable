"""Run selected real tests and publish their worked teaching storyboards.

Storyboard transitions are explanatory, not new mission simulation or recorded vehicle motion.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
NODES=[('9','tests/test_convoy_cargo_delivery.py','test_cargo_conservation_invariant'),
 ('12','tests/test_convoy_contact_reaction.py','test_halt_holds_column_then_times_out'),
 ('13','tests/test_convoy_route_stationing.py','test_route_polyline_geometry_and_projection'),
 ('14','tests/test_convoy_autonomous_unit.py','test_reference_convoy_with_escorts'),
 ('15','tests/test_convoy_separation_search.py','test_mission_score_road_space_penalty'),
 ('16','tests/test_convoy_street_graph.py','test_building_los_blocking'),
 ('17','tests/test_convoy_leader_loss.py','test_promote_latency'),
 ('18','studies/convoy-study/urban_review/worked/test_priority_example.py','test_control_priority_and_ineligible_fallback'),
 ('19','tests/test_c2_units.py','test_attention_below_at_and_above_capacity')]

def build():
    xml=HERE/'verification.xml'
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    cmd=[sys.executable,'-B','-m','pytest','-q',*[p+'::'+n for _,p,n in NODES],'--junitxml='+str(xml)]
    subprocess.run(cmd,cwd=ROOT,env=env,check=True)
    cases=ET.parse(xml).getroot().findall('.//testcase')
    assert cases and not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in cases)
    data=[]
    def add(issue,title,setup,formula,steps,states,limit,kind='state'):
        _,path,name=next(n for n in NODES if n[0]==issue)
        source=(ROOT/path).read_text();tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        matched=[c for c in cases if c.attrib['name'].split('[')[0]==name]
        assert matched,name
        data.append(dict(issue=issue,title=title,setup=setup,formula=formula,steps=steps,states=states,limit=limit,kind=kind,
            source=path,node=name,source_code='\n'.join(source.splitlines()[min([fn.lineno]+[d.lineno for d in fn.decorator_list])-1:fn.end_lineno]),source_sha256=hashlib.sha256(source.encode()).hexdigest(),verified_cases=len(matched),status='passed'))
    add('9','Cargo conservation', 'Two units × five vehicles. Each unit has control, three cargo trucks and recovery. Only the six cargo trucks carry 5 tonnes each.',
        r'L=\sum c_i,\quad D=\sum D_i,\quad X=\sum(1-a_i)(c_i-D_i),\quad I=\sum a_i(c_i-D_i)',
        ['Load: 6 cargo trucks × 5 t = 30 t; control/recovery carry zero.',
         'Deliver: 2 trucks × 5 t = 10 t. Remaining undelivered cargo is 20 t.',
         'Force destruction of 2 different loaded trucks: X = 2 × 5 = 10 t.',
         'Two living undelivered trucks remain: I = 2 × 5 = 10 t. Check 30 = 10 + 10 + 10; delivered fraction = 10/30 = 1/3.'],
        [dict(label='Loaded',values='L=30, D=0, X=0, I=30',vehicles=['cargo']*6),dict(label='Two delivered',values='L=30, D=10, X=0, I=20',vehicles=['delivered']*2+['cargo']*4),dict(label='Two destroyed',values='L=30, D=10, X=10, I=10',vehicles=['delivered']*2+['dead']*2+['cargo']*2),dict(label='Conservation confirmed',values='30 = 10 + 10 + 10',vehicles=['delivered']*2+['dead']*2+['cargo']*2)],
        'The test assigns delivery/destruction states directly. The six glyphs represent cargo trucks only; their drawn positions and transitions are explanatory, not simulated travel.')
    add('12','Halt and timed release','A receive-fire signal is supplied at step 0. clear_s=5 and dt=1 s. Signals are cleared for steps 1–5, then supplied again at step 6.',
        r'hold(k)=1[k-k_{last}<5],\qquad t=k\Delta t',
        ['k=0: receive_fire=true, so k_last=0 and 0−0=0<5. Hold activates.',
         'k=1,2,3,4: no new trigger; elapsed values 1,2,3,4 are all less than 5. Hold remains active.',
         'k=5: elapsed=5; 5<5 is false. Hold clears and contact ends.',
         'k=6: a new receive-fire trigger starts a second contact episode; contact_count=2.'],
        [dict(label='k=0 · incoming-fire signal',values='elapsed=0; HOLD',vehicles=['hold']*5),dict(label='k=4 · no fresh signal',values='4 < 5; HOLD',vehicles=['hold']*5),dict(label='k=5 · timeout',values='5 < 5 is false; RELEASE',vehicles=['cargo']*5),dict(label='k=6 · new signal',values='contact_count=2; HOLD',vehicles=['hold']*5)],
        'This is a behavior-state test, not a full movement or Herringbone test. Five representative glyphs stand for the held column; the test does not assert their travel distances.')
    add('13','Arc length on an L-shaped road','Route: (0,0) → (1000,0) → (1000,1000). Both segments are 1000 m.',
        r'L=1000+1000=2000,\quad r(1500)=(1000,500)',
        ['First segment length: sqrt((1000−0)²+0²)=1000 m. Second segment length: 1000 m. Total=2000 m.',
         'At s=500 m, remain on the first segment: r(500)=(500,0), heading=0.',
         'At s=1500 m, pass the first 1000 m and travel 500 m along the second: r(1500)=(1000,500), heading=π/2.',
         'Project (1050,600) onto x=1000: foot=(1000,600), s=1000+600=1600 m, cross-track distance=50 m.'],
        [dict(label='Two connected segments',values='L=2000 m',point=[0,0]),dict(label='First segment',values='s=500 → (500,0)',point=[500,0]),dict(label='Second segment',values='s=1500 → (1000,500)',point=[1000,500]),dict(label='Orthogonal projection',values='(1050,600) → s=1600, offset=50 m',point=[1050,600])],
        'The marker visits query positions from the geometry test. Interpolation is a teaching animation, not execution of vehicle motion.',kind='route')
    add('14','Crew counts with escorts','Three units of five core vehicles, plus three armed escorts. Manned control/cargo crew=2; escort crew=3. Autonomous cargo crew=0.',
        r'N_{manned}=15(2)+3(3)=39,\quad N_{auto}=3(2)+12(0)+3(3)=15',
        ['Core organization: 3 units × 5 vehicles = 15 vehicles, comprising 3 control vehicles and 12 cargo trucks.',
         'Manned case: 15 × 2 + 3 × 3 = 30 + 9 = 39 people.',
         'Autonomous-cargo case: 3 × 2 + 12 × 0 + 3 × 3 = 6 + 0 + 9 = 15 people.',
         'Ratio: 39/15=2.6. Difference: 39−15=24 fewer onboard people. This is crew assignment, not evidence of fewer casualties.'],
        [dict(label='15 core vehicles + 3 escorts',values='18 vehicles in each configuration',vehicles=['control']*3+['cargo']*12+['escort']*3),dict(label='Manned',values='39 onboard people',vehicles=['control']*3+['cargo']*12+['escort']*3),dict(label='Autonomous cargo',values='15 onboard people',vehicles=['control']*3+['empty']*12+['escort']*3),dict(label='Same vehicle count',values='39 / 15 = 2.6',vehicles=['control']*3+['empty']*12+['escort']*3)],
        'This test also checks five escorts (45 versus 21 crew); this worked example covers only the three-escort subcase. It does not calculate exposure or casualty probability.')
    add('15','An explicit road-space penalty','The test uses success=1, time=500 s, Blue loss fraction=0.1 and road space=1000 m. Defaults: w_fail=1, w_time=0.3, w_loss=0.5, time_scale=1800 s.',
        r'J=1(1-success)+0.3(T/1800)+0.5f_{loss}+w_{road}(RS/1000)',
        ['Without the road penalty: J=1×0+0.3×(500/1800)+0.5×0.1=0.133333…',
         'Enable w_road=0.2: added penalty=0.2×(1000/1000)=0.2.',
         'New score: 0.133333…+0.2=0.333333…; the asserted score increase is exactly 0.2.',
         'At RS=2000 m, penalty=0.2×2=0.4, giving J=0.533333…; higher is worse for this minimization score.'],
        [dict(label='Road penalty off',values='J=0.133333',vehicles=['cargo']*4),dict(label='Road penalty on',values='ΔJ=+0.2',vehicles=['cargo']*4),dict(label='RS=1000 m',values='J=0.333333',vehicles=['cargo']*4),dict(label='RS=2000 m',values='J=0.533333',vehicles=['cargo']*4)],
        'This verifies a configurable objective term, not optimization or a best policy. Drawn spacing is schematic; the test supplies road-space summary values directly.')
    add('16','A building blocks one ray','World: 1000×1000 m, 25 m raster cells. Building cells [16:24,16:24] occupy the central 400–600 m block.',
        r'LOS=1[\text{no sampled ray point intersects a building}]',
        ['Raster bounds: 16×25=400 m and 24×25=600 m; cells 16 through 23 are occupied.',
         'Ray (200,500)→(800,500) crosses the building at y=500. Expected LOS=false.',
         'Ray (200,200)→(800,200) stays below the building. Expected LOS=true.',
         'Ray (100,100)→(200,100) also avoids the building. Assert [false,true,true].'],
        [dict(label='Building footprint',values='400–600 m central block',ray=0),dict(label='Ray through building',values='LOS=false',ray=0),dict(label='Parallel ray outside',values='LOS=true',ray=1),dict(label='Short street ray',values='LOS=true',ray=2)],
        'The ray is animated for explanation. LOS is calculated by the raster model; this test does not validate radio propagation or probability of detection.',kind='los')
    add('17','Promotion after three steps','The first unit head is deliberately marked dead. leader_loss_policy=promote and handoff_steps=3.',
        r'k_{handoff}=k_{observed\ loss}+3=0+3',
        ['Before tick 0, mark the unit head dead. This is a forced state change, not an enemy kill.',
         'Ticks 0,1,2: no handoff yet. The first survivor still references the dead head; leaderless_steps accumulates to 3.',
         'Tick 3: the configured delay is reached. Promote the first eligible survivor.',
         'Assert: the new head has leader=−1, the unit head points to that survivor, and ll_handoffs=1.'],
        [dict(label='Head marked dead',values='loss observed at k=0',vehicles=['dead','cargo','cargo','cargo','cargo']),dict(label='Ticks 0–2',values='leaderless_steps=3; no handoff',vehicles=['dead','hold','hold','hold','hold']),dict(label='Tick 3',values='handoff occurs',vehicles=['dead','control','cargo','cargo','cargo']),dict(label='New head assigned',values='leader=−1; ll_handoffs=1',vehicles=['dead','control','cargo','cargo','cargo'])],
        'Glyph colors show leadership status, not physical halt commands. This unit test does not prove the superiority of promotion or transfer any console.')
    add('18','Priority respects eligibility','New dedicated selector diagnostic: Red at x=0, cargo at x=40, control at x=100. The fixture initially declares both Blue targets eligible.',
        r't^*=\arg\min_{i\in E\cap Control}d_i;\quad\text{if empty, use nearest eligible}',
        ['Distances: d_cargo=|40−0|=40 m; d_control=|100−0|=100 m. Nearest eligible is cargo.',
         'With order=[control] and both eligible, the control set is nonempty. Select the control at 100 m.',
         'Change the supplied eligibility mask: control becomes ineligible.',
         'The control set is now empty. Fall back to cargo at 40 m; priority cannot restore an ineligible target.'],
        [dict(label='Nearest rule',values='cargo at 40 m',target='cargo'),dict(label='Control-first',values='control at 100 m',target='control'),dict(label='Control ineligible',values='control removed from E',target='none'),dict(label='Fallback',values='cargo at 40 m',target='cargo')],
        'This new test calls the preserved branch selector used by the study. It supplies eligibility directly; it does not simulate sensing, LOS, firing or kill draws.',kind='priority')
    add('19','Attention and served quality','Use one parameterized test case: four assigned crewless followers per console, span_capacity=2, q_auto=0.70 and q_operator=0.95.',
        r'A=\min(1,2/4)=0.5,\quad q=0.70+(0.95-0.70)A',
        ['Count N=4 assigned followers per console. The selected test case sets capacity C=2.',
         'Attention A=min(1,C/N)=min(1,2/4)=0.5.',
         'Quality gain q_operator−q_auto=0.95−0.70=0.25; diluted gain=0.25×0.5=0.125.',
         'Served quality q=0.70+0.125=0.825 for each of the three consoles. Other tested capacities 8,4,1 give attention 1,1,0.25.'],
        [dict(label='Assigned followers',values='N=4; C=2',vehicles=['control','cargo','cargo','cargo','cargo']),dict(label='Attention',values='A=0.5',vehicles=['control','cargo','cargo','cargo','cargo']),dict(label='Diluted gain',values='0.25 × 0.5 = 0.125',vehicles=['control','cargo','cargo','cargo','cargo']),dict(label='Served quality',values='q=0.825',vehicles=['control','cargo','cargo','cargo','cargo'])],
        'This verifies the attention equation, not human workload calibration. The animation depicts one console; the assertion covers all three. Attention does not by itself change service time.')
    output=dict(examples=data,verification=dict(selected_tests=len(cases),passed=len(cases),command=' '.join(cmd),kind='Selected unit tests only; not the full suite'))
    (HERE/'examples.json').write_text(json.dumps(output,indent=2))
    print('Exported',len(data),'worked examples from',len(cases),'passing test cases.')

if __name__=='__main__':build()
