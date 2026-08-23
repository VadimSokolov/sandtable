# CR-41 CLOSING ARM. The no-retry control at every dwell, so line 2 of the decomposition is
# established at all ten points rather than at one.
#
# The dwellow sweep showed the jittered arm's residual flat at +0.055 across a 240-fold dwell range,
# and the noretry battery showed the no-retry arm at +0.053 at one of those dwells. If they are the
# same quantity the identity should hold at every dwell, and if it does not, the flat residual has a
# dwell-independent source that is not the no-retry baseline and needs its own account.
#
#   P1. jit18 - noretry on arrival_excess is null at all ten dwells, paired, so the null cancels.
#   FALSIFIER. A gated gap at any dwell means the jittered arm is NOT at the no-retry baseline and
#     the four-term decomposition loses its second line.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step"'
C='"control_mode":"direct","comms_level":3'
W='"fano_window":7,"mult_window":7'

for M in arrival_excess arrival_rate arrival_ge2 arrival_ge3; do
echo "### N1 the no-retry line at every dwell ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'ge_burst_len=1,2,3,5,7,15,30,60,120,240' \
  --arm "noretry={$C,$G,$W,\"n_blue\":6,\"retry_prob\":0.0}" \
  --arm "jit18={$C,$G,$W,\"n_blue\":6,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17}" \
  --arm "fix18={$C,$G,$W,\"n_blue\":6,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":0}"
done
