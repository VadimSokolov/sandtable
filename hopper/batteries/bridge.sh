# CR-58. DOES THE DETERMINISTIC PROBE PREDICT THE STOCHASTIC CHANNEL.
#
# Registered in doc/autoresearch-conjectures.md. CR-57 measured the staleness cut-off against a
# forced sawtooth track age, which no channel produces. The defence is that a sawtooth is a transfer
# function probe rather than a claimed environment, and the test of that defence is arithmetic: the
# probe's response curve predicts the channel's null with no free parameter.
#
#   E1. cut-off against no cut-off under Gilbert-Elliot mean bad run 60 at C3 lands at -0.014
#       within 0.007. Falsifier: outside [-0.021, -0.007].
#   E2. the same at mean bad run 240, where the deep fraction is 0.465 and the mean deep depth is
#       280, so the cost rate is being extrapolated in depth and not merely repeated.
#   E3. under Bernoulli at the same rung the deep fraction is about 1e-11, so the two arms must be
#       BIT-IDENTICAL. Any difference means the cut-off fires on something other than track age.
#
# THIS BATTERY RUNS AT 256 BLOCKS, EIGHT TIMES THE STANDARD TIER, because the quantity is 0.014 and
# the tier's materiality floor is 0.06: this is an estimate against a registered value, not a gate.
# Submit it with BLOCKS=0-255.
. hopper/batteries/_common.sh
F='"control_mode":"supervisory","blue_behavior":"leader_follow","follow_mode":"link","follow_topology":"star","n_blue":8'
GE='"channel":"gilbert_elliot","channel_clock":"step","comms_level":3'
INF='"track_timeout":1000000000'

for M in success station_err_mean follow_lost_frac track_stale_frac; do
echo "### E1 the bridge, Gilbert-Elliot mean bad run 60 and 240 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'ge_burst_len=60,240' \
  --arm "cut={$F,$GE}" \
  --arm "nocut={$F,$GE,$INF}"
done

for M in success track_stale_frac; do
echo "### E3 the control: Bernoulli, where the cut-off can never fire ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=3,5' \
  --arm "cut={$F}" \
  --arm "nocut={$F,$INF}"
done
