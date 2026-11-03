"""Regression checks against the generated Herringbone teaching traces."""
import json
import math
from pathlib import Path

traces = json.loads((Path(__file__).parent / 'replays.json').read_text())[-2:]
for trace in traces:
    frames = trace['frames']
    stable = 0
    for i, entity in enumerate(trace['entities']):
        if entity['side'] != 0:
            continue
        turns = [(b['h'][i] - a['h'][i] + math.pi) % (2 * math.pi) - math.pi
                 for a, b in zip(frames, frames[1:])]
        # The observed orbit advanced about 0.6 rad/tick for a full revolution.
        assert all(abs(sum(turns[j:j+12])) < 2 * math.pi
                   for j in range(len(turns)-12)), (trace['label'], i)
        for a, b in zip(frames, frames[1:]):
            dt = b['t'] - a['t']
            distance = math.hypot(b['x'][i]-a['x'][i], b['y'][i]-a['y'][i])
            assert distance <= 12 * dt + .03
            if (a['herringbone_parked'][i] and b['herringbone_parked'][i]
                    and abs(abs(a['h'][i]) - math.pi/4) < .002):
                assert abs(b['h'][i] - a['h'][i]) < .002
                assert distance < .02
                stable += 1
    assert stable > 0
    assert trace['outcome']['cargo_delivered'] == 60
    print(trace['label'], ': no sustained orbit, stable parking, finite speed, 60 tons delivered')
