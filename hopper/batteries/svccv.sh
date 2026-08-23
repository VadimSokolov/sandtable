# CR-51 and CR-53. THE OPERATOR IS A METRONOME, IN SANDTABLE THIS TIME.
#
# service_cv is now a parameter of the console: zero is the published metronome and every closed
# form in this paper was derived against it, above zero the service time is a gamma with the SAME
# MEAN so anything that moves is variability and not speed. The draw is skipped at zero, so the
# published path is bit-identical, which tests/test_c2.py pins.
#
# REGISTERED (CR-53), with the n=10 blind rows declared read in advance:
#   P1. the console-metric gain from cv > 0 is largest where the blind console is collapsed and
#       vanishes where it is not.
#   P2. on a console that already randomizes or already runs admission control, the gain is smaller.
#       NOTE, recorded before the run: `retry_spread` jitters the hold a REBUFFED vehicle waits, and
#       a blind console rebuffs nobody, so a jitter arm is only meaningful on top of admission
#       control. A first version of this battery paired it with `blind`, where it is a no-op and
#       measured bit-identical to the control; that arm was replaced before any of it was read.
#   P3. the mission-metric LOSS is real and gated.
# And CR-51 P2 in the full simulator: the lever's sign does not change with cv.
. hopper/batteries/_common.sh
D='"control_mode":"direct","comms_level":0'

for M in served_per_step success operator_goodput; do
echo "### C1 service variability against span, blind console ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12,16' \
  --arm "cv00={$D}" \
  --arm "cv25={$D,\"service_cv\":0.25}" \
  --arm "cv50={$D,\"service_cv\":0.5}" \
  --arm "cv100={$D,\"service_cv\":1.0}"
echo "### C2 does the gain survive a console that already desynchronizes ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,10,12' \
  --arm "blind_cv00={$D}" \
  --arm "blind_cv50={$D,\"service_cv\":0.5}" \
  --arm "admit_cv00={$D,\"queue_policy\":\"admit\"}" \
  --arm "admit_cv50={$D,\"queue_policy\":\"admit\",\"service_cv\":0.5}" \
  --arm "ajit_cv00={$D,\"queue_policy\":\"admit\",\"retry_spread\":8}" \
  --arm "ajit_cv50={$D,\"queue_policy\":\"admit\",\"retry_spread\":8,\"service_cv\":0.5}"
done
