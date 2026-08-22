# CR-16 full-tier confirm. The proxy tier (16x16) showed no separation anywhere, but its MDE is
# roughly 0.05-0.06 against an MPE of 0.03, so a flat proxy can only rule out a LARGE effect. A
# null claim needs the tier the contract defines a null on.
#
# Two cells, chosen because they are where the effect must be if it exists:
#   Y1  the strongest heterogeneity at the congested span. If priority matters at all, the gap
#       between hard_first and easy_first is widest where the ground varies most.
#   Y2  the single proxy cell that gated (n=10, terrain_demand=2), which favored easy_first, the
#       ADVERSARIAL control. Re-run to see whether it survives or was a multiple-comparison
#       artifact across ~48 gated cells.
. hopper/batteries/_common.sh

echo "### Y1 strongest coupling at the congested span, full tier"
$PY tools/ar_eval.py $S --metric success $B --sweep 'terrain_demand=4' \
  --arm "random={$D,\"n_blue\":8,\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"n_blue\":8,\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"n_blue\":8,\"queue_discipline\":\"easy_first\"}"

echo "### Y2 the one proxy cell that gated, re-run at full tier (n=10, terrain_demand=2)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=10' \
  --arm "random={$D,\"terrain_demand\":2,\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"terrain_demand\":2,\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"terrain_demand\":2,\"queue_discipline\":\"easy_first\"}" \
  --arm "fcfs={$D,\"terrain_demand\":2}"

echo "### Y3 goodput at the same two cells: the throughput-invariance claim at full tier"
for TD in 2 4; do
echo "## terrain_demand=$TD"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep "terrain_demand=$TD" \
  --arm "fcfs={$D,\"n_blue\":8}" \
  --arm "random={$D,\"n_blue\":8,\"queue_discipline\":\"random\"}" \
  --arm "hard={$D,\"n_blue\":8,\"queue_discipline\":\"hard_first\"}" \
  --arm "easy={$D,\"n_blue\":8,\"queue_discipline\":\"easy_first\"}"
done
