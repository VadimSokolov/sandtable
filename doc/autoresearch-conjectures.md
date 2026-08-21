# Autoresearch run `aug12`: conjecture ledger

Workflow 7, **mode I** (idea search). The loop proposes falsifiable claims about SandTable's
mechanics, tries to kill them numerically, and records a verdict. The scoreboard is a verdict per
conjecture, not a scalar.

Governed by `references/rules/autoresearch-integrity.md`. Contract in `.autoresearch/contract.json`;
full search trace in `results.tsv` (untracked). This file is the human-readable index.

## Measurement contract

| Item | Value |
| --- | --- |
| Metric | `success` (mission success rate), direction max |
| Unit of replication | a **block**: block *b* at *R* reps runs mission seeds *bR .. bR+R-1* and reports the block mean |
| Contract blocks | 0-31 |
| Proxy tier | 16 blocks x 16 reps = 256 missions/condition, about 10 s |
| Full tier | 32 blocks x 64 reps = 2048 missions/condition, about 78 s |
| Noise floor (full tier) | block sd 0.0599, se 0.0106, **MDE 0.0246** |
| Minimum practical effect | 0.03 (above MDE, so the gate can see what we claim to care about) |
| Frozen | `tools/ar_eval.py`, `scenarios/` |

Block sd is within Monte-Carlo error of the pure binomial value, so precision scales with total
missions per condition and nothing structural inflates it.

## Verdict key

`refuted` the numerical test killed it. `open` tested, not resolved, budget spent.
`supported` survived a falsification attempt at the full tier and cleared the gate.
A `supported` conjecture is a paper *candidate*, not a paper claim: it still owes ablation and the
promotion criteria in the integrity rule.

## Conjectures

| # | Conjecture | Status | Verdict |
| --- | --- | --- | --- |
| C1 | Under a Gilbert-Elliot channel calibrated to the **same mean drop rate** as the Bernoulli ladder, direct-control mission success differs, and the direct-vs-supervisory crossover rung moves. Mean drop rate is therefore not a sufficient statistic for choosing a control mode. | in progress | |
| C2 | The ladder's top rungs are not resolvable: C4 and C5 produce identical results because every direct-control request already times out at C4. The six-rung ladder has fewer than six distinguishable levels. | observed at proxy | |
| C3 | There is no direct-vs-supervisory crossover at the published span (n=6): supervisory dominates at every rung. The crossover exists only in a 2-D (span x rung) structure, so a 1-D ladder sweep understates the modality result. | observed at proxy | |
| C4 | Correcting teleoperation stop semantics (CR-2) moves the crossover toward cleaner links, because a severed-link teleoperated vehicle currently keeps driving at 54.5% speed. | queued | |
| C5 | A behaviour-based follower (on-platform dead reckoning) degrades less than a link-based follower as the ladder worsens, matching the sign of Cheung et al. 2022 at mission rather than path-error level. | queued (needs CR-1, CR-3) | |
| C6 | Network robustness (r-robustness) and algebraic connectivity rank the same formations differently, so a formation tuned for connectivity is not thereby robust. | queued (CR-8) | |

## Log

- **Setup.** Contract initialised at 24 blocks; noise reported MDE 0.0384 against MPE 0.03, so the
  design was resized to 32 blocks x 64 reps, giving MDE 0.0246. Recorded because the first sizing
  was not viable and that is part of the method.
- **CR-9 channel implemented.** Gilbert-Elliot chain calibrated so stationary drop rate equals the
  ladder value rung by rung; verified empirically at C1-C5 (max deviation 0.0012) with mean burst
  length 4.0 against Bernoulli's 1.05-2.22. Draws exactly one uniform per message, the same as the
  Bernoulli path, so the two channels stay stream-aligned and their comparison is paired. Default
  path byte-identical across all four scenarios.
