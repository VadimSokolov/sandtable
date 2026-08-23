# CR-39. THREE VEHICLES ARRIVING TOGETHER, OR ONE VEHICLE ARRIVING THREE TIMES.
#
# Every burstiness statistic in this paper counts arrivals per window and none of them counts
# SENDERS. The two are the same number for a retry cohort and very different for one vehicle's
# refusal echo, and the paper's mechanism sentence is about the first. `arrival_distinct` and
# `arrival_repeat` split them. Same arms and same window as CR-37 so the statistic is the only
# thing that changes.
#
#   P1. At backoff 18 the fix-minus-jit contrast is carried by arrival_distinct, gated.
#   P2. arrival_repeat_frac is higher at backoff 4 than at 18 (instrument check, answer known).
#   P3. The memoryless control shows the same P1 pattern.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
W='"retry_prob":1.0,"fano_window":7,"mult_window":7'

for M in arrival_distinct arrival_repeat arrival_repeat_frac arrival_multiplicity; do
echo "### S1 the bursty link, senders against arrivals ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "fix04={$C,$G,$W,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$G,$W,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix18={$C,$G,$W,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$W,\"retry_backoff\":18,\"retry_spread\":17}"
echo "### S2 the memoryless control, senders against arrivals ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "fix04={$C,$W,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$W,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix18={$C,$W,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$W,\"retry_backoff\":18,\"retry_spread\":17}"
done

# The no-retry arm is the zero control: with no retry there is no echo train and no cohort, so
# repeat_frac there is whatever the console's own refusal traffic produces and is the floor both
# retry arms should be read against.
echo "### S3 the no-retry floor (arrival_repeat_frac)"
$PY tools/ar_eval.py $S --metric arrival_repeat_frac $B --sweep 'n_blue=4,5,6,8' \
  --arm "noretry={$C,$G,\"fano_window\":7,\"mult_window\":7,\"retry_prob\":0.0}" \
  --arm "fix18={$C,$G,$W,\"retry_backoff\":18,\"retry_spread\":0}"
