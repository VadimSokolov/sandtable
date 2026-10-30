"""Learning experiment: isolate crew allocation while keeping movement identical.

Run with the sandtable virtualenv Python. No repository files are modified.
"""
import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--seeds', type=int, default=40)
args = parser.parse_args()
if args.seeds < 1:
    parser.error('--seeds must be positive')
sys.path.insert(0, str(args.repo / 'src'))
from sandtable.scenario import Scenario
from sandtable.sim import run_mission

base = json.loads((args.repo / 'scenarios/uc3_convoy.json').read_text())
base['objective']['delivery_fraction'] = 1.0
base['params'] = {
    'route_bias': 0.0, 'formation_spread': 40.0, 'tempo': 1.0,
    'comms_level': 0, 'follow_mode': 'behavior', 'follow_topology': 'chain',
    'convoy': {
        'march_unit_size': 5, 'march_units_per_serial': 3, 'serials_per_column': 1,
        'pace': 10.0, 'time_gap': 4.0, 'cargo_per_vehicle': 5.0,
        'roles': ['control', 'cargo', 'cargo', 'cargo', 'cargo'],
        'succession': 'any',
    },
}
# Explicitly hold succession and following fixed: this is a crew-allocation
# diagnostic, not a human-driver model or an autonomy-performance comparison.
keys = ['cargo_loaded', 'cargo_delivered', 'cargo_lost', 'cargo_in_transit',
        'delivered_frac', 'crew_total', 'crew_lost', 'crew_steps_at_risk',
        'blue_losses', 'success']
raw, summary, scenarios = [], [], {}
for condition in ('no_threat', 'threat'):
    config = json.loads(json.dumps(base))
    if condition == 'no_threat':
        config['forces'] = [f for f in config['forces'] if f['side'] == 0]
    scenarios[condition] = config
    for arm, allocation in [('manned', 'manned'), ('reduced_crew', 'autonomous_march_unit')]:
        runs = []
        for seed in range(args.seeds):
            r = run_mission(Scenario.from_dict(config), seed=seed,
                            params={'autonomy_arm': allocation})
            assert abs(r['cargo_loaded'] - sum(r[k] for k in
                ('cargo_delivered', 'cargo_lost', 'cargo_in_transit'))) < 1e-6
            assert r['cargo_loaded'] == 60
            assert r['crew_total'] == (30 if arm == 'manned' else 6)
            if condition == 'no_threat':
                assert r['cargo_delivered'] == 60
                assert r['crew_lost'] == r['crew_steps_at_risk'] == r['blue_losses'] == 0
            row = {'condition': condition, 'arm': arm, 'seed': seed,
                   **{k: float(r[k]) for k in keys}}
            # Common force baseline vs deployed-personnel denominator: distinct questions.
            row['crew_lost_fraction_original_30'] = r['crew_lost'] / 30
            row['crew_lost_fraction_deployed'] = r['crew_lost'] / r['crew_total']
            row['crew_seconds_at_risk'] = r['crew_steps_at_risk'] * config['dt']
            raw.append(row)
            runs.append(row)
        summary.append({'condition': condition, 'arm': arm, 'n': len(runs),
                        **{k: statistics.mean(r[k] for r in runs) for k in runs[0]
                           if k not in ('condition', 'arm', 'seed')}})
        print(condition, arm, {k: round(summary[-1][k], 3) for k in
              ('cargo_delivered', 'cargo_lost', 'cargo_in_transit',
               'crew_steps_at_risk', 'crew_lost', 'blue_losses')}, flush=True)

# Crew labels must not alter paths/combat under this deliberately fixed policy.
for condition in ('no_threat', 'threat'):
    for seed in range(args.seeds):
        a, b = [r for r in raw if r['condition'] == condition and r['seed'] == seed]
        for k in ('cargo_delivered', 'cargo_lost', 'cargo_in_transit', 'blue_losses', 'success'):
            assert a[k] == b[k], (condition, seed, k, a[k], b[k])

digest = hashlib.sha256()
for p in sorted((args.repo / 'src/sandtable').rglob('*.py')):
    digest.update(str(p.relative_to(args.repo)).encode())
    digest.update(p.read_bytes())
revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=args.repo,
                          capture_output=True, text=True, check=True).stdout.strip()
output = {'purpose': 'Crew-allocation diagnostic; same local following and succession in both arms',
          'source_revision': revision, 'source_python_sha256': digest.hexdigest(),
          'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'seeds': list(range(args.seeds)), 'scenarios': scenarios,
          'summary': summary, 'runs': raw,
          'limits': ['One synthetic scenario; no real-world calibration.',
                     'Succession any is an idealized fixed assumption, including for uncrewed vehicles.',
                     'No contact policy, special Red priority, per-unit console, lane blocking, or urban graph.',
                     'Exposure is alive crew within eligible enemy weapon range, without LOS/detection requirement.',
                     'A destroyed vehicle loses its entire crew in this model.',
                     'Full-delivery goal differs from the original 50% stopping rule.',
                     'No communication sweep; follow mode is local behavior in both arms.']}
(HERE / 'results.json').write_text(json.dumps(output, indent=2, allow_nan=False))
lines = ['# Issues #9 + #14: controlled baseline', '',
         'Means over seeds 0–%d. Cargo in tons; exposure in person-seconds (dt = 1 s).' % (args.seeds-1), '',
         '| Condition | Arm | Delivered | Lost | In transit | Exposure | Crew lost | Vehicles lost |',
         '|---|---|---:|---:|---:|---:|---:|---:|']
for r in summary:
    lines.append('| %s | %s | %s |' % (r['condition'], r['arm'], ' | '.join(
        f'{r[k]:.2f}' for k in ('cargo_delivered', 'cargo_lost', 'cargo_in_transit',
                               'crew_steps_at_risk', 'crew_lost', 'blue_losses'))))
lines += ['', 'Every run passed cargo balance and initial crew/cargo checks. No-threat runs delivered all 60 tons with no losses or exposure. Paired cargo and vehicle losses matched across allocations.',
          '', '## Limits', '', *['- '+x for x in output['limits']]]
(HERE / 'RESULTS.md').write_text('\n'.join(lines)+'\n')
