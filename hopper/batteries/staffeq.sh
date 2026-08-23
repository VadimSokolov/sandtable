# CR-38. THE STAFFING EQUIVALENCE, ON METRICS WITH NO DENOMINATOR.
#
# The staffing table reads 17.0 / 73.4 / 99.0 at eight assets for one blind console, one console
# with admission control, and two blind consoles. That says the software lever buys most of a second
# operator, which is the single most sponsor-legible claim available here.
#
# It is built on operator_goodput. CR-31 showed `admit` inflates its own denominator by up to 32%
# while a second console changes nothing about the asking, so the table compares an arm whose
# denominator moved against one whose did not. That is exactly the configuration that produced the
# spurious -0.131 "inversion".
#
# REGISTERED (CR-38):
#   P1. On served_per_step and success, one console with admit still sits BETWEEN one and two blind
#       consoles at n = 8, 10, 12. The equivalence survives; only its size changes.
#   FALSIFIER. If it falls at or below one blind console on the absolute rate, the equivalence is a
#     metric artifact and the table is withdrawn rather than restated.
#   P2. The AIMD rule looks WORSE than plain admit on served_per_step and BETTER on success, so the
#       staffing question has two answers depending on which is asked.
#   FALSIFIER. Winning or losing on both drops the framing and reports whichever it wins on.
. hopper/batteries/_common.sh
RF='"queue_policy":"refund"'
AD='"queue_policy":"admit"'
AI='"queue_policy":"admit","admit_response":"aimd"'

for L in 0 3; do
for M in served_per_step success requests_per_step abandoned_per_step operator_goodput; do
echo "### G$L consoles against software, rung $L ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,4,6,8,10,12,16' \
  --arm "c1_blind={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1}" \
  --arm "c1_refund={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1,$RF}" \
  --arm "c1_admit={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1,$AD}" \
  --arm "c1_aimd={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1,$AI}" \
  --arm "c2_blind={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":2}" \
  --arm "c3_blind={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":3}"
done
done
