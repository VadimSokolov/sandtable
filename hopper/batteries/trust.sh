# CR-61. THE OPERATOR CAN NOW BE WRONG, AND D7 IS COMPUTABLE.
#
# Registered in doc/autoresearch-conjectures.md with both pilots disclosed. Every console before
# this one was an oracle: never wrong, only late, lost or refused. That made the project's own
# recorded literature gap D7 uncomputable, because a discrimination score against agent ground-truth
# correctness needs an agent that can be incorrect.
#
# The design rests on one fact the rest of this paper established: AT A SATURATED CONSOLE A SLOT HAS
# A PRICE. Checking a recommendation costs a slot; shipping it costs a quarter of one. So the
# question is not whether checking is good, it is whether it is worth its price, and the price is
# set by load rather than by anything about the autonomy.
. hopper/batteries/_common.sh
TB='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit","service_cv":0.5'
T="$TB,\"auto_error\":0.3"

echo "### BATTERY trust START"

# R1, P1 and P2. The check-rate ladder against the load ladder. The prediction is a flat ladder
# below the collapse span and a steeply falling one above it, which is the shadow price of a slot
# showing up in a decision that has nothing to do with queueing.
for M in served_per_step success answer_correct_frac operator_utilization check_frac; do
echo "### R1 the check ladder against the load ladder ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16' \
  --arm "chk00={$T,\"check_rate\":0.0}" \
  --arm "chk25={$T,\"check_rate\":0.25}" \
  --arm "chk50={$T,\"check_rate\":0.5}" \
  --arm "chk75={$T,\"check_rate\":0.75}" \
  --arm "chk100={$T}"
done

# R2, P3, THE REQUIREMENTS NUMBER. What must a wrong answer cost before checking is worth its slot?
# `bad_answer_hold` is that cost as a multiple of the patience an UNANSWERED vehicle waits, so 1.0
# says a wrong answer is exactly as expensive as no answer and is the weakest assumption available.
for M in success served_per_step answer_correct_frac; do
echo "### R2 the break-even cost of a wrong answer, at sixteen assets ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'bad_answer_hold=1.0,2.0,3.0,5.0,8.0,12.0' \
  --arm "chk00={$T,\"n_blue\":16,\"check_rate\":0.0}" \
  --arm "chk50={$T,\"n_blue\":16,\"check_rate\":0.5}" \
  --arm "chk100={$T,\"n_blue\":16}"
done

# R3, P4 AND D7. At MATCHED checking rate, does discrimination separate operators that the rate
# cannot? This is the section the gap is closed by, and the confusion matrix is carried with it so
# the ROC point is in the log rather than reconstructed from a summary.
for M in trust_dprime trust_hit_rate trust_fa_rate check_frac answer_correct_frac served_per_step success; do
echo "### R3 discrimination against criterion, which is the ROC the gap asks for ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "d00={$T,\"check_rate\":0.5}" \
  --arm "d05={$T,\"check_rate\":0.5,\"check_dprime\":0.5}" \
  --arm "d10={$T,\"check_rate\":0.5,\"check_dprime\":1.0}" \
  --arm "d20={$T,\"check_rate\":0.5,\"check_dprime\":2.0}" \
  --arm "d10lo={$T,\"check_rate\":0.25,\"check_dprime\":1.0}" \
  --arm "d10hi={$T,\"check_rate\":0.75,\"check_dprime\":1.0}"
done

# R4, P5. The centrepiece. If the price of checking is the price of a slot and the slot's price is
# set by load, then jamming, which throttles the arrival of requests, must make checking CHEAPER.
# The correct level of trust in an autonomous subordinate would then be a property of the channel.
for M in success served_per_step answer_correct_frac operator_utilization; do
echo "### R4 does the channel set the right level of trust ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3,4' \
  --arm "chk00={$T,\"n_blue\":16,\"check_rate\":0.0}" \
  --arm "chk50={$T,\"n_blue\":16,\"check_rate\":0.5}" \
  --arm "chk100={$T,\"n_blue\":16}" \
  --arm "h5c00={$T,\"n_blue\":16,\"check_rate\":0.0,\"bad_answer_hold\":5.0}" \
  --arm "h5c100={$T,\"n_blue\":16,\"bad_answer_hold\":5.0}"
done

# R5. The autonomy's own error rate, which is the axis a procurement document would write. If the
# break-even checking rate moves LESS with q than it does with the span, that is the sentence: a
# trust policy cannot be specified from the autonomy's error rate alone.
for M in success served_per_step answer_correct_frac; do
echo "### R5 the axis a specification would use ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'auto_error=0.05,0.1,0.2,0.3,0.5' \
  --arm "n8c00={$TB,\"n_blue\":8,\"check_rate\":0.0}" \
  --arm "n8c100={$TB,\"n_blue\":8}" \
  --arm "n16c00={$TB,\"n_blue\":16,\"check_rate\":0.0}" \
  --arm "n16c100={$TB,\"n_blue\":16}"
done

echo "### BATTERY trust COMPLETE"
