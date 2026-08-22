# The sharp prediction from `queue_theory.two_way_delivery_bursty`, registered before the run.
#
# A request-reply handshake needs two messages. A memoryless channel makes their fates
# independent, so d = (1-p)^2; a bursty channel correlates them, so d = (1-p)(1-p_gb) and MORE
# round trips complete at the same mean loss. Since n* = c(P+tau+1)mu/d, burstiness moves the
# collapse threshold LEFT. Predicted thresholds:
#
#   rung 2 (p=0.10):  bernoulli 7.96   gilbert-elliot 7.37
#   rung 3 (p=0.20):  bernoulli 10.08  gilbert-elliot 8.60
#
# So the sign of the burstiness effect must FLIP with span, and the flip must happen between the
# two predicted thresholds: below n*_GE the extra completed round trips are answers a vehicle
# wanted, above it they are load an operator cannot absorb. Registered: GE minus bernoulli is
# positive at small span, negative in the bracket (n*_GE, n*_bern), and converges again once both
# arms are collapsed. Rung 3 has the wider bracket and is the better resolved test.
. hopper/batteries/_common.sh
GE='"channel":"gilbert_elliot"'

echo "### S1 rung 3, span sweep: does the burstiness effect change sign inside (8.60, 10.08)?"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6,7,8,9,10,11,12' \
  --arm "bern={\"control_mode\":\"direct\",\"comms_level\":3}" \
  --arm "ge={\"control_mode\":\"direct\",\"comms_level\":3,$GE}"

echo "### S2 rung 2, the same sweep, narrower bracket (7.37, 7.96)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6,7,8,9,10,11,12' \
  --arm "bern={\"control_mode\":\"direct\",\"comms_level\":2}" \
  --arm "ge={\"control_mode\":\"direct\",\"comms_level\":2,$GE}"
