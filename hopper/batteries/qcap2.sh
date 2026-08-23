# CR-49 CONTINUED. Q3 THROUGH Q5, WHICH JOB 9448688 DID NOT REACH BEFORE ITS TIME LIMIT.
#
# 9448688 completed Q1 and Q2 on all three metrics, which is the whole of CR-48's span evidence and
# CR-49's discriminating cell, and was cancelled two hours in at the first row of Q3. This battery is
# Q3, Q4 and Q5 only, at the same tier, so the two logs compose. Nothing is re-registered: the
# predictions below are the ones in qcap.sh, unchanged, and were written before 9448688 ran.
#
# The discriminating content is Q3. The mean-fits rule and the median-fits rule disagree at four of
# the ten operating points in the original battery and the patience sweep carries three of them:
#   P=12 -> 0 vs 1     P=20 -> 2 vs 2     P=25 -> 2 vs 3     P=27 -> 3 vs 3
# The deterministic re-derivation that replaced both, k* = floor(lambda + 1/2) - 1, is a third
# answer at P=25 and the sweep is where it is checked against the other two.

. hopper/batteries/_common.sh
CD='"control_mode":"direct","queue_model":"buffer","queue_policy":"blind"'
CAPS='cap_none=-1 cap_zero=0 cap_one=1 cap_two=2 cap_three=3 cap_four=4 cap_five=5 cap_six=6 cap_ten=10'

# The capacity ladder as arms, so any sweep below reads an argmax per sweep point.
mkarms() {
  A=""
  for kv in $CAPS; do
    nm=${kv%%=*}; v=${kv##*=}
    A="$A --arm $nm={$CD,\"queue_capacity\":$v$1}"
  done
  echo "$A"
}

for M in served_per_step success; do
echo "### Q3 the capacity ladder against PATIENCE, clear link, n=12 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'patience=12,20,25,27,30,34,38,45' \
  $(mkarms ',"comms_level":0,"n_blue":12')
echo "### Q4 the capacity ladder against SERVICE RATE, clear link, n=12 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'service_rate=0.075,0.15,0.30' \
  $(mkarms ',"comms_level":0,"n_blue":12')
echo "### Q5 the requirements ladder: a counter, a stack, a message field ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,10,12,16' \
  --arm "bound={$CD,\"comms_level\":0,\"queue_capacity\":2}" \
  --arm "newest={$CD,\"comms_level\":0,\"queue_discipline\":\"patient_first\"}" \
  --arm "deadline={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"admit\",\"comms_level\":0}" \
  --arm "nothing={$CD,\"comms_level\":0}"
done
