# CR-75, section X3, split into its own job so it does not queue behind X1 and X2.
#
# The section that decides what the latent-shift model is ABOUT. X1 and X2 move the baseline by
# changing opposing strength, which is the same knob the model was fitted on, so a model that is
# secretly a fact about red strength would pass both. X3 moves the baseline with SPAN instead, at an
# opposing strength that appears nowhere in the fit, and asks whether the effects land on the same
# curve. If they do, the compression belongs to the metric. If they do not, it belongs to the knob,
# and the account is wrong in the way that matters most.
#
# Prediction is unchanged and carries no free parameters: effect(b) = Phi(Phi^-1(b) + delta) - b
# with delta 0.454 for the backlog bound and 0.394 for the admission rule, both from CR-74.
# Falsifier: RMS deviation above 0.045 across the gradeable cells.
. hopper/batteries/_common.sh
BLDN='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind"'
ADM='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'

echo "### BATTERY ceiling3 START"
for M in success blue_loss_frac served_per_step; do
echo "### X3 the same curve reached by moving span instead, n_red=9 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24,32' \
  --arm "blindUnbound={$BLDN,\"n_red\":9}" \
  --arm "boundOne={$BLDN,\"n_red\":9,\"queue_capacity\":1}" \
  --arm "admits={$ADM,\"n_red\":9}"
done
echo "### BATTERY ceiling3 DONE"
