# CR-38 RIDER. THE EQUIVALENCE OWES A TAIL BEFORE IT GOES TO A SPONSOR.
#
# "One console with software equals two blind consoles" is now an affirmative equivalence on
# mission success and delivered service, at six operating points, against the same materiality
# floor the gate uses to call a difference real. Adversarial review's objection: two queues can
# match on throughput and differ entirely in their tails, and a requester does not experience a
# mean. If the single console makes the same number of decisions but a tenth of its clients wait
# twice as long, the sentence a program office reads is wrong in the way that matters.
#
# `wait_p95` is already computed in metrics.py and no battery has ever logged it. This one does,
# on exactly the staffeq arms, so the tail can be TOSTed against the same margin.
#
# REGISTERED before any arm is read:
#   P1. One console with the rate rule is EQUIVALENT to two blind consoles on wait_p95 at n = 10,
#       12 and 16, clear and jammed, against a margin of FULL_MPE times the two-console level.
#   FALSIFIER. Failing equivalence at two or more of the six cells means the throughput
#     equivalence does not carry to the tail, and the sponsor-facing sentence is narrowed to
#     "equal in decisions delivered, not in what a requester waits."
#   P2 (direction, in case P1 fails). If the tails differ, the single console's is the LONGER,
#       because one server has no second queue to overflow into.
#   FALSIFIER. A single console with a SHORTER tail than two consoles refutes the queueing reading
#     of the whole section and would need explaining before anything else here is trusted.
. hopper/batteries/_common.sh
AD='"queue_policy":"admit"'
AI='"queue_policy":"admit","admit_response":"aimd"'

for L in 0 3; do
for M in wait_p95 mean_wait; do
echo "### G$L the tail of the wait, rung $L ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,10,12,16' \
  --arm "c1_blind={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1}" \
  --arm "c1_admit={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1,$AD}" \
  --arm "c1_aimd={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":1,$AI}" \
  --arm "c2_blind={\"control_mode\":\"direct\",\"comms_level\":$L,\"n_operators\":2}"
done
done
