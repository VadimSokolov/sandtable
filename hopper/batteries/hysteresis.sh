# CR-17. Closed-loop reliance: a vehicle whose request went unanswered asks again after
# `retry_backoff` steps instead of the standing `decision_interval`. Offered load then depends on
# the state the queue is already in, and `tools/queue_theory.py:fold_band` predicts the threshold
# splits into a band (n_c, n_h) inside which BOTH the healthy and the collapsed state sustain
# themselves. At the published operating point with pi=1, rho=4 the band is (3.75, 5.85), so five
# vehicles are inside it and three and eight are not.
#
# Bistability is a statement about initial conditions, so the arms differ only in one:
# `stagger_decisions` spreads the vehicles' first decision events (a healthy start) against the
# default synchronized burst (which is what every published run uses). Staggering also perturbs
# the RNG stream and has its own direct effect on the mission, so the RETRY-OFF arm is the
# control and the quantity that tests the claim is the difference of differences,
#   [stag - burst | retry]  -  [stag - burst | no retry],
# which must be large at five vehicles and null at three and eight.
. hopper/batteries/_common.sh
R='"retry_prob":1.0,"retry_backoff":4'

echo "### H1 mission outcome: is the initial condition load-bearing only inside the band?"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=3,4,5,6,8' \
  --arm "burst_retry={$D,$R}" \
  --arm "stag_retry={$D,$R,\"stagger_decisions\":true}" \
  --arm "burst_off={$D}" \
  --arm "stag_off={$D,\"stagger_decisions\":true}"

echo "### H2 the same contrast on the queue itself, where the mechanism is legible"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=3,4,5,6,8' \
  --arm "burst_retry={$D,$R}" \
  --arm "stag_retry={$D,$R,\"stagger_decisions\":true}" \
  --arm "burst_off={$D}" \
  --arm "stag_off={$D,\"stagger_decisions\":true}"

echo "### H3 does admission control close the band? Five vehicles, retry on, all three policies."
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'queue_policy=blind,refund,admit' \
  --arm "burst={$D,\"n_blue\":5,$R}" \
  --arm "stag={$D,\"n_blue\":5,$R,\"stagger_decisions\":true}"

echo "### H4 backoff floor: rho >= tau - 1/(c*mu*pi) = 15.33 should close the band at n=5"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'retry_backoff=4,8,12,16,20' \
  --arm "burst={$D,\"n_blue\":5,\"retry_prob\":1.0}" \
  --arm "stag={$D,\"n_blue\":5,\"retry_prob\":1.0,\"stagger_decisions\":true}"
