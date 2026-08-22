# CR-19e. The correction to CR-19's lag produced a prediction the coherence battery does not test:
# a CR-17 retry at rho = 4 cuts the failed-request cycle from P+tau+1 = 43 steps to P+rho+1 = 25,
# and the cycle is the interval at which a vehicle re-consults the channel. So the within-vehicle
# coherence knee moves from a dwell of 54.4 down to 31.9, and a team that closes its reliance loop
# faster is MORE exposed to the link's burst structure, not less. The same shortened cycle that
# opens a fold band makes channel memory visible.
#
# L = 40 is the straddle: theta_v is 0.73 without the retry and 1.26 with it, so the retry alone
# carries the arm across the knee while nothing else changes. L = 4 is deep below it on both sides
# and L = 120 deep above on both, so the DiD in the predicted excess is 1e-4, 0.159, 0.111: an
# INTERIOR MAXIMUM near the straddle, which is the falsifier. A monotone rise in L refutes the
# mechanism as stated even if every cell gates.
#
# n_blue = 5 sits below n_c = 5.86 at this rung with the retry on, so the cell is outside the fold
# band and single-state; putting it inside would add initial-condition variance to a contrast that
# is not about initial conditions. Retry-off arms carry the same span so the pairing is exact.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step"'
R='"retry_prob":1.0,"retry_backoff":4'
C='"control_mode":"direct","comms_level":3,"n_blue":5'

for M in success wait_p95 queue_depth_mean; do
echo "### M-$M does a faster reliance loop buy more exposure to burst structure?"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'ge_burst_len=4,40,120' \
  --arm "bern_off={$C}" \
  --arm "bern_retry={$C,$R}" \
  --arm "ge_off={$C,$G}" \
  --arm "ge_retry={$C,$R,$G}"
done
