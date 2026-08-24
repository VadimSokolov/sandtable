# CR-71. THE TIER-1 SIDE OF THE CROSS-TIER BRIDGE, REGISTERED BEFORE ANY TIER-2 DATA EXISTS.
#
# Every requirement this paper writes is single-tier evidence. The program's own premise is that
# SandTable searches and ProjectGL confirms, and there are currently ZERO cross-tier data points.
# This battery does the half that can be run without ProjectGL: it fixes the tier-1 predictions at
# the exact operating point the confirmation run will use, on the observables the two tiers SHARE,
# so the comparison is against a registered number rather than against whatever tier 1 says on the
# day tier-2 data arrives.
#
# Operating point, fixed here and not to be re-chosen later: published physics, n_blue = 8, clear
# link (C0), default fleet, blind against refund against admit. Chosen because it carries the
# paper's largest and cheapest lever, because the published success gap there is 23.8 points and so
# is detectable at the five-to-ten missions per arm that tier 2 costs, and because CR-69 says
# success has full range at eight assets, so the pre-flight for censoring passes by construction.
#
# Observables restricted to what a high-fidelity tier can be expected to report: mission success,
# arrived fraction, blue losses, mission time. No served_per_step, no console telemetry. Tier 2 does
# not owe us our instruments.
#
# C2 is carried as a second link state so a tier-2 team that cannot reproduce a perfectly clear link
# still has a registered cell to land in.
. hopper/batteries/_common.sh

echo "### BATTERY crosstier START"

for M in success arrived_frac blue_losses blue_loss_frac mission_time; do
echo "### X1 the bridge operating point, blind vs refund vs admit ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,2' \
  --arm "blind={$D,\"n_blue\":8}" \
  --arm "refund={$D,\"n_blue\":8,\"queue_policy\":\"refund\"}" \
  --arm "admit={$D,\"n_blue\":8,\"queue_policy\":\"admit\"}"
done

# X2. The sensitivity the tier-2 team will ask about first: how much does the prediction move if
# their scenario is not exactly ours? Span is the parameter most likely to differ, so the same
# contrast is registered across the spans a confirmation run might plausibly be built at. A bridge
# whose sign holds across this range is one a tier-2 team can land in without matching us exactly.
for M in success arrived_frac blue_losses; do
echo "### X2 the same contrast across the spans a confirmation run might use ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,10,12' \
  --arm "blind={$D,\"comms_level\":0}" \
  --arm "refund={$D,\"comms_level\":0,\"queue_policy\":\"refund\"}" \
  --arm "admit={$D,\"comms_level\":0,\"queue_policy\":\"admit\"}"
done

echo "### BATTERY crosstier DONE"
