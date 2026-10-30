"""Actual-loop teaching replays: dedicated escorts and leader-loss recovery.

No source edits in sandtable. Forced loss is a diagnostic intervention only.
"""
import copy
import hashlib
import importlib.util
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
import numpy as np
from sandtable import behavior, metrics
from sandtable.sim import run_mission
from sandtable.scenario import Scenario
from herringbone import Herringbone

def record(config, seed=0, kill_at=None, herringbone=False, c2_bridge=None):
    state, frames, events = {}, [], []
    original_step, original_risk = behavior.step, metrics.accumulate_crew_at_risk
    def snap(ent, t):
        bhv = state['bhv']
        frames.append(dict(t=t, x=ent.x.round(2).tolist(), y=ent.y.round(2).tolist(),
            h=ent.heading.round(3).tolist(), alive=ent.alive.astype(int).tolist(),
            seen=ent.seen.astype(int).tolist(), cq=ent.control_quality.round(3).tolist(),
            kills=[], cargo_delivered=ent.cargo_delivered.tolist(),
            crew_alive=(ent.crew*ent.alive).astype(int).tolist(),
            holding=(getattr(bhv,'study_herringbone_parked',np.zeros(ent.n,dtype=int)) if
                config['params'].get('study_herringbone') else bhv.holding).astype(int).tolist(),
            hold_command=bhv.holding.astype(int).tolist(), in_contact=bool(bhv.in_contact),
            exposure=float(state.get('risk', 0)),
            leader=ent.leader.tolist(), march_unit=ent.march_unit.tolist(),
            ll_head=bhv.ll_head.tolist() if bhv.ll_head is not None else [],
            leaderless_steps=float(bhv.leaderless_steps), handoffs=float(bhv.ll_handoffs),
            herringbone_active=bool(getattr(bhv,'study_herringbone_active',False)),
            herringbone_parked=getattr(bhv,'study_herringbone_parked',np.zeros(ent.n,dtype=int)).astype(int).tolist()))
        if c2_bridge is not None:
            frames[-1]['console']=c2_bridge.snapshot(ent)
        urban=getattr(bhv,'study_urban_telemetry',None)
        if urban is not None:
            frames[-1]['urban']=dict(urban)
        route=getattr(state.get('world'),'route',None)
        if route is not None:
            ids=np.flatnonzero((ent.side==0)&(ent.domain==0))
            rs,rc=route.project(ent.x[ids],ent.y[ids])
            frames[-1]['route_s']=rs.tolist()
            frames[-1]['route_cross']=rc.tolist()
    def step(ent, bhv, *args, **kwargs):
        k = args[3]
        state.update(bhv=bhv, ent=ent, world=kwargs.get('world'),t=(k+1)*config['dt'])
        if not frames:
            state['entities'] = [dict(side=int(ent.side[i]), domain=int(ent.domain[i]),
                crew=int(ent.crew[i]), sensor_range=float(ent.sensor_range[i]),
                weapon_range=float(ent.weapon_range[i]), convoy_role=int(ent.convoy_role[i]),
                march_unit=int(ent.march_unit[i]), serial=int(ent.serial[i]),
                section=int(ent.section[i]), cargo=float(ent.cargo[i]),
                callsign=f'{"Blue" if ent.side[i]==0 else "Red"} {i+1} / crew {int(ent.crew[i])}')
                for i in range(ent.n)]
            snap(ent, 0)
        if kill_at is not None and k == kill_at:
            heads=np.flatnonzero((ent.side==0)&(ent.convoy_role==0)&(ent.march_unit==0)&ent.alive)
            assert len(heads)==1
            h=int(heads[0]); ent.alive[h]=False; ent.hp[h]=0
            events.append(dict(t=k*config['dt'], event='FORCED_CONTROL_LOSS', entity=h))
        original_step(ent, bhv, *args, **kwargs)
        if c2_bridge is not None:
            c2_bridge.after_behavior(k,ent,bhv)
        heads=bhv.ll_head.tolist() if bhv.ll_head is not None else []
        status=(tuple(heads), bool(bhv.in_contact), tuple(np.flatnonzero(bhv.holding)))
        if status != state.get('status'):
            events.append(dict(t=k*config['dt'], event='STATE_CHANGE', heads=heads,
                contact=bool(bhv.in_contact), held=np.flatnonzero(bhv.holding).tolist()))
            state['status']=status
    def risk(ent, acc):
        original_risk(ent, acc); state['risk']=acc.sum(); snap(ent,state['t'])
    adapter=Herringbone() if herringbone else nullcontext()
    with adapter, (c2_bridge if c2_bridge is not None else nullcontext()), patch.object(behavior,'step',step), patch.object(metrics,'accumulate_crew_at_risk',risk):
        outcome=run_mission(Scenario.from_dict(config),seed=seed)
    if herringbone:
        if adapter.episodes:
            assert adapter.park_checks > 0
        outcome.update(study_herringbone_episodes=adapter.episodes,
            study_parked_vehicle_steps=adapter.parked_vehicle_steps,
            study_maneuver_vehicle_steps=adapter.maneuver_vehicle_steps)
        if config['params'].get('study_urban'):
            outcome.update(study_building_blocked_moves=adapter.blocked_moves,
                           study_rejected_parking_stations=adapter.rejected_stations)
    snap(state['ent'],state['t'])
    assert abs(outcome['cargo_loaded']-sum(outcome[k] for k in
        ('cargo_delivered','cargo_lost','cargo_in_transit'))) < 1e-6
    baseline=json.loads((STUDY/'baseline_09_14/replays.json').read_text())
    trace=copy.deepcopy(baseline[0 if len(config['forces'])==1 else 2])
    trace.update(seed=seed,params=config['params'],entities=state['entities'],frames=frames,
                 outcome={**outcome,'cargo_total':60},total_cargo=60,events=events)
    if config['params'].get('route'):
        trace['route']=config['params']['route']
    world=state.get('world')
    if world is not None and config['params'].get('study_urban'):
        trace['street_graph']=world.street_graph.to_dict() if world.street_graph is not None else None
        trace['building_boxes']=world.building_boxes.tolist() if world.building_boxes is not None else []
        def downsample(a):
            return a[::max(1,a.shape[0]//40),::max(1,a.shape[1]//80)].tolist()
        trace['terrain']['cover']=downsample(world.cover)
        trace['terrain']['conceal']=downsample(world.conceal)
        trace['terrain']['buildings']=downsample(world.buildings.astype(int)) if world.buildings is not None else []
    return trace,outcome

def main():
    baseline=json.loads((STUDY/'baseline_09_14/results.json').read_text())
    old=json.loads((STUDY/'baseline_09_14/replays.json').read_text())
    old+=json.loads((STUDY/'contact_09_12_14/replays.json').read_text())
    traces,rows,configs=[],[],{}
    gun=dict(domain=0,max_speed=12.,turn_rate=.6,sensor_range=1500.,weapon_range=1200.,pk_base=.01,hp=1.)
    def config(condition,arm):
        c=copy.deepcopy(baseline['scenarios'][condition])
        c['platform_types']['study_gun_truck']=gun
        c['params']['convoy'].update(escort_vehicles=3, security_ptype='study_gun_truck',
            autonomy_arm='manned' if arm=='manned' else 'autonomous_march_unit', succession='manned_only')
        return c
    def add(c,arm,name,group,kill_at=None,herringbone=False):
        trace,r=record(c,kill_at=kill_at,herringbone=herringbone)
        trace.update(group=group,label=f'{len(old)+len(traces)+1}. {name}',
            desc=('Actual mission loop; seed 0; 18 Blue vehicles, 60 tons, 3 armed escorts. '+
                  ('Forced loss of first control at T+150s; no enemy; verifies mechanisms, not policy superiority.' if kill_at is not None else
                   'Natural engagement; placeholder escort armament; no Herringbone manoeuvre.')))
        assert sum(e['side']==0 for e in trace['entities'])==18
        assert sum(e['side']==0 and e['convoy_role']==2 for e in trace['entities'])==3
        assert r['cargo_loaded']==60
        assert r['crew_total']==(39 if arm=='manned' else 15)
        traces.append(trace);configs[name]=c;rows.append(dict(name=name,arm=arm,forced=kill_at is not None,**r))
        if herringbone:
            trace['desc']='EXPERIMENTAL STUDY ADAPTER, not a production engine feature. Actual finite-speed movement to alternating side stations during contact. 20 m offset is a placeholder. No claimed defensive benefit. Seed 0.'
        print(name,{k:r.get(k) for k in ('cargo_delivered','cargo_in_transit','crew_lost','ll_handoffs','ll_halt_steps')},flush=True)
        return r
    for action in ('continue','halt'):
        for arm in ('manned','reduced_crew'):
            c=config('threat',arm)
            c['params']['convoy']['contact_reaction']=dict(action=action,triggers=['receive_fire'],
                halt_scope='non_security',release=dict(rule='timeout',clear_s=15.))
            r=add(c,arm,f'Escorts / {arm} / contact {action.upper()}', '#12 — dedicated escorts, natural engagement')
            if action=='continue':assert r['convoy_halt_steps']==0
    policies=[('continue',{}),('promote',dict(handoff_steps=0)),
              ('promote',dict(handoff_steps=5)),('absorb',dict(handoff_steps=5)),
              ('halt',{}),('halt',dict(halt_release=dict(max_hold_steps=30)))]
    for arm in ('manned','reduced_crew'):
        control=config('no_threat',arm)
        control['params']['convoy']['leader_loss_policy']='promote'
        r=add(control,arm,f'No loss control / {arm}', '#17 — no-enemy forced-loss diagnostics')
        assert r['cargo_delivered']==60 and r['crew_lost']==0 and r['ll_handoffs']==0
        for policy,extra in policies:
            c=config('no_threat',arm)
            c['params']['convoy'].update(leader_loss_policy=policy,**extra)
            details=' / delay '+str(extra['handoff_steps'])+'s' if 'handoff_steps' in extra else (' / release 30s' if extra else '')
            name=f'Forced loss / {arm} / {policy.upper()}{details}'
            r=add(c,arm,name,'#17 — no-enemy forced-loss diagnostics',kill_at=150)
            assert r['crew_lost']==2 and r['cargo_lost']==0 and r['first_leader_loss_step']==150
            if policy=='halt' and not extra:
                assert r['cargo_in_transit']>0 and r['ll_halt_steps']>0 and r['ll_handoffs']==0
            if policy in ('promote','absorb') or extra.get('halt_release'):
                assert r['ll_handoffs']==1
            if policy=='continue':assert r['ll_handoffs']==0
    for arm in ('manned','reduced_crew'):
        c=config('threat',arm)
        c['params']['convoy']['contact_reaction']=dict(action='halt',triggers=['receive_fire'],
            halt_scope='all',release=dict(rule='timeout',clear_s=15.))
        c['params']['study_herringbone']=dict(experimental=True,offset_m=20.,road='straight clear only')
        add(c,arm,f'EXPERIMENTAL HALT + HERRINGBONE / escorts / {arm}',
            '#12 — experimental geometry adapter (not production)',herringbone=True)
    digest=hashlib.sha256()
    for p in sorted((REPO/'src/sandtable').rglob('*.py')):
        digest.update(str(p.relative_to(REPO)).encode());digest.update(p.read_bytes())
    (HERE/'results.json').write_text(json.dumps(dict(source_python_sha256=digest.hexdigest(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scenarios=configs,runs=rows),indent=2))
    (HERE/'replays.json').write_text(json.dumps(traces))
    build_viewer(old+traces)
    lines=['# Dedicated escorts and leader-loss diagnostics','','Single seed 0 teaching runs. Not 40-seed averages.','',
        '| Run | Delivered t | In transit t | Crew lost | Vehicle lost | Handoffs | Leaderless unit-steps |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:lines.append('| '+r['name']+' | '+' | '.join(str(r.get(k,'—')) for k in
        ('cargo_delivered','cargo_in_transit','crew_lost','blue_losses','ll_handoffs','leaderless_steps'))+' |')
    lines+=['','## Assumptions and limits','',
        '- 3 escorts are added, not substituted for cargo: 18 vehicles, 60 tons. Manned crew 39; reduced crew 15. Each escort has 3 people.',
        '- The gun-truck kill-probability parameter 0.01 is a placeholder, not a calibrated real-world value.',
        '- Escorts are placed immediately after each control vehicle by the existing layout; not a front-and-rear deployment.',
        '- Natural engagement: receive-fire trigger, 15 seconds clear before release; non-security vehicles halt, escorts remain mobile.',
        '- Leader-loss diagnostics: no enemy, forced destruction of first control at time 150 seconds. No contact reaction is enabled in these diagnostics.',
        '- Succession is manned_only: the armed, crewed escort is eligible to succeed the control. No console/C2 transfer model is enabled.',
        '- Continue sends survivors onward independently; promote selects a crewed successor; absorb logically joins another living unit; halt holds the affected unit until release if configured.',
        '- Handoff delay is policy latency, not necessarily stationary time. Promotion/absorption do not automatically stop movement during that delay.',
        '- Absorb is experimental logical reassignment, not a validated formation manoeuvre.',
        '- Herringbone is NOT implemented by sandtable; disperse explicitly raises NotImplementedError. These escort/halt runs must not be labelled Herringbone.',
        '- Two separately labelled HERRINGBONE options use a local study adapter: real finite-speed movement to alternating 20 m side stations, then park outward. This is not the core disperse implementation and does not complete production #12.',
        '- Herringbone uses contact halt with halt_scope=all. During the halt command the adapter first moves to side stations, then parks. Core convoy_halt_steps counts commanded hold, including manoeuvre time; study_parked_vehicle_steps counts actual parking separately.',
        '- Original eight options and their datasets are retained. New results use one seed and are not comparable as statistical averages to the prior 40-seed report.',
        '- Checks: cargo conservation, crew/escort counts, forced head loss and personnel accounting, recovery handoffs, permanent-halt stranded cargo, no-loss control, and zero halt steps under continue.']
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('Viewer updated:',len(old)+len(traces),'options')

def build_viewer(traces):
    maps_data=STUDY/'urban_maps/replays.json'
    if maps_data.exists() and not any(t.get('group','').startswith('#16 — map collection') for t in traces):
        traces=list(traces)+json.loads(maps_data.read_text())
    urban_data=STUDY/'urban_16/replays.json'
    if urban_data.exists() and not any(t.get('group','').startswith('#16 — streets') for t in traces):
        traces=list(traces)+json.loads(urban_data.read_text())
    route_data=STUDY/'route_13/replays.json'
    if route_data.exists() and not any(t.get('group','').startswith('#13 — curved') for t in traces):
        traces=list(traces)+json.loads(route_data.read_text())
    natural=STUDY/'red_priority_18/replays.json'
    if natural.exists() and not any(t.get('group','').startswith('#18 — natural') for t in traces):
        traces=list(traces)+json.loads(natural.read_text())
    combined=STUDY/'integrated/replays.json'
    if combined.exists() and not any(t.get('group','').startswith('ALL TOGETHER') for t in traces):
        traces=list(traces)+json.loads(combined.read_text())
    extra=STUDY/'console_19/replays.json'
    if extra.exists() and not any(t.get('params',{}).get('study_console_transfer') for t in traces):
        traces=list(traces)+json.loads(extra.read_text())
    spec=importlib.util.spec_from_file_location('viewer',REPO/'tools/make_mission_viewer_v2.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    # Convert non-finite diagnostic metrics to null for a portable JSON payload.
    def clean(x):
        if isinstance(x,float) and not np.isfinite(x):return None
        if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
        if isinstance(x,list):return [clean(v) for v in x]
        return x
    payload=json.dumps(clean(traces),separators=(',',':'),allow_nan=False)
    template=m.TEMPLATE.replace('/*__TRACES__*/',payload)
    template=template.replace('// 2. 1km Military Grid Lines', '''
    // Draw the entire street network, including the unused branch, below routes/buildings.
    if(T.street_graph){
      const nodes=new Map(T.street_graph.nodes.map(n=>[n.id,n]));
      T.street_graph.edges.forEach(e=>{
        const u=nodes.get(e.u),v=nodes.get(e.v);if(!u||!v)return;
        ctx.strokeStyle='#425264';ctx.lineWidth=Math.max(2,(e.width||8)*sc);
        ctx.beginPath();ctx.moveTo(X(u.x),Y(u.y));
        (e.geometry||[]).forEach(p=>ctx.lineTo(X(p[0]),Y(p[1])));
        ctx.lineTo(X(v.x),Y(v.y));ctx.stroke();
      });
      ctx.font='bold 11px sans-serif';
      nodes.forEach(n=>{ctx.fillStyle='#b9d5ed';ctx.beginPath();ctx.arc(X(n.x),Y(n.y),3,0,Math.PI*2);ctx.fill();ctx.fillText(String(n.id),X(n.x)+5,Y(n.y)-6);});
    }
    // 2. 1km Military Grid Lines''')
    template=template.replace('<button class="tp" id="labels"',
        '<button class="tp" id="zoom_in" title="Zoom in">Zoom +</button><button class="tp" id="zoom_out" title="Zoom out">Zoom −</button><button class="tp" id="zoom_reset" title="Fit whole map">Reset zoom</button><span id="zoom_level">1×</span><label>Follow vehicle <select id="follow_vehicle" aria-label="Follow vehicle" style="min-width:140px;max-width:250px"></select></label><span id="follow_state"></span><button class="tp" id="labels"')
    template=template.replace('let DW=1200, DH=520, PAD=24, sc=1, offX=0, offY=0;',
        'let followId=0, followTrace=null; let zoom=1, cameraX=null, cameraY=null; let DW=1200, DH=520, PAD=24, sc=1, offX=0, offY=0;')
    template=template.replace('function prep(idx){','function prep(idx){ followId=0; followTrace=null; zoom=1; cameraX=null; cameraY=null;')
    template=template.replace('offY = (DH - T.size[1]*sc) / 2;',
        '''offY = (DH - T.size[1]*sc) / 2;
    sc *= zoom;
    if(cameraX===null){cameraX=T.size[0]/2;cameraY=T.size[1]/2;}
    offX=DW/2-cameraX*sc; offY=DH/2-cameraY*sc;
    document.getElementById('zoom_level').textContent=zoom.toFixed(1)+'×';''')
    template=template.replace('ctx.clearRect(0,0,DW,DH);', '''
    const followPick=document.getElementById('follow_vehicle');
    if(followTrace!==T){
      followPick.replaceChildren();
      const free=document.createElement('option');free.value='-1';free.textContent='Free camera';followPick.appendChild(free);
      T.entities.forEach((e,i)=>{if(e.side!==BLUE)return;const o=document.createElement('option');o.value=String(i);o.textContent=`V${i+1} — ${e.convoy_role===0?'Control':e.convoy_role===2?'Escort':'Cargo'}`;followPick.appendChild(o);});
      if(!T.entities[followId] || T.entities[followId].side!==BLUE)followId=-1;
      followPick.value=String(followId);followTrace=T;
    }
    if(zoom>1 && followId>=0){
      const p=pos(followId,head);cameraX=p[0];cameraY=p[1];offX=DW/2-cameraX*sc;offY=DH/2-cameraY*sc;
      document.getElementById('follow_state').textContent=`Following V${followId+1}${f.alive[followId]?'':' (destroyed)'} · ${Math.round(cameraX)}, ${Math.round(cameraY)} m`;
    }else document.getElementById('follow_state').textContent=followId>=0?'Zoom in to follow':'Free camera';
    ctx.clearRect(0,0,DW,DH);''')
    template=template.replace('const ringsBtn=document.getElementById("rings");',
        '''function changeZoom(factor,px=DW/2,py=DH/2){
      if(!T)return;
      const wx=(px-offX)/sc, wy=(py-offY)/sc;
      const next=Math.min(32,Math.max(1,zoom*factor));
      const nextScale=sc*next/zoom;
      cameraX=wx-(px-DW/2)/nextScale;cameraY=wy-(py-DH/2)/nextScale;
      zoom=next;resize();
    }
    document.getElementById('zoom_in').onclick=()=>changeZoom(1.5);
    document.getElementById('zoom_out').onclick=()=>changeZoom(1/1.5);
    document.getElementById('zoom_reset').onclick=()=>{zoom=1;cameraX=null;cameraY=null;resize();};
    document.getElementById('follow_vehicle').onchange=e=>{followId=Number(e.target.value);draw();};
    cv.style.touchAction='none';cv.style.cursor='grab';
    cv.addEventListener('wheel',e=>{
      e.preventDefault();const r=cv.getBoundingClientRect();
      changeZoom(e.deltaY<0?1.2:1/1.2,(e.clientX-r.left)*DW/r.width,(e.clientY-r.top)*DH/r.height);
    },{passive:false});
    let mapDrag=null;
    cv.addEventListener('pointerdown',e=>{
      if(e.button!==0)return;
      mapDrag={x:e.clientX,y:e.clientY};cv.setPointerCapture(e.pointerId);cv.style.cursor='grabbing';
    });
    cv.addEventListener('pointermove',e=>{
      if(!mapDrag)return;const r=cv.getBoundingClientRect();
      if(e.clientX===mapDrag.x && e.clientY===mapDrag.y)return;
      followId=-1;document.getElementById('follow_vehicle').value='-1';
      cameraX-=(e.clientX-mapDrag.x)*DW/r.width/sc;
      cameraY-=(e.clientY-mapDrag.y)*DH/r.height/sc;
      mapDrag={x:e.clientX,y:e.clientY};offX=DW/2-cameraX*sc;offY=DH/2-cameraY*sc;draw();
    });
    const endMapDrag=()=>{mapDrag=null;cv.style.cursor='grab';};
    cv.addEventListener('pointerup',endMapDrag);cv.addEventListener('pointercancel',endMapDrag);
    const ringsBtn=document.getElementById("rings");''')
    template=template.replace('Phases 1-5 Integrated','Learning environment: #9 + #12 + #14 + #17 + #19')
    template=template.replace('<h3>Personnel & Autonomy (Issue #14)</h3>','<h3>Personnel — final run totals (#14)</h3>')
    template=template.replace('<div class="card" id="crew_card">',
        '<div class="card"><h3>Street visibility (#16) — live</h3><div id="live_urban"></div></div><div class="card"><h3>Route stationing (#13) — live</h3><div id="live_route"></div></div><div class="card"><h3>Live contact &amp; leadership (#12 / #17)</h3><div id="live_policy"></div></div><div class="card"><h3>Console service (#19) — live</h3><div id="live_console"></div></div><div class="card" id="crew_card">')
    # Let the existing animation publish its current frame to the new panel.
    template=template.replace('const s=series[fi], d=T._den, f=T.frames[fi];',
        '''const s=series[fi], d=T._den, f=T.frames[fi];
        const cv=T.params.convoy||{};
        document.getElementById('live_urban').textContent=f.urban ?
          `In-range sensor pairs: ${f.urban.sensor_pairs} | blocked by buildings: ${f.urban.blocked_pairs} | Red detected: ${f.urban.red_detected} | first Red detection: ${f.urban.first_red_detection===null?'none':f.urban.first_red_detection+'s'} | road path: ${(T.params.study_street_path||[]).join(' → ')}` : 'Not enabled in this replay';
        const ri=followId>=0?followId:0;
        document.getElementById('live_route').textContent=f.route_s ?
          `V${ri+1}: s = ${Number(f.route_s[ri]).toFixed(1)} m along route | cross-track = ${Number(f.route_cross[ri]).toFixed(2)} m | ${f.herringbone_active?'Herringbone: off-route parking intentional':'Cruise / rejoin'} | route length = ${T.params.study_route_length_m.toFixed(1)} m` : 'No route-stationing telemetry in this replay';
        const cs=f.console;
        document.getElementById('live_console').textContent=cs ?
          `Rule: ${cs.rule} | hosts: ${cs.hosts.map(i=>'V'+(i+1)).join(', ')} | available: ${cs.available.map(x=>x?'YES':'NO').join(', ')} | requests accepted for service: ${cs.serviced.join(', ')} | denied (host lost): ${cs.abandon.join(', ')} | leader restored: ${cs.leader_restored===null?'pending':cs.leader_restored+'s'} | console transferred: ${cs.console_restored===null?'pending / not transferred':cs.console_restored+'s'} | first new service after loss: ${cs.first_new_service===null?'none':cs.first_new_service+'s'}` : 'Not enabled in this replay';
        document.getElementById('live_policy').textContent=
          `Contact: ${T.params.study_herringbone?'EXPERIMENTAL HALT + HERRINGBONE':(cv.contact_reaction?cv.contact_reaction.action:'OFF')} | active: ${f.in_contact?'YES':'NO'} | hold commanded: ${(f.hold_command||f.holding||[]).reduce((a,b)=>a+b,0)} | held / parked: ${(f.holding||[]).reduce((a,b)=>a+b,0)} | heads (entity index): ${(f.ll_head||[]).join(', ')||'not recorded'} | handoffs: ${f.handoffs||0} | exposure so far: ${f.exposure===undefined?'not recorded':f.exposure} person-s`;
        ''')
    html='<!doctype html><html><head><meta charset="utf-8"><title>Convoy learning: escorts and leader loss</title></head><body>'+template+'</body></html>'
    (STUDY/'baseline_09_14/viewer.html').write_text(html)

if __name__=='__main__':main()
