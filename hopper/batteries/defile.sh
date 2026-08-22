# The initial-condition-free form of CR-17, and the answer to the obvious objection to it.
#
# H1 demonstrated bistability by contrasting two initial conditions, which invites the reply that
# the synchronized start is arbitrary. It is not needed. `terrain_demand` ties the call-for-help
# rate to trafficability (CR-15), so difficult ground raises offered load endogenously and at
# staggered times. Starting HEALTHY (stagger_decisions) at five vehicles and driving into harder
# ground, the team crosses to the collapsed branch and stays there, but only with the reliance
# loop closed. Local probe, staggered start, n=5, operator goodput:
#
#   terrain_demand   0.0    0.5    1.0    2.0
#   retry on        0.815  0.509  0.287  0.234
#   retry off       0.977  0.956  0.908  0.723
#
# With the loop open the team degrades gracefully; with it closed the same terrain tips it.
# Feeding the shortened interval through the closed form puts the band at (3.75, 5.02) at
# terrain_demand = 1.0, so five vehicles sit just inside its upper edge, which is why a
# fluctuating load can knock the system out of a shallow healthy basin and leave it there.
#
# Registered: the difference of differences is null at terrain_demand = 0 and gated from 0.5 up,
# at five vehicles; and it is null at three vehicles, which is below the band at every terrain
# setting tested.
. hopper/batteries/_common.sh
R='"retry_prob":1.0,"retry_backoff":4'
ST='"stagger_decisions":true'

echo "### D1 five vehicles, healthy start: does terrain alone select the collapsed branch?"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'terrain_demand=0.0,0.5,1.0,2.0' \
  --arm "retry={$D,\"n_blue\":5,$ST,$R}" \
  --arm "noretry={$D,\"n_blue\":5,$ST}"

echo "### D2 the same on mission outcome"
$PY tools/ar_eval.py $S --metric success $B --sweep 'terrain_demand=0.0,0.5,1.0,2.0' \
  --arm "retry={$D,\"n_blue\":5,$ST,$R}" \
  --arm "noretry={$D,\"n_blue\":5,$ST}"

echo "### D3 three vehicles, below the band at every terrain setting: must stay null"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'terrain_demand=0.0,0.5,1.0,2.0' \
  --arm "retry={$D,\"n_blue\":3,$ST,$R}" \
  --arm "noretry={$D,\"n_blue\":3,$ST}"

echo "### D4 does a backoff floor above 15.33 protect the team on the same ground?"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'retry_backoff=4,8,12,16,20' \
  --arm "hard={$D,\"n_blue\":5,$ST,\"retry_prob\":1.0,\"terrain_demand\":1.0}" \
  --arm "flat={$D,\"n_blue\":5,$ST,\"retry_prob\":1.0}"
