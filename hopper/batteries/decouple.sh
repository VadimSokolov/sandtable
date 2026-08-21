# P3: latency and loss rise together on the C0-C5 ladder, so the ladder cannot separate
# "delay hurts" from "load shedding helps". SandTable carries them as independent parameters.
# Prediction: at n=8 the surface is monotone DECREASING in latency and non-monotone in drop
# under the published operator, and monotone in both under admission control. The interior
# optimum on the ladder is then the projection of that surface onto a diagonal path.
. hopper/batteries/_common.sh
for M in operator_goodput success; do
for POL in blind admit; do
echo "### P3 metric=$M policy=$POL"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_p_drop=0.0,0.05,0.1,0.2,0.35,0.55' \
  --arm "lat0={\"control_mode\":\"direct\",\"n_blue\":8,\"comms_latency\":0,\"queue_policy\":\"$POL\"}" \
  --arm "lat1={\"control_mode\":\"direct\",\"n_blue\":8,\"comms_latency\":1,\"queue_policy\":\"$POL\"}" \
  --arm "lat2={\"control_mode\":\"direct\",\"n_blue\":8,\"comms_latency\":2,\"queue_policy\":\"$POL\"}" \
  --arm "lat4={\"control_mode\":\"direct\",\"n_blue\":8,\"comms_latency\":4,\"queue_policy\":\"$POL\"}" \
  --arm "lat6={\"control_mode\":\"direct\",\"n_blue\":8,\"comms_latency\":6,\"queue_policy\":\"$POL\"}" \
  --arm "lat8={\"control_mode\":\"direct\",\"n_blue\":8,\"comms_latency\":8,\"queue_policy\":\"$POL\"}"
done; done
