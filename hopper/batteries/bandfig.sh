# Data for the bifurcation panel of the fold-band figure, and a finer-grained replication of H1/H2.
# H2 sampled spans 3, 4, 5, 6 and 8; the band is (3.75, 5.80) so only five vehicles fell inside it,
# and seven was never measured. This fills the sweep in so the two branches can be drawn rather
# than asserted, and so the null at seven is measured rather than interpolated between six and eight.
. hopper/batteries/_common.sh
R='"retry_prob":1.0,"retry_backoff":4'
ST='"stagger_decisions":true'

echo "### B1 both branches across span, at full resolution (queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=3,4,5,6,7,8,9' \
  --arm "stag_retry={$D,$ST,$R}" \
  --arm "burst_retry={$D,$R}" \
  --arm "stag_off={$D,$ST}" \
  --arm "burst_off={$D}"

echo "### B2 the same on mission outcome"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=3,4,5,6,7,8,9' \
  --arm "stag_retry={$D,$ST,$R}" \
  --arm "burst_retry={$D,$R}" \
  --arm "stag_off={$D,$ST}" \
  --arm "burst_off={$D}"
