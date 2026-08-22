# CR-26. THE SIGNAL NOTHING CONSUMED.
#
# The paper already reports that admission control has two halves and that they are not equal:
# discarding work the operator cannot finish carries most of the gain, and telling the requester
# adds a smaller increment that survives the gate only where a waiting asset is a stopped one.
# I recorded that as a fact. Fable's reading of it is sharper and it is a criticism of the model
# rather than of the world: a refusal IS a congestion signal in the sense of Floyd and Fall, and
# in this model NOTHING CONSUMES IT. The refused vehicle goes autonomous sooner and then comes
# back on exactly the same standing cadence, so the signal changes one wait and never once changes
# the offered load. In TCP the signal changes the sender's RATE. That is the whole disanalogy, and
# it is fixable rather than fundamental.
#
# `admit_response="aimd"` makes the vehicle consume it the way a sender does: halve its own request
# rate on a refusal, add back an eighth on each answered request, floored at a quarter of the
# standing rate. Verified byte-identical on the 29 pre-existing metrics when off.
#
# REGISTERED.
#   1. The NOTIFICATION SHARE grows to a majority. Without a response the share
#      (admit - refund)/(admit - blind) is the small half; with it, (aimd - refund)/(aimd - blind)
#      exceeds 0.5 at the collapsed spans.
#   2. AIMD beats plain `admit` on goodput ABOVE the collapse span and is indistinguishable from it
#      BELOW, because a vehicle that is never refused never halves anything and pays nothing.
# FALSIFIER: (i) aimd is not gated-better than admit at ANY span, in which case the signal still
# does nothing and the disanalogy with congestion control is deeper than signal consumption;
# (ii) aimd is gated-WORSE than admit below the collapse span, in which case the rule costs
# cadence where there is no congestion to pay for it and should not be recommended.
. hopper/batteries/_common.sh
RF='"queue_policy":"refund"'
AD='"queue_policy":"admit"'
AI='"queue_policy":"admit","admit_response":"aimd"'

for L in 0 2; do
for M in operator_goodput success; do
echo "### C$L the four policies across span at rung $L ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12' \
  --arm "blind={\"control_mode\":\"direct\",\"comms_level\":$L}" \
  --arm "refund={\"control_mode\":\"direct\",\"comms_level\":$L,$RF}" \
  --arm "admit={\"control_mode\":\"direct\",\"comms_level\":$L,$AD}" \
  --arm "aimd={\"control_mode\":\"direct\",\"comms_level\":$L,$AI}"
done
done
