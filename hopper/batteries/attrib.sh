# CR-25. THE SIGN REVERSAL, ATTRIBUTED, OR ELSE GIVEN AWAY.
#
# `st-forceratio-9445778` measured, all gated at 32 blocks x 64 reps: sweeping span with the
# defenders fixed at four RAISES mission success +0.555 from three to fifteen, and sweeping the
# same span with the force ratio held at 1.5 LOWERS it -0.676. DiD +1.231, t = +75.9, 32/32. The
# steepest single step is n=6 to n=9 at held ratio, -0.440, t = -31.2.
#
# I want to report that as a result about span of control. Fable's objection is that three channels
# are live and I have attributed the whole of it to one:
#
#   1. CONSOLE CONGESTION. Operator goodput falls 0.759 to 0.160 over exactly that step.
#   2. FORCE GEOMETRY. Holding the ratio scales n_red, which deepens the defending column on one
#      lane rather than widening the engagement. That is a scenario fact, not a teaming one.
#   3. THRESHOLD CONCENTRATION. `success` is the one bit `arrived >= 0.5 * n_blue`. At a FIXED
#      per-vehicle arrival probability the binomial gets SHARPER as n grows, so a step in success
#      can be a step in the fraction or a step across the cut, and the published metric cannot
#      tell them apart. `arrived_frac` is added here for exactly this reason.
#
# REGISTERED. Supervisory control has no console at all, so it bounds channels 2 and 3 together;
# refund keeps the console but stops it spending slots on requesters who have gone.
#   (a) SUPERVISORY at held ratio falls by LESS THAN HALF the direct arm's -0.440 step.
#       FALSIFIER: it falls by more than 0.30, i.e. at least 68% of the direct step, in which case
#       the reversal is a scenario result and must be reported as one.
#   (b) REFUND at held ratio recovers at least half the direct step at n=9.
#       FALSIFIER: it recovers less than 0.10.
#   (c) `arrived_frac` on the direct held-ratio arm falls monotonically, so the reversal is a real
#       fall in the delivered fraction. FALSIFIER: it is flat or rising while success falls, which
#       makes the headline a threshold artifact and must be said in those words.
#
# Predictions (a) and (c) can each independently take the result away from me. That is the point.
. hopper/batteries/_common.sh
C0='"comms_level":0'
RF='"queue_policy":"refund"'
R3='"n_blue":3,"n_red":2'; R6='"n_blue":6,"n_red":4'; R9='"n_blue":9,"n_red":6'
R12='"n_blue":12,"n_red":8'; R15='"n_blue":15,"n_red":10'

for M in success arrived_frac; do
echo "### T1 held force ratio, three control regimes ($M)"
$PY tools/ar_eval.py $S --metric $M $B \
  --arm "dir03={$C0,\"control_mode\":\"direct\",$R3}" \
  --arm "dir06={$C0,\"control_mode\":\"direct\",$R6}" \
  --arm "dir09={$C0,\"control_mode\":\"direct\",$R9}" \
  --arm "dir12={$C0,\"control_mode\":\"direct\",$R12}" \
  --arm "dir15={$C0,\"control_mode\":\"direct\",$R15}" \
  --arm "ref03={$C0,\"control_mode\":\"direct\",$RF,$R3}" \
  --arm "ref06={$C0,\"control_mode\":\"direct\",$RF,$R6}" \
  --arm "ref09={$C0,\"control_mode\":\"direct\",$RF,$R9}" \
  --arm "ref12={$C0,\"control_mode\":\"direct\",$RF,$R12}" \
  --arm "ref15={$C0,\"control_mode\":\"direct\",$RF,$R15}" \
  --arm "sup03={$C0,\"control_mode\":\"supervisory\",$R3}" \
  --arm "sup06={$C0,\"control_mode\":\"supervisory\",$R6}" \
  --arm "sup09={$C0,\"control_mode\":\"supervisory\",$R9}" \
  --arm "sup12={$C0,\"control_mode\":\"supervisory\",$R12}" \
  --arm "sup15={$C0,\"control_mode\":\"supervisory\",$R15}"
done

for M in success arrived_frac; do
echo "### T2 defenders fixed at four, the same three regimes ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=3,6,9,12,15' \
  --arm "dir={$C0,\"control_mode\":\"direct\",\"n_red\":4}" \
  --arm "ref={$C0,\"control_mode\":\"direct\",$RF,\"n_red\":4}" \
  --arm "sup={$C0,\"control_mode\":\"supervisory\",\"n_red\":4}"
done
