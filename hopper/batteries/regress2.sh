# CR-62 CONTINUED. P5 AND P6 ONLY, SPLIT OUT AFTER JOB 9450238 TIMED OUT PART-WAY INTO P5.
#
# P1 to P4 completed in 9450238 and are read from that log. This battery reruns P5 from the
# start (its answer_rate_iqr section was cut mid-write) and adds P6, which never ran.
#
# Registered in doc/autoresearch-conjectures.md under CR-62, before this ran. M4 of the `capped`
# battery priced the throughput gain in abandonment but could not say who abandons, because
# `starved_frac` is saturated at its floor (instrument defect 13). `answer_rate_min` and
# `answer_rate_gap` are the replacements and this is their first battery.
#
# The mechanism is in the admission test itself: `start + b*svc + lat <= deadline`. Latency is a
# scalar so it cannot sort vehicles; `deadline` comes from `patience_v` and can. Raising b shrinks
# the slack fastest for the smallest deadline, so the offset should sort refusals onto the
# impatient vehicles WITHOUT containing any per-vehicle term. `admit_response=aimd` is the second
# key, and it is feedback rather than a static sort.
#
#   G1  uniform fleet, AIMD off: the gap must NOT grow with b. Falsified if it gates up.
#   G2  dispersed fleet: the gap gates up with b and the min falls by more than the mean.
#   G3  AIMD grows the gap more than dispersion does.
#   G4  at matched b the two fleets are EQUIVALENT on served_per_step and answer_rate_v while
#       separating on answer_rate_gap. This is the finding; the rest is mechanism.
#   G5  the mission end, registered with equivalence as the expected outcome.
#   G9  at a MATCHED fleet mean, length selection compresses answer_rate_iqr and tightness does
#       not. cap7 vs b100: IQR gates down, mean equivalent. rand60 reaches a similar IQR only by
#       gating down on the mean too. This supersedes G6 and G7, whose verdicts are still reported.
#   G10 the stratification needs dispersed deadlines to exist: the uniform fleet's IQR is small and
#       no admission rule moves it much. uniPlain and uniCap7 in P4 are that control.
#   G11 `starved_frac` was NOT saturated, it was reporting a true zero in a uniform fleet. In a
#       dispersed one a plain console excludes 7.6 percent of vehicles outright at sixteen assets
#       and a service cap takes that to zero with the mean answer rate unchanged. Every section
#       now carries starved_frac, because it is the quantity a sponsor asks about first.
#   G12 exclusion rises with span, so there is a span below which no admission rule is needed.
#       P1 and P2 sweep it; P2's sweep is the dispersion at fixed span, so P1 carries G12.
#   G13 the reviewer's fifth explanation, and it beat mine: the console walks pending FCFS, so
#       in-queue death is patience-dependent by construction. Deadline ordering compresses the
#       stratification further than any admission rule (63.4 -> 1.2 against cap7's 4.2 in a
#       twelve-block pilot) with throughput equivalent. Until this arm runs, attributing the
#       stratification to admission control is premature and no version of it ships.
#   G14 the two levers compose rather than substitute: edfCap7 no lower than edf alone.
#   G16 the compression tracks how well the ordering approximates URGENCY, not merely whether the
#       queue is sorted. patient_first is the same key reversed and must be no better than fcfs;
#       easy_first sorts on length and is the discipline analogue of the cap. If easy_first
#       compresses as much as edf, the claim is about length and not about deadlines. P5.
#   G17 the quantile budget reads the SAME message field as edf and should spend it in the
#       opposite direction, because it refuses tight slack by rule and tight slack is the
#       impatient vehicle. If it is regressive, the deadline field is fairness-neutral and the
#       RULE carries the sign. P5 and P6.
#   G15 the fourteen percent dispersion cost is a second-moment result, not a property of the
#       uniform layout. `twoPt` holds the mean and the extremes and raises the variance 2.67x, so
#       if the cost scales with variance rather than with shape the claim promotes.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5,"admit_acuity":1.0'
D='"patience_spread":12'
M='"admit_response":"aimd"'
E='"queue_discipline":"edf"'
T='"patience_shape":"twopoint"'

echo "### BATTERY regress2 START"

# P5, G16. The full discipline ladder, which is the control that decides whether the finding is
# about DEADLINES or merely about SORTING. `patient_first` is the same key in the wrong direction
# and must be no better than fcfs; `easy_first` sorts on the job's length rather than the
# requester's deadline and is the discipline analogue of the cap, so if it compresses as well as
# edf the honest claim is about length and not about urgency.
for MET in starved_frac answer_step_ratio answer_rate_iqr answer_rate_v served_per_step abandoned_per_step success; do
echo "### P5 the discipline ladder, deadlines against sorting ($MET)"
$PY tools/ar_eval.py $S --metric $MET $B --sweep 'n_blue=8,16' \
  --arm "fcfs={$A,$D}" \
  --arm "random={$A,$D,\"queue_discipline\":\"random\"}" \
  --arm "edf={$A,$D,$E}" \
  --arm "patientFirst={$A,$D,\"queue_discipline\":\"patient_first\"}" \
  --arm "easyFirst={$A,$D,\"queue_discipline\":\"easy_first\"}" \
  --arm "hardFirst={$A,$D,\"queue_discipline\":\"hard_first\"}" \
  --arm "cap7={$A,$D,\"admit_cap\":7.0}" \
  --arm "quant80={$A,$D,\"admit_quantile\":0.80}" \
  --arm "quant95={$A,$D,\"admit_quantile\":0.95}"
done

# P6. The reviewer's Round 31 registration, and the sharpest prediction in the battery. The
# quantile budget selects on the REQUESTER's slack, so it refuses tight slack by rule, and tight
# slack is exactly the impatient vehicle. It reads the same message field EDF reads and should
# spend it in the opposite direction. If it lands, the deadline field is fairness-NEUTRAL and the
# rule decides the sign, which is the same-information-opposite-rule genus a fourth time.
#
#   G17  quant80 and quant95 are REGRESSIVE in a dispersed fleet: answer_step_ratio ABOVE fcfs's
#        at a fleet-mean answer rate no lower. Falsifier: the quantile budget compresses, or its
#        mean gates down so the comparison is not at matched information value.
#
# And the effort decomposition, which is the reviewer's watch item on the mechanism. Serving the
# dying first should push EDF's late bin slightly ABOVE fcfs's, with edfCap7 suppressing it. If
# EDF's late bin comes back BELOW fcfs's, the compression is not coming from the mechanism claimed
# and the whole attribution needs a second look.
for MET in worked_late_per_step worked_lost_per_step stale_per_step worked_per_step served_per_step; do
echo "### P6 the effort decomposition and the quantile budget ($MET)"
$PY tools/ar_eval.py $S --metric $MET $B --sweep 'n_blue=16' \
  --arm "fcfs={$A,$D}" \
  --arm "edf={$A,$D,$E}" \
  --arm "edfCap7={$A,$D,$E,\"admit_cap\":7.0}" \
  --arm "cap7={$A,$D,\"admit_cap\":7.0}" \
  --arm "quant80={$A,$D,\"admit_quantile\":0.80}" \
  --arm "quant95={$A,$D,\"admit_quantile\":0.95}"
done

echo "### BATTERY regress2 DONE"
