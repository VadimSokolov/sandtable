# CR-70. THE CONSOLE REQUIREMENT DOES NOT STOP MATTERING AT SCALE; MISSION SUCCESS STOPS SEEING IT.
#
# Registered in doc/autoresearch-conjectures.md with the pilot disclosed and two falsifiers, one for
# the conjecture and one for the diagnosis. CR-66's V1 reads the requirements ladder against span on
# `success` and the free bound's value decays from +0.1743 at eight assets to +0.0024 at twenty-four.
# CR-69 then found baseline success pinned at exactly 1.0 from sixteen assets up on this scenario.
# The decay and the ceiling are the same three cells and the ladder battery has no uncensored
# mission axis to tell them apart. This battery supplies one.
#
# Falsifier: boundOne against blindUnbound on blue_loss_frac at twenty-four assets reading
# `equivalent` or gating the wrong way refutes the conjecture.
# Falsifier for the diagnosis: if the success gain is still equivalent at twenty-four once the
# ceiling is lifted at n_red = 8, the decay is real and this is retracted whatever W1 says.
. hopper/batteries/_common.sh
BLDN='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind"'
ADM='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'
MIX='"patience_spread":12,"patience_shape":"twopoint"'
HARD='"n_red":8'

echo "### BATTERY loss START"

# W1. The ladder against span on a uniform fleet, with the censored axis and the uncensored one on
# the same page. blue_losses and blue_survivors are carried because a loss FRACTION on a span sweep
# changes denominator with the sweep, and the counts say whether it moves because fewer die or
# because more are present. Thirty-two is added past CR-66's grid: it is where success is furthest
# into its ceiling and so where the two axes should disagree most.
for M in blue_loss_frac success blue_losses blue_survivors served_per_step starved_frac; do
echo "### W1 the four rungs against span, uniform fleet ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24,32' \
  --arm "blindUnbound={$BLDN}" \
  --arm "boundOne={$BLDN,\"queue_capacity\":1}" \
  --arm "boundTwo={$BLDN,\"queue_capacity\":2}" \
  --arm "admits={$ADM}" \
  --arm "admitsEdf={$ADM,\"queue_discipline\":\"edf\"}"
done

# W2. The same on the TWO-POINT fleet, which is where CR-66's V2 says the rungs come apart. If the
# ordering rung earns anything on the mission it earns it here and nowhere else.
for M in blue_loss_frac success blue_losses served_per_step starved_frac; do
echo "### W2 the four rungs against span, two-point fleet ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24,32' \
  --arm "blindUnbound={$BLDN,$MIX}" \
  --arm "boundOne={$BLDN,$MIX,\"queue_capacity\":1}" \
  --arm "boundTwo={$BLDN,$MIX,\"queue_capacity\":2}" \
  --arm "admits={$ADM,$MIX}" \
  --arm "admitsEdf={$ADM,$MIX,\"queue_discipline\":\"edf\"}"
done

# W3. The discriminator, and the section that decides whether the diagnosis or the decay is right.
# Identical ladder, identical spans, at a red strength where baseline success is saturated nowhere
# (0.125 at eight assets to 0.938 at thirty-two). A success gain that reappears at twenty-four here
# is a gain the published difficulty could not show.
for M in success blue_loss_frac blue_losses served_per_step; do
echo "### W3 the same ladder with the ceiling lifted, n_red=8 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24,32' \
  --arm "blindUnbound={$BLDN,$HARD}" \
  --arm "boundOne={$BLDN,$HARD,\"queue_capacity\":1}" \
  --arm "boundTwo={$BLDN,$HARD,\"queue_capacity\":2}" \
  --arm "admits={$ADM,$HARD}" \
  --arm "admitsEdf={$ADM,$HARD,\"queue_discipline\":\"edf\"}"
done

# W4. The same question as a dose-response rather than at two hand-picked points. Span is held at
# twenty-four, where W1's success gain vanished, and red strength is swept through the ceiling, the
# transition band and the floor. The registered shape is an INTERIOR maximum in the success gain:
# nothing at the ceiling because the metric cannot move, nothing at the floor because the mission is
# lost either way, and the whole effect in the band between. If the gain is flat across this sweep
# then W3 found one lucky cell and the diagnosis does not generalize.
for M in success blue_loss_frac served_per_step; do
echo "### W4 the ladder against red strength at a fixed large span ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_red=4,6,8,10,12' \
  --arm "blindUnbound={$BLDN,\"n_blue\":24}" \
  --arm "boundOne={$BLDN,\"n_blue\":24,\"queue_capacity\":1}" \
  --arm "admits={$ADM,\"n_blue\":24}"
done

echo "### BATTERY loss DONE"
