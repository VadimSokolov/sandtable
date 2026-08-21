# P2, the sharpest test of the closed form: n* = (patience + decision_interval) * service_rate
# depends on the OPERATOR, not the link. Moving service_rate must move the collapse threshold
# and therefore must create or destroy the interior optimum at a fixed span.
#   sr=0.30  -> n* = 12.6, so n=8 is stable and the interior optimum must VANISH
#   sr=0.15  -> n* =  6.3, so n=8 is collapsed and the optimum must be present (published)
#   sr=0.075 -> n* =  3.15, so n=4 is collapsed and an optimum must APPEAR where there was none
. hopper/batteries/_common.sh
for M in operator_goodput success; do
echo "### P2 metric=$M"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3' \
  --arm 'n8_fast={"control_mode":"direct","n_blue":8,"service_rate":0.30}' \
  --arm 'n8_pub={"control_mode":"direct","n_blue":8}' \
  --arm 'n4_slow={"control_mode":"direct","n_blue":4,"service_rate":0.075}' \
  --arm 'n4_pub={"control_mode":"direct","n_blue":4}'
done
echo "### P2b patience also moves the LATENCY cut-off: (patience - 1/service_rate)/2"
echo "###     p=20 -> 6.67 steps, so C4 (lat 8) and C5 (lat 16) are the same rung"
echo "###     p=30 -> 11.67, so C4 separates from C5"
echo "###     p=45 -> 19.17, so both resolve"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'comms_level=3,4,5' \
  --arm 'pat20={"control_mode":"direct","n_blue":4,"patience":20}' \
  --arm 'pat30={"control_mode":"direct","n_blue":4,"patience":30}' \
  --arm 'pat45={"control_mode":"direct","n_blue":4,"patience":45}'
