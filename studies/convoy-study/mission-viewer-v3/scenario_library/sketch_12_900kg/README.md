# Your sketch — twelve integrated scenarios

This is the agreed full factorial: 2 core-unit sizes × 3 contact responses × 2 communication levels. Each scenario has 20 seeds (0–19): 240 real Python missions. The immutable input design and hashes are in `manifest.json`; individual editable inputs are in `configs/S1.json` through `configs/S12.json`.

| ID | Core/unit | Total vehicles | Cargo trucks | Payload/truck (kg) | Response | Comms |
|---|---:|---:|---:|---:|---|---|
| S1 | 5 | 18 | 12 | 900 | Continue | C0 |
| S2 | 5 | 18 | 12 | 900 | Halt | C0 |
| S3 | 5 | 18 | 12 | 900 | Halt + experimental Herringbone | C0 |
| S4 | 5 | 18 | 12 | 900 | Continue | C3 |
| S5 | 5 | 18 | 12 | 900 | Halt | C3 |
| S6 | 5 | 18 | 12 | 900 | Halt + experimental Herringbone | C3 |
| S7 | 7 | 24 | 18 | 600 | Continue | C0 |
| S8 | 7 | 24 | 18 | 600 | Halt | C0 |
| S9 | 7 | 24 | 18 | 600 | Halt + experimental Herringbone | C0 |
| S10 | 7 | 24 | 18 | 600 | Continue | C3 |
| S11 | 7 | 24 | 18 | 600 | Halt | C3 |
| S12 | 7 | 24 | 18 | 600 | Halt + experimental Herringbone | C3 |

## Fixed inputs

- Capacity per cargo truck: **907.18474 kg**, one short ton. Actual load is 900 or 600 kg, not the capacity rating. Every scenario loads **10,800 kg**, or **10.8 metric tonnes**.
- Three march units in one serial; three additional escorts. Supervised cargo with zero onboard crew; controls have two people, escorts three: **15 people** in every scenario.
- Exact original Your sketch geometry and four Red sites; fixed manual lower-loop route. No threat-responsive rerouting.
- Pace 10 m/s, max speed 12 m/s, time gap 4 s, minimum centre gap 40 m, fixed lead staging offset 1,400 m.
- Red control-first selection; weapon range 1,000 m, sensor range 2,000 m and base damage parameter 0.008. No forced loss.
- Promote after five steps, crewed successors only; experimental successor-console transfer after twenty seconds. Span capacity four, service rate 0.5, decision interval thirty steps and patience twenty. Contact timeout fifteen seconds. Herringbone offset twenty metres.
- Horizon 1,800 s, dt=1 s, delivery target 100%. Radio levels and response differ exactly as the table states.

## Viewer

Open http://127.0.0.1:8767/#library → **Saved scenarios**. Choose scenario, saved execution and seed. You can load an input as a draft, preview the map, download JSON or watch the seed's recorded mission in Run & inspect. A saved replay starts at t=0; its explicit final record remains separate.

The library shows n/20 and provisional means while the job runs. Only the complete 240-run result has full uncertainty and interaction summaries. Completed artifacts remain replayable if a job is cancelled; a partial job is never labelled complete. A new execution gets a new UUID and preserves older executions. The general one-factor Compare runs feature retains its original 60-run limit; this fixed declared study has a separate 240-run executor with four isolated simulation processes.

## Reading the results

Report cargo delivered/lost/in-transit, cargo success, crew exposure/losses, vehicle losses, leadership handoffs and console service/transfer. Record how many runs actually had contact or leader loss: configuring a policy does not imply it fired. Conditional full-delivery times include successful runs only; ordinary run duration also includes failures and horizon-limited runs.

Response × comms interaction is calculated **per seed** as:

`(response − Continue under C3) − (response − Continue under C0)`

Do this separately for core sizes five and seven, and for Halt and Herringbone. Saved summaries include descriptive 95% Student t intervals. These are exploratory and unadjusted for multiple comparisons. Matched seeds need not preserve matched random paths after divergence. Increasing core size also redistributes cargo and lengthens the formation; differences are effects of that configuration package, not pure attention effects.

This integrates the implemented concepts from #9–#19. It does not complete unresolved issue requirements: Herringbone and console transfer are experimental; #18 supplies control-first selection here, without lane blocking, the Red halt cost or a calibrated ambush reconstruction. No overall policy ranking is implied.
