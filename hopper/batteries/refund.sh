# Review finding R1: the paper attributes the admission-control gain to the NOTIFICATION
# ("tell the requester"), but `refund` (free the slot, say nothing) may carry nearly all of it.
# If so the operational recommendation in the Discussion is wrong: the load-bearing act is not
# telling the vehicle, it is not spending service time on requests that will expire.
#
# Three-way decomposition at full tier, at both physics settings and both link states, so the
# split is gated rather than inferred from a probe.
. hopper/batteries/_common.sh
TELEOP='"control_mode":"direct","blue_behavior":"auto","teleop_stop":true'

echo "### R1 published physics, n=8, blind vs refund vs admit"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=0,2' \
  --arm "blind={$D,\"n_blue\":8}" \
  --arm "refund={$D,\"n_blue\":8,\"queue_policy\":\"refund\"}" \
  --arm "admit={$D,\"n_blue\":8,\"queue_policy\":\"admit\"}"

echo "### R2 teleoperation physics, n=8, blind vs refund vs admit"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=0,2' \
  --arm "blind={$TELEOP,\"n_blue\":8}" \
  --arm "refund={$TELEOP,\"n_blue\":8,\"queue_policy\":\"refund\"}" \
  --arm "admit={$TELEOP,\"n_blue\":8,\"queue_policy\":\"admit\"}"

echo "### R3 goodput for the same decomposition: where does the freed slot actually go?"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=6,8,10,12' \
  --arm "blind={$D}" \
  --arm "refund={$D,\"queue_policy\":\"refund\"}" \
  --arm "admit={$D,\"queue_policy\":\"admit\"}"
