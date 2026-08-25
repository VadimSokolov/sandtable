# CR-75, section X2, split into its own job. A CAPABILITY'S WORTH IS A CONSTANT; THE METRIC'S COMPRESSION IS WHAT VARIES.
#
# CR-74 fitted one latent shift per capability across the twenty cells of the CR-70 battery and
# predicted the fourth section from the other three at out-of-sample R-squared 0.888. That fit was
# post hoc. This battery is the registered test, and it has NO free parameters: delta is fixed at
# 0.454 for the backlog bound and 0.394 for the admission rule, taken from CR-74 and not refitted.
#
# The prediction is conditional on the baseline the control arm reads in the SAME run, which is what
# makes it testable without knowing in advance where a new operating point will land:
#
#     effect(b) = Phi(Phi^-1(b) + delta) - b
#
# Falsifier, registered before the run: RMS deviation of the observed effects from the predicted
# ones, across all cells of X1 and X2 with a gradeable baseline, exceeding 0.045. That is twice the
# out-of-sample RMS of 0.0225 that CR-74's leave-one-section-out check achieved, so a model that
# holds only as well as it already did passes and one that degrades by a factor of two fails.
# Second falsifier, for the shape rather than the level: the success gain's maximum over X1 falling
# outside the baseline band 0.35 to 0.65. The curve puts it at exactly 0.5 with no freedom at all,
# and W4 observed 0.484 on cells the model was fitted to; this asks for it on cells it was not.
#
# X1 goes deeper into the floor than W4 could. W4 swept red strength to twelve and left baseline
# success at 0.220, so the descending limb of the registered interior maximum rests on a single
# point. Sixteen and twenty push baseline toward zero, where the model predicts the gain collapses
# for the opposite reason it collapses at the ceiling: the mission is lost whatever the console does.
# X2 interpolates at strengths W4 skipped, which tests the curve rather than its endpoints.
. hopper/batteries/_common.sh
BLDN='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind"'
ADM='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'

echo "### BATTERY ceiling2 START"

# X2. The interior, at strengths W4 skipped. These are the cells where the curve is steepest and so
# where a wrong shape costs the most, and none of them appear in the fit.
for M in success blue_loss_frac served_per_step; do
echo "### X2 the interior of the band, strengths the dose-response skipped ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_red=5,7,9,11' \
  --arm "blindUnbound={$BLDN,\"n_blue\":24}" \
  --arm "boundOne={$BLDN,\"n_blue\":24,\"queue_capacity\":1}" \
  --arm "admits={$ADM,\"n_blue\":24}"
done

echo "### BATTERY ceiling2 DONE"
