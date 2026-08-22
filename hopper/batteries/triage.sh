# CR-16. Does the ORDER the operator serves arrivals in matter, once admission control exists?
#
# Pre-registered in doc/autoresearch-conjectures.md: ordering cannot change how many requests are
# served, only which vehicle is served, so any effect must come from heterogeneity in what the help
# is worth. Two controls are built into the design rather than bolted on afterwards:
#   random     -- the NULL. Reordering also reassigns which entity draws which random number, so a
#                 priority arm moves two things at once. `random` moves only the RNG assignment.
#   easy_first -- the ADVERSARY for hard_first. A real priority effect must be two-sided.
# A flat result across all four arms is a publishable negative, not a failed run.
. hopper/batteries/_common.sh

echo "### X1 ordering with NO heterogeneity (terrain_demand=0). Prediction: all four agree."
for M in operator_goodput success; do
echo "## metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10' \
  --arm "fcfs={$D}" \
  --arm "random={$D,\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"queue_discipline\":\"easy_first\"}"
done

echo "### X2 ordering WITH heterogeneity (terrain_demand=2), across span. If ordering ever bites"
echo "###    it is in the congested band just above n*=6.30, not below it (no queue) and not far"
echo "###    above it (nothing serviceable). Band-limited, not monotone."
for M in operator_goodput success; do
echo "## metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12' \
  --arm "fcfs={$D,\"terrain_demand\":2}" \
  --arm "random={$D,\"terrain_demand\":2,\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"terrain_demand\":2,\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"terrain_demand\":2,\"queue_discipline\":\"easy_first\"}"
done

echo "### X3 does admission control absorb whatever ordering was worth? Same contrast, admit on."
echo "###    If ordering only ever mattered because blind wastes slots, this row should be flat"
echo "###    even where X2 is not."
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=6,8,10,12' \
  --arm "fcfs={$D,\"terrain_demand\":2,\"queue_policy\":\"admit\"}" \
  --arm "random={$D,\"terrain_demand\":2,\"queue_policy\":\"admit\",\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"terrain_demand\":2,\"queue_policy\":\"admit\",\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"terrain_demand\":2,\"queue_policy\":\"admit\",\"queue_discipline\":\"easy_first\"}"

echo "### X4 coupling strength at the congested span. Ordering should matter more the more the"
echo "###    ground varies, if it matters at all."
$PY tools/ar_eval.py $S --metric success $B --sweep 'terrain_demand=0,1,2,4' \
  --arm "random={$D,\"n_blue\":8,\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"n_blue\":8,\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"n_blue\":8,\"queue_discipline\":\"easy_first\"}"
