# CR-19, the coherence ratio. K1 showed the time-clocked Gilbert-Elliot channel is
# indistinguishable from a memoryless one at every span, because the chain decorrelates in
# tau_corr = L(1-p) = 2.67 steps while the operator decides every tau = 22. Registered claim: the
# controlling quantity is theta = tau_corr / tau, not L, so the contrast is null below theta = 1
# and gates above it, and the crossover MOVES when tau moves.
#
# Marginal drop rate held at 0.20 +/- 0.01 across all five burst lengths (400k-step chain probe),
# so the arms differ only in structure. Coherence ratios: L = 4 -> 0.12, 14 -> 0.49, 28 -> 1.00,
# 60 -> 2.16, 120 -> 4.34, all at tau = 22.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step"'
C='"control_mode":"direct","comms_level":3,"n_blue":8'

echo "### L1 does burst structure become visible as the coherence ratio crosses one? (success)"
$PY tools/ar_eval.py $S --metric success $B \
  --arm "bern={$C}" \
  --arm "ge4={$C,$G,\"ge_burst_len\":4}" \
  --arm "ge14={$C,$G,\"ge_burst_len\":14}" \
  --arm "ge28={$C,$G,\"ge_burst_len\":28}" \
  --arm "ge60={$C,$G,\"ge_burst_len\":60}" \
  --arm "ge120={$C,$G,\"ge_burst_len\":120}"

echo "### L2 the registered mechanism: clustering pushes vehicles past patience (abandonment)"
$PY tools/ar_eval.py $S --metric abandon_queue_frac $B \
  --arm "bern={$C}" \
  --arm "ge4={$C,$G,\"ge_burst_len\":4}" \
  --arm "ge14={$C,$G,\"ge_burst_len\":14}" \
  --arm "ge28={$C,$G,\"ge_burst_len\":28}" \
  --arm "ge60={$C,$G,\"ge_burst_len\":60}" \
  --arm "ge120={$C,$G,\"ge_burst_len\":120}"

echo "### L3 is it a blind-policy effect? refund should absorb it (success)"
$PY tools/ar_eval.py $S --metric success $B \
  --arm "bern_blind={$C}" \
  --arm "ge120_blind={$C,$G,\"ge_burst_len\":120}" \
  --arm "bern_ref={$C,\"queue_policy\":\"refund\"}" \
  --arm "ge120_ref={$C,\"queue_policy\":\"refund\",$G,\"ge_burst_len\":120}" \
  --arm "ge4_ref={$C,\"queue_policy\":\"refund\",$G,\"ge_burst_len\":4}"

echo "### L4 the falsifier: halve tau and the crossover must move from L=28 to L=14 (success)"
# n_blue = 6 at tau = 11 sits at 0.80 n*, matching n_blue = 8 at tau = 22 (0.79 n*), so the cell
# holds its position relative to collapse and only the clock changes.
T='"control_mode":"direct","comms_level":3,"n_blue":6,"decision_interval":11'
$PY tools/ar_eval.py $S --metric success $B \
  --arm "bern11={$T}" \
  --arm "ge4_11={$T,$G,\"ge_burst_len\":4}" \
  --arm "ge14_11={$T,$G,\"ge_burst_len\":14}" \
  --arm "ge28_11={$T,$G,\"ge_burst_len\":28}" \
  --arm "ge60_11={$T,$G,\"ge_burst_len\":60}"
