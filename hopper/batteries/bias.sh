# CR-59. THE ESTIMATOR REQUIREMENT: WHAT A DIFFICULTY ESTIMATE HAS TO BE GOOD AT.
#
# Registered in doc/autoresearch-conjectures.md, including the four-block pilot that already put F1
# and F2 on the table, so this battery is confirmatory for those two and decisive for F3, F4 and
# F6-F8. `admit_bias` is a multiplicative offset on what the console reads off its difficulty
# estimate and `admit_sigma` is the log-scale spread around it; at (1.0, 0.0) the console is exactly
# CR-56's foresighted console and no randomness is drawn.
#
# The point of the battery in one sentence: a feasibility test carrying an inflated estimate is a
# shortest-job filter, so the MOST ACCURATE estimator is not the one that produces the best mission
# outcome, and the offset that buys throughput at sixteen assets costs it at four.
#
# Every arm here carries admit_acuity 1.0 except where the section says otherwise, because the
# question is about the QUALITY of an estimate the console already has, not about whether it has one.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5,"admit_acuity":1.0'
AC='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5'

echo "### BATTERY bias START"

# H1 is F1 and F2 in one table: the offset ladder against the load ladder. b* is read off each
# column. The prediction is an interior maximum that MOVES with load, so the sweep has to be the
# load and the arms have to be the offsets.
for M in served_per_step svc_serviced_mean busy_total abandon_queue_frac; do
echo "### H1 the offset ladder against the load ladder ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16' \
  --arm "b060={$A,\"admit_bias\":0.6}" \
  --arm "b080={$A,\"admit_bias\":0.8}" \
  --arm "b100={$A}" \
  --arm "b125={$A,\"admit_bias\":1.25}" \
  --arm "b160={$A,\"admit_bias\":1.6}" \
  --arm "b200={$A,\"admit_bias\":2.0}" \
  --arm "b250={$A,\"admit_bias\":2.5}" \
  --arm "b320={$A,\"admit_bias\":3.2}" \
  --arm "b400={$A,\"admit_bias\":4.0}"
done

# H2, F3 and F4. Spread is the error an offset is supposed to compensate. If the two are substitutes
# the ladder's peak moves right as sigma grows, and the peak value at sigma=0.7 stays close to the
# peak value at sigma=0. If they are not, the peak stays put and the value collapses.
for M in served_per_step svc_serviced_mean; do
echo "### H2 spread against offset, at sixteen assets ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'admit_bias=1.0,1.25,1.6,2.0,2.5,3.2,4.0' \
  --arm "s000={$A,\"n_blue\":16}" \
  --arm "s035={$A,\"n_blue\":16,\"admit_sigma\":0.35}" \
  --arm "s070={$A,\"n_blue\":16,\"admit_sigma\":0.7}" \
  --arm "s140={$A,\"n_blue\":16,\"admit_sigma\":1.4}"
done

# H3, F8. The information-free null at matched tightness. `admit_refuse` throws away a fixed fraction
# AT RANDOM, so it buys admission tightness and nothing else. Its own best fraction is the honest
# comparator for the best offset, and `abandon_queue_frac` is carried so the two can be read at
# matched refusal rate rather than at matched parameter.
for M in served_per_step abandon_queue_frac svc_serviced_mean; do
echo "### H3 tightness without selectivity, at sixteen assets ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "base={$A}" \
  --arm "bias={$A,\"admit_bias\":2.5}" \
  --arm "r20={$A,\"admit_refuse\":0.2}" \
  --arm "r40={$A,\"admit_refuse\":0.4}" \
  --arm "r60={$A,\"admit_refuse\":0.6}" \
  --arm "r80={$A,\"admit_refuse\":0.8}"
done

# H4. Does the paradox need an estimate at all? The blind console budgets a quantile instead of the
# mean, which is the same pessimism with no per-job information in it. If the quantile ladder has
# its own interior optimum of the same size, the result is about ADMISSION TIGHTNESS and the word
# estimator comes out of the finding. If it is much smaller, the gain is in the selection.
for M in served_per_step svc_serviced_mean; do
echo "### H4 pessimism without a per-job estimate ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "q000={$AC}" \
  --arm "q50={$AC,\"admit_quantile\":0.5}" \
  --arm "q75={$AC,\"admit_quantile\":0.75}" \
  --arm "q90={$AC,\"admit_quantile\":0.9}" \
  --arm "q99={$AC,\"admit_quantile\":0.99}"
done

# H5. The paradox against cv, because VoI = mu*cv says the whole value of an estimate scales with
# spread and the offset is a way of spending that value. Registered expectation: b* rises with cv,
# and at cv=0 the ladder is flat because there is nothing to select on.
for M in served_per_step svc_serviced_mean; do
echo "### H5 the offset ladder against service spread, at sixteen assets ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'admit_bias=1.0,1.6,2.5,4.0' \
  --arm "cv00={$A,\"n_blue\":16,\"service_cv\":0.0}" \
  --arm "cv25={$A,\"n_blue\":16,\"service_cv\":0.25}" \
  --arm "cv50={$A,\"n_blue\":16}" \
  --arm "cv100={$A,\"n_blue\":16,\"service_cv\":1.0}"
done

# H6. And the mission end of it, because served per step is a console quantity and the sponsor's
# question is scored on the mission. Nothing in the model guarantees the two agree.
for M in success mission_time; do
echo "### H6 does the offset reach the mission ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,8,12,16' \
  --arm "b100={$A}" \
  --arm "b160={$A,\"admit_bias\":1.6}" \
  --arm "b250={$A,\"admit_bias\":2.5}" \
  --arm "b400={$A,\"admit_bias\":4.0}"
done

echo "### BATTERY bias COMPLETE"
