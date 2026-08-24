# CR-63. THE VERIFICATION FRONTIER, AND THE DEGENERATE CORNER THAT WAS CARRYING CR-61's HEADLINE.
#
# Registered in doc/autoresearch-conjectures.md before this ran. The `trust` battery's three-price
# comparison had two corners and no middle, and one of those corners is a constant: at check_rate 1.0
# every wrong answer is caught, so the harm channel and the automation error rate are both inert and
# the six always-checking cells are byte-identical. Instrument defect 14, a REFERENCE that cannot
# move. This battery supplies the interior, the stakes ladder the reviewer registered, and the one
# cheap test that can kill the throughput explanation outright.
. hopper/batteries/_common.sh
TB='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5'

echo "### BATTERY verify START"

# R1. The interior of the check ladder, in each of the three harm channels. The registered claim is
# that the best rate is interior somewhere and rises with the automation's error rate. The falsifier
# is a tolerance band that contains a corner in every cell, which would make the finding binary.
for CH in time weak reflect; do
for M in success blue_loss_frac served_per_step answer_correct_frac; do
echo "### R1 the check ladder interior, $CH channel ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'auto_error=0.1,0.3,0.5,0.7,0.9' \
  --arm "r000={$TB,\"n_blue\":8,\"bad_answer_harm\":\"$CH\",\"check_rate\":0.0}" \
  --arm "r025={$TB,\"n_blue\":8,\"bad_answer_harm\":\"$CH\",\"check_rate\":0.25}" \
  --arm "r050={$TB,\"n_blue\":8,\"bad_answer_harm\":\"$CH\",\"check_rate\":0.50}" \
  --arm "r075={$TB,\"n_blue\":8,\"bad_answer_harm\":\"$CH\",\"check_rate\":0.75}" \
  --arm "r100={$TB,\"n_blue\":8,\"bad_answer_harm\":\"$CH\",\"check_rate\":1.0}"
done
done

# R2. The stakes ladder. `g = q_operator - q_auto` is what a right answer is worth, swept by moving
# the autonomy baseline under a fixed operator. The reflect channel is used because it is the only
# one in which a wrong answer can put a vehicle BELOW its own autonomy, which is the failure mode
# the whole over-trust literature is about.
for M in success blue_loss_frac served_per_step; do
echo "### R2 the stakes ladder, what a right answer is worth ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'q_auto=0.50,0.60,0.70,0.80,0.90' \
  --arm "nop={\"control_mode\":\"supervisory\",\"comms_level\":0}" \
  --arm "g000={$TB,\"n_blue\":8,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":0.0}" \
  --arm "g050={$TB,\"n_blue\":8,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":0.50}" \
  --arm "g100={$TB,\"n_blue\":8,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":1.0}"
done

# R3. The decomposition, and the only arm here that can kill the reading outright. If never checking
# wins because a shipped answer costs a fraction of a slot, then pricing a shipped answer at a FULL
# slot must take the advantage away. If it does not, throughput is not the mechanism.
for M in success served_per_step blue_loss_frac; do
echo "### R3 is the advantage throughput or correctness ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comply_frac=0.25,0.50,0.75,1.0' \
  --arm "c000={$TB,\"n_blue\":8,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":0.0}" \
  --arm "c050={$TB,\"n_blue\":8,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":0.50}" \
  --arm "c100={$TB,\"n_blue\":8,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":1.0}"
done

# R4. The frontier against console load, because a rate that is right at eight assets need not be
# right at sixteen, and the whole point of the ladder is that the console is capacity-limited.
for M in success blue_loss_frac operator_utilization; do
echo "### R4 the frontier against console load ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16' \
  --arm "l000={$TB,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":0.0}" \
  --arm "l050={$TB,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":0.50}" \
  --arm "l100={$TB,\"auto_error\":0.5,\"bad_answer_harm\":\"reflect\",\"check_rate\":1.0}" \
  --arm "lnop={\"control_mode\":\"supervisory\",\"comms_level\":0}"
done

echo "### BATTERY verify DONE"
