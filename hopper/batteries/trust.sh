# CR-61 AS AMENDED. THE COST OF SCRUTINY IS NOT THE SCRUTINY.
#
# Registered in doc/autoresearch-conjectures.md, amendment included, with three pilots disclosed.
# Every console in eleven batteries was an oracle, which made the project's own recorded literature
# gap D7 uncomputable. The operator can now be wrong, its check-or-ship decision is a signal
# detection one, and a wrong answer can harm either through the requester's TIME or through the
# vehicle's own effectiveness.
#
# The registration was rewritten before this battery ran, twice. The h-sweep came out because a
# time price provably cannot represent a harm that makes a vehicle fight worse. The closed form
# q* = 1 - comply_frac came out because it is wrong by a term: it omits the queue of vehicles idled
# behind each check, and that term is four times the one it kept.
. hopper/batteries/_common.sh
TB='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5'
T="$TB,\"auto_error\":0.5"
NOP='"control_mode":"supervisory","comms_level":0'

echo "### BATTERY trust START"

# S1, Q1 and Q2 together, because the decomposition is the claim and the crossing is only its setup.
# `nop` is the same force with no console at all, which is the baseline an operator has to beat and
# which no earlier battery in this paper ever ran as a comparator. The `free` arms price a waiting
# asset at q_auto instead of q_stall: same console, same checking, waiting made free.
for M in success blue_loss_frac served_per_step answer_correct_frac operator_utilization; do
echo "### S1 does an operator beat no operator, and what carries the answer ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16' \
  --arm "nop={$NOP}" \
  --arm "chk100={$T,\"bad_answer_harm\":\"reflect\"}" \
  --arm "chk000={$T,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "chk100free={$T,\"bad_answer_harm\":\"reflect\",\"q_stall\":0.70}" \
  --arm "chk000free={$T,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\",\"q_stall\":0.70}"
done

# S2, Q3. The requirement, swept in the units a programme can write it in. If there is an interior
# threshold in q_stall above which the always-checking console beats no console, that number is the
# requirement, and it is about what a waiting asset may DO rather than about the console at all.
for M in success blue_loss_frac; do
echo "### S2 the threshold on what a waiting asset may do ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'q_stall=0.30,0.40,0.50,0.60,0.70' \
  --arm "chk100={$T,\"n_blue\":8,\"bad_answer_harm\":\"reflect\"}" \
  --arm "chk050={$T,\"n_blue\":8,\"check_rate\":0.5,\"bad_answer_harm\":\"reflect\"}" \
  --arm "chk000={$T,\"n_blue\":8,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}"
done

# S3, Q6. Corners are the wrong comparison, so this is the curve. r* is read off each column.
for M in success blue_loss_frac served_per_step operator_utilization answer_correct_frac; do
echo "### S3 the optimal check rate against console load ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16' \
  --arm "r000={$T,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "r025={$T,\"check_rate\":0.25,\"bad_answer_harm\":\"reflect\"}" \
  --arm "r050={$T,\"check_rate\":0.5,\"bad_answer_harm\":\"reflect\"}" \
  --arm "r075={$T,\"check_rate\":0.75,\"bad_answer_harm\":\"reflect\"}" \
  --arm "r100={$T,\"bad_answer_harm\":\"reflect\"}"
done

# S4, Q7. SUFFICIENCY, not correlation. If r* is scheduled by console slack whatever sets the slack,
# then cells matched on utilization must agree across rungs of the comms ladder. Span and rung are
# crossed so the matched pairs can be found in the output rather than assumed here.
for M in operator_utilization success served_per_step blue_loss_frac; do
echo "### S4 is the check rate scheduled by slack or by the channel ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3' \
  --arm "n06r000={$T,\"n_blue\":6,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "n06r100={$T,\"n_blue\":6,\"bad_answer_harm\":\"reflect\"}" \
  --arm "n08r000={$T,\"n_blue\":8,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "n08r100={$T,\"n_blue\":8,\"bad_answer_harm\":\"reflect\"}" \
  --arm "n16r000={$T,\"n_blue\":16,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "n16r100={$T,\"n_blue\":16,\"bad_answer_harm\":\"reflect\"}"
done

# S5, Q5. The three harm channels on ONE grid. The registered null is that they order the design
# space identically; any inversion is the only thing this model can say about over-trust and is a
# result rather than a failure. Nothing here chooses between them.
for M in success blue_loss_frac served_per_step; do
echo "### S5 three prices for a wrong answer, one grid ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'auto_error=0.1,0.3,0.5,0.7,0.9' \
  --arm "timeR000={$TB,\"n_blue\":8,\"check_rate\":0.0}" \
  --arm "timeR100={$TB,\"n_blue\":8}" \
  --arm "weakR000={$TB,\"n_blue\":8,\"check_rate\":0.0,\"bad_answer_harm\":\"weak\"}" \
  --arm "weakR100={$TB,\"n_blue\":8,\"bad_answer_harm\":\"weak\"}" \
  --arm "reflR000={$TB,\"n_blue\":8,\"check_rate\":0.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "reflR100={$TB,\"n_blue\":8,\"bad_answer_harm\":\"reflect\"}"
done

# S6, D7. The instrument, and the reason a rate cannot stand in for a discrimination score.
# Sensitivity and criterion move independently by construction; the section reports the ROC point.
for M in trust_dprime trust_hit_rate trust_fa_rate check_frac answer_correct_frac success served_per_step; do
echo "### S6 discrimination against criterion, which is the ROC the gap asks for ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,12,16' \
  --arm "d00={$T,\"check_rate\":0.5,\"bad_answer_harm\":\"reflect\"}" \
  --arm "d05={$T,\"check_rate\":0.5,\"check_dprime\":0.5,\"bad_answer_harm\":\"reflect\"}" \
  --arm "d10={$T,\"check_rate\":0.5,\"check_dprime\":1.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "d20={$T,\"check_rate\":0.5,\"check_dprime\":2.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "d10lo={$T,\"check_rate\":0.25,\"check_dprime\":1.0,\"bad_answer_harm\":\"reflect\"}" \
  --arm "d10hi={$T,\"check_rate\":0.75,\"check_dprime\":1.0,\"bad_answer_harm\":\"reflect\"}"
done

echo "### BATTERY trust COMPLETE"
