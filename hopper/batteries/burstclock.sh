# C2 gated a large interaction: with the reliance loop closed, a bursty channel at matched mean
# drop rate costs 0.20 to 0.29 of operator goodput that it does not cost with the loop open.
# CR-18 says that is very likely the same artifact as the S1 sign flip. The message-clocked chain
# inflates round-trip delivery, inflated delivery is extra offered load, and extra load with a
# reliance loop is exactly what pushes five vehicles across the fold band. Remove the inflation and
# the interaction should have nothing left to run on.
#
# Registered: under `channel_clock="step"` the difference of differences is null at every rung. If
# it survives, burst structure has a second channel into this model that is not the scalar `d`,
# and the Fano evidence (arrivals not clustered) says it should not.
. hopper/batteries/_common.sh
R='"retry_prob":1.0,"retry_backoff":4'
GES='"channel":"gilbert_elliot","channel_clock":"step"'

echo "### J1 the C2 interaction under physical clocking (queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "ge_off={\"control_mode\":\"direct\",\"n_blue\":5,$GES}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R}" \
  --arm "ge_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R,$GES}"

echo "### J2 the same on mission outcome"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "ge_off={\"control_mode\":\"direct\",\"n_blue\":5,$GES}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R}" \
  --arm "ge_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R,$GES}"
