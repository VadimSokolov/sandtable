# CR-18. st-bspan gated a sign flip in the burstiness effect across span. It is an artifact.
#
# The Gilbert-Elliot chain advances one transition per MESSAGE, and `c2.step` drew the request and
# the reply back to back, so the model treated them as adjacent in channel time even though the
# operator's whole service delay (tens of steps) separates them. That inflates round-trip delivery
# from (1-p)^2 to (1-p)(1-p_gb) for a coding reason, not a physical one. Pricing the reply at the
# moment it is actually sent (`channel_clock="step"`) collapses realized delivery back onto the
# Bernoulli value at every rung: 0.7598 to 0.6478 against Bernoulli's 0.6348 at rung 3, n=8.
#
# Registered: under step clocking the S1 sign flip disappears and GE minus Bernoulli is null at
# every span. If it does not, the artifact story is wrong and the effect has a second channel.
#
# Bernoulli is untouched by the clock (there is no chain to clock), so every published gated cell
# is unaffected. This battery re-runs the Bernoulli arm anyway, as the check on that claim.
. hopper/batteries/_common.sh
GEM='"channel":"gilbert_elliot"'
GES='"channel":"gilbert_elliot","channel_clock":"step"'

echo "### K1 rung 3 span sweep under BOTH clocks: does the flip survive physical timing?"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6,7,8,9,10,11,12' \
  --arm "bern={\"control_mode\":\"direct\",\"comms_level\":3}" \
  --arm "ge_msg={\"control_mode\":\"direct\",\"comms_level\":3,$GEM}" \
  --arm "ge_step={\"control_mode\":\"direct\",\"comms_level\":3,$GES}"

echo "### K2 the clock must not touch a memoryless channel"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=1,2,3,4' \
  --arm "bern_msg={\"control_mode\":\"direct\",\"n_blue\":8}" \
  --arm "bern_step={\"control_mode\":\"direct\",\"n_blue\":8,\"channel_clock\":\"step\"}"
