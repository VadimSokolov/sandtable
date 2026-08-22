# Does the throughput cliff survive a longer mission window? The zeros at n>=10 come from a
# formation moving at roughly 36% of top speed against a fixed 1800 s deadline, so a longer
# window should convert "none arrive" into "they arrive late". The non-monotonicity and its
# location should survive; the exact zero should not.
#
# `duration` is a Scenario field rather than a params entry, and tools/ar_eval.py is frozen,
# so the arms are separate scenario FILES that differ only in that field. Their `id` is
# deliberately unchanged, because make_rng keys the stream on it and keeping it fixed leaves
# the three windows paired on common random numbers.
. hopper/batteries/_common.sh
TB='"control_mode":"direct","comms_level":0,"blue_behavior":"auto","teleop_stop":true'
for M in arrived success; do
for SCN in scenarios/sc_span_control.json \
           experiments/ar_scenarios/sc_span_control_d3600.json \
           experiments/ar_scenarios/sc_span_control_d7200.json; do
echo "### DURATION metric=$M scenario=$(basename $SCN .json)"
$PY tools/ar_eval.py --scenario "$SCN" --metric $M $B --sweep 'n_blue=4,6,8,10,12' \
  --arm "blind={$TB}" \
  --arm "admit={$TB,\"queue_policy\":\"admit\"}"
done; done
