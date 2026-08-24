# CR-64 AS AMENDED TWICE. THE FAIRNESS FIX THAT NEEDS NO MESSAGE FIELD, AND ITS PRECONDITION.
#
# Registered in doc/autoresearch-conjectures.md with both amendments and both pilots disclosed.
# Serve whoever has been served least: a discipline that reads nothing about the request, only a
# counter the console keeps about itself. The first amendment killed an untestable section using the
# guard registered the same day. The second inverted the conjecture: the discipline recommendation
# is void without admission control, and deadline order is the WORST of the four rules on a console
# that cannot refuse.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5,"admit_acuity":1.0'
BL='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind","service_cv":0.5,"admit_acuity":1.0'
D='"patience_spread":12,"patience_shape":"twopoint"'
NOSEE='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5,"admit_acuity":0.0'

echo "### BATTERY roundrobin START"

# T1, S1/S2/S3/S5. The admitting console, mixed fleet. Twenty-four assets is included because
# exclusion under arrival order is far larger there and the equivalence tests need room to fail.
for M in starved_frac answer_step_ratio answer_step_share answer_step_censored answer_rate_iqr answer_rate_v served_per_step abandoned_per_step died_feasible_per_step died_feasible_frac success; do
echo "### T1 the zero-information rule against arrival order and against the field ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16,24' \
  --arm "fcfs={$A,$D}" \
  --arm "random={$A,$D,\"queue_discipline\":\"random\"}" \
  --arm "roundRobin={$A,$D,\"queue_discipline\":\"round_robin\"}" \
  --arm "edf={$A,$D,\"queue_discipline\":\"edf\"}"
done

# T2, S7. The blind console, where the pilot says the whole ordering inverts. This is the section
# that decides whether the paper ships an unconditional recommendation or an order of adoption.
for M in starved_frac answer_step_ratio answer_step_share answer_step_censored answer_rate_iqr answer_rate_v served_per_step died_feasible_per_step died_feasible_frac success; do
echo "### T2 the same four rules on a console that cannot refuse ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24' \
  --arm "fcfs={$BL,$D}" \
  --arm "random={$BL,$D,\"queue_discipline\":\"random\"}" \
  --arm "roundRobin={$BL,$D,\"queue_discipline\":\"round_robin\"}" \
  --arm "edf={$BL,$D,\"queue_discipline\":\"edf\"}"
done

# T3, S6. The precondition test. Deadline order's dominance is welded to job sight; a rule that never
# consults the job should not be, and if it is, the free-lunch framing is wrong for both.
for M in starved_frac answer_step_ratio answer_step_share answer_step_censored answer_rate_iqr answer_rate_v served_per_step died_feasible_per_step died_feasible_frac; do
echo "### T3 without job sight, which is where the free lunch had its precondition ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24' \
  --arm "blindFcfs={$NOSEE,$D}" \
  --arm "blindRoundRobin={$NOSEE,$D,\"queue_discipline\":\"round_robin\"}" \
  --arm "blindEdf={$NOSEE,$D,\"queue_discipline\":\"edf\"}"
done

# T4, S4 as reworded. The uniform fleet on a blind console, which is the configuration the `maps`
# battery already showed excludes 81 percent under arrival order, so the metric is known to move
# here. The registered prediction is now a NEGATIVE: round-robin does not repair it.
for M in starved_frac answer_rate_iqr answer_rate_v served_per_step success; do
echo "### T4 a uniform fleet on a console that cannot refuse ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24' \
  --arm "fcfs={$BL}" \
  --arm "random={$BL,\"queue_discipline\":\"random\"}" \
  --arm "roundRobin={$BL,\"queue_discipline\":\"round_robin\"}" \
  --arm "edf={$BL,\"queue_discipline\":\"edf\"}"
done

# T5. The link, because a rule recommended without a span condition still has to be checked against
# the ladder it will be flown on. C3 is expected to saturate the ratio at its sentinel value and is
# kept in so the saturation is on the record rather than hidden by a narrower sweep.
for M in starved_frac answer_step_ratio answer_step_share answer_step_censored answer_rate_v served_per_step died_feasible_per_step died_feasible_frac entered_feasible_frac success; do
echo "### T5 the same rules against the link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3' \
  --arm "fcfs={$A,$D,\"n_blue\":16}" \
  --arm "random={$A,$D,\"n_blue\":16,\"queue_discipline\":\"random\"}" \
  --arm "roundRobin={$A,$D,\"n_blue\":16,\"queue_discipline\":\"round_robin\"}" \
  --arm "edf={$A,$D,\"n_blue\":16,\"queue_discipline\":\"edf\"}"
done

# T6, registered on the pilot that found the counter's exact zero. Doubling the patience takes
# `died_feasible_frac` to 0.0000 at two assets, which is the configuration in which the ordering has
# genuinely nothing to order. Every discipline must then be equivalent on every reading. This is the
# negative control the discrimination needs to be two-sided, and it is the arm that would kill the
# information claim if the rules separated where there is no scheduling problem to solve.
for M in died_feasible_frac answer_step_ratio starved_frac answer_rate_v served_per_step; do
echo "### T6 where there is no scheduling problem, no rule may win ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,4,8' \
  --arm "fcfs={$A,\"patience\":40,\"patience_spread\":24,\"service_cv\":0.0}" \
  --arm "random={$A,\"patience\":40,\"patience_spread\":24,\"service_cv\":0.0,\"queue_discipline\":\"random\"}" \
  --arm "roundRobin={$A,\"patience\":40,\"patience_spread\":24,\"service_cv\":0.0,\"queue_discipline\":\"round_robin\"}" \
  --arm "edf={$A,\"patience\":40,\"patience_spread\":24,\"service_cv\":0.0,\"queue_discipline\":\"edf\"}"
done

echo "### BATTERY roundrobin DONE"
