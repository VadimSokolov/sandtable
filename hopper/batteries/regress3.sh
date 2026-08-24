# CR-62 CORRECTIONS. TWO REGISTERED TESTS THAT COULD NOT MOVE IN THE CONFIGURATION I RAN THEM IN.
#
# Job 9455454 returned two nulls that were not nulls. Both are instrument defect 13's genus, which
# is now on its third and fourth instance: a test registered in a configuration where the quantity
# under test is structurally pinned.
#
#   G17 the quantile budget arms came back BIT-IDENTICAL to fcfs, 0 of 32 blocks differing.
#       `_admit_budget` is consulted only when `_sees_the_draw` is False, and I ran every arm at
#       `admit_acuity: 1.0`, so the console always saw the job and never read the budget. The
#       quantile could not act. Rerun at acuity 0, which is the console the budget exists for.
#   G18 the effort bins came back exactly 0.0000 for every arm. At comms_level 0 with a feasibility
#       test, the console never starts work that ends lost, late or stale: worked_per_step equals
#       served_per_step exactly. The decomposition needs a console that CAN waste work, which is
#       C3, and `stale` and `late` need the blind policy on top.
#
# Every arm below was piloted locally at four blocks FIRST and confirmed to move. That check is the
# repair for the genus and it costs four minutes.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","queue_policy":"admit","service_cv":0.5'
D='"patience_spread":12'
E='"queue_discipline":"edf"'

echo "### BATTERY regress3 START"

# Q1, G17. The reviewer's Round 31 registration, now in the configuration where it can act. The
# budget console cannot see the job and works from the deadline field alone, which is the SAME
# field edf reads. If the budget is regressive while edf is progressive, the field is
# fairness-neutral and the RULE carries the sign.
#
#   Registered: q80 and q95 raise answer_step_ratio above the mean-budget console's at a fleet-mean
#   answer rate no lower. Falsifier: the quantile compresses, or its mean gates down so the two are
#   not being compared at matched information value.
for M in answer_step_ratio answer_rate_iqr starved_frac answer_rate_v served_per_step; do
echo "### Q1 the quantile budget spends the deadline field regressively ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "meanBudget={$A,$D,\"admit_acuity\":0.0}" \
  --arm "q80={$A,$D,\"admit_acuity\":0.0,\"admit_quantile\":0.80}" \
  --arm "q95={$A,$D,\"admit_acuity\":0.0,\"admit_quantile\":0.95}" \
  --arm "edfBudget={$A,$D,$E,\"admit_acuity\":0.0}" \
  --arm "edfSees={$A,$D,$E,\"admit_acuity\":1.0}" \
  --arm "seesMean={$A,$D,\"admit_acuity\":1.0}"
done

# Q2, G18. The mechanism watch item, at an operating point where the console can waste work.
# Serving the most urgent first means serving requests closer to expiry, so edf's LATE bin should
# sit above fcfs's and edfCap7 should suppress it again. C3 is required for the bins to be nonzero
# at all, and `stale` and `late` additionally require the blind policy.
#
#   Falsifier: edf's late bin comes back BELOW fcfs's, in which case the compression is not
#   produced by the mechanism claimed and the attribution reopens.
for M in worked_late_per_step worked_lost_per_step stale_per_step worked_per_step served_per_step answer_step_ratio; do
echo "### Q2 the effort decomposition where work can be wasted ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=16' \
  --arm "admitFcfs={$A,$D,\"comms_level\":3}" \
  --arm "admitEdf={$A,$D,$E,\"comms_level\":3}" \
  --arm "admitEdfCap={$A,$D,$E,\"comms_level\":3,\"admit_cap\":7.0}" \
  --arm "blindFcfs={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"blind\",\"service_cv\":0.5,$D,\"comms_level\":3}" \
  --arm "blindEdf={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"blind\",\"service_cv\":0.5,$D,$E,\"comms_level\":3}" \
  --arm "blindEdfCap={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"blind\",\"service_cv\":0.5,$D,$E,\"comms_level\":3,\"admit_cap\":7.0}"
done

# Q3, G14 at full tier. The composition test P5 could not run, because edfCap7 was not a P5 arm.
for M in answer_step_ratio answer_rate_iqr starved_frac answer_rate_v served_per_step abandoned_per_step; do
echo "### Q3 do the two levers compose ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,16' \
  --arm "fcfs={$A,$D,\"admit_acuity\":1.0}" \
  --arm "edf={$A,$D,$E,\"admit_acuity\":1.0}" \
  --arm "cap7={$A,$D,\"admit_acuity\":1.0,\"admit_cap\":7.0}" \
  --arm "edfCap7={$A,$D,$E,\"admit_acuity\":1.0,\"admit_cap\":7.0}"
done

echo "### BATTERY regress3 DONE"
