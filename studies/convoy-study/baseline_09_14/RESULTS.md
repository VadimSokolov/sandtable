# Issues #9 + #14: controlled baseline

Means over seeds 0–39. Cargo in tons; exposure in person-seconds (dt = 1 s).

| Condition | Arm | Delivered | Lost | In transit | Exposure | Crew lost | Vehicles lost |
|---|---|---:|---:|---:|---:|---:|---:|
| no_threat | manned | 60.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| no_threat | reduced_crew | 60.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| threat | manned | 36.12 | 23.88 | 0.00 | 3901.85 | 12.50 | 6.25 |
| threat | reduced_crew | 36.12 | 23.88 | 0.00 | 685.15 | 2.95 | 6.25 |

Every run passed cargo balance and initial crew/cargo checks. No-threat runs delivered all 60 tons with no losses or exposure. Paired cargo and vehicle losses matched across allocations.

## Limits

- One synthetic scenario; no real-world calibration.
- Succession any is an idealized fixed assumption, including for uncrewed vehicles.
- No contact policy, special Red priority, per-unit console, lane blocking, or urban graph.
- Exposure is alive crew within eligible enemy weapon range, without LOS/detection requirement.
- A destroyed vehicle loses its entire crew in this model.
- Full-delivery goal differs from the original 50% stopping rule.
- No communication sweep; follow mode is local behavior in both arms.
