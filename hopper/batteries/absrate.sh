# CR-35 and CR-36. THE PAPER'S GOODPUT CONTRASTS, RE-READ ON METRICS WITH NO DENOMINATOR.
#
# CR-31 found operator_goodput inflatable by any treatment that changes the asking, and every queue
# policy in this paper changes it: a refusal returns a vehicle to autonomy sooner so it re-consults
# sooner (+32.4% requests at n=12), and an AIMD rule suppresses re-consultation by construction
# (-40.9%). The metric penalizes the first and flatters the second, and the paper's third lever was
# stated as a throughput gain when the console in fact serves 4% LESS.
#
# CR-23R established this for retries. It was never carried to the policies. This battery carries it.
#
# A1/A2 is CR-36, the audit: every arm pair the manuscript reports on goodput, on the absolute rate.
# A3 is CR-35, registered: whether the service AIMD forgoes is service that would have been wasted.
#   PREDICTION. aimd - admit on abandoned_per_step is negative, gated, and larger in RELATIVE
#     magnitude than the same contrast on served_per_step, at n = 8, 10, 12 on both rungs.
#   FALSIFIER. If abandonment falls by the same relative amount as service or less, or wasted_frac
#     does not fall, the "suppresses doomed work" mechanism is WITHDRAWN and the manuscript reports
#     the outcome gain without an explanation for it.
. hopper/batteries/_common.sh
RF='"queue_policy":"refund"'
AD='"queue_policy":"admit"'
AI='"queue_policy":"admit","admit_response":"aimd"'

for L in 0 3; do
for M in served_per_step requests_per_step abandoned_per_step wasted_frac success; do
echo "### A$L the four policies across span at rung $L ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,4,6,8,10,12,16' \
  --arm "blind={\"control_mode\":\"direct\",\"comms_level\":$L}" \
  --arm "refund={\"control_mode\":\"direct\",\"comms_level\":$L,$RF}" \
  --arm "admit={\"control_mode\":\"direct\",\"comms_level\":$L,$AD}" \
  --arm "aimd={\"control_mode\":\"direct\",\"comms_level\":$L,$AI}"
done
done

# The centerpiece operating point the abstract quotes, on every metric at once, so the headline
# sentence can be checked against one table rather than assembled from four.
for M in served_per_step requests_per_step abandoned_per_step wasted_frac success blue_loss_frac; do
echo "### A4 the centerpiece point, n=8, across the comms ladder ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3,4,5' \
  --arm "blind={\"control_mode\":\"direct\",\"n_blue\":8}" \
  --arm "refund={\"control_mode\":\"direct\",\"n_blue\":8,$RF}" \
  --arm "admit={\"control_mode\":\"direct\",\"n_blue\":8,$AD}" \
  --arm "aimd={\"control_mode\":\"direct\",\"n_blue\":8,$AI}"
done
