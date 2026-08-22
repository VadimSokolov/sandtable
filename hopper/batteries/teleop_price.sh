# CR-29. THE EXPOSURE TEST, PRICED BY A MECHANISM AUTHORED FOR SOMETHING ELSE.
#
# CR-28 asked whether "do not re-ask" survives pricing a wait by exposure, using a `stall_decay`
# knob written for the purpose. A null on a self-authored knob with a self-chosen range is not
# evidence, so that version is cut. This one prices the wait with `behavior.py`, written two
# conjectures earlier for CR-2 on the observation that the published model let a teleoperated
# vehicle keep driving at 54.5% speed with its operator link severed. Under `teleop_stop = true` a
# vehicle with no answer coming back STOPS. `teleop_stop = false` reproduces the published path
# exactly, which is the control, and the pilot confirms the identity cell for cell.
#
# REGISTERED (full text in doc/autoresearch-conjectures.md, CR-29).
#   1. Confirmatory, pilot-suggested and declared as such: under stop-dead physics no-retry still
#      leads and the retry penalty is LARGER, not smaller. FALSIFIER: any retry arm gates above
#      no-retry there.
#   2. The falsifiable content: the mechanism is time in stall, so `hold_fraction` rises
#      monotonically as the backoff shortens and the success damage tracks it. FALSIFIER: flat or
#      non-monotone hold fraction while success still moves.
#   3. `blue_loss_frac` is a CONFOUND here, not a gate. In the pilot rho = 4 has the highest hold
#      fraction and the LOWEST blue losses, because vehicles that never advance are never engaged.
#      Read only jointly with `arrived_frac`.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
J='"retry_prob":1.0,"retry_spread":0'
T='"blue_behavior":"teleop"'

# P1. The recommendation grid under both physics. The `keeps` arms are the identity control: they
# must reproduce the no-behaviour-layer path, and any drift there invalidates the whole contrast.
for M in success arrived_frac hold_fraction; do
echo "### P1 the retry ladder under stop-dead against keeps-driving physics ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6,8' \
  --arm "keep_noretry={$C,$G,$T,\"teleop_stop\":false}" \
  --arm "keep_rho04={$C,$G,$T,\"teleop_stop\":false,$J,\"retry_backoff\":4}" \
  --arm "keep_rho12={$C,$G,$T,\"teleop_stop\":false,$J,\"retry_backoff\":12}" \
  --arm "keep_rho21={$C,$G,$T,\"teleop_stop\":false,$J,\"retry_backoff\":21}" \
  --arm "keep_adapt={$C,$G,$T,\"teleop_stop\":false,$J,\"retry_backoff\":4,\"retry_mode\":\"double\"}" \
  --arm "stop_noretry={$C,$G,$T,\"teleop_stop\":true}" \
  --arm "stop_rho04={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":4}" \
  --arm "stop_rho12={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":12}" \
  --arm "stop_rho21={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":21}" \
  --arm "stop_adapt={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":4,\"retry_mode\":\"double\"}"
done

# P2. The finer backoff ladder under stop-dead physics alone, which is where the monotonicity
# claim of prediction 2 has to hold. A knee here would be the first one this project has found,
# and CR-23 died looking for one, so it is worth the arms to be able to say either way.
for M in hold_fraction success; do
echo "### P2 the fine backoff ladder under stop-dead physics ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6' \
  --arm "rho02={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":2}" \
  --arm "rho04={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":4}" \
  --arm "rho08={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":8}" \
  --arm "rho12={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":12}" \
  --arm "rho16={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":16}" \
  --arm "rho21={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":21}" \
  --arm "noretry={$C,$G,$T,\"teleop_stop\":true}"
done

# P3. The bloodless-day confound, measured rather than assumed. Blue losses and arrival fraction
# on the same arms: if the low-loss arms are also the low-arrival arms, the loss metric is
# reporting non-advance and cannot gate anything, and this is the cell that says so.
for M in blue_loss_frac arrived_frac; do
echo "### P3 losses read jointly with arrivals, so non-advance cannot pass for survival ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6' \
  --arm "stop_noretry={$C,$G,$T,\"teleop_stop\":true}" \
  --arm "stop_rho04={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":4}" \
  --arm "stop_rho12={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":12}" \
  --arm "stop_rho21={$C,$G,$T,\"teleop_stop\":true,$J,\"retry_backoff\":21}"
done

# P4. Does the console's own fix still work when the wait is priced? `refund` and `admit` were
# measured under physics that let a stalled vehicle drive. If admission control is the lever the
# paper leads with, it has to hold where waiting actually costs something.
echo "### P4 the console policies under stop-dead physics (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6,8' \
  --arm "blind={$C,$G,$T,\"teleop_stop\":true}" \
  --arm "refund={$C,$G,$T,\"teleop_stop\":true,\"queue_policy\":\"refund\"}" \
  --arm "admit={$C,$G,$T,\"teleop_stop\":true,\"queue_policy\":\"admit\"}"
