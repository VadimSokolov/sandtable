# Dedicated escorts and leader-loss diagnostics

Single seed 0 teaching runs. Not 40-seed averages.

| Run | Delivered t | In transit t | Crew lost | Vehicle lost | Handoffs | Leaderless unit-steps |
|---|---:|---:|---:|---:|---:|---:|
| Escorts / manned / contact CONTINUE | 60.0 | 0.0 | 2.0 | 1.0 | — | — |
| Escorts / reduced_crew / contact CONTINUE | 60.0 | 0.0 | 2.0 | 1.0 | — | — |
| Escorts / manned / contact HALT | 60.0 | 0.0 | 2.0 | 1.0 | — | — |
| Escorts / reduced_crew / contact HALT | 60.0 | 0.0 | 2.0 | 1.0 | — | — |
| No loss control / manned | 60.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Forced loss / manned / CONTINUE | 60.0 | 0.0 | 2.0 | 1.0 | 0.0 | 447.0 |
| Forced loss / manned / PROMOTE / delay 0s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 0.0 |
| Forced loss / manned / PROMOTE / delay 5s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 5.0 |
| Forced loss / manned / ABSORB / delay 5s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 5.0 |
| Forced loss / manned / HALT | 40.0 | 20.0 | 2.0 | 1.0 | 0.0 | 1650.0 |
| Forced loss / manned / HALT / release 30s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 29.0 |
| No loss control / reduced_crew | 60.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Forced loss / reduced_crew / CONTINUE | 60.0 | 0.0 | 2.0 | 1.0 | 0.0 | 447.0 |
| Forced loss / reduced_crew / PROMOTE / delay 0s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 0.0 |
| Forced loss / reduced_crew / PROMOTE / delay 5s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 5.0 |
| Forced loss / reduced_crew / ABSORB / delay 5s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 5.0 |
| Forced loss / reduced_crew / HALT | 40.0 | 20.0 | 2.0 | 1.0 | 0.0 | 1650.0 |
| Forced loss / reduced_crew / HALT / release 30s | 60.0 | 0.0 | 2.0 | 1.0 | 1.0 | 29.0 |
| EXPERIMENTAL HALT + HERRINGBONE / escorts / manned | 60.0 | 0.0 | 5.0 | 2.0 | — | — |
| EXPERIMENTAL HALT + HERRINGBONE / escorts / reduced_crew | 60.0 | 0.0 | 5.0 | 2.0 | — | — |

## Assumptions and limits

- 3 escorts are added, not substituted for cargo: 18 vehicles, 60 tons. Manned crew 39; reduced crew 15. Each escort has 3 people.
- The gun-truck kill-probability parameter 0.01 is a placeholder, not a calibrated real-world value.
- Escorts are placed immediately after each control vehicle by the existing layout; not a front-and-rear deployment.
- Natural engagement: receive-fire trigger, 15 seconds clear before release; non-security vehicles halt, escorts remain mobile.
- Leader-loss diagnostics: no enemy, forced destruction of first control at time 150 seconds. No contact reaction is enabled in these diagnostics.
- Succession is manned_only: the armed, crewed escort is eligible to succeed the control. No console/C2 transfer model is enabled.
- Continue sends survivors onward independently; promote selects a crewed successor; absorb logically joins another living unit; halt holds the affected unit until release if configured.
- Handoff delay is policy latency, not necessarily stationary time. Promotion/absorption do not automatically stop movement during that delay.
- Absorb is experimental logical reassignment, not a validated formation manoeuvre.
- Herringbone is NOT implemented by sandtable; disperse explicitly raises NotImplementedError. These escort/halt runs must not be labelled Herringbone.
- Two separately labelled HERRINGBONE options use a local study adapter: real finite-speed movement to alternating 20 m side stations, then park outward. This is not the core disperse implementation and does not complete production #12.
- Herringbone uses contact halt with halt_scope=all. During the halt command the adapter first moves to side stations, then parks. Core convoy_halt_steps counts commanded hold, including manoeuvre time; study_parked_vehicle_steps counts actual parking separately.
- Original eight options and their datasets are retained. New results use one seed and are not comparable as statistical averages to the prior 40-seed report.
- Checks: cargo conservation, crew/escort counts, forced head loss and personnel accounting, recovery handoffs, permanent-halt stranded cargo, no-loss control, and zero halt steps under continue.
