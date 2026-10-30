"""Verify saved curved-route diagnostics without rerunning missions."""
import json
import math
from pathlib import Path

HERE=Path(__file__).parent
data=json.loads((HERE/'results.json').read_text())
route=data['route']
length=sum(math.dist(a,b) for a,b in zip(route,route[1:]))
assert math.isclose(length,data['length_m'],abs_tol=1e-7)
assert length>math.dist(route[0],route[-1])
traces=json.loads((HERE/'replays.json').read_text())
for t in traces:
    assert t['outcome']['cargo_delivered']==60
    fs=t['frames']
    for a,b in zip(fs,fs[1:]):
        dt=b['t']-a['t']
        for i in range(18):
            assert math.hypot(b['x'][i]-a['x'][i],b['y'][i]-a['y'][i])<=12*dt+.04
    assert max(fs[-1]['route_cross'])<.1
    assert not any('FORCED' in e['event'] for e in t['events'])
clear=traces[0]['frames']
assert max(max(f['route_cross']) for f in clear if f['t']>=30)<.1
combat=traces[1]['frames']
assert any(f['herringbone_active'] for f in combat)
assert any(a['herringbone_active'] and not b['herringbone_active'] for a,b in zip(combat,combat[1:]))
assert max(max(f['route_cross']) for f in combat)>10
print('Arc length, centerline following, finite speed, halt/release, rejoin, cargo and no forced loss verified.')
