"""Extend the learning viewer with contact continue/halt; no sandtable edits."""
import copy
import hashlib
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'baseline_09_14'
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
from sandtable.scenario import Scenario
from sandtable.sim import run_mission
from sandtable import behavior, metrics

baseline = json.loads((BASE / 'results.json').read_text())
old_traces = json.loads((BASE / 'replays.json').read_text())
traces, raw, summaries, configs = copy.deepcopy(old_traces), [], [], {}
keys = ['cargo_loaded', 'cargo_delivered', 'cargo_lost', 'cargo_in_transit',
        'crew_total', 'crew_lost', 'crew_steps_at_risk', 'blue_losses',
        'red_losses', 'mission_time', 'success', 'convoy_contact_count',
        'convoy_contact_steps', 'convoy_halt_steps', 'convoy_first_contact_step']

def record_actual(config, arm):
    """Observe the actual mission loop without RNG draws or state mutations."""
    frames, state = [], {}
    original_step, original_risk = behavior.step, metrics.accumulate_crew_at_risk
    def snapshot(ent, t):
        b = state['behavior']
        frames.append({'t': t, 'x': ent.x.round(1).tolist(), 'y': ent.y.round(1).tolist(),
            'h': ent.heading.round(2).tolist(), 'alive': ent.alive.astype(int).tolist(),
            'seen': ent.seen.astype(int).tolist(), 'cq': ent.control_quality.round(2).tolist(),
            'kills': [], 'cargo_delivered': ent.cargo_delivered.tolist(),
            'crew_alive': (ent.crew * ent.alive).astype(int).tolist(),
            'holding': b.holding.astype(int).tolist(), 'in_contact': bool(b.in_contact),
            'exposure': float(state.get('risk', 0))})
    def step(ent, bhv, *args, **kwargs):
        state['behavior'] = bhv
        state['ent'] = ent
        k = args[3]  # op, comms, scenario, k, rng
        state['t'] = (k + 1) * config['dt']
        if not frames:
            snapshot(ent, 0.0)
        original_step(ent, bhv, *args, **kwargs)
    def risk(ent, acc):
        original_risk(ent, acc)
        state['risk'] = acc.sum()
        # Record every tick, so first contact and release remain visible.
        snapshot(ent, state['t'])
    with patch.object(behavior, 'step', step), patch.object(metrics, 'accumulate_crew_at_risk', risk):
        result = run_mission(Scenario.from_dict(config), seed=0)
    snapshot(state['ent'], state['t'])
    template = copy.deepcopy(next(t for t in old_traces if
                                 ('Threat — Manned' if arm == 'manned' else 'Threat — Reduced') in t['label']))
    template.update(frames=frames, params=config['params'], outcome=result,
                    seed=0, total_cargo=60)
    template['outcome']['cargo_total'] = 60
    return template, result

for action in ('continue', 'halt'):
    for arm, allocation in [('manned', 'manned'), ('reduced_crew', 'autonomous_march_unit')]:
        cfg = copy.deepcopy(baseline['scenarios']['threat'])
        cfg['params']['convoy'].update(autonomy_arm=allocation,
            contact_reaction={'action': action, 'triggers': ['receive_fire'],
                              'halt_scope': 'all', 'release': {'rule': 'timeout', 'clear_s': 15.0}})
        label = f'{arm}_{action}'
        configs[label] = cfg
        runs = []
        for seed in range(40):
            r = run_mission(Scenario.from_dict(cfg), seed=seed)
            assert abs(r['cargo_loaded'] - sum(r[k] for k in
                       ('cargo_delivered', 'cargo_lost', 'cargo_in_transit'))) < 1e-6
            assert r['cargo_loaded'] == 60
            assert r['crew_total'] == (30 if arm == 'manned' else 6)
            if action == 'continue':
                expected = next(x for x in baseline['runs'] if x['condition'] == 'threat'
                                and x['arm'] == arm and x['seed'] == seed)
                for k in ('cargo_delivered', 'crew_lost', 'crew_steps_at_risk', 'blue_losses'):
                    assert r[k] == expected[k], (label, seed, k)
                assert r['convoy_halt_steps'] == 0
            row = {'arm': arm, 'action': action, 'seed': seed, **{k: r[k] for k in keys}}
            runs.append(row); raw.append(row)
        summary = {'arm': arm, 'action': action, 'n': 40,
                   **{k: statistics.mean(r[k] for r in runs) for k in keys}}
        summaries.append(summary)
        print(label, {k: round(summary[k], 3) for k in
              ('cargo_delivered', 'crew_steps_at_risk', 'blue_losses', 'convoy_halt_steps')}, flush=True)
        trace, result = record_actual(cfg, arm)
        for k in keys:
            assert result[k] == runs[0][k], (label, k)
        trace['group'] = 'Issues #9 + #12 + #14 — contact reaction'
        trace['label'] = f'{len(traces)+1}. Threat — {"Manned (30 people)" if arm=="manned" else "Reduced crew (6 people)"} — {action.upper()}'
        trace['desc'] = 'Actual mission loop, seed 0. Receive-fire trigger; all vehicles halt; release after 15 seconds without a new trigger. No added escorts. Personnel summary is final; contact status below is live.'
        traces.append(trace)

# Check that crew allocation remains isolated inside each policy.
for action in ('continue', 'halt'):
    for seed in range(40):
        a, b = [r for r in raw if r['action'] == action and r['seed'] == seed]
        for k in ('cargo_delivered', 'cargo_lost', 'cargo_in_transit', 'blue_losses', 'convoy_halt_steps'):
            assert a[k] == b[k], (action, seed, k)

spec = importlib.util.spec_from_file_location('existing_viewer', REPO / 'tools/make_mission_viewer_v2.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
template = module.TEMPLATE.replace('/*__TRACES__*/', json.dumps(traces, separators=(',', ':')))
template = template.replace('<h3>Personnel & Autonomy (Issue #14)</h3>',
                            '<h3>Personnel — final run totals (#14)</h3>')
template = template.replace('<div class="card" id="crew_card">',
    '<div class="card"><h3>Contact reaction (#12) — live</h3><div id="contact_live">--</div></div><div class="card" id="crew_card">')
template = template.replace('const fi = frameAt(head), f = T.frames[fi];',
    'const fi = frameAt(head), f = T.frames[fi];')
# Independent UI listener reads the same timeline and selected trace, never changes physics.
extra = '''<script>
const contactTraces=PAYLOAD;
function showContact(){
 const tr=contactTraces[Number(document.getElementById('pick').value)||0];
 const percent=Number(document.getElementById('seek').value);
 const f=tr.frames[Math.min(tr.frames.length-1,Math.floor(percent/100*(tr.frames.length-1)))];
 const rx=tr.params.convoy.contact_reaction;
 document.getElementById('contact_live').textContent=rx ?
 `${rx.action.toUpperCase()} | T+${f.t}s | contact: ${f.in_contact?'YES':'NO'} | held: ${(f.holding||[]).reduce((a,b)=>a+b,0)} vehicles | exposure so far: ${f.exposure||0} person-seconds`:
 'Baseline: contact policy OFF';
 requestAnimationFrame(showContact);
} showContact();
</script>'''.replace('PAYLOAD', json.dumps(traces, separators=(',', ':')))
html = '<!doctype html><html><head><meta charset="utf-8"><title>Convoy learning — cargo, crew and contact</title></head><body>'+template+extra+'</body></html>'
# Keep the same URL and all four previous options; store new records separately.
(BASE / 'viewer.html').write_text(html)
(HERE / 'replays.json').write_text(json.dumps(traces[4:], allow_nan=True))
digest = hashlib.sha256()
for p in sorted((REPO / 'src/sandtable').rglob('*.py')):
    digest.update(str(p.relative_to(REPO)).encode()); digest.update(p.read_bytes())
(HERE / 'results.json').write_text(json.dumps({'scenarios': configs, 'seeds': list(range(40)),
    'source_python_sha256': digest.hexdigest(), 'runs': raw, 'summary': summaries}, indent=2))
lines = ['# Contact reaction: #9 + #12 + #14', '',
 '40 seeds, 0–39. Same convoy, no added escorts, local chain following, succession any, C0, full-delivery goal.', '',
 '| Crew | Action | Delivered tons | Lost tons | In transit tons | Exposure person-s | Crew lost | Vehicles lost | Held vehicle-s |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|']
for s in summaries:
    lines.append('| '+s['arm']+' | '+s['action']+' | '+' | '.join(f'{s[k]:.2f}' for k in
        ('cargo_delivered','cargo_lost','cargo_in_transit','crew_steps_at_risk','crew_lost','blue_losses','convoy_halt_steps'))+' |')
lines += ['', 'Halt duration is cumulative vehicle-steps; dt=1 second. Ten vehicles held for ten seconds count as 100 vehicle-seconds, not 100 seconds of mission delay.',
 'Trigger: incoming fire in the previous tick, not just a successful hit. Release: 15 seconds without a new trigger. Shooting continues while movement is held.',
 'No special additional enemy penalty for halting is modelled. This is one synthetic scenario and does not establish a real-world preferred policy.',
 'The original four viewer options remain. New options 5–8 show seed 0, not these averages. Live contact and holding status come from the actual mission loop.',
 'Checks: per-run cargo balance; continue matches original no-reaction runs on key outcomes; same-policy crew comparisons match cargo/vehicle outcomes; all replay final metrics match seed-0 runs.']
(HERE / 'RESULTS.md').write_text('\n'.join(lines)+'\n')
print('Updated viewer with all 8 options; original data retained.', flush=True)
