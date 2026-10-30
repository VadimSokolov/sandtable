"""Build a self-contained review page using saved Sandtable mission traces.

Run with a Python environment containing markdown and latex2mathml.
No simulations or tests are executed by this builder or the delivered page.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import html
import importlib.util
import json
import re
import subprocess
import markdown
from latex2mathml.converter import convert
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STUDY=HERE.parent
ORDER=('baseline_09_14','contact_09_12_14','leader_12_17','console_19','integrated','red_priority_18','route_13','urban_16','urban_maps','sketch_map','sweep_15')

def pack(obj):
    return base64.b64encode(gzip.compress(json.dumps(obj,separators=(',',':'),allow_nan=False).encode(),mtime=0)).decode()

def clean(x):
    import math
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list):return [clean(v) for v in x]
    if isinstance(x,float) and not math.isfinite(x):return None
    return x

def equation(tex):
    return '<div class="equation">'+convert(tex,display='block')+'</div>'

def guide(source):
    return render_lesson(source.read_text())

def render_lesson(text):
    text=re.sub(r'\$\$(.*?)\$\$',lambda m:'\n\n'+equation(m[1].strip())+'\n\n',text,flags=re.S)
    return markdown.markdown(text,extensions=['tables','fenced_code','sane_lists'])

CARDS=[
 ('8','Organization','Three march units; one serial/column layout. Roles identify control, cargo and security vehicles. A role is not a tactical planner.',r'N_{vehicles}=3(1+1+4)=18', 'test_convoy_hierarchy.py','Same integrated layout: 3 control vehicles, 3 escorts and 12 cargo trucks.'),
 ('9','Cargo accounting','Cargo is delivered on entering the goal radius. No unloading service is modeled in these convoy runs.',r'L=D+X+I,\qquad f_D=D/L','test_convoy_cargo_delivery.py','60 tonnes loaded. Alive and undelivered is in transit; delivered cargo is not lost if its vehicle is later destroyed.'),
 ('10','Pace and time gap','The following target uses the predecessor track. The requested pace is a speed cap, not guaranteed achieved speed.',r'g=\max(g_{min},v_{ref}\tau)','test_convoy_pace_time_gap.py','At 10 m/s, a 4 s gap and a 40 m floor produce a 40 m target gap.'),
 ('11','Column arithmetic','Nominal doctrine arithmetic describes the configured column; maneuvering can change measured geometry.',r'PT=CL/v,\qquad T_{clear}=T_{distance}+PT','test_convoy_doctrine_arithmetic.py','For column length CL=650 m and rate v=10 m/s, pass time PT=65 s. Road space equals CL only when the safety factor is zero. Use consistent units.'),
 ('12','Escorts and contact reaction','Incoming fire can trigger a halt without a successful hit. Each new trigger resets the clear timer.',r't-t_{last}<T_{clear}','test_convoy_contact_reaction.py','Choose continue, halt or experimental halt + Herringbone. Herringbone has no automatic protection bonus.'),
 ('13','Distance along a route','Route progress uses arc length along the polyline, with a convergence rule near the goal.',r'L_{route}=\sum_j\lVert P_j-P_{j-1}\rVert,\quad T_i=r(s_{ref}-g_i)','test_convoy_route_stationing.py','The same following rule works on a straight or curved route. The recorded route does not change interactively.'),
 ('14','Personnel exposure','Count living crew inside at least one eligible enemy weapon range, once per step. LOS and detection are not required by this metric.',r'E=\sum_k\sum_i a_{i,k}n_i z_{i,k},\quad N_{lost}=\sum_i(1-a_i)n_i','test_convoy_autonomous_unit.py','Exposure is crew-steps; multiply by dt for crew-seconds. Vehicle destruction loses the full crew in this abstraction.'),
 ('15','Settings and repeated runs','Compare one factor at a time over seeds 0–9 on the fixed direct route. This design does not estimate interactions.',r'\bar Y=\frac{1}{n}\sum_sY_s,\quad SE=SD/\sqrt{n}','test_convoy_separation_search.py','Nine configurations × ten seeds = 90 runs. The animation shows seed 0; the comparison table reports all ten.'),
 ('16','Streets and building visibility','A ground observer needs range and unobstructed LOS. Buildings do not automatically block radio in this model.',r'P_{detect}=1-concealment(p_{target})','test_convoy_street_graph.py','Explore the street-map collection and three sketch routes. No adaptive in-mission rerouting is connected here.'),
 ('17','Leader loss and recovery','Promote chooses an eligible successor after the configured handoff. Other saved diagnostics exercise continue, absorb and halt.',r't_{eligible\ handoff}=t_{loss\ observed}+H','test_convoy_leader_loss.py','Exact logged recovery time depends on update ordering and successor eligibility. The integrated study uses manned-only promotion.'),
 ('18','Red target priority','Choose an eligible, detected, in-range target with clear LOS, then apply priority. Control-first does not fire through buildings.',r'p=clip\{p_{base}(1-cover)q_{shooter}(2-q_{target}),0,1\}','test_convoy_contact_reaction.py','Natural control-first runs are distinct from forced-loss diagnostics. This study uses preserved #18 branch sources; the listed contact test is supporting coverage, not a dedicated #18 acceptance test.'),
 ('19','One console per march unit','Each console serves its assigned crewless followers. Host recovery and leadership recovery are separate events.',r'A_c=\min(1,C/N_c),\quad q_c=q_{auto}+(q_{operator}-q_{auto})A_c','test_c2_units.py','The study transfers a console to a living crewed successor 20 steps after leadership recovery. This is an experimental rule, not closure of issue #19.')]

def build():
    traces=[];inventory=[]
    for name in ORDER:
        path=STUDY/name/'replays.json'
        data=json.loads(path.read_text());start=len(traces)
        for trace in data:
            trace['source_file']=str(path.relative_to(ROOT))
            trace['study_folder']=name
            trace['forced_diagnostic']=any('FORCED' in e.get('event','') or 'DIAGNOSTIC_LOSS' in e.get('event','') for e in trace.get('events',[]))
        traces+=data
        inventory.append(dict(source=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),count=len(data),first_option=start+1))
    assert len(traces)==56
    exposure_path=HERE/'exposure_lesson/replays.json'
    exposure_traces=json.loads(exposure_path.read_text())
    assert len(exposure_traces)==2
    traces+=exposure_traces
    inventory.append(dict(source=str(exposure_path.relative_to(ROOT)),sha256=hashlib.sha256(exposure_path.read_bytes()).hexdigest(),count=2,first_option=57))
    original=(HERE/'original.html').read_text()
    styles=''.join(re.findall(r'<style>(.*?)</style>',original,flags=re.S))
    cards=''.join('<details class="pc" id="issue-'+n+'"><summary><h3>#'+n+' · '+title+'</h3></summary><p>'+desc+'</p>'+equation(tex)+'<p>'+note+'</p><p class="src">Verification source: <code>tests/'+test+'</code></p></details>' for n,title,desc,tex,test,note in CARDS)
    guide_html=guide(STUDY/'INTEGRATED_SCENARIOS_MATH.md')
    source_links=''.join('<li><code>'+row['source']+'</code> — '+str(row['count'])+' recorded missions</li>' for row in inventory)
    sweeps=clean(json.loads((STUDY/'sweep_15/results.json').read_text()))
    worked=json.loads((HERE/'worked/examples.json').read_text())
    lesson_spec=importlib.util.spec_from_file_location('review_lessons',HERE/'lessons.py')
    lesson_module=importlib.util.module_from_spec(lesson_spec);lesson_spec.loader.exec_module(lesson_module)
    lesson_module.configure(worked['examples'],traces,sweeps)
    for example in worked['examples']:
        example['formula_html']=equation(example['formula'])
        example['lesson_html']=render_lesson(example['lesson_markdown'])
    legacy=base64.b64encode(gzip.compress(original.encode(),mtime=0)).decode()
    provenance=dict(generated_from='Builder reads saved files; exposure diagnostics were generated separately by exposure_lesson/run.py',sources=inventory,
        snapshot_revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        distinctions='unit tests verify rules; saved missions illustrate behavior; experiments estimate outcomes within the model',
        presentation_sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'build.py',HERE/'page.html',HERE/'app.js',HERE/'original.html',STUDY/'INTEGRATED_SCENARIOS_MATH.md',HERE/'worked/examples.json',HERE/'worked/export.py',HERE/'worked/test_priority_example.py',HERE/'lessons.py',HERE/'exposure_lesson/run.py']})
    payload=pack(clean(dict(traces=traces,sweep=sweeps,worked=worked,provenance=provenance)))
    template=(HERE/'page.html').read_text()
    out=ROOT/'report/viz/urban_resupply.html';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(template.replace('__ORIGINAL_STYLES__',styles).replace('__ISSUE_CARDS__',cards)
        .replace('__FULL_GUIDE__',guide_html).replace('__SOURCE_LIST__',source_links)
        .replace('__DATA__',payload).replace('__LEGACY__',legacy).replace('__APP__',(HERE/'app.js').read_text()))
    (HERE/'source_inventory.json').write_text(json.dumps(provenance,indent=2))
    print(str(out),len(traces),'options;',round(out.stat().st_size/1024/1024,2),'MiB')
    return out

if __name__=='__main__':build()
