# CR-23R / CR-24R. THE SAME LADDERS ON A METRIC THE TREATMENT CANNOT INFLATE.
#
# Fable's catch on the CR-23 v2 table, and it is a real contamination of every retry contrast in
# this project. `operator_goodput = n_serviced / n_request`, and a retry MANUFACTURES requests: the
# failure cycle falls from `P + tau + 1` = 43 steps to `P + rho + 1`, so at rho = 2 a vehicle
# re-consults nearly twice as often and the denominator inflates on its own. Measured at n = 5,
# rung 3, GE-120: requests per step run 0.0870 with no retry, 0.1500 at rho = 2, 0.1031 at rho = 8
# and 0.0906 at rho = 21. Every goodput cell in that table therefore mixes real congestion with
# denominator inflation.
#
# `served_per_step` is the absolute rate and has no denominator to inflate. A first local read at
# 48 seeds says the contamination is large at n = 4 (goodput -0.203 at rho = 2, served rate only
# -14% of its own baseline against goodput's -30%) and nearly absent at n = 5 (-85% goodput against
# -80% served rate). If that holds at full tier the SHAPE of the CR-23 result survives its own
# contamination, which is worth knowing either way.
#
# REGISTERED, on Fable's construction rather than mine, because it is his account being retried:
#   1. The n = 4 damage collapses toward the determinism stratum of about -0.05 in relative terms.
#   2. The n = 5 half-damage backoff moves LEFT relative to the goodput reading.
#   3. If a knee re-emerges near rho = 10 to 12 on the absolute rate, the load rule REVIVES on the
#      metric it was derived for and CR-23's burial is withdrawn.
#   4. If the decline is still smooth at every span, the load rule is dead on its own metric and
#      Fable drops it.
# There is no way for me to win this one, which is the point of running it.
#
# Two cells added on Fable's Round 9 read of the n = 4 result. First, `rho = 22`: the deterministic
# hold then equals the standing consultation interval `tau`, so the retry arm re-consults on
# exactly the cadence the no-retry arm already uses and the cycle arithmetic is identical. Any
# residual difference at rho = 22 is determinism proper and not the extra attempts a shorter cycle
# buys, which is the confound the whole rho ladder otherwise carries. The unplanned n = 4 finding
# reads -0.052 gated on GE against -0.024 ungated on Bernoulli, and roughly -0.017 of the Bernoulli
# floor is cadence arithmetic alone (cycle 42 against 43 is 2.4% more attempts on a 0.688 base), so
# the quantity the pump clause is entitled to is the CROSS-CHANNEL difference of about -0.028 and
# not the -0.052. Second, the `n = 3` rung, where the post-fade spike books 15.6 steps against a
# patience of 20 and the account therefore predicts nothing to find.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
J='"retry_prob":1.0,"retry_spread":0'
GE_ARMS=()
BE_ARMS=()
for R in 2 4 6 8 10 12 14 16 18 21 22; do
  GE_ARMS+=(--arm "ge$R={$C,$G,$J,\"retry_backoff\":$R}")
  BE_ARMS+=(--arm "be$R={$C,$J,\"retry_backoff\":$R}")
done

for M in served_per_step requests_per_step; do
echo "### E1 the rho ladder on the coherent channel ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=3,4,5,6,8' \
  --arm "ge_noretry={$C,$G}" "${GE_ARMS[@]}"
done

echo "### E2 the Bernoulli ladder, including the other half of the discriminator (served_per_step)"
$PY tools/ar_eval.py $S --metric served_per_step $B --sweep 'n_blue=3,4,5,6,8' \
  --arm "be_noretry={$C}" "${BE_ARMS[@]}"

echo "### E3 CR-24's four arms on the same uncontaminated metric"
$PY tools/ar_eval.py $S --metric served_per_step $B --sweep 'n_blue=3,4,5,6,8' \
  --arm "noretry={$C,$G}" \
  --arm "fixed4={$C,$G,$J,\"retry_backoff\":4}" \
  --arm "fixed20={$C,$G,$J,\"retry_backoff\":20}" \
  --arm "adaptive={$C,$G,$J,\"retry_backoff\":4,\"retry_mode\":\"double\"}"
