"""Study illustrations from saved results, not new mission experiments."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
DATA = REPO / 'report/viz'
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
W, H = 1440, 1480
INK, MUTED, BLUE, GREEN, ORANGE, RED = '#172c40', '#526579', '#1769aa', '#217b68', '#b56b13', '#aa4650'
manifest = {}

def read(name):
    p = DATA / (name + '.json')
    manifest[name] = {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    return json.loads(p.read_text())

def font(size=28, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def text(x, y, s, size=28, color=INK, bold=False):
    d.text((x,y), str(s), font=font(size,bold), fill=color)

def para(y, s, color=INK, size=28, width=1280):
    words=s.split(); line=''; yy=y
    for word in words:
        test=(line+' '+word).strip()
        if d.textlength(test,font=font(size)) > width:
            text(70,yy,line,size,color); yy+=42; line=word
        else: line=test
    if line: text(70,yy,line,size,color)
    return yy+46

def start(num,title,subtitle):
    global im,d
    im=Image.new('RGB',(W,H),'#f8fafc');d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,18),fill=BLUE)
    text(70,55,'SANDTABLE / STUDY SHEET',25,MUTED,True)
    text(70,105,f'#{num}  {title}',48,INK,True)
    para(180,subtitle,size=28)

def section(y,title):
    d.line((70,y-16,1370,y-16),fill='#cbd5df',width=2)
    text(70,y,title,30,INK,True)

def bars(y,labels,vals,maxv,unit='',errors=None,colors=None):
    x0,x1=470,1190
    for idx,(label,v) in enumerate(zip(labels,vals)):
        yy=y+idx*75
        text(70,yy+7,label,25)
        d.rectangle((x0,yy+8,x1,yy+41),fill='#e4eaf0')
        end=x0+(x1-x0)*v/maxv
        d.rectangle((x0,yy+8,end,yy+41),fill=(colors[idx] if colors else BLUE))
        if errors:
            lo=x0+(x1-x0)*max(0,v-errors[idx])/maxv
            hi=x0+(x1-x0)*min(maxv,v+errors[idx])/maxv
            d.line((lo,yy+24,hi,yy+24),fill=INK,width=3)
            d.line((lo,yy+15,lo,yy+34),fill=INK,width=3)
            d.line((hi,yy+15,hi,yy+34),fill=INK,width=3)
        text(1210,yy+4,f'{v:.2f}{unit}',25)
    yy=y+len(vals)*75
    d.line((x0,yy-10,x1,yy-10),fill=MUTED,width=2)
    text(x0,yy,'0',22,MUTED);text(x1-75,yy,f'{maxv:g}{unit}',22,MUTED)

def save(n):
    text(70,1395,'Saved-result illustrations / single-model evidence / 29 October 2026',22,MUTED)
    im.save(ROOT/f'{n}.png')

start(9,'Cargo delivery','Question: Did the supplies arrive, rather than merely some vehicles?')
section(290,'MODEL / accounting identity')
text(70,350,'Loaded = Delivered + Lost + Still in transit',38,BLUE,True)
text(70,415,'Delivery fraction = Delivered / Loaded',32)
text(70,465,'Success = 1 when delivery fraction reaches the required threshold',28)
section(570,'CONTROLLED CODE EXAMPLE / executed for this study guide')
para(625,'Two units, six cargo trucks total, 5 tons each. Two deliver, two are destroyed before delivery, and two remain alive on the road.')
bars(770,['Delivered','Lost','In transit'],[10,10,10],30,' t',colors=[GREEN,RED,ORANGE])
para(1080,'30 = 10 + 10 + 10 tons. Delivered fraction = 33.3%. At a 50% requirement this state is not successful.')
para(1200,'This verifies accounting in a constructed state. It is not a before/after mission-effect experiment.',MUTED)
save('09-cargo')

contact=read('contact_arms')['arms']
start(12,'Contact reaction','Question: On contact, keep moving or hold the convoy?')
section(290,'MODEL / a state rule, not one continuous equation')
text(70,350,'Trigger -> contact active -> continue OR hold',36,BLUE,True)
para(420,'For halt, hold stays active until the configured release rule allows movement. Movement can stop while weapons continue firing.')
section(570,'SAVED EXPERIMENT / UC-3 / means over 20 seeds')
bars(640,['No escort / no reaction','Escort / no reaction','Escort / continue','Escort / halt'],[r['blue_losses'] for r in contact],6,colors=[MUTED,BLUE,BLUE,GREEN])
text(470,1005,'Mean Blue vehicles lost',27,MUTED)
para(1070,'Time to objective: escort/continue 565.65 s; escort/halt 747.35 s. In this saved setup, halting had fewer losses and took longer.')
para(1210,'Limits: placeholder gun-truck strength; no additional Red halt-cost mechanism; no uncertainty saved. This does not establish that halting is generally safer.',RED)
save('12-contact')

aut=read('autonomy_arms')['rows']; a=[r for r in aut if r['comms_level']==0]
start(14,'People at risk','Question: How does removing crews from cargo trucks change exposure?')
section(290,'MODEL / count each person at most once per step')
text(70,350,'Exposure = sum over steps and living Blue vehicles:',30,BLUE,True)
text(100,405,'crew count x indicator(any eligible Red shooter in range)',29)
para(475,'Two people exposed for 10 steps contribute 20 crew-steps. This range-only measure does not require detection or line of sight.')
section(620,'OLDER SAVED EXPERIMENT / C0 / means over 10 seeds')
bars(690,['Manned','Autonomous / link','Autonomous / behavior'],[r['crew_steps_at_risk'] for r in a],4000,colors=[MUTED,BLUE,GREEN])
text(470,980,'Mean crew-steps at risk',27,MUTED)
para(1045,'Saved delivered fractions: 40.8%, 43.3%, 46.7%, respectively. Reduced personnel exposure and delivered cargo are different outcomes.')
para(1190,'Historical output, not a fresh rerun. All C0-C5 rows repeat within each arm: this file does not demonstrate a communications-degradation effect. No uncertainty saved.',RED)
save('14-personnel')

start(16,'Streets and visibility','Question: Which street path is chosen, and does a building block sight?')
section(290,'MODEL / shortest path using a configurable cost')
text(70,350,'cost(edge) = (1-b) x L/m + b x L x e',35,BLUE,True)
para(415,'L = configured length; m = speed multiplier; e = exposure score; b = route bias. This is a weighted cost, not a calibrated travel time or casualty probability.')
section(570,'CONTROLLED CODE EXAMPLE / same structure as the route test')
text(70,630,'Path A: L=1000, m=1.0, e=0.9',29)
text(70,680,'Path B: L=1200, m=0.6, e=0.1',29)
bars(770,['b=0: Path A cost','b=0: Path B cost'],[1000,2000],2200)
bars(1000,['b=1: Path A cost','b=1: Path B cost'],[900,120],2200)
para(1230,'Executed code selects A at b=0 and B at b=1. This checks route selection; no isolated city-vs-open-road mission comparison was found in the reviewed saved results.',MUTED)
save('16-streets')

leader=read('leader_loss_arms')['rows']
selected=['legacy','continue','promote_h0_idealized','absorb_h0_idealized','halt_no_release','halt_clear10_max30']
lr=[next(r for r in leader if r['experiment']=='engagement' and r['arm']==k) for k in selected]
start(17,'Leader loss','Question: What do the survivors do after the unit head dies?')
section(290,'MODEL / explicit policy and release conditions')
para(350,'promote: choose a replacement. absorb: logically join another unit. continue: navigate independently. halt: hold the affected unit. legacy: retain old behavior.')
text(70,500,'Release halt if clear counter >= N OR hold counter >= T',29,BLUE,True)
section(590,'SAVED ENGAGEMENT EXPERIMENT / means over 20 seeds')
bars(650,['Legacy','Continue','Promote / delay 0','Absorb / delay 0','Halt / no release','Halt / clear10 or max30'],[100*r['delivered_frac'] for r in lr],100,'%',errors=[100*r['delivered_frac_se'] for r in lr])
para(1170,'Bars show delivered cargo, not success rate. Whiskers are +/-1 standard error. Absorb is a logical reassignment; its higher mean is not a validated real-world advantage.',RED)
save('17-leader-loss')

red=read('red_priority_arms')['experiments']['abeam_ambush']['rows']; ref=red[0]; ends=next(r for r in red if r['arm']=='ends_seen')
start(18,'Red selection and blockage','Question: Which eligible vehicle is selected, and can a wreck stop motion?')
section(290,'MODEL / two separate mechanisms')
para(350,'Selection: choose the nearest eligible member of the first available configured class. Priority does not bypass sensing, range or line of sight.')
para(475,'Blockage extension: while a wreck is active, constrain a vehicle behind it to stop before the wreck. No bypass or street-graph rerouting is modeled.')
section(620,'SAVED PRIORITY EXPERIMENT / abeam setting / 40 seeds')
bars(690,['Legacy / head-loss events','Ends / head-loss events','Legacy / trail-loss events','Ends / trail-loss events'],[ref['tp_head_destroyed'],ends['tp_head_destroyed'],ref['tp_trail_destroyed'],ends['tp_trail_destroyed']],4,errors=[ref['tp_head_destroyed_se'],ends['tp_head_destroyed_se'],ref['tp_trail_destroyed_se'],ends['tp_trail_destroyed_se']])
para(1080,'Cargo delivered: legacy 49.17%; ends 49.58%. More end-loss events did not establish a delivery difference. Head identity may change; these are events, not original heads only.')
para(1230,'Whiskers: +/-1 SE. This priority file predates lane blocking. Later blocking runs unexpectedly raised delivery in some arms; the cause remains unresolved.',RED)
save('18-red-priority')

att=read('attention_diagnostic_short'); vals=att['arm_means']
start(19,'Console attention','Question: How is one operator console assigned to each march unit?')
section(290,'MODEL / per-console attention and served quality')
text(70,350,'a = min(1, capacity / supervised followers)',35,BLUE,True)
text(70,410,'q = q_auto + (q_operator - q_auto) x a',35,BLUE,True)
para(480,'Example: 4 followers, q_auto=0.70, q_operator=0.95. A host loss disables its console; followers keep their original assignments in this checkpoint.')
section(620,'SAVED SHORT DIAGNOSTIC / 30 seeds / no host losses')
bars(690,['Capacity 8 / a=1','Capacity 4 / a=1','Capacity 2 / a=0.5','Capacity 1 / a=0.25'],[vals[f'span={k}']['c2u_quality_mean'] for k in [8,4,2,1]],1)
para(1080,'Wait = 0.713 steps and served share = 80.87% in every arm. Quality changes; queue metrics stay identical in this controlled short experiment.')
para(1220,'Equation verification, not human-workload validation. Quality also changes speed and combat. The saved runs belong to earlier source snapshots; #19 remains incomplete.',RED)
save('19-consoles')

sweep=read('convoy_sweep_data'); pick=[sweep[i] for i in [0,1,2,3]]
start(15,'Search over settings','Question: Which configurations trade time, losses and road space?')
section(290,'MODEL / choose parameters, then minimize a weighted cost')
text(70,350,'J = wF x failure + wT x T/T0',34,BLUE,True)
text(145,402,'+ wL x loss fraction + wR x road space/R0',32,BLUE,True)
para(470,'With cargo active, failure = 1 - delivered fraction. Without cargo, the fallback uses mission success. Weights state preferences, not physical laws.')
section(620,'OLDER SAVED SCREEN / 33 settings / 5 seeds per setting')
bars(690,[r['id'] for r in pick],[r['mission_score'] for r in pick],1.6)
text(470,1030,'Saved mission cost J / lower is preferred by these weights',25,MUTED)
para(1090,'REF-BASE: 15 vehicles, pace 10, gap 4, J=0.329. LHS-02: 15 vehicles, pace 10.01, gap 4.86, J=0.323. Several settings change together.')
para(1230,'This older screen has no cargo-delivery metrics or saved uncertainty. It cannot isolate one parameter or establish an optimum. Registered Baseline is its saved label, not a provenance claim.',RED)
save('15-search')

(ROOT/'result-sources.json').write_text(json.dumps(manifest,indent=2))
print('Created eight study sheets and result-sources.json')
