# The strongest cell of `st-coherence-9444790` and the control that decides how to read it.
#
# L3 measured, at eight vehicles and rung 3 on mission success: a link whose outages last 120 steps
# costs a BLIND operator -0.0742 (t = -5.43, 28 of 32 blocks) against a memoryless link at the same
# marginal rate, and costs a REFUNDING operator +0.0083 (t = 0.59), nothing. The policy interaction
# gates at -0.0825 (t = -3.87). Meanwhile refunding on a memoryless link buys +0.0229 and does not
# gate. So the value of refund is not a constant: it is near zero on a smooth link and worth ten
# points on a bursty one.
#
# Two things could produce that and they need separating.
#   (a) STRUCTURAL. Bursts concentrate failures into runs, runs produce requests the operator
#       cannot finish inside the requester's patience, and a blind operator spends a full service
#       slot on every one of them. Refund is exactly the policy that stops paying for those.
#   (b) FIRST MOMENT. A coherent channel raises round-trip delivery d from 0.640 to 0.789, so
#       n* = c mu Lambda / d falls from 10.08 to 8.17 and eight vehicles walk from 0.79 to 0.98 of
#       the collapse span. Refund raises effective capacity, so the refunding arm sits further from
#       the cliff and is less sensitive to the same shift. No structure required.
#
# `reply_model=marginal` pins d at 0.640 for every dwell, so the mg arms carry (a) without (b). And
# the span sweep tests (b) on its own terms: if distance from the cliff is doing the work, the
# blind penalty must shrink at five and six vehicles and grow at ten.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
M='"reply_model":"marginal"'
RF='"queue_policy":"refund"'
C='"control_mode":"direct","comms_level":3'

echo "### Q1 is the policy interaction structural or the collapse walk? (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6,8,10' \
  --arm "bern_blind={$C}" \
  --arm "co_blind={$C,$G}" \
  --arm "mg_blind={$C,$G,$M}" \
  --arm "bern_ref={$C,$RF}" \
  --arm "co_ref={$C,$G,$RF}" \
  --arm "mg_ref={$C,$G,$RF,$M}"

echo "### Q2 the same on the queue, where the mechanism is supposed to live"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=5,6,8,10' \
  --arm "bern_blind={$C}" \
  --arm "co_blind={$C,$G}" \
  --arm "mg_blind={$C,$G,$M}" \
  --arm "bern_ref={$C,$RF}" \
  --arm "co_ref={$C,$G,$RF}" \
  --arm "mg_ref={$C,$G,$RF,$M}"
