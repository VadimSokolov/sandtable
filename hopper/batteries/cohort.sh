# CR-34. WHAT JITTER CAN AND CANNOT SCATTER, MEASURED NET OF DELIVERY RATE.
#
# The manuscript briefly carried the claim that a bursty channel's outage releases its vehicles at
# different instants, so the cohort is born pre-scattered and there is nothing for jitter to
# dissolve. Fable asked for the instrument that would decide it. The instrument refuted the claim
# in the opposite direction: GE arrivals are MORE clustered, not less.
#
# The instrument is collision multiplicity, `E[k | k >= 1]` over windows one service time long,
# because k requests inside one service is k-1 forced waits and that is the quantity the mechanism
# consumes. A Fano factor is a variance and cannot distinguish many small clusters from few large
# ones. The window matters: the D1 battery set `fano_window` to the CHANNEL DWELL of 120 on the
# reasoning that that is where the channel's structure lives, which is exactly backwards.
# `tools/bench_fano.py` at the dwell recovers only 0.46 of a known injected cohort on a memoryless
# stream and overshoots to 1.31 on an on-off one, at t = 4 where the same bench at a service-time
# window returns t > 300. The published Fano null was read through a window that had almost no
# power.
#
# And multiplicity is confounded by rate: `E[k | k >= 1]` rises with lambda for ANY process, and
# GE's two-way delivery is 0.798 against the memoryless 0.640, so GE looks clustered merely by
# delivering more. `arrival_excess` divides by the Poisson value at the arm's own delivered rate,
# `lw / (1 - exp(-lw))`, which is the scatter-only control and the only form comparable across
# channels.
#
# A 32-seed local probe at rho = 18, rung 3, deterministic against jittered:
#   bern n=5  excess 1.096 -> 1.001    bern n=6  1.099 -> 1.011
#   ge   n=5  excess 1.214 -> 1.042    ge   n=6  1.348 -> 1.083
#
# REGISTERED, at full tier and on more spans and pair means than the probe:
#   P1. On the memoryless channel the jittered arm's `arrival_excess` is statistically
#       indistinguishable from 1.0, i.e. randomizing the hold scatters the stream COMPLETELY,
#       because the hold is the only thing setting arrival phase there.
#   P2. On the GE channel the jittered arm's excess remains ABOVE 1.0 by a gated margin: the
#       channel gate is a second synchronizer downstream of the hold, and it re-clusters what the
#       hold scattered.
#   FALSIFIER for both: if the jittered GE excess also reaches 1.0, the channel adds no
#     irreducible clustering and the two-synchronizer account is withdrawn; if the jittered
#     memoryless excess stays above 1.0, the hold is not the only phase-setter even there and P1's
#     mechanism is wrong.
#   P3. The residual GE excess is what the goodput gain tracks, not the amount dissolved. GE
#       dissolves MORE (-0.173, -0.265) and gains LESS goodput than memoryless at n = 6, which only
#       makes sense if what is left over is what costs.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
P='"retry_prob":1.0','"mult_window":7'
W='"mult_window":7'

for M in arrival_excess arrival_multiplicity operator_goodput served_per_step; do
echo "### K1 memoryless: what the hold alone can scatter ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10' \
  --arm "fix04={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix18={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17}"
echo "### K2 GE-120: the gate downstream of the hold ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10' \
  --arm "fix04={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix18={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":18,\"retry_spread\":17}"
done

# CR-33. The residue's flip must MOVE with the pair mean if it is threshold-located at all.
# mean 4 puts the thresholds at 5.86 (memoryless) and 4.70 (GE); mean 18 at 9.14 and 7.33. So the
# crossing should sit near n=4-5 for the first and n=6-7 for the second. If it sits at 5-6 for both,
# neither the single-peak account nor its null survives.
for M in operator_goodput; do
for RHO in 4 18; do
echo "### K3 the dwell residue across span at pair mean $RHO ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,7,8,10,12' \
  --arm "bern_fix={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":$RHO,\"retry_spread\":0}" \
  --arm "bern_jit={$C,$W,\"retry_prob\":1.0,\"retry_backoff\":$RHO,\"retry_spread\":$((RHO-1))}" \
  --arm "ge_fix={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":$RHO,\"retry_spread\":0}" \
  --arm "ge_jit={$C,$G,$W,\"retry_prob\":1.0,\"retry_backoff\":$RHO,\"retry_spread\":$((RHO-1))}"
done
done
