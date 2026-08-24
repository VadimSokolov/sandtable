# CR-67. THE SIGN OF THE FLEET-SIDE LEVER IS SET BY THE CONSOLE'S POLICY.
#
# Registered in doc/autoresearch-conjectures.md with the pilot disclosed. Every console lever in this
# paper so far has been on the console: which request to serve, whether to refuse it, whether to
# recognise it as superseded. `reask_hold` is on the other side. It changes how long a vehicle that
# gave up stays on autonomy before asking again, it changes nothing whatever on the console, and it
# requires no message, no field and no coordination. The pilot says it is a large POSITIVE lever on a
# console that cannot refuse and a NEGATIVE one on a console that can, which makes the two sides of
# the system not separable and makes the fleet-side change unprocurable without knowing the console.
#
# `answer_rate_v` is carried in every section but is NOT this battery's primary reading, and the
# reason is a rule this project already wrote down: a metric whose denominator the treatment moves
# cannot audit that treatment. Slowing the fleet is a change to how often vehicles ASK, which is
# exactly that denominator, so a rise in the answered fraction is partly mechanical. The primary
# intermediate reading is `served_per_step`, whose denominator is the mission clock and which the
# treatment does not touch, and every cell is gated on `success` and `blue_loss_frac` as well, since
# the mission is the arbiter of a lever whose two intermediate readings disagree.
#
# It also splits two metrics that agree everywhere else in this paper: on a refusing console, slowing
# the fleet RAISES the per-vehicle answer rate and LOWERS delivered throughput at the same time.
. hopper/batteries/_common.sh
BL='"control_mode":"direct","queue_model":"buffer","queue_policy":"blind"'
BD='"control_mode":"direct","queue_model":"buffer","queue_policy":"blind","queue_capacity":2'
AD='"control_mode":"direct","queue_model":"buffer","queue_policy":"admit"'
SLOW='"reask_hold":4.0'

echo "### BATTERY fleet START"

# W1. The lever on three consoles against span, on a clear link. The admitting console is expected
# INERT here and the reason is structural rather than empirical: its refusal hold is min(2*lat,
# patience), which is zero at zero latency, so there is nothing for the knob to scale. That
# prediction is registered so the null is read as a mechanism rather than as an absence of effect.
for M in served_per_step answer_rate_v abandoned_per_step requests_per_step busy_dead success blue_loss_frac; do
echo "### W1 the fleet cadence on three consoles, clear link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,12,16' \
  --arm "blindBase={$BL,\"comms_level\":0}" \
  --arm "blindSlow={$BL,\"comms_level\":0,$SLOW}" \
  --arm "boundBase={$BD,\"comms_level\":0}" \
  --arm "boundSlow={$BD,\"comms_level\":0,$SLOW}" \
  --arm "admitBase={$AD,\"comms_level\":0}" \
  --arm "admitSlow={$AD,\"comms_level\":0,$SLOW}"
done

# W2. The same six arms against the LINK, which is where the sign flip is sharpest because latency
# is what gives the refusing console a hold to scale in the first place. This is the section the
# headline rests on.
for M in served_per_step answer_rate_v abandoned_per_step requests_per_step busy_dead success blue_loss_frac; do
echo "### W2 the fleet cadence against the comms ladder ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,2,3,4' \
  --arm "blindBase={$BL,\"n_blue\":8}" \
  --arm "blindSlow={$BL,\"n_blue\":8,$SLOW}" \
  --arm "boundBase={$BD,\"n_blue\":8}" \
  --arm "boundSlow={$BD,\"n_blue\":8,$SLOW}" \
  --arm "admitBase={$AD,\"n_blue\":8}" \
  --arm "admitSlow={$AD,\"n_blue\":8,$SLOW}"
done

# W3. The cadence curve on each console, because a lever with a sign that depends on the console
# probably has a magnitude that depends on how hard it is pulled, and a recommendation to "back off"
# without a number is not a recommendation. Run at C2 so all three consoles have a hold to scale.
for M in served_per_step answer_rate_v abandoned_per_step requests_per_step success blue_loss_frac; do
echo "### W3 how far to back off, on each console ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'reask_hold=1.0,2.0,4.0,8.0,16.0' \
  --arm "blind={$BL,\"n_blue\":8,\"comms_level\":2}" \
  --arm "bound={$BD,\"n_blue\":8,\"comms_level\":2}" \
  --arm "admit={$AD,\"n_blue\":8,\"comms_level\":2}"
done

# W4. The other fleet-side lever, in the opposite direction. Retrying is asking again SOONER, and the
# pilot says it costs 0.0386 served per step down to 0.0138 on the blind console at eight assets. Two
# fleet-side changes, no console change in either, opposite signs: that is the point of running them
# in one battery rather than reporting each against its own baseline.
for M in served_per_step answer_rate_v abandoned_per_step requests_per_step success blue_loss_frac; do
echo "### W4 the opposite fleet-side lever on the same three consoles ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,12,16' \
  --arm "blindBase={$BL,\"comms_level\":2}" \
  --arm "blindRetry={$BL,\"comms_level\":2,\"retry_prob\":1.0,\"retry_backoff\":4}" \
  --arm "boundBase={$BD,\"comms_level\":2}" \
  --arm "boundRetry={$BD,\"comms_level\":2,\"retry_prob\":1.0,\"retry_backoff\":4}" \
  --arm "admitBase={$AD,\"comms_level\":2}" \
  --arm "admitRetry={$AD,\"comms_level\":2,\"retry_prob\":1.0,\"retry_backoff\":4}"
done

# W5. The negative control, and it is the defect-14 guard. A fleet-side lever acts by changing
# offered load, so where the console is not load-limited it must do nothing at all on any console.
# Two to four assets on a fast console is that place, and every pair must be equivalent there.
for M in served_per_step answer_rate_v abandoned_per_step requests_per_step success blue_loss_frac; do
echo "### W5 where the console is not load-limited ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,3,4' \
  --arm "blindBase={$BL,\"comms_level\":2,\"service_rate\":1.2}" \
  --arm "blindSlow={$BL,\"comms_level\":2,\"service_rate\":1.2,$SLOW}" \
  --arm "admitBase={$AD,\"comms_level\":2,\"service_rate\":1.2}" \
  --arm "admitSlow={$AD,\"comms_level\":2,\"service_rate\":1.2,$SLOW}"
done

echo "### BATTERY fleet DONE"
