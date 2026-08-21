# CR-15. The closed-form threshold assumes stationary arrivals. Terrain-correlated demand
# makes a column call for help together, so the queue should collapse at a LOWER span than
# the closed form predicts, and the published span of six should be the case in point.
. hopper/batteries/_common.sh
echo "### T1 terrain-correlated demand moves the collapse threshold left"
for M in operator_goodput success; do
echo "## metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,4,6,8,10,12' \
  --arm "td0={$D,\"terrain_demand\":0}" \
  --arm "td2={$D,\"terrain_demand\":2}" \
  --arm "td2_admit={$D,\"terrain_demand\":2,\"queue_policy\":\"admit\"}" \
  --arm "td2_crew2={$D,\"terrain_demand\":2,\"n_operators\":2}"
done
echo "### T2 coupling strength at the published span of six"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'terrain_demand=0,0.5,1,2,4' \
  --arm "blind={$D,\"n_blue\":6}" \
  --arm "admit={$D,\"n_blue\":6,\"queue_policy\":\"admit\"}"
echo "### T3 route choice is now an operator-load decision. The covered lane is slower AND"
echo "###    harder ground, so under direct control it costs attention the operator does not"
echo "###    have. Prediction: the best route_bias under direct+blind sits LOWER (faster, more"
echo "###    exposed) than under supervisory, and admission control moves it back."
for M in success time_to_objective blue_losses; do
echo "## metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'route_bias=0.0,0.2,0.4,0.65,0.85,1.0' \
  --arm "dir_flat={$D,\"n_blue\":6,\"terrain_demand\":0}" \
  --arm "dir_terr={$D,\"n_blue\":6,\"terrain_demand\":2}" \
  --arm "adm_terr={$D,\"n_blue\":6,\"terrain_demand\":2,\"queue_policy\":\"admit\"}" \
  --arm "sup_terr={\"control_mode\":\"supervisory\",\"comms_level\":0,\"n_blue\":6,\"terrain_demand\":2}"
done
