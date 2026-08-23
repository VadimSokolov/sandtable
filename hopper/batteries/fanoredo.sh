# CR-37. THE P1 RE-RUN, AT A WINDOW CHOSEN FROM THE BENCH POWER CURVE.
#
# The original D1/D2 run set fano_window = 120, the channel dwell, on the reasoning that that is
# where the channel's structure lives. bench_fano says the estimator recovers 0.681 of a known
# injected cohort there at t = 4.7, against 0.936 at t = 25 with a window of 7. P1's refutation was
# read through an instrument with a fifth of the power, so its status is VOID pending this run.
#
# Window 7 = one service time at 0.15 per step. Chosen for two reasons that agree: the bench power
# curve, and the doctrine the episode established, that the window belongs to the mechanism's
# timescale and not the channel's. Window 1 has more power and is deliberately NOT chosen, because
# a one-step window asks whether two requests land on the same tick and the mechanism is about
# landing inside one service.
#
# Same arms as D1/D2 so the contrast is the window and nothing else. arrival_excess runs alongside
# at the same window, because a Fano is a variance and cannot tell many small clusters from few
# large ones.
#
#   P1R. On the bursty link, within each mean-matched pair, the jittered arm has a LOWER arrival
#     Fano at window 7, gated.
#   FALSIFIER. No gated reduction at window 7 either moves P1 from VOID to REFUTED and leaves it
#     there, with the instrument objection answered rather than outstanding.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
W='"retry_prob":1.0,"fano_window":7,"mult_window":7'

for M in arrival_fano arrival_excess operator_goodput; do
echo "### F1 the bursty link at a service-time window ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "fix04={$C,$G,$W,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$G,$W,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix10={$C,$G,$W,\"retry_backoff\":10,\"retry_spread\":0}" \
  --arm "jit10={$C,$G,$W,\"retry_backoff\":10,\"retry_spread\":9}" \
  --arm "fix18={$C,$G,$W,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$W,\"retry_backoff\":18,\"retry_spread\":17}"
echo "### F2 the memoryless control at the same window ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "fix04={$C,$W,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$W,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix18={$C,$W,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$W,\"retry_backoff\":18,\"retry_spread\":17}"
done

# CR-34 P4, Fable's free signature: the residual should GROW with the channel dwell and collapse as
# the dwell approaches the service time, because a gate that opens and closes faster than a service
# cannot hold a cohort together across one.
for M in arrival_excess operator_goodput; do
echo "### F3 the residual against dwell length ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'ge_burst_len=7,15,30,60,120,240' \
  --arm "fix18={$C,$G,$W,\"n_blue\":6,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$W,\"n_blue\":6,\"retry_backoff\":18,\"retry_spread\":17}"
done
