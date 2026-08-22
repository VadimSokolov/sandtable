# CR-30. THE ORACLE OPERATOR, AND WHETHER THE PAPER DEPENDS ON IT.
#
# Fable's Round 11, and it names the single largest threat to this paper. The thesis as first
# written said an operator's effective span is a queueing outcome "rather than a property of human
# attention". That proves too much. This model contains NO psychology by construction: the operator
# never errs, never slows, never tires, and answers the ten-thousandth request exactly as well as
# the first. So the attention term was removed by assumption, and reporting its absence as a
# discovery is the review that kills. The utilization-performance relation is a real literature and
# the sentence waved it away.
#
# Two repairs. The thesis is rescoped to SUFFICIENCY, which is what the model can actually support:
# queueing alone, with a flawless operator, suffices to produce the span pathologies usually
# attributed to attention, so attention arguments ALONE cannot set span doctrine. And the
# assumption is tested rather than merely declared, which is what this battery does.
#
# `q_droop` takes the quality of a serviced decision down toward the autonomous baseline in
# proportion to the console's running utilization. It is the DESCENDING limb of the
# utilization-performance relation, not the full inverted U, and it is a sensitivity control rather
# than a claim about people. Zero is byte-identical to the published model.
#
# REGISTERED. The claim is about ORDERINGS, not magnitudes, because magnitudes under an invented
# droop rate would be exactly the self-authored-knob error that killed CR-28.
#   1. Every shipped ordering survives at every droop level: admit over blind at the centerpiece
#      operating point on success and on goodput, refund over blind there, no-retry over rho = 4 on
#      the bursty channel, and supervisory over direct at high span. That last one is ONE-SIDED
#      by construction, because a droop harms only the direct arm, so it is reported and not
#      counted among the orderings that could have failed.
#   FALSIFIER: any one of those five reverses sign at any droop level, in which case the result it
#   supports is conditional on an oracle operator and the manuscript says so in those words next to
#   that result.
#   2. A DECOMPOSITION, and the prediction is split because the first version of it was aimed at
#      something this knob cannot produce. Fable's Round 11 co-option sentence said a droop should
#      move the collapse itself left, since a degraded answer is rework and rework is offered load.
#      That carries a rework CONDITION which this model does not meet, verified in the code before
#      this battery ran: `_reset_cooldown` sees the terrain difficulty and nothing else, and
#      `control_quality` reaches motion, engagement and belief but never the request cadence. A
#      badly served vehicle drives slower and shoots worse; it does not ask again sooner. The
#      queue's booking arithmetic is quality-BLIND by construction, so an O4 that predicted a
#      moving cliff would have been refuted by construction rather than on the merits. Split:
#        2a. The SUCCESS-optimal span moves LEFT as droop rises, because quality reaches the
#            mission even though it does not reach the queue.
#        2b. The GOODPUT cliff location is droop-INVARIANT, up to the second-order mission loop
#            (fewer surviving vehicles offer less load).
#      FALSIFIER for the pair: the goodput cliff moves materially while the success optimum does
#      not, which would mean quality is reaching the booking arithmetic by a path neither of us
#      found in the code, and the mechanism section would need it.
#      Passing 2a and 2b together is itself the result: quality effects and load effects separate
#      exactly where the model's own structure says they must, which is a sharper statement than
#      the co-option claim it replaces. The full co-option claim needs a rework knob, not attempted.
#
# A 48-seed pilot ran first and all five orderings held, with the goodput gap flat at +0.542 to
# +0.564 across the whole droop range. That is recorded so the tier result cannot be read as if the
# registration had been written to fit it.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'

# O1. The two console levers at the operating point the paper quotes, on both metrics.
for M in success operator_goodput; do
echo "### O1 admission control against the oracle assumption ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'q_droop=0.0,0.25,0.5,0.75,1.0' \
  --arm "blind={$D,\"n_blue\":8}" \
  --arm "refund={$D,\"n_blue\":8,\"queue_policy\":\"refund\"}" \
  --arm "admit={$D,\"n_blue\":8,\"queue_policy\":\"admit\"}"
done

# O2. The retry recommendation and the modality crossover, which are the other two shipped
# orderings. The crossover is the one a droop could most plausibly move, because a degraded
# operator is a worse operator and supervisory control does not have one.
echo "### O2 the retry recommendation under droop (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'q_droop=0.0,0.25,0.5,0.75,1.0' \
  --arm "noretry={$D,$G,\"comms_level\":3,\"n_blue\":6}" \
  --arm "rho04={$D,$G,\"comms_level\":3,\"n_blue\":6,\"retry_prob\":1.0,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "rho21={$D,$G,\"comms_level\":3,\"n_blue\":6,\"retry_prob\":1.0,\"retry_backoff\":21,\"retry_spread\":0}"

echo "### O3 the modality crossover under droop (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'q_droop=0.0,0.25,0.5,0.75,1.0' \
  --arm "dir06={\"control_mode\":\"direct\",\"comms_level\":3,\"n_blue\":6}" \
  --arm "sup06={\"control_mode\":\"supervisory\",\"comms_level\":3,\"n_blue\":6}" \
  --arm "dir12={\"control_mode\":\"direct\",\"comms_level\":3,\"n_blue\":12}" \
  --arm "sup12={\"control_mode\":\"supervisory\",\"comms_level\":3,\"n_blue\":12}"

# O4. The decomposition of prediction 2, and it needs BOTH metrics over the same span sweep,
# because the whole claim is that they come apart. Goodput is the queue's own metric and should
# not move its cliff; success is the mission's and should move its optimum.
for M in operator_goodput success; do
echo "### O4 does quality reach the queue, or only the mission? ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,7,8,10,12' \
  --arm "oracle={$D,\"q_droop\":0.0}" \
  --arm "droop50={$D,\"q_droop\":0.5}" \
  --arm "droop100={$D,\"q_droop\":1.0}"
done
