# Review finding R3, decisive cell. The three-way decomposition showed `refund` (free the slot,
# say nothing) carries ~90% of admission control, and that the remaining notification increment
# gates under teleoperation physics but not under the published physics. Two readings survive:
#
#   (a) notification buys the requester nothing the operator was not already going to give it,
#       and its teleop-only gain is an artifact of that physics; or
#   (b) notification's only job is to end a WAIT, so its value is exactly the cost of waiting,
#       which teleop physics raises.
#
# `q_stall` is the control quality of an agent awaiting a decision and `q_fallback` (0.50) the
# quality of one that gave up and went autonomous. Setting q_stall = q_fallback makes waiting
# free: under reading (b) the notification increment must vanish there and grow as q_stall falls;
# under (a) it should be flat in q_stall. A dose-response, not a single null, so the sign of the
# trend decides rather than a failure to reject.
#
# `blind` rides along as the control: if the whole queue effect scaled with q_stall the sweep
# would not be isolating notification at all.
. hopper/batteries/_common.sh
TELEOP='"control_mode":"direct","blue_behavior":"auto","teleop_stop":true'

echo "### W1 published physics, n=8, C0: is the notification increment the price of waiting?"
$PY tools/ar_eval.py $S --metric success $B --sweep 'q_stall=0.10,0.30,0.50' \
  --arm "blind={$D,\"n_blue\":8}" \
  --arm "refund={$D,\"n_blue\":8,\"queue_policy\":\"refund\"}" \
  --arm "admit={$D,\"n_blue\":8,\"queue_policy\":\"admit\"}"

echo "### W2 teleoperation physics, n=8, C0: same sweep where the increment DID gate"
$PY tools/ar_eval.py $S --metric success $B --sweep 'q_stall=0.10,0.30,0.50' \
  --arm "blind={$TELEOP,\"n_blue\":8}" \
  --arm "refund={$TELEOP,\"n_blue\":8,\"queue_policy\":\"refund\"}" \
  --arm "admit={$TELEOP,\"n_blue\":8,\"queue_policy\":\"admit\"}"
