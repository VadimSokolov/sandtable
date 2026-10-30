# #15 — Settings comparison

Run from the repository root:

```sh
PYTHONPATH=src python studies/convoy-study/sweep_15/run.py
python tools/convoy_study.py build
python tools/convoy_study.py serve --port 8766
```

Open `http://127.0.0.1:8766/convoy_sweep.html` for the comparison or `convoy_study.html` for replay options 48–56. All earlier options remain. Results and replays are generated locally; the frozen design is versioned. Re-running refuses source/design drift. Preserve a historical design rather than overwriting it to disguise a changed experiment.

## Fixed conditions

User sketch, direct route, 18 Blue vehicles, 60 tonnes, 15 crew, four Red sites. Natural control-first engagement, Herringbone halt, leader promotion, console transfer. No forced kills, lane blockage, adaptive rerouting or factorial interaction estimation. Experimental geometry and C2 assumptions from the earlier study remain.

## Design

Nine arms, seeds 0–9. Baseline: speed 10 m/s, time gap 4 s, spacing 40 m, communications C0. Individually vary speed to 8/12; gap to 6/8; spacing to 20/60; comms to C2/C5. Each replay is seed 0, never a selected representative run.

Spacing affects initial laydown and the minimum follower-gap floor. Behavior following stays active; comms affects console requests, not link-following latency. C2 has 2 s one-way delay / 10% drop; C5 has 16 s / 55% drop. C5's nominal round trip exceeds the 20 s patience. Exempt crewed vehicles retain quality 1 under current rules. This is not calibrated human workload or a validated real-world policy comparison.

## Calculation

For each metric: mean = sum of ten results / 10; SE = sample SD / sqrt(10). For paired differences, subtract the baseline result with the same seed, average ten differences, and use mean difference ± t(0.975,9) × SE(differences). Intervals are exploratory, unadjusted, and not evidence of equivalence. Shared seeds may cease to share request streams after paths diverge.

Cargo is checked: loaded = delivered + lost + in transit. Exposure is crew-steps, dt=1 s. Serviced fraction measures accepted/scheduled requests, not all confirmed reply deliveries. Capped completion time is mission time for successes, otherwise the 1800 s horizon; it is not average arrival time.

The design and Python source digests are frozen before this sweep, after earlier scenario exploration. This is a reproducible exploratory comparison, not a blinded preregistered confirmatory experiment. No optimization or best-arm selection is performed.

The speed column is the commanded convoy pace, not a measured achieved speed; quality, contact and following can slow vehicles. The time gap is a following target with a spacing floor, not a guaranteed separation at every instant.

Execution note: the first 90-run launch completed simulation but failed before saving results because undefined auxiliary metrics contained NaN. `design_initial.json` preserves its frozen design. The revised runner encodes undefined auxiliary values as null, requires all primary metrics to be finite, and saves per-run progress. The same settings/seeds were rerun under a new source digest; no scenario or analysis choices were tuned from the unsaved results.

## Observed results (10 seeds, this fixed scenario)

Baseline delivered 26.5 ± 8.53 tonnes (mean ± SE). Every non-baseline paired cargo-delivery 95% interval includes zero; no best setting is established. C2 accepted-service fraction averaged 0.767 at C0, 0.547 at C2 and 0 at C5. The latter is interpreted under the configured latency/patience relationship, not as a universal C5 outcome. Improved cargo means under degraded comms do not establish a communications benefit: trajectories, exposure and engagement change, with broad cargo intervals.

Validation: 90 unique arm/seed results; cargo conservation in each; nine seed-0 natural-combat replays; capture on/off matched on primary metrics; all 47 earlier option labels preserved within the 56-option viewer; 84 focused core tests passed.
