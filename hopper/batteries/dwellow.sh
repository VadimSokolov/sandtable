# CR-41. THE COLLAPSE LIMB, AT DWELLS BELOW ONE SERVICE.
#
# CR-34 P4 predicted the excess residual grows with the channel dwell L and collapses as L approaches
# the service time. F3 confirmed the growth limb monotonically over L = 7..240. It did not test the
# collapse limb: its lowest point, L = 7, IS the service window, and a dwell equal to the window is
# the most favorable configuration for producing multiplicity there is. This runs the dwells the
# prediction actually names.
#
#   P1. The residual falls monotonically below L = 7 and is not gated at L = 1.
#   FALSIFIER. Flat or still growing below one service refutes the gate account of the residual.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step"'
C='"control_mode":"direct","comms_level":3'
W='"retry_prob":1.0,"fano_window":7,"mult_window":7'

for M in arrival_excess arrival_multiplicity arrival_rate arrival_repeat_frac; do
echo "### D1 the residual below one service ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'ge_burst_len=1,2,3,5,7,15,30' \
  --arm "fix18={$C,$G,$W,\"n_blue\":6,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$W,\"n_blue\":6,\"retry_backoff\":18,\"retry_spread\":17}"
done
