# CR-24. THE RULE INSTEAD OF THE NUMBER.
#
# CR-23 measures where the jam floor rho*(n,d) = n d/(c mu) - (P+1) sits. A console cannot use that
# number: it does not know n at design time, it certainly does not know d, and both move during a
# mission. The fielded form of this fix is the one Ethernet and TCP already use, doubling the hold
# on consecutive unanswered requests and resetting it the moment a request is served. It reaches the
# floor from below without measuring anything and it pays nothing when the system is healthy,
# because a healthy vehicle never accumulates a streak.
#
#   streak  0  1  2  3  4+          (base rho = 4, capped at the standing interval tau = 22)
#   hold    4  4  8 16 22
#
# So it clears rho* = 5 on the second unanswered request, rho* = 10 on the third, and rho* = 20 on
# the fourth, which is the ladder CR-23 predicts for n = 5, 6 and 8.
#
# REGISTERED, as a DOMINANCE claim, which is the only kind worth shipping to a sponsor:
#   1. At every span and on both channels the adaptive arm is at least as good as the BETTER of
#      fixed rho=4 and fixed rho=20, to within the gate.
#   2. It gets there from opposite directions: it beats fixed-4 where the team is jammed (n >= 6)
#      and it matches fixed-4, not fixed-20, where the team is healthy (n = 4, and rung 0).
#   3. At rung 0 it is indistinguishable from fixed-4, because there is no streak to accumulate.
# FALSIFIER: the adaptive arm is gated-WORSE than max(fixed-4, fixed-20) at any cell; or it fails
# to separate from fixed-20 in the healthy cells, which would mean it is just a slow retry wearing
# a costume and the sponsor should be told the number after all.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
C0='"control_mode":"direct","comms_level":0'
F4='"retry_prob":1.0,"retry_backoff":4'
F20='"retry_prob":1.0,"retry_backoff":20'
AD='"retry_prob":1.0,"retry_backoff":4,"retry_mode":"double"'

echo "### A1 dominance across span, coherent channel (goodput)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=4,5,6,8' \
  --arm "noretry={$C,$G}" --arm "fixed4={$C,$G,$F4}" \
  --arm "fixed20={$C,$G,$F20}" --arm "adaptive={$C,$G,$AD}"

echo "### A2 the same, on mission success"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=4,5,6,8' \
  --arm "noretry={$C,$G}" --arm "fixed4={$C,$G,$F4}" \
  --arm "fixed20={$C,$G,$F20}" --arm "adaptive={$C,$G,$AD}"

echo "### A3 dominance across span, Bernoulli channel (goodput)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=4,5,6,8' \
  --arm "noretry={$C}" --arm "fixed4={$C,$F4}" \
  --arm "fixed20={$C,$F20}" --arm "adaptive={$C,$AD}"

echo "### A4 the healthy cell: no latency paid where none is owed (rung 0, goodput)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=4,6,8' \
  --arm "fixed4={$C0,$G,$F4}" --arm "fixed20={$C0,$G,$F20}" --arm "adaptive={$C0,$G,$AD}"

echo "### A5 and the same at the published operating point, six vehicles across the ladder"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'comms_level=0,1,2,3,4' \
  --arm "noretry={\"control_mode\":\"direct\",$G}" \
  --arm "fixed4={\"control_mode\":\"direct\",$G,$F4}" \
  --arm "adaptive={\"control_mode\":\"direct\",$G,$AD}"
