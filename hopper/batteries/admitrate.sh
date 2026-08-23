# CR-31. IS ADMISSION CONTROL'S INVERSION REAL, OR IS IT THE DENOMINATOR AGAIN?
#
# `admit - refund` on operator_goodput goes -0.012, -0.066, -0.109, -0.131 at n = 6, 8, 10, 12 on
# the clear channel, at t up to -76 with 32/32 blocks. Taken at face value that is a scope limit on
# this paper's own recommendation: refusing work without a client-side rate rule is worse than
# merely refunding the time.
#
# But `operator_goodput = n_serviced / n_request`, and a refusal manufactures requests the same way
# a retry does. A refused vehicle returns to autonomy sooner and re-consults sooner, so the
# denominator inflates without anything about the console changing. CR-23R found exactly this
# contamination for retries; nothing about it was specific to retries.
#
# So the contrast is re-run on the absolute rate, which has no denominator, and on the request rate
# itself, which measures the inflation directly rather than inferring it.
#
# REGISTERED (doc/autoresearch-conjectures.md, CR-31):
#   PREDICTION. On served_per_step, admit - refund is negative and gates at n = 8, 10, 12 at rung 0.
#   FALSIFIER. If admit >= refund there, or the effect fails to gate, the goodput inversion is
#     denominator inflation: the doctrine sentence is WITHDRAWN and the goodput column is marked
#     contaminated, exactly as the CR-23 v2 ladder was.
#
# requests_per_step is the diagnostic either way. If admit inflates it and served_per_step is flat,
# the whole gap is bookkeeping. If admit inflates it AND served_per_step falls, both are true and
# the size of the real part is what the paper should quote.
. hopper/batteries/_common.sh
RF='"queue_policy":"refund"'
AD='"queue_policy":"admit"'
AI='"queue_policy":"admit","admit_response":"aimd"'

for L in 0 2; do
for M in served_per_step requests_per_step; do
echo "### E$L admit against refund on a metric with no denominator, rung $L ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12' \
  --arm "blind={\"control_mode\":\"direct\",\"comms_level\":$L}" \
  --arm "refund={\"control_mode\":\"direct\",\"comms_level\":$L,$RF}" \
  --arm "admit={\"control_mode\":\"direct\",\"comms_level\":$L,$AD}" \
  --arm "aimd={\"control_mode\":\"direct\",\"comms_level\":$L,$AI}"
done
done

# The mission metric, at the same spans, so the "costs console cycles, not missions" reading is
# stated on its own run rather than inherited from the aimd battery.
for L in 0 2; do
echo "### E$L the same four policies on the mission metric, rung $L (blue_loss_frac)"
$PY tools/ar_eval.py $S --metric blue_loss_frac $B --sweep 'n_blue=4,6,8,10,12' \
  --arm "blind={\"control_mode\":\"direct\",\"comms_level\":$L}" \
  --arm "refund={\"control_mode\":\"direct\",\"comms_level\":$L,$RF}" \
  --arm "admit={\"control_mode\":\"direct\",\"comms_level\":$L,$AD}" \
  --arm "aimd={\"control_mode\":\"direct\",\"comms_level\":$L,$AI}"
done
