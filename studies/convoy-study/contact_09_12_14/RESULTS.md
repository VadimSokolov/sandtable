# Contact reaction: #9 + #12 + #14

40 seeds, 0–39. Same convoy, no added escorts, local chain following, succession any, C0, full-delivery goal.

| Crew | Action | Delivered tons | Lost tons | In transit tons | Exposure person-s | Crew lost | Vehicles lost | Held vehicle-s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| manned | continue | 36.12 | 23.88 | 0.00 | 3901.85 | 12.50 | 6.25 | 0.00 |
| reduced_crew | continue | 36.12 | 23.88 | 0.00 | 685.15 | 2.95 | 6.25 | 0.00 |
| manned | halt | 51.75 | 8.25 | 0.00 | 843.55 | 5.30 | 2.65 | 6676.88 |
| reduced_crew | halt | 51.75 | 8.25 | 0.00 | 356.40 | 2.00 | 2.65 | 6676.88 |

Halt duration is cumulative vehicle-steps; dt=1 second. Ten vehicles held for ten seconds count as 100 vehicle-seconds, not 100 seconds of mission delay.
Trigger: incoming fire in the previous tick, not just a successful hit. Release: 15 seconds without a new trigger. Shooting continues while movement is held.
No special additional enemy penalty for halting is modelled. This is one synthetic scenario and does not establish a real-world preferred policy.
The original four viewer options remain. New options 5–8 show seed 0, not these averages. Live contact and holding status come from the actual mission loop.
Checks: per-run cargo balance; continue matches original no-reaction runs on key outcomes; same-policy crew comparisons match cargo/vehicle outcomes; all replay final metrics match seed-0 runs.
