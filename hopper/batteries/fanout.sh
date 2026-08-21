# C9: does the Olsen and Wood duty-cycle capacity, measured from SandTable's own hold
# durations, predict the span one operator can actually hold? `arrived` is a count rather
# than a thresholded rate, so it is comparable ACROSS spans in a way `success` is not.
. hopper/batteries/_common.sh
TB='"control_mode":"direct","comms_level":0,"blue_behavior":"auto","teleop_stop":true'
for M in arrived fan_out hold_fraction interaction_steps neglect_steps success; do
echo "### C9 metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,3,4,5,6,8,10,12' \
  --arm "blind={$TB}" \
  --arm "admit={$TB,\"queue_policy\":\"admit\"}" \
  --arm "crew2={$TB,\"n_operators\":2}" \
  --arm "superv={\"control_mode\":\"supervisory\",\"comms_level\":0,\"blue_behavior\":\"auto\"}"
done
