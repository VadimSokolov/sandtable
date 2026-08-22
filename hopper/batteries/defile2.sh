# Correction to st-defile-9443710. D1 contrasted retry against no-retry at a staggered start and
# swept terrain. That contrast is gated at EVERY terrain level including flat ground (-0.1474 at
# terrain_demand = 0), which refutes the null I registered there, and on inspection the registered
# prediction was testing the wrong thing: retry raises offered load, so it costs something at any
# terrain, and a contrast that shows so is not evidence of bistability.
#
# Bistability is a claim about INITIAL CONDITIONS, so the terrain sweep has to carry both of them.
# The quantity is the same difference of differences H1 and H2 used, now swept over terrain:
#
#   [stag - burst | retry] - [stag - burst | no retry]
#
# Registered: this is near zero on flat ground at five vehicles when the start is the only thing
# that differs and the load is well below the band's upper edge, rises as terrain shortens the
# decision interval and drags the band down across the operating point, and falls again once
# terrain has pushed the upper edge below five vehicles, where only the collapsed branch remains.
# A single-peaked profile in terrain is the signature of a band being dragged past a fixed span;
# a monotone profile would mean I am watching a moved cliff and not a band.
. hopper/batteries/_common.sh
R='"retry_prob":1.0,"retry_backoff":4'
ST='"stagger_decisions":true'

echo "### E1 terrain drags the band across a fixed span: single-peaked, or monotone?"
$PY tools/ar_eval.py $S --metric operator_goodput $B \
  --sweep 'terrain_demand=0.0,0.25,0.5,0.75,1.0,1.5,2.0' \
  --arm "stag_retry={$D,\"n_blue\":5,$ST,$R}" \
  --arm "burst_retry={$D,\"n_blue\":5,$R}" \
  --arm "stag_off={$D,\"n_blue\":5,$ST}" \
  --arm "burst_off={$D,\"n_blue\":5}"

echo "### E2 the same on mission outcome"
$PY tools/ar_eval.py $S --metric success $B \
  --sweep 'terrain_demand=0.0,0.25,0.5,0.75,1.0,1.5,2.0' \
  --arm "stag_retry={$D,\"n_blue\":5,$ST,$R}" \
  --arm "burst_retry={$D,\"n_blue\":5,$R}" \
  --arm "stag_off={$D,\"n_blue\":5,$ST}" \
  --arm "burst_off={$D,\"n_blue\":5}"
