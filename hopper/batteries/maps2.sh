# CR-52 P3, ALONE, AT A RESOLUTION THAT CAN ANSWER IT.
#
# The maps battery (job 9448824) registered three predictions and its sweep can only answer two.
# P1 (the admit-over-blind lever holds its sign and gates on both new maps) and P2 (the capacity
# ladder's argmax is unchanged by the map) are settled and both hold. P3 said the collapse span is
# SMALLER on chokepoint than on band, and the sweep it was registered against steps 4, 6, 8, so the
# collapse lands between 6 and 8 on all three maps and the prediction is unfalsifiable there. It is
# recorded as untestable at that resolution rather than as held, and this battery is the resolution.
#
# n* = c(P + tau + 1)mu / d is a property of the CONSOLE and carries nothing about terrain, so the
# null is that the three maps collapse at the same span. P3 needs a mechanism to beat that null, and
# the one it was registered on is that a chokepoint concentrates the force where the map chooses, so
# assets arrive at their decisions together and the console sees a burstier arrival process at the
# same mean rate. That predicts an earlier collapse WITHOUT any change to n*, which is a second
# prediction and a sharper one.
#
#   P3a. the blind console's delivered service falls below half its peak at a smaller span on
#        chokepoint than on band, by at least one span.
#   P3b, the mechanism: the arrival process is burstier on chokepoint at the same mean. Read as
#        requests_per_step (the mean, which should NOT separate) against backlog_mean at a span
#        below collapse (which should, if arrivals are clumped).
#   P3c, the harm: starved_frac at the collapse span is HIGHER on chokepoint, for the same reason.
#
# FALSIFIER for P3a: if the half-peak span is the same on all three maps to within one sweep step,
# P3 is retracted and the record says the collapse span is a console property that terrain does not
# reach, which is the more useful negative anyway.
. hopper/batteries/_common.sh
BLIND='"control_mode":"direct","comms_level":0'
CHOKE='"terrain_profile":"chokepoint"'
OPEN='"terrain_profile":"open"'

# N1 is on the PUBLISHED reservation console, which is the one M1 measured and the one P3a is a
# prediction about. N2 repeats it on the buffer console, because P3b is about a BACKLOG and a
# reservation console does not have one: `backlog_mean` is identically zero there, so reading the
# mechanism on N1 would be reading a constant. Defect 8 is one page up in the log and this is what
# not repeating it looks like.
for M in served_per_step requests_per_step starved_frac success; do
echo "### N1 the collapse span at one-asset resolution, reserve ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,7,8,9,10' \
  --arm "band={$BLIND}" \
  --arm "choke={$BLIND,$CHOKE}" \
  --arm "open={$BLIND,$OPEN}"
done

for M in served_per_step requests_per_step backlog_mean starved_frac stale_per_step; do
echo "### N2 the same on the buffer console, where the mechanism is readable ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,7,8,9,10' \
  --arm "band={$DB}" \
  --arm "choke={$DB,$CHOKE}" \
  --arm "open={$DB,$OPEN}"
done
