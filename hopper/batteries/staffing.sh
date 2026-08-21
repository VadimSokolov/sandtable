# C10: how many operators does a formation of n vehicles need, and what does admission
# control substitute for? Theory: n* = c * (patience + decision_interval) * service_rate / d,
# which at this operating point is 6.30 per console on a clean link and 7.78 at C2.
. hopper/batteries/_common.sh
for LVL in 0 2; do
for M in operator_goodput success; do
echo "### STAFFING comms_level=$LVL metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,4,6,8,10,12,16' \
  --arm "c1_blind={\"control_mode\":\"direct\",\"comms_level\":$LVL,\"n_operators\":1}" \
  --arm "c1_admit={\"control_mode\":\"direct\",\"comms_level\":$LVL,\"n_operators\":1,\"queue_policy\":\"admit\"}" \
  --arm "c2_blind={\"control_mode\":\"direct\",\"comms_level\":$LVL,\"n_operators\":2}" \
  --arm "c3_blind={\"control_mode\":\"direct\",\"comms_level\":$LVL,\"n_operators\":3}" \
  --arm "superv={\"control_mode\":\"supervisory\",\"comms_level\":$LVL}"
done; done
