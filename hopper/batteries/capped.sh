# CR-59 CONTROL. THE HONEST CAPPED CONSOLE, WHICH DECIDES WHETHER F6 IS A FINDING OR A STRAWMAN.
#
# Registered in doc/autoresearch-conjectures.md under the Round 28 amendment. The reviewer's attack
# on F6 is that at sigma=0 the console's RANKING of jobs is exact, so a multiplicative factor on a
# threshold rule slides the operating point along a perfect ROC and destroys no information: "the
# most accurate estimator is beaten" then reads as "a default threshold is beaten by a re-tuned
# threshold". The rule-repair that answers it is a console that is wrong about NOTHING and has
# simply been told a slot has a price: admit only if the job is BOTH feasible AND shorter than a
# cap, with an unbiased estimate in each test. `admit_cap` is that console.
#
#   If the capped console at its best cap reaches the inflated console's 0.2186, F6 dies as worded.
#   If it does not, the residue is a coupling between the cap and the deadline slack, and that is
#   its own finding. Either way nothing about F6 goes near the manuscript until this lands.
#
# M2, M3 and M4 are F9, F10 and F11: the shadow-price reading predicts WHERE the ladder turns, and
# those predictions are what separate a price knob from a fitted constant.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5,"admit_acuity":1.0'

echo "### BATTERY capped START"

# M1. The control. The cap ladder is in units of the mean service time, which is 6.667 steps, so
# c=4 is 0.6 of the mean and c=10 is 1.5 of it. The inflated console at b=2.5 is the target.
for M in served_per_step svc_serviced_mean busy_total abandon_queue_frac success; do
echo "### M1 the capped console against the inflated one ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "plain={$A}" \
  --arm "bias250={$A,\"admit_bias\":2.5}" \
  --arm "cap3={$A,\"admit_cap\":3.0}" \
  --arm "cap4={$A,\"admit_cap\":4.0}" \
  --arm "cap5={$A,\"admit_cap\":5.0}" \
  --arm "cap7={$A,\"admit_cap\":7.0}" \
  --arm "cap10={$A,\"admit_cap\":10.0}" \
  --arm "cap15={$A,\"admit_cap\":15.0}"
done

# M2, F9 and F10. Where the ladder turns, read against the span at which the queue collapses. The
# shadow-price reading says b* crosses 1 exactly at the collapse span and that BELOW it the ladder
# is flat under b=1 rather than falling, because an idle server loses nothing by taking a long job.
for M in served_per_step operator_utilization; do
echo "### M2 where the price turns, against the collapse span ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,7,8,10,12,16' \
  --arm "b080={$A,\"admit_bias\":0.8}" \
  --arm "b090={$A,\"admit_bias\":0.9}" \
  --arm "b100={$A}" \
  --arm "b110={$A,\"admit_bias\":1.1}" \
  --arm "b125={$A,\"admit_bias\":1.25}" \
  --arm "b160={$A,\"admit_bias\":1.6}"
done

# M3, F11. At cv=0 every job is the same length, so a price knob has nothing to select on and the
# ladder must degenerate to a step: admit all, or refuse all. An interior optimum at cv=0 would mean
# the knob is doing something other than selecting on length and the shadow-price reading is wrong.
for M in served_per_step svc_serviced_mean; do
echo "### M3 the degenerate case, no spread to price ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'admit_bias=0.8,1.0,1.1,1.25,1.6,2.0,2.5' \
  --arm "cv000={$A,\"n_blue\":16,\"service_cv\":0.0}" \
  --arm "cv010={$A,\"n_blue\":16,\"service_cv\":0.1}" \
  --arm "cv050={$A,\"n_blue\":16}"
done

# M4. THE RIDER, which must sit beside any version of F6 that survives. Throughput bought by pricing
# the slot is bought from a subpopulation: long jobs. `starved_frac` is the column that says so, and
# `answer_rate_v` says whether the harm is spread or concentrated.
for M in starved_frac answer_rate_v abandoned_per_step served_per_step; do
echo "### M4 who pays for the throughput ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "plain={$A}" \
  --arm "b160={$A,\"admit_bias\":1.6}" \
  --arm "b250={$A,\"admit_bias\":2.5}" \
  --arm "cap5={$A,\"admit_cap\":5.0}"
done

echo "### BATTERY capped COMPLETE"
