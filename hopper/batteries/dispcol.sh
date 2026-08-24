# CR-60's OWED SECTION. The reading the conjecture recommends is the one whose threshold was never
# checked against column length, because `fleet_spread_mean` was not among the metrics section L3
# logged. A threshold that holds at one column length is a fitted constant, and the two readings L3
# DID log move their thresholds by a factor of five across spans, which is exactly why this is owed
# rather than optional. Same arms, same sweep, the recommended reading added, plus the nuisance
# family at every span so the blindness test is not a single-span number either.
. hopper/batteries/_common.sh
F='"control_mode":"supervisory","blue_behavior":"leader_follow","follow_mode":"link","follow_topology":"star","comms_level":0,"n_blue":8'

echo "### BATTERY dispcol START"

for M in success fleet_spread_mean fleet_cross_mean station_cross_mean station_err_mean; do
echo "### K1 the recommended reading against column length ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,8,12,16' \
  --arm "base={$F}" \
  --arm "out320={$F,\"follow_outage\":320}" \
  --arm "sp120={$F,\"formation_spread\":120}" \
  --arm "sp300={$F,\"formation_spread\":300}" \
  --arm "sp600={$F,\"formation_spread\":600}"
done

# The nuisance family at every span. The blindness claim is that route bias never carries a cell
# across the threshold; that was measured at one span and a requirement cannot be written on it.
for M in success fleet_spread_mean fleet_cross_mean station_cross_mean; do
echo "### K2 the nuisance family against column length ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'route_bias=0.0,0.25,0.5,0.75,1.0' \
  --arm "tight4={$F,\"n_blue\":4}" \
  --arm "tight16={$F,\"n_blue\":16}" \
  --arm "wide4={$F,\"n_blue\":4,\"formation_spread\":300}" \
  --arm "wide16={$F,\"n_blue\":16,\"formation_spread\":300}"
done

echo "### BATTERY dispcol DONE"
