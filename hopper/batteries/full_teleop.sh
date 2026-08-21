# G4: the remaining full-tier gate. Admission control under CR-2 teleoperation physics,
# where a vehicle with no answer coming back actually stops. Pre-registered contrast.
. hopper/batteries/_common.sh
TB='"control_mode":"direct","n_blue":8,"blue_behavior":"auto","teleop_stop":true'
echo "### G4 FULL TIER: teleop physics, n=8, direct, C0 and C2"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=0,2' \
  --arm "blind={$TB}" \
  --arm "admit={$TB,\"queue_policy\":\"admit\"}"
echo "### G4b same contrast under a staggered start (robustness)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=0' \
  --arm "blind={$TB,\"stagger_decisions\":true}" \
  --arm "admit={$TB,\"stagger_decisions\":true,\"queue_policy\":\"admit\"}"
