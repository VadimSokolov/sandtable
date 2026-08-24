# CR-65. THE BLIND CONSOLE'S WASTE IS FREE TO REMOVE AND IT BUYS ALMOST NOTHING.
#
# Registered in doc/autoresearch-conjectures.md with the pilot disclosed. A request whose vehicle has
# already asked again is a ghost: nobody is holding the answer. The published console discovers this
# by working the request. `stale_check = "before"` discovers it by reading `req_seq`, the console's
# own record of what each vehicle last asked, which travels in no message. The repair is free in
# information and free in time and it removes ALL of the waste rather than some. The registered
# prediction is that it buys almost no throughput, because the dead clock is CONSERVED: it moves
# from stale to late. `busy_dead` is reported beside `busy_stale` in every section for exactly that
# reason, since a reader shown only the bucket that fell would read a relabelling as a recovery.
. hopper/batteries/_common.sh
GW='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind"'
GD='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind","stale_check":"before"'
AD='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'
# U2 carries CR-64's own fleet, because a section about which rule reaches which ghost first has to
# be read on a fleet whose deadlines differ; on a uniform fleet the stratified readings are
# undefined and the comparison would be to arrival order under another name.
GF='"patience_spread":12,"patience_shape":"twopoint"'

echo "### BATTERY ghost START"

# U1. The decomposition against span, with the zero-information BOUND in the same table. The bound
# is drop-oldest at capacity: refusal by overflow, which costs no information either and is the
# floor that any claim about what the deadline field buys has to clear first.
for M in busy_stale busy_late busy_dead busy_serviced served_per_step answer_rate_v stale_frac stale_dropped_frac; do
echo "### U1 what dropping the ghost buys, against span ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,12,16,24' \
  --arm "worksGhost={$GW}" \
  --arm "dropsGhost={$GD}" \
  --arm "boundTwo={$GW,\"queue_capacity\":2}" \
  --arm "admits={$AD}"
done

# U2. The link to CR-64. On a blind console the ORDER decides which ghosts the console reaches
# first, and the pilot says serve-least-served spends 0.6177 of its clock on them at eight assets
# against arrival order's 0.2670. If that is why the discipline ordering inverts on a console that
# cannot refuse, dropping the ghost should COLLAPSE the difference between the three rules rather
# than shift all three. This section decides whether CR-64's inversion is a property of the rules
# or of what a blind buffer contains.
for M in busy_stale busy_dead served_per_step answer_rate_v starved_frac answer_step_share; do
echo "### U2 order and ghost on a console that cannot refuse ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24' \
  --arm "fcfsWorks={$GW,$GF}" \
  --arm "rrWorks={$GW,$GF,\"queue_discipline\":\"round_robin\"}" \
  --arm "edfWorks={$GW,$GF,\"queue_discipline\":\"edf\"}" \
  --arm "fcfsDrops={$GD,$GF}" \
  --arm "rrDrops={$GD,$GF,\"queue_discipline\":\"round_robin\"}" \
  --arm "edfDrops={$GD,$GF,\"queue_discipline\":\"edf\"}"
done

# U3. The cadence control, and it is the answer to the sharpest objection this result faces: the
# ghost population is manufactured by how fast a requester that gave up comes back, so a claim about
# wasted effort measured at one cadence is a claim about that cadence. `reask_hold` scales the hold
# and the sweep spans sixteenfold. The pilot says `busy_stale` moves from 0.9525 to 0.9608 across
# the whole range, so the registered prediction is EQUIVALENCE and the section exists to put that on
# the record rather than to find an effect. Eight assets is carried BECAUSE the pilot says the
# cadence bites hard there and not at sixteen: 2x takes `busy_stale` from 0.2025 to 0.0099 and
# `served_per_step` from 0.0374 to 0.0837. Reporting inertness measured only at the span where
# nothing moves would be the flat-reference defect wearing a control's clothes.
for M in busy_stale busy_dead busy_serviced served_per_step answer_rate_v stale_frac requests_per_step; do
echo "### U3 the ghost clock against the re-ask cadence ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'reask_hold=0.25,0.5,1.0,2.0,4.0,8.0,16.0' \
  --arm "worksSixteen={$GW,\"n_blue\":16}" \
  --arm "dropsSixteen={$GD,\"n_blue\":16}" \
  --arm "worksEight={$GW,\"n_blue\":8}" \
  --arm "dropsEight={$GD,\"n_blue\":8}"
done

# U4. The negative control, and it is the defect-14 guard rather than an extra section. The claim is
# about a console losing its clock to ghosts, so it is checked where there are none: a short span on
# a fast console, where the pilot reads `busy_stale` at zero. Every arm must be equivalent on every
# reading. If the arms separate where there is nothing to repair, the repair is not what is doing
# the work anywhere else either.
for M in busy_stale busy_dead served_per_step answer_rate_v abandoned_per_step success; do
echo "### U4 where there is no ghost to drop ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=2,3,4' \
  --arm "worksGhost={$GW,\"service_rate\":1.2}" \
  --arm "dropsGhost={$GD,\"service_rate\":1.2}" \
  --arm "admits={$AD,\"service_rate\":1.2}"
done

# U5. The link, because every console recommendation in this paper is checked against the ladder it
# will be flown on. A degraded link drops requests before they reach the buffer, which is an
# accidental admission control, so the ghost problem should SHRINK as the link gets worse. That is a
# prediction with a sign, and it is the one direction in which the repair could look better than it
# is.
for M in busy_stale busy_dead served_per_step answer_rate_v abandoned_per_step success; do
echo "### U5 the ghost against the comms ladder ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,2,3,4' \
  --arm "worksGhost={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"blind\",\"n_blue\":16}" \
  --arm "dropsGhost={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"blind\",\"stale_check\":\"before\",\"n_blue\":16}" \
  --arm "admits={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"admit\",\"n_blue\":16}"
done

# U6. Load rather than span. Twelve assets on a slow console and twenty-four on a fast one are the
# same offered load and a different fleet, and a claim about a console should follow the load rather
# than the headcount. The span is held at sixteen and the console speed is swept instead.
for M in busy_stale busy_dead served_per_step answer_rate_v abandoned_per_step; do
echo "### U6 the same question on the console speed rather than the fleet ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'service_rate=0.15,0.25,0.5,0.8' \
  --arm "worksGhost={$GW,\"n_blue\":16}" \
  --arm "dropsGhost={$GD,\"n_blue\":16}" \
  --arm "admits={$AD,\"n_blue\":16}"
done

echo "### BATTERY ghost DONE"
