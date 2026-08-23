# CR-34 P6. THE CONTROL THE COHORT BATTERY SHOULD HAVE CARRIED.
#
# Every arm in K1/K2 retries, so no cell has the retry cohort absent by construction. The excess
# above the Bernoulli floor that refutes P1 might therefore be the retry cohort, or it might be the
# standing decision cadence, whose superposition over four to ten vehicles is not Bernoulli and need
# not read at a Bernoulli reference.
#
#   P6. The jittered arms sit ABOVE the noretry arm on arrival_excess at matched span, gated.
#   FALSIFIER. If noretry shows the same excess, the residual is the standing cadence, P1 returns
#     to UNDECIDED, and the two-synchronizer account rests on the matched-rate GE-minus-memoryless
#     gap, which is floor-free and unaffected either way.
#
# stagger_decisions is swept alongside, because if the residual IS the standing cadence then
# staggering the vehicles' first decision events should reduce it and staggering should do nothing
# to a genuine retry cohort. That is a second, independent read on the same question.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
W='"mult_window":7'

for M in arrival_excess arrival_multiplicity; do
echo "### N1 memoryless: the retry cohort against no retry at all ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10' \
  --arm "noretry={$C,$W}" \
  --arm "noretry_stag={$C,$W,\"stagger_decisions\":true}" \
  --arm "fix18={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17}" \
  --arm "jit18_stag={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17,\"stagger_decisions\":true}"
echo "### N2 GE-120: the same control on the bursty link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10' \
  --arm "noretry={$C,$G,$W}" \
  --arm "noretry_stag={$C,$G,$W,\"stagger_decisions\":true}" \
  --arm "fix18={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17}" \
  --arm "jit18_stag={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17,\"stagger_decisions\":true}"
done
