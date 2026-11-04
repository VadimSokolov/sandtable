# Saved integrated study results

Job: `fdecba4790794210b706f0596c7f8018` · 240 completed runs · seeds 0–19 in each scenario.

All scenarios use 10,800 kg initial cargo, capacity 907.18474 kg/truck and 15 people. These are model results on one map, not operational recommendations.

| Scenario | Core/unit | Response | Comms | Delivered kg | Exposure crew-steps | Crew lost | Vehicle losses | Cargo success | Head-loss runs | Mean console transfers |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| S1 | 5 | continue | C0 | 10755.00 | 1853.15 | 3.20 | 1.55 | 95.0% | 15/20 | 1.25 |
| S2 | 5 | halt | C0 | 5445.00 | 2851.35 | 10.05 | 7.90 | 20.0% | 20/20 | 2.40 |
| S3 | 5 | herringbone | C0 | 6300.00 | 4348.75 | 9.50 | 6.10 | 25.0% | 20/20 | 2.35 |
| S4 | 5 | continue | C3 | 10260.00 | 1814.75 | 3.80 | 2.30 | 85.0% | 15/20 | 1.30 |
| S5 | 5 | halt | C3 | 6300.00 | 4092.50 | 10.55 | 7.70 | 45.0% | 20/20 | 2.40 |
| S6 | 5 | herringbone | C3 | 7020.00 | 3242.80 | 9.40 | 6.05 | 60.0% | 20/20 | 2.30 |
| S7 | 7 | continue | C0 | 10740.00 | 1697.50 | 4.25 | 2.05 | 90.0% | 17/20 | 1.60 |
| S8 | 7 | halt | C0 | 6180.00 | 2816.75 | 9.90 | 8.10 | 20.0% | 20/20 | 2.30 |
| S9 | 7 | herringbone | C0 | 6030.00 | 2918.25 | 8.55 | 5.75 | 40.0% | 20/20 | 2.10 |
| S10 | 7 | continue | C3 | 10350.00 | 1720.70 | 4.25 | 2.70 | 70.0% | 17/20 | 1.50 |
| S11 | 7 | halt | C3 | 5130.00 | 2442.05 | 10.70 | 8.15 | 30.0% | 20/20 | 2.45 |
| S12 | 7 | herringbone | C3 | 7950.00 | 2540.20 | 7.70 | 4.70 | 60.0% | 20/20 | 2.05 |

## Interactions: response × communications

Per-seed contrast: (response − Continue under C3) − (response − Continue under C0). These exploratory 95% Student t intervals are unadjusted for multiple comparisons. Seed pairing does not preserve matched trajectories after divergence.

| Core/unit | Response | Metric | Mean contrast | 95% t interval |
|---|---|---|---:|---|
| 5 | halt | cargo_delivered | 1.3500 | [-2.2018, 4.9018] |
| 5 | halt | crew_steps_at_risk | 1279.5500 | [-95.2563, 2654.3563] |
| 5 | halt | blue_losses | -0.9500 | [-4.9888, 3.0888] |
| 5 | herringbone | cargo_delivered | 1.2150 | [-1.6687, 4.0987] |
| 5 | herringbone | crew_steps_at_risk | -1067.5500 | [-2758.4164, 623.3164] |
| 5 | herringbone | blue_losses | -0.8000 | [-4.0659, 2.4659] |
| 7 | halt | cargo_delivered | -0.6600 | [-3.7987, 2.4787] |
| 7 | halt | crew_steps_at_risk | -397.9000 | [-1387.9405, 592.1405] |
| 7 | halt | blue_losses | -0.6000 | [-4.7678, 3.5678] |
| 7 | herringbone | cargo_delivered | 2.3100 | [-0.8739, 5.4939] |
| 7 | herringbone | crew_steps_at_risk | -401.2500 | [-1438.1881, 635.6881] |
| 7 | herringbone | blue_losses | -1.7000 | [-4.5411, 1.1411] |

## Reproduction and verification

Design hash: `f4baf52d5af979a3637ebb6f21729d1f3709e5e0ce3d22ab17aad3b7972d8ced`.
Source hash: `7743fb354094bc45c8872e84f688087d55a1fa0c77a10e23b34968f86852354c`.

Audited all 240 artifacts and 82,326 frames for cargo conservation, final snapshot accounting, configuration hashes and common map/route. S7 seed 19 was rerun: frames, events and outcomes were identical.

Full per-run outcomes, descriptive uncertainty, successful-run-only delivery times and mechanism diagnostics are in the viewer and saved result JSON. The local job directory is `../../data/fdecba4790794210b706f0596c7f8018/`.

No overall ranking is inferred. Increasing core size redistributes cargo and changes convoy geometry as well as attention load. Herringbone and console transfer are experimental; unimplemented #18 mechanisms remain excluded.

All reported response × comms interaction intervals in this study include zero. That does not establish equivalence or prove that interactions are absent. Descriptive t intervals are not clipped to physical outcome bounds and can extend above the maximum loaded cargo.
