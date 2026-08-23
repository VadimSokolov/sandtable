# CR-40. THE REMAINING GOODPUT SITES ON A METRIC WITH NO DENOMINATOR.
#
# operator_goodput is serviced over requested. The absrate audit shows every policy in this paper
# moves the denominator, including `refund`, which I had reasoned could not: it does not tell the
# requester, but it frees the slot, so more vehicles complete a round trip and come back to ask.
# +20.6% at n=8. Three sites in the manuscript are still read on the ratio. This reads all three on
# served_per_step, with requests_per_step alongside so the movement is visible rather than assumed.
#
#   P1. refund - blind on served_per_step is larger on GE than on Bernoulli at n=8, gated.
#   P2. jit - fix on served_per_step is positive and gated on the memoryless link at n=5,6.
#   P3. The C2 reliance-loop DiD keeps its sign on served_per_step.
. hopper/batteries/_common.sh
C='"control_mode":"direct"'
G='"channel":"gilbert_elliot"'
GS='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
RF='"queue_policy":"refund"'
R='"retry_prob":1.0,"retry_backoff":4'
W='"retry_prob":1.0,"fano_window":7,"mult_window":7'
L3='"comms_level":3'

for M in served_per_step requests_per_step; do
echo "### G1 the burst interaction, refund against blind on both links ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6,8,10' \
  --arm "bern_blind={$C,$L3}" \
  --arm "ge_blind={$C,$L3,$G}" \
  --arm "bern_ref={$C,$L3,$RF}" \
  --arm "ge_ref={$C,$L3,$G,$RF}"
echo "### G2 the self-collision decomposition, both links ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "ge_fix={$C,$L3,$GS,$W,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "ge_jit={$C,$L3,$GS,$W,\"retry_backoff\":18,\"retry_spread\":17}" \
  --arm "bern_fix={$C,$L3,$W,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "bern_jit={$C,$L3,$W,\"retry_backoff\":18,\"retry_spread\":17}"
echo "### G3 the reliance-loop sign flip ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={$C,\"n_blue\":5}" \
  --arm "ge_off={$C,\"n_blue\":5,$G}" \
  --arm "bern_retry={$C,\"n_blue\":5,$R}" \
  --arm "ge_retry={$C,\"n_blue\":5,$R,$G}"
done
